# MIDI Reconstruction Audit

- RPP: `reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp`
- Classification recommendation: `master_only`
- True rebeat allowed: `False`
- Fullmix dependency: `low`
- Bus renders complete: `False`

## Counts

- Kick notes: `0`
- Snare notes: `0`
- Hat/percussion notes: `0`
- Bass notes: `0`
- Music notes: `0`

## Tracks

| # | Name | Roles | MIDI | Notes | Audio | Muted |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 01_REF_V11_CURRENT_FAVORITE_MUTED | - | False | 0 | True | True |
| 2 | 02_FULL_MIX_ORIGINAL_REF_MUTED | - | False | 0 | False | True |
| 3 | 03_LEAD_VOCAL_RAW_MUTED | music,vocal | False | 0 | False | True |
| 4 | 04_LEAD_VOCAL_CODEX_TUNE_EQ_SUBSTITUTE | music,vocal | False | 0 | False | False |
| 5 | 05_VOCAL_BUS_CODEX | vocal | False | 0 | False | False |
| 6 | 06_MUSIC_SUPPORT_LOW_MUTED | music | False | 0 | False | True |
| 7 | 07_DRUMS_SUPPORT_MUTED | drums | False | 0 | False | True |
| 8 | 08_BASS_SUPPORT_MUTED | bass | False | 0 | False | True |
| 9 | 09_PRINT_TARGET | - | False | 0 | False | True |

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARN | REBEAT_BUS_RENDERS_MISSING | reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp | Role bus render evidence exists. | {"bass": [], "drums": [], "master": [], "mix": [], "music": []} | Render drums, bass, music/support, mix, and master buses, then rerun audit. | - | no |
