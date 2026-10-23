"""Signal invariants and integration with the real versioned contract."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from validate_contracts import validate_message, validators
from simulator.signals import idle_samples

START = datetime(2026, 10, 23, tzinfo=timezone.utc)
STREAM = UUID('f7fe612b-a890-4f82-a746-a02bb7df03ce')


class IdleSignalTests(unittest.TestCase):
    def samples(self, **kwargs):
        return list(idle_samples('sim-001', STREAM, START, **kwargs))

    def test_reproducible_with_fixed_inputs(self):
        self.assertEqual(self.samples(seed=10), self.samples(seed=10))
        a, b = self.samples(seed=10), self.samples(seed=11)
        self.assertNotEqual(a[0]['accelerationMps2'], b[0]['accelerationMps2'])

    def test_identity_order_and_timestamps(self):
        samples = self.samples(count=20, rate_hz=10)
        self.assertEqual([s['sequence'] for s in samples], list(range(20)))
        self.assertEqual(len({s['messageId'] for s in samples}), 20)
        for i, sample in enumerate(samples):
            self.assertEqual(datetime.fromisoformat(sample['sampledAt']), START + timedelta(seconds=i / 10))
        other = list(idle_samples('sim-001', UUID(int=1), START, count=1))
        self.assertNotEqual(samples[0]['messageId'], other[0]['messageId'])

    def test_gravity_noise_and_reference_label_exclusion(self):
        for sample in self.samples(count=100):
            a, w = sample['accelerationMps2'], sample['angularVelocityRadps']
            self.assertLessEqual(abs(a['z'] - 9.81), 0.030001)
            self.assertTrue(all(abs(a[axis]) <= 0.03 for axis in 'xy'))
            self.assertTrue(all(abs(value) <= 0.003 for value in w.values()))
            self.assertNotIn('simulation', sample)
            self.assertNotIn('scenario', sample)

    def test_every_sample_matches_existing_contract(self):
        checks = validators()
        for sample in self.samples():
            self.assertEqual(validate_message('motion/v1/devices/sim-001/telemetry',
                                              json.dumps(sample), checks), [])

    def test_invalid_inputs(self):
        for options in ({'count': 0}, {'count': 10001}, {'rate_hz': 0}, {'rate_hz': 1001}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.samples(**options)
        with self.assertRaises(ValueError):
            list(idle_samples('invalid/topic', STREAM, START))
        with self.assertRaises(ValueError):
            list(idle_samples('sim-001', STREAM, START.replace(tzinfo=None)))


if __name__ == '__main__':
    unittest.main()
