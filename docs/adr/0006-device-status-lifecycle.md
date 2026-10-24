# ADR 0006: isolated device status lifecycle demo

Status: accepted for Phase 1 slice, 2026-10-24.

## Context
Single-device MQTT is verified by logs; the owner reports two-device receiving
success. Presence is not derivable solely from successful telemetry transmission.
We need a small inspectable status experiment before integration with publishers.

## Decision
Use the existing status contract and role ACL. Publish retained QoS 1 online after
CONNACK, graceful offline before normal disconnect. Register a retained offline
Will before CONNECT with reportedAt null. Each run has a fresh connectionId.
A watcher distinguishes cached from live messages and requires matching live
online/offline connection IDs. A separate snapshot command requires retained state.
Fault injection exits only its own process with code 17, bypassing offline/Disconnect.
Initial user acceptance covers graceful behavior first; Will acceptance follows.

## Alternatives
Infer online from traffic only; retained state without Will; add application
heartbeats immediately; integrate lifecycle into every publisher at once.

## Costs and limits
Status-only CLI adds a temporary separate entry point. Retained is a last known
announcement, not current connectivity truth or history. Unexpected disconnect
is detected asynchronously; broker downtime cannot guarantee Will emission.
Shared credentials do not isolate device identity. Only one writer per device is
assumed; stale-session conflict arbitration and activity timeouts are deferred.
On some failure paths graceful disconnect can leave a stale retained online;
this demo is not a production state machine. No automatic reconnect or replay.

## Validation
20 offline tests and existing 46 contract checks passed in author environment.
Tests cover null Will time, fractional UTC timestamps, cached/live interpretation,
connection IDs, retained snapshots and Will-before-connect/graceful ordering.
Status Schema contained an over-escaped fractional-second dot in both branches;
corrected it to accept the documented 1–6 decimal UTC precision. New regression
covers seconds, milliseconds, microseconds and rejected 7-digit fractions.
Real Windows status/Will execution pending; no runtime guarantee inferred.

## Reconsider when
Merging status into the real telemetry producer, reconnecting, simultaneous device
writers, backend presence timeout rules, retained ordering or broker recovery tests.

Reference: https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html
