# Engineering roadmap and verified capability audit

Audit date: 2026-10-28. Source branch: phase-1/virtual-sensors.
Audited commit: 4dfbb0bc6ad491faa510a4b69790926faefcffd9.
This document extends the original Phases 0–6. It does not replace the architecture
or convert roadmap items into completed implementation.

## Repository and evidence

- main: 9c73dfb, initial README only; do not silently merge or reset it.
- docs/phase-0-baseline: 7e5a3d; phase-1/virtual-sensors: 4dfbb0b at audit.
- Source includes six ADRs, MQTT schemas/examples, Python idle generator, MQTT
  demo, status demo, three unit-test files, broker Compose and initialization.
- GitHub Actions API reports zero workflow runs; no .github/workflows exists.
- No .csproj/.sln, backend application, PostgreSQL service, SQL migration, API,
  Dockerfile, Prometheus/Grafana, OPC UA, Modbus or ROS 2 code exists at audit.
- Existing 20 unit tests and 46 contract checks passed when rerun in the author
  Linux environment with repository-declared dependencies. Windows evidence
  proves 46 contract checks, five offline idle tests and ten-message MQTT delivery.
- Two-device reception is owner-confirmed, not a raw-log capacity/security test.
- Status/retained/Will source and unit checks exist, but no real-broker status
  acceptance output is recorded. Automatic reconnect is explicitly disabled.

## Capability matrix against P0–P3

| Priority | Capability | Actual state | Evidence or missing acceptance |
| --- | --- | --- | --- |
| P0 | PostgreSQL/SQL, constraints/indexes/migrations | Not started | Planned devices/readings model only; no DB service or SQL execution |
| P0 | ASP.NET Core, consumer, persistence, REST | Not started | Modular monolith design; no .NET implementation |
| P0 | Linux deployment and Compose | Partial | Real Linux Mosquitto container on Windows; no complete stack, application image or clean-machine acceptance |
| P1 | MQTT networking/authentication/ACL | Partial | QoS 1 route/refusal checks passed; no TLS or complete QoS 0/1/2 experiment |
| P1 | Status/retained/Will/reconnect | Partial | Status code plus unit checks; runtime pending; no reconnect/replay |
| P1 | Automated tests and CI/CD | Partial | 20 existing unit tests + 46 contract vectors; no CI, API/.NET/DB tests or image build verification |
| P1 | Observability/diagnostics | Partial | Stage-specific console output and broker logs; no structured backend logs, metrics or health endpoints |
| P1 | Performance/data integrity | Partial | Identity, logical timestamps and small-stream checks; no measured throughput/latency or load report |
| P2 | OPC UA/Modbus | Not started, optional | Choose OPC UA first, after core acceptance; do not implement both initially |
| P2 | ROS 2/MQTT bridge | Not started, optional | No ROS packages or robot deployment |
| P3 | Azure/IaC/Kubernetes | Not started, deferred | Existing professional Azure experience is separate from this project |

## Implementation order, dependencies and gates

1. Phase 1 status gate (current slice): automate graceful online/offline,
   unexpected process-exit Will, retained late-subscriber snapshot, correct
   connection ID and reportedAt semantics. Requires running broker and existing
   ignored credentials. PASS must come from a real-broker run, not mock tests.
2. Phase 1 minimum completion: 1–10 concurrently simulated device streams,
   isolated identities, idle/motion/jump/landing teaching signals, separately
   stored reference labels, basic reconnect with new connection identity and
   explicit outage data-loss boundary. No hard-real-time or action accuracy claim.
   Reconnect, status and telemetry lifecycle must be integrated. Defer advanced
   buffering, complete replay and 100–1,000-device load to Phase 4.
3. Phase 2A PostgreSQL first: add one version-pinned service and named volume,
   loopback port, ignored secrets and readiness. Implement devices and
   sensor_readings with FK, unique message_id and unique
   (device_id, stream_id, sequence), UTC times and a historical-query index.
   Do not add a separate sensors table without a multi-sensor requirement.
   Gate: migration from empty DB, insert/update/select/join exercises, duplicate
   and FK violations, restart retains rows. Record versions/commands/results.
4. Phase 2B .NET ingestion/persistence: one ASP.NET Core host with MQTT background
   adapter and separate application/database boundaries, DI, async cancellation,
   configuration and bounded queues/retries. Gate: Python -> MQTT -> .NET -> DB,
   stable retry identity, exact row counts, conflict diagnosis, DB-outage behavior.
   Verify MQTTnet acknowledgment behavior before claiming persistence guarantees.
5. Phase 2C REST: device queries and bounded history by device/time, stable cursor
   ordering, validation and error responses. Gate: API integration tests against
   real PostgreSQL; no unbounded full-table history endpoint.
6. Phase 3 deployment/LINUX/CI: containerize backend; Compose broker/backend/DB,
   explicit migrations, service DNS and health checks. Gate: documented clean
   checkout startup, restart retains data, fresh Linux execution and image build.
   Add CI incrementally during Phases 1/2: Python unit/contracts, .NET unit,
   real DB/API integration, then Docker build and selected broker integration.
   Keep unittest; do not replace it just to add another framework name.
7. Phase 3 diagnostics: structured logs with device/message/stream identity,
   liveness/readiness distinction, counters and bounded latency histograms.
   Gate: diagnose injected malformed message, DB outage and disconnected device
   from logs/health; never label metrics by unbounded device/message IDs.
   Prometheus/Grafana follow stable instrumentation, not precede it.
8. Phase 4 reliability/capacity: bounded buffering/backpressure, reconnect and
   retry budgets, duplicate/conflict/out-of-order/missing samples, broker/DB
   outages and process crashes; first 100 then 1,000 virtual devices. Reconcile
   sent/acknowledged/received/committed identities, report throughput, p50/p95/p99
   latency, resources and actual loss windows. No unmeasured scale claim.
9. Phase 5 analytics: quality checks, features, rule-based events, separated
   generator labels and detector inputs; reproducible analysis dataset.
10. Phase 6 optional adapters: 6A OPC UA simulated server/client mapped to the
    existing telemetry model; reconnect and invalid-input tests, then compare to
    MQTT. 6B ROS 2 Python nodes and MQTT bridge only for robotics targets; timestamp,
    frame and QoS mappings, bounded bridge buffers and loop prevention. Hardware/
    BLE remains a separate optional adapter under the existing design.
11. After core acceptance: Azure, IaC, and only demonstrated need for Kubernetes.
    None is a prerequisite for the local MVP.

Dependencies: Phase 1 gate -> PostgreSQL -> .NET persistence -> REST -> full
container deployment/observability -> fault/load evidence -> optional adapters.
Unit/contract CI starts as early as practical; DB and API tests follow their code.
Each stage has Windows instructions, failure cases, evidence and a separate
Chinese HTML explanation/interview summary on completion.

## Backend/data access proposal (not installed)

Use a supported .NET LTS SDK, with .NET 10 the initial implementation candidate
as of this audit. Pin SDK/EF Core/Npgsql/MQTTnet compatible versions at Phase 2
implementation, not by copying old documentation examples.

Proposed default: EF Core with the Npgsql PostgreSQL provider for explicit
models, constraints and versioned migrations. EF Core and Npgsql are not mutually
exclusive: the provider uses Npgsql underneath. Learn actual parameterized SQL
SELECT/JOIN/INSERT/UPDATE and transaction behavior alongside generated migration
SQL. Use EXPLAIN (ANALYZE, BUFFERS) on a reproducible seeded dataset; a tiny table
may legitimately use a sequential scan. EXPLAIN ANALYZE executes its statement.

Alternative: direct Npgsql/Dapper for tighter SQL control but more mapping and
migration plumbing. Reconsider when measured ingestion overhead justifies
batching/COPY/direct SQL. Do not maintain competing EF and ad-hoc production
migration histories. Final data-access decision gets a dedicated ADR at Phase 2.

## Linux decision

Current: Windows/PowerShell dev + Docker Desktop's WSL2 Linux engine.
No user-installed Ubuntu distribution is evidenced; no independent VM/host exists
in project evidence. Linux containers already run real broker software, but this
alone does not prove general Linux administration skills.

Next Linux skills: shell, processes/signals, permissions, environment variables,
DNS/ports, volumes, container logs and health diagnostics, captured in runbooks.
An Ubuntu LTS distribution in WSL2 is optional for shell practice, not an MVP gate.
A separate Linux VM is a later clean-deployment target if useful. No dedicated
Linux hardware is required. See ADR 0007.

## Current implementation: automatic status gate

New tools/test_status_lifecycle.py uses the current status_demo unchanged.
The parent observes real MQTT messages; it starts unique one-second child device
processes for graceful and abrupt cases, checks connection/time semantics and
late-subscriber retained snapshots, then removes only its own retained topics.
Exit 17 belongs to the intentional child crash. No arbitrary process, volume or
broker is stopped. A network blackhole, broker restart and DB persistence remain
outside this test. Cleanup on broker failure is best effort and reports its topic.

Five new offline assertion tests make 25 tests total; 46 contract checks remain.
The author environment has no Docker engine; runtime status acceptance is pending.
After this gate, finish only the essential Phase 1 work before starting Phase 2A.

## Portfolio and interviews

CV A can currently cite a personal simulated-device MQTT pipeline and contract/
unit verification; PostgreSQL/.NET/CI are planned, not completed project claims.
CV B can cite the Windows sensor-stream demo, stable identities and staged
diagnostics; not production industrial/medical deployment or hard real time.
Qualisys and other professional experience remains separately attributed.

Every case study: trigger, architecture, decision/alternatives/costs, failure
behavior, command/environment, observed evidence, limitations and lessons.
main currently does not expose the development work by default; later choose a
validated release/merge explicitly, without rewriting history during this audit.
Existing direct branch/commit workflow is retained; no PR was opened automatically.

## Official sources checked 2026-10-28

- https://docs.docker.com/desktop/features/wsl/
- https://dotnet.microsoft.com/en-us/platform/support/policy
- https://www.postgresql.org/docs/current/ddl-constraints.html
- https://www.npgsql.org/efcore/
