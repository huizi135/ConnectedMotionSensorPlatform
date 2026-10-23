"""Initialize ignored local client credentials and a Docker auth volume.

Run from the repository using its existing Python virtual environment.
No third-party Python dependency is required for this script.
"""
from pathlib import Path
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / 'infrastructure/compose.yaml'
CLIENTS = ROOT / 'secrets/mqtt/clients.json'


def run_docker(arguments, *, input_text=None, capture=False):
    result = subprocess.run(
        ['docker', *arguments], cwd=ROOT, input=input_text, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode:
        detail = (result.stderr or '').strip() if capture else 'See Docker output above.'
        raise RuntimeError(f'Docker operation failed (exit {result.returncode}). {detail}')
    return result.stdout.strip() if capture else ''


def compose(*args, **kwargs):
    return run_docker(['compose', '--file', str(COMPOSE), *args], **kwargs)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if not shutil.which('docker'):
        raise RuntimeError('Docker CLI not found in PATH.')
    if run_docker(['info', '--format', '{{.OSType}}'], capture=True) != 'linux':
        raise RuntimeError('A reachable Linux Docker engine is required.')
    compose('config', '--quiet')
    running = compose('ps', '--status', 'running', '--quiet', 'mosquitto', capture=True)
    if running:
        if CLIENTS.exists():
            print('Broker is already running and the local credential file exists. Nothing changed.')
            return
        raise RuntimeError('Broker is running but local credentials are missing. Stop and recover them first.')
    ignored = subprocess.run(
        ['git', 'check-ignore', '--quiet', 'secrets/mqtt/clients.json'], cwd=ROOT,
    )
    if ignored.returncode:
        raise RuntimeError('secrets/mqtt/clients.json must be ignored by Git before generating credentials.')

    existed = CLIENTS.exists()
    if existed:
        clients = json.loads(CLIENTS.read_text(encoding='utf-8'))
        print('Reusing existing ignored local credentials; passwords will not be rotated.')
    else:
        clients = {
            'host': '127.0.0.1', 'port': 1883,
            'simulator': {'username': 'simulator', 'password': secrets.token_urlsafe(24)},
            'backend': {'username': 'backend', 'password': secrets.token_urlsafe(24)},
        }
    for role in ('simulator', 'backend'):
        item = clients[role]
        if item['username'] != role or not isinstance(item['password'], str):
            raise RuntimeError('Unexpected local credential structure.')
        if len(item['password']) < 24 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in item['password']):
            raise RuntimeError('Unexpected generated password format.')

    compose('--profile', 'tools', 'pull', 'mqtt-init')
    if not existed:
        # Refuse a lost-local-file scenario before writing new credentials.
        compose('--profile', 'tools', 'run', '--rm', '--no-deps', '-T',
                'mqtt-init', '/init/initialize.sh', 'check-new')
        CLIENTS.parent.mkdir(parents=True, exist_ok=True)
        pending = CLIENTS.with_suffix('.pending')
        # Save before Docker initialization so retries reuse exactly the same credentials.
        with pending.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(clients, stream, indent=2)
            stream.write('\n')
        os.chmod(pending, 0o600)
        pending.replace(CLIENTS)
    mode = 'reuse' if existed else 'new'
    compose(
        '--profile', 'tools', 'run', '--rm', '--no-deps', '-T',
        'mqtt-init', '/init/initialize.sh', mode,
        input_text=clients['simulator']['password'] + '\n' + clients['backend']['password'] + '\n',
    )
    print('Ready: two MQTT roles initialized; local credentials stay under ignored secrets/mqtt/.')
    print('Next: docker compose -f infrastructure/compose.yaml up -d mosquitto')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f'Initialization failed: {exc}', file=sys.stderr)
        sys.exit(1)
