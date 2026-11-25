\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
    fixture sensor_readings%ROWTYPE;
    retry_count integer;
BEGIN
    INSERT INTO devices (device_id) VALUES ('phase2a-smoke') ON CONFLICT DO NOTHING;
    INSERT INTO sensor_readings
        (message_id, device_id, stream_id, sequence, sampled_at,
         acceleration_x, acceleration_y, acceleration_z,
         angular_velocity_x, angular_velocity_y, angular_velocity_z)
    VALUES ('7395991c-2054-4bf8-b455-cb015eb05ad1', 'phase2a-smoke',
            '309b2562-cf56-4e91-bb8f-a6b55f8a7f35', 0, '2026-01-01T00:00:00Z',
            0, 0, 9.81, 0, 0, 0)
    ON CONFLICT (message_id) DO NOTHING;
    SELECT * INTO STRICT fixture FROM sensor_readings
      WHERE message_id = '7395991c-2054-4bf8-b455-cb015eb05ad1';
    IF fixture.device_id <> 'phase2a-smoke'
       OR fixture.stream_id <> '309b2562-cf56-4e91-bb8f-a6b55f8a7f35'
       OR fixture.sequence <> 0 OR fixture.acceleration_z <> 9.81 THEN
        RAISE EXCEPTION 'Smoke fixture does not match';
    END IF;

    INSERT INTO sensor_readings SELECT (fixture).*
      ON CONFLICT (message_id) DO NOTHING;
    GET DIAGNOSTICS retry_count = ROW_COUNT;
    IF retry_count <> 0 THEN RAISE EXCEPTION 'Duplicate message inserted'; END IF;

    BEGIN
        INSERT INTO sensor_readings
        SELECT gen_random_uuid(), fixture.device_id, fixture.stream_id, fixture.sequence,
               fixture.sampled_at, fixture.received_at, 0, 0, 9.81, 0, 0, 0;
        RAISE EXCEPTION 'Expected duplicate stream sequence rejection';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO sensor_readings
        SELECT gen_random_uuid(), 'phase2a-missing-' || gen_random_uuid()::text,
               fixture.stream_id, 1, fixture.sampled_at, fixture.received_at, 0, 0, 9.81, 0, 0, 0;
        RAISE EXCEPTION 'Expected missing device rejection';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
END $$;
COMMIT;
\echo PASS PostgreSQL: wrote sample; duplicate message, stream sequence and foreign key checks passed.
