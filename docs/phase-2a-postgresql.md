# Phase 2A: PostgreSQL foundation

The local database is opt-in (Compose profile storage). Directly targeting
postgres activates that service. PostgreSQL 17's bookworm tag tracks minor
updates; it is not a digest pin. Port 5433 on Windows maps to 5432 in the container.
The named volume persists across normal container lifecycle operations.

## Windows acceptance

In the repository root, create a local password file once:
```powershell
Copy-Item infrastructure/postgres/.env.example infrastructure/postgres/.env
notepad infrastructure/postgres/.env
```

Replace the placeholder with a unique local password. Keep this ignored file
when returning later. Changing the file does not change an existing database role.
Start Docker Desktop and run the following. Stop if any command fails.
```powershell
docker compose -f infrastructure/compose.yaml up -d --wait postgres
docker compose -f infrastructure/compose.yaml exec -T postgres psql -X -U motion -d motion -f /sql/001_initial.sql
docker compose -f infrastructure/compose.yaml exec -T postgres psql -X -U motion -d motion -f /sql/smoke.sql
docker compose -f infrastructure/compose.yaml restart postgres
docker compose -f infrastructure/compose.yaml up -d --wait postgres
docker compose -f infrastructure/compose.yaml exec -T postgres psql -X -U motion -d motion -f /sql/verify.sql
```

Expect two PASS lines, one for constraints and one for the persisted fixture.
The final query only reads; do not rerun the insert after restarting when
checking persistence. If startup fails, inspect 'docker compose -f
infrastructure/compose.yaml logs --tail 50 postgres'. Do not remove the volume
to troubleshoot. A missing password prevents first initialization. The local
psql commands use the container's Unix socket and do not verify host TCP login.

## Decisions and limits

- devices owns identity; sensor_readings stores scalar IMU values in contract
  units. A foreign key rejects readings for unregistered devices.
- message_id is the primary key. A second unique key protects the logical
  sample (device_id, stream_id, sequence). The smoke fixture verifies both
  identity constraints and the foreign key. It uses DO NOTHING for a known retry;
  the future consumer must distinguish an exact retry from conflicting content.
- sampled_at is distinct from received_at, which here defaults to insert time.
  The device/time index supports bounded history with a stable message ID tie-break.
- Migration 001 runs explicitly in a transaction, records its version, and uses
  an advisory lock to serialize concurrent application. This psql script is the
  initial schema baseline; future migrations must respect that history.
- The motion role is the local bootstrap administrator. A scoped application
  role and application-side validation belong to the ingestion step.
- Author verification: DDL and both SQL checks ran against embedded PostgreSQL,
  including running the write check twice. psql directives, Docker networking,
  container health, and volume persistence await Windows validation.

烘焙类比：设备表是烤箱名册，遥测表是读数台账。报告编号避免同一份报告登记两次，
外键保证报告属于名册中的烤箱。重启后只查询，不重新登记，才能验证台账确实保留。
