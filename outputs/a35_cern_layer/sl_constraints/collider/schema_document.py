"""Single declarative source for the exported Draft 2020-12 wire schemas."""
from copy import deepcopy

VERSION = '1.0.0'
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 32768}
ID = {'type': 'string', 'pattern': r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$'}
HASH = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
NUMBER = {'type': 'string', 'pattern': r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$', 'maxLength': 128}


def nullable(value):
    return {'anyOf': [deepcopy(value), {'type': 'null'}]}


def enum(*values):
    return {'enum': list(values)}


def array(items, minimum=0):
    return {'type': 'array', 'items': deepcopy(items), 'minItems': minimum, 'maxItems': 1000000}


def obj(**properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


PURPOSE = enum('RESEARCH', 'TEST_FIXTURE')
QUANTITY = obj(value=nullable(NUMBER), unit=TEXT, definition=TEXT)
REF = obj(source_id=ID, source_version=TEXT, sha256=HASH, locator=TEXT)
ARTIFACT_REF = obj(artifact_id=ID, sha256=HASH)
PARAM = obj(name=ID, role=enum('FIXED', 'SCAN'), value=nullable(NUMBER), definition=TEXT)
OBJECT = enum('QUANTUM_BLACK_HOLE', 'SEMICLASSICAL_BLACK_HOLE', 'STRING_BALL', 'SPHALERON', 'GENERIC_HIGH_MULTIPLICITY')
OBSERVABLE = enum('MASS_THRESHOLD', 'SIGMA', 'SIGMA_TIMES_BR', 'SIGMA_TIMES_ACCEPTANCE',
                  'SPHALERON_FRACTION', 'EVENT_FRACTION', 'DIMENSIONLESS_PARAMETER', 'OTHER', 'EXCLUSION_CONTOUR')
ASSUMPTIONS = obj(**{k: nullable(TEXT) for k in (
    'generator', 'pdf', 'threshold_convention', 'fundamental_scale_definition',
    'spin', 'charge', 'lifetime', 'decay_regime', 'branching_ratios', 'loss_model', 'remnant')})
BASE = {'schema_version': {'const': VERSION}}
BENCHMARK = dict(benchmark_id=ID, object_class=OBJECT, model_family=nullable(TEXT),
                 model_version=nullable(TEXT), n_extra_dimensions=nullable({'type': 'integer', 'minimum': 1}),
                 model_parameters=array(PARAM), assumptions=ASSUMPTIONS, validity_domain=nullable(TEXT))
ANALYSIS = dict(experiment=enum('ATLAS', 'CMS'), collaboration=TEXT, analysis_id=ID,
                publication_date=nullable(TEXT), data_period=nullable(TEXT), dataset_id=ID,
                sqrt_s=QUANTITY, luminosity=QUANTITY)
MEASUREMENT = dict(channel_id=ID, selection_id=nullable(TEXT), observable_type=OBSERVABLE,
                   observable_definition=nullable(TEXT), limit_type=enum('LOWER_BOUND', 'UPPER_BOUND', 'EXCLUDED_REGION'),
                   confidence_level=nullable(NUMBER), statistical_method=nullable(TEXT), unit=nullable(TEXT))
STATUS = enum('PROPOSED', 'ACCEPTED', 'INCOMPLETE', 'REJECTED')
SCHEMAS = {
    'constraint': obj(**BASE, constraint_id=ID, snapshot_id=ID, source_id=ID, source_version=TEXT,
                      **ANALYSIS, **BENCHMARK, **MEASUREMENT,
                      observed_value=nullable(NUMBER), expected_value=nullable(NUMBER),
                      expected_bands=array(obj(label=TEXT, lower=NUMBER, upper=NUMBER)),
                      comparison_group=nullable(HASH), provenance=array(REF, 1),
                      extraction_refs=array(ARTIFACT_REF, 1), missing_fields=array(TEXT),
                      validation_status=STATUS, purpose=PURPOSE),
    'benchmark': obj(**BASE, **BENCHMARK, provenance=array(REF, 1), purpose=PURPOSE),
    'dataset': obj(**BASE, **ANALYSIS, provenance=array(REF, 1), purpose=PURPOSE),
    'observable': obj(**BASE, observable_id=ID, observable_type=OBSERVABLE,
                      definition=TEXT, unit=TEXT, numerator=nullable(TEXT), denominator=nullable(TEXT)),
    'source': obj(**BASE, source_id=ID, source_version=TEXT, title=TEXT, url=TEXT, actual_url=TEXT,
                  retrieved_at=TEXT, sha256=HASH, media_type=TEXT,
                  byte_count={'type': 'integer', 'minimum': 1, 'maximum': 52428800},
                  collaboration=TEXT, analysis_id=ID, published_at=nullable(TEXT),
                  publication_date_precision=enum('DAY', 'MONTH', 'YEAR', 'UNKNOWN'),
                  arxiv_version=nullable(TEXT), journal_ref=nullable(TEXT), doi=nullable(TEXT),
                  inspire_id=nullable(TEXT), hepdata_record_id=nullable(TEXT), hepdata_version=nullable(TEXT),
                  table_ids=array(TEXT), source_relationships=array(REF),
                  historical_evidence=nullable(REF), purpose=PURPOSE),
    'snapshot': obj(**BASE, snapshot_id=ID, cutoff_date=TEXT, created_at=TEXT,
                    status=enum('FROZEN_PARTIAL', 'FROZEN_COMPLETE'),
                    parser_version=TEXT, normalizer_version=TEXT,
                    sources=array(ARTIFACT_REF, 1), artifacts=array(obj(path=TEXT, sha256=HASH), 1),
                    constraint_ids=array(ID, 1),
                    gaps=array(obj(scope=TEXT, status=TEXT, detail=TEXT)),
                    unavailable_receipts=array(ARTIFACT_REF), supersedes=nullable(ID)),
}


def document(kind):
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'urn:sl-collider:' + kind + ':' + VERSION, **deepcopy(SCHEMAS[kind])}
