"""Assertions used by real-broker acceptance; no Docker required here."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from test_status_lifecycle import assert_transition


class StatusAcceptanceTests(unittest.TestCase):
    def events(self, abrupt=False):
        base = {'deviceId': 'device-1', 'connectionId': 'connection-1',
                'state': 'online', 'reportedAt': '2026-10-28T10:00:00Z'}
        offline = dict(base, state='offline', reportedAt=None if abrupt else '2026-10-28T10:00:01Z')
        return [base, offline]

    def test_accepts_both_lifecycles(self):
        for abrupt in (False, True):
            assert_transition(self.events(abrupt), 'device-1', abrupt)

    def test_rejects_wrong_state_order(self):
        with self.assertRaises(RuntimeError):
            assert_transition(self.events()[::-1], 'device-1', False)

    def test_rejects_identity_or_device_mismatch(self):
        for key in ('connectionId', 'deviceId'):
            events = copy.deepcopy(self.events())
            events[1][key] = 'wrong'
            with self.assertRaises(RuntimeError):
                assert_transition(events, 'device-1', False)

    def test_rejects_wrong_timestamp_semantics(self):
        for abrupt in (False, True):
            with self.assertRaises(RuntimeError):
                assert_transition(self.events(not abrupt), 'device-1', abrupt)
        events = self.events()
        events[0]['reportedAt'] = None
        with self.assertRaises(RuntimeError):
            assert_transition(events, 'device-1', False)

    def test_requires_complete_transition(self):
        for events in ([], self.events()[:1], self.events() + self.events()):
            with self.assertRaises(RuntimeError):
                assert_transition(events, 'device-1', False)


if __name__ == '__main__':
    unittest.main()
