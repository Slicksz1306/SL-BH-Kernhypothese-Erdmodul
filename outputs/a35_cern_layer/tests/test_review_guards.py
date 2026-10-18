"""Adversarial SYNTHETIC fixtures found during foundation self-review."""
from dataclasses import asdict, replace
from decimal import localcontext
from fractions import Fraction
import unittest
from fixtures import q, REF
import test_material
import test_ledger
from sl_constraints.common import schema
from sl_constraints.common.types import ContractError, SourceRef, ConversionStep, SnapshotInfo
from sl_constraints.common.units import convert_quantity
from sl_constraints.common.provenance import SourceSnapshot
from sl_constraints.a35 import material as m, ledger as l


class ReviewGuards(unittest.TestCase):
    def setUp(self):
        self.material = test_material.MaterialTests('runTest')
        self.ledger = test_ledger.LedgerTests('runTest')
        self.ledger.setUp()

    def test_conversion_independent_of_decimal_context(self):
        with localcontext() as context:
            context.prec = 2
            result = convert_quantity(q(1, 'eV', 'ENERGY'), 'J')
        self.assertEqual(Fraction(result.value), Fraction('1.602176634e-19'))

    def test_empty_source_missing_version_not_ready(self):
        ref = SourceRef('', '', '', '')
        self.assertEqual(len(ref.readiness_reasons()), 4)

    def test_untrusted_source_hash_type_is_contract_error(self):
        for value in (True, 123, [], {}):
            with self.subTest(value=value), self.assertRaises(ContractError):
                SourceRef('test', '1', '2026-10-07T00:00:00Z', value)

    def test_conversion_receipt_is_validated(self):
        with self.assertRaises(ContractError):
            ConversionStep('kg', 'C', 1, 0)

    def test_untrusted_schema_wrong_hash_not_uncaught_typeerror(self):
        value = asdict(q(1, 'J', 'ENERGY'))
        value['value'] = '1'
        value['provenance'] = [dict(asdict(REF), source_hash=True)]
        value['conversions'] = []
        self.assertFalse(schema.validate_schema(value).valid_structure)

    def test_schema_missing_version_in_snapshot(self):
        self.assertFalse(schema.validate_schema({'snapshot_id': 'x'}, 'snapshot_info').valid_structure)

    def test_source_snapshot_nested_immutable(self):
        info = SnapshotInfo('s', '1.0.0', '2026-10-07', '2026-10-07T00:00:00Z')
        sources = []
        snap = SourceSnapshot(info, sources, 'a' * 64)
        sources.append('injected')
        self.assertEqual(snap.sources, ())

    def test_snapshot_bad_created_date_rejected(self):
        with self.assertRaises(ContractError):
            SnapshotInfo('s', '1.0.0', '2026-10-07', '2026-10-06T00:00:00Z')

    def test_material_wrong_temperature_convention(self):
        report = m.validate_material(self.material.package())
        self.assertIn('TEMPERATURE_CONVENTION_UNVERIFIED', report.gate('thermodynamics_ready').codes)

    def test_bare_coverage_labels_are_not_data(self):
        block = m.MaterialBlock('thermo', 'test_domain', (q(1, 'kg', 'MASS'),),
                                ('free_energy', 'pressure', 'internal_energy', 'chemical_potentials', 'cross_derivatives'), ())
        report = m.validate_material(self.material.package(thermodynamics=block))
        self.assertIn('VALUE_MISSING:free_energy', report.gate('thermodynamics_ready').codes)

    def test_thermodynamic_value_semantic_mismatch(self):
        block = m.MaterialBlock('thermo', 'test_domain', (q(1, 'kg', 'MASS', 'free_energy'),), (), ())
        with self.assertRaisesRegex(ContractError, 'UNIT_MISMATCH'):
            m.validate_material(self.material.package(thermodynamics=block))

    def test_research_state_cannot_ready_from_coverage_only(self):
        block = m.MaterialBlock('ionization', 'test_domain', (q(1, '1', 'DIMENSIONLESS'),),
                                ('resolved_populations', 'electron_bookkeeping', 'regime'), ())
        report = m.validate_material(self.material.package(ionization=block))
        self.assertIn('POPULATIONS_MISSING', report.gate('charge_state_ready').codes)

    def test_transport_three_species_symmetric_positive(self):
        species = self.material.species() + (m.Species('neutral', 'Y', q(1, 'kg', 'MASS'),
                    q(0, '1', 'DIMENSIONLESS'), q(1, 'm^-3', 'NUMBER_DENSITY')),)
        ids = ('ion', 'electron', 'neutral')
        c = self.material.matrix([[1, 0], [-2, -1], [0, 1]], ids, ('r1', 'r2'))
        mobility = self.material.matrix([[2, 1], [1, 2]], ('r1', 'r2'), ('r1', 'r2'),
                                       'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY')
        contract = self.material.transport(species_order=ids, reduced_order=('r1', 'r2'), projector=c, mobility=mobility)
        m.validate_transport(contract, species)
        nonsymmetric = self.material.matrix([[2, 1], [0, 2]], ('r1', 'r2'), ('r1', 'r2'),
                                            'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY')
        with self.assertRaisesRegex(ContractError, 'TRANSPORT_NOT_SYMMETRIC'):
            m.validate_transport(replace(contract, mobility=nonsymmetric), species)
        tiny = self.material.matrix([[1, 0], [0, '1e-13']], ('r1', 'r2'), ('r1', 'r2'),
                                    'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY')
        with self.assertRaisesRegex(ContractError, 'TRANSPORT_NOT_POSITIVE'):
            m.validate_transport(replace(contract, mobility=tiny), species)

    def test_flux_domain_mismatch(self):
        flux = replace(q(1, 'm^-2/s', 'NUMBER_FLUX'), domain_id='other')
        with self.assertRaisesRegex(ContractError, 'STATE_DOMAIN_MISMATCH'):
            m.validate_flux(self.material.species(), (flux, q(-2, 'm^-2/s', 'NUMBER_FLUX')))

    def test_multistage_shared_event_group_different_boundaries(self):
        a = self.ledger.transfer(event_id='event', double_count_group='packet')
        b = self.ledger.transfer('absorbed', 'transition_region', 'seed',
                                 event_id='event', double_count_group='packet')
        self.assertTrue(l.TransferLedger((a, b)).audit().valid)

    def test_ledger_exposes_semantic_balance(self):
        ledger = l.TransferLedger((self.ledger.transfer(kind='CURRENT', unit='A'),))
        balance = ledger.balance('transition_region', 'CHARGE')
        self.assertEqual((balance.value, balance.unit, balance.kind), (Fraction(2), 'A', 'CURRENT'))

    def test_ledger_zero_charge_valid(self):
        ledger = l.TransferLedger((self.ledger.transfer(value='0', kind='CHARGE', unit='C'),))
        self.assertTrue(ledger.audit().valid)

    def test_missing_ledger_provenance_not_ready(self):
        transfer = self.ledger.transfer(quantity=replace(q(1, 'kg', 'MASS'), provenance=()))
        self.assertIn('PROVENANCE_MISSING', l.TransferLedger((transfer,)).provenance_reasons)

    def test_open_transport_is_not_ready_not_exception(self):
        item = replace(q(1, 'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY'), value=None,
                       status='OPEN', open_reason='SYNTHETIC missing coefficient')
        mobility = m.TensorRecord(((item,),), (('r1',), ('r1',)), 'SYNTHETIC TEST')
        report = m.validate_material(self.material.package(transport=self.material.transport(mobility=mobility)))
        self.assertIn('OPEN_VALUE', report.gate('transport_ready').codes)

    def test_open_wrong_unit_remains_invalid(self):
        item = replace(q(1, 'kg', 'MASS', 'free_energy'), value=None,
                       status='OPEN', open_reason='SYNTHETIC missing')
        block = m.MaterialBlock('thermo', 'test_domain', (item,), (), ())
        with self.assertRaisesRegex(ContractError, 'UNIT_MISMATCH'):
            m.validate_material(self.material.package(thermodynamics=block))

    def test_invalid_material_top_level_type(self):
        with self.assertRaises(ContractError):
            self.material.package(state=True)

    def test_decimal_strings_match_wire_grammar(self):
        for text in ('1_000', ' 1 ', '\u0661'):
            with self.subTest(text=text), self.assertRaises(ContractError):
                q(text, 'J', 'ENERGY')


if __name__ == '__main__':
    unittest.main()
