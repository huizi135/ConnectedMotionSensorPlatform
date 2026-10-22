# ADR 0001 Start with software simulation and MQTT

- Status: accepted for the Phase 0 design baseline; implementation unverified.
- Date: 2026-10-22.
- Scope: initial data source and transport boundary.

## Context

No IMU or ESP32 hardware is currently available. The owner already has C#/.NET,
Azure, Unity and BLE integration experience and wants to deepen backend,
persistence, reliability and architecture skills. The MVP must be reproducible
on Windows without paid cloud services.

## Decision

Implement Python virtual IMU devices that publish versioned JSON samples directly
to a local Mosquitto MQTT broker. Do not implement BLE/GATT in the first version.

Keep the backend dependent on a transport-independent observation model and an
MQTT contract, rather than simulator internals. A future BLE Gateway can map
physical readings into that contract. Keep simulator reference labels outside
the detector's inference input.

## Rationale

This creates a repeatable starting point without blocking on hardware. Fixed
seeds and controlled scenarios support contract checks and later failure/load
experiments. Python is convenient for signal generation while .NET remains the
core backend language.

## Alternatives

| Alternative | Benefit | Reason deferred |
| --- | --- | --- |
| Buy and integrate hardware first | Exercise real timing and BLE behavior immediately | Hardware unavailable and it delays the backend learning path |
| Emulate a BLE peripheral | Exercise some Gateway integration | Adds OS and BLE complexity without validating real radio behavior |
| Replay recorded sensor files | Use realistic captured patterns | No validated recording dataset is available; controlled synthesis is simpler initially |
| Write samples directly to an HTTP API or database | Fewer initial components | Bypasses the MQTT messaging behavior this project intends to study |

## Consequences and costs

- BLE pairing, fragmentation, radio interference and firmware behavior remain untested.
- Synthetic patterns can be unrealistically clean or biased toward the detector.
- Simulation success cannot demonstrate physical sensing accuracy.
- The contract, units, coordinate frame and identity rules must be maintained
  when a real-device adapter is introduced.
- MQTT delivery and end-to-end durable storage still require separate validation.

## Validation

In Phase 1, verify one device and then three devices for five minutes. Check
independent identities/sequences, deterministic motion values, contract validity,
retained status, Last Will and reconnection after a broker restart. Record gaps
and recovery time rather than assuming complete delivery.

In Phase 5, verify that changing reference labels alone does not change detector
predictions. Evaluate independent runs rather than reusing tuning data.

No implementation results are claimed by this ADR.

## Reconsideration conditions

Revisit when the local pipeline has passed acceptance and physical hardware is
available, when real-world timing/radio effects become a learning requirement,
or when a verified dataset provides better test coverage than synthesis.
Revisit the encoding and batching decision separately if measured throughput or
bandwidth overhead exceeds the required operating envelope.
