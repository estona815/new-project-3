# Pipeline Claim Contract Check

- Contract: `mesi_v10_evidence_pipeline_contract`
- Max severity: `FAIL`
- Claim status: `not_final_warn_plus`

## Quoted Requirements

> If the only source is MP3, mark it as lossy source.
- Source: `chat`

> Do not claim true rebeat unless drums, bass, and core music elements are actually reconstructed as MIDI/audio/stem tracks inside the REAPER project and bus renders exist.
- Source: `chat`

> If any validation result is WARN or higher, do NOT claim final success.
- Source: `chat`

> drum_reinforcement was rendered as candidate E and audited in the RPP, but it was not selected for the final WAV.
- Source: `mesi_1_v10_final_report`

> This is not true_rebeat, not stem rebuild, not vocal tuned, and not lossless restoration.
- Source: `mesi_1_v10_final_report`

> REAPER project was generated and audited, but audio candidates were rendered through the Python/ffmpeg fallback path.
- Source: `mesi_1_v10_final_report`

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARN | LOSSY_SOURCE_LANGUAGE_REQUIRED | - | MP3-derived processing can be presented as lossless restoration. | source_is_lossy=true or source_format=mp3 | Use processed-print language and do not claim lossless restoration. | - | no |
| WARN | REAPER_RENDER_NOT_PROVEN | - | RPP creation is the same as REAPER audio rendering. | REAPER_RENDER_FALLBACK present | Run REAPER renderproject/batch render before saying REAPER rendered the final WAV. | - | yes |
| FAIL | WARN_PLUS_SURFACED | - | - | EXTERNAL_VALIDATOR_WARN,FULLMIX_ACTIVE_WITH_REBUILD_ITEMS,FULLMIX_DEESSER_RISK,GRID_CONFIDENCE_FAIL,INTEGRATED_LOUDNESS_UNAVAILABLE,LOSSY_SOURCE_REBEAT_LIMITATION,REAPER_RENDER_FALLBACK,REBEAT_BUS_RENDERS_MISSING | Keep every WARN+ item in the final report and do not upgrade claims. | - | yes |

## Allowed Claims

- `Suno DeAI repair`
- `drum reinforcement candidate/audit only`
- `fullmix rescue`
- `lossy-source processed print`

## Forbidden Claims

- `lossless restoration`
- `professional final master`
- `true_rebeat`
- `vocal tuned`
- `비트 다 새로 찍음`
