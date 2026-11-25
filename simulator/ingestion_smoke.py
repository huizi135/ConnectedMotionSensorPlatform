"""Send five valid samples and replay the first sample without changing its ID."""
from datetime import datetime, timezone
import json
from uuid import uuid4

from simulator.mqtt_demo import Connection, ROOT, mqtt
from simulator.signals import idle_samples


def publish_fixture():
    device = 'phase2b-' + uuid4().hex
    topic = f'motion/v1/devices/{device}/telemetry'
    samples = list(idle_samples(device, uuid4(), datetime.now(timezone.utc), count=5))
    credentials = json.loads((ROOT / 'secrets/mqtt/clients.json').read_text(encoding='utf-8'))
    conn = Connection(credentials, 'simulator')
    try:
        conn.open()
        for sample in [*samples, samples[0]]:
            info = conn.client.publish(topic, json.dumps(sample, allow_nan=False), qos=1)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError('Could not queue smoke sample')
            conn.wait(lambda: info.mid in conn.acknowledged, 10, 'Smoke PUBACK')
            conn.acknowledged.remove(info.mid)
        print(f'Broker acknowledged 5 samples + 1 retry. deviceId={device}')
    finally:
        conn.close()
    return device


if __name__ == '__main__':
    publish_fixture()
