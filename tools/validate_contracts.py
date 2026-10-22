"""Offline contract regression checks; no broker, simulator or backend required.

After Python setup in Phase 1:
  python -m pip install -r tools/requirements-contracts.txt
  python tools/validate_contracts.py
"""
from pathlib import Path
import json
import math
import re
import sys
from importlib.metadata import version
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'contracts/mqtt/v1'
TOPIC = re.compile(r'motion/v1/devices/([a-z0-9][a-z0-9_-]{0,63})/(telemetry|status)\Z')


def reject_constant(value):
    raise ValueError(f'Invalid JSON numeric constant: {value}')


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def finite_numbers(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Number outside finite floating-point range')
    if isinstance(value, dict):
        for child in value.values():
            finite_numbers(child)
    if isinstance(value, list):
        for child in value:
            finite_numbers(child)


def read_payload(raw):
    obj = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique_keys)
    finite_numbers(obj)
    return obj


def validators():
    checker = FormatChecker()
    # Fail rather than silently ignoring date-time checking if dependencies are missing.
    if 'date-time' not in checker.checkers or 'uuid' not in checker.checkers:
        raise RuntimeError('Install jsonschema[format] to enable required format assertions')
    result = {}
    for kind in ['telemetry', 'status']:
        schema = json.loads((CONTRACTS / f'{kind}.schema.json').read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
        result[kind] = Draft202012Validator(schema, format_checker=checker)
    return result


def validate_message(topic, raw, checks):
    match = TOPIC.fullmatch(topic)
    if match is None:
        return ['Unsupported topic or invalid device identity']
    try:
        obj = read_payload(raw)
    except (ValueError, TypeError) as exc:
        return [str(exc)]
    errors = [error.message for error in checks[match[2]].iter_errors(obj)]
    if isinstance(obj, dict) and obj.get('deviceId') != match[1]:
        errors.append('Topic/payload deviceId mismatch')
    return errors


def main():
    checks = validators()
    examples = [
        ('telemetry.json', 'telemetry'),
        ('status-online.json', 'status'),
        ('status-offline-will.json', 'status'),
    ]
    results = []
    for filename, kind in examples:
        raw = (CONTRACTS / 'examples' / filename).read_text(encoding='utf-8')
        errors = validate_message(f'motion/v1/devices/sim-001/{kind}', raw, checks)
        results.append((f'example {filename}', not errors))
    vectors = json.loads((CONTRACTS / 'validation-cases.json').read_text(encoding='utf-8'))
    for case in vectors:
        raw = case['rawPayload'] if 'rawPayload' in case else json.dumps(case['payload'], allow_nan=False)
        errors = validate_message(case['topic'], raw, checks)
        observed = not errors
        passed = observed == case['expectedValid']
        results.append((case['name'], passed))
        if not passed:
            print(f"MISMATCH: {case['name']}: expected valid={case['expectedValid']}; errors={errors}")
    for name, passed in results:
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    total = len(results)
    passed = sum(result for _, result in results)
    print(f'jsonschema {version("jsonschema")}; Python {sys.version.split()[0]}')
    print(f'{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
