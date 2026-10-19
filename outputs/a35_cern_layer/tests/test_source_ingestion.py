"""Offline integrity tests with real files and synthetic source bytes."""
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import unittest
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from sl_constraints.common.types import ContractError
from collider_fixtures import constraint

try:
    s = importlib.import_module('sl_constraints.collider.sources')
except ModuleNotFoundError:
    s = None


def source_record(payload=b'SYNTHETIC', version='v1'):
    return dict(schema_version='1.0.0', source_id='synthetic_source', source_version=version,
                title='SYNTHETIC source', url='https://arxiv.org/html/synthetic',
                actual_url='https://arxiv.org/html/synthetic', retrieved_at='2026-10-18T00:00:00Z',
                sha256=hashlib.sha256(payload).hexdigest(), media_type='text/plain', byte_count=len(payload),
                collaboration='SYNTHETIC', analysis_id='SYNTHETIC', published_at='2026-01-01',
                publication_date_precision='DAY', arxiv_version=None, journal_ref=None, doi=None,
                inspire_id=None, hepdata_record_id=None, hepdata_version=None, table_ids=[],
                source_relationships=[], historical_evidence=None, purpose='TEST_FIXTURE')


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(s, 'P07 missing')
        self.parent = Path(__file__).resolve().parents[3] / 'work/test-tmp'
        self.root = self.parent / ('collider-' + uuid4().hex)
        self.store = s.EvidenceStore(self.root)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if self.root.resolve().parent == self.parent.resolve() and self.root.exists():
            shutil.rmtree(self.root)

    def fixture(self):
        ref = source_record(); self.store.ingest(ref, b'SYNTHETIC')
        extract = {'artifact_id': 'synthetic_extract', 'source_id': ref['source_id'],
                   'source_version': 'v1', 'source_hash': ref['sha256'], 'purpose': 'TEST_FIXTURE'}
        path, digest = self.store.artifact('extracted', extract['artifact_id'], extract)
        row = constraint(); row['provenance'][0]['sha256'] = ref['sha256']
        row['extraction_refs'][0]['sha256'] = digest
        self.store.artifact('normalized', row['constraint_id'], row)
        return ref, row

    def freeze(self):
        ref, row = self.fixture()
        return self.store.freeze('synthetic_snapshot', '2026-10-07', [ref], [row],
                                 [{'scope': 'HEPData', 'status': 'SOURCE_UNAVAILABLE', 'detail': 'Synthetic unavailable'}])

    def test_hash_mismatch(self):
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            self.store.ingest(source_record(), b'changed')

    def test_tampered_raw_read_rejected(self):
        ref = source_record(); self.store.ingest(ref, b'SYNTHETIC')
        self.store.safe_path('raw/' + ref['sha256']).write_bytes(b'changed')
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            self.store.read(ref)

    def test_source_version_change_does_not_overwrite(self):
        a, b = source_record(), source_record(b'NEW', 'v2')
        self.store.ingest(a, b'SYNTHETIC'); self.store.ingest(b, b'NEW')
        self.assertEqual(self.store.read(a), b'SYNTHETIC')
        self.assertEqual(self.store.read(b), b'NEW')
        with self.assertRaisesRegex(ContractError, 'IMMUTABLE_CONFLICT'):
            self.store.ingest(source_record(b'NEW'), b'NEW')

    def test_snapshot_immutable(self):
        manifest = self.freeze()
        before = self.store.safe_path('snapshots/synthetic_snapshot.json').read_bytes()
        with self.assertRaisesRegex(ContractError, 'SNAPSHOT_EXISTS'):
            self.freeze()
        self.assertEqual(self.store.safe_path('snapshots/synthetic_snapshot.json').read_bytes(), before)
        self.assertEqual(manifest['status'], 'FROZEN_PARTIAL')

    def test_tampered_normalized_snapshot_read_rejected(self):
        self.freeze()
        path = next(self.store.safe_path('normalized').rglob('*.json'))
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            self.store.read_snapshot('synthetic_snapshot')

    def test_missing_hepdata_blocks_complete(self):
        self.assertEqual(self.freeze()['status'], 'FROZEN_PARTIAL')

    def test_zero_records_never_success(self):
        with self.assertRaises(ContractError):
            self.store.freeze('empty', '2026-10-07', [], [], [])

    def test_wrong_source_version_rejected(self):
        ref, row = self.fixture(); row['source_version'] = 'v2'
        with self.assertRaises(ContractError):
            self.store.freeze('bad', '2026-10-07', [ref], [row], [])

    def test_post_cutoff_publication_rejected(self):
        ref = source_record(); ref['published_at'] = '2026-10-08'
        self.store.ingest(ref, b'SYNTHETIC')
        with self.assertRaisesRegex(ContractError, 'SOURCE_AFTER_CUTOFF'):
            self.store.freeze('bad', '2026-10-07', [ref], [constraint()], [])

    def test_duplicate_source_id_rejected(self):
        ref, row = self.fixture()
        with self.assertRaisesRegex(ContractError, 'DUPLICATE_SOURCE_ID'):
            self.store.freeze('bad', '2026-10-07', [ref, ref], [row], [])

    def test_concurrent_freeze_exactly_one_winner(self):
        ref, row = self.fixture()
        def attempt(_):
            try:
                self.store.freeze('race', '2026-10-07', [ref], [dict(row, snapshot_id='race')], [])
                return 'ok'
            except ContractError as exc:
                return exc.code
        # Publish matching record in advance; both writers operate on the same bytes.
        self.store.artifact('normalized', row['constraint_id'], dict(row, snapshot_id='race'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(results), ['SNAPSHOT_EXISTS', 'ok'])

    def test_download_url_guard(self):
        for url in ['http://arxiv.org/a', 'https://127.0.0.1/a', 'https://arxiv.org.evil/a',
                    'https://user:pass@arxiv.org/a', 'file:///C:/secret', 'https://arxiv.org:8443/a']:
            with self.subTest(url=url), self.assertRaises(ContractError):
                s.validate_url(url)


if __name__ == '__main__':
    unittest.main()
