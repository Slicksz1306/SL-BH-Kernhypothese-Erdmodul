"""Closed wire contracts. No automatic coercion, downloads or remote schema refs."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
import re
from typing import ClassVar

from jsonschema import Draft202012Validator
from ..common.types import ContractError, timestamp
from ..common.provenance import canonical_bytes
from .schema_document import SCHEMAS, document


def check_schemas():
    for kind in SCHEMAS:
        Draft202012Validator.check_schema(document(kind))


def exact(value):
    if type(value) is not str or len(value) > 128 or not re.fullmatch(
            r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', value):
        raise ContractError('INVALID_DECIMAL', 'exact decimal string required')
    result = Decimal(value)
    if not result.is_finite() or abs(result.as_tuple().exponent) > 1000:
        raise ContractError('RESOURCE_LIMIT', 'decimal exponent')
    return result


def validate(kind, data):
    errors = sorted(Draft202012Validator(document(kind)).iter_errors(data), key=lambda e: str(e.path))
    if errors:
        raise ContractError('SCHEMA_INVALID', str(list(errors[0].path)) + ': ' + errors[0].message[:300])
    if kind == 'source':
        timestamp(data['retrieved_at'])
        if data['published_at'] is not None:
            try:
                date.fromisoformat(data['published_at'])
            except ValueError as exc:
                raise ContractError('INVALID_DATE') from exc
    if kind in ('constraint', 'dataset'):
        for name, unit in [('sqrt_s', 'TeV'), ('luminosity', 'fb^-1')]:
            q = data[name]
            if q['unit'] != unit:
                raise ContractError('UNIT_MISMATCH', name)
            if q['value'] is not None and exact(q['value']) <= 0:
                raise ContractError('INVALID_QUANTITY', name)
    if kind == 'constraint':
        cl = data['confidence_level']
        if cl is not None and not 0 < exact(cl) < 1:
            raise ContractError('INVALID_CL')
        units = {'MASS_THRESHOLD': 'TeV', 'SIGMA': 'fb', 'SIGMA_TIMES_BR': 'fb',
                 'SIGMA_TIMES_ACCEPTANCE': 'fb', 'SPHALERON_FRACTION': '1',
                 'EVENT_FRACTION': '1', 'DIMENSIONLESS_PARAMETER': '1'}
        if data['unit'] is not None and data['observable_type'] in units and data['unit'] != units[data['observable_type']]:
            raise ContractError('UNIT_MISMATCH', data['observable_type'])
        if data['object_class'] == 'SPHALERON' and data['observable_type'] == 'MASS_THRESHOLD':
            raise ContractError('OBSERVABLE_MISMATCH', 'transition energy is not a mass exclusion')
        for key in ('observed_value', 'expected_value'):
            if data[key] is not None:
                value = exact(data[key])
                if value < 0 or (data['observable_type'] in ('EVENT_FRACTION', 'SPHALERON_FRACTION') and value > 1):
                    raise ContractError('INVALID_LIMIT', key)
        if data['observable_type'] == 'MASS_THRESHOLD' and data['limit_type'] != 'LOWER_BOUND':
            raise ContractError('OBSERVABLE_MISMATCH', 'mass lower bound required')
        for band in data['expected_bands']:
            if not 0 <= exact(band['lower']) <= exact(band['upper']):
                raise ContractError('INVALID_BAND')
        if not any(p['source_id'] == data['source_id'] and p['source_version'] == data['source_version'] for p in data['provenance']):
            raise ContractError('PROVENANCE_MISMATCH')
    if kind in ('constraint', 'benchmark'):
        names = [p['name'] for p in data['model_parameters']]
        if len(set(names)) != len(names):
            raise ContractError('DUPLICATE_PARAMETER')
        for p in data['model_parameters']:
            if p['value'] is not None:
                exact(p['value'])


@dataclass(frozen=True)
class WireRecord:
    _json: str
    kind: ClassVar[str]

    def __post_init__(self):
        validate(self.kind, json.loads(self._json))

    @classmethod
    def from_dict(cls, value):
        validate(cls.kind, value)
        return cls(canonical_bytes(value).decode('utf-8'))

    def to_dict(self):
        return json.loads(self._json)


class ConstraintRecord(WireRecord):
    kind = 'constraint'


class BenchmarkDefinition(WireRecord):
    kind = 'benchmark'


class DatasetRecord(WireRecord):
    kind = 'dataset'


class SourceRecord(WireRecord):
    kind = 'source'


class ObservableDefinition(WireRecord):
    kind = 'observable'


class SnapshotManifest(WireRecord):
    kind = 'snapshot'
