"""Synthetic adapters and source-to-cell provenance; never research evidence."""
import copy
import hashlib
import importlib
import json
import unittest
from collider_fixtures import constraint
from sl_constraints.common.types import ContractError

try:
    e = importlib.import_module('sl_constraints.collider.extraction')
    n = importlib.import_module('sl_constraints.collider.normalize')
except ModuleNotFoundError:
    e = n = None


def source(payload):
    return {'source_id': 'synthetic_source', 'source_version': 'v1',
            'sha256': hashlib.sha256(payload).hexdigest(), 'purpose': 'TEST_FIXTURE',
            'hepdata_record_id': 'ins123', 'hepdata_version': '1', 'table_ids': ['Table 1']}


def table():
    return {'independent_variables': [{'header': {'name': 'M', 'units': 'TeV'},
                                      'values': [{'value': '8'}]}],
            'dependent_variables': [{'header': {'name': 'Observed', 'units': 'TeV'},
                                     'qualifiers': [{'name': 'BENCHMARK', 'value': 'synthetic_add2'}],
                                     'values': [{'value': '8.6', 'errors': [{'label': 'exp', 'asymerror': {'minus': '-0.1', 'plus': '0.2'}}]}]}]}


def binding():
    return {'record_id': 'ins123', 'version': '1', 'table_id': 'Table 1',
            'benchmark_id': 'synthetic_add2', 'channel_id': 'electron_jet',
            'observable_type': 'MASS_THRESHOLD', 'unit': 'TeV',
            'dependent_name': 'Observed', 'qualifiers': {'BENCHMARK': 'synthetic_add2'},
            'limit_role': 'OBSERVED', 'axis_parameters': {'M': {'name': 'threshold', 'unit': 'TeV'}}}


class NormalizeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(e, 'P06 missing')

    def extract(self, data=None, selected=None):
        raw = json.dumps(data or table()).encode()
        return e.extract_hepdata(raw, source(raw), selected or binding(),
                                 {'record_id': 'ins123', 'version': '1', 'table_ids': ['Table 1']})

    def test_valid_table_retains_qualifiers_errors_axes(self):
        record = self.extract()
        self.assertEqual(record['table'], table())
        self.assertEqual(record['cells'][0]['parsed_value'], '8.6')
        self.assertEqual(record['cells'][0]['original_cell_text'], '8.6')

    def test_missing_table_is_error(self):
        bind = binding(); bind['table_id'] = 'absent'
        with self.assertRaisesRegex(ContractError, 'TABLE_NOT_FOUND'):
            self.extract(selected=bind)

    def test_wrong_version_is_error(self):
        bind = binding(); bind['version'] = '2'
        with self.assertRaisesRegex(ContractError, 'SOURCE_CHANGED'):
            self.extract(selected=bind)

    def test_wrong_units(self):
        data = table(); data['dependent_variables'][0]['header']['units'] = 'fb'
        with self.assertRaisesRegex(ContractError, 'UNIT_MISMATCH'):
            self.extract(data)

    def test_missing_qualifier(self):
        data = table(); data['dependent_variables'][0]['qualifiers'] = []
        with self.assertRaisesRegex(ContractError, 'BENCHMARK_MISMATCH'):
            self.extract(data)

    def test_empty_values_not_success(self):
        data = table(); data['dependent_variables'][0]['values'] = []
        with self.assertRaisesRegex(ContractError, 'PARSE_ERROR'):
            self.extract(data)

    def test_censored_not_coerced(self):
        data = table(); data['dependent_variables'][0]['values'][0]['value'] = '<8.6'
        record = self.extract(data)
        self.assertIsNone(record['cells'][0]['parsed_value'])
        self.assertEqual(record['cells'][0]['interpretation_status'], 'CENSORED')

    def test_duplicate_json_keys_rejected(self):
        raw = b'{"a":1,"a":2}'
        with self.assertRaisesRegex(ContractError, 'PARSE_ERROR'):
            e.extract_hepdata(raw, source(raw), binding(), {})

    def test_raw_hash_checked(self):
        raw = json.dumps(table()).encode(); ref = source(raw); ref['sha256'] = '0' * 64
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            e.extract_hepdata(raw, ref, binding(), {})

    def test_paragraph_exact_bytes_retained(self):
        self.assertTrue(hasattr(e, 'extract_paragraph'), 'paragraph adapter missing')
        raw = b'<p id="reference">Observed <b>0.0034</b>; expected 0.0035.</p>'
        record = e.extract_paragraph(raw, source(raw), 'reference')
        self.assertEqual(record['original_html'], raw.decode())
        self.assertEqual(record['byte_start'], 0)
        self.assertEqual(record['byte_end'], len(raw))
        with self.assertRaises(ContractError):
            e.extract_paragraph(raw, source(raw), 'missing')

    def test_html_table_identity_and_cell_locators(self):
        raw = b'<figure id="S6.T2"><table><tr><td>7.2</td><td>7.1</td></tr></table></figure>'
        rows = e.extract_html_table(raw, source(raw), 'S6.T2')
        self.assertEqual(rows['rows'], [['7.2', '7.1']])
        self.assertEqual(rows['source_hash'], hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ContractError, 'TABLE_NOT_FOUND'):
            e.extract_html_table(raw, source(raw), 'S6.T3')

    def test_crosscheck_exact_rounding_missing_and_mismatch(self):
        args = {'paper_unit': 'TeV', 'table_unit': 'TeV'}
        self.assertEqual(n.crosscheck('8.6', '8.6', **args), 'MATCH')
        self.assertEqual(n.crosscheck('8.6', '8.61', **args), 'MISMATCH')
        self.assertEqual(n.crosscheck('8.6', '8.61', rounding_places=1, rounding_evidence='Table caption', **args), 'ROUNDING_MATCH')
        self.assertEqual(n.crosscheck(None, '8.6', **args), 'SOURCE_MISSING')
        self.assertEqual(n.crosscheck('8.6', '8.6', paper_unit='fb', table_unit='TeV'), 'NOT_COMPARABLE')

    def test_conversion_exact(self):
        for value, unit, target, expected in [('1000', 'GeV', 'TeV', '1'), ('1', 'pb', 'fb', '1000'), ('1000', 'pb^-1', 'fb^-1', '1')]:
            self.assertEqual(n.convert(value, unit, target), expected)

    def test_normalize_preserves_missing_and_lineage(self):
        result = n.normalize_cell(constraint(), self.extract(), 0)
        self.assertEqual(result['observed_value'], '8.6')
        self.assertIsNone(result['expected_value'])
        self.assertTrue(result['extraction_refs'][0]['sha256'])

    def test_binding_not_swappable(self):
        template = constraint(); template['channel_id'] = 'muon_jet'
        with self.assertRaisesRegex(ContractError, 'BENCHMARK_MISMATCH'):
            n.normalize_cell(template, self.extract(), 0)

    def test_atlas_channel_rows_preserved(self):
        pairs = [('RS', 1, '7.2', '7.1', '6.6', '6.6'), ('ADD', 2, '8.6', '8.5', '8.2', '8.1'),
                 ('ADD', 4, '9.1', '9.1', '8.7', '8.7'), ('ADD', 6, '9.4', '9.4', '9.0', '9.0')]
        outputs = []
        for family, dim, eo, ee, mo, me in pairs:
            for channel, observed, expected in [('electron_jet', eo, ee), ('muon_jet', mo, me)]:
                template = constraint()
                template.update(model_family=family, n_extra_dimensions=dim, channel_id=channel,
                                benchmark_id=f'{family}{dim}', constraint_id=f'{family}{dim}_{channel}')
                outputs.append(n.normalize_reviewed(template, observed, expected))
        self.assertEqual(len({r['constraint_id'] for r in outputs}), 8)
        self.assertEqual([(r['observed_value'], r['expected_value']) for r in outputs],
                         [('7.2','7.1'), ('6.6','6.6'), ('8.6','8.5'), ('8.2','8.1'),
                          ('9.1','9.1'), ('8.7','8.7'), ('9.4','9.4'), ('9.0','9.0')])


if __name__ == '__main__':
    unittest.main()
