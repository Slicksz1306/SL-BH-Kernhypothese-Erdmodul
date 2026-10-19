"""End-to-end synthetic source -> material evidence; never research data."""
from dataclasses import replace
import unittest
import test_provenance
from fixtures import q
from sl_constraints.common.types import ContractError, Domain, StateNode, Status
from sl_constraints.a35 import material as m


class LocalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.sources = test_provenance.ProvenanceTests('runTest')
        self.sources.setUp()
        self.addCleanup(self.sources.doCleanups)
        self.record = self.sources.record()
        self.sources.store.ingest_bytes(self.record, self.sources.raw)

        def value(number, unit, kind):
            return replace(q(number, unit, kind), provenance=(self.record.ref,))

        species = (m.Species('ion', 'X', value(2, 'kg', 'MASS'), value(1, '1', 'DIMENSIONLESS'),
                             value(3, 'm^-3', 'NUMBER_DENSITY')),
                   m.Species('electron', 'electron', value(1, 'kg', 'MASS'), value(-1, '1', 'DIMENSIONLESS'),
                             value(3, 'm^-3', 'NUMBER_DENSITY')))
        state = m.MaterialState(species, value(2, 'K', 'TEMPERATURE'), 'BARYCENTRIC',
                                'test_domain', 'node1', 'test_phase')
        node = StateNode('node1', state.temperature, tuple((s.species_id, s.number_density) for s in species))
        domain = Domain('test_domain', ('node1',), 'test_phase', 'SYNTHETIC TEST', (node,))
        quality = m.MaterialBlock('quality', 'test_domain', (value(1, '1', 'DIMENSIONLESS'),),
                                   ('method_version', 'uncertainty_budget'),
                                   (m.CheckEvidence('convergence', 'PASS', (self.record.ref,)),))
        self.package = m.MaterialPackage('integration', '1', '2026-10-07T00:00:00Z', state,
                                          (domain,), (self.record,), numerical_quality=quality)

    def test_verified_bytes_still_fixture_not_ready(self):
        report = m.validate_material(self.package, store=self.sources.store)
        self.assertEqual(report.gate('composition_ready').codes, ('TEST_FIXTURE',))
        self.assertEqual(report.gate('composition_ready').status, Status.NOT_READY)
        self.assertEqual(report.gate('capture_ready').status, Status.OPEN_OPERATOR)

    def test_no_store_no_byte_verification(self):
        report = m.validate_material(self.package)
        self.assertIn('SOURCE_BYTES_UNVERIFIED', report.gate('composition_ready').codes)

    def test_tamper_blocks_material_evidence(self):
        path = self.sources.store.safe_path('blobs/' + self.record.ref.source_hash)
        with path.open('wb') as stream:
            stream.write(b'SYNTHETIC TAMPER')
        with self.assertRaisesRegex(ContractError, 'HASH_MISMATCH'):
            m.validate_material(self.package, store=self.sources.store)


if __name__ == '__main__':
    unittest.main()
