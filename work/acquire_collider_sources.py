"""One explicit public-source acquisition batch for P07; never invoked on import."""
import json
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

workspace = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(workspace / 'outputs/a35_cern_layer'))
from sl_constraints.collider.sources import EvidenceStore, acquire_public

store = EvidenceStore(workspace / 'outputs/a35_cern_layer/data/cern_lhc_snapshot_2026_10_07')
sources = [
    ('atlas_metadata', 'https://arxiv.org/abs/2604.19495', 'ATLAS', 'EXOT-2024-32', None, None),
    ('cms_metadata', 'https://arxiv.org/abs/2604.10732', 'CMS', 'EXO-24-028', None, None),
    ('atlas_paper_v2', 'https://arxiv.org/html/2604.19495v2', 'ATLAS', 'EXOT-2024-32', '2026-09-24', '2604.19495v2'),
    ('cms_paper_v2', 'https://arxiv.org/html/2604.10732v2', 'CMS', 'EXO-24-028', '2026-08-26', '2604.10732v2'),
    ('atlas_aux', 'https://atlas.web.cern.ch/Atlas/GROUPS/PHYSICS/PAPERS/EXOT-2024-32/', 'ATLAS', 'EXOT-2024-32', None, None),
    ('cms_aux', 'https://cms-results.web.cern.ch/cms-results/public-results/publications/EXO-24-028/', 'CMS', 'EXO-24-028', None, None),
    ('atlas_publisher', 'https://doi.org/10.1016/j.physletb.2026.140849', 'ATLAS', 'EXOT-2024-32', None, None),
    ('cms_publisher', 'https://doi.org/10.1007/JHEP08(2026)098', 'CMS', 'EXO-24-028', None, None),
    ('atlas_hepdata', 'https://www.hepdata.net/record/ins3147718?format=json', 'ATLAS', 'EXOT-2024-32', None, None),
    ('cms_hepdata', 'https://www.hepdata.net/record/165871?format=json', 'CMS', 'EXO-24-028', None, None),
]


def acquire(item):
    identity, url, collaboration, analysis, published, arxiv = item
    raw, receipt = acquire_public(url)
    receipt['requested_source_id'] = identity
    store.artifact('receipts', identity, receipt)
    print(identity, receipt['status'], receipt['byte_count'], receipt['error_class'], flush=True)
    if raw is None:
        return
    record = dict(schema_version='1.0.0', source_id=identity,
                  source_version=arxiv or 'retrieved-' + receipt['sha256'][:16],
                  title=analysis + ' ' + identity, url=url, actual_url=receipt['actual_url'],
                  retrieved_at=receipt['retrieved_at'], sha256=receipt['sha256'],
                  media_type=receipt['media_type'], byte_count=receipt['byte_count'],
                  collaboration=collaboration, analysis_id=analysis, published_at=published,
                  publication_date_precision='DAY' if published else 'UNKNOWN',
                  arxiv_version=arxiv, journal_ref=None, doi=None, inspire_id=None,
                  hepdata_record_id=None, hepdata_version=None, table_ids=[],
                  source_relationships=[], historical_evidence=None, purpose='RESEARCH')
    # Staging records are intentionally not ingested until publication metadata is reviewed.
    store.artifact('catalogs', identity + '_acquisition', {'source': record, 'status': 'VERSION_REVIEW_REQUIRED'})
    store._publish('raw/' + receipt['sha256'], raw)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(acquire, sources))
