"""A0 -> A35 foundation contract. Validation is not a physical closure claim."""
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal
import numpy as np
from ..common.types import (QuantityRecord, SourceRef, Domain, ContractError, Status,
                            identifier, nonempty, require_frame, timestamp, version)
from ..common.provenance import SourceRecord, DerivationRecord, LocalSourceStore, validate_derivations
from ..common.numerics import matrix_threshold


def require_signature(q: QuantityRecord, kind: str, unit: str):
    if not isinstance(q, QuantityRecord):
        raise ContractError('QUANTITY_REQUIRED')
    if q.kind != kind or q.unit != unit:
        raise ContractError('UNIT_MISMATCH', f'explicit {unit} / {kind} required')


def require_quantity(q: QuantityRecord, kind: str, unit: str) -> Fraction:
    require_signature(q, kind, unit)
    if q.value is None:
        raise ContractError('OPEN_VALUE')
    return Fraction(q.value)


@dataclass(frozen=True)
class TensorRecord:
    values: tuple[tuple[QuantityRecord, ...], ...]
    axes: tuple[tuple[str, ...], tuple[str, ...]]
    definition: str

    def __post_init__(self):
        values = tuple(tuple(row) for row in self.values)
        axes = tuple(tuple(axis) for axis in self.axes)
        nonempty(self.definition)
        if len(axes) != 2 or not all(axes) or len(values) != len(axes[0]) or any(
                len(row) != len(axes[1]) for row in values):
            raise ContractError('MATRIX_SHAPE_MISMATCH')
        for axis in axes:
            if len(set(axis)) != len(axis):
                raise ContractError('DUPLICATE_AXIS')
            for label in axis:
                identifier(label)
        flat = tuple(q for row in values for q in row)
        if not all(isinstance(q, QuantityRecord) for q in flat):
            raise ContractError('QUANTITY_REQUIRED')
        if len({(q.unit, q.kind, q.domain_id) for q in flat}) != 1:
            raise ContractError('TENSOR_CONVENTION_MISMATCH')
        object.__setattr__(self, 'values', values)
        object.__setattr__(self, 'axes', axes)

    def quantities(self):
        return tuple(q for row in self.values for q in row)

    def rational(self, kind: str, unit: str):
        return tuple(tuple(require_quantity(q, kind, unit) for q in row) for row in self.values)


@dataclass(frozen=True)
class Species:
    species_id: str
    element_id: str
    bookkeeping_mass: QuantityRecord
    charge_number: QuantityRecord
    number_density: QuantityRecord

    def __post_init__(self):
        identifier(self.species_id)
        identifier(self.element_id)
        require_quantity(self.bookkeeping_mass, 'MASS', 'kg')
        z = require_quantity(self.charge_number, 'DIMENSIONLESS', '1')
        require_quantity(self.number_density, 'NUMBER_DENSITY', 'm^-3')
        if z.denominator != 1:
            raise ContractError('CHARGE_BASIS_INVALID')

    def quantities(self):
        return (self.bookkeeping_mass, self.charge_number, self.number_density)


@dataclass(frozen=True)
class MaterialState:
    species: tuple[Species, ...]
    temperature: QuantityRecord
    frame: str
    domain_id: str
    node_id: str
    phase: str
    density: QuantityRecord | None = None
    density_role: Literal['DERIVED', 'VALIDATION', 'INPUT'] = 'DERIVED'
    temperature_convention: str = 'UNVERIFIED'
    potential_convention: str = 'UNVERIFIED'

    def __post_init__(self):
        object.__setattr__(self, 'species', tuple(self.species))
        require_quantity(self.temperature, 'TEMPERATURE', 'K')
        require_frame(self.frame)
        identifier(self.domain_id)
        identifier(self.node_id)
        nonempty(self.phase)
        if self.density_role not in ('DERIVED', 'VALIDATION', 'INPUT'):
            raise ContractError('INVALID_STATE_ROLE')

    def quantities(self):
        return (self.temperature,) + tuple(q for s in self.species for q in s.quantities()) + (
            (self.density,) if self.density is not None else ())


def _species_basis(species):
    if len(species) < 2 or not all(isinstance(s, Species) for s in species):
        raise ContractError('SPECIES_BASIS_MISMATCH')
    ids = tuple(s.species_id for s in species)
    if len(set(ids)) != len(ids):
        raise ContractError('SPECIES_BASIS_MISMATCH')
    return ids


def validate_state(state: MaterialState) -> Fraction:
    _species_basis(state.species)
    if state.frame != 'BARYCENTRIC':
        raise ContractError('FRAME_TRANSFORM_REQUIRED')
    if any(q.domain_id != state.domain_id for q in state.quantities()):
        raise ContractError('STATE_DOMAIN_MISMATCH')
    density = sum((require_quantity(s.bookkeeping_mass, 'MASS', 'kg') *
                   require_quantity(s.number_density, 'NUMBER_DENSITY', 'm^-3')
                   for s in state.species), Fraction(0))
    if density <= 0:
        raise ContractError('INCONSISTENT_STATE', 'empty mixture')
    if state.density is not None:
        if state.density_role == 'INPUT':
            raise ContractError('REDUNDANT_STATE', 'T and n_s are the independent coordinates')
        if require_quantity(state.density, 'MASS_DENSITY', 'kg/m^3') != density:
            raise ContractError('INCONSISTENT_STATE', 'rho != sum(m_s*n_s)')
    return density


@dataclass(frozen=True)
class TransportContract:
    species_order: tuple[str, ...]
    reduced_order: tuple[str, ...]
    projector: TensorRecord
    mobility: TensorRecord
    frame: str
    force_convention: str
    flux_convention: str
    domain_id: str

    def __post_init__(self):
        object.__setattr__(self, 'species_order', tuple(self.species_order))
        object.__setattr__(self, 'reduced_order', tuple(self.reduced_order))
        require_frame(self.frame)
        identifier(self.domain_id)
        if not isinstance(self.projector, TensorRecord) or not isinstance(self.mobility, TensorRecord):
            raise ContractError('INVALID_TRANSPORT')

    def quantities(self):
        return self.projector.quantities() + self.mobility.quantities()


def _rank(matrix):
    work = [list(row) for row in matrix]
    rank = 0
    for column in range(len(work[0])):
        pivot = next((r for r in range(rank, len(work)) if work[r][column]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        factor = work[rank][column]
        work[rank] = [x / factor for x in work[rank]]
        for row in range(rank + 1, len(work)):
            factor = work[row][column]
            work[row] = [x - factor * y for x, y in zip(work[row], work[rank])]
        rank += 1
    return rank


def validate_transport(contract: TransportContract, species: tuple[Species, ...]):
    ids = _species_basis(species)
    reduced = contract.reduced_order
    if contract.frame != 'BARYCENTRIC':
        raise ContractError('FRAME_TRANSFORM_REQUIRED')
    if contract.force_convention != 'GRAD_MU_ISOTHERMAL' or contract.flux_convention != 'NUMBER_FLUX':
        raise ContractError('TRANSPORT_CONVENTION_UNSUPPORTED')
    if contract.species_order != ids:
        raise ContractError('SPECIES_BASIS_MISMATCH')
    if len(reduced) != len(ids) - 1 or any((len(contract.projector.axes[0]) != len(ids),
                                         len(contract.projector.axes[1]) != len(reduced),
                                         len(contract.mobility.axes[0]) != len(reduced),
                                         len(contract.mobility.axes[1]) != len(reduced))):
        raise ContractError('MATRIX_SHAPE_MISMATCH')
    if contract.projector.axes != (ids, reduced) or contract.mobility.axes != (reduced, reduced):
        raise ContractError('SPECIES_BASIS_MISMATCH')
    if any(q.domain_id != contract.domain_id for q in contract.quantities()):
        raise ContractError('STATE_DOMAIN_MISMATCH')
    for tensor, kind, unit in ((contract.projector, 'DIMENSIONLESS', '1'),
                               (contract.mobility, 'ONSAGER_MOBILITY', 'm^-1*s^-1*J^-1')):
        for q in tensor.quantities():
            require_signature(q, kind, unit)
    c = contract.projector.rational('DIMENSIONLESS', '1')
    masses = tuple(require_quantity(s.bookkeeping_mass, 'MASS', 'kg') for s in species)
    if any(sum(masses[i] * c[i][j] for i in range(len(ids))) != 0 for j in range(len(reduced))):
        raise ContractError('BARYCENTRIC_CONSTRAINT')
    if _rank(c) != len(reduced):
        raise ContractError('RANK_DEFICIENT')
    rational = contract.mobility.rational('ONSAGER_MOBILITY', 'm^-1*s^-1*J^-1')
    scale = max(abs(value) for row in rational for value in row)
    if scale == 0:
        raise ContractError('TRANSPORT_NOT_POSITIVE')
    matrix = np.array([[float(value / scale) for value in row] for row in rational])
    threshold = matrix_threshold()
    if np.max(np.abs(matrix - matrix.T)) > threshold:
        raise ContractError('TRANSPORT_NOT_SYMMETRIC')
    # Only the explicitly tested roundoff envelope is symmetrized. Never clip eigenvalues.
    eigenvalues = np.linalg.eigvalsh((matrix + matrix.T) / 2)
    if not np.all(np.isfinite(eigenvalues)) or np.min(eigenvalues) <= threshold:
        raise ContractError('TRANSPORT_NOT_POSITIVE', 'negative or unresolved null mode')


def validate_flux(species: tuple[Species, ...], fluxes: tuple[QuantityRecord, ...], frame='BARYCENTRIC'):
    _species_basis(species)
    require_frame(frame)
    if frame != 'BARYCENTRIC':
        raise ContractError('FRAME_TRANSFORM_REQUIRED')
    if len(fluxes) != len(species):
        raise ContractError('MATRIX_SHAPE_MISMATCH')
    if len({q.domain_id for q in fluxes} | {q.domain_id for s in species for q in s.quantities()}) != 1:
        raise ContractError('STATE_DOMAIN_MISMATCH')
    total = sum((require_quantity(s.bookkeeping_mass, 'MASS', 'kg') *
                 require_quantity(f, 'NUMBER_FLUX', 'm^-2/s') for s, f in zip(species, fluxes)), Fraction(0))
    if total:
        raise ContractError('BARYCENTRIC_CONSTRAINT')


@dataclass(frozen=True)
class CheckEvidence:
    check_id: str
    outcome: str
    sources: tuple[SourceRef, ...]

    def __post_init__(self):
        identifier(self.check_id)
        if self.outcome not in ('PASS', 'FAIL', 'UNVERIFIED'):
            raise ContractError('INVALID_EVIDENCE')
        object.__setattr__(self, 'sources', tuple(self.sources))
        if not all(isinstance(s, SourceRef) for s in self.sources):
            raise ContractError('INVALID_EVIDENCE')


@dataclass(frozen=True)
class MaterialBlock:
    """Named quantities, coverage, and source-backed quality evidence, not ready=True."""
    block_id: str
    domain_id: str
    quantities: tuple[QuantityRecord, ...]
    coverage: tuple[str, ...]
    checks: tuple[CheckEvidence, ...]
    tensors: tuple[tuple[str, TensorRecord], ...] = ()
    explicit_dofs: tuple[str, ...] = ()
    integrated_dofs: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.block_id)
        identifier(self.domain_id)
        for name in ('quantities', 'coverage', 'checks', 'explicit_dofs', 'integrated_dofs'):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        tensors = tuple(tuple(pair) for pair in self.tensors)
        if any(len(pair) != 2 or not isinstance(pair[1], TensorRecord) for pair in tensors):
            raise ContractError('INVALID_BLOCK')
        for name, _ in tensors:
            identifier(name)
        if len({pair[0] for pair in tensors}) != len(tensors):
            raise ContractError('DUPLICATE_ID')
        object.__setattr__(self, 'tensors', tensors)
        for label in self.explicit_dofs + self.integrated_dofs:
            identifier(label)
        if set(self.explicit_dofs) & set(self.integrated_dofs):
            raise ContractError('RESPONSE_DOUBLE_COUNT')
        if not all(isinstance(q, QuantityRecord) for q in self.quantities) or not all(
                isinstance(c, CheckEvidence) for c in self.checks):
            raise ContractError('INVALID_BLOCK')
        for label in self.coverage:
            identifier(label)
        if len({q.quantity_id for q in self.quantities}) != len(self.quantities) or len(
                {c.check_id for c in self.checks}) != len(self.checks):
            raise ContractError('DUPLICATE_ID')


@dataclass(frozen=True)
class MaterialPackage:
    package_id: str
    package_version: str
    created_at: str
    state: MaterialState
    domains: tuple[Domain, ...]
    source_records: tuple[SourceRecord, ...] = ()
    derivation_records: tuple[DerivationRecord, ...] = ()
    thermodynamics: MaterialBlock | None = None
    ionization: MaterialBlock | None = None
    transport: TransportContract | None = None
    transport_evidence: MaterialBlock | None = None
    screening: MaterialBlock | None = None
    numerical_quality: MaterialBlock | None = None
    schema_version: str = '1.0.0'

    def __post_init__(self):
        version(self.schema_version)
        identifier(self.package_id)
        identifier(self.package_version)
        timestamp(self.created_at)
        if not isinstance(self.state, MaterialState):
            raise ContractError('INVALID_STATE')
        for name, typ in (('domains', Domain), ('source_records', SourceRecord), ('derivation_records', DerivationRecord)):
            values = tuple(getattr(self, name))
            if not all(isinstance(value, typ) for value in values):
                raise ContractError('INVALID_TYPE', name)
            object.__setattr__(self, name, values)
        for name in ('thermodynamics', 'ionization', 'transport_evidence', 'screening', 'numerical_quality'):
            value = getattr(self, name)
            if value is not None and not isinstance(value, MaterialBlock):
                raise ContractError('INVALID_BLOCK', name)
        if self.transport is not None and not isinstance(self.transport, TransportContract):
            raise ContractError('INVALID_TRANSPORT')


@dataclass(frozen=True)
class GateResult:
    name: str
    status: Status
    codes: tuple[str, ...]


@dataclass(frozen=True)
class MaterialReport:
    gates: tuple[GateResult, ...]
    valid_structure: bool = True

    def gate(self, name: str) -> GateResult:
        return next(g for g in self.gates if g.name == name)


def validate_material(package: MaterialPackage, requirements=None,
                      store: LocalSourceStore | None = None) -> MaterialReport:
    from .readiness import BranchRequirements
    requirements = BranchRequirements() if requirements is None else requirements
    if not isinstance(requirements, BranchRequirements):
        raise ContractError('INVALID_REQUIREMENTS')
    validate_state(package.state)
    domains = {d.domain_id: d for d in package.domains}
    if len(domains) != len(package.domains) or package.state.domain_id not in domains:
        raise ContractError('STATE_DOMAIN_MISMATCH')
    domain = domains[package.state.domain_id]
    if package.state.node_id not in domain.nodes:
        raise ContractError('EXTRAPOLATION_FORBIDDEN')
    if package.state.phase != domain.phase:
        raise ContractError('STATE_DOMAIN_MISMATCH')
    records = {(r.ref.source_id, r.ref.source_version): r for r in package.source_records}
    if len(records) != len(package.source_records):
        raise ContractError('DUPLICATE_ID')
    validate_derivations(package.derivation_records, tuple(r.ref.source_id for r in package.source_records))

    def evidence(ref):
        reasons = list(ref.readiness_reasons())
        record = records.get((ref.source_id, ref.source_version))
        if record is None:
            reasons.append('SOURCE_MISSING')
        elif record.ref != ref:
            raise ContractError('HASH_MISMATCH')
        elif store is None:
            reasons.append('SOURCE_BYTES_UNVERIFIED')
        else:
            store.read(record)
        return reasons

    def quantities(items):
        reasons = []
        for item in items:
            if item.domain_id != domain.domain_id:
                raise ContractError('STATE_DOMAIN_MISMATCH')
            reasons.extend(item.readiness_reasons())
            for ref in item.provenance:
                reasons.extend(evidence(ref))
        return reasons

    def block(item, coverage, checks, required_values=(), required_tensors=()):
        if item is None:
            return ['BLOCK_MISSING']
        if not isinstance(item, MaterialBlock):
            raise ContractError('INVALID_BLOCK')
        if item.domain_id != domain.domain_id:
            raise ContractError('STATE_DOMAIN_MISMATCH')
        reasons = quantities(item.quantities)
        for _, tensor in item.tensors:
            reasons.extend(quantities(tensor.quantities()))
        if not item.quantities and not item.tensors:
            reasons.append('VALUES_MISSING')
        values = {value.quantity_id: value for value in item.quantities}
        for name, kind, unit in required_values:
            if name not in values:
                reasons.append('VALUE_MISSING:' + name)
            else:
                require_signature(values[name], kind, unit)
        tensors = dict(item.tensors)
        ids = tuple(s.species_id for s in package.state.species)
        for name, kind, unit, columns in required_tensors:
            if name not in tensors:
                reasons.append('TENSOR_MISSING:' + name)
            else:
                tensor = tensors[name]
                if tensor.axes != (ids, ids if columns == 'species' else ('value',)):
                    raise ContractError('SPECIES_BASIS_MISMATCH')
                for q in tensor.quantities():
                    require_signature(q, kind, unit)
                if all(q.status != 'OPEN' for q in tensor.quantities()):
                    tensor.rational(kind, unit)
        reasons.extend('COVERAGE_MISSING:' + label for label in sorted(set(coverage) - set(item.coverage)))
        by_id = {check.check_id: check for check in item.checks}
        for label in checks:
            check = by_id.get(label)
            if check is None or check.outcome != 'PASS' or not check.sources:
                reasons.append('UNVERIFIED_CHECK:' + label)
            if check:
                for ref in check.sources:
                    reasons.extend(evidence(ref))
        return reasons

    base = quantities(package.state.quantities())
    node = next((node for node in domain.state_nodes if node.node_id == package.state.node_id), None)
    if node is None:
        base.append('NODE_COORDINATES_UNVERIFIED')
    else:
        base.extend(quantities((node.temperature,) + tuple(value for _, value in node.number_densities)))
        expected = dict(node.number_densities)
        if set(expected) != {s.species_id for s in package.state.species}:
            raise ContractError('SPECIES_BASIS_MISMATCH')
        if node.temperature.value != package.state.temperature.value or any(
                expected[s.species_id].value != s.number_density.value for s in package.state.species):
            raise ContractError('STATE_DOMAIN_MISMATCH')
    elements = {s.element_id for s in package.state.species}
    species_ids = {s.species_id for s in package.state.species}
    base.extend('ELEMENT_MISSING:' + x for x in requirements.required_elements if x not in elements)
    base.extend('SPECIES_MISSING:' + x for x in requirements.required_species if x not in species_ids)
    quality = block(package.numerical_quality, ('method_version', 'uncertainty_budget'), ('convergence',))
    thermo = block(package.thermodynamics,
                   ('free_energy', 'pressure', 'internal_energy', 'chemical_potentials', 'cross_derivatives'),
                   ('gibbs_duhem', 'mixed_derivatives', 'subspace_stability'),
                   (('free_energy', 'ENERGY_DENSITY', 'J/m^3'), ('pressure', 'PRESSURE', 'Pa'),
                    ('internal_energy', 'ENERGY_DENSITY', 'J/m^3')),
                   (('chemical_potentials', 'ENERGY', 'J', 'value'),
                    ('cross_derivatives', 'CHEMICAL_DERIVATIVE', 'J*m^3', 'species')))
    if package.state.temperature_convention != 'PHYSICAL_EQUILIBRIUM':
        thermo.append('TEMPERATURE_CONVENTION_UNVERIFIED')
    if package.state.potential_convention == 'UNVERIFIED':
        thermo.append('POTENTIAL_CONVENTION_UNVERIFIED')
    charge = block(package.ionization, ('resolved_populations', 'electron_bookkeeping', 'regime'),
                   ('population_normalization', 'element_conservation', 'charge_conservation'))
    populations = dict(package.ionization.tensors).get('populations') if package.ionization else None
    if populations is None:
        charge.append('POPULATIONS_MISSING')
    else:
        ions = tuple(s for s in package.state.species if s.element_id != 'electron')
        if populations.axes != (tuple(s.species_id for s in ions), ('value',)):
            raise ContractError('SPECIES_BASIS_MISMATCH')
        if all(value.status != 'OPEN' for value in populations.quantities()):
            pop = populations.rational('DIMENSIONLESS', '1')
            for element in {s.element_id for s in ions}:
                entries = [(s, row[0]) for s, row in zip(ions, pop) if s.element_id == element]
                total_n = sum(Fraction(s.number_density.value) for s, _ in entries)
                if total_n <= 0 or any(value < 0 or value > 1 for _, value in entries) or sum(
                        value for _, value in entries) != 1:
                    raise ContractError('POPULATION_NORMALIZATION')
                if any(value * total_n != Fraction(s.number_density.value) for s, value in entries):
                    raise ContractError('INCONSISTENT_STATE')
    trans = block(package.transport_evidence, ('ion_ion', 'electrons', 'electron_ion', 'isothermal'),
                  ('response_validation',))
    if requirements.thermal_branch == 'NONISOTHERMAL':
        trans.append('HEAT_CROSS_BLOCKS_OPEN')
    if package.transport is None:
        trans.append('TRANSPORT_MISSING')
    else:
        try:
            validate_transport(package.transport, package.state.species)
        except ContractError as exc:
            if exc.code != 'OPEN_VALUE':
                raise
            trans.append('OPEN_VALUE')
        if package.transport.domain_id != domain.domain_id:
            raise ContractError('STATE_DOMAIN_MISMATCH')
        trans.extend(quantities(package.transport.quantities()))
    screening = block(package.screening, ('response', 'normalization', 'dof_partition', 'regime'),
                      ('response_partition', 'causality', 'sum_rules'))
    # A generic scalar response is insufficient for a dynamic k/omega contract.
    # Phase 1 does not certify any unimplemented dynamic-response branch.
    screening.append('DYNAMIC_RESPONSE_CONTRACT_OPEN')

    def gate(name, reasons):
        reasons = tuple(dict.fromkeys(reasons))
        return GateResult(name, Status.NOT_READY if reasons else Status.READY, reasons)

    return MaterialReport((gate('thermodynamics_ready', base + quality + thermo),
                           gate('composition_ready', base + quality),
                           gate('charge_state_ready', base + quality + charge),
                           gate('transport_ready', base + quality + trans),
                           gate('screening_input_ready', base + quality + screening),
                           GateResult('capture_ready', Status.OPEN_OPERATOR, ('CAPTURE_OPERATOR_MISSING',)),
                           GateResult('charge_matching_ready', Status.OPEN_OPERATOR, ('MATCHING_OPERATOR_MISSING',))))


@dataclass(frozen=True)
class MatchingRecord:
    operator_id: str
    operator_version: str
    sources: tuple[SourceRef, ...]
    domain_id: str
    definition: str

    def __post_init__(self):
        identifier(self.operator_id)
        identifier(self.operator_version)
        identifier(self.domain_id)
        nonempty(self.definition)
        object.__setattr__(self, 'sources', tuple(self.sources))
        if not self.sources or not all(isinstance(ref, SourceRef) for ref in self.sources):
            raise ContractError('PROVENANCE_MISSING')


@dataclass(frozen=True)
class ChargeBoundary:
    q_bullet: QuantityRecord
    q_m: QuantityRecord | None = None
    matching: MatchingRecord | None = None

    def __post_init__(self):
        require_quantity(self.q_bullet, 'CHARGE', 'C')
        if self.q_m is not None:
            require_quantity(self.q_m, 'CHARGE', 'C')
            if not isinstance(self.matching, MatchingRecord):
                raise ContractError('OPEN_OPERATOR')
            if self.q_m.domain_id != self.matching.domain_id or self.q_bullet.domain_id != self.matching.domain_id:
                raise ContractError('STATE_DOMAIN_MISMATCH')

    @property
    def status(self):
        # A declared relation is not certification of a physical operator.
        return Status.OPEN_OPERATOR if self.matching is None else Status.NOT_READY
