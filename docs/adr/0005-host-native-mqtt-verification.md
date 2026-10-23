# ADR 0005: bounded host-native MQTT verification using Paho

Status: accepted for Phase 1 slice, 2026-10-23.

## Context
Broker container-client checks and Windows offline idle generation passed.
A host-native Python communication path still needs real verification. Previous
live CLI debug parsing was fragile and its precise failure remains unconfirmed.

## Decision
Pin paho-mqtt 2.1.0; use MQTT v5 and callback API VERSION2. Run a separate bounded
publisher/subscriber on Windows with existing simulator/backend roles. Drive the
network loop synchronously so callback state shares one thread. Wait for successful
CONNACK, SUBACK and PUBACK reason codes. Publish QoS 1 non-retained telemetry and
validate received unique observations. Use a clean ephemeral session, bounded
waits, explicit failures and graceful disconnect. No auto reconnect in this slice.

## Alternatives
Parse CLI debug lines; start callbacks on background threads; combine publisher
and subscriber into one orchestration script; immediately implement robust replay.

## Costs
Two terminals and manual READY sequencing. Subscriber intentionally requires one
stream starting at zero for this demo; future ingestion must support valid late
and out-of-order data. In-memory deduplication is not durable. Ten Hz is an ideal
timestamp/pacing schedule; delayed ACKs may cause catch-up and timing is not hard
real time. Local plaintext MQTT remains restricted to loopback; no cloud identity.

## Validation
Thirteen offline tests passed in author environment, including actual Paho reason-code
objects for failure paths. Windows live two-process acceptance remains pending.
Success requires both publisher acknowledgments and subscriber validation.

## Reconsider when
Implementing multi-device scheduling, retained status/Will, bounded buffering,
reconnect, durable persistence or throughput testing. Do not infer stronger end-to-
end guarantees from successful PUBACKs.

Reference: https://eclipse.dev/paho/clients/python/docs/
