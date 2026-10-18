"""Synthetic wire/domain boundary fixtures."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest
import test_material
from fixtures import q
from sl_constraints.common import schema, types as t
from sl_constraints.common.units import convert_quantity
from sl_constraints.a35 import material as m


class WireDomainTests(unittest.TestCase):
    def test_cross_section_and_luminosity_conversions(self):
        self.assertEqual(convert_quantity(q(1, 'pb', 'CROSS_SECTION'), 'fb').value, 1000)
        self.assertEqual(convert_quantity(q(1000, 'pb^-1', 'INTEGRATED_LUMINOSITY'), 'fb^-1').value, 1)

    def test_molar_energy_not_particle_energy(self):
        with self.assertRaisesRegex(t.ContractError, 'UNIT_MISMATCH'):
            convert_quantity(q(1, 'J/mol', 'MOLAR_ENERGY'), 'J')

    def test_json_roundtrip(self):
        data = schema.to_wire(q(1, 'J', 'ENERGY'))
        wire = json.loads(json.dumps(data, allow_nan=False))
        self.assertEqual(schema.quantity_from_dict(wire), q(1, 'J', 'ENERGY'))

    def test_duplicate_json_keys(self):
        with self.assertRaisesRegex(t.ContractError, 'DUPLICATE_FIELD'):
            schema.parse_json('{"unit":"kg","unit":"C"}')

    def test_no_json_float_physical_values(self):
        with self.assertRaisesRegex(t.ContractError, 'EXACT_NUMBER_REQUIRED'):
            schema.parse_json('{"value": 0.1}')

    def test_no_json_nonfinite(self):
        for text in ('{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(t.ContractError):
                schema.parse_json(text)

    def test_invalid_json_is_contract_error(self):
        with self.assertRaises(t.ContractError):
            schema.parse_json('{')

    def test_common_schema_is_local_and_closed(self):
        path = Path(__file__).resolve().parents[1] / 'schemas/common.schema.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        self.assertFalse(value['additionalProperties'])
        self.assertEqual(value['$schema'], 'https://json-schema.org/draft/2020-12/schema')

    def test_external_ref_rejected(self):
        report = schema.validate_schema({'$ref': 'https://invalid.example/execute'})
        self.assertFalse(report.valid_structure)

    def test_node_label_without_coordinates_not_ready(self):
        fixture = test_material.MaterialTests('runTest')
        report = m.validate_material(fixture.package())
        self.assertIn('NODE_COORDINATES_UNVERIFIED', report.gate('composition_ready').codes)

    def test_exact_node_coordinates_verified(self):
        fixture = test_material.MaterialTests('runTest')
        state = fixture.state()
        node = t.StateNode('node1', state.temperature,
                           tuple((s.species_id, s.number_density) for s in state.species))
        domain = t.Domain('test_domain', ('node1',), 'test_phase', 'SYNTHETIC TEST', (node,))
        report = m.validate_material(fixture.package(domains=(domain,)))
        self.assertNotIn('NODE_COORDINATES_UNVERIFIED', report.gate('composition_ready').codes)
        wrong = fixture.package(domains=(domain,), state=replace(state, temperature=q(3, 'K', 'TEMPERATURE')))
        with self.assertRaisesRegex(t.ContractError, 'STATE_DOMAIN_MISMATCH'):
            m.validate_material(wrong)


if __name__ == '__main__':
    unittest.main()
