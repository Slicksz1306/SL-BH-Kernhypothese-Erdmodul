"""Synthetic mathematical fixtures; deliberately not physical material data."""
from dataclasses import replace
from fractions import Fraction
import importlib
import unittest
from fixtures import q, REF
from sl_constraints.common.types import ContractError, Domain, Status

try:
    m = importlib.import_module('sl_constraints.a35.material')
except ModuleNotFoundError:
    m = None


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(m, 'P03 not implemented')

    def species(self):
        return (m.Species('ion', 'X', q(2, 'kg', 'MASS'), q(1, '1', 'DIMENSIONLESS'),
                          q(3, 'm^-3', 'NUMBER_DENSITY')),
                m.Species('electron', 'electron', q(1, 'kg', 'MASS'), q(-1, '1', 'DIMENSIONLESS'),
                          q(3, 'm^-3', 'NUMBER_DENSITY')))

    def state(self, **kwargs):
        return m.MaterialState(self.species(), q(2, 'K', 'TEMPERATURE'),
                               'BARYCENTRIC', 'test_domain', 'node1', 'test_phase', **kwargs)

    def matrix(self, values, rows, cols, unit='1', kind='DIMENSIONLESS'):
        return m.TensorRecord(tuple(tuple(q(v, unit, kind) for v in row) for row in values),
                              (tuple(rows), tuple(cols)), 'SYNTHETIC TEST ONLY')

    def transport(self, **kwargs):
        args = dict(species_order=('ion', 'electron'), reduced_order=('r1',),
                    projector=self.matrix([[1], [-2]], ('ion', 'electron'), ('r1',)),
                    mobility=self.matrix([[1]], ('r1',), ('r1',),
                                         'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY'),
                    frame='BARYCENTRIC', force_convention='GRAD_MU_ISOTHERMAL',
                    flux_convention='NUMBER_FLUX', domain_id='test_domain')
        args.update(kwargs)
        return m.TransportContract(**args)

    def test_derived_density(self):
        self.assertEqual(m.validate_state(self.state()), Fraction(9))

    def test_consistent_redundant_validation_value(self):
        m.validate_state(self.state(density=q(9, 'kg/m^3', 'MASS_DENSITY'), density_role='VALIDATION'))

    def test_inconsistent_density(self):
        with self.assertRaisesRegex(ContractError, 'INCONSISTENT_STATE'):
            m.validate_state(self.state(density=q(10, 'kg/m^3', 'MASS_DENSITY'), density_role='VALIDATION'))

    def test_even_consistent_density_cannot_be_independent(self):
        with self.assertRaisesRegex(ContractError, 'REDUNDANT_STATE'):
            m.validate_state(self.state(density=q(9, 'kg/m^3', 'MASS_DENSITY'), density_role='INPUT'))

    def test_unknown_frame(self):
        with self.assertRaisesRegex(ContractError, 'INVALID_FRAME'):
            self.state().__class__(self.species(), q(2, 'K', 'TEMPERATURE'), 'ION_COM',
                                  'test_domain', 'node1', 'test_phase')

    def test_lab_frame_not_silently_transformed(self):
        with self.assertRaisesRegex(ContractError, 'FRAME_TRANSFORM_REQUIRED'):
            m.validate_state(replace(self.state(), frame='LAB'))

    def test_fractional_resolved_charge_rejected(self):
        with self.assertRaisesRegex(ContractError, 'CHARGE_BASIS_INVALID'):
            replace(self.species()[0], charge_number=q('1.5', '1', 'DIMENSIONLESS'))

    def test_duplicate_species_rejected(self):
        with self.assertRaisesRegex(ContractError, 'SPECIES_BASIS_MISMATCH'):
            m.validate_state(replace(self.state(), species=(self.species()[0],) * 2))

    def test_s_minus_one_valid(self):
        m.validate_transport(self.transport(), self.species())

    def test_wrong_projector_shape(self):
        bad = self.matrix([[1, 0], [-2, 0]], ('ion', 'electron'), ('r1', 'r2'))
        with self.assertRaisesRegex(ContractError, 'MATRIX_SHAPE_MISMATCH'):
            m.validate_transport(self.transport(projector=bad), self.species())

    def test_barycentric_constraint_violated(self):
        bad = self.matrix([[1], [-1]], ('ion', 'electron'), ('r1',))
        with self.assertRaisesRegex(ContractError, 'BARYCENTRIC_CONSTRAINT'):
            m.validate_transport(self.transport(projector=bad), self.species())

    def test_axes_not_reordered_implicitly(self):
        bad = self.matrix([[1], [-2]], ('electron', 'ion'), ('r1',))
        with self.assertRaisesRegex(ContractError, 'SPECIES_BASIS_MISMATCH'):
            m.validate_transport(self.transport(projector=bad), self.species())

    def test_rank_deficient_projector(self):
        bad = self.matrix([[0], [0]], ('ion', 'electron'), ('r1',))
        with self.assertRaisesRegex(ContractError, 'RANK_DEFICIENT'):
            m.validate_transport(self.transport(projector=bad), self.species())

    def test_negative_mobility(self):
        bad = self.matrix([[-1]], ('r1',), ('r1',), 'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY')
        with self.assertRaisesRegex(ContractError, 'TRANSPORT_NOT_POSITIVE'):
            m.validate_transport(self.transport(mobility=bad), self.species())

    def test_unexpected_transport_nullmode(self):
        bad = self.matrix([[0]], ('r1',), ('r1',), 'm^-1*s^-1*J^-1', 'ONSAGER_MOBILITY')
        with self.assertRaisesRegex(ContractError, 'TRANSPORT_NOT_POSITIVE'):
            m.validate_transport(self.transport(mobility=bad), self.species())

    def test_mass_flux_pass_and_fail(self):
        m.validate_flux(self.species(), (q(1, 'm^-2/s', 'NUMBER_FLUX'), q(-2, 'm^-2/s', 'NUMBER_FLUX')))
        with self.assertRaisesRegex(ContractError, 'BARYCENTRIC_CONSTRAINT'):
            m.validate_flux(self.species(), (q(1, 'm^-2/s', 'NUMBER_FLUX'), q(-1, 'm^-2/s', 'NUMBER_FLUX')))

    def test_flux_dimension(self):
        with self.assertRaisesRegex(ContractError, 'MATRIX_SHAPE_MISMATCH'):
            m.validate_flux(self.species(), (q(1, 'm^-2/s', 'NUMBER_FLUX'),))

    def test_ragged_tensor(self):
        with self.assertRaisesRegex(ContractError, 'MATRIX_SHAPE_MISMATCH'):
            self.matrix([[1], [1, 2]], ('ion', 'electron'), ('r1',))

    def package(self, **kwargs):
        args = dict(package_id='test_package', package_version='1', created_at='2026-10-07T00:00:00Z',
                    state=self.state(), domains=(Domain('test_domain', ('node1',), 'test_phase',
                                                         'SYNTHETIC TEST ONLY'),))
        args.update(kwargs)
        return m.MaterialPackage(**args)

    def test_material_does_not_create_capture_or_matching(self):
        report = m.validate_material(self.package())
        self.assertEqual(report.gate('capture_ready').status, Status.OPEN_OPERATOR)
        self.assertEqual(report.gate('charge_matching_ready').status, Status.OPEN_OPERATOR)
        self.assertEqual(len(report.gates), 7)

    def test_fixture_never_scientifically_ready(self):
        report = m.validate_material(self.package(transport=self.transport()))
        self.assertTrue(all(g.status != Status.READY for g in report.gates))
        self.assertIn('TEST_FIXTURE', report.gate('composition_ready').codes)

    def test_domain_outside_exact_nodes(self):
        package = self.package(state=replace(self.state(), node_id='node2'))
        with self.assertRaisesRegex(ContractError, 'EXTRAPOLATION_FORBIDDEN'):
            m.validate_material(package)

    def test_phase_mismatch(self):
        with self.assertRaisesRegex(ContractError, 'STATE_DOMAIN_MISMATCH'):
            m.validate_material(self.package(state=replace(self.state(), phase='other')))

    def test_boolean_ready_is_not_an_evidence_block(self):
        with self.assertRaisesRegex(ContractError, 'INVALID_BLOCK'):
            m.validate_material(self.package(thermodynamics=True))

    def test_qbullet_does_not_alias_qm(self):
        charge = m.ChargeBoundary(q(1, 'C', 'CHARGE'))
        self.assertIsNone(charge.q_m)
        self.assertEqual(charge.status, Status.OPEN_OPERATOR)

    def test_qm_requires_explicit_matching_record(self):
        with self.assertRaisesRegex(ContractError, 'OPEN_OPERATOR'):
            m.ChargeBoundary(q(1, 'C', 'CHARGE'), q(1, 'C', 'CHARGE'))


if __name__ == '__main__':
    unittest.main()
