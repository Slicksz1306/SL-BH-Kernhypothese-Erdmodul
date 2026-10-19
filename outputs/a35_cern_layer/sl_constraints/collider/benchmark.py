"""Conservative SAME_DATASET identity guard, NOT a numeric comparison engine."""
from hashlib import sha256
from ..common.types import ContractError
from ..common.provenance import canonical_bytes
from .contracts import ConstraintRecord

KEY_FIELDS = ('object_class', 'model_family', 'model_version', 'n_extra_dimensions',
              'model_parameters', 'assumptions', 'validity_domain', 'channel_id',
              'selection_id', 'observable_type', 'observable_definition', 'limit_type',
              'confidence_level', 'statistical_method', 'unit', 'sqrt_s',
              'dataset_id', 'luminosity', 'data_period')


def _missing(value, path=''):
    if value is None:
        return [path]
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in _missing(v, path + '.' + k if path else k)]
    if isinstance(value, list):
        result = []
        for i, v in enumerate(value):
            # A declared scan axis may have no point coordinate for a threshold limit.
            if isinstance(v, dict) and v.get('role') == 'SCAN':
                v = {k: x for k, x in v.items() if k != 'value'}
            result.extend(_missing(v, f'{path}[{i}]'))
        return result
    return []


def semantic_key(record):
    data = ConstraintRecord.from_dict(record).to_dict()
    key = {k: data[k] for k in KEY_FIELDS}
    key['model_parameters'] = sorted(key['model_parameters'], key=lambda p: p['name'])
    if _missing(key):
        return None
    return key


def comparison_group(key):
    if key is None or _missing(key):
        raise ContractError('COMPARISON_REFUSED', 'incomplete key')
    return sha256(canonical_bytes(key)).hexdigest()


def normalize_identity(record):
    data = ConstraintRecord.from_dict(record).to_dict()
    key = semantic_key(data)
    data['comparison_group'] = comparison_group(key) if key is not None else None
    fields = {k: data[k] for k in (*KEY_FIELDS, 'observed_value', 'expected_value', 'publication_date')}
    data['missing_fields'] = sorted(_missing(fields))
    if data['missing_fields']:
        data['validation_status'] = 'INCOMPLETE'
    return data


def validate_constraint(record):
    data = normalize_identity(record)
    if record['comparison_group'] != data['comparison_group']:
        raise ContractError('FINGERPRINT_MISMATCH')
    return {'valid': True, 'missing_fields': data['missing_fields']}


def require_compatible(left, right):
    for record in (left, right):
        validate_constraint(record)
    a, b = semantic_key(left), semantic_key(right)
    if a is None or b is None or a != b:
        raise ContractError('COMPARISON_REFUSED')
