"""SYNTHETIC TEST DATA ONLY. No values in this module are research inputs."""
from sl_constraints.common.types import QuantityRecord, SourceRef, Uncertainty

REF = SourceRef('synthetic_test', '1', '2026-10-07T00:00:00Z', 'a' * 64, 'TEST_FIXTURE')


def q(value, unit, kind, name='fixture'):
    return QuantityRecord(name, str(value), unit, kind, 'SYNTHETIC TEST ONLY',
                          'test_domain', (REF,), Uncertainty('EXACT'))
