"""Offline, one-snapshot assembly. Freezing is an explicit separate call after review."""
from hashlib import sha256
import json
from pathlib import Path
import sys

workspace = Path(__file__).resolve().parents[1]
package = workspace / 'outputs/a35_cern_layer'
sys.path.insert(0, str(package))
from sl_constraints.collider.sources import EvidenceStore
from sl_constraints.collider.reproduce import atlas_constraints, cms_constraints, SNAPSHOT
from sl_constraints.collider.contracts import BenchmarkDefinition, DatasetRecord, ObservableDefinition, check_schemas
from sl_constraints.collider.schema_document import BENCHMARK, ANALYSIS
from sl_constraints.collider.normalize import audit_coverage
from sl_constraints.collider.coverage import declared_scope
from sl_constraints.common.provenance import canonical_bytes

store = EvidenceStore(package / 'data' / SNAPSHOT)


def build():
    check_schemas()
    staged = {json.loads(p.read_bytes())['source']['source_id']: json.loads(p.read_bytes())['source']
              for p in store.safe_path('catalogs').glob('*_acquisition/*.json')}
    sources = []
    for identity in ('atlas_metadata', 'cms_metadata', 'atlas_aux', 'cms_aux', 'atlas_paper_v2', 'cms_paper_v2'):
        source = staged[identity]
        if identity.endswith('_v2'):
            experiment = identity.split('_')[0]
            metadata = staged[experiment + '_metadata']
            source['historical_evidence'] = dict(source_id=metadata['source_id'], source_version=metadata['source_version'],
                                                 sha256=metadata['sha256'], locator='arXiv submission history v2; current version v2')
            source['source_relationships'] = [source['historical_evidence']]
            source['doi'] = '10.1016/j.physletb.2026.140849' if experiment == 'atlas' else '10.1007/JHEP08(2026)098'
            source['journal_ref'] = 'Phys.Lett.B881(2026)140849' if experiment == 'atlas' else 'JHEP08(2026)098'
            source['table_ids'] = ['S6.T2'] if experiment == 'atlas' else ['Ch0.S9.SS2.tab1']
        store.ingest(source, store.safe_path('raw/' + source['sha256']).read_bytes())
        sources.append(source)
    all_records = []
    for name, builder in [('atlas_paper_v2', atlas_constraints), ('cms_paper_v2', cms_constraints)]:
        source = next(s for s in sources if s['source_id'] == name)
        extracted, records = builder(store.read(source), source)
        for record in extracted:
            store.artifact('extracted', record['artifact_id'], record)
        for record in records:
            store.artifact('normalized', record['constraint_id'], record)
        store._publish('catalogs/' + ('ATLAS_NORMALIZED.json' if name.startswith('atlas') else 'CMS_NORMALIZED.json'), canonical_bytes(records))
        all_records.extend(records)
    benchmarks, datasets, observables = {}, {}, {}
    for row in all_records:
        benchmark = dict(schema_version='1.0.0', **{k: row[k] for k in BENCHMARK}, provenance=row['provenance'], purpose='RESEARCH')
        BenchmarkDefinition.from_dict(benchmark)
        benchmarks.setdefault(row['benchmark_id'], benchmark)
        dataset = dict(schema_version='1.0.0', **{k: row[k] for k in ANALYSIS}, provenance=row['provenance'], purpose='RESEARCH')
        DatasetRecord.from_dict(dataset)
        datasets.setdefault(row['dataset_id'], dataset)
        observable = dict(schema_version='1.0.0', observable_id=row['constraint_id'], observable_type=row['observable_type'],
                          definition=row['observable_definition'], unit=row['unit'], numerator=None, denominator=None)
        ObservableDefinition.from_dict(observable)
        observables[row['constraint_id']] = observable
    for name, values in [('BENCHMARKS', benchmarks), ('DATASETS', datasets), ('OBSERVABLES', observables)]:
        store._publish('catalogs/' + name + '.json', canonical_bytes(list(values.values())))
    scopes = declared_scope()
    # Explicit additional requirements not represented by the scalar slots.
    gaps = [
        dict(scope='ATLAS_HEPData', status='SOURCE_UNAVAILABLE', detail='Official ins3147718 link known; record version and table IDs unconfirmed; no tables acquired or crosschecked'),
        dict(scope='CMS_HEPData', status='SOURCE_UNAVAILABLE', detail='Official ins3144373 link and paper DOI165871 known; version/table identity unconfirmed; no tables acquired or crosschecked'),
        dict(scope='ATLAS_publisher', status='SOURCE_UNAVAILABLE', detail='DOI redirect stopped at host allowlist; publisher bytes not acquired'),
        dict(scope='CMS_publisher', status='SOURCE_UNAVAILABLE', detail='HTTP200 body is Client Challenge, not a paper; retained raw rejection evidence only'),
        dict(scope='ATLAS_sigmaBR_curves', status='TABLE_NOT_FOUND', detail='Eight Table2 mass rows present; cross-section curves, quantile bands and auxiliary numerical data absent'),
        dict(scope='CMS_B1-B3_C1-C6_sigma_curves', status='TABLE_NOT_FOUND', detail='216 declared (model,n,MD) mass-threshold slots; only two observed scalar mass limits explicitly quoted; expected limits and full curves unavailable'),
        dict(scope='CMS_StringBall_sigma_curves', status='TABLE_NOT_FOUND', detail='21 (MS,gs) mass-threshold slots, all scalar limits null; cross-section curves unavailable'),
        dict(scope='CMS_sphaleron_curves', status='TABLE_NOT_FOUND', detail='15 (Esph,pNCS) prefactor slots; only E9,p0.5 observed/expected available; cross sections and expected bands unavailable'),
        dict(scope='CMS_nmax_Table0.9.2', status='PARSE_ERROR', detail='HTML rendering contains grouped parameter ranges and censored <2/>6; no unambiguous typed contour normalization implemented; original paper retained'),
        dict(scope='CMS_model_independent_Fig7', status='TABLE_NOT_FOUND', detail='N>=4 sigma*A slot explicit; remaining multiplicity axes and all numerical curve points not tabulated locally'),
        dict(scope='CMS_sphaleron_observable', status='BENCHMARK_MISMATCH', detail='Abstract event-fraction claim differs from Eq2/section9 dimensionless prefactor; no equality or conversion inferred'),
        dict(scope='CMS_C2_spin', status='SOURCE_CHANGED', detail='Internal wording conflict, NOT a byte/version change: section3 defines C2 nonrotating, section9 groups C2 with rotating scenarios. Definition retained; independent source reconciliation pending'),
        dict(scope='generator_cards_and_complete_physics', status='INCOMPLETE', detail='Detailed generator cards, lifetime/charge/BR/loss/remnant assumptions not all explicitly available; comparison groups remain null'),
        dict(scope='scientific_review', status='PROPOSED', detail='Agent-reviewed extraction is not independent human ACCEPTED data; raw-local lineage and code tests do not establish physics truth')]
    hepdata = []
    for experiment, link in [('ATLAS', 'https://www.hepdata.net/record/ins3147718'), ('CMS', 'https://www.hepdata.net/record/ins3144373')]:
        hepdata.append(dict(experiment=experiment, linked_record_url=link,
                            record_id=None, source_version=None, table_ids=None,
                            raw_sha256=None, units_checked=False, structure_checked=False,
                            benchmark_binding_checked=False, paper_crosscheck='SOURCE_MISSING',
                            status='SOURCE_UNAVAILABLE', success=False))
    store._publish('catalogs/HEPDATA_STATUS.json', canonical_bytes(hepdata))
    coverage = audit_coverage(all_records, scopes)
    coverage.update(required_scope=scopes, additional_gaps=gaps, frozen_scalar_count=len(all_records),
                    observed_nonnull_count=sum(r['observed_value'] is not None for r in all_records),
                    paired_nonnull_count=sum(r['observed_value'] is not None and r['expected_value'] is not None for r in all_records),
                    sigma_SL_project='UNDEFINED')
    store._publish('coverage/COVERAGE_REVIEWED.json', canonical_bytes(coverage))
    receipts = []
    for path in store.safe_path('receipts').rglob('*.json'):
        receipt = json.loads(path.read_bytes())
        if receipt['status'] == 'SOURCE_UNAVAILABLE':
            receipts.append(dict(artifact_id=path.parent.name, sha256=sha256(path.read_bytes()).hexdigest()))
    return sources, all_records, gaps, receipts


def freeze():
    # Existing validated numerical artifacts are read, not regenerated or replaced.
    sources = [json.loads(p.read_bytes()) for p in sorted(store.safe_path('sources').glob('*.json'))]
    records = []
    for name in ('ATLAS_NORMALIZED', 'CMS_NORMALIZED'):
        records.extend(json.loads(store.safe_path('catalogs/' + name + '.json').read_bytes()))
    previous = json.loads(store.safe_path('coverage/COVERAGE.json').read_bytes())
    coverage = audit_coverage(records, declared_scope())
    coverage.update(required_scope=declared_scope(), additional_gaps=previous['additional_gaps'],
                    frozen_scalar_count=len(records),
                    observed_nonnull_count=sum(r['observed_value'] is not None for r in records),
                    paired_nonnull_count=sum(r['observed_value'] is not None and r['expected_value'] is not None for r in records),
                    sigma_SL_project='UNDEFINED')
    store._publish('coverage/COVERAGE_REVIEWED.json', canonical_bytes(coverage))
    receipts = [dict(artifact_id=p.parent.name, sha256=sha256(p.read_bytes()).hexdigest())
                for p in sorted(store.safe_path('receipts').rglob('*.json'))
                if json.loads(p.read_bytes())['status'] == 'SOURCE_UNAVAILABLE']
    manifest = store.freeze(SNAPSHOT, '2026-10-07', sources, records, previous['additional_gaps'],
                            unavailable_receipts=receipts, required_scope=declared_scope())
    print(manifest['status'], len(manifest['sources']), len(manifest['constraint_ids']), len(manifest['gaps']))


if __name__ == '__main__':
    sources, records, gaps, receipts = build()
    print('ASSEMBLED_NOT_FROZEN', len(sources), len(records), len(gaps), len(receipts))
