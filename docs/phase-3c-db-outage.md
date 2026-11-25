# Phase 3C: controlled PostgreSQL outage

Scope: local Compose stack, no other publishers. Build the updated ingestion
image and verify a baseline smoke before stopping the database.

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app up -d --build
.\.venv\Scripts\python.exe -m tools.test_compose_stack
```

Wait for the baseline to pass. Then run the outage publish in one terminal.
The finally block restarts PostgreSQL even if the publisher fails. The short
hold gives the running subscriber time to report a failure; a missing matching
delivery_failed log makes the experiment inconclusive, not a pass.

```powershell
$failedDevice = $null
docker compose -f infrastructure/compose.yaml --profile storage --profile app stop postgres
if ($LASTEXITCODE -ne 0) { throw "Could not stop postgres" }
try {
    $out = .\.venv\Scripts\python.exe -m simulator.ingestion_smoke
    $out
    if ($LASTEXITCODE -ne 0 -or ($out -join " ") -notmatch 'deviceId=(phase2b-[0-9a-f]{32})') {
        throw "Outage publish failed or did not report a device ID"
    }
    $failedDevice = $Matches[1]
    Start-Sleep -Seconds 8
} finally {
    docker compose -f infrastructure/compose.yaml --profile storage --profile app up -d --wait postgres
}
```

Inspect the logs before manually restarting anything. A delivery_failed line
must match the outage device and include its message identity. A following
READY line shows the consumer came back, not that any message was replayed.
SQLSTATE is populated only for a PostgreSQL server error; connection-level
failures may correctly report null. The logger does not include database
exception messages, credentials or payloads.

```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app logs --tail 60 ingestion
docker compose -f infrastructure/compose.yaml --profile storage --profile app ps -a ingestion
```

If the consumer does not return to READY after PostgreSQL recovers, record
that outcome and start it manually before testing fresh delivery:
```powershell
docker compose -f infrastructure/compose.yaml --profile storage --profile app start ingestion
```

After READY, run a fresh smoke and independently query the old device from the
same PowerShell window (the variable came from the outage publish):
```powershell
.\.venv\Scripts\python.exe -m tools.test_compose_stack
if ($failedDevice -match '^phase2b-[0-9a-f]{32}$') {
    docker compose -f infrastructure/compose.yaml exec -T postgres psql -X -U motion -d motion -c "SELECT count(*) AS rows, array_agg(sequence ORDER BY sequence) AS sequences FROM sensor_readings WHERE device_id = '$failedDevice';"
}
```

Record the old batch's observed count (including zero), its sequences, and
the failed message's sequence from the log. Do not resend the old batch.
A successful fresh smoke establishes new delivery after recovery. It does not
prove recovery of the outage batch; the consumer uses a clean MQTT session.

Author review: checked the change against the existing logging calls; .NET
build and fault acceptance require the Windows Compose run.
