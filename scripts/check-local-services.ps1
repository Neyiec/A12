# Read-only integration preflight. It never changes credentials, service state or database data.
$ErrorActionPreference = 'Stop'
$targets = @(
    @{ Name = 'MySQL'; Port = 3306 },
    @{ Name = 'PostgreSQL'; Port = 5432 },
    @{ Name = 'Redis'; Port = 6379 },
    @{ Name = 'Java'; Port = 8088 },
    @{ Name = 'Python'; Port = 8001 },
    @{ Name = 'Teacher frontend'; Port = 5173 },
    @{ Name = 'Admin frontend'; Port = 8888 }
)
$failed = $false
foreach ($target in $targets) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.ConnectAsync('127.0.0.1', $target.Port)
        if (-not $pending.Wait(1000) -or -not $client.Connected) { throw 'Unavailable' }
        Write-Host ('[OK] {0} 127.0.0.1:{1}' -f $target.Name, $target.Port)
    } catch {
        $failed = $true
        Write-Host ('[FAIL] {0} port {1} is unavailable. Start this dependency before testing its pages.' -f $target.Name, $target.Port)
    } finally { $client.Dispose() }
}
foreach ($port in @(5173, 8888)) {
    try {
        $entry = Invoke-WebRequest -Uri "http://127.0.0.1:$port/src/main.ts" -TimeoutSec 5 -SkipHttpErrorCheck
        if ($entry.StatusCode -ne 200 -or $entry.Headers['Content-Type'] -notmatch 'javascript') { throw 'Entry module failed' }
        $dependencies = [regex]::Matches($entry.Content, '["''](/node_modules/\.vite/deps/[^"'']+)["'']') |
            ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique -First 6
        foreach ($path in $dependencies) {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port$path" -TimeoutSec 5 -SkipHttpErrorCheck
            if ($response.StatusCode -ne 200) { throw "Dependency HTTP $($response.StatusCode)" }
        }
        Write-Host "[OK] Frontend $port entry and optimized dependencies"
    } catch {
        $failed = $true
        Write-Host "[FAIL] Frontend $port modules unavailable: $($_.Exception.Message). Restart the frontend; do not clear project files."
    }
}
Write-Host 'This checks connectivity and frontend modules, not account permissions or model quality.'
if ($failed) { exit 1 }
