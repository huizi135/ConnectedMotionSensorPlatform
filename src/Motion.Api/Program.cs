using System.Globalization;
using System.Text.RegularExpressions;
using Npgsql;
using NpgsqlTypes;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls(Environment.GetEnvironmentVariable("MOTION_API_URL") ?? "http://127.0.0.1:5086");
var password = Environment.GetEnvironmentVariable("MOTION_DB_PASSWORD")
        ?? Environment.GetEnvironmentVariable("POSTGRES_PASSWORD");
if (string.IsNullOrEmpty(password))
    throw new InvalidOperationException("Set MOTION_DB_PASSWORD for this terminal.");

builder.Services.AddSingleton<NpgsqlDataSource>(_ => NpgsqlDataSource.Create(
    new NpgsqlConnectionStringBuilder
    {
        Host = Environment.GetEnvironmentVariable("MOTION_DB_HOST") ?? "127.0.0.1",
        Port = int.Parse(Environment.GetEnvironmentVariable("MOTION_DB_PORT") ?? "5433"),
        Database = "motion", Username = "motion",
        Password = password, Timeout = 5, CommandTimeout = 10
    }.ConnectionString));

var app = builder.Build();
app.MapGet("/api/v1/devices/{deviceId}/readings", async Task<IResult> (
    string deviceId, string? from, string? to, int? limit,
    string? afterSampledAt, Guid? afterMessageId, NpgsqlDataSource db, CancellationToken ct) =>
{
    if (!Regex.IsMatch(deviceId, @"\A[a-z0-9][a-z0-9_-]{0,63}\z"))
        return Results.BadRequest(new { error = "Invalid device ID." });
    if (!TryUtc(from, out var start) || !TryUtc(to, out var end) || start >= end)
        return Results.BadRequest(new { error = "Provide from < to as UTC ISO timestamps ending with Z." });
    var size = limit ?? 100;
    if (size is < 1 or > 500)
        return Results.BadRequest(new { error = "limit must be between 1 and 500." });
    DateTime? after = null;
    if (afterSampledAt is not null || afterMessageId.HasValue)
    {
        if (!afterMessageId.HasValue || !TryUtc(afterSampledAt, out var parsed) || parsed < start || parsed >= end)
            return Results.BadRequest(new { error = "Provide both cursor fields within the query interval." });
        after = parsed;
    }

    const string sql = """
        SELECT message_id, stream_id, sequence, sampled_at, received_at,
               acceleration_x, acceleration_y, acceleration_z,
               angular_velocity_x, angular_velocity_y, angular_velocity_z
        FROM sensor_readings
        WHERE device_id = $1 AND sampled_at >= $2 AND sampled_at < $3
        """;
    var pageSql = after.HasValue
        ? sql + "\nAND (sampled_at, message_id) > ($5, $6)"
        : sql;
    pageSql += "\nORDER BY sampled_at, message_id LIMIT $4";
    try
    {
        await using var cmd = db.CreateCommand(pageSql);
        cmd.Parameters.Add(new NpgsqlParameter { Value = deviceId });
        cmd.Parameters.Add(new NpgsqlParameter { Value = start });
        cmd.Parameters.Add(new NpgsqlParameter { Value = end });
        cmd.Parameters.Add(new NpgsqlParameter { Value = size + 1 });
        if (after.HasValue)
        {
            cmd.Parameters.Add(new NpgsqlParameter { NpgsqlDbType = NpgsqlDbType.TimestampTz, Value = after.Value });
            cmd.Parameters.Add(new NpgsqlParameter { Value = afterMessageId!.Value });
        }
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        var items = new List<ReadingDto>(size + 1);
        while (await reader.ReadAsync(ct))
            items.Add(new ReadingDto(reader.GetGuid(0), deviceId, reader.GetGuid(1), reader.GetInt64(2),
                reader.GetDateTime(3), reader.GetDateTime(4),
                new VectorDto(reader.GetDouble(5), reader.GetDouble(6), reader.GetDouble(7)),
                new VectorDto(reader.GetDouble(8), reader.GetDouble(9), reader.GetDouble(10))));
        object? nextCursor = null;
        if (items.Count > size)
        {
            items.RemoveAt(size);
            var last = items[^1];
            nextCursor = new { afterSampledAt = last.SampledAt, afterMessageId = last.MessageId };
        }
        return Results.Ok(new { items, nextCursor });
    }
    catch (NpgsqlException ex) when (ex.IsTransient && !ct.IsCancellationRequested)
    {
        app.Logger.LogWarning("PostgreSQL history query temporarily unavailable ({ExceptionType}).", ex.GetType().Name);
        return Results.Problem(statusCode: 503, title: "Telemetry storage temporarily unavailable.");
    }
});
await app.RunAsync();

static bool TryUtc(string? value, out DateTime utc)
{
    utc = default;
    return value is not null && Regex.IsMatch(value,
        @"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z\z") &&
        DateTime.TryParseExact(value, ["yyyy-MM-dd'T'HH:mm:ss'Z'", "yyyy-MM-dd'T'HH:mm:ss.FFFFFF'Z'"],
            CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out utc);
}

sealed record VectorDto(double X, double Y, double Z);
sealed record ReadingDto(Guid MessageId, string DeviceId, Guid StreamId, long Sequence,
    DateTime SampledAt, DateTime ReceivedAt, VectorDto AccelerationMps2, VectorDto AngularVelocityRadps);
