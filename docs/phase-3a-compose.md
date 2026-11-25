# Phase 3A: containerized application

Run from the repository root after starting Docker Desktop. For a new checkout,
follow the README's Python and MQTT credential setup and the Phase 2A PostgreSQL
password setup. An existing checkout should reuse its ignored files and volumes.
Stop any host-run .NET API and ingestion console before starting their containers.

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app up -d --build
docker compose -f infrastructure/compose.yaml --profile storage --profile app ps -a
docker compose -f infrastructure/compose.yaml --profile storage --profile app logs --tail 40 migrate ingestion api
```

PostgreSQL health gates the one-shot migration, and successful migration gates
both .NET services. Migration should exit 0; look for READY .NET ingestion
and the API listening on port 5086. The broker is ordered by container startup;
transient ingestion startup failures have bounded container restarts. These
logs and the HTTP smoke check, not Compose 'Up' alone, show application readiness.

```powershell
.\.venv\Scripts\python.exe -m simulator.ingestion_smoke
.\.venv\Scripts\python.exe tools/test_history_api.py --device-id REPLACE-WITH-PRINTED-ID
```

Before running the second command, check the ingestion log for five STORED
entries and one DUPLICATE for the new device. The history script must report
pages 2+2+1, five unique readings and HTTP 400 for an invalid range.

The containers use service DNS (mosquitto and postgres). Host tools still use
loopback. The API listens on all interfaces inside the container, but the host
mapping binds only 127.0.0.1. Database credentials come from the ignored local
env file; MQTT credentials are mounted read-only. The Docker build context
excludes local credentials. The local roles and configuration are for development.

Stop the stack without deleting named volumes:

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app down
```

Author checks: YAML and dependency/credential wiring inspected. Docker image build,
Compose runtime and fresh end-to-end acceptance remain pending on Windows.
