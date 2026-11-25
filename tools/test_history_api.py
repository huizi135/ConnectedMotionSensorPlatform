"""Verify the Phase 2B five-row fixture through the local history API."""
import argparse
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True)
    device = parser.parse_args().device_id
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", device):
        parser.error("Invalid device ID")
    verify_history(device)


def verify_history(device):
    url = f"http://127.0.0.1:5086/api/v1/devices/{device}/readings"
    params = {"from": "2000-01-01T00:00:00Z", "to": "2100-01-01T00:00:00Z", "limit": 2}
    readings = []
    for size in (2, 2, 1):
        with urlopen(f"{url}?{urlencode(params)}", timeout=10) as response:
            page = json.load(response)
        require(len(page["items"]) == size, "Unexpected page size")
        readings.extend(page["items"])
        cursor = page["nextCursor"]
        require(bool(cursor) == (size == 2), "Unexpected pagination cursor")
        if cursor:
            params.update(cursor)
    require([r["sequence"] for r in readings] == list(range(5)), "Unexpected sequence")
    require(len({r["messageId"] for r in readings}) == 5, "Duplicate message ID")
    require(all(r["deviceId"] == device for r in readings), "Wrong device")
    try:
        with urlopen(f"{url}?from=2027-01-01T00:00:00Z&to=2026-01-01T00:00:00Z", timeout=10):
            raise RuntimeError("Expected HTTP 400")
    except HTTPError as error:
        require(error.code == 400, f"Expected HTTP 400, got {error.code}")
    print("PASS history API: pages 2+2+1; five unique readings; invalid range returns 400.")


if __name__ == "__main__":
    main()
