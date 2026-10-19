"""Exactly one GET per originally failed endpoint; append diagnostic evidence only."""
import base64
import json
from pathlib import Path
import sys
workspace = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(workspace / 'outputs/a35_cern_layer'))
from sl_constraints.collider.sources import EvidenceStore, acquire_public

store = EvidenceStore(workspace / 'outputs/a35_cern_layer/data/cern_lhc_snapshot_2026_10_07')
for identity, url in [('atlas_hepdata_recheck', 'https://www.hepdata.net/record/ins3147718?format=json'),
                      ('cms_hepdata_recheck', 'https://www.hepdata.net/record/165871?format=json')]:
    raw, receipt = acquire_public(url)
    receipt['requested_source_id'] = identity
    if receipt['error_response_base64'] is not None:
        body = base64.b64decode(receipt['error_response_base64'])
        store._publish('raw/' + receipt['error_response_sha256'], body)
        receipt['error_response_path'] = 'raw/' + receipt['error_response_sha256']
        print(identity, 'body excerpt:', body[:1500].decode('utf-8', errors='replace'))
    if raw is not None:
        store._publish('raw/' + receipt['sha256'], raw)
        receipt['content_validation'] = 'PENDING_NOT_INGESTED'
    path, digest = store.artifact('receipts', identity, receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'error_response_base64'}), flush=True)
    print(path, digest, flush=True)
