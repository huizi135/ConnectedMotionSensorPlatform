# ADR 0003 Run a local authenticated Mosquitto broker with Compose

- Date: 2026-10-23.
- Status: implementation prepared; Windows runtime acceptance pending.

## Context

The owner has passed Windows Python contract checks and Docker hello-world.
The next learning goal is MQTT routing, authentication and authorization before
introducing signal generation or backend persistence. The setup must remain
local, reproducible and free of paid cloud dependencies.

## Decision and rationale

Use the official explicit tag eclipse-mosquitto:2.1.2-alpine. Run one broker via
Compose and expose TCP 1883 only on the host loopback interface. Use Mosquitto 2.1
password-file/ACL-file plugins with a simulator write role and backend read role.

Generate random development client credentials locally into an ignored JSON
file. Use an opt-in initialization container for hashed broker credentials and
ACL ownership in a Linux named volume. Run the broker as UID/GID 1883. Use a
separate named volume for broker snapshots and stdout logging with rotation.

The named auth volume avoids depending on Windows bind-mount ownership for
sensitive broker files. Local initialization reuses credentials and does not
silently replace an existing auth volume after the client file is lost.

## Alternatives

| Alternative | Benefit | Cost or reason deferred |
| --- | --- | --- |
| Native Windows Mosquitto service | No container dependency | More OS-specific installation/service management |
| Anonymous local broker | Smallest configuration | Does not exercise authentication or role boundaries |
| Managed cloud broker | Reduced local operations | Conflicts with offline/local MVP objectives and adds external dependency |
| Dynamic Security plugin | Runtime-managed clients, groups and roles | More initial management concepts than this two-role learning slice needs |
| Bind all sensitive files from Windows | Fewer Docker volumes | Sensitive-file ownership/permissions differ across host and container |

## Costs and limits

- Docker Desktop must run. Image pull access and a free local port are required.
- A version tag may be rebuilt; log actual RepoDigests before drawing reproducibility conclusions.
- Shared simulator credentials do not isolate individual devices.
- Plaintext development client credentials live in an ignored local file; this
  is not production provisioning, TLS or a cloud secret-management design.
- Container client checks alone do not prove host-native Python MQTT behavior.
- Built-in snapshots do not establish durable application ingestion or zero loss.
- There is no formal health dashboard yet; verify authenticated behavior explicitly.

## Verification

Static checks: parse Compose, inspect loopback/volume/profile constraints, compile
Python helpers and check shell syntax. No assistant-side Docker runtime result
is claimed. On Windows, initialize credentials, inspect startup logs, then test
anonymous/wrong-password refusal, backend write denial and contract-valid
simulator-to-backend delivery. Preserve exact observed output.

## Reconsideration conditions

Revisit per-device identities or Dynamic Security when real devices/provisioning
are introduced. Require TLS/identity redesign before remote exposure. Consider
SQLite persistence or a different durability mechanism only against explicit
recovery requirements and fault tests. Revisit image pinning/update policy when
build reproducibility or security maintenance becomes an operational requirement.
