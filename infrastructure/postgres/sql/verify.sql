\set ON_ERROR_STOP on
SET TIME ZONE 'UTC';
DO $$
BEGIN
    IF (SELECT count(*) FROM sensor_readings JOIN devices USING (device_id)
        WHERE message_id = '7395991c-2054-4bf8-b455-cb015eb05ad1'
          AND device_id = 'phase2a-smoke' AND sequence = 0 AND acceleration_z = 9.81
          AND sampled_at >= '2026-01-01T00:00:00Z' AND sampled_at < '2026-01-02T00:00:00Z') <> 1 THEN
        RAISE EXCEPTION 'Expected one persisted smoke sample';
    END IF;
END $$;
SELECT device_id, sequence, sampled_at, received_at, acceleration_z
FROM sensor_readings JOIN devices USING (device_id)
WHERE message_id = '7395991c-2054-4bf8-b455-cb015eb05ad1';
\echo PASS PostgreSQL: persisted sample found.
