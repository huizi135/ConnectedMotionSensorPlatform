# Phase 2B: MQTT ingestion into PostgreSQL

Run from the repository root on Windows. Reuse Phase 2A's database, migration
and password. The .NET 10 SDK is required (check with dotnet --list-sdks).
This console consumer uses MQTTnet and parameterized Npgsql SQL, preserving the
existing SQL migration as the schema authority.

Open Docker Desktop and start both services:

```powershell
docker compose -f infrastructure/compose.yaml up -d --wait postgres mosquitto
```

In terminal A (PowerShell 7.2 or newer), enter the existing database password
at the masked prompt, then run the consumer:

```powershell
$env:MOTION_DB_PASSWORD = Read-Host "PostgreSQL password" -MaskInput
try {
    dotnet run --project src/Motion.Ingestion
} finally {
    Remove-Item Env:MOTION_DB_PASSWORD -ErrorAction SilentlyContinue
}
```

Wait for READY .NET ingestion, which follows a database probe and granted
QoS 1 subscription. In terminal B, run the existing Python environment:

```powershell
.\.venv\Scripts\python.exe -m simulator.ingestion_smoke
```

Terminal A should log five STORED lines followed by one DUPLICATE for the same
device run. The broker's own publish acknowledgments alone cannot confirm that.
Copy the device ID printed in B into the query below, replacing the placeholder:

```powershell
docker compose -f infrastructure/compose.yaml exec -T postgres psql -X -U motion -d motion -c "SELECT count(*) AS rows, array_agg(sequence ORDER BY sequence) AS sequences FROM sensor_readings WHERE device_id = 'REPLACE-WITH-DEVICE-ID';"
```

Expect 5 and {0,1,2,3,4}. Each smoke run creates a different device ID.

## Behavior and limits

A new device and its first sample are inserted in the same transaction.
The consumer acknowledges a valid QoS 1 delivery after its database operation
completes. Exact retries mean equality of the persisted observation fields
(not unknown JSON extensions); inconsistent identity or content logs CONFLICT
and keeps the original row. Invalid messages and conflicts are deliberately
discarded and acknowledged. Unexpected database/transport failures stop the
consumer rather than acknowledge an unsuccessful write. The current clean
session does not provide durable replay, automatic reconnect, or recovery
of in-flight messages after consumer disconnect.

The current consumer uses the local Phase 2A bootstrap role over loopback;
scoped application credentials, a durable MQTT session, automated integration
CI and the query API are later work.
