param([switch]$Execute)

$envExecute = $env:EXECUTE_INSTALL -eq "1"
Write-Host "Free plugin install harness for Windows"
Write-Host "Official source URLs are listed in plugin_registry/plugin_source_urls.md"

if (-not $Execute -and -not $envExecute) {
    Write-Host "[dry-run] Would open/download official installers for core plugins only on the main computer."
    Write-Host "[dry-run] Refusing to install. Pass -Execute or set EXECUTE_INSTALL=1 on the main computer."
    exit 0
}

Write-Host "[refuse] Execution placeholder. Add reviewed commands locally after manual URL verification."
exit 2

