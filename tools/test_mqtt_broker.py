"""Broker smoke checks using the image's clients; run after broker startup.

These checks require a real Docker engine and do not run from --help.
The first TCP check uses the published host port. MQTT client checks execute
inside the broker container; host-native MQTT will be tested with the simulator.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import queue
import socket
import subprocess
import sys
import threading
import time
import uuid

from validate_contracts import validators, validate_message

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / 'infrastructure/compose.yaml'


def command(client, *args):
    return ['docker', 'compose', '--file', str(COMPOSE), 'exec', '-T',
            'mosquitto', client, *args]


def execute(client, *args, raw=None):
    result = subprocess.run(command(client, *args), cwd=ROOT, input=raw, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=25)
    return result.returncode, result.stdout


def expect_denied(label, args, raw=None, *, publish_refusal=False):
    rc, output = execute('mosquitto_pub', *args, raw=raw)
    # MQTT v5 publish rejection can be reported as a warning with exit 0.
    # Accept that observed client behavior only for the publish-ACL probe;
    # connection-authentication probes still require a nonzero exit status.
    text = output.lower()
    explicit_refusal = 'not authori' in text
    rejected_publish = publish_refusal and 'publish 1 failed: not authori' in text
    if not explicit_refusal or (rc == 0 and not rejected_publish):
        raise RuntimeError(f'{label}: expected explicit authorization refusal; exit={rc}; output={output.strip()}')
    print(f'PASS {label}: explicitly refused')


def read_lines(stream, messages):
    try:
        for line in stream:
            messages.put(line.rstrip('\r\n'))
    finally:
        messages.put(None)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    credentials = json.loads((ROOT / 'secrets/mqtt/clients.json').read_text(encoding='utf-8'))
    with socket.create_connection(('127.0.0.1', 1883), timeout=5):
        print('PASS published host TCP port reachable (not an MQTT authentication test)')
    topic_id = 'smoke-' + uuid.uuid4().hex
    topic = f'motion/v1/devices/{topic_id}/telemetry'
    payload = json.loads((ROOT / 'contracts/mqtt/v1/examples/telemetry.json').read_text(encoding='utf-8'))
    payload.update(deviceId=topic_id, messageId=str(uuid.uuid4()), streamId=str(uuid.uuid4()),
                   sequence=0, sampledAt=datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'))
    raw = json.dumps(payload, allow_nan=False)
    errors = validate_message(topic, raw, validators())
    if errors:
        raise RuntimeError('Generated smoke payload failed the existing contract: ' + '; '.join(errors))
    common = ['-h', '127.0.0.1', '-p', '1883', '-V', 'mqttv5', '-q', '1', '-t', topic]
    expect_denied('anonymous connection', [*common, '-n'])
    expect_denied('incorrect password', [*common, '-u', 'simulator', '-P', 'intentionally-wrong', '-n'])
    backend = credentials['backend']
    publisher = credentials['simulator']
    expect_denied('backend publish outside its read-only role',
                  [*common, '-u', backend['username'], '-P', backend['password'], '-s'], raw,
                  publish_refusal=True)

    messages = queue.Queue()
    subscriber = subprocess.Popen(
        command('mosquitto_sub', *common, '-u', backend['username'], '-P', backend['password'],
                '-v', '-d', '-C', '1', '-W', '20'), cwd=ROOT,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
    )
    reader = threading.Thread(target=read_lines, args=(subscriber.stdout, messages), daemon=True)
    reader.start()
    try:
        # Wait for the actual SUBACK, not a guessed sleep before publishing.
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                line = messages.get(timeout=0.25)
            except queue.Empty:
                continue
            if line is None:
                raise RuntimeError('Subscriber exited before SUBACK.')
            if 'received SUBACK' in line:
                break
        else:
            raise RuntimeError('Subscriber readiness timed out before SUBACK.')
        rc, output = execute('mosquitto_pub', *common, '-u', publisher['username'],
                             '-P', publisher['password'], '-s', raw=raw)
        if rc:
            raise RuntimeError(f'Authenticated publish failed (exit {rc}): {output.strip()}')
        matched = False
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                line = messages.get(timeout=0.25)
            except queue.Empty:
                continue
            if line is None:
                break
            if line.startswith(topic + ' '):
                received = json.loads(line[len(topic) + 1:])
                if received != payload:
                    raise RuntimeError('Received payload differs from the generated sample.')
                matched = True
                break
        if not matched:
            raise RuntimeError('Expected sample not received by the authenticated backend subscriber.')
        if subscriber.wait(timeout=5):
            raise RuntimeError('Subscriber returned a failure status.')
        print('PASS simulator publish -> backend subscribe: complete JSON payload matches')
        print('Broker smoke checks passed. No persistence, restart, retain or simulator claims yet.')
    finally:
        if subscriber.poll() is None:
            subscriber.terminate()
            try:
                subscriber.wait(timeout=3)
            except subprocess.TimeoutExpired:
                subscriber.kill()
                subscriber.wait(timeout=3)
        # -W 20 also bounds the in-container subscriber if docker exec is interrupted.


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        # Avoid echoing command arrays containing development passwords.
        message = 'Docker client operation timed out.' if isinstance(exc, subprocess.TimeoutExpired) else str(exc)
        print(f'Broker smoke check failed: {message}', file=sys.stderr)
        sys.exit(1)
