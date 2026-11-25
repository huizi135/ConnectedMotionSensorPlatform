param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9][a-z0-9_-]{0,63}$')]
    [string]$DeviceId
)
$ErrorActionPreference = 'Stop'
$base = "http://127.0.0.1:5086/api/v1/devices/$DeviceId/readings"
$query = 'from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z&limit=2'
$url = "$($base)?$query"
$items = @()
foreach ($expected in 2, 2, 1) {
    $page = Invoke-RestMethod -Uri $url
    if ($page.items.Count -ne $expected) { throw "Unexpected page size" }
    $items += $page.items
    if ($expected -eq 2) {
        if (!$page.nextCursor) { throw "Missing next cursor" }
        # Invoke-RestMethod may parse ISO timestamps into DateTime.
        $stamp = $page.nextCursor.afterSampledAt
        if ($stamp -is [datetime]) {
            $stamp = $stamp.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'")
        }
        $encoded = [uri]::EscapeDataString([string]$stamp)
        $url = "$($base)?$query&afterSampledAt=$encoded&afterMessageId=$($page.nextCursor.afterMessageId)"
    } elseif ($null -ne $page.nextCursor) {
        throw "Unexpected next cursor on last page"
    }
}
if (($items.sequence -join ',') -ne '0,1,2,3,4' -or
    @($items.messageId | Select-Object -Unique).Count -ne 5 -or
    @($items | Where-Object { $_.deviceId -ne $DeviceId }).Count -ne 0) {
    throw "Unexpected device, sequence or duplicate message ID"
}
$bad = Invoke-WebRequest -SkipHttpErrorCheck -Uri "$($base)?from=2027-01-01T00:00:00Z&to=2026-01-01T00:00:00Z"
if ([int]$bad.StatusCode -ne 400) { throw "Expected HTTP 400 for reversed range" }
Write-Output 'PASS history API: pages 2+2+1; five unique readings; invalid range returns 400.'
