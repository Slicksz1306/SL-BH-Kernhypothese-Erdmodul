"""Exact scalar normalization and evidence cross-checks; no recast or limit ranking."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP, localcontext
from hashlib import sha256
from ..common.types import ContractError
from ..common.provenance import canonical_bytes
from .contracts import exact
from .benchmark import normalize_identity

NORMALIZER_VERSION = '1.0.0'


def convert(value, unit, target):
    parsed = exact(value)
    units = {'GeV', 'TeV', 'pb', 'fb', 'pb^-1', 'fb^-1', '1'}
    if unit not in units or target not in units:
        raise ContractError('UNIT_MISMATCH')
    factors = {('GeV', 'TeV'): Decimal('0.001'), ('pb', 'fb'): Decimal('1000'),
               ('pb^-1', 'fb^-1'): Decimal('0.001')}
    if unit == target:
        return value
    if (unit, target) not in factors:
        raise ContractError('UNIT_MISMATCH')
    with localcontext() as context:
        context.prec = 2048
        result = parsed * factors[unit, target]
    text = format(result, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def crosscheck(paper, table, *, paper_unit, table_unit, rounding_places=None, rounding_evidence=None):
    if paper is None or table is None:
        return 'SOURCE_MISSING'
    if paper_unit != table_unit:
        return 'NOT_COMPARABLE'
    a, b = exact(paper), exact(table)
    if a == b:
        return 'MATCH'
    if rounding_places is not None:
        if not rounding_evidence or type(rounding_places) is not int or not 0 <= rounding_places <= 12:
            raise ContractError('ROUNDING_POLICY_REQUIRED')
        with localcontext() as context:
            context.prec = 2048
            quantum = Decimal(1).scaleb(-rounding_places)
            if a == b.quantize(quantum, rounding=ROUND_HALF_UP):
                return 'ROUNDING_MATCH'
    return 'MISMATCH'


def normalize_reviewed(template, observed, expected):
    """Explicit reviewed scalar input; remains PROPOSED/INCOMPLETE, never auto-accepted."""
    data = deepcopy(template)
    data.update(observed_value=observed, expected_value=expected, validation_status='PROPOSED')
    return normalize_identity(data)


def normalize_cell(template, extraction, index):
    binding = extraction['binding']
    if len(extraction['cells']) != 1:
        raise ContractError('MULTIPOINT_UNSUPPORTED', 'explicit reviewed point mapping required')
    if type(index) is not int or index != 0:
        raise ContractError('INVALID_CELL_INDEX')
    role = binding.get('limit_role')
    if role not in ('OBSERVED', 'EXPECTED'):
        raise ContractError('LIMIT_ROLE_REQUIRED')
    if any(template[k] != binding[k] for k in ('benchmark_id', 'channel_id', 'observable_type', 'unit')):
        raise ContractError('BENCHMARK_MISMATCH')
    if template['source_id'] != extraction['source_id'] or template['source_version'] != extraction['source_version']:
        raise ContractError('SOURCE_CHANGED')
    cell = extraction['cells'][index]
    data = deepcopy(template)
    axes = extraction['table']['independent_variables']
    mapping = binding.get('axis_parameters', {})
    names = [axis['header']['name'] for axis in axes]
    if len(set(names)) != len(names) or set(mapping) != set(names):
        raise ContractError('AXIS_BINDING_REQUIRED')
    coordinates = {}
    for axis in axes:
        spec = mapping[axis['header']['name']]
        if not isinstance(spec, dict) or set(spec) != {'name', 'unit'}:
            raise ContractError('AXIS_BINDING_REQUIRED')
        parameters = [p for p in data['model_parameters'] if p['name'] == spec['name']]
        if len(parameters) != 1 or spec['name'] in coordinates:
            raise ContractError('AXIS_BINDING_REQUIRED')
        values = axis['values']
        if len(values) != 1 or set(values[0]) != {'value'}:
            raise ContractError('AXIS_BINDING_REQUIRED', 'scalar coordinate required')
        from .extraction import parse_cell
        value, status = parse_cell(values[0]['value'])
        if status != 'PARSED':
            raise ContractError('AXIS_BINDING_REQUIRED', 'censored coordinate')
        value = convert(value, axis['header'].get('units', '1'), spec['unit'])
        parameter = parameters[0]
        if parameter['role'] == 'FIXED' and parameter['value'] is not None and exact(parameter['value']) != exact(value):
            raise ContractError('BENCHMARK_MISMATCH', 'fixed coordinate')
        parameter['value'] = value
        coordinates[spec['name']] = {'value': value, 'unit': spec['unit']}
    data['constraint_id'] = data['constraint_id'][:95] + '_' + sha256(canonical_bytes(coordinates)).hexdigest()[:24]
    data['provenance'] = [{'source_id': extraction['source_id'], 'source_version': extraction['source_version'],
                           'sha256': extraction['source_hash'], 'locator': cell['locator']}]
    data['extraction_refs'] = [{'artifact_id': extraction['artifact_id'], 'sha256': sha256(canonical_bytes(extraction)).hexdigest()}]
    return normalize_reviewed(data, cell['parsed_value'] if role == 'OBSERVED' else None,
                             cell['parsed_value'] if role == 'EXPECTED' else None)


def audit_coverage(records, required_scope):
    """Explicit semantic tuples, not counts. Each requirement must be independently met."""
    present = {(r['analysis_id'], r['benchmark_id'], r['channel_id'], r['observable_type']): normalize_identity(r) for r in records}
    if len(present) != len(records):
        raise ContractError('DUPLICATE_CONSTRAINT_SCOPE')
    gaps = []
    for item in required_scope:
        key = tuple(item[k] for k in ('analysis_id', 'benchmark_id', 'channel_id', 'observable_type'))
        row = present.get(key)
        if (row is None or row['observed_value'] is None or row['expected_value'] is None or row['missing_fields']
                or row['purpose'] != 'RESEARCH' or row['validation_status'] != 'ACCEPTED'):
            gaps.append({'scope': '/'.join(key), 'status': 'INCOMPLETE', 'detail': 'Missing record, scalar, defining metadata or scientific acceptance'})
    return {'status': 'COMPLETE' if required_scope and not gaps else 'PARTIAL', 'gaps': gaps}
