"""Demonstrate retained status, graceful offline and unexpected-disconnect Will."""
import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
import time
from uuid import uuid4

import paho.mqtt.client as mqtt
from .mqtt_demo import Connection, ROOT, validate_message, validators


def status_payload(device_id, connection_id, state, *, will=False):
    if will and state != 'offline':
        raise ValueError('Will must represent offline')
    return {
        'schemaVersion': 1, 'deviceId': device_id,
        'connectionId': str(connection_id), 'state': state,
        'reportedAt': None if will else datetime.now(timezone.utc).isoformat(
            timespec='microseconds').replace('+00:00', 'Z'),
    }


def encode_status(payload, topic, checks):
    raw = json.dumps(payload, allow_nan=False, separators=(',', ':'))
    errors = validate_message(topic, raw, checks)
    if errors:
        raise ValueError('Status contract violation: ' + '; '.join(errors))
    return raw


def send_status(connection, payload, topic, checks):
    info = connection.client.publish(topic, encode_status(payload, topic, checks),
                                     qos=1, retain=True)
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError('Status could not be queued')
    connection.wait(lambda: info.mid in connection.acknowledged, 10, 'Status PUBACK')
    connection.acknowledged.remove(info.mid)
    print('ACK status=' + payload['state'] + ' connectionId=' + payload['connectionId'], flush=True)


def run_device(credentials, args, topic, checks):
    connection_id = uuid4()
    connection = Connection(credentials, 'simulator')
    will = status_payload(args.device_id, connection_id, 'offline', will=True)
    # Register before CONNECT. Broker publishes this only on unexpected disconnect.
    connection.client.will_set(topic, encode_status(will, topic, checks), qos=1, retain=True)
    online = False
    try:
        connection.open()
        send_status(connection, status_payload(args.device_id, connection_id, 'online'), topic, checks)
        online = True
        print(f'DEVICE active for {args.seconds}s; exit-mode={args.exit_mode}', flush=True)
        until = time.monotonic() + args.seconds
        try:
            connection.wait(lambda: time.monotonic() >= until, args.seconds + 2, 'Device lifetime')
        except KeyboardInterrupt:
            print('User interruption: attempting graceful offline.', flush=True)
        else:
            if args.exit_mode == 'abrupt':
                print('SIMULATED CRASH: exit 17, no offline publish and no MQTT DISCONNECT.', flush=True)
                os._exit(17)  # Exit only this demo process; intentionally bypass finally.
    finally:
        try:
            if online and connection.connected and not connection.error:
                send_status(connection, status_payload(args.device_id, connection_id, 'offline'), topic, checks)
                print('PASS device: graceful offline acknowledged.', flush=True)
        finally:
            connection.close()


class StatusObservation:
    """Keep cached announcements distinct from observed live transitions."""
    def __init__(self, topic, checks):
        self.topic = topic
        self.checks = checks
        self.live_connection = None
        self.completed = False
        self.snapshot = None

    def accept(self, message, snapshot=False, expected='offline'):
        raw = message.payload.decode('utf-8')
        errors = validate_message(message.topic, raw, self.checks)
        if message.topic != self.topic or errors:
            raise ValueError('Invalid status message: ' + '; '.join(errors))
        payload = json.loads(raw)
        print(('CACHED ' if message.retain else 'LIVE ') + raw, flush=True)
        if snapshot:
            if not message.retain or payload['state'] != expected:
                raise ValueError('Expected a retained ' + expected + ' snapshot')
            self.snapshot = payload
            self.completed = True
        elif not message.retain:
            if payload['state'] == 'online':
                self.live_connection = payload['connectionId']
            elif payload['connectionId'] == self.live_connection:
                self.completed = True
        return payload


def observe(credentials, args, topic, checks):
    connection = Connection(credentials, 'backend')
    observed = StatusObservation(topic, checks)
    def on_message(client, userdata, message):
        try:
            observed.accept(message, snapshot=args.mode == 'snapshot', expected=args.expect)
        except (ValueError, UnicodeError, KeyError) as exc:
            connection.error = 'Status observation rejected: ' + str(exc)
    connection.client.on_message = on_message
    try:
        connection.open()
        rc, _ = connection.client.subscribe(topic, qos=1)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError('Status subscription could not be queued')
        connection.wait(lambda: connection.subscribed, 10, 'Status SUBACK')
        print('READY: status subscription accepted.', flush=True)
        connection.wait(lambda: observed.completed, args.timeout, 'Status observation')
        if args.mode == 'snapshot':
            print('PASS snapshot: retained ' + args.expect + ' received; announcement only.', flush=True)
        else:
            print('PASS watch: live online -> offline for the same connectionId.', flush=True)
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['watch', 'device', 'snapshot'])
    parser.add_argument('--device-id', default='sim-status-001')
    parser.add_argument('--seconds', type=int, default=8)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--exit-mode', choices=['graceful', 'abrupt'], default='graceful')
    parser.add_argument('--expect', choices=['online', 'offline'], default='offline')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', args.device_id):
        parser.error('Invalid device ID')
    if not 1 <= args.seconds <= 300 or not 1 <= args.timeout <= 300:
        parser.error('seconds and timeout must be 1..300')
    credentials = json.loads((ROOT / 'secrets/mqtt/clients.json').read_text(encoding='utf-8'))
    topic = f'motion/v1/devices/{args.device_id}/status'
    checks = validators()
    if args.mode == 'device':
        run_device(credentials, args, topic, checks)
    else:
        observe(credentials, args, topic, checks)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f'Status demo failed: {exc}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Observer stopped by user.', file=sys.stderr)
        sys.exit(130)
