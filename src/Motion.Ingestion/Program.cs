using System.Buffers;
using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using MQTTnet;
using MQTTnet.Formatter;
using Npgsql;

using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; stop.Cancel(); };
var failure = new TaskCompletionSource<Exception>(TaskCreationOptions.RunContinuationsAsynchronously);
try
{
    var password = Environment.GetEnvironmentVariable("MOTION_DB_PASSWORD");
    if (string.IsNullOrEmpty(password))
        throw new InvalidOperationException("Set MOTION_DB_PASSWORD for this terminal.");
    using var credentials = JsonDocument.Parse(await File.ReadAllTextAsync("secrets/mqtt/clients.json", stop.Token));
    var backend = credentials.RootElement.GetProperty("backend");
    var connection = new NpgsqlConnectionStringBuilder
    {
        Host = "127.0.0.1", Port = 5433, Database = "motion", Username = "motion",
        Password = password, Timeout = 5, CommandTimeout = 10
    };
    await using var db = NpgsqlDataSource.Create(connection.ConnectionString);
    await using (var probe = db.CreateCommand("SELECT 1 FROM sensor_readings LIMIT 1"))
        await probe.ExecuteScalarAsync(stop.Token);

    var factory = new MqttClientFactory();
    using var mqtt = factory.CreateMqttClient();
    mqtt.DisconnectedAsync += _ =>
    {
        failure.TrySetResult(new IOException("MQTT disconnected; restart the consumer after checking services."));
        return Task.CompletedTask;
    };
    mqtt.ApplicationMessageReceivedAsync += async e =>
    {
        e.AutoAcknowledge = false;
        if (failure.Task.IsCompleted || stop.IsCancellationRequested) return;
        try
        {
            string outcome;
            try
            {
                var sample = Reading.Parse(e.ApplicationMessage.Topic, e.ApplicationMessage.Payload.ToArray());
                outcome = await SaveAsync(db, sample, stop.Token);
            }
            catch (InvalidTelemetryException)
            {
                Console.WriteLine("REJECT invalid telemetry");
                await e.AcknowledgeAsync(stop.Token);
                return;
            }
            Console.WriteLine(outcome);
            await e.AcknowledgeAsync(stop.Token);
        }
        catch (Exception ex)
        {
            failure.TrySetResult(ex);
        }
    };

    using var startup = CancellationTokenSource.CreateLinkedTokenSource(stop.Token);
    startup.CancelAfter(TimeSpan.FromSeconds(15));
    var result = await mqtt.ConnectAsync(new MqttClientOptionsBuilder()
        .WithTcpServer("127.0.0.1", 1883)
        .WithProtocolVersion(MqttProtocolVersion.V500)
        .WithClientId("motion-ingest-" + Guid.NewGuid().ToString("N"))
        .WithCredentials(backend.GetProperty("username").GetString()!, backend.GetProperty("password").GetString()!)
        .Build(), startup.Token);
    if ((int)result.ResultCode != 0) throw new IOException($"MQTT CONNECT rejected: {result.ResultCode}");

    var subscription = await mqtt.SubscribeAsync(factory.CreateSubscribeOptionsBuilder()
        .WithTopicFilter(f => f.WithTopic("motion/v1/devices/+/telemetry").WithAtLeastOnceQoS())
        .Build(), startup.Token);
    if (subscription.Items.Count() != 1 || subscription.Items.Any(i => (int)i.ResultCode != 1))
        throw new IOException("Broker did not grant QoS 1 for telemetry.");
    Console.WriteLine("READY .NET ingestion");
    var error = await failure.Task.WaitAsync(stop.Token);
    throw error;
}
catch (OperationCanceledException) when (stop.IsCancellationRequested) { }
catch (Exception ex)
{
    // Do not print connection strings, credentials, or payloads.
    Console.Error.WriteLine(ex is IOException or InvalidOperationException
        ? $"Ingestion stopped: {ex.GetType().Name}"
        : $"Ingestion stopped: {ex.GetType().Name}; check broker, database and migration.");
    return 1;
}
return 0;

static async Task<string> SaveAsync(NpgsqlDataSource db, Reading r, CancellationToken ct)
{
    await using var conn = await db.OpenConnectionAsync(ct);
    await using var tx = await conn.BeginTransactionAsync(ct);
    await using (var device = new NpgsqlCommand(
        "INSERT INTO devices (device_id) VALUES ($1) ON CONFLICT DO NOTHING", conn, tx))
    {
        device.Parameters.AddWithValue(r.Device);
        await device.ExecuteNonQueryAsync(ct);
    }
    const string columns = "message_id,device_id,stream_id,sequence,sampled_at," +
        "acceleration_x,acceleration_y,acceleration_z,angular_velocity_x,angular_velocity_y,angular_velocity_z";
    const string values = "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11";
    await using var write = new NpgsqlCommand(
        $"INSERT INTO sensor_readings ({columns}) VALUES ({values}) ON CONFLICT DO NOTHING", conn, tx);
    Bind(write);
    var count = await write.ExecuteNonQueryAsync(ct);
    if (count == 1)
    {
        await tx.CommitAsync(ct);
        return $"STORED {r.Id} {r.Device} seq={r.Sequence}";
    }

    await using var match = new NpgsqlCommand(
        $"SELECT EXISTS (SELECT 1 FROM sensor_readings WHERE message_id=$1 AND ({columns})=({values}))",
        conn, tx);
    Bind(match);
    var identical = (bool)(await match.ExecuteScalarAsync(ct))!;
    await tx.RollbackAsync(ct);
    return identical ? $"DUPLICATE {r.Id}" : $"CONFLICT {r.Id}";

    void Bind(NpgsqlCommand cmd)
    {
        foreach (var value in new object[] { r.Id, r.Device, r.Stream, r.Sequence, r.SampledAt,
            r.Ax, r.Ay, r.Az, r.Gx, r.Gy, r.Gz })
            cmd.Parameters.Add(new NpgsqlParameter { Value = value });
    }
}

sealed class InvalidTelemetryException : FormatException { }

sealed record Reading(Guid Id, string Device, Guid Stream, long Sequence, DateTime SampledAt,
    double Ax, double Ay, double Az, double Gx, double Gy, double Gz)
{
    public static Reading Parse(string topic, byte[] bytes)
    {
        try
        {
            using var json = JsonDocument.Parse(bytes);
            var p = json.RootElement;
            ValidateKeys(p);
            var device = p.GetProperty("deviceId").GetString()!;
            var sequence = p.GetProperty("sequence").GetInt64();
            var timestamp = p.GetProperty("sampledAt").GetString()!;
            if (p.GetProperty("schemaVersion").GetInt32() != 1 ||
                !Regex.IsMatch(device, @"\A[a-z0-9][a-z0-9_-]{0,63}\z") ||
                topic != $"motion/v1/devices/{device}/telemetry" ||
                sequence is < 0 or > 9007199254740991 ||
                !Regex.IsMatch(timestamp, @"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z\z") ||
                !DateTime.TryParseExact(timestamp, ["yyyy-MM-dd'T'HH:mm:ss'Z'", "yyyy-MM-dd'T'HH:mm:ss.FFFFFF'Z'"],
                    CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                    out var sampled))
                throw new InvalidTelemetryException();

            if (p.TryGetProperty("simulation", out var sim) &&
                sim.GetProperty("scenario").GetString() is not ("idle" or "motion" or "jump" or "landing"))
                throw new InvalidTelemetryException();
            var a = p.GetProperty("accelerationMps2");
            var g = p.GetProperty("angularVelocityRadps");
            return new Reading(IdOf("messageId"), device, IdOf("streamId"), sequence, sampled,
                Axis(a, "x"), Axis(a, "y"), Axis(a, "z"), Axis(g, "x"), Axis(g, "y"), Axis(g, "z"));

            Guid IdOf(string key)
            {
                var value = p.GetProperty(key).GetString();
                if (value?.Length != 36 || !Guid.TryParseExact(value, "D", out var id))
                    throw new InvalidTelemetryException();
                return id;
            }
        }
        catch (Exception ex) when (ex is JsonException or FormatException or KeyNotFoundException or InvalidOperationException or ArgumentNullException)
        {
            throw new InvalidTelemetryException();
        }
    }

    static void ValidateKeys(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name)) throw new InvalidTelemetryException();
                ValidateKeys(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
            foreach (var item in element.EnumerateArray()) ValidateKeys(item);
    }

    static double Axis(JsonElement vector, string axis)
    {
        var value = vector.GetProperty(axis).GetDouble();
        return double.IsFinite(value) ? value : throw new InvalidTelemetryException();
    }
}
