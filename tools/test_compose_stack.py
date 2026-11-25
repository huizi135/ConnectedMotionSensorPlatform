"""Publish a fresh fixture and verify its persistence through the local API."""
import json
import sys
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from simulator.ingestion_smoke import publish_fixture
from tools.test_history_api import verify_history


def wait_for_readings(device, timeout=20):
    url = (f"http://127.0.0.1:5086/api/v1/devices/{device}/readings"
           "?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z&limit=6")
    deadline = monotonic() + timeout
    while (remaining := deadline - monotonic()) > 0:
        try:
            with urlopen(url, timeout=min(2, remaining)) as response:
                count = len(json.load(response)["items"])
            if count > 5:
                raise RuntimeError(f"Expected five rows for {device}, found at least {count}")
            if count == 5:
                return
        except HTTPError as exc:
            if exc.code != 503:
                raise
        except (URLError, TimeoutError):
            pass
        sleep(min(0.25, max(0, deadline - monotonic())))
    raise RuntimeError(f"Timed out waiting for five rows for {device}; check api and ingestion logs")


def main():
    device = publish_fixture()
    wait_for_readings(device)
    verify_history(device)
    print(f"PASS Compose end-to-end: {device}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Compose smoke failed: {exc}", file=sys.stderr)
        sys.exit(1)
