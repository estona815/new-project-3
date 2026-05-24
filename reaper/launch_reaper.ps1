$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Reaper = $env:REAPER_EXE
if (-not $Reaper) { $Reaper = "C:\Program Files\REAPER (x64)\reaper.exe" }
Start-Process -FilePath $Reaper -ArgumentList "-newinst", "-reascript", (Join-Path $ScriptDir "build_project.lua")
