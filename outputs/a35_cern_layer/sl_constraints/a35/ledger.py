"""Exact source/sink accounting with an explicit transition-region reservoir.

No integration, capture, reaction, Q_m matching, or mass-energy conversion.
Caller owns physical event identity: renaming both an event and its group
cannot be detected from numbers alone. Shared physical events MUST share IDs.
"""
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from ..common.types import (ContractError, QuantityRecord, SourceRef, Status,
                            Uncertainty, identifier, nonempty, require_frame, exact_decimal)
from .material import Species, require_quantity

RESERVOIRS = frozenset(('outer_material', 'transition_region', 'seed', 'radiation', 'bath', 'external'))
KINDS = MappingProxyType({
    'MASS': ('MASS', 'kg', 'AMOUNT'), 'CHARGE': ('CHARGE', 'C', 'AMOUNT'),
    'ENERGY': ('ENERGY', 'J', 'AMOUNT'), 'MASS_RATE': ('MASS', 'kg/s', 'RATE'),
    'CURRENT': ('CHARGE', 'A', 'RATE'), 'POWER': ('ENERGY', 'W', 'RATE'),
})


@dataclass(frozen=True)
class OperatorRef:
    operator_id: str
    operator_version: str
    provenance: tuple[SourceRef, ...]
    definition: str

    def __post_init__(self):
        identifier(self.operator_id)
        identifier(self.operator_version)
        nonempty(self.definition)
        object.__setattr__(self, 'provenance', tuple(self.provenance))
        if not all(isinstance(ref, SourceRef) for ref in self.provenance):
            raise ContractError('INVALID_PROVENANCE')


@dataclass(frozen=True)
class SpeciesMovement:
    species: Species
    count: QuantityRecord

    def __post_init__(self):
        if not isinstance(self.species, Species) or not isinstance(self.count, QuantityRecord):
            raise ContractError('SPECIES_BASIS_MISMATCH')
        unit = {'COUNT': 'particle', 'PARTICLE_RATE': 'particle/s'}.get(self.count.kind)
        if unit is None or require_quantity(self.count, self.count.kind, unit) <= 0:
            raise ContractError('INVALID_TRANSFER')


@dataclass(frozen=True)
class Transfer:
    channel_id: str
    event_id: str
    quantity: QuantityRecord
    source: str
    target: str
    sign: int
    frame: str
    operator: OperatorRef
    double_count_group: str
    external: bool = False
    energy_convention: str = ''
    species_movement: SpeciesMovement | None = None

    def __post_init__(self):
        for name in ('channel_id', 'event_id', 'double_count_group'):
            identifier(getattr(self, name))
        if self.source not in RESERVOIRS or self.target not in RESERVOIRS:
            raise ContractError('UNKNOWN_RESERVOIR')
        if self.source == self.target or type(self.sign) is not int or self.sign not in (-1, 1):
            raise ContractError('INVALID_TRANSFER')
        if type(self.external) is not bool or self.external != ('external' in (self.source, self.target)):
            raise ContractError('EXTERNAL_MARKER_REQUIRED')
        require_frame(self.frame)
        if not isinstance(self.operator, OperatorRef):
            raise ContractError('INVALID_OPERATOR')
        if not isinstance(self.quantity, QuantityRecord) or self.quantity.kind not in KINDS:
            raise ContractError('LEDGER_QUANTITY_UNSUPPORTED')
        observable, unit, _ = KINDS[self.quantity.kind]
        amount = require_quantity(self.quantity, self.quantity.kind, unit)
        if observable != 'CHARGE' and amount < 0:
            raise ContractError('INVALID_TRANSFER', 'use explicit sign to reverse mass/energy')
        if observable == 'ENERGY' and not self.energy_convention.strip():
            raise ContractError('ENERGY_CONVENTION_REQUIRED')
        if self.species_movement is not None:
            if not isinstance(self.species_movement, SpeciesMovement) or observable == 'ENERGY':
                raise ContractError('INVALID_SPECIES_TRANSFER')
            movement = self.species_movement
            expected_mode = 'AMOUNT' if movement.count.kind == 'COUNT' else 'RATE'
            if self.mode != expected_mode:
                raise ContractError('AMOUNT_RATE_MISMATCH')
            if len({q.domain_id for q in movement.species.quantities()} | {
                    movement.count.domain_id, self.quantity.domain_id}) != 1:
                raise ContractError('STATE_DOMAIN_MISMATCH')
            factor = (Fraction(movement.species.bookkeeping_mass.value) if observable == 'MASS'
                      else Fraction(movement.species.charge_number.value) * Fraction('1.602176634e-19'))
            if amount != Fraction(movement.count.value) * factor:
                raise ContractError('INCONSISTENT_SPECIES_TRANSFER')

    @property
    def observable(self):
        return KINDS[self.quantity.kind][0]

    @property
    def mode(self):
        return KINDS[self.quantity.kind][2]


@dataclass(frozen=True)
class Posting:
    channel_id: str
    reservoir: str
    observable: str
    amount: Fraction
    unit: str
    mode: str

    def __post_init__(self):
        identifier(self.channel_id)
        if self.reservoir not in RESERVOIRS or self.observable not in ('MASS', 'CHARGE', 'ENERGY'):
            raise ContractError('INVALID_POSTING')
        if not isinstance(self.amount, Fraction):
            raise ContractError('EXACT_NUMBER_REQUIRED')
        if (self.observable, self.unit, self.mode) not in KINDS.values():
            raise ContractError('UNIT_MISMATCH')


@dataclass(frozen=True)
class LedgerAudit:
    valid: bool
    codes: tuple[str, ...]
    residuals: tuple[tuple[str, Fraction], ...]
    external: tuple[tuple[str, Fraction], ...]

    def external_contribution(self, observable: str) -> Fraction:
        return dict(self.external)[observable]


@dataclass(frozen=True)
class Balance:
    reservoir: str
    kind: str
    unit: str
    value: Fraction
    frame: str
    domain_id: str
    definition: str


@dataclass(frozen=True)
class TransferLedger:
    transfers: tuple[Transfer, ...]

    def __post_init__(self):
        transfers = tuple(self.transfers)
        object.__setattr__(self, 'transfers', transfers)
        if not all(isinstance(t, Transfer) for t in transfers):
            raise ContractError('INVALID_TRANSFER')
        channels, signatures, bundles = set(), [], {}
        for transfer in transfers:
            # Factory-created mass and charge use separate channel IDs.
            if transfer.channel_id in channels:
                raise ContractError('DUPLICATE_CHANNEL')
            channels.add(transfer.channel_id)
            boundary = tuple(sorted((transfer.source, transfer.target)))
            group = (transfer.double_count_group, boundary, transfer.observable)
            event = (transfer.event_id, boundary, transfer.observable)
            component = transfer.species_movement.species.species_id if transfer.species_movement else None
            for prior_group, prior_event, prior_component in signatures:
                if (group == prior_group or event == prior_event) and (
                        component is None or prior_component is None or component == prior_component):
                    raise ContractError('DOUBLE_COUNT')
            signatures.append((group, event, component))
            if transfer.species_movement:
                key = (transfer.event_id, transfer.source, transfer.target, component)
                bundle = bundles.setdefault(key, [])
                bundle.append(transfer)
        for bundle in bundles.values():
            if {t.observable for t in bundle} != {'MASS', 'CHARGE'} or len(bundle) != 2:
                raise ContractError('SPECIES_COUNTERCHANNEL_MISSING')
            first, second = bundle
            if (first.species_movement != second.species_movement or first.sign != second.sign or
                    first.double_count_group != second.double_count_group or first.operator != second.operator):
                raise ContractError('INCONSISTENT_SPECIES_TRANSFER')
        if len({t.mode for t in transfers}) > 1:
            raise ContractError('AMOUNT_RATE_MISMATCH')
        if len({t.frame for t in transfers}) > 1:
            raise ContractError('FRAME_MISMATCH')
        if len({t.quantity.domain_id for t in transfers}) > 1:
            raise ContractError('STATE_DOMAIN_MISMATCH')
        if len({t.energy_convention for t in transfers if t.observable == 'ENERGY'}) > 1:
            raise ContractError('ENERGY_CONVENTION_MISMATCH')

    @property
    def mode(self):
        return self.transfers[0].mode if self.transfers else 'AMOUNT'

    @property
    def postings(self) -> tuple[Posting, ...]:
        entries = []
        for transfer in self.transfers:
            amount = Fraction(transfer.quantity.value) * transfer.sign
            for reservoir, factor in ((transfer.source, -1), (transfer.target, 1)):
                entries.append(Posting(transfer.channel_id, reservoir, transfer.observable,
                                       amount * factor, transfer.quantity.unit, transfer.mode))
        return tuple(entries)

    def change(self, reservoir: str, observable: str) -> Fraction:
        if reservoir not in RESERVOIRS or observable not in ('MASS', 'CHARGE', 'ENERGY'):
            raise ContractError('INVALID_BALANCE_QUERY')
        return sum((p.amount for p in self.postings if p.reservoir == reservoir and p.observable == observable),
                   Fraction(0))

    def balance(self, reservoir: str, observable: str) -> Balance:
        value = self.change(reservoir, observable)
        if not self.transfers:
            raise ContractError('EMPTY_LEDGER_CONTEXT')
        kind, (_, unit, _) = next((k, v) for k, v in KINDS.items() if v[0] == observable and v[2] == self.mode)
        first = self.transfers[0]
        return Balance(reservoir, kind, unit, value, first.frame, first.quantity.domain_id,
                       'Exact reservoir increment' if self.mode == 'AMOUNT' else 'Exact reservoir time derivative')

    def _population_change(self, reservoir, key, by_element=False):
        if reservoir not in RESERVOIRS or not self.transfers:
            raise ContractError('INVALID_BALANCE_QUERY')
        identifier(key)
        total = Fraction(0)
        for transfer in self.transfers:
            movement = transfer.species_movement
            if movement is None or transfer.observable != 'MASS':
                continue
            identity = movement.species.element_id if by_element else movement.species.species_id
            if identity == key:
                factor = int(transfer.target == reservoir) - int(transfer.source == reservoir)
                total += factor * transfer.sign * Fraction(movement.count.value)
        first = self.transfers[0]
        return Balance(reservoir, 'COUNT' if self.mode == 'AMOUNT' else 'PARTICLE_RATE',
                       'particle' if self.mode == 'AMOUNT' else 'particle/s', total,
                       first.frame, first.quantity.domain_id, ('Element ' if by_element else 'Species ') + key)

    def species_change(self, reservoir: str, species_id: str) -> Balance:
        return self._population_change(reservoir, species_id)

    def element_change(self, reservoir: str, element_id: str) -> Balance:
        return self._population_change(reservoir, element_id, True)

    def require_stationary_transition(self):
        if any(self.change('transition_region', kind) for kind in ('MASS', 'CHARGE', 'ENERGY')):
            raise ContractError('NONSTATIONARY_TRANSITION')
        ids = {t.species_movement.species.species_id for t in self.transfers if t.species_movement}
        if any(self.species_change('transition_region', key).value for key in ids):
            raise ContractError('NONSTATIONARY_TRANSITION')

    def audit(self, postings: tuple[Posting, ...] | None = None) -> LedgerAudit:
        entries = self.postings if postings is None else tuple(postings)
        if not all(isinstance(p, Posting) for p in entries):
            raise ContractError('INVALID_POSTING')
        codes = []
        if Counter(entries) != Counter(self.postings):
            codes.append('COUNTERENTRY_MISMATCH')
        if any(p.mode != self.mode for p in entries):
            codes.append('AMOUNT_RATE_MISMATCH')
        residuals, external = [], []
        for observable in ('MASS', 'CHARGE', 'ENERGY'):
            total = sum((p.amount for p in entries if p.observable == observable), Fraction(0))
            source = -sum((p.amount for p in entries if p.observable == observable and
                           p.reservoir == 'external'), Fraction(0))
            residuals.append((observable, total))
            external.append((observable, source))
            if total:
                codes.append('CONSERVATION_FAIL:' + observable)
        return LedgerAudit(not codes, tuple(codes), tuple(residuals), tuple(external))

    @property
    def scientific_status(self):
        # Arithmetic correctness never certifies external physical operators.
        return Status.NOT_READY

    @property
    def provenance_reasons(self):
        reasons = []
        for transfer in self.transfers:
            reasons.extend(transfer.quantity.readiness_reasons())
            if not transfer.operator.provenance:
                reasons.append('PROVENANCE_MISSING')
            for ref in transfer.operator.provenance:
                reasons.extend(ref.readiness_reasons())
        return tuple(dict.fromkeys(reasons))


def species_transfer(species: Species, count: QuantityRecord, *, channel_id: str, event_id: str,
                     source: str, target: str, operator: OperatorRef, double_count_group: str,
                     frame: str, sign: int = 1, external: bool = False) -> tuple[Transfer, ...]:
    """Derive both mass and charge for ONE species event. Energy is not inferred.

    e = 1.602176634e-19 C is the exact SI elementary-charge definition.
    Uncertainty is left OPEN unless all inputs are exact (no covariance guessed).
    """
    if count.kind == 'COUNT':
        amount = require_quantity(count, 'COUNT', 'particle')
        mass_kind, mass_unit, charge_kind, charge_unit = 'MASS', 'kg', 'CHARGE', 'C'
    elif count.kind == 'PARTICLE_RATE':
        amount = require_quantity(count, 'PARTICLE_RATE', 'particle/s')
        mass_kind, mass_unit, charge_kind, charge_unit = 'MASS_RATE', 'kg/s', 'CURRENT', 'A'
    else:
        raise ContractError('UNIT_MISMATCH')
    if amount <= 0:
        raise ContractError('INVALID_TRANSFER', 'omit zero event; direction uses sign')
    inputs = (count, species.bookkeeping_mass, species.charge_number)
    if len({v.domain_id for v in inputs}) != 1:
        raise ContractError('STATE_DOMAIN_MISMATCH')
    provenance = tuple(dict.fromkeys(ref for item in inputs for ref in item.provenance))
    exact = all(item.uncertainty.kind == 'EXACT' for item in inputs)
    uncertainty = Uncertainty('EXACT') if exact else Uncertainty(reason='covariance propagation not supplied')
    mass = amount * require_quantity(species.bookkeeping_mass, 'MASS', 'kg')
    charge = amount * require_quantity(species.charge_number, 'DIMENSIONLESS', '1') * Fraction('1.602176634e-19')

    def derived(suffix, value, unit, kind, formula):
        return QuantityRecord(channel_id + '_' + suffix, exact_decimal(value), unit, kind,
                              f'{formula}; species={species.species_id}; parents={count.quantity_id},'
                              f'{species.bookkeeping_mass.quantity_id},{species.charge_number.quantity_id}; '
                              'foundation formula v1; SI exact e', count.domain_id, provenance, uncertainty)

    mass_quantity = derived('mass', mass, mass_unit, mass_kind, 'N_s*m_s')
    charge_quantity = derived('charge', charge, charge_unit, charge_kind, 'N_s*z_s*e')
    return tuple(Transfer(channel_id + '_' + suffix, event_id, quantity, source, target,
                          sign, frame, operator, double_count_group, external,
                          species_movement=SpeciesMovement(species, count))
                 for suffix, quantity in (('mass', mass_quantity), ('charge', charge_quantity)))
