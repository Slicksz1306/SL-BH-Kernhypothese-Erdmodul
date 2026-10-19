"""Independent-review findings: each regression guards a demonstrated bad input."""
import base64
from copy import deepcopy
from email.message import Message
from http.client import IncompleteRead
import io
import json
import importlib
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from collider_fixtures import constraint
from test_normalize import source, table, binding
import test_source_ingestion as source_tests
from test_source_ingestion import source_record
from sl_constraints.collider import extraction as e, normalize as n
from sl_constraints.collider.sources import acquire_public
from sl_constraints.common.types import ContractError


class ReviewNormalizationTests(unittest.TestCase):
    def test_required_scope_independent_of_present_records(self):
        module = importlib.import_module('sl_constraints.collider.coverage')
        required = module.declared_scope()
        self.assertEqual(len(required), 262)
        self.assertEqual(len({tuple(row.values()) for row in required}), 262)
        result = n.audit_coverage([], required)
        self.assertEqual(len(result['gaps']), 262)
        self.assertIn('EXOT-2024-32/ATLAS_RS_n1/electron_jet/MASS_THRESHOLD',
                      [gap['scope'] for gap in result['gaps']])

    def extract(self, data=None, bind=None, ref_mutation=None):
        raw = json.dumps(data or table()).encode()
        ref = source(raw)
        if ref_mutation:
            ref.update(ref_mutation)
        return e.extract_hepdata(raw, ref, bind or binding(),
                                 {'record_id': 'ins123', 'version': '1', 'table_ids': ['Table 1']})

    def test_expected_never_written_as_observed(self):
        data = table(); data['dependent_variables'][0]['header']['name'] = 'Expected'
        bind = binding(); bind.update(dependent_name='Expected', limit_role='EXPECTED')
        result = n.normalize_cell(constraint(), self.extract(data, bind), 0)
        self.assertIsNone(result['observed_value'])
        self.assertEqual(result['expected_value'], '8.6')

    def test_unknown_limit_role_refused(self):
        bind = binding(); bind['limit_role'] = 'UNKNOWN'
        with self.assertRaises(ContractError):
            self.extract(bind=bind)

    def test_hepdata_identity_bound_to_source(self):
        for change in [{'hepdata_record_id': 'insOTHER'}, {'hepdata_version': '2'}, {'table_ids': ['Other']},
                       {'hepdata_record_id': None}, {'hepdata_version': None}]:
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.extract(ref_mutation=change)

    def test_unknown_identities_do_not_match_each_other(self):
        raw = json.dumps(table()).encode(); bind = binding(); bind.update(record_id=None, version=None)
        with self.assertRaises(ContractError):
            e.extract_hepdata(raw, source(raw), bind, {'record_id': None, 'version': None, 'table_ids': ['Table 1']})

    def test_multi_point_normalization_refused_until_supported(self):
        data = table()
        data['independent_variables'][0]['values'].append({'value': '9'})
        data['dependent_variables'][0]['values'].append({'value': '9.1'})
        with self.assertRaisesRegex(ContractError, 'MULTIPOINT_UNSUPPORTED'):
            n.normalize_cell(constraint(), self.extract(data), 0)

    def test_single_point_coordinate_bound(self):
        result = n.normalize_cell(constraint(), self.extract(), 0)
        self.assertEqual(result['model_parameters'][0]['value'], '8')
        data = table(); data['independent_variables'][0]['values'][0]['value'] = '9'
        other = n.normalize_cell(constraint(), self.extract(data), 0)
        self.assertNotEqual(result['constraint_id'], other['constraint_id'])

    def test_missing_axis_binding_refused(self):
        bind = binding(); bind['axis_parameters'] = {}
        with self.assertRaisesRegex(ContractError, 'AXIS_BINDING_REQUIRED'):
            n.normalize_cell(constraint(), self.extract(bind=bind), 0)

    def test_invalid_conversion_inputs_refused(self):
        for value, unit, target in [(True, 'pb', 'fb'), (False, 'pb', 'fb'), (1.5, 'pb', 'fb'),
                                    ('NaN', 'fb', 'fb'), (True, 'fb', 'fb'), ('1', 'bananas', 'bananas')]:
            with self.subTest(value=value, unit=unit), self.assertRaises(ContractError):
                n.convert(value, unit, target)

    def test_coverage_revalidates_metadata_and_acceptance(self):
        row = constraint()
        required = [{k: row[k] for k in ('analysis_id', 'benchmark_id', 'channel_id', 'observable_type')}]
        for field, value in [('purpose', 'TEST_FIXTURE'), ('validation_status', 'REJECTED'), ('pdf', None)]:
            item = deepcopy(row); item.update(purpose='RESEARCH', validation_status='ACCEPTED')
            if field == 'pdf': item['assumptions']['pdf'] = value
            else: item[field] = value
            self.assertEqual(n.audit_coverage([item], required)['status'], 'PARTIAL')

    def test_incomplete_http_body_keeps_status_and_partial_bytes(self):
        class Broken(io.BytesIO):
            def read(self, *args):
                raise IncompleteRead(b'partial challenge', 100)
        error = HTTPError('https://www.hepdata.net/record/123', 403, 'Forbidden', Message(), Broken())
        with patch('urllib.request.OpenerDirector.open', side_effect=error):
            raw, receipt = acquire_public(error.url)
        self.assertIsNone(raw)
        self.assertEqual(receipt['http_status'], 403)
        self.assertTrue(receipt['error_response_truncated'])
        self.assertEqual(base64.b64decode(receipt['error_response_base64']), b'partial challenge')


class ReviewFreezeTests(unittest.TestCase):
    # Reuse setup/cleanup only: do not duplicate the original test cases in discovery.
    setUp = source_tests.SourceTests.setUp
    cleanup = source_tests.SourceTests.cleanup
    def complete_fixture(self):
        ref = source_record(); ref.update(purpose='RESEARCH')
        ref['historical_evidence'] = {'source_id': ref['source_id'], 'source_version': ref['source_version'],
                                      'sha256': ref['sha256'], 'locator': 'synthetic date evidence'}
        self.store.ingest(ref, b'SYNTHETIC')
        extracted = dict(artifact_id='synthetic_extract', source_id=ref['source_id'],
                         source_version='v1', source_hash=ref['sha256'], purpose='RESEARCH')
        _, digest = self.store.artifact('extracted', 'synthetic_extract', extracted)
        row = constraint(); row.update(purpose='RESEARCH', validation_status='ACCEPTED')
        row['provenance'][0]['sha256'] = ref['sha256']; row['extraction_refs'][0]['sha256'] = digest
        self.store.artifact('normalized', row['constraint_id'], row)
        return ref, row

    def test_partial_coverage_and_receipt_block_complete(self):
        ref, row = self.complete_fixture()
        self.store.artifact('coverage', 'required', {'status': 'PARTIAL'})
        _, digest = self.store.artifact('receipts', 'unavailable', {'status': 'SOURCE_UNAVAILABLE'})
        result = self.store.freeze('synthetic_snapshot', '2026-10-07', [ref], [row], [],
                                   unavailable_receipts=[{'artifact_id': 'unavailable', 'sha256': digest}])
        self.assertEqual(result['status'], 'FROZEN_PARTIAL')

    def test_stored_failure_cannot_be_hidden_by_omitting_receipt_argument(self):
        ref, row = self.complete_fixture()
        self.store.artifact('receipts', 'unavailable', {'status': 'SOURCE_UNAVAILABLE'})
        required = [{k: row[k] for k in ('analysis_id', 'benchmark_id', 'channel_id', 'observable_type')}]
        result = self.store.freeze('synthetic_snapshot', '2026-10-07', [ref], [row], [], required_scope=required)
        self.assertEqual(result['status'], 'FROZEN_PARTIAL')

    def test_verified_complete_synthetic_scope_can_pass(self):
        ref, row = self.complete_fixture()
        required = [{k: row[k] for k in ('analysis_id', 'benchmark_id', 'channel_id', 'observable_type')}]
        result = self.store.freeze('synthetic_snapshot', '2026-10-07', [ref], [row], [], required_scope=required)
        self.assertEqual(result['status'], 'FROZEN_COMPLETE')

    def test_undeclared_scope_never_complete(self):
        ref, row = self.complete_fixture()
        result = self.store.freeze('synthetic_snapshot', '2026-10-07', [ref], [row], [])
        self.assertEqual(result['status'], 'FROZEN_PARTIAL')

    def test_missing_receipt_never_accepted(self):
        ref, row = self.complete_fixture()
        with self.assertRaisesRegex(ContractError, 'RECEIPT_MISSING'):
            self.store.freeze('synthetic_snapshot', '2026-10-07', [ref], [row], [],
                              unavailable_receipts=[{'artifact_id': 'absent', 'sha256': 'a' * 64}])

    def test_extraction_must_be_parent_of_constraint(self):
        ref, row = self.complete_fixture()
        other = source_record(b'OTHER'); other['source_id'] = 'other_source'
        self.store.ingest(other, b'OTHER')
        extract = dict(artifact_id='other_extract', source_id='other_source', source_version='v1',
                       source_hash=other['sha256'], purpose='TEST_FIXTURE')
        _, digest = self.store.artifact('extracted', 'other_extract', extract)
        row['extraction_refs'] = [{'artifact_id': 'other_extract', 'sha256': digest}]
        self.store.artifact('normalized', row['constraint_id'], row)
        with self.assertRaisesRegex(ContractError, 'PROVENANCE_MISMATCH'):
            self.store.freeze('synthetic_snapshot', '2026-10-07', [ref, other], [row], [])

    def relationship_fixture(self, relation_id, relation_version, relation_hash, snapshot_id):
        parent = source_record(b'PARENT'); parent['source_id'] = 'parent_source'
        parent['purpose'] = 'RESEARCH'
        parent['historical_evidence'] = {'source_id': parent['source_id'], 'source_version': parent['source_version'],
                                         'sha256': parent['sha256'], 'locator': 'synthetic dated parent'}
        self.store.ingest(parent, b'PARENT')
        ref = source_record(version=snapshot_id); ref['source_id'] = 'child_' + snapshot_id; ref['purpose'] = 'RESEARCH'
        ref['historical_evidence'] = {'source_id': ref['source_id'], 'source_version': ref['source_version'],
                                      'sha256': ref['sha256'], 'locator': 'synthetic dated child'}
        ref['source_relationships'] = [{'source_id': relation_id, 'source_version': relation_version,
                                        'sha256': relation_hash, 'locator': 'synthetic relationship'}]
        self.store.ingest(ref, b'SYNTHETIC')
        extracted = {'artifact_id': 'extract_' + snapshot_id, 'source_id': ref['source_id'],
                     'source_version': ref['source_version'], 'source_hash': ref['sha256'], 'purpose': 'RESEARCH'}
        _, digest = self.store.artifact('extracted', extracted['artifact_id'], extracted)
        row = constraint(); row.update(snapshot_id=snapshot_id, source_id=ref['source_id'],
                                        source_version=ref['source_version'], purpose='RESEARCH', validation_status='ACCEPTED')
        row['provenance'][0].update(source_id=ref['source_id'], source_version=ref['source_version'], sha256=ref['sha256'])
        row['extraction_refs'][0]['artifact_id'] = extracted['artifact_id']
        row['extraction_refs'][0]['sha256'] = digest
        self.store.artifact('normalized', row['constraint_id'], row)
        return parent, ref, row

    def test_source_relationship_must_resolve_exactly(self):
        parent = source_record(b'PARENT'); parent['source_id'] = 'parent_source'
        cases = [('missing_source', 'v1', parent['sha256']),
                 ('parent_source', 'wrong_version', parent['sha256']),
                 ('parent_source', 'v1', '0' * 64)]
        for index, (target_id, target_version, target_hash) in enumerate(cases):
            with self.subTest(target=(target_id, target_version, target_hash)):
                snapshot_id = f'relationship_{index}'
                parent, ref, row = self.relationship_fixture(target_id, target_version, target_hash, snapshot_id)
                with self.assertRaisesRegex(ContractError, 'PROVENANCE_MISMATCH'):
                    self.store.freeze(snapshot_id, '2026-10-07', [parent, ref], [row], [])

    def test_valid_source_relationship_is_accepted(self):
        parent = source_record(b'PARENT'); parent['source_id'] = 'parent_source'
        parent, ref, row = self.relationship_fixture(parent['source_id'], parent['source_version'], parent['sha256'], 'relationship_valid')
        manifest = self.store.freeze('relationship_valid', '2026-10-07', [parent, ref], [row],
                                     [{'scope': 'synthetic', 'status': 'INCOMPLETE', 'detail': 'fixture only'}])
        self.assertEqual(manifest['status'], 'FROZEN_PARTIAL')


if __name__ == '__main__':
    unittest.main()
