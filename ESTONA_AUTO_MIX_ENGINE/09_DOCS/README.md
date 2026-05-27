# ESTONA_AUTO_MIX_ENGINE

ESTONA_AUTO_MIX_ENGINE is a code-first mix/master policy engine for user-owned references, previous approved versions, and current stems. It measures abstract balance traits, compares them conservatively, generates mix/master policy JSON, and prepares REAPER/JSFX automation without paid plugin assumptions.

It does not copy melody, chords, toplines, lyrics, arrangement, or a commercial song identity. A reference is a direction profile, not source material.

## Install

```sh
cd ESTONA_AUTO_MIX_ENGINE
python3 -m pip install -r requirements.txt
```

The MVP can run WAV smoke tests with only `numpy` and `scipy`. `librosa`, `soundfile`, and `pyloudnorm` improve analysis accuracy. `ffmpeg` is checked from PATH first; if missing, `imageio-ffmpeg` is used when available.

## Folder Use

- `00_REFERENCES/approved_tracks`: user-approved reference or previous approved renders.
- `01_CURRENT_SONG/stems`: current song stems.
- `02_ANALYSIS`: Python feature extractors and analysis JSON outputs.
- `03_POLICY_ENGINE`: reference comparison and mix/master policy JSON.
- `04_REAPER_AUTOMATION`: Lua scripts for REAPER policy application and render helpers.
- `05_JSFX`: free JSFX processors.
- `06_OUTPUTS`: renders, MP3 checks, A/B previews, logs.
- `07_REPORTS`: markdown reports.

## Run

```sh
python3 02_ANALYSIS/reference_feature_extractor.py
python3 02_ANALYSIS/current_song_analyzer.py
python3 02_ANALYSIS/vocal_beat_masking_analyzer.py
python3 02_ANALYSIS/vocal_pitch_analyzer.py
python3 02_ANALYSIS/saturation_analyzer.py
python3 03_POLICY_ENGINE/compare_current_to_reference.py
python3 03_POLICY_ENGINE/generate_mix_policy.py
python3 03_POLICY_ENGINE/generate_master_policy.py
python3 02_ANALYSIS/loudness_codec_qc.py
```

## REAPER

Copy or symlink the JSFX files in `05_JSFX` to REAPER's Effects folder, then run `04_REAPER_AUTOMATION/apply_policy_to_reaper.lua` from the Action List. Track matching is name-based, so clear names like `lead vocal`, `female adlib`, `beat`, `drums`, `808` help.

## Reports

Reports separate measured facts, policy recommendations, and human listening checks. Do not call a render final until measured QC and user listening approval both pass.

## Limits

This MVP uses proxy metrics. LUFS is approximate unless `pyloudnorm` is installed. Pitch analysis is diagnostic only and does not replace manual correction. REAPER FX parameter mapping is intentionally conservative and JSFX/stock-first.
