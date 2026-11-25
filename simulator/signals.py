"""Offline synthetic IMU signal generation, independent of MQTT and validation I/O."""
from datetime import timedelta
import math
import random
import re
from uuid import UUID, uuid5


def idle_samples(device_id, stream_id, start, count=10, rate_hz=10, seed=42):
    """Yield the original stationary signal."""
    return imu_samples(device_id, stream_id, start, count, rate_hz, seed)


SCENARIOS = ('idle', 'motion', 'jump', 'landing')


def imu_samples(device_id, stream_id, start, count=10, rate_hz=10, seed=42, *, scenario='idle'):
    """Generate illustrative observations; jump models only the airborne segment."""
    if scenario not in SCENARIOS:
        raise ValueError('unknown IMU scenario')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', device_id):
        raise ValueError('device_id must match the MQTT contract')
    if not isinstance(count, int) or not 1 <= count <= 10000:
        raise ValueError('count must be an integer from 1 to 10000')
    if not 1 <= rate_hz <= 1000:
        raise ValueError('rate_hz must be from 1 to 1000')
    if start.tzinfo is None or start.utcoffset() != timedelta(0):
        raise ValueError('start must be timezone-aware UTC')
    stream = UUID(str(stream_id))
    rng = random.Random(seed)
    for sequence in range(count):
        sampled_at = start + timedelta(seconds=sequence / rate_hz)
        acceleration = {axis: round(rng.uniform(-0.03, 0.03), 6) for axis in 'xyz'}
        acceleration['z'] = round(acceleration['z'] + 9.81, 6)
        angular_velocity = {axis: round(rng.uniform(-0.003, 0.003), 6) for axis in 'xyz'}
        t = sequence / rate_hz
        if scenario == 'motion':
            phase = 2 * math.pi * t
            acceleration['x'] += 1.5 * math.sin(phase)
            acceleration['y'] += 0.7 * math.cos(phase)
            angular_velocity['z'] += 0.8 * math.cos(phase)
        elif scenario == 'jump':
            acceleration['z'] = round(acceleration['z'] - 9.81, 6)
        elif scenario == 'landing':
            acceleration['z'] += 15 * math.exp(-8 * t)

        yield {
            'schemaVersion': 1,
            'messageId': str(uuid5(stream, f'{device_id}:{sequence}')),
            'deviceId': device_id,
            'streamId': str(stream),
            'sequence': sequence,
            'sampledAt': sampled_at.isoformat(timespec='microseconds').replace('+00:00', 'Z'),
            'accelerationMps2': acceleration,
            'angularVelocityRadps': angular_velocity,
        }
