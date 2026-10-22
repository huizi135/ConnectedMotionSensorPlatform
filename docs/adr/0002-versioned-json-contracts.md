# ADR 0002 Use versioned JSON contracts with explicit envelope validation

- Status: accepted as a Phase 0 baseline for review; application integration unverified.
- Date: 2026-10-22.
- Scope: Python/.NET wire compatibility, validation and protocol evolution.

## Context

Independent simulator and backend modules need a shared definition of valid IMU
and status messages. Readable JSON is useful at the initial 10 Hz debugging rate.
Implicit units, ambiguous clocks and simulator labels can create hidden coupling.
A JSON payload schema cannot inspect its MQTT topic or remember previous messages.

## Decision and rationale

Use JSON Schema Draft 2020-12 for telemetry and status, versioned under v1. Publish
one sample per telemetry message; separate retained status from non-retained data.
Specify SI units, axes, UTC timestamp spelling, stable sample identity and a
JSON-interoperable sequence range. Configure validators to assert date-time and
UUID formats rather than assuming the format keyword always enforces validation.

Allow unknown optional fields for additive evolution. Require and validate known
fields. Use strict JSON decoding plus a separate topic/payload identity check.
Keep stateful and transport guarantees out of the schema. Detector inputs exclude
simulation labels even when the optional debugging label is present in the envelope.

## Alternatives

| Alternative | Benefit | Cost or reason deferred |
| --- | --- | --- |
| Ad hoc parsing only | Minimal upfront files | Python and .NET validation can drift |
| Reject all unknown fields | Catches more misspelled optional fields | Optional extensions become coordinated deployments |
| Protobuf or CBOR | Compact messages and potentially lower parsing overhead | Extra tooling and less transparent debugging; no measured need yet |
| Batch many samples | Less repeated metadata | More complex retry identity, timestamps and latency |
| Infer types, units or time zones | Less explicit metadata | Ambiguous behavior and weak interoperability |

## Consequences and costs

- Schemas, examples and regression tests must evolve together.
- Permissive optional extensions may hide a typo in an optional field; required
  known fields still protect the essential observation shape.
- Format checks and strict numeric decoding need explicit configuration in each
  implementation. The .NET behavior remains a future interoperability test.
- JSON metadata and single-sample messages add bandwidth and parsing cost.
- Protocol versions add migration work but make incompatible changes explicit.
- Synthetic labels cannot be used as evidence of independent event detection.

## Validation

Validate schemas, all three examples and 43 positive/negative regression vectors.
Exercise required fields, numeric types, sequence boundaries, dates, UUIDs,
unknown optional fields, online/offline null handling, topic identity, malformed
JSON, duplicate keys and finite-range numbers. Preserve the output and runner.
The author-environment 46/46 result does not establish Windows or broker behavior.

## Reconsideration conditions

Revisit batching/encoding if measured bandwidth or CPU limits the required rate.
Revisit extension policy if consumer compatibility or optional-field typo rates
justify stricter controls. Require a new major version or a migration plan for
changes to required fields, units, coordinate frames or identity semantics.
Verify the selected .NET parser and validator against the same cases in Phase 2.
