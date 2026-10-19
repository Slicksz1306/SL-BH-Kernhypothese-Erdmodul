"""Local-only immutable source identities and minimal source-index snapshots.

No downloading, extraction, dataset parsing or execution. The root must be
owned by the caller; this is not an OS sandbox against a concurrent local
attacker replacing directories. Existing links/reparse points fail closed.
"""
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PureWindowsPath
import stat
import tempfile
import re
from .types import (ContractError, SourceRef, SnapshotInfo, identifier, nonempty)

MAX_SOURCE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class SourceRecord:
    ref: SourceRef
    title: str
    author: str
    published: str
    locator: str
    origin: str
    access: str
    media_type: str
    byte_count: int

    def __post_init__(self):
        if not isinstance(self.ref, SourceRef):
            raise ContractError('INVALID_SOURCE')
        for name in ('title', 'author', 'published', 'locator', 'origin', 'access', 'media_type'):
            nonempty(getattr(self, name))
        if type(self.byte_count) is not int or not 0 <= self.byte_count <= MAX_SOURCE_BYTES:
            raise ContractError('INVALID_SIZE')


@dataclass(frozen=True)
class SourceSnapshot:
    info: SnapshotInfo
    sources: tuple[SourceRecord, ...]
    manifest_hash: str

    def __post_init__(self):
        object.__setattr__(self, 'sources', tuple(self.sources))
        if not isinstance(self.info, SnapshotInfo) or not all(isinstance(r, SourceRecord) for r in self.sources):
            raise ContractError('INVALID_SNAPSHOT')
        if not isinstance(self.manifest_hash, str) or not re.fullmatch('[0-9a-f]{64}', self.manifest_hash):
            raise ContractError('INVALID_HASH')


@dataclass(frozen=True)
class DerivationRecord:
    derivation_id: str
    parents: tuple[str, ...]
    formula: str
    formula_version: str
    code_version: str
    uncertainty_rule: str

    def __post_init__(self):
        identifier(self.derivation_id)
        identifier(self.formula_version)
        for name in ('formula', 'code_version', 'uncertainty_rule'):
            nonempty(getattr(self, name))
        parents = tuple(self.parents)
        if not parents or len(set(parents)) != len(parents):
            raise ContractError('INVALID_PARENTS')
        for parent in parents:
            identifier(parent)
        object.__setattr__(self, 'parents', parents)


def validate_derivations(records: tuple[DerivationRecord, ...], source_ids: tuple[str, ...]):
    nodes = {r.derivation_id: r for r in records}
    if len(nodes) != len(records) or set(nodes).intersection(source_ids):
        raise ContractError('DUPLICATE_ID')
    done, visiting = set(source_ids), set()

    def visit(key):
        if key in visiting:
            raise ContractError('PROVENANCE_CYCLE')
        if key in done:
            return
        if key not in nodes:
            raise ContractError('PARENT_MISSING', key)
        visiting.add(key)
        for parent in nodes[key].parents:
            visit(parent)
        visiting.remove(key)
        done.add(key)

    for key in nodes:
        visit(key)


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def _no_link(path: Path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ContractError('PATH_OUTSIDE_ROOT', 'links/reparse points forbidden')


class LocalSourceStore:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()
        for part in (self.root, *self.root.parents):
            _no_link(part)
        self.root.mkdir(parents=True, exist_ok=True)

    def safe_path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
            raise ContractError('PATH_OUTSIDE_ROOT')
        path = Path(relative)
        if path.is_absolute() or PureWindowsPath(relative).is_absolute() or any(
                part in ('', '.', '..') for part in relative.split('/')):
            raise ContractError('PATH_OUTSIDE_ROOT')
        current = self.root
        _no_link(current)
        for part in path.parts:
            current = current / part
            _no_link(current)
        if not current.resolve().is_relative_to(self.root.resolve()):
            raise ContractError('PATH_OUTSIDE_ROOT')
        return current

    def _publish(self, relative: str, content: bytes):
        path = self.safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.safe_path(relative)
        # Hard-link publication is atomic and refuses to replace an existing file.
        fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                self.safe_path(relative)
                if path.read_bytes() != content:
                    raise ContractError('IMMUTABLE_CONFLICT', relative)
        finally:
            os.unlink(temporary)

    @staticmethod
    def _identity(record: SourceRecord) -> str:
        # Hash the exact identity, avoiding case-insensitive Windows name collisions.
        digest = sha256(canonical_bytes([record.ref.source_id, record.ref.source_version])).hexdigest()
        return f'identities/{digest}.json'

    @staticmethod
    def _check(record: SourceRecord, raw: bytes):
        reasons = set(record.ref.readiness_reasons()) - {'TEST_FIXTURE'}
        if reasons:
            raise ContractError('PROVENANCE_MISSING', ','.join(sorted(reasons)))
        if not isinstance(raw, bytes) or len(raw) > MAX_SOURCE_BYTES:
            raise ContractError('INVALID_SIZE')
        if sha256(raw).hexdigest() != record.ref.source_hash:
            raise ContractError('HASH_MISMATCH')
        if len(raw) != record.byte_count:
            raise ContractError('SIZE_MISMATCH')

    def ingest_bytes(self, record: SourceRecord, raw: bytes):
        self._check(record, raw)
        identity = self.safe_path(self._identity(record))
        content = canonical_bytes(asdict(record))
        if identity.exists() and identity.read_bytes() != content:
            raise ContractError('IMMUTABLE_CONFLICT')
        self._publish(f'blobs/{record.ref.source_hash}', raw)
        self._publish(self._identity(record), content)

    def read(self, record: SourceRecord) -> bytes:
        # Validate identifiers/hash before constructing any path.
        if set(record.ref.readiness_reasons()) - {'TEST_FIXTURE'}:
            raise ContractError('PROVENANCE_MISSING')
        try:
            identity = self.safe_path(self._identity(record)).read_bytes()
            if identity != canonical_bytes(asdict(record)):
                raise ContractError('IMMUTABLE_CONFLICT')
            path = self.safe_path(f'blobs/{record.ref.source_hash}')
            if path.stat().st_size > MAX_SOURCE_BYTES:
                raise ContractError('INVALID_SIZE')
            raw = path.read_bytes()
        except FileNotFoundError as exc:
            raise ContractError('SOURCE_UNAVAILABLE') from exc
        self._check(record, raw)
        return raw

    def snapshot(self, info: SnapshotInfo, sources: tuple[SourceRecord, ...]) -> SourceSnapshot:
        sources = tuple(sorted(sources, key=lambda r: (r.ref.source_id, r.ref.source_version)))
        keys = [(r.ref.source_id, r.ref.source_version) for r in sources]
        if len(set(keys)) != len(keys):
            raise ContractError('DUPLICATE_ID')
        for record in sources:
            self.read(record)
            retrieved = datetime.fromisoformat(record.ref.retrieved_at.replace('Z', '+00:00')).astimezone(timezone.utc)
            if retrieved.date() > date.fromisoformat(info.snapshot_date):
                raise ContractError('SNAPSHOT_DATE_MISMATCH')
        manifest = canonical_bytes({'info': asdict(info), 'sources': [asdict(r) for r in sources]})
        key = sha256(info.snapshot_id.encode('utf-8')).hexdigest()
        self._publish(f'source_indexes/{key}.json', manifest)
        return SourceSnapshot(info, sources, sha256(manifest).hexdigest())
