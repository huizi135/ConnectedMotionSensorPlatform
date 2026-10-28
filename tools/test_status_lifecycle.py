"""Real local-broker status acceptance; uses existing ignored credentials.

Run after initialize_mqtt.py and Compose broker startup. This test launches only
its own bounded device processes. It never restarts Docker or deletes volumes.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulator.mqtt_demo import Connection, mqtt, validate_message, validators


def assert_transition(events, device_id, abrupt):
    """Check identity, order and time semantics independently of CLI text."""
    if len(events) != 2:
        raise RuntimeError('Expected exactly online and offline status observations')
    online, offline = events
    if online['deviceId'] != device_id or offline['deviceId'] != device_id:
        raise RuntimeError('Status belongs to a different device')
    if online['state'] != 'online' or offline['state'] != 'offline':
        raise RuntimeError('Expected online -> offline')
    if online['connectionId'] != offline['connectionId']:
        raise RuntimeError('Connection identity changed during transition')
    if online['reportedAt'] is None:
        raise RuntimeError('Online status needs a device-reported timestamp')
    if (offline['reportedAt'] is None) != abrupt:
        raise RuntimeError('Offline time does not match graceful/Will semantics')


def receive_callback(connection, topic, checks, messages):
    def on_message(client, userdata, message):
        try:
            raw = message.payload.decode('utf-8')
            errors = validate_message(message.topic, raw, checks)
            if message.topic != topic or errors:
                raise ValueError('Unexpected topic or invalid status contract')
            messages.append((json.loads(raw), bool(message.retain)))
        except (ValueError, UnicodeError) as exc:
            connection.error = 'Status reception failed: ' + str(exc)
    return on_message


def subscribe(connection, topic):
    connection.open()
    rc, _ = connection.client.subscribe(topic, qos=1)
    if rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError('Status subscribe could not be queued')
    connection.wait(lambda: connection.subscribed, 10, 'Status SUBACK')


def snapshot(credentials, topic, checks, expected):
    connection = Connection(credentials, 'backend')
    messages = []
    connection.client.on_message = receive_callback(connection, topic, checks, messages)
    try:
        subscribe(connection, topic)
        connection.wait(lambda: bool(messages), 10, 'Retained snapshot')
        payload, retained = messages[0]
        if not retained or payload != expected:
            raise RuntimeError('Retained snapshot differs from observed offline status')
    finally:
        connection.close()


def clear_test_status(credentials, topic):
    """Delete only this unique test topic's retained message, not stored volumes."""
    connection = Connection(credentials, 'simulator')
    try:
        connection.open()
        info = connection.client.publish(topic, b'', qos=1, retain=True)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError('Retained cleanup could not be queued')
        connection.wait(lambda: info.mid in connection.acknowledged, 10, 'Retained cleanup PUBACK')
    finally:
        connection.close()


def run_case(credentials, checks, abrupt):
    device_id = 'status-check-' + uuid4().hex
    topic = f'motion/v1/devices/{device_id}/status'
    observer = Connection(credentials, 'backend')
    messages = []
    child = None
    observer.client.on_message = receive_callback(observer, topic, checks, messages)
    mode = 'abrupt' if abrupt else 'graceful'
    try:
        subscribe(observer, topic)
        child = subprocess.Popen(
            [sys.executable, '-m', 'simulator.status_demo', 'device',
             '--device-id', device_id, '--seconds', '1', '--exit-mode', mode],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        # Observe broker events directly; never parse subprocess READY/debug logs.
        observer.wait(lambda: any(p['state'] == 'offline' for p, _ in messages),
                      45, mode + ' status transition')
        output, _ = child.communicate(timeout=10)
        expected_exit = 17 if abrupt else 0
        if child.returncode != expected_exit:
            raise RuntimeError(f'{mode} device exit={child.returncode}: {output[-2000:]}')
        live = [p for p, retained in messages if not retained]
        # QoS 1 may repeat a delivery; compare unique, identical observations.
        unique = []
        for payload in live:
            if payload not in unique:
                unique.append(payload)
        assert_transition(unique, device_id, abrupt)
        print(f'PASS {mode}: live online -> offline, matching connectionId and time semantics', flush=True)
        snapshot(credentials, topic, checks, unique[-1])
        print(f'PASS {mode}: new subscriber received identical retained offline', flush=True)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate(timeout=5)
        observer.close()
        try:
            clear_test_status(credentials, topic)
        except (RuntimeError, OSError):
            print('WARNING cleanup not confirmed for unique test topic: ' + topic, file=sys.stderr)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    with socket.create_connection(('127.0.0.1', 1883), timeout=5):
        pass
    credentials = json.loads((ROOT / 'secrets/mqtt/clients.json').read_text(encoding='utf-8'))
    checks = validators()
    run_case(credentials, checks, abrupt=False)
    run_case(credentials, checks, abrupt=True)
    print('PASS status lifecycle: graceful, simulated process crash and retained snapshots. '
          'No network-blackhole, broker-restart or database guarantee.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print('Status acceptance failed: ' + str(exc), file=sys.stderr)
        print('Confirm Docker Desktop, broker startup and existing local credentials.', file=sys.stderr)
        sys.exit(1)
