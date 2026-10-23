"""Print validated idle telemetry as JSON Lines; this step does not use MQTT."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from .signals import idle_samples

# Reuse the repository's existing contract checker at this CLI boundary.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from validate_contracts import validate_message, validators


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device-id', default='sim-001')
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--rate-hz', type=int, default=10)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    checks = validators()
    topic = f'motion/v1/devices/{args.device_id}/telemetry'
    try:
        samples = idle_samples(args.device_id, uuid4(), datetime.now(timezone.utc),
                               args.samples, args.rate_hz, args.seed)
        for sample in samples:
            raw = json.dumps(sample, allow_nan=False, separators=(',', ':'))
            errors = validate_message(topic, raw, checks)
            if errors:
                raise ValueError('; '.join(errors))
            print(raw)
    except ValueError as exc:
        parser.error(str(exc))
    print(f'PASS offline idle: {args.samples} contract-valid samples; '
          f'{args.rate_hz} Hz logical timestamps; no MQTT, no real-time pacing.', file=sys.stderr)


if __name__ == '__main__':
    main()
