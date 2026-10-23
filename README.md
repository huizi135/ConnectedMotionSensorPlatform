# Connected Motion Sensor Platform

An incremental IoT engineering project that connects simulated motion
sensors to a local backend, database, API and observability stack.

The project explores device-to-cloud architecture, reliable messaging,
data processing and operational diagnostics.

## Project status

Phase 1 — broker smoke acceptance passed; offline idle simulator prepared.

Verified:

- Windows repository clone and repository-local Git identity.
- Phase 0 architecture, ADRs and versioned MQTT contracts.
- Windows contract checks: Python 3.12.3, jsonschema 4.26.0, 46/46 passed.
- Docker Desktop Linux engine and hello-world on Windows.
- Mosquitto 2.1.2 startup, authentication/ACL plugin loading and loopback port
  binding, confirmed by the user's Windows output on 2026-10-23.
- Clean Windows working tree after broker initialization.

Windows broker smoke checks passed on 2026-10-23: TCP reachability, anonymous
and incorrect-password refusal, backend publish denial, temporary-session
registration and identical JSON receipt. This checks in-container clients and
brief session queue delivery, not host-native streaming or crash durability.

An offline idle IMU generator and five automated tests are prepared and passed
in the author environment. Windows signal acceptance is next. Phase 1 is not
complete; MQTT publishing, multiple devices, status and reconnect remain pending.

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

- [Phase 1 静止虚拟 IMU：操作、原理和面试提示](docs/Phase1_Idle_Signal_ZH.html)
- [Windows broker smoke acceptance](docs/testing/phase-1-broker-windows.txt)
- [ADR 0004: offline signal generation](docs/adr/0004-offline-signal-generation.md)

- [Phase 0 中文复盘：烘焙类比、设计取舍与面试问答](docs/Phase0_Explanation_Interview_QA_ZH.html)
- [阶段讲解与验收文档约定](docs/phase-learning-workflow.md)

- [用烘焙理解技术术语 — 中文学习手册](docs/Technology_Glossary_Baking_ZH.html)

- [Architecture](docs/architecture.md)
- [MQTT contract v1](docs/mqtt-contract.md)
- [ADR 0001: software first](docs/adr/0001-software-first.md)
- [ADR 0002: versioned JSON contracts](docs/adr/0002-versioned-json-contracts.md)
- [Git workflow and Windows synchronization](docs/git-workflow.md)
- [Phase 0 acceptance](docs/testing/phase-0-acceptance.md)
- [Phase 1 Windows environment](docs/phase-1-environment.md)
- [Local Mosquitto setup and verification](docs/phase-1-mosquitto.md)
- [双语 Broker 操作与验收](docs/Phase1_Mosquitto_Broker_ZH_EN.html)
- [ADR 0003: local authenticated broker](docs/adr/0003-local-mqtt-broker.md)
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

The broker smoke test has passed on Windows. The offline signal generator can
be run with `python -m simulator --samples 3 --seed 42` from the repository root.
No MQTT sensor publisher or backend application is implemented yet.

## Scope and attribution

This is an independent learning project inspired by the problem domain
of sports motion tracking. It does not reproduce Aiving's proprietary
algorithms or internal architecture.

Synthetic motion detection results will not be presented as evidence
of real-world sporting accuracy.

## License

A license has not yet been selected.
