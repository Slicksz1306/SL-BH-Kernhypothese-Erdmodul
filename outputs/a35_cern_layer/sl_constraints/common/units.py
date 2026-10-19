"""Closed registry. Factors relative to SI; e and eV use SI exact e.

Dimensions alone are insufficient: ENERGY and TORQUE deliberately cannot mix.
Conversions return a new value and an exact rational conversion receipt.
"""
from dataclasses import replace
from fractions import Fraction
from types import MappingProxyType
from .types import ContractError, ConversionStep, QuantityRecord, exact_decimal

# (semantic kind, exact scale). No inferred unit strings or implicit conversion.
UNITS = MappingProxyType({
    'kg': ('MASS', '1'), 'g': ('MASS', '.001'),
    'C': ('CHARGE', '1'), 'e': ('CHARGE', '1.602176634e-19'),
    'J': ('ENERGY', '1'), 'eV': ('ENERGY', '1.602176634e-19'),
    'GeV': ('ENERGY', '1.602176634e-10'), 'TeV': ('ENERGY', '1.602176634e-7'),
    'K': ('TEMPERATURE', '1'), 'Pa': ('PRESSURE', '1'), 'GPa': ('PRESSURE', '1e9'),
    'kg/m^3': ('MASS_DENSITY', '1'), 'g/cm^3': ('MASS_DENSITY', '1000'),
    'm^-3': ('NUMBER_DENSITY', '1'), 's': ('TIME', '1'), 'm': ('LENGTH', '1'),
    'm^-2/s': ('NUMBER_FLUX', '1'), 'm^2/s': ('DIFFUSIVITY', '1'),
    'A': ('CURRENT', '1'), 'kg/s': ('MASS_RATE', '1'), 'W': ('POWER', '1'),
    '1': ('DIMENSIONLESS', '1'), 'particle': ('COUNT', '1'),
    'particle/s': ('PARTICLE_RATE', '1'), 'm/s': ('VELOCITY', '1'),
    'S/m': ('CONDUCTIVITY', '1'), 'J/m^3': ('ENERGY_DENSITY', '1'),
    'Pa*m^3': ('EOS_DERIVATIVE', '1'), 'J*m^3': ('CHEMICAL_DERIVATIVE', '1'),
    'm^-1*s^-1*J^-1': ('ONSAGER_MOBILITY', '1'),
    'm^2': ('AREA', '1'), 'pb': ('CROSS_SECTION', '1e-40'), 'fb': ('CROSS_SECTION', '1e-43'),
    'pb^-1': ('INTEGRATED_LUMINOSITY', '1e40'), 'fb^-1': ('INTEGRATED_LUMINOSITY', '1e43'),
    'J/mol': ('MOLAR_ENERGY', '1'), 'W/(m*K)': ('THERMAL_CONDUCTIVITY', '1'),
    's^-1': ('FREQUENCY', '1'), 'm^-3/s': ('VOLUMETRIC_RATE', '1'),
    'rad/s': ('ANGULAR_FREQUENCY', '1'), 'm^-1': ('WAVENUMBER', '1'),
})


def require_unit(unit: str, kind: str):
    if not isinstance(unit, str) or unit not in UNITS:
        raise ContractError('UNKNOWN_UNIT', str(unit))
    entry = UNITS[unit]
    if entry[0] != kind:
        raise ContractError('UNIT_MISMATCH', f'{unit} / {kind}')
    return entry


def convert_quantity(q: QuantityRecord, target: str) -> QuantityRecord:
    _, source_scale = require_unit(q.unit, q.kind)
    _, target_scale = require_unit(target, q.kind)
    ratio = Fraction(source_scale) / Fraction(target_scale)
    value = None if q.value is None else exact_decimal(Fraction(q.value) * ratio)
    uncertainty = q.uncertainty
    if uncertainty.value is not None:
        power = 2 if uncertainty.kind == 'VARIANCE' else 1
        uncertainty = replace(uncertainty, value=exact_decimal(Fraction(uncertainty.value) * ratio ** power))
    step = ConversionStep(q.unit, target, ratio.numerator, ratio.denominator)
    return replace(q, value=value, unit=target, uncertainty=uncertainty,
                   conversions=q.conversions + (step,))
