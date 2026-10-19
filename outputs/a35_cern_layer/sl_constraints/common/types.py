"""Immutable semantic values. Missing evidence is representable, never ready."""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from fractions import Fraction
import re

SCHEMA_VERSION = '1.0.0'


class ContractError(ValueError):
    def __init__(self, code: str, detail: str = ''):
        self.code = code
        super().__init__(f'{code}: {detail}')


class Status(str, Enum):
    READY = 'READY'
    NOT_READY = 'NOT_READY'
    OPEN_OPERATOR = 'OPEN_OPERATOR'
    INVALID = 'INVALID'
    SOURCE_UNAVAILABLE = 'SOURCE_UNAVAILABLE'


def identifier(value: str, *, allow_empty: bool = False) -> str:
    if allow_empty and value == '':
        return value
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ContractError('INVALID_ID')
    if '..' in value:
        raise ContractError('INVALID_ID')
    return value


def nonempty(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError('MISSING_TEXT')


def timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContractError('INVALID_TIMESTAMP') from exc


def version(value: str) -> None:
    if value != SCHEMA_VERSION:
        raise ContractError('SCHEMA_VERSION_UNSUPPORTED', str(value))


def decimal(value: str | int | Decimal) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ContractError('EXACT_NUMBER_REQUIRED')
    if isinstance(value, str) and not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', value):
        raise ContractError('INVALID_NUMBER')
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise ContractError('INVALID_NUMBER') from exc
    if not out.is_finite():
        raise ContractError('NONFINITE_NUMBER')
    # Bounded input prevents absurd exponents from exhausting exact arithmetic.
    if len(out.as_tuple().digits) > 256 or abs(out.as_tuple().exponent) > 1000:
        raise ContractError('NUMBER_LIMIT')
    return out


def exact_decimal(value: Fraction) -> Decimal:
    """Produce a terminating decimal without depending on ambient context."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    if denominator != 1:
        raise ContractError('ROUNDING_REQUIRED')
    places = max(twos, fives)
    integer = value.numerator * 2 ** (places - twos) * 5 ** (places - fives)
    digits = tuple(int(x) for x in str(abs(integer)))
    return decimal(Decimal((int(integer < 0), digits, -places)))


def require_frame(value: str) -> str:
    if value not in ('BARYCENTRIC', 'LAB', 'SEED_REST', 'MATCHING_SURFACE'):
        raise ContractError('INVALID_FRAME', str(value))
    return value


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_version: str
    retrieved_at: str
    source_hash: str
    purpose: str = 'RESEARCH'

    def __post_init__(self):
        identifier(self.source_id, allow_empty=True)
        identifier(self.source_version, allow_empty=True)
        if not isinstance(self.retrieved_at, str) or not isinstance(self.source_hash, str):
            raise ContractError('INVALID_PROVENANCE')
        if self.retrieved_at:
            timestamp(self.retrieved_at)
        if self.source_hash and not re.fullmatch('[0-9a-f]{64}', self.source_hash):
            raise ContractError('INVALID_HASH')
        if self.purpose not in ('RESEARCH', 'TEST_FIXTURE'):
            raise ContractError('INVALID_PURPOSE')

    def readiness_reasons(self) -> tuple[str, ...]:
        return tuple(code for value, code in (
            (self.source_id, 'SOURCE_MISSING'), (self.source_version, 'VERSION_MISSING'),
            (self.retrieved_at, 'RETRIEVED_AT_MISSING'), (self.source_hash, 'HASH_MISSING'),
            (self.purpose != 'TEST_FIXTURE', 'TEST_FIXTURE')) if not value)


@dataclass(frozen=True)
class Uncertainty:
    kind: str = 'UNKNOWN'
    value: Decimal | str | int | None = None
    reason: str = 'not supplied'

    def __post_init__(self):
        if self.kind not in ('EXACT', 'STDDEV', 'VARIANCE', 'UNKNOWN'):
            raise ContractError('INVALID_UNCERTAINTY')
        if self.kind in ('STDDEV', 'VARIANCE'):
            val = decimal(self.value)
            if val < 0:
                raise ContractError('INVALID_UNCERTAINTY')
            object.__setattr__(self, 'value', val)
        elif self.value is not None:
            raise ContractError('INVALID_UNCERTAINTY')
        if self.kind == 'UNKNOWN':
            nonempty(self.reason)


@dataclass(frozen=True)
class ConversionStep:
    from_unit: str
    to_unit: str
    factor_numerator: int
    factor_denominator: int

    def __post_init__(self):
        from .units import UNITS, require_unit
        if not isinstance(self.from_unit, str) or self.from_unit not in UNITS:
            raise ContractError('UNKNOWN_UNIT')
        source = UNITS[self.from_unit]
        target = require_unit(self.to_unit, source[0])
        if type(self.factor_numerator) is not int or type(self.factor_denominator) is not int or self.factor_denominator <= 0:
            raise ContractError('INVALID_CONVERSION')
        if Fraction(self.factor_numerator, self.factor_denominator) != Fraction(source[1]) / Fraction(target[1]):
            raise ContractError('INVALID_CONVERSION')


@dataclass(frozen=True)
class QuantityRecord:
    quantity_id: str
    value: Decimal | str | int | None
    unit: str
    kind: str
    definition: str
    domain_id: str
    provenance: tuple[SourceRef, ...] = ()
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    status: str = 'KNOWN'
    open_reason: str = ''
    conversions: tuple[ConversionStep, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        from .units import require_unit
        version(self.schema_version)
        identifier(self.quantity_id)
        identifier(self.domain_id)
        nonempty(self.definition)
        require_unit(self.unit, self.kind)
        if self.status not in ('KNOWN', 'OPEN'):
            raise ContractError('INVALID_STATUS')
        if self.status == 'OPEN':
            nonempty(self.open_reason)
            if self.value is not None:
                raise ContractError('OPEN_WITH_VALUE')
        else:
            val = decimal(self.value)
            positive = ('MASS', 'MASS_DENSITY', 'TEMPERATURE', 'LENGTH', 'TIME')
            nonnegative = ('NUMBER_DENSITY', 'PRESSURE', 'DIFFUSIVITY', 'COUNT')
            if (self.kind in positive and val <= 0) or (self.kind in nonnegative and val < 0):
                raise ContractError('OUT_OF_RANGE', self.kind)
            object.__setattr__(self, 'value', val)
        if not isinstance(self.uncertainty, Uncertainty):
            raise ContractError('INVALID_UNCERTAINTY')
        for name, typ in (('provenance', SourceRef), ('conversions', ConversionStep)):
            values = tuple(getattr(self, name))
            if not all(isinstance(v, typ) for v in values):
                raise ContractError('INVALID_TYPE', name)
            object.__setattr__(self, name, values)

    def readiness_reasons(self) -> tuple[str, ...]:
        reasons = []
        if self.status == 'OPEN':
            reasons.append('OPEN_VALUE')
        if not self.provenance:
            reasons.append('PROVENANCE_MISSING')
        for ref in self.provenance:
            reasons.extend(ref.readiness_reasons())
        if self.uncertainty.kind == 'UNKNOWN':
            reasons.append('UNCERTAINTY_OPEN')
        return tuple(dict.fromkeys(reasons))


@dataclass(frozen=True)
class StateNode:
    node_id: str
    temperature: QuantityRecord
    number_densities: tuple[tuple[str, QuantityRecord], ...]

    def __post_init__(self):
        identifier(self.node_id)
        entries = tuple(tuple(pair) for pair in self.number_densities)
        if not entries or any(len(pair) != 2 for pair in entries):
            raise ContractError('INVALID_DOMAIN')
        if len({pair[0] for pair in entries}) != len(entries):
            raise ContractError('DUPLICATE_ID')
        for name, quantity in entries:
            identifier(name)
            if not isinstance(quantity, QuantityRecord) or quantity.kind != 'NUMBER_DENSITY' or quantity.unit != 'm^-3':
                raise ContractError('UNIT_MISMATCH')
        if not isinstance(self.temperature, QuantityRecord) or self.temperature.kind != 'TEMPERATURE' or self.temperature.unit != 'K':
            raise ContractError('UNIT_MISMATCH')
        object.__setattr__(self, 'number_densities', entries)


@dataclass(frozen=True)
class Domain:
    """Exact node whitelist, not a bounding-box interpolation permission."""
    domain_id: str
    nodes: tuple[str, ...]
    phase: str
    definition: str
    state_nodes: tuple[StateNode, ...] = ()

    def __post_init__(self):
        identifier(self.domain_id)
        nonempty(self.phase)
        nonempty(self.definition)
        nodes = tuple(self.nodes)
        if not nodes or len(set(nodes)) != len(nodes):
            raise ContractError('INVALID_DOMAIN')
        for node in nodes:
            identifier(node)
        object.__setattr__(self, 'nodes', nodes)
        state_nodes = tuple(self.state_nodes)
        if not all(isinstance(node, StateNode) for node in state_nodes) or len(
                {node.node_id for node in state_nodes}) != len(state_nodes):
            raise ContractError('INVALID_DOMAIN')
        if any(node.node_id not in nodes for node in state_nodes):
            raise ContractError('INVALID_DOMAIN')
        if any(q.domain_id != self.domain_id for node in state_nodes for q in
               (node.temperature,) + tuple(value for _, value in node.number_densities)):
            raise ContractError('STATE_DOMAIN_MISMATCH')
        object.__setattr__(self, 'state_nodes', state_nodes)


@dataclass(frozen=True)
class SnapshotInfo:
    snapshot_id: str
    schema_version: str
    snapshot_date: str
    created_at: str

    def __post_init__(self):
        identifier(self.snapshot_id)
        version(self.schema_version)
        timestamp(self.created_at)
        try:
            cutoff = date.fromisoformat(self.snapshot_date)
            created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00')).astimezone(timezone.utc)
            if created.date() < cutoff:
                raise ValueError()
        except (TypeError, ValueError) as exc:
            raise ContractError('INVALID_DATE') from exc


@dataclass(frozen=True)
class ValidationReport:
    valid_structure: bool
    status: Status
    codes: tuple[str, ...] = ()
