"""SYNTHETIC branch/continuity fixtures, not accretion inputs."""
from dataclasses import replace
from fractions import Fraction
import importlib
import unittest
import test_material
import test_ledger
from fixtures import q
from sl_constraints.common.types import ContractError, Status
from sl_constraints.a35 import material as m, ledger as l

try:
    r = importlib.import_module('sl_constraints.a35.readiness')
except ModuleNotFoundError:
    r = None


class ReadinessBoundaries(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(r, 'branch requirements not yet implemented')
        self.material = test_material.MaterialTests('runTest')
        self.ledger = test_ledger.LedgerTests('runTest')
        self.ledger.setUp()

    def test_missing_element_not_full_mixture(self):
        requirements = r.BranchRequirements(required_elements=('X', 'Ni'))
        report = m.validate_material(self.material.package(), requirements=requirements)
        self.assertIn('ELEMENT_MISSING:Ni', report.gate('composition_ready').codes)

    def test_no_solver_release_from_material_report(self):
        report = m.validate_material(self.material.package())
        release = r.assess_readiness(report)
        self.assertEqual(release.status, Status.OPEN_OPERATOR)
        self.assertIn('MATCHING_OPERATOR_MISSING', release.codes)

    def test_nonisothermal_transport_not_certified(self):
        report = m.validate_material(self.material.package(transport=self.material.transport()),
                                     requirements=r.BranchRequirements(thermal_branch='NONISOTHERMAL'))
        self.assertIn('HEAT_CROSS_BLOCKS_OPEN', report.gate('transport_ready').codes)

    def test_unrecognized_branch(self):
        with self.assertRaisesRegex(ContractError, 'UNSUPPORTED_BRANCH'):
            r.BranchRequirements(branch_id='legacy_H0')

    def test_positive_full_mixture_inflow_zero_u_rejected(self):
        with self.assertRaisesRegex(ContractError, 'MASS_BOUNDARY_INCOMPATIBLE'):
            r.validate_full_mixture_boundary(self.material.species(),
                (q(1, 'particle/s', 'PARTICLE_RATE'), q(1, 'particle/s', 'PARTICLE_RATE')),
                q(9, 'kg/m^3', 'MASS_DENSITY'), q(0, 'm/s', 'VELOCITY'), q(1, 'm^2', 'AREA'))

    def test_compatible_full_mixture_boundary(self):
        r.validate_full_mixture_boundary(self.material.species(),
            (q(3, 'particle/s', 'PARTICLE_RATE'), q(3, 'particle/s', 'PARTICLE_RATE')),
            q(9, 'kg/m^3', 'MASS_DENSITY'), q(-1, 'm/s', 'VELOCITY'), q(1, 'm^2', 'AREA'))

    def test_stationary_storage_requires_balanced_inner_region(self):
        ledger = l.TransferLedger((self.ledger.transfer(),))
        with self.assertRaisesRegex(ContractError, 'NONSTATIONARY_TRANSITION'):
            ledger.require_stationary_transition()
        balanced = l.TransferLedger((self.ledger.transfer(),
                    self.ledger.transfer('absorb', 'transition_region', 'seed')))
        balanced.require_stationary_transition()

    def test_energy_seven_then_two(self):
        a = self.ledger.transfer(value='7', kind='ENERGY', unit='J')
        b = self.ledger.transfer('absorbed', 'transition_region', 'seed', value='2', kind='ENERGY', unit='J')
        ledger = l.TransferLedger((a, b))
        self.assertEqual(tuple(ledger.change(res, 'ENERGY') for res in
                               ('outer_material', 'transition_region', 'seed')), (-7, 5, 2))
        self.assertTrue(ledger.audit().valid)

    def test_disjoint_species_same_event(self):
        transfers = ()
        for species in self.material.species():
            transfers += l.species_transfer(species, q(1, 'particle', 'COUNT'),
                channel_id=species.species_id, event_id='event', source='transition_region', target='seed',
                operator=self.ledger.op, double_count_group='particles', frame='BARYCENTRIC')
        ledger = l.TransferLedger(transfers)
        self.assertEqual(ledger.change('seed', 'MASS'), 3)
        self.assertEqual(ledger.change('seed', 'CHARGE'), 0)
        self.assertEqual(ledger.species_change('seed', 'ion').value, 1)
        self.assertEqual(ledger.element_change('seed', 'X').value, 1)
        extra = self.ledger.transfer('I_plasma', 'transition_region', 'seed', kind='CHARGE', unit='C',
                                     event_id='event', double_count_group='particles')
        with self.assertRaisesRegex(ContractError, 'DOUBLE_COUNT'):
            l.TransferLedger(transfers + (extra,))

    def test_external_sink_sign(self):
        transfer = self.ledger.transfer('loss', 'seed', 'external', external=True)
        report = l.TransferLedger((transfer,)).audit()
        self.assertTrue(report.valid)
        self.assertEqual(report.external_contribution('MASS'), Fraction(-2))


if __name__ == '__main__':
    unittest.main()
