# ADR 0008: automatic real-broker status acceptance

Status: accepted, 2026-10-28.

## Context
Status code and unit tests exist; real lifecycle evidence is missing. Manual
terminals and debug-log parsing are difficult to reproduce. PostgreSQL follows
minimal Phase 1 completion.

## Decision
Reuse Paho Connection/status_demo. Subscribe before launching a unique one-second
device child; inspect real MQTT online/offline identity and time semantics, then
require a new subscriber to receive identical retained offline. Repeat with
intentional child exit 17. Bound waits and clean only own test retained topics.

## Alternatives
Manual terminals; CLI debug parsing; entirely mocked broker; immediate network
blackhole or broker restart experiments.

## Costs
Requires a real broker and existing ignored credentials. The author has no Docker
engine, so runtime remains pending. Cleanup during outages is best effort.
Process exit does not verify network-blackhole detection, broker disk durability,
DB commits, general high availability or offline replay.

## Reconsider when
Disposable CI infrastructure, integrated telemetry/status, reconnect or dedicated
Phase 4 failure/capacity experiments are implemented.
