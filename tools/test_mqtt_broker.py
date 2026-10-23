"""Broker smoke checks using the image's clients; run after broker startup.

These checks require a real Docker engine and do not run from --help.
The first TCP check uses the published host port. MQTT client checks execute
inside the broker container; host-native MQTT will be tested with the simulator.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import socket
import subprocess
import sys
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

    # Register a short-lived session synchronously. -E exits after SUBACK;
    # complete output is collected at process exit, without live log parsing.
    session_id = 'smoke-session-' + uuid.uuid4().hex
    subscriber_args = [*common, '-u', backend['username'], '-P', backend['password'],
                       '-i', session_id]

    def checked(client, args, stage, raw=None):
        rc, output = execute(client, *args, raw=raw)
        if rc or 'not authori' in output.lower():
            for role in (backend, publisher):
                output = output.replace(role['password'], '[REDACTED]')
            raise RuntimeError(f'{stage}: exit={rc}; output={output.strip()[-2000:]}')
        return output

    try:
        checked('mosquitto_sub', [*subscriber_args, '-c', '-x', '60', '-E', '-W', '10'],
                'Subscription registration')
        print('PASS backend subscription acknowledged; temporary session registered')
        checked('mosquitto_pub',
                [*common, '-u', publisher['username'], '-P', publisher['password'], '-s'],
                'Authenticated publish', raw)
        # QoS 1 queues the sample for this registered, briefly offline session.
        output = checked('mosquitto_sub',
                         [*subscriber_args, '-c', '-x', '0', '-v', '-C', '1', '-W', '10'],
                         'Receive queued sample')
        received = [line[len(topic) + 1:] for line in output.splitlines()
                    if line.startswith(topic + ' ')]
        if len(received) != 1 or json.loads(received[0]) != payload:
            raise RuntimeError('Expected identical JSON sample was not received.')
        print('PASS simulator publish -> backend subscribe: complete JSON payload matches')
        print('Broker smoke checks passed. Temporary session delivery only; '
              'no restart, disk durability, retain or simulator claims yet.')
    finally:
        # Clean Start + zero expiry clears any remaining test session.
        # If cleanup cannot connect, the original session expires after 60 s.
        try:
            checked('mosquitto_sub', [*subscriber_args, '-x', '0', '-E', '-W', '5'],
                    'Temporary session cleanup')
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            print('WARNING temporary session cleanup could not be confirmed; '
                  'session expiry bounds leftover state.', file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        # Avoid echoing command arrays containing development passwords.
        message = 'Docker client operation timed out.' if isinstance(exc, subprocess.TimeoutExpired) else str(exc)
        print(f'Broker smoke check failed: {message}', file=sys.stderr)
        sys.exit(1)
