"""Protocol-result checks without opening a network connection."""
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from datetime import datetime, timezone
import json
from uuid import UUID
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

from simulator.mqtt_demo import Connection, subscribe, validators
from simulator.signals import idle_samples


class MqttResultTests(unittest.TestCase):
    def connection(self):
        return Connection({'simulator': {'username': 'simulator', 'password': 'test-only'}}, 'simulator')

    def test_puback_failure_is_not_success(self):
        c = self.connection()
        c.on_publish(None, None, 12, ReasonCode(PacketTypes.PUBACK, identifier=135), None)
        self.assertNotIn(12, c.acknowledged)
        with self.assertRaisesRegex(RuntimeError, 'publish refused'):
            c.wait(lambda: True, 1, 'test')

    def test_successful_puback(self):
        c = self.connection()
        c.on_publish(None, None, 12, ReasonCode(PacketTypes.PUBACK, identifier=0), None)
        self.assertIn(12, c.acknowledged)

    def test_subscription_refusal(self):
        c = self.connection()
        c.on_subscribe(None, None, 1, [ReasonCode(PacketTypes.SUBACK, identifier=135)], None)
        self.assertFalse(c.subscribed)
        with self.assertRaisesRegex(RuntimeError, 'subscription refused'):
            c.wait(lambda: c.subscribed, 1, 'test')

    def test_connection_refusal(self):
        c = self.connection()
        c.on_connect(None, None, None, ReasonCode(PacketTypes.CONNACK, identifier=135), None)
        self.assertFalse(c.connected)
        self.assertIn('connection refused', c.error)

    def test_network_failure_and_bounded_wait(self):
        c = self.connection()
        c.client.loop = Mock(return_value=mqtt.MQTT_ERR_CONN_LOST)
        with self.assertRaisesRegex(RuntimeError, 'network loop failed'):
            c.wait(lambda: False, 1, 'receive')
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            c.wait(lambda: False, 0, 'receive')

    def receive(self, samples, expected):
        c = self.connection()
        c.subscribed = True
        c.client.subscribe = Mock(return_value=(mqtt.MQTT_ERR_SUCCESS, 1))
        messages = iter(samples)
        def loop(**kwargs):
            c.client.on_message(c.client, None, SimpleNamespace(
                topic='motion/v1/devices/sim-001/telemetry', retain=False,
                payload=json.dumps(next(messages)).encode()))
            return mqtt.MQTT_ERR_SUCCESS
        c.client.loop = loop
        with patch('builtins.print'):
            subscribe(c, SimpleNamespace(samples=expected, timeout=1), validators(),
                      'motion/v1/devices/sim-001/telemetry')

    def samples(self):
        return list(idle_samples('sim-001', UUID(int=1),
                                datetime(2026, 10, 23, tzinfo=timezone.utc), count=2))

    def test_duplicate_delivery_does_not_increase_unique_count(self):
        a, b = self.samples()
        self.receive([a, a, b], 2)

    def test_conflicting_duplicate_rejected(self):
        a, _ = self.samples()
        conflict = dict(a, accelerationMps2={'x': 0, 'y': 0, 'z': 1})
        with self.assertRaisesRegex(RuntimeError, 'Conflicting duplicate'):
            self.receive([a, conflict], 2)

    def test_midstream_start_rejected_by_demo(self):
        _, b = self.samples()
        with self.assertRaisesRegex(RuntimeError, 'start at sequence 0'):
            self.receive([b], 1)


if __name__ == '__main__':
    unittest.main()
