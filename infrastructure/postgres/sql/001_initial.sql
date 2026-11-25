\set ON_ERROR_STOP on
BEGIN;
SELECT pg_advisory_xact_lock(2041381);
CREATE TABLE IF NOT EXISTS schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);
SELECT NOT EXISTS (SELECT FROM schema_migrations WHERE version = 1) AS apply_v1 \gset
\if :apply_v1
CREATE TABLE devices (
    device_id text PRIMARY KEY CHECK (device_id ~ '^[a-z0-9][a-z0-9_-]{0,63}$'),
    registered_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE sensor_readings (
    message_id uuid PRIMARY KEY,
    device_id text NOT NULL REFERENCES devices (device_id),
    stream_id uuid NOT NULL,
    sequence bigint NOT NULL CHECK (sequence BETWEEN 0 AND 9007199254740991),
    sampled_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    acceleration_x double precision NOT NULL,
    acceleration_y double precision NOT NULL,
    acceleration_z double precision NOT NULL,
    angular_velocity_x double precision NOT NULL,
    angular_velocity_y double precision NOT NULL,
    angular_velocity_z double precision NOT NULL,
    CONSTRAINT sensor_readings_stream_sequence_key UNIQUE (device_id, stream_id, sequence)
);
CREATE INDEX sensor_readings_device_time_idx
    ON sensor_readings (device_id, sampled_at, message_id);
INSERT INTO schema_migrations (version) VALUES (1);
\endif
COMMIT;
