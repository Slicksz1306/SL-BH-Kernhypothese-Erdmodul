"""Closed wire-contract validator, not a general JSON Schema interpreter."""
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
import json
from .types import (ContractError, QuantityRecord, SourceRef, Uncertainty,
                    ConversionStep, SnapshotInfo, ValidationReport, Status)


def _construct(cls, payload):
    if not isinstance(payload, dict):
        raise ContractError('OBJECT_REQUIRED')
    if set(payload) - {f.name for f in fields(cls)}:
        raise ContractError('UNKNOWN_FIELD')
    try:
        return cls(**payload)
    except TypeError as exc:
        raise ContractError('MISSING_OR_INVALID_FIELD') from exc


def quantity_from_dict(payload: dict) -> QuantityRecord:
    if not isinstance(payload, dict):
        raise ContractError('OBJECT_REQUIRED')
    required = {'schema_version', 'quantity_id', 'value', 'unit', 'kind',
                'definition', 'domain_id', 'provenance', 'status', 'uncertainty'}
    if not required <= payload.keys():
        raise ContractError('MISSING_FIELD')
    data = dict(payload)
    for name in ('provenance', 'conversions'):
        if name in data and not isinstance(data[name], list):
            raise ContractError('ARRAY_REQUIRED', name)
    data['provenance'] = tuple(_construct(SourceRef, p) for p in data['provenance'])
    data['uncertainty'] = _construct(Uncertainty, data['uncertainty'])
    data['conversions'] = tuple(_construct(ConversionStep, p) for p in data.get('conversions', []))
    return _construct(QuantityRecord, data)


def validate_schema(payload: dict, schema_id: str = 'quantity') -> ValidationReport:
    try:
        if schema_id == 'quantity':
            obj = quantity_from_dict(payload)
            reasons = obj.readiness_reasons()
        elif schema_id == 'snapshot_info':
            _construct(SnapshotInfo, payload)
            reasons = ()
        else:
            raise ContractError('UNKNOWN_SCHEMA')
        return ValidationReport(True, Status.NOT_READY if reasons else Status.READY, reasons)
    except ContractError as exc:
        return ValidationReport(False, Status.INVALID, (exc.code,))


def parse_json(text: str):
    """Reject duplicate keys, bare floating point, nonfinite tokens, and oversize input."""
    if not isinstance(text, str) or len(text.encode('utf-8')) > 1024 * 1024:
        raise ContractError('RESOURCE_LIMIT')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError('DUPLICATE_FIELD', key)
            result[key] = value
        return result

    def reject_number(_):
        raise ContractError('EXACT_NUMBER_REQUIRED', 'encode physical decimal values as strings')

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_float=reject_number, parse_constant=reject_number)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError('INVALID_JSON') from exc


def to_wire(value):
    """Explicit serializer for declared dataclasses; never imports from data."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_wire(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, tuple):
        return [to_wire(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ContractError('UNSUPPORTED_WIRE_TYPE')
