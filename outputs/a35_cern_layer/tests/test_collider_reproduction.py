"""Offline regression against locally hashed original publication bytes."""
import importlib
import json
from pathlib import Path
import unittest
from sl_constraints.common.types import ContractError

try:
    r = importlib.import_module('sl_constraints.collider.reproduce')
except ModuleNotFoundError:
    r = None


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(r, 'reviewed analysis adapter missing')
        self.root = Path(__file__).resolve().parents[1] / 'data/cern_lhc_snapshot_2026_10_07'

    def input(self, name):
        path = next((self.root / 'catalogs' / (name + '_acquisition')).glob('*.json'))
        source = json.loads(path.read_bytes())['source']
        return (self.root / 'raw' / source['sha256']).read_bytes(), source

    def test_eight_atlas_rows_exact(self):
        extractions, rows = r.atlas_constraints(*self.input('atlas_paper_v2'))
        self.assertEqual(len(rows), 8)
        self.assertEqual([(v['observed_value'], v['expected_value']) for v in rows],
                         [('7.2','7.1'), ('6.6','6.6'), ('8.6','8.5'), ('8.2','8.1'),
                          ('9.1','9.1'), ('8.7','8.7'), ('9.4','9.4'), ('9.0','9.0')])
        self.assertEqual({v['channel_id'] for v in rows}, {'electron_jet', 'muon_jet'})
        self.assertTrue(all(v['source_id'] == 'atlas_paper_v2' for v in rows))
        self.assertTrue(extractions)

    def test_atlas_source_mutation_rejected(self):
        raw, source = self.input('atlas_paper_v2')
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            r.atlas_constraints(raw + b'X', source)

    def test_cms_benchmarks_split_and_nominal_values(self):
        extractions, rows = r.cms_constraints(*self.input('cms_paper_v2'))
        bh = [v for v in rows if v['object_class'] == 'SEMICLASSICAL_BLACK_HOLE']
        sb = [v for v in rows if v['object_class'] == 'STRING_BALL']
        sph = [v for v in rows if v['object_class'] == 'SPHALERON' and v['observable_type'] == 'DIMENSIONLESS_PARAMETER']
        self.assertEqual(len(bh), 216)
        self.assertEqual(len(sb), 21)
        self.assertEqual(len(sph), 15)
        self.assertEqual(len({v['constraint_id'] for v in rows}), len(rows))
        concrete = [v for v in bh if v['observed_value'] is not None]
        self.assertEqual(sorted(v['observed_value'] for v in concrete), ['10.4', '11.0'])
        concrete = [v for v in sph if v['observed_value'] is not None]
        self.assertEqual([(v['observed_value'], v['expected_value']) for v in concrete], [('0.0034', '0.0035')])
        self.assertTrue(all(v['observed_value'] is None and v['expected_value'] is None for v in sb))

    def test_cms_fraction_not_prefactor_alias(self):
        _, rows = r.cms_constraints(*self.input('cms_paper_v2'))
        claims = [v for v in rows if v['observable_type'] == 'SPHALERON_FRACTION']
        self.assertEqual(len(claims), 1)
        self.assertIsNone(claims[0]['expected_value'])
        self.assertIsNone(claims[0]['comparison_group'])
        self.assertEqual(claims[0]['observed_value'], '0.0034')


if __name__ == '__main__':
    unittest.main()
