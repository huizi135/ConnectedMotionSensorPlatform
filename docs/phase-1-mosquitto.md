# Phase 1 Mosquitto broker slice

Status: Windows startup and corrected temporary-session smoke checks passed on
2026-10-23. See testing/phase-1-broker-windows.txt for evidence and limits.
Offline signal generation is the next slice; Phase 1 remains incomplete.

No MQTT sensor publisher or backend is implemented in this broker slice.

## Objective and architecture

Start one local, authenticated MQTT broker. Verify connection refusal and role
permissions, then publish a valid example and receive it with a separate role.

Windows host tools -> localhost:1883 -> Mosquitto container.

The smoke helper checks the published host TCP port. MQTT client checks use
mosquitto_pub/sub inside the container through docker compose exec. This proves
in-container MQTT routing, not host-native Python MQTT. That path will be tested
with the simulator next. Keep this distinction in validation reports.

## Files

| File | Purpose |
| --- | --- |
| infrastructure/compose.yaml | Single broker plus an opt-in initialization helper |
| infrastructure/mosquitto/config/mosquitto.conf | Listener, plugins, persistence and stdout logging |
| infrastructure/mosquitto/acl | Simulator write role and backend read role |
| infrastructure/mosquitto/init-credentials.sh | Create hashed credentials and correctly owned ACL files in a named volume |
| tools/initialize_mqtt.py | Generate/reuse ignored local credentials; invoke the helper container |
| tools/test_mqtt_broker.py | Authentication, authorization and valid-payload routing checks |
| secrets/mqtt/clients.json | Generated locally only; never tracked or printed |

## Design decisions and limits

- Use official eclipse-mosquitto:2.1.2-alpine, a verified explicit version tag,
  rather than latest. A tag can be rebuilt; capture the actual RepoDigest during
  Windows validation. This is not an immutable digest-pinned environment.
- Publish only 127.0.0.1:1883 on the Windows host. The listener binds 0.0.0.0 inside
  its container so Docker forwarding works. This is local development, not a
  LAN/cloud deployment or a complete host security boundary.
- Use the Mosquitto 2.1 password-file and ACL-file plugins. Do not mix examples
  from older versions or rely on deprecated per_listener_settings.
- Run the long-lived broker as UID/GID 1883. A short-lived root helper owns and
  protects auth files inside a Linux Docker volume, avoiding NTFS ownership drift.
- simulator may write only telemetry/status device topics; backend may only read
  those topics. Accounts are shared local-development roles, not device identity
  provisioning or isolation between individual virtual devices.
- Transport is local MQTT TCP without TLS. Remote deployment needs a separate
  security design; do not broaden the host port binding as a shortcut.
- Broker snapshots persist in a named data volume every configured interval and
  on graceful stop. They are not a raw-reading database, do not replace future
  PostgreSQL, and do not establish end-to-end zero-loss delivery.
- Log rotation limits local Docker log growth. Formal monitoring/health dashboards
  remain Phase 3 work. A running container is not proof of MQTT readiness.

See ADR 0003 for alternatives and reconsideration conditions.

## Step A Initialize local credentials

From the project root on phase-1/virtual-sensors, with Docker Desktop running:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe tools/initialize_mqtt.py
```

The script validates Compose configuration and engine type, verifies that the
local credential path is ignored, pulls the selected image and generates two
random credentials locally. Secrets go to the ignored secrets/mqtt directory;
plaintext values are sent over stdin to the helper instead of being put into
Docker command arguments. The helper hashes a fresh temporary password file,
copies the ACL and sets volume ownership/permissions.

Rerunning while stopped reuses existing local credentials; it does not generate
new passwords if the local file is present. Rerunning while the broker is running
and the local file exists leaves it unchanged. If an initialized auth volume
exists but the local file was lost, initialization refuses rather than silently
rotating credentials. Stop and diagnose that situation; do not delete volumes.

Local client passwords necessarily remain available to local development clients.
The smoke helper passes them to ephemeral container client processes, so this
local setup is not a production secret-management solution. Do not paste the
credential file or secret-bearing process arguments into issue reports.

## Step B Start and inspect the broker

```powershell
docker compose -f infrastructure/compose.yaml config --quiet
docker compose -f infrastructure/compose.yaml up -d mosquitto
docker compose -f infrastructure/compose.yaml ps
docker compose -f infrastructure/compose.yaml logs --tail 40 mosquitto
git status --short
```

Expected: mosquitto is running, the listener starts, authentication/ACL plugins
load and there are no missing-file/permission/plugin errors. git status remains
clean because credentials are ignored and runtime data lives in Docker volumes.
Do not start mqtt-init with an ordinary up command; it has the tools profile.

## Step C Verify authentication and routing

Only after startup inspection succeeds:

```powershell
.\.venv\Scripts\python.exe tools/test_mqtt_broker.py
```

Expected checks:
1. Published host TCP port is reachable (not an MQTT authentication check).
2. Anonymous connection is explicitly refused.
3. Wrong password is explicitly refused.
4. The read-only backend role cannot publish (MQTT v5 QoS 1 refusal).
5. An authenticated simulator publishes a contract-valid sample and an
   authenticated backend subscriber receives the identical JSON object.

The helper registers a unique short-lived session using mosquitto_sub -E -c
-x 60, which exits after subscription acknowledgment. It then publishes QoS 1
and reconnects the same session to receive the queued sample with -x 0.
Clean-start cleanup runs in finally. No fixed sleep or live debug-log parsing
is used. This exercises temporary session queueing, not simultaneous live delivery. It uses a unique smoke device ID and validates the generated sample
against the existing contract. Subscriber waits are bounded. A failed negative
test is an investigation trigger, not permission to turn off authentication.
No credentials are printed by the helper. It does not instantiate a simulator,
check Last Will/retained behavior, test restarts or write to PostgreSQL.

## Evidence and troubleshooting

Record command output, actual image identity and errors without credentials:

```powershell
docker image inspect eclipse-mosquitto:2.1.2-alpine --format '{{json .RepoDigests}}'
```

- Docker connection failure: confirm Desktop and active context before retrying.
- Port 1883 already allocated: identify the conflicting service; do not kill it
  automatically or expose a different host interface.
- Missing auth files: verify initialization succeeded before starting the broker.
- Permission/plugin error: keep the broker logs and selected image tag; do not
  loosen files to world-writable or change authentication to anonymous.
- Lost local credentials/existing volumes: preserve state and request diagnosis.
- Script timeout: record which readiness/authorization step failed.

The image and scripts have not been executed in the assistant environment because
it has no Docker engine. Python compile and shell syntax checks plus structural
Compose checks are recorded separately. Windows startup and smoke output must be
supplied before marking this slice passed. Startup output has now been supplied;
the corrected smoke test must still be rerun.

## Stop without deleting state

```powershell
docker compose -f infrastructure/compose.yaml down
```

Named volumes persist. Do not use down -v or manually delete credentials to fix
an unexplained failure; those actions discard state.

## Sources checked 2026-10-23

- https://hub.docker.com/_/eclipse-mosquitto
- https://mosquitto.org/documentation/plugins/password-file/
- https://mosquitto.org/documentation/plugins/acl-file/
- https://mosquitto.org/man/mosquitto_passwd-1.html
- https://mosquitto.org/man/mosquitto-conf-5.html

## Windows finding: process exit versus publish result

The user's Mosquitto 2.1.2 client reported `Warning: Publish 1 failed: Not authorized.`
while exiting with code 0. The original helper incorrectly required both explicit
refusal and a nonzero exit for every negative probe. The publish-ACL probe now
also accepts this specific warning with exit 0. Connection-authentication probes
still require nonzero exit plus explicit refusal. Exit 0 without the warning and
unrelated failures remain test failures. ACL/configuration are unchanged.

Eight local regression cases verify rejection classification, including the
observed warning, normal authentication failures, unexpected zero exits, empty
output and network errors. They do not replace a real Windows broker rerun.

Baking analogy: a messenger returning successfully does not mean the kitchen
accepted the order; the returned receipt explicitly says the order was refused.
Interview point: process success and protocol/business success are distinct.
Use evidence from each layer and keep negative tests specific to avoid false passes.

## Windows finding: subscriber readiness timeout

The second Windows run passed TCP reachability and all three refusal probes,
but no SUBACK line reached the reader before the deadline. Publish/subscribe
acceptance remains pending. Child stdout buffering is the current hypothesis,
not a confirmed broker failure. Python Popen bufsize=1 does not flush the C
client's stdout inside the container.

The subscriber now uses Compose exec's default pseudo-TTY with interactive
stdin disabled, while publishers retain -T for exact stdin payload transfer.
The reader strips CR/LF. SUBACK is still required before publishing; there is
no guessed startup sleep or automatic success on timeout. Bounded, password-
redacted client output is included on readiness failure. Subscriber lifetime
is bounded at 30 seconds. Local syntax and command-mode checks passed; actual
Docker/Windows validation must be rerun.

Baking analogy: the kitchen may have acknowledged an order, but the messenger
has not yet delivered the receipt. A missing visible receipt does not identify
which layer failed. Interview point: distinguish a readiness event from its
log transport, and add bounded diagnostics before claiming a root cause.

Reference: https://docs.docker.com/reference/cli/docker/compose/exec/

## Follow-up evidence and revised smoke sequence

Owner-supplied broker logs show an authenticated backend connection remaining
open for approximately 30 seconds, and ps shows Up 45 minutes. Startup or invalid
backend credentials do not explain this observed run. These information-level
logs do not prove SUBACK receipt; the earlier TTY change did not resolve timeout.
The exact original log transport failure is not confirmed.

The smoke helper now uses the documented -E completion event and a unique session
with 60-second expiry. After registration it publishes, resumes the session,
compares complete JSON, and clears it with Clean Start and zero expiry. All
clients use non-TTY execution. This intentionally changes the test to bounded
session queue delivery; host-native live streaming remains a simulator test.
It does not verify disk persistence, crash recovery or general offline replay.

Local checks: Python compilation and mocked success, registration failure,
receive timeout, registration-before-publish and cleanup paths passed. These
are script-control-flow checks, not actual broker acceptance. Windows rerun pending.
Reference: https://mosquitto.org/man/mosquitto_sub-1.html (-E, -c, -x).
