"""Offline final verification, writing only its derived audit report under outputs."""
import ast
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import subprocess

workspace = Path(__file__).resolve().parents[1]
package = workspace / 'outputs/a35_cern_layer'
sys.path.insert(0, str(package))
from sl_constraints.collider.sources import EvidenceStore
from sl_constraints.collider.contracts import ConstraintRecord, check_schemas
from sl_constraints.collider.schema_document import SCHEMAS, document
from sl_constraints.collider.reproduce import SNAPSHOT
from sl_constraints.collider.coverage import declared_scope

baseline = workspace / 'work/collider-baseline/a35_cern_layer'
unchanged = []
for original in baseline.rglob('*'):
    if original.is_file():
        relative = original.relative_to(baseline)
        assert original.read_bytes() == (package / relative).read_bytes(), relative
        unchanged.append(relative.as_posix())
check_schemas()
for kind in SCHEMAS:
    assert json.loads((package / 'schemas' / (kind + '.schema.json')).read_bytes()) == document(kind), kind
python_files = list(package.rglob('*.py'))
for path in python_files:
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
store = EvidenceStore(package / 'data' / SNAPSHOT)
source_records = [json.loads(p.read_bytes()) for p in store.safe_path('sources').glob('*.json')]
source_by_id = {source['source_id']: source for source in source_records}
for source in source_records:
    store.read(source)
    for relationship in source['source_relationships']:
        parent = source_by_id.get(relationship['source_id'])
        assert parent is not None
        assert parent['source_version'] == relationship['source_version']
        assert parent['sha256'] == relationship['sha256']
        store.read(parent)
raw_count = 0
for path in store.safe_path('raw').iterdir():
    if path.is_file():
        assert sha256(path.read_bytes()).hexdigest() == path.name, path
        raw_count += 1
records = []
for name in ('ATLAS_NORMALIZED', 'CMS_NORMALIZED'):
    records.extend(json.loads(store.safe_path('catalogs/' + name + '.json').read_bytes()))
for row in records:
    ConstraintRecord.from_dict(row)
assert len({row['constraint_id'] for row in records}) == len(records)
scope_fields = ('analysis_id', 'benchmark_id', 'channel_id', 'observable_type')
assert {tuple(row[k] for k in scope_fields) for row in records} == {
    tuple(row[k] for k in scope_fields) for row in declared_scope()}
hepdata_rechecks = {}
for identity in ('atlas_hepdata_recheck', 'cms_hepdata_recheck'):
    matches = list(store.safe_path('receipts').glob(identity + '/*.json'))
    assert len(matches) == 1
    receipt = json.loads(matches[0].read_bytes())
    body = base64.b64decode(receipt['error_response_base64'], validate=True)
    assert receipt['status'] == 'SOURCE_UNAVAILABLE' and receipt['http_status'] == 403
    assert sha256(body).hexdigest() == receipt['error_response_sha256']
    raw_body = store.safe_path('raw/' + receipt['error_response_sha256']).read_bytes()
    assert raw_body == body
    hepdata_rechecks[identity] = {'http_status': receipt['http_status'], 'sha256': receipt['error_response_sha256']}
cms_aux = store.read(source_by_id['cms_aux'])
cms_active_csv_links = re.findall(rb'<a\s+[^>]*href=["\']([^"\']+\.csv)',
                                  re.sub(rb'<!--.*?-->', b'', cms_aux, flags=re.DOTALL), re.IGNORECASE)
assert not cms_active_csv_links
manifest_path = store.safe_path('snapshots/' + SNAPSHOT + '.json')
manifest = store.read_snapshot(SNAPSHOT) if manifest_path.exists() else None
research = Path('C:/Users/xfire/Documents/Codex/2026-08-29/github-plugin-github-openai-curated-remote-3/work/SL-BH-Kernhypothese-Erdmodul')
reference_hashes = {
    'STAGE3_95B_A35_WDM_CHARGE_CLOSURE_SPEC.md': '131cfc48301dd5e8ee6a93a346e35f0345212e8c831e6712d5e291ca70f57df5',
    'STAGE3_95C_A35_WDM_THEORETICAL_CLOSURE_ARCHITECTURE.md': '3877c7dbf7a40bb436f93e769f7e2dc5dfcae08c555430e4587cc2f83fd20985',
    'STAGE3_95J_A35_PHYSICAL_CLOSURE_NUMERICAL_INVENTORY.md': 'a320727e02bef7c2c4994460843b7e0439c178856be6bbd981627bda299c85dd',
    'data/stage3_95k/a35_acquisition_jobs.json': '91038f26f251f60cecea2f9dd515620cd51fcd3c7669d634ee17837c2eef8e20',
}
for path, digest in reference_hashes.items():
    assert sha256((research / path).read_bytes()).hexdigest() == digest, path
diff = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c',
                       'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol',
                       '-c', 'core.attributesFile=' + str(package / '.gitattributes'),
                       'diff', '--no-index', '--check', '--', str(baseline), str(package)],
                      capture_output=True, text=True, cwd=workspace)
assert diff.returncode in (0, 1) and not diff.stdout.strip() and not diff.stderr.strip(), (diff.returncode, diff.stdout, diff.stderr)
authored = [p for p in package.rglob('*') if p.is_file() and 'data' not in p.relative_to(package).parts
            and '__pycache__' not in p.parts]
authored += [workspace / 'outputs' / name for name in
             ('CERN_DATA_LAYER_IMPLEMENTATION_REPORT.md', 'CERN_INDEPENDENT_REVIEW.md',
              'CERN_FINAL_CODE_RECHECK.md', 'CERN_GITHUB_SYNC_PREPARATION.md',
              'CERN_TEST_RESULTS.json', 'CERN_TEST_full_212.log', 'CERN_TEST_prior_full_baseline_210.log',
              'HEPDATA_RETRIEVAL_DIAGNOSIS.md')]
authored += [workspace / 'work' / name for name in
             ('build_collider_snapshot.py', 'verify_collider_delivery.py', 'run_collider_final_tests.py',
              'recheck_hepdata.py', 'acquire_collider_sources.py', 'finish_collider_acquisition.py')]
code_manifest = {p.relative_to(workspace).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(authored)}
(workspace / 'outputs/CERN_CODE_MANIFEST.json').write_text(json.dumps(code_manifest, indent=2) + '\n', encoding='utf-8')
report = dict(foundation_files_unchanged=unchanged, source_count=len(source_records), raw_hashes_verified=raw_count,
              syntax_files_checked=len(python_files), schema_exports_checked=list(SCHEMAS),
              constraints=len(records), observed_nonnull=sum(r['observed_value'] is not None for r in records),
              expected_nonnull=sum(r['expected_value'] is not None for r in records),
              comparison_groups_nonnull=sum(r['comparison_group'] is not None for r in records),
              source_relationships_resolved=True, hepdata_rechecks=hepdata_rechecks,
              cms_aux_active_csv_links=len(cms_active_csv_links),
              research_reference_hashes=reference_hashes,
              snapshot_status=manifest['status'] if manifest else 'NOT_FROZEN',
              manifest_file_sha256=sha256(manifest_path.read_bytes()).hexdigest() if manifest else None,
              artifact_count=len(manifest['artifacts']) if manifest else None,
              declared_scope_exact_match=True,
              whitespace_check=dict(status='PASS', method='git diff --no-index --check; raw binary; CRLF allowed',
                                    exit_code=diff.returncode, stdout=diff.stdout, stderr=diff.stderr),
              code_manifest='CERN_CODE_MANIFEST.json')
(workspace / 'outputs/CERN_FINAL_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
