"""SYNTHETIC accounting fixtures only; no capture or absorption physics."""
from dataclasses import replace
from decimal import localcontext
from fractions import Fraction
import importlib
import unittest
from fixtures import q, REF
from sl_constraints.common.types import ContractError, Status
from sl_constraints.a35.material import Species

try:
    l = importlib.import_module('sl_constraints.a35.ledger')
except ModuleNotFoundError:
    l = None


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(l, 'P04 not implemented')
        self.op = l.OperatorRef('test_operator', '1', (REF,), 'SYNTHETIC TEST operator')

    def transfer(self, channel='outer_in', source='outer_material', target='transition_region',
                 value='2', kind='MASS', unit='kg', **kwargs):
        args = dict(channel_id=channel, event_id=channel, quantity=q(value, unit, kind),
                    source=source, target=target, sign=1, frame='BARYCENTRIC',
                    operator=self.op, double_count_group=channel)
        if kind in ('ENERGY', 'POWER'):
            args['energy_convention'] = 'THERMAL_ONLY_EXCLUDES_REST_MASS'
        args.update(kwargs)
        return l.Transfer(**args)

    def test_internal_mass_charge_energy_pass(self):
        for kind, unit in (('MASS', 'kg'), ('CHARGE', 'C'), ('ENERGY', 'J')):
            with self.subTest(kind=kind):
                ledger = l.TransferLedger((self.transfer(kind=kind, unit=unit),))
                self.assertTrue(ledger.audit().valid)
                self.assertEqual(ledger.change('transition_region', kind), Fraction(2))
                self.assertEqual(ledger.change('seed', kind), Fraction(0))

    def test_multistage_storage_not_absorption(self):
        outer = self.transfer(value='5')
        inner = self.transfer('seed_in', 'transition_region', 'seed', value='2')
        ledger = l.TransferLedger((outer, inner))
        self.assertEqual(ledger.change('transition_region', 'MASS'), 3)
        self.assertEqual(ledger.change('seed', 'MASS'), 2)
        self.assertEqual(ledger.change('outer_material', 'MASS'), -5)
        self.assertTrue(ledger.audit().valid)

    def test_rate_storage_derivative(self):
        ledger = l.TransferLedger((self.transfer(kind='MASS_RATE', unit='kg/s'),))
        self.assertEqual(ledger.change('transition_region', 'MASS'), 2)
        self.assertEqual(ledger.mode, 'RATE')

    def test_amounts_rates_cannot_mix(self):
        with self.assertRaisesRegex(ContractError, 'AMOUNT_RATE_MISMATCH'):
            l.TransferLedger((self.transfer(), self.transfer('other', kind='MASS_RATE', unit='kg/s')))

    def test_explicit_external_source(self):
        transfer = self.transfer(source='external', external=True)
        ledger = l.TransferLedger((transfer,))
        self.assertEqual(ledger.audit().external_contribution('MASS'), 2)
        self.assertTrue(ledger.audit().valid)

    def test_implicit_external_source_rejected(self):
        with self.assertRaisesRegex(ContractError, 'EXTERNAL_MARKER_REQUIRED'):
            self.transfer(source='external')

    def test_external_marker_cannot_hide_internal(self):
        with self.assertRaisesRegex(ContractError, 'EXTERNAL_MARKER_REQUIRED'):
            self.transfer(external=True)

    def test_missing_counterentry(self):
        ledger = l.TransferLedger((self.transfer(),))
        report = ledger.audit(ledger.postings[:-1])
        self.assertFalse(report.valid)
        self.assertIn('COUNTERENTRY_MISMATCH', report.codes)

    def test_corrupt_mass_charge_energy_fail(self):
        for kind, unit in (('MASS', 'kg'), ('CHARGE', 'C'), ('ENERGY', 'J')):
            with self.subTest(kind=kind):
                ledger = l.TransferLedger((self.transfer(kind=kind, unit=unit),))
                bad = (ledger.postings[0], replace(ledger.postings[1], amount=Fraction(3)))
                report = ledger.audit(bad)
                self.assertFalse(report.valid)
                self.assertIn('CONSERVATION_FAIL:' + kind, report.codes)

    def test_balanced_but_wrong_postings_fail(self):
        ledger = l.TransferLedger((self.transfer(),))
        bad = tuple(replace(p, amount=p.amount * 2) for p in ledger.postings)
        self.assertFalse(ledger.audit(bad).valid)

    def test_duplicate_transfer(self):
        transfer = self.transfer()
        with self.assertRaisesRegex(ContractError, 'DUPLICATE_CHANNEL'):
            l.TransferLedger((transfer, transfer))

    def test_double_count_group(self):
        a = self.transfer(kind='CHARGE', unit='C', double_count_group='same', event_id='event')
        b = replace(a, channel_id='I_plasma')
        with self.assertRaisesRegex(ContractError, 'DOUBLE_COUNT'):
            l.TransferLedger((a, b))

    def test_renamed_group_cannot_bypass_same_event(self):
        a = self.transfer(kind='CHARGE', unit='C', double_count_group='same', event_id='event')
        b = replace(a, channel_id='I_plasma', double_count_group='renamed')
        with self.assertRaisesRegex(ContractError, 'DOUBLE_COUNT'):
            l.TransferLedger((a, b))

    def test_species_charge_already_booked(self):
        species = Species('X', 'X', q(2, 'kg', 'MASS'), q(1, '1', 'DIMENSIONLESS'),
                          q(1, 'm^-3', 'NUMBER_DENSITY'))
        transfers = l.species_transfer(species, q(3, 'particle', 'COUNT'),
                                      channel_id='species_absorption', event_id='event',
                                      source='transition_region', target='seed',
                                      operator=self.op, double_count_group='absorption', frame='BARYCENTRIC')
        ledger = l.TransferLedger(transfers)
        self.assertEqual(ledger.change('seed', 'MASS'), 6)
        self.assertEqual(ledger.change('seed', 'CHARGE'), Fraction('4.806529902e-19'))
        extra = self.transfer('I_plasma', 'transition_region', 'seed', kind='CHARGE', unit='C',
                              event_id='event', double_count_group='absorption')
        with self.assertRaisesRegex(ContractError, 'DOUBLE_COUNT'):
            l.TransferLedger(transfers + (extra,))

    def test_unknown_reservoir(self):
        with self.assertRaisesRegex(ContractError, 'UNKNOWN_RESERVOIR'):
            self.transfer(target='magic')

    def test_same_reservoir(self):
        with self.assertRaisesRegex(ContractError, 'INVALID_TRANSFER'):
            self.transfer(target='outer_material')

    def test_incompatible_unit(self):
        with self.assertRaisesRegex(ContractError, 'LEDGER_QUANTITY_UNSUPPORTED'):
            self.transfer(kind='TEMPERATURE', unit='K')

    def test_explicit_si_required(self):
        with self.assertRaisesRegex(ContractError, 'UNIT_MISMATCH'):
            self.transfer(unit='g')

    def test_energy_convention_required(self):
        with self.assertRaisesRegex(ContractError, 'ENERGY_CONVENTION_REQUIRED'):
            self.transfer(kind='ENERGY', unit='J', energy_convention='')

    def test_energy_conventions_cannot_mix(self):
        a = self.transfer(kind='ENERGY', unit='J')
        b = self.transfer('other', kind='ENERGY', unit='J', energy_convention='REST_MASS_ONLY')
        with self.assertRaisesRegex(ContractError, 'ENERGY_CONVENTION_MISMATCH'):
            l.TransferLedger((a, b))

    def test_sign_negative_reverses_bookings(self):
        ledger = l.TransferLedger((self.transfer(sign=-1),))
        self.assertEqual(ledger.change('transition_region', 'MASS'), -2)
        with self.assertRaises(ContractError):
            self.transfer(sign=True)

    def test_no_implicit_frame_change(self):
        with self.assertRaisesRegex(ContractError, 'FRAME_MISMATCH'):
            l.TransferLedger((self.transfer(), self.transfer('other', frame='LAB')))

    def test_exact_independent_of_decimal_context(self):
        a = self.transfer(value='0.12345678901234567890123456789')
        with localcontext() as context:
            context.prec = 3
            ledger = l.TransferLedger((a,))
            self.assertEqual(ledger.change('transition_region', 'MASS'), Fraction(a.quantity.value))
            self.assertTrue(ledger.audit().valid)

    def test_fixture_provenance_not_scientifically_ready(self):
        ledger = l.TransferLedger((self.transfer(),))
        self.assertEqual(ledger.scientific_status, Status.NOT_READY)

    def test_species_pair_cannot_be_split_or_charge_changed(self):
        species = Species('X', 'X', q(2, 'kg', 'MASS'), q(1, '1', 'DIMENSIONLESS'),
                          q(1, 'm^-3', 'NUMBER_DENSITY'))
        transfers = l.species_transfer(species, q(3, 'particle', 'COUNT'),
                                      channel_id='species_absorption', event_id='event',
                                      source='transition_region', target='seed',
                                      operator=self.op, double_count_group='absorption', frame='BARYCENTRIC')
        with self.assertRaisesRegex(ContractError, 'SPECIES_COUNTERCHANNEL_MISSING'):
            l.TransferLedger(transfers[:1])
        with self.assertRaisesRegex(ContractError, 'INCONSISTENT_SPECIES_TRANSFER'):
            replace(transfers[1], quantity=q(1, 'C', 'CHARGE'))


if __name__ == '__main__':
    unittest.main()
