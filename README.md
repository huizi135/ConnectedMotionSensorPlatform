# Connected Motion Sensor Platform

An incremental IoT engineering project that connects simulated motion
sensors to a local backend, database, API and observability stack.

The project explores device-to-cloud architecture, reliable messaging,
data processing and operational diagnostics.

## Project status

Phase 0 design baseline verified; Phase 1 environment preparation is next.

Verified:

- Git is available on the Windows development machine.
- The repository has been cloned locally.
- The Windows checkout tracks origin/docs/phase-0-baseline at f8bfed5.
- Repository-local commit identity is configured.

Prepared in this Phase 0 change set:

- Architecture documentation, two ADRs and versioned MQTT contracts.
- Repository configuration, bilingual HTML guides and implementation records.
- Contract regression checks: 46/46 passed in the author environment.

Windows execution of the contract runner also passed: Python 3.12.3 with
jsonschema 4.26.0, 46/46 checks, repository-local .venv and clean Git status.
MQTT runtime behavior remains unverified. WSL installation requires a reboot;
Docker Desktop and the broker are not yet ready. The Phase 0 branch has been synchronized on Windows with a clean
working tree. Phase 1 starts with environment inspection.

Application implementation has not started.

## Goals

- Build a reproducible sensor-to-backend data pipeline.
- Use C#/.NET for the backend.
- Use Python for virtual sensors and later data analysis.
- Run the complete MVP locally without paid cloud services.
- Document design decisions, failure behavior and test evidence.
- Preserve an adapter boundary for future BLE hardware integration.

## Planned architecture

Python Virtual IMU → Mosquitto MQTT Broker → .NET Backend → PostgreSQL

The .NET backend will host:

- An MQTT ingestion background service.
- Validation and persistence processing.
- A REST API for device and historical-reading queries.

Prometheus and Grafana will provide operational visibility.

The initial backend will be a modular monolith with one deployment unit.

The simulator will publish MQTT directly; it will not implement BLE/GATT.

## Delivery phases

| Phase | Focus |
| --- | --- |
| 0 | Architecture, contracts, repository and ADRs |
| 1 | Python virtual sensors and MQTT communication |
| 2 | .NET ingestion, PostgreSQL and REST API |
| 3 | Docker Compose and observability |
| 4 | Reliability and capacity experiments |
| 5 | Data quality and motion analytics |
| 6 | Optional hardware and cloud integration |

Each phase requires verification before the next phase begins.

## Initial MVP boundaries

- 1–10 virtual devices, initially configured at 10 Hz each.
- Acceleration and angular velocity samples.
- Device identity, timestamps and device status.
- MQTT ingestion, validation and database deduplication.
- Device and historical-reading queries.
- Local deployment, structured logs and basic metrics.

The initial sampling rate supports debugging. It is not a validated
requirement for real-world motion analysis.

Physical sensors, BLE, OTA, user accounts, high availability and
complete offline replay are outside the initial MVP.

## Reliability principles

- MQTT delivery acknowledgment is distinct from database persistence.
- QoS 1 may deliver duplicates.
- Retries must preserve sample identity.
- In-memory buffering does not provide durability.
- Failure guarantees must be supported by tests.
- Simulator scenario labels must remain separate from detector inputs.

## Documentation

- [Architecture](docs/architecture.md)
- [MQTT contract v1](docs/mqtt-contract.md)
- [ADR 0001: software first](docs/adr/0001-software-first.md)
- [ADR 0002: versioned JSON contracts](docs/adr/0002-versioned-json-contracts.md)
- [Git workflow and Windows synchronization](docs/git-workflow.md)
- [Phase 0 acceptance](docs/testing/phase-0-acceptance.md)
- [Phase 1 Windows environment](docs/phase-1-environment.md)
- [Chinese HTML guide](docs/Connected_Motion_Platform_Phase0_ZH.html)
- [English HTML guide](docs/Connected_Motion_Platform_Phase0_EN.html)
- [Bilingual phase casebook](docs/Connected_Motion_Platform_Phase_Cases_ZH_EN.html)
- [Implementation record](docs/Phase0_Implementation_Record_ZH_EN.html)
- [Contract validation output](docs/testing/mqtt-contract-validation.txt)

GitHub displays HTML source; open the checked-out HTML files in a browser to
read their formatted local versions. Git is the source of truth for these files.
Changes are committed directly to work branches without pull requests;
ZIP-based file transfer is no longer the development workflow.

Casebook entries for unimplemented phases describe proposed designs
and tests, not completed engineering results.

## Development environment

Initial development targets Windows and PowerShell.

Planned dependencies include Python, .NET, Docker, Mosquitto
and PostgreSQL. Compatible versions will be selected and recorded
when the corresponding phase begins.

There is no runnable application yet. Startup instructions will be
added after the first implementation has been verified.

## Scope and attribution

This is an independent learning project inspired by the problem domain
of sports motion tracking. It does not reproduce Aiving's proprietary
algorithms or internal architecture.

Synthetic motion detection results will not be presented as evidence
of real-world sporting accuracy.

## License

A license has not yet been selected.
