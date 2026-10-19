"""Immutable content-addressed evidence store and explicitly invoked public GET.

Trusted local root required. Hashes detect mutation; they do not stop an OS admin.
No network on import/read, no archive extraction, no execution of source content.
"""
from datetime import date, datetime, timezone
import base64
from hashlib import sha256
from http.client import IncompleteRead
import json
import os
import tempfile
from urllib.parse import urlsplit
import urllib.request
from urllib.error import HTTPError, URLError

from ..common.provenance import LocalSourceStore, canonical_bytes
from ..common.types import ContractError, identifier
from .contracts import SourceRecord, ConstraintRecord, SnapshotManifest
from .benchmark import normalize_identity
from .extraction import MAX_BYTES, parse_json

HOSTS = frozenset(('arxiv.org', 'www.hepdata.net', 'hepdata.net', 'doi.org', 'dx.doi.org',
                   'atlas.web.cern.ch', 'cms-results.web.cern.ch', 'link.springer.com',
                   'www.sciencedirect.com', 'inspirehep.net'))


def validate_url(url):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname in HOSTS and
                 parsed.port in (None, 443) and not parsed.username and not parsed.password and not parsed.fragment)
    except ValueError as exc:
        raise ContractError('URL_REFUSED') from exc
    if not valid:
        raise ContractError('URL_REFUSED')


class _Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def acquire_public(url):
    """Return (original bytes or None, honest receipt); caller validates source identity."""
    validate_url(url)
    receipt = dict(schema_version='1.0.0', attempted_url=url, retrieved_at=utc_now(),
                   status='SOURCE_UNAVAILABLE', actual_url=None, media_type=None,
                   byte_count=None, sha256=None, error_class=None, http_status=None,
                   error_message=None, response_headers={}, error_response_base64=None,
                   error_response_sha256=None, error_response_truncated=False)
    try:
        opener = urllib.request.build_opener(_Redirect())
        request = urllib.request.Request(url, headers={'User-Agent': 'SL-Research-Evidence/1.0', 'Accept-Encoding': 'identity'})
        with opener.open(request, timeout=20) as response:
            validate_url(response.url)
            raw = response.read(MAX_BYTES + 1)
            if not raw or len(raw) > MAX_BYTES:
                raise ContractError('RESOURCE_LIMIT')
            receipt.update(actual_url=response.url, media_type=response.headers.get_content_type(),
                           byte_count=len(raw), sha256=sha256(raw).hexdigest(), status='ACQUIRED',
                           http_status=response.status)
            return raw, receipt
    except HTTPError as exc:
        # Preserve the failure, not a fabricated empty dataset. Never retry automatically.
        receipt.update(http_status=exc.code, actual_url=exc.url, error_class='HTTPError',
                       error_message=str(exc.reason)[:1000], media_type=exc.headers.get_content_type())
        receipt['response_headers'] = {k: exc.headers[k] for k in
                                       ('content-type', 'server', 'retry-after', 'location') if exc.headers.get(k)}
        try:
            try:
                body = exc.read(65537)
            except IncompleteRead as read_error:
                body = read_error.partial
                receipt['error_response_truncated'] = True
                receipt['error_message'] += '; response incomplete: IncompleteRead'
            receipt['error_response_truncated'] |= len(body) > 65536
            body = body[:65536]
            receipt['error_response_base64'] = base64.b64encode(body).decode('ascii')
            receipt['error_response_sha256'] = sha256(body).hexdigest()
        except (OSError, TimeoutError) as read_error:
            receipt['error_message'] += '; response unreadable: ' + type(read_error).__name__
        finally:
            exc.close()
        return None, receipt
    except (URLError, TimeoutError, OSError, ContractError) as exc:
        receipt['error_class'] = type(exc).__name__ + (':' + exc.code if isinstance(exc, ContractError) else '')
        return None, receipt


class EvidenceStore(LocalSourceStore):
    @staticmethod
    def source_path(source):
        key = sha256(canonical_bytes([source['source_id'], source['source_version']])).hexdigest()
        return f'sources/{key}.json'

    def ingest(self, source, raw):
        SourceRecord.from_dict(source)
        if not isinstance(raw, bytes) or sha256(raw).hexdigest() != source['sha256']:
            raise ContractError('HASH_MISMATCH')
        if len(raw) != source['byte_count']:
            raise ContractError('SIZE_MISMATCH')
        path = self.safe_path(self.source_path(source))
        if path.exists() and path.read_bytes() != canonical_bytes(source):
            raise ContractError('IMMUTABLE_CONFLICT')
        self._publish('raw/' + source['sha256'], raw)
        self._publish(self.source_path(source), canonical_bytes(source))

    def read(self, source):
        SourceRecord.from_dict(source)
        try:
            if self.safe_path(self.source_path(source)).read_bytes() != canonical_bytes(source):
                raise ContractError('IMMUTABLE_CONFLICT')
            path = self.safe_path('raw/' + source['sha256'])
            if path.stat().st_size > MAX_BYTES:
                raise ContractError('RESOURCE_LIMIT')
            raw = path.read_bytes()
        except FileNotFoundError as exc:
            raise ContractError('SOURCE_UNAVAILABLE') from exc
        if sha256(raw).hexdigest() != source['sha256']:
            raise ContractError('HASH_MISMATCH')
        if len(raw) != source['byte_count']:
            raise ContractError('SIZE_MISMATCH')
        return raw

    def artifact(self, layer, identity, data):
        if layer not in ('extracted', 'normalized', 'receipts', 'catalogs', 'coverage'):
            raise ContractError('INVALID_LAYER')
        identifier(identity)
        payload = canonical_bytes(data)
        if len(payload) > MAX_BYTES:
            raise ContractError('RESOURCE_LIMIT')
        digest = sha256(payload).hexdigest()
        relative = f'{layer}/{identity}/{digest}.json'
        self._publish(relative, payload)
        return relative, digest

    def _artifact_entries(self):
        entries = []
        for layer in ('sources', 'raw', 'extracted', 'normalized', 'receipts', 'catalogs', 'coverage'):
            folder = self.safe_path(layer)
            if not folder.exists():
                continue
            for path in sorted(folder.rglob('*')):
                relative = path.relative_to(self.root).as_posix()
                self.safe_path(relative)
                if path.is_file():
                    if path.stat().st_size > MAX_BYTES:
                        raise ContractError('RESOURCE_LIMIT')
                    entries.append({'path': relative, 'sha256': sha256(path.read_bytes()).hexdigest()})
        return entries

    def freeze(self, snapshot_id, cutoff_date, sources, constraints, gaps, *, unavailable_receipts=(), required_scope=None):
        identifier(snapshot_id)
        path = self.safe_path(f'snapshots/{snapshot_id}.json')
        if path.exists():
            raise ContractError('SNAPSHOT_EXISTS')
        cutoff = date.fromisoformat(cutoff_date)
        sources = sorted(sources, key=lambda s: s['source_id'])
        if len({s['source_id'] for s in sources}) != len(sources):
            raise ContractError('DUPLICATE_SOURCE_ID')
        if not sources or not constraints:
            raise ContractError('EMPTY_SNAPSHOT')
        gaps = list(gaps)
        by_source = {s['source_id']: s for s in sources}
        for source in sources:
            self.read(source)
            if source['published_at'] is not None and date.fromisoformat(source['published_at']) > cutoff:
                raise ContractError('SOURCE_AFTER_CUTOFF')
            for relation in source['source_relationships']:
                parent = by_source.get(relation['source_id'])
                if (parent is None or parent['source_version'] != relation['source_version']
                        or parent['sha256'] != relation['sha256']):
                    raise ContractError('PROVENANCE_MISMATCH', 'source relationship')
                self.read(parent)
            if source['purpose'] != 'RESEARCH' or source['historical_evidence'] is None or source['published_at'] is None:
                gaps.append({'scope': source['source_id'], 'status': 'HISTORICAL_VERSION_UNVERIFIED',
                             'detail': 'Synthetic or missing dated version evidence; not proof of historical availability'})
            evidence = source['historical_evidence']
            if evidence is not None:
                parent = by_source.get(evidence['source_id'])
                if parent is None or parent['sha256'] != evidence['sha256'] or parent['source_version'] != evidence['source_version']:
                    raise ContractError('PROVENANCE_MISMATCH', 'historical evidence')
        entries = self._artifact_entries()
        artifact_map = {entry['path']: entry['sha256'] for entry in entries}
        from .normalize import audit_coverage
        coverage = audit_coverage(constraints, required_scope or [])
        gaps.extend(coverage['gaps'])
        if not required_scope:
            gaps.append({'scope': 'coverage', 'status': 'INCOMPLETE', 'detail': 'Independent required scope not supplied'})
        receipts = {(r['artifact_id'], r['sha256']): r for r in unavailable_receipts}
        for entry in entries:
            if entry['path'].startswith('coverage/'):
                stored = parse_json(self.safe_path(entry['path']).read_bytes())
                if stored.get('status') != 'COMPLETE':
                    gaps.append({'scope': entry['path'], 'status': 'INCOMPLETE', 'detail': 'Stored coverage is not complete'})
            if entry['path'].startswith('receipts/'):
                stored = parse_json(self.safe_path(entry['path']).read_bytes())
                if stored.get('status') == 'SOURCE_UNAVAILABLE':
                    identity = entry['path'].split('/')[-2]
                    receipts[(identity, entry['sha256'])] = {'artifact_id': identity, 'sha256': entry['sha256']}
        unavailable_receipts = [receipts[key] for key in sorted(receipts)]
        for ref in unavailable_receipts:
            relative = f"receipts/{ref['artifact_id']}/{ref['sha256']}.json"
            if artifact_map.get(relative) != ref['sha256']:
                raise ContractError('RECEIPT_MISSING')
            receipt = parse_json(self.safe_path(relative).read_bytes())
            if receipt.get('status') != 'SOURCE_UNAVAILABLE':
                raise ContractError('RECEIPT_STATUS_MISMATCH')
            gaps.append({'scope': ref['artifact_id'], 'status': 'SOURCE_UNAVAILABLE', 'detail': 'Verified unavailable-source receipt'})
        identifiers = []
        for record in constraints:
            ConstraintRecord.from_dict(record)
            if record['snapshot_id'] != snapshot_id:
                raise ContractError('SNAPSHOT_ID_MISMATCH')
            identifiers.append(record['constraint_id'])
            for ref in record['provenance']:
                source = by_source.get(ref['source_id'])
                if source is None or source['source_version'] != ref['source_version'] or source['sha256'] != ref['sha256']:
                    raise ContractError('PROVENANCE_MISMATCH')
            for ref in record['extraction_refs']:
                relative = f"extracted/{ref['artifact_id']}/{ref['sha256']}.json"
                if artifact_map.get(relative) != ref['sha256']:
                    raise ContractError('EXTRACTION_MISSING')
                extract = parse_json(self.safe_path(relative).read_bytes())
                parent = by_source.get(extract['source_id'])
                if parent is None or parent['sha256'] != extract['source_hash'] or parent['source_version'] != extract['source_version']:
                    raise ContractError('PROVENANCE_MISMATCH')
                if not any(p['source_id'] == extract['source_id'] and p['source_version'] == extract['source_version']
                           and p['sha256'] == extract['source_hash'] for p in record['provenance']):
                    raise ContractError('PROVENANCE_MISMATCH', 'extraction is not a parent of this constraint')
            digest = sha256(canonical_bytes(record)).hexdigest()
            relative = f"normalized/{record['constraint_id']}/{digest}.json"
            if artifact_map.get(relative) != digest:
                raise ContractError('NORMALIZED_MISSING')
            normalized = normalize_identity(record)
            if record['comparison_group'] is not None and record['comparison_group'] != normalized['comparison_group']:
                raise ContractError('FINGERPRINT_MISMATCH')
            if normalized['missing_fields'] or record['validation_status'] != 'ACCEPTED' or record['purpose'] != 'RESEARCH':
                gaps.append({'scope': record['constraint_id'], 'status': 'INCOMPLETE',
                             'detail': 'Missing metadata/value or pending independent scientific acceptance'})
        if len(set(identifiers)) != len(identifiers):
            raise ContractError('DUPLICATE_CONSTRAINT_ID')
        manifest = dict(schema_version='1.0.0', snapshot_id=snapshot_id, cutoff_date=cutoff_date,
                        created_at=utc_now(), status='FROZEN_PARTIAL' if gaps else 'FROZEN_COMPLETE',
                        parser_version='1.0.0', normalizer_version='1.0.0',
                        sources=[{'artifact_id': s['source_id'], 'sha256': s['sha256']} for s in sources],
                        artifacts=entries, constraint_ids=sorted(identifiers), gaps=gaps,
                        unavailable_receipts=list(unavailable_receipts), supersedes=None)
        SnapshotManifest.from_dict(manifest)
        content = canonical_bytes(manifest)
        envelope = canonical_bytes({'manifest': manifest, 'manifest_sha256': sha256(content).hexdigest()})
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.freeze-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(envelope); stream.flush(); os.fsync(stream.fileno())
            self.safe_path(f'snapshots/{snapshot_id}.json')
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                raise ContractError('SNAPSHOT_EXISTS') from exc
        finally:
            os.unlink(temporary)
        self.read_snapshot(snapshot_id)
        return manifest

    def read_snapshot(self, snapshot_id):
        identifier(snapshot_id)
        path = self.safe_path(f'snapshots/{snapshot_id}.json')
        envelope = parse_json(path.read_bytes())
        manifest = envelope['manifest']
        SnapshotManifest.from_dict(manifest)
        if manifest['snapshot_id'] != snapshot_id or sha256(canonical_bytes(manifest)).hexdigest() != envelope['manifest_sha256']:
            raise ContractError('HASH_MISMATCH', 'manifest')
        for entry in manifest['artifacts']:
            path = self.safe_path(entry['path'])
            if not path.exists() or path.stat().st_size > MAX_BYTES or sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ContractError('HASH_MISMATCH', entry['path'])
        return manifest
