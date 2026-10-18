"""Synthetic schema and compatibility tests; no limit comparison engine."""
import copy
import importlib
import unittest
from collider_fixtures import constraint
from sl_constraints.common.types import ContractError

try:
    b = importlib.import_module('sl_constraints.collider.benchmark')
    c = importlib.import_module('sl_constraints.collider.contracts')
except ModuleNotFoundError:
    b = c = None


class ColliderSchemaTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(b, 'P05 missing')

    def test_all_schemas_valid(self):
        c.check_schemas()

    def test_constraint_required_fields(self):
        for key in constraint():
            record = constraint()
            del record[key]
            with self.subTest(key=key), self.assertRaises(ContractError):
                c.ConstraintRecord.from_dict(record)

    def test_null_not_missing(self):
        record = constraint()
        record['expected_value'] = None
        result = b.normalize_identity(record)
        self.assertIsNone(result['expected_value'])
        self.assertIn('expected_value', result['missing_fields'])

    def test_missing_observed_not_substituted(self):
        record = constraint()
        record['observed_value'] = None
        self.assertIsNone(b.normalize_identity(record)['observed_value'])

    def test_unknown_version(self):
        record = constraint()
        record['schema_version'] = '2.0.0'
        with self.assertRaises(ContractError):
            c.ConstraintRecord.from_dict(record)

    def test_unknown_field(self):
        record = constraint()
        record['execute'] = 'evil'
        with self.assertRaises(ContractError):
            c.ConstraintRecord.from_dict(record)

    def test_invalid_cl(self):
        for value in ('95', '0', '1', '-0.1', True, 0.95):
            record = constraint()
            record['confidence_level'] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                b.normalize_identity(record)

    def test_incompatible_unit(self):
        record = constraint()
        record['unit'] = 'fb'
        with self.assertRaisesRegex(ContractError, 'UNIT_MISMATCH'):
            b.normalize_identity(record)

    def test_unknown_never_gets_group(self):
        record = constraint()
        record['assumptions']['pdf'] = None
        self.assertIsNone(b.normalize_identity(record)['comparison_group'])

    def test_add_dimensions_split_groups(self):
        a, other = constraint(), constraint()
        other['n_extra_dimensions'] = 6
        self.assertNotEqual(b.normalize_identity(a)['comparison_group'], b.normalize_identity(other)['comparison_group'])

    def test_channels_never_merge(self):
        a, other = constraint(), constraint()
        other['channel_id'] = 'muon_jet'
        with self.assertRaisesRegex(ContractError, 'COMPARISON_REFUSED'):
            b.require_compatible(b.normalize_identity(a), b.normalize_identity(other))

    def test_forged_group_rejected(self):
        record = b.normalize_identity(constraint())
        record['n_extra_dimensions'] = 6
        with self.assertRaisesRegex(ContractError, 'FINGERPRINT_MISMATCH'):
            b.require_compatible(record, record)

    def test_null_groups_never_compatible(self):
        record = constraint()
        record['assumptions']['spin'] = None
        record = b.normalize_identity(record)
        with self.assertRaises(ContractError):
            b.require_compatible(record, record)

    def test_cl_and_observable_separate(self):
        a = b.normalize_identity(constraint())
        for key, value in [('confidence_level', '0.9'), ('observable_type', 'SIGMA')]:
            record = constraint()
            record[key] = value
            if key == 'observable_type':
                record.update(unit='fb', limit_type='UPPER_BOUND')
            with self.subTest(key=key), self.assertRaises(ContractError):
                b.require_compatible(a, b.normalize_identity(record))

    def test_sphaleron_mass_alias_rejected(self):
        record = constraint()
        record.update(object_class='SPHALERON', model_family='ELECTROWEAK', n_extra_dimensions=None)
        with self.assertRaisesRegex(ContractError, 'OBSERVABLE_MISMATCH'):
            b.normalize_identity(record)

    def test_canonical_object_order(self):
        a = constraint()
        other = dict(reversed(list(a.items())))
        self.assertEqual(b.normalize_identity(a)['comparison_group'], b.normalize_identity(other)['comparison_group'])

    def test_inputs_immutable(self):
        original = constraint()
        before = copy.deepcopy(original)
        obj = c.ConstraintRecord.from_dict(original)
        output = obj.to_dict()
        output['assumptions']['pdf'] = 'changed'
        self.assertEqual(original, before)
        self.assertEqual(obj.to_dict(), before)

    def test_sigma_times_br_not_sigma(self):
        a, other = constraint(), constraint()
        a.update(observable_type='SIGMA', unit='fb', limit_type='UPPER_BOUND')
        other.update(observable_type='SIGMA_TIMES_BR', unit='fb', limit_type='UPPER_BOUND')
        with self.assertRaises(ContractError):
            b.require_compatible(b.normalize_identity(a), b.normalize_identity(other))


if __name__ == '__main__':
    unittest.main()
