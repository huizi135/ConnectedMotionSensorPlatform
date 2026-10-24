"""Status contract and cached/live interpretation; no broker required."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
from uuid import UUID

from simulator.status_demo import status_payload, encode_status, StatusObservation, validators, run_device

TOPIC = 'motion/v1/devices/sim-status-001/status'
CONNECTION = UUID('00c46f11-2f1c-48a6-bcc1-0f0c45ae76ad')


class StatusTests(unittest.TestCase):
    def message(self, state, retained=False, connection=CONNECTION, will=False):
        return SimpleNamespace(topic=TOPIC, retain=retained, payload=json.dumps(
            status_payload('sim-status-001', connection, state, will=will)).encode())

    def test_generated_states_match_contract(self):
        checks = validators()
        for state, will in [('online', False), ('offline', False), ('offline', True)]:
            payload = status_payload('sim-status-001', CONNECTION, state, will=will)
            encode_status(payload, TOPIC, checks)
            self.assertEqual(payload['reportedAt'] is None, will)
        with self.assertRaises(ValueError):
            status_payload('sim-status-001', CONNECTION, 'online', will=True)

    @patch('builtins.print')
    def test_cached_online_does_not_prove_live_transition(self, _):
        observation = StatusObservation(TOPIC, validators())
        observation.accept(self.message('online', retained=True))
        observation.accept(self.message('offline', will=True))
        self.assertFalse(observation.completed)

    def test_fractional_status_timestamps(self):
        checks = validators()
        for stamp in ['2026-10-24T10:00:00Z', '2026-10-24T10:00:00.123Z',
                      '2026-10-24T10:00:00.123456Z']:
            payload = status_payload('sim-status-001', CONNECTION, 'online')
            payload['reportedAt'] = stamp
            encode_status(payload, TOPIC, checks)
        payload['reportedAt'] = '2026-10-24T10:00:00.1234567Z'
        with self.assertRaises(ValueError):
            encode_status(payload, TOPIC, checks)

    @patch('builtins.print')
    def test_same_connection_required(self, _):
        observation = StatusObservation(TOPIC, validators())
        observation.accept(self.message('online'))
        observation.accept(self.message('offline', connection=UUID(int=1)))
        self.assertFalse(observation.completed)
        observation.accept(self.message('offline', will=True))
        self.assertTrue(observation.completed)

    @patch('builtins.print')
    def test_snapshot_must_be_retained_and_match_state(self, _):
        observation = StatusObservation(TOPIC, validators())
        with self.assertRaises(ValueError):
            observation.accept(self.message('offline'), snapshot=True)
        with self.assertRaises(ValueError):
            observation.accept(self.message('online', retained=True), snapshot=True)
        observation.accept(self.message('offline', retained=True), snapshot=True)
        self.assertTrue(observation.completed)

    def test_invalid_payload_and_topic_rejected(self):
        observation = StatusObservation(TOPIC, validators())
        message = self.message('online')
        message.topic = 'motion/v1/devices/wrong-device/status'
        with self.assertRaises(ValueError):
            observation.accept(message)

    @patch('builtins.print')
    def test_will_registered_before_connect_and_graceful_order(self, _):
        events = []
        connection = Mock(connected=True, error=None)
        connection.open.side_effect = lambda: events.append('connect')
        connection.client.will_set.side_effect = lambda *a, **k: events.append('will')
        connection.close.side_effect = lambda: events.append('close')
        def send(c, payload, topic, checks):
            events.append(payload['state'])
        args = SimpleNamespace(device_id='sim-status-001', seconds=1, exit_mode='graceful')
        with patch('simulator.status_demo.Connection', return_value=connection), patch(
                'simulator.status_demo.send_status', side_effect=send):
            run_device({}, args, TOPIC, validators())
        self.assertEqual(events, ['will', 'connect', 'online', 'offline', 'close'])


if __name__ == '__main__':
    unittest.main()
