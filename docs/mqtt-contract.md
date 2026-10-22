# MQTT contract v1

Status: Phase 0 baseline for review. Schemas and envelope regression tests passed
in the author's environment. Windows installation and runtime communication are
not yet verified. No broker or backend has been implemented.

## Topics and delivery settings

| Published topic | QoS | Retain | Meaning |
| --- | --- | --- | --- |
| `motion/v1/devices/{deviceId}/telemetry` | 1 | false | One timestamped IMU sample |
| `motion/v1/devices/{deviceId}/status` | 1 | true | Latest announced connection state |

Subscribe separately to `motion/v1/devices/+/telemetry` and
`motion/v1/devices/+/status`. Publishers use concrete identities, never wildcards.
Device IDs match `[a-z0-9][a-z0-9_-]{0,63}`: 1–64 ASCII characters, starting with
a lowercase letter or digit. This prevents topic separators and wildcard tokens.
The payload device ID must equal the ID in the topic.

QoS and retain are transport settings, not JSON fields. The static validator does
not test broker behavior. QoS 1 permits duplicate delivery and is not proof of a
database commit or complete offline replay.

## JSON envelope and validation

Encode a UTF-8 JSON object. Reject malformed JSON, duplicate object keys, NaN,
Infinity and numbers that overflow finite double-precision floating-point range.
Do not coerce strings or booleans into sensor numbers or sequence counters.

Validate using JSON Schema Draft 2020-12, with date-time and UUID format assertions
enabled. Some validators treat format as an annotation unless configured. The
provided runner explicitly enables and checks format support. Regex enforces
canonical wire spelling; format assertions also reject impossible calendar dates.

- `schemaVersion` is the integer 1; the topic major version is `v1`.
- Timestamp format is `YYYY-MM-DDTHH:mm:ss[.ffffff]Z`, with 1–6 optional fractional
  digits, uppercase T/Z and a real calendar date. Use UTC, no numeric offsets.
  Leap-second spellings and precision beyond microseconds are outside v1.
- UUIDs use the standard hyphenated hexadecimal spelling; either hex case is accepted.
- Unknown optional fields are allowed for additive evolution. Known fields must
  still satisfy their constraints. Consumers explicitly select known inputs.
- Required fields cannot be omitted or null unless the schema explicitly allows null.

## Telemetry

Schema: `contracts/mqtt/v1/telemetry.schema.json`.
Example: `contracts/mqtt/v1/examples/telemetry.json`.

| Field | Requirement | Purpose |
| --- | --- | --- |
| schemaVersion | Required, integer 1 | Protocol major version |
| messageId | Required UUID | Sample identity; preserved on retry |
| deviceId | Required device ID | Topic/payload identity check |
| streamId | Required UUID | Identifies one sampling run |
| sequence | Required integer, 0–9,007,199,254,740,991 | Run-local order and gap evidence |
| sampledAt | Required canonical UTC timestamp | Sampling time, not arrival time |
| accelerationMps2 | Required numeric x/y/z object | Acceleration including gravity, m/s² |
| angularVelocityRadps | Required numeric x/y/z object | Angular velocity, rad/s |
| simulation | Optional object with required scenario if present | Debugging/reference label only |

The sequence ceiling preserves exact integer interoperability with common JSON
number implementations. Start at zero and increase per generated sample; a
retransmission does not consume a new sequence. On process restart, create a new
streamId; network reconnection alone can preserve the stream. A stream is not a
training session. Never reuse a sample identity for different content.

Use a device-local right-handed frame: X forward, Y left, Z up. Positive rotation
follows the right-hand rule. A stationary sensor with Z upward reads approximately
(0, 0, 9.81) m/s². A future Gateway normalizes hardware units/axes. Map Unity axes
explicitly. No unvalidated physical acceleration bound is imposed by this schema.

The backend adds receivedAt outside the producer envelope. Clock skew prevents
sampledAt/receivedAt differences from being interpreted as pure network latency.

Allowed simulation scenario values: idle, motion, jump, landing. The whole field
may be absent for real-device messages. Scenario labels describe generator intent,
not detected events. Project observations into a separate detector input type;
compare independently produced events with reference intervals afterward.

## Status and Last Will

Schema: `contracts/mqtt/v1/status.schema.json`.
Examples: `status-online.json` and `status-offline-will.json`.

| Field | Requirement | Purpose |
| --- | --- | --- |
| schemaVersion | Required integer 1 | Protocol major version |
| deviceId | Required device ID | Must match topic |
| connectionId | Required UUID | One connection attempt/lifetime |
| state | Required online or offline | Announced state |
| reportedAt | Required field | UTC timestamp; null allowed only for offline |
| batteryPercent | Optional number, 0–100 | Latest reported battery; omit if unavailable |

Before a connection, configure a retained offline Last Will using that connection's
ID and a null reportedAt. After connection, publish retained online status with a
real timestamp and periodically send status heartbeats. On graceful shutdown,
publish retained offline status with a real timestamp. Preserve an ID within that
connection; use a new connectionId when establishing a new connection and ensure
the configured Will matches. Exact client reconnect/Will setup is a Phase 1 test.

A Will cannot know the actual future disconnection time. The backend records its
own observation time. Retained online status can be stale, so device activity
uses both last-announced state and a timeout based on received messages. Define
heartbeat, keep-alive and timeout values during Phase 1 testing, not arbitrarily
in the schema. A retained status is not a historical event log.

## Layer responsibilities and guarantees

1. JSON decoding: syntax, duplicate keys and finite numeric representation.
2. Schema validation: fields, types, ranges, UUIDs and timestamp shape/calendar.
3. Envelope validation: supported topic/version and topic/payload identity equality.
4. Stateful processing later: identity conflicts, duplicates, order/gap evidence,
   stale connections and persistence transactions.
5. Operational tests later: QoS/retain/Will, reconnection, outages, acknowledgments
   and actual durable storage.

The first three are exercised by the included runner. Schema validation alone
cannot test topic equality, sample uniqueness across messages, physical accuracy,
clock synchronization, actual publication rate or persistence guarantees.

## Compatibility and change control

Adding a truly optional field may remain in v1. Changing units, coordinate frame,
identity semantics, required fields or timestamp rules is a breaking change and
requires a new major contract/topic version or an explicit migration plan.

Update schemas, examples, test vectors, contract documentation and ADRs together.
During initial Phase 0 review, this baseline may be revised before the first
implementation. Do not describe pre-implementation decisions as measured results.

## Validation and reproduction

The repository includes three examples and 43 regression vectors. Rejected-case
PASS means rejection matched the expected result, not that the payload was valid.
See `docs/testing/mqtt-contract-validation.txt` for author-environment output.

After Python is installed and checked in Phase 1, run from the repository root:

```powershell
python -m pip install -r tools/requirements-contracts.txt
python tools/validate_contracts.py
```

Use an isolated virtual environment at that point. The requirements file pins the
top-level validation dependency; it is not a full lockfile or the simulator's
runtime dependency definition. This utility validates contracts only and neither
connects to MQTT nor implements a sensor or backend.

## References

- https://json-schema.org/draft/2020-12/
- https://json-schema.org/draft/2020-12/json-schema-validation
- https://python-jsonschema.readthedocs.io/en/stable/validate/

References consulted on 2026-10-22. The validator version used in this specific
experiment is recorded in its output; this is not a latest-version claim.
