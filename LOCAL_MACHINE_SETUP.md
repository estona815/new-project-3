# Local Machine Setup

Use these instructions only on the main trusted music production computer.

## Clone

```bash
git clone <your-github-url> AI_SUNO_VOCAL_REPAIR_REAPER_HARNESS
cd AI_SUNO_VOCAL_REPAIR_REAPER_HARNESS
```

Run safety checks before installing anything:

```bash
python scripts/public_pc/verify_no_audio_files.py
python scripts/public_pc/verify_no_secrets.py
python scripts/local_install/verify_local_install.py
python scripts/runner/runner.py --mode safety-check
```

## Installation Order

1. Read `PUBLIC_PC_RULES.md` and `SECURITY.md`.
2. Run all local install scripts in dry-run mode.
3. Install REAPER.
4. Install REAPER extensions: SWS, ReaPack, ReaTeam packages, js_ReaScriptAPI, ReaImGui.
5. Install audio tools: FFmpeg, Demucs, UVR, DeepFilterNet, RNNoise/noise-suppression-for-voice.
6. Install Python QC packages.
7. Build REAPER template from blueprints.
8. Test with dummy audio.
9. Run real Suno vocal workflow only after dummy test passes.

## macOS

Dry-run:

```bash
bash scripts/local_install/install_reaper_extensions_mac.sh
bash scripts/local_install/install_audio_tools_mac.sh
```

Execute intentionally:

```bash
EXECUTE_INSTALL=1 bash scripts/local_install/install_reaper_extensions_mac.sh
EXECUTE_INSTALL=1 bash scripts/local_install/install_audio_tools_mac.sh
```

## Windows

Dry-run:

```powershell
.\scripts\local_install\install_reaper_extensions_windows.ps1
.\scripts\local_install\install_audio_tools_windows.ps1
```

Execute intentionally:

```powershell
.\scripts\local_install\install_reaper_extensions_windows.ps1 -Execute
.\scripts\local_install\install_audio_tools_windows.ps1 -Execute
```

## v0.2 Local Runner

Set these only on the trusted main computer when you are ready for real execution:

```powershell
$env:LOCAL_PRODUCTION_MACHINE="1"
$env:EXECUTE_INSTALL="1"
```

Even with those variables, runner modes that perform real work still require `--execute`.
