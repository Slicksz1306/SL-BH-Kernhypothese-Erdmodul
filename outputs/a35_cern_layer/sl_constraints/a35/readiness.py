"""Explicit branch requirements and algebraic boundary checks, no evolution."""
from dataclasses import dataclass
from fractions import Fraction
from ..common.types import QuantityRecord, ContractError, Status, identifier


@dataclass(frozen=True)
class BranchRequirements:
    branch_id: str = 'A35_FULL_MIXTURE'
    thermal_branch: str = 'ISOTHERMAL'
    required_elements: tuple[str, ...] = ()
    required_species: tuple[str, ...] = ()

    def __post_init__(self):
        if self.branch_id != 'A35_FULL_MIXTURE' or self.thermal_branch not in ('ISOTHERMAL', 'NONISOTHERMAL'):
            raise ContractError('UNSUPPORTED_BRANCH')
        for name in ('required_elements', 'required_species'):
            values = tuple(getattr(self, name))
            if len(set(values)) != len(values):
                raise ContractError('DUPLICATE_ID')
            for value in values:
                identifier(value)
            object.__setattr__(self, name, values)


def assess_readiness(material_report):
    from .material import GateResult
    reasons = tuple(dict.fromkeys(code for gate in material_report.gates for code in gate.codes))
    # No physical inner operator implementation exists in this foundation slice.
    reasons += tuple(code for code in ('CAPTURE_OPERATOR_MISSING', 'MATCHING_OPERATOR_MISSING',
                                      'ENERGY_MATCHING_OPERATOR_MISSING') if code not in reasons)
    return GateResult('A35.RELEASE', Status.OPEN_OPERATOR, reasons)


def validate_full_mixture_boundary(species, inward_particle_rates: tuple[QuantityRecord, ...],
                                   density: QuantityRecord, outward_velocity: QuantityRecord,
                                   surface_area: QuantityRecord):
    """sum(m_s F_s) = -area*rho*u, positive F inward and u outward.

    Surface area is an explicit input: no hidden pi/radius approximation.
    The sum concerns total particle rates, not barycentric diffusion alone.
    """
    from .material import _species_basis, require_quantity
    _species_basis(species)
    if len(inward_particle_rates) != len(species):
        raise ContractError('SPECIES_BASIS_MISMATCH')
    rho = require_quantity(density, 'MASS_DENSITY', 'kg/m^3')
    velocity = require_quantity(outward_velocity, 'VELOCITY', 'm/s')
    area = require_quantity(surface_area, 'AREA', 'm^2')
    if area <= 0:
        raise ContractError('OUT_OF_RANGE')
    inputs = tuple(inward_particle_rates) + (density, outward_velocity, surface_area) + tuple(
        q for s in species for q in s.quantities())
    if len({q.domain_id for q in inputs}) != 1:
        raise ContractError('STATE_DOMAIN_MISMATCH')
    expected_density = sum((Fraction(s.bookkeeping_mass.value) * Fraction(s.number_density.value)
                            for s in species), Fraction(0))
    if expected_density != rho:
        raise ContractError('INCONSISTENT_STATE')
    inward_mass = sum((require_quantity(s.bookkeeping_mass, 'MASS', 'kg') *
                       require_quantity(flow, 'PARTICLE_RATE', 'particle/s')
                       for s, flow in zip(species, inward_particle_rates)), Fraction(0))
    if inward_mass != -area * rho * velocity:
        raise ContractError('MASS_BOUNDARY_INCOMPATIBLE')
