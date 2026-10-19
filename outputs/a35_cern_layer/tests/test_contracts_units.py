"""Synthetic fixtures only; these values are not scientific material inputs."""
import copy
import importlib
import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

try:
    t = importlib.import_module('sl_constraints.common.types')
    u = importlib.import_module('sl_constraints.common.units')
    schema = importlib.import_module('sl_constraints.common.schema')
except ModuleNotFoundError:
    t = u = schema = None


class ContractsUnitsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(t, 'P01 foundation modules are not implemented')

    def quantity(self, value='1', unit='J', kind='ENERGY', **kw):
        return t.QuantityRecord('test_q', value, unit, kind,
                                'SYNTHETIC TEST quantity', 'test_domain', **kw)

    def test_explicit_energy_conversion(self):
        out = u.convert_quantity(self.quantity('1000', 'GeV'), 'TeV')
        self.assertEqual(out.value, Decimal('1'))
        self.assertEqual(out.conversions[-1].from_unit, 'GeV')
        self.assertEqual(out.conversions[-1].to_unit, 'TeV')

    def test_ev_joule_exact(self):
        self.assertEqual(u.convert_quantity(self.quantity('1', 'eV'), 'J').value,
                         Decimal('1.602176634e-19'))

    def test_density_conversion(self):
        out = u.convert_quantity(self.quantity('12', 'g/cm^3', 'MASS_DENSITY'), 'kg/m^3')
        self.assertEqual(out.value, Decimal('12000'))

    def test_dimension_mismatch(self):
        with self.assertRaisesRegex(t.ContractError, 'UNIT_MISMATCH'):
            u.convert_quantity(self.quantity(), 'kg')

    def test_number_density_not_mass_density(self):
        with self.assertRaisesRegex(t.ContractError, 'UNIT_MISMATCH'):
            self.quantity('1', 'kg/m^3', 'NUMBER_DENSITY')

    def test_unknown_unit(self):
        with self.assertRaisesRegex(t.ContractError, 'UNKNOWN_UNIT'):
            self.quantity('1', 'banana')

    def test_float_and_nonfinite_rejected(self):
        for value in (1.1, True, 'NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value), self.assertRaises(t.ContractError):
                self.quantity(value)

    def test_temperature_and_density_positive(self):
        for value, unit, kind in (('-1', 'K', 'TEMPERATURE'),
                                  ('-1', 'm^-3', 'NUMBER_DENSITY')):
            with self.subTest(kind=kind), self.assertRaises(t.ContractError):
                self.quantity(value, unit, kind)

    def test_zero_charge_valid(self):
        self.assertEqual(self.quantity('0', 'C', 'CHARGE').value, 0)

    def test_quantity_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.quantity().unit = 'kg'

    def test_open_quantity_needs_reason(self):
        with self.assertRaises(t.ContractError):
            self.quantity(None)
        q = self.quantity(None, status='OPEN', open_reason='test missing')
        self.assertIsNone(q.value)

    def test_missing_provenance_not_ready(self):
        self.assertIn('PROVENANCE_MISSING', self.quantity().readiness_reasons())

    def test_source_ref_hash_missing(self):
        ref = t.SourceRef('source', '1.0.0', '2026-10-07T00:00:00Z', '')
        self.assertIn('HASH_MISSING', ref.readiness_reasons())

    def test_source_ref_source_missing(self):
        ref = t.SourceRef('', '1.0.0', '2026-10-07T00:00:00Z', 'a' * 64)
        self.assertIn('SOURCE_MISSING', ref.readiness_reasons())

    def test_invalid_source_version(self):
        with self.assertRaises(t.ContractError):
            t.SourceRef('source', '../evil', '2026-10-07T00:00:00Z', 'a' * 64)

    def test_source_timestamp_requires_timezone(self):
        with self.assertRaises(t.ContractError):
            t.SourceRef('source', '1', '2026-10-07', 'a' * 64)

    def test_provenance_survives_conversion(self):
        ref = t.SourceRef('source', '1', '2026-10-07T00:00:00Z', 'a' * 64)
        q = self.quantity('1', 'eV', provenance=(ref,))
        self.assertEqual(u.convert_quantity(q, 'J').provenance, (ref,))

    def test_uncertainty_scales_squared(self):
        q = self.quantity('1', 'GeV', uncertainty=t.Uncertainty('VARIANCE', '4'))
        out = u.convert_quantity(q, 'TeV')
        self.assertEqual(out.uncertainty.value, Decimal('0.000004'))

    def test_nonterminating_conversion_fail_closed(self):
        with self.assertRaisesRegex(t.ContractError, 'ROUNDING_REQUIRED'):
            u.convert_quantity(self.quantity('1', 'J'), 'eV')

    def payload(self):
        return dict(schema_version='1.0.0', quantity_id='test_q', value='1',
                    unit='J', kind='ENERGY', definition='SYNTHETIC TEST',
                    domain_id='test_domain', provenance=[], status='KNOWN',
                    uncertainty={'kind': 'UNKNOWN', 'reason': 'test unknown'})

    def test_schema_valid_structure_but_not_ready(self):
        report = schema.validate_schema(self.payload(), 'quantity')
        self.assertTrue(report.valid_structure)
        self.assertEqual(report.status, t.Status.NOT_READY)

    def test_schema_missing_fields(self):
        p = self.payload()
        del p['unit']
        self.assertFalse(schema.validate_schema(p, 'quantity').valid_structure)

    def test_schema_unknown_version(self):
        p = self.payload()
        p['schema_version'] = '2.0.0'
        self.assertIn('SCHEMA_VERSION_UNSUPPORTED', schema.validate_schema(p, 'quantity').codes)

    def test_schema_unknown_property(self):
        p = self.payload()
        p['execute'] = '__import__("os")'
        self.assertIn('UNKNOWN_FIELD', schema.validate_schema(p, 'quantity').codes)

    def test_schema_does_not_mutate_payload(self):
        p = self.payload()
        before = copy.deepcopy(p)
        schema.validate_schema(p, 'quantity')
        self.assertEqual(before, p)

    def test_unknown_frame(self):
        with self.assertRaises(t.ContractError):
            t.require_frame('earth-ish')

    def test_snapshot_info_immutable_and_versioned(self):
        s = t.SnapshotInfo('test_snapshot', '1.0.0', '2026-10-07', '2026-10-07T12:00:00Z')
        with self.assertRaises(FrozenInstanceError):
            s.snapshot_id = 'other'
        with self.assertRaises(t.ContractError):
            t.SnapshotInfo('test_snapshot', '2.0.0', '2026-10-07', '2026-10-07T12:00:00Z')


if __name__ == '__main__':
    unittest.main()
