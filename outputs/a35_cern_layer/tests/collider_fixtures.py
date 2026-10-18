"""SYNTHETIC ONLY; no fixture in this module is a collider measurement."""
def quantity(value, unit, definition='SYNTHETIC definition'):
    return {'value': value, 'unit': unit, 'definition': definition}


def constraint():
    return {
        'schema_version': '1.0.0', 'constraint_id': 'synthetic_constraint',
        'snapshot_id': 'synthetic_snapshot', 'source_id': 'synthetic_source', 'source_version': 'v1',
        'experiment': 'ATLAS', 'collaboration': 'ATLAS', 'analysis_id': 'SYNTHETIC',
        'benchmark_id': 'synthetic_add2', 'channel_id': 'electron_jet', 'dataset_id': 'synthetic_data',
        'publication_date': '2026-01-01', 'data_period': 'SYNTHETIC',
        'sqrt_s': quantity('13.6', 'TeV'), 'luminosity': quantity('164', 'fb^-1'),
        'object_class': 'QUANTUM_BLACK_HOLE', 'model_family': 'ADD',
        'model_version': 'SYNTHETIC_v1', 'n_extra_dimensions': 2,
        'model_parameters': [{'name': 'threshold', 'role': 'SCAN', 'value': None, 'definition': 'SYNTHETIC Mth'}],
        'observable_type': 'MASS_THRESHOLD', 'observable_definition': 'SYNTHETIC threshold lower bound',
        'limit_type': 'LOWER_BOUND', 'confidence_level': '0.95',
        'observed_value': '8.6', 'expected_value': '8.5', 'unit': 'TeV',
        'expected_bands': [], 'statistical_method': 'CLs_asymptotic',
        'validity_domain': 'SYNTHETIC declared scan domain',
        'assumptions': {name: 'SYNTHETIC_' + name for name in (
            'generator', 'pdf', 'threshold_convention', 'fundamental_scale_definition',
            'spin', 'charge', 'lifetime', 'decay_regime', 'branching_ratios', 'loss_model', 'remnant')},
        'selection_id': 'synthetic_selection', 'comparison_group': None,
        'provenance': [{'source_id': 'synthetic_source', 'source_version': 'v1',
                        'sha256': 'a' * 64, 'locator': 'SYNTHETIC Table 1 row 1'}],
        'extraction_refs': [{'artifact_id': 'synthetic_extract', 'sha256': 'b' * 64}],
        'missing_fields': [], 'validation_status': 'PROPOSED', 'purpose': 'TEST_FIXTURE'
    }
