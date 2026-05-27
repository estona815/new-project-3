param([switch]$Execute)

if (-not $Execute) {
    Write-Host "[dry-run] Would install/verify FFmpeg, Python QC packages, Demucs, UVR, DeepFilterNet, and RNNoise candidates."
    Write-Host "[dry-run] No models or packages are downloaded in dry-run mode."
    exit 0
}

Write-Host "[execute] Placeholder only. Add reviewed commands on the main computer."
exit 2

