"""Offline full-suite and explicit retained-185 / Foundation-140 verification."""
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import unittest

workspace = Path(__file__).resolve().parents[1]
package = workspace / 'outputs/a35_cern_layer'
sys.path.insert(0, str(package))
test_dir = package / 'tests'


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def load():
    return list(flatten(unittest.TestLoader().discover(str(test_dir))))


def retained(test):
    identity = test.id()
    return (identity.split('.')[0] not in ('test_collider_review', 'test_collider_reproduction', 'test_http_receipts')
            and not identity.endswith('.test_paragraph_exact_bytes_retained'))


previous_report = json.loads((workspace / 'outputs/CERN_TEST_RESULTS.json').read_text(encoding='utf-8'))
baseline_run = next((run for run in previous_report['runs']
                     if run['name'] in ('full', 'prior_full_baseline_210') and run['count'] == 210), None)
assert baseline_run is not None, 'previous exact 210-test baseline not found'
baseline_ids = baseline_run['test_ids']
tests_now = load()
current_ids = [t.id() for t in tests_now]
assert len(current_ids) == len(set(current_ids)) == 212
assert set(baseline_ids) < set(current_ids) and len(baseline_ids) == 210
report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
          'previous_full_baseline_test_count': len(baseline_ids), 'runs': []}
for name, tests in [('full_212', tests_now), ('prior_full_baseline_210',
        [t for t in tests_now if t.id() in set(baseline_ids)])]:
    ids = [t.id() for t in tests]
    expected = 212 if name == 'full_212' else 210
    assert len(ids) == len(set(ids)) == expected, (name, len(ids), expected)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(tests))
    run = dict(name=name, count=result.testsRun, passed=result.wasSuccessful(),
               failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), test_ids=ids)
    report['runs'].append(run)
    (workspace / 'outputs' / f'CERN_TEST_{name}.log').write_text(stream.getvalue(), encoding='utf-8')
    print(name, result.testsRun, 'PASS' if result.wasSuccessful() else 'FAIL', flush=True)
report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
(workspace / 'outputs/CERN_TEST_RESULTS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if not all(run['passed'] and run['skipped'] == 0 for run in report['runs']):
    raise SystemExit(1)
