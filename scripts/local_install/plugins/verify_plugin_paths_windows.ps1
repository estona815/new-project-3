$paths = @(
    "C:\Program Files\Common Files\VST3",
    "C:\Program Files\VSTPlugins",
    "C:\Program Files\Common Files\Avid\Audio\Plug-Ins"
)

Write-Host "Windows plugin path dry-run verification"
foreach ($path in $paths) {
    if (Test-Path -LiteralPath $path) {
        Write-Host "[found] $path"
    } else {
        Write-Host "[missing] $path"
    }
}
Write-Host "[ok] No plugin scan performed."

