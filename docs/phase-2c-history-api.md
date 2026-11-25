# Phase 2C: Read-only telemetry API

Run from the repository root. Start Docker Desktop and PostgreSQL. The API
uses the same local database and .NET 10 SDK as the ingestion console. It
runs as a separate loopback-only process for this slice so it can be tested
against stored data without keeping the MQTT consumer running.

```powershell
docker compose -f infrastructure/compose.yaml up -d --wait postgres
$secure = Read-Host "PostgreSQL password" -AsSecureString
$env:MOTION_DB_PASSWORD = ([System.Net.NetworkCredential]::new('', $secure)).Password
$secure.Dispose()
try {
    dotnet run --project src/Motion.Api
} finally {
    Remove-Item Env:MOTION_DB_PASSWORD -ErrorAction SilentlyContinue
}
```

Provide the current local
database password. Do not paste it into logs or chat.

The endpoint is `GET /api/v1/devices/{deviceId}/readings` on
`http://127.0.0.1:5086`. Supply UTC `from` (inclusive) and `to` (exclusive),
with optional `limit` (1–500, default 100). The response contains `items` and
an optional `nextCursor`. Pass both cursor fields back with the same device
and time range to get the next page. Unknown devices and empty windows yield
an empty list. Invalid inputs yield HTTP 400.

From another terminal, verify the five persisted readings from the Phase 2B run:

```powershell
.\.venv\Scripts\python.exe tools/test_history_api.py --device-id phase2b-6480516f36b042018842ef908969cea5
```

If that fixture was removed, repeat Phase 2B and use the newly printed device ID.
The Python script requires no extra dependencies or PowerShell script execution policy changes. The script walks pages of size two and requires three pages, unique IDs and
sequences 0–4, plus HTTP 400 for a reversed time range.

The query is parameterized and uses the existing (device_id, sampled_at,
message_id) index order. The message ID breaks timestamp ties; offset paging
is not used. This is a live query, not a snapshot across requests; newly
inserted samples at or before the cursor may be missed during a paging session.
The program only queries data; the development database role is still the local
bootstrap role, not a restricted production role. No authentication, UI, or
production hosting is introduced in this slice.
