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
.\.venv\Scripts\python.exe -m tools.test_compose_stack
```

The runner publishes a fresh device fixture and one exact retry, waits up to
20 seconds for five rows, then checks pagination, identity and HTTP 400.
Expect PASS Compose end-to-end. To confirm explicit duplicate classification,
check ingestion logs for the fresh device's five STORED entries and one DUPLICATE.

The containers use service DNS (mosquitto and postgres). Host tools still use
loopback. The API listens on all interfaces inside the container, but the host
mapping binds only 127.0.0.1. Database credentials come from the ignored local
env file; MQTT credentials are mounted read-only. The Docker build context
excludes local credentials. The local roles and configuration are for development.

Stop the stack without deleting named volumes:

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app down
```

Windows startup reported: images built, database healthy, migration exit 0, and both
applications ready. Fresh end-to-end acceptance is pending. Author checks for the
runner: Python compilation and simulated delayed readiness, excess rows and timeout.
