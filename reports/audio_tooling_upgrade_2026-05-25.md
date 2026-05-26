# Audio Tooling Upgrade - 2026-05-25

## Scope

This upgrade turns the basic REAPER + Python audio setup into a repeatable audio automation toolchain for `/Users/hantaeheuk/Documents/New project 3`.

No paid plugins were installed. No Antares tools were used. Existing reports were not deleted.

## Already Confirmed Before This Pass

- SWS Extension `v2.14.0.7` ARM64 was installed.
  - Installed file: `/Users/hantaeheuk/Library/Application Support/REAPER/UserPlugins/reaper_sws-arm64.dylib`
  - Source: `https://github.com/reaper-oss/sws/releases/download/v2.14.0.7/reaper_sws-arm64.dylib`
- ReaPack `v1.2.6` ARM64 was installed.
  - Installed file: `/Users/hantaeheuk/Library/Application Support/REAPER/UserPlugins/reaper_reapack-arm64.dylib`
  - Source: `https://github.com/cfillion/reapack/releases/download/v1.2.6/reaper_reapack-arm64.dylib`
- REAPER extension smoke test confirmed:
  - `SWS_CF_GetSWSVersion=true`
  - `SWS_BR_GetMouseCursorContext=true`
  - `ReaPack_BrowsePackages=true`
  - `ReaPack_GetOwner=true`
- ReaPack initialized:
  - `/Users/hantaeheuk/Library/Application Support/REAPER/reapack.ini`
  - `/Users/hantaeheuk/Library/Application Support/REAPER/ReaPack/registry.db`
- Default enabled ReaPack remotes are present: ReaPack, ReaTeam Scripts, ReaTeam JSFX, ReaTeam Themes, ReaTeam LangPacks, ReaTeam Extensions, MPL Scripts, and X-Raym Scripts.
- Existing v27 master was previously checked with `pyloudnorm`:
  - file: `renders/hangang_shadow_v27_kick_bass_melody_tune/hangang_shadow_mashup_v27_kick_bass_melody_tune_MASTER_loud_24-48.wav`
  - measured: `-8.92 LUFS`
  - existing report target: approximately `-8.9 LUFS`

## Newly Created Or Updated Files

- `/Users/hantaeheuk/Documents/New project 3/tools/audio_qc_env.sh`
  - Activates the QC venv.
  - Exposes `python`, `ffmpeg`, `ffprobe`, and `ffmpeg-normalize`.
  - Uses `imageio_ffmpeg.get_ffmpeg_exe()` for bundled `ffmpeg`.
  - Adds the bundled ffmpeg directory to `PATH`.
  - Adds `static-ffmpeg` binary directory to `PATH` for real `ffprobe`.
  - Provides `--check`.
- `/Users/hantaeheuk/Documents/New project 3/requirements-audio-qc.txt`
  - Frozen package versions from the QC venv.
- `/Users/hantaeheuk/Documents/New project 3/tools/run_audio_qc.py`
  - Produces JSON and Markdown QC reports for rendered audio.
  - Supports optional `--reference`.
- `/Users/hantaeheuk/Documents/New project 3/tools/reaper_smoke_render.lua`
  - Creates a temporary REAPER project.
  - Synthesizes/imports a short 48 kHz / 24-bit test WAV.
  - Creates a track, inserts ReaEQ, adds marker and region.
  - Saves a temporary render project and renders through REAPER CLI.
  - Logs SWS/ReaPack API status and render output status.
- `/Users/hantaeheuk/Documents/New project 3/reports/reaper_render_qc_test.json`
- `/Users/hantaeheuk/Documents/New project 3/reports/reaper_render_qc_test.md`

## Python QC Environment

- Virtual environment: `/Users/hantaeheuk/.cache/codex-audio-qc/new-project-3-venv`
- Python: `3.12.13`
- Main pinned packages:
  - `pyloudnorm==0.2.0`
  - `ffmpeg-normalize==1.37.8`
  - `soundfile==0.13.1`
  - `imageio-ffmpeg==0.6.0`
  - `static_ffmpeg==3.0`
  - `numpy==2.4.6`
  - `scipy==1.17.1`
  - `tqdm==4.67.3`
  - `mutagen==1.47.0`
  - `cffi==2.0.0`

`static_ffmpeg==3.0` was added because `imageio-ffmpeg` provides `ffmpeg` but not `ffprobe`. Existing core QC packages were not upgraded.

## Commands Run

```sh
tools/audio_qc_env.sh --check
```

```sh
source tools/audio_qc_env.sh && ffmpeg -y -hide_banner -loglevel error -f lavfi -i "sine=frequency=440:duration=2:sample_rate=48000" -filter:a "volume=-12dB" -c:a pcm_s24le /tmp/codex_reaper_render_test.wav && python tools/run_audio_qc.py /tmp/codex_reaper_render_test.wav --out reports/reaper_render_qc_test
```

```sh
open -n -a "REAPER" --args -newinst -new "/Users/hantaeheuk/Documents/New project 3/tools/reaper_smoke_render.lua"
```

```sh
source tools/audio_qc_env.sh && python tools/run_audio_qc.py /tmp/codex_reaper_render_test.wav --out reports/reaper_render_qc_test
```

```sh
source tools/audio_qc_env.sh && ffprobe -hide_banner -v error -show_entries stream=codec_name,sample_rate,channels,bits_per_sample,duration -of json /tmp/codex_reaper_render_test.wav
```

```sh
shasum -a 256 "$HOME/Library/Application Support/REAPER/UserPlugins/reaper_sws-arm64.dylib" "$HOME/Library/Application Support/REAPER/UserPlugins/reaper_reapack-arm64.dylib" requirements-audio-qc.txt
```

## Pass/Fail Results

| Check | Result | Evidence |
| --- | --- | --- |
| `tools/audio_qc_env.sh --check` | PASS | `python`, `pip`, `ffmpeg`, `ffprobe`, `ffmpeg-normalize`, `pyloudnorm`, `soundfile`, `numpy`, and `scipy` all reported available |
| `ffmpeg` callable from env | PASS | `ffmpeg_path=/Users/hantaeheuk/.cache/codex-audio-qc/new-project-3-venv/bin/ffmpeg` |
| `ffprobe` callable from env | PASS | `ffprobe_path=/Users/hantaeheuk/.cache/codex-audio-qc/new-project-3-venv/bin/ffprobe` |
| `ffmpeg-normalize` callable | PASS | `ffmpeg-normalize v1.37.8` |
| Fallback temporary WAV QC | PASS | `reports/reaper_render_qc_test.json` and `.md` were generated from `/tmp/codex_reaper_render_test.wav` |
| REAPER SWS API in smoke render | PASS | `/tmp/codex_reaper_smoke_render.log` shows `SWS_CF_GetSWSVersion=true` and `SWS_BR_GetMouseCursorContext=true` |
| REAPER ReaPack API in smoke render | PASS | `/tmp/codex_reaper_smoke_render.log` shows `ReaPack_BrowsePackages=true` and `ReaPack_GetOwner=true` |
| REAPER ReaEQ insertion | PASS | `/tmp/codex_reaper_smoke_render.log` shows `ReaEQ_insert_index=0` |
| REAPER render output | PASS after fix | Direct render action first failed to create the file; script was fixed to save a temp `.rpp` and call REAPER CLI `-renderproject`; final log shows `render_file_exists_after_renderproject=true` |
| REAPER render format | PASS | `ffprobe` reports `pcm_s24le`, `48000`, `2` channels, `24` bits, `2.000000` seconds |
| Python QC output from REAPER render | PASS | `reports/reaper_render_qc_test.json` and `reports/reaper_render_qc_test.md` generated |

## REAPER Smoke Render Log Summary

Final log path: `/tmp/codex_reaper_smoke_render.log`

Key lines:

```text
SWS_CF_GetSWSVersion=true
SWS_BR_GetMouseCursorContext=true
ReaPack_BrowsePackages=true
ReaPack_GetOwner=true
source_file_exists=true
ReaEQ_insert_index=0
project_file_exists=true
render_cli_exit=true
render_file_exists_after_renderproject=true
```

Rendered file:

- `/tmp/codex_reaper_render_test.wav`

`ffprobe` result:

```json
{
  "codec_name": "pcm_s24le",
  "sample_rate": "48000",
  "channels": 2,
  "bits_per_sample": 24,
  "duration": "2.000000"
}
```

## QC Test Output Summary

Target: `/tmp/codex_reaper_render_test.wav`

- sample rate: `48000`
- channels: `2`
- duration: `2.0`
- integrated LUFS: `-12.788`
- peak dBFS: `-12.041`
- approximate true peak dBFS: `-12.036`
- RMS dBFS: `-15.125`
- crest factor: `3.083 dB`
- DC offset: `0.00000006`
- stereo correlation: `1.0`
- spectral centroid: `436.951 Hz`
- high-frequency energy ratio 8k-20k: `0.0`

Warning flags:

- `too_loud=false`
- `too_quiet=false`
- `possible_clipping=false`
- `excessive_high_frequency_hash=false`
- `mono_incompatibility_risk=false`
- `vocal_beat_balance_cannot_be_judged_without_stems=true`

The stem-related warning is intentionally always true for single-file QC because vocal/beat balance cannot be judged from a stereo render alone.

## SHA256 Hashes

- `reaper_sws-arm64.dylib`
  - `8e6ba86f4aac958871884d9285f4f063844900a04b25251bf95044334b103dba`
- `reaper_reapack-arm64.dylib`
  - `c7670f3b2e405b9037d49b1941a4d8c3762fff326cecc0c58ac4faeca171f07b`
- `requirements-audio-qc.txt`
  - `7c72fc8afa11cb6d40798f65ddede966da3934dd3d924a7b0ff628418fa4467a`

## Remaining Risks

- Approximate true peak uses 4x oversampling in Python. It is useful for catching inter-sample risk, but it is not a certified broadcast meter.
- `static_ffmpeg` introduced extra packaging dependencies because it is used to provide `ffprobe`. This is acceptable for the QC venv but should not be copied into a minimal runtime without review.
- `tools/reaper_smoke_render.lua` proves REAPER can synthesize/import, insert ReaEQ, save, and render through CLI. It does not prove a full song session will render correctly.
- ReaPack repositories are initialized, but no third-party ReaPack packages were installed in this pass.
- Matchering, Pedalboard, Demucs/Open-Unmix, Essentia, and audioFlux remain deferred for sandbox A/B testing before main pipeline adoption.
- Human listening approval is still required for mix/master claims; this toolchain improves automation and QC, not subjective final taste judgment.
