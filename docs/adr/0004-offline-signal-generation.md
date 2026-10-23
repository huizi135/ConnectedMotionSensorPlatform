# ADR 0004: separate offline signal generation from MQTT transport

Status: accepted for the first simulator slice, 2026-10-23.

## Context

The broker has passed Windows smoke checks. The next concern is whether generated
IMU observations and message identities match the existing contract. Python is
newer to the owner than C#; a small independently runnable slice improves diagnosis.

## Decision

Use a network-independent generator, beginning with fixed-orientation idle data.
Use seeded bounded illustrative noise, explicit UTC start and sampling parameters,
a caller-supplied stream UUID, and UUID5 sample IDs derived from stream/device/sequence.
The CLI creates a fresh stream/start each run and validates every sample against
the existing schema. Emit observations without optional scenario labels. Print
JSON Lines to stdout and summary to stderr. Logical 10 Hz timestamps do not imply
wall-clock pacing. CLI inputs are bounded to 1–10,000 samples and 1–1,000 Hz for
this offline debugging slice; these are tool limits, not validated IMU requirements.

## Alternatives

Generate data inside MQTT callbacks; start with complete motion/jump scenarios;
replay a recorded dataset; implement device hardware first.

## Costs

Adds a small CLI boundary and uses the existing tools validator via an explicit
repository path. Noise is not physically calibrated. UUID5 identifies a logical
sample, not content: reusing stream identity with changed inputs is forbidden.
No MQTT, real-time scheduling, status, buffering or reconnect is provided yet.

## Validation

Five tests cover deterministic full messages with all inputs fixed, distinct
stream identities, timestamps/order, signal ranges and label exclusion, real
schema validation and invalid inputs. Author checks passed; Windows is pending.

## Reconsider when

Adding transport scheduling, physical device data, calibrated noise, additional
scenarios or reusable packaging. Change sample batching/identity through an
explicit contract review, not by silently changing retry semantics.
