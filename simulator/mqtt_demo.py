"""Bounded host-native MQTT demo: subscribe first in one terminal, then publish."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from uuid import uuid4

import paho.mqtt.client as mqtt
from .signals import idle_samples

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validate_contracts import validate_message, validators


class Connection:
    """Single-threaded network loop; inspect MQTT v5 reason codes directly."""
    def __init__(self, credentials, role):
        self.connected = False
        self.error = None
        self.subscribed = False
        self.acknowledged = set()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id='demo-' + uuid4().hex,
                                  protocol=mqtt.MQTTv5, reconnect_on_failure=False)
        self.client.connect_timeout = 5
        self.client.username_pw_set(credentials[role]['username'], credentials[role]['password'])
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish

    def on_connect(self, client, userdata, flags, reason, properties):
        if reason.is_failure:
            self.error = 'MQTT connection refused: ' + str(reason)
        else:
            self.connected = True

    def on_disconnect(self, client, userdata, flags, reason, properties):
        self.connected = False
        self.error = 'MQTT connection closed: ' + str(reason)

    def on_subscribe(self, client, userdata, mid, reasons, properties):
        if not reasons or any(reason.is_failure for reason in reasons):
            self.error = 'MQTT subscription refused'
        else:
            self.subscribed = True

    def on_publish(self, client, userdata, mid, reason, properties):
        if reason.is_failure:
            self.error = 'MQTT publish refused: ' + str(reason)
        else:
            self.acknowledged.add(mid)

    def wait(self, predicate, timeout, stage):
        deadline = time.monotonic() + timeout
        while True:
            if self.error:
                raise RuntimeError(self.error)
            if predicate():
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(stage + ' timed out')
            rc = self.client.loop(timeout=min(0.1, remaining))
            if rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(stage + ': network loop failed: ' + mqtt.error_string(rc))

    def open(self):
        self.client.connect('127.0.0.1', 1883, keepalive=30,
                            clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY)
        self.wait(lambda: self.connected, 10, 'CONNACK')

    def close(self):
        self.client.disconnect()
        self.client.loop(timeout=0.1)


def publish(connection, args, checks, topic):
    stream = uuid4()
    start = datetime.now(timezone.utc)
    clock_start = time.monotonic()
    for sample in idle_samples(args.device_id, stream, start, args.samples, 10, args.seed):
        # Ideal sample time is explicit; desktop scheduling is not hard real time.
        target = clock_start + sample['sequence'] / 10
        connection.wait(lambda: time.monotonic() >= target, 10, 'Pacing')
        raw = json.dumps(sample, allow_nan=False, separators=(',', ':'))
        errors = validate_message(topic, raw, checks)
        if errors:
            raise RuntimeError('Generated payload invalid: ' + '; '.join(errors))
        info = connection.client.publish(topic, raw, qos=1, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError('Publish could not be queued')
        connection.wait(lambda: info.mid in connection.acknowledged, 10, 'PUBACK')
        connection.acknowledged.remove(info.mid)
        print(f'ACK sequence={sample["sequence"]} messageId={sample["messageId"]}', flush=True)
    print(f'PASS publisher: {args.samples} successful broker PUBACKs; no database guarantee.', flush=True)


def subscribe(connection, args, checks, topic):
    seen = {}
    received_stream = None

    def on_message(client, userdata, message):
        nonlocal received_stream
        try:
            raw = message.payload.decode('utf-8')
            errors = validate_message(message.topic, raw, checks)
            if errors:
                raise ValueError('; '.join(errors))
            sample = json.loads(raw)
            if message.retain:
                raise ValueError('Unexpected retained telemetry')
            identity = sample['messageId']
            if identity in seen:
                if seen[identity] != sample:
                    raise ValueError('Conflicting duplicate message identity')
                return
            if received_stream is not None and sample['streamId'] != received_stream:
                raise ValueError('Multiple publishers/streams on this demo topic')
            if sample['sequence'] != len(seen):
                raise ValueError('Expected this demo to start at sequence 0 without gaps')
            received_stream = sample['streamId']
            seen[identity] = sample
            print(raw, flush=True)
        except (UnicodeError, ValueError, KeyError) as exc:
            connection.error = 'Received sample rejected: ' + str(exc)

    connection.client.on_message = on_message
    rc, _ = connection.client.subscribe(topic, qos=1)
    if rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError('Subscribe could not be queued')
    connection.wait(lambda: connection.subscribed, 10, 'SUBACK')
    print('READY: subscription accepted. Start publisher in terminal B now.', flush=True)
    connection.wait(lambda: len(seen) >= args.samples, args.timeout, 'Receive samples')
    print(f'PASS subscriber: {len(seen)} unique contract-valid samples, contiguous sequence; '
          'in-memory verification only.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['subscribe', 'publish'])
    parser.add_argument('--device-id', default='sim-live-001')
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', args.device_id):
        parser.error('Invalid device ID')
    if not 1 <= args.samples <= 1000 or not 1 <= args.timeout <= 300:
        parser.error('samples must be 1..1000; timeout must be 1..300 seconds')
    checks = validators()
    credentials = json.loads((ROOT / 'secrets/mqtt/clients.json').read_text(encoding='utf-8'))
    connection = Connection(credentials, 'simulator' if args.mode == 'publish' else 'backend')
    try:
        connection.open()
        topic = f'motion/v1/devices/{args.device_id}/telemetry'
        (publish if args.mode == 'publish' else subscribe)(connection, args, checks, topic)
    finally:
        connection.close()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f'MQTT demo failed: {exc}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Stopped by user; no replay guarantee.', file=sys.stderr)
        sys.exit(130)
