"""All source bytes are synthetic fixtures, never research inputs."""
import hashlib
import importlib
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import shutil
from uuid import uuid4
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from types import SimpleNamespace
import stat
from sl_constraints.common.types import ContractError, SnapshotInfo, SourceRef

try:
    p = importlib.import_module('sl_constraints.common.provenance')
except ModuleNotFoundError:
    p = None


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(p, 'P02 not implemented')
        # Python 3.12 Windows mkdtemp(mode=0700) excludes the restricted test
        # token. Inherit workspace ACLs instead; never change system temp ACLs.
        base = Path(__file__).resolve().parents[3] / 'work' / 'test-tmp'
        self.root = base / ('source-test-' + uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(self.cleanup_root, base)
        self.store = p.LocalSourceStore(self.root)
        self.raw = b'SYNTHETIC TEST SOURCE ONLY'

    def cleanup_root(self, base):
        if self.root.resolve().parent != base.resolve():
            raise RuntimeError('unsafe test cleanup')
        shutil.rmtree(self.root)

    def record(self, **kw):
        data = dict(ref=SourceRef('fixture', '1', '2026-10-07T00:00:00Z',
                                 hashlib.sha256(self.raw).hexdigest(), 'TEST_FIXTURE'),
                    title='Synthetic fixture', author='unit test', published='2026-10-07',
                    locator='test line 1', origin='local:test', access='TEST_ONLY',
                    media_type='text/plain', byte_count=len(self.raw))
        data.update(kw)
        return p.SourceRecord(**data)

    def test_roundtrip_verified_bytes(self):
        r = self.record()
        self.store.ingest_bytes(r, self.raw)
        self.assertEqual(self.store.read(r), self.raw)

    def test_idempotent_ingest(self):
        r = self.record()
        self.store.ingest_bytes(r, self.raw)
        self.store.ingest_bytes(r, self.raw)
        self.assertEqual(self.store.read(r), self.raw)

    def test_hash_mismatch(self):
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            self.store.ingest_bytes(self.record(), b'wrong')

    def test_size_mismatch(self):
        with self.assertRaisesRegex(ContractError, 'SIZE_MISMATCH'):
            self.store.ingest_bytes(self.record(byte_count=1), self.raw)

    def test_no_missing_source_hash_ingestion(self):
        with self.assertRaisesRegex(ContractError, 'PROVENANCE_MISSING'):
            self.store.ingest_bytes(self.record(ref=SourceRef('', '1', '', '')), self.raw)

    def test_identity_version_cannot_be_rebound(self):
        r = self.record()
        self.store.ingest_bytes(r, self.raw)
        new_raw = b'OTHER TEST'
        new = replace(r, ref=replace(r.ref, source_hash=hashlib.sha256(new_raw).hexdigest()),
                      byte_count=len(new_raw))
        with self.assertRaisesRegex(ContractError, 'IMMUTABLE_CONFLICT'):
            self.store.ingest_bytes(new, new_raw)

    def test_missing_source_is_not_available(self):
        with self.assertRaisesRegex(ContractError, 'SOURCE_UNAVAILABLE'):
            self.store.read(self.record())

    def test_traversal_not_opened(self):
        for path in ('../outside', '/outside', 'C:\\outside', 'dir/../../outside', 'x:stream'):
            with self.subTest(path=path), self.assertRaisesRegex(ContractError, 'PATH_OUTSIDE_ROOT'):
                self.store.safe_path(path)

    def test_snapshot_immutable_and_dated(self):
        r = self.record()
        self.store.ingest_bytes(r, self.raw)
        info = SnapshotInfo('index_1', '1.0.0', '2026-10-07', '2026-10-07T01:00:00Z')
        snap = self.store.snapshot(info, (r,))
        with self.assertRaises(FrozenInstanceError):
            snap.info = None
        with self.assertRaisesRegex(ContractError, 'IMMUTABLE_CONFLICT'):
            self.store.snapshot(info, ())
        self.assertEqual(snap.sources, (r,))

    def test_snapshot_missing_blob_rejected(self):
        info = SnapshotInfo('index_1', '1.0.0', '2026-10-07', '2026-10-07T01:00:00Z')
        with self.assertRaisesRegex(ContractError, 'SOURCE_UNAVAILABLE'):
            self.store.snapshot(info, (self.record(),))

    def test_derivation_cycle(self):
        a = p.DerivationRecord('a', ('b',), 'test_formula', '1', 'test_code', 'exact')
        b = p.DerivationRecord('b', ('a',), 'test_formula', '1', 'test_code', 'exact')
        with self.assertRaisesRegex(ContractError, 'PROVENANCE_CYCLE'):
            p.validate_derivations((a, b), ())

    def test_derivation_missing_parent(self):
        a = p.DerivationRecord('a', ('missing',), 'test_formula', '1', 'test_code', 'exact')
        with self.assertRaisesRegex(ContractError, 'PARENT_MISSING'):
            p.validate_derivations((a,), ())

    def test_derivation_valid(self):
        a = p.DerivationRecord('a', ('source',), 'test_formula', '1', 'test_code', 'exact')
        p.validate_derivations((a,), ('source',))

    def test_concurrent_identical_ingest(self):
        r = self.record()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.store.ingest_bytes, r, self.raw) for _ in range(2)]
            for future in futures:
                future.result()
        self.assertEqual(self.store.read(r), self.raw)

    def test_modified_raw_detected(self):
        record = self.record()
        self.store.ingest_bytes(record, self.raw)
        path = self.store.safe_path('blobs/' + record.ref.source_hash)
        with path.open('wb') as stream:
            stream.write(b'tampered SYNTHETIC TEST')
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            self.store.read(record)

    def test_reparse_point_rejected(self):
        metadata = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        with patch.object(Path, 'lstat', return_value=metadata):
            with self.assertRaisesRegex(ContractError, 'PATH_OUTSIDE_ROOT'):
                self.store.safe_path('outside')

    def test_symlink_rejected(self):
        metadata = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        with patch.object(Path, 'lstat', return_value=metadata):
            with self.assertRaisesRegex(ContractError, 'PATH_OUTSIDE_ROOT'):
                self.store.safe_path('outside')

    def test_future_source_not_in_earlier_snapshot(self):
        record = self.record(ref=replace(self.record().ref, retrieved_at='2026-10-08T00:00:00Z'))
        self.store.ingest_bytes(record, self.raw)
        info = SnapshotInfo('index_1', '1.0.0', '2026-10-07', '2026-10-08T00:00:00Z')
        with self.assertRaisesRegex(ContractError, 'SNAPSHOT_DATE_MISMATCH'):
            self.store.snapshot(info, (record,))


if __name__ == '__main__':
    unittest.main()
