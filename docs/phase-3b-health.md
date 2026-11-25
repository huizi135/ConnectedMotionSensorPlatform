# Phase 3B: API health and structured ingestion logs

From the repository root, with the local stack configured:

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app up -d --build
curl.exe -i http://127.0.0.1:5086/health/live
curl.exe -i http://127.0.0.1:5086/health/ready
.\.venv\Scripts\python.exe -m tools.test_compose_stack
docker compose -f infrastructure/compose.yaml --profile storage --profile app logs --tail 30 ingestion
```

Both health requests should return 200. Readiness checks connectivity and
access to sensor_readings with a three-second probe budget. It does not check
MQTT or guarantee successful future writes. Look for JSON outcomes STORED and
DUPLICATE, correlated by deviceId, streamId, messageId and sequence. Failures log
their type without dumping the payload or credentials.

After the smoke fixture has completed and while no publishers are running:

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app stop postgres
curl.exe -i http://127.0.0.1:5086/health/live
curl.exe -i http://127.0.0.1:5086/health/ready
docker compose -f infrastructure/compose.yaml --profile storage --profile app up -d --wait postgres
curl.exe -i http://127.0.0.1:5086/health/ready
```

Expected: live 200 and ready 503 during the outage, then ready 200 after recovery.
This verifies the query API's health behavior, not MQTT replay or recovery
during an in-flight write. These endpoints are not wired into container restart
policies. The Windows health outage/recovery sequence passed; see [evidence](testing/health-windows.txt). Structured ingestion log acceptance remains pending.
