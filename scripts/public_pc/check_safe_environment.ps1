param([switch]$VerboseCheck)

Write-Host "Public PC safe environment check"
Write-Host "No installation will be performed."

$commands = @("git", "python", "ffmpeg", "reaper")
foreach ($cmd in $commands) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "[info] $cmd found at $($found.Source)"
    } else {
        Write-Host "[info] $cmd not found"
    }
}

Write-Host "[ok] Dry-run safety check complete."

