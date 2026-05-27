# Tool Manifest

| Tool | Purpose | Install Status | Official Source | Risk | Fallback |
|---|---|---:|---|---|---|
| REAPER | DAW host and render automation | placeholder | TBD official URL | medium | Manual DAW workflow |
| SWS Extension | Extra actions, markers, workflow utilities | placeholder | TBD official URL | medium | Stock REAPER actions |
| ReaPack | Package manager for REAPER scripts | placeholder | TBD official URL | medium | Manual script copy |
| ReaTeam Scripts | Community script library | placeholder | TBD official URL | medium | Local Lua scripts |
| ReaTeam Extensions | Community REAPER extensions | placeholder | TBD official URL | medium | Skip extension-only steps |
| js_ReaScriptAPI | Advanced REAPER scripting API | placeholder | TBD official URL | medium | Simpler Lua automation |
| ReaImGui | GUI scripting for REAPER tools | placeholder | TBD official URL | medium | CLI/template workflow |
| FFmpeg | Decode, encode, loudness probes, format conversion | placeholder | TBD official URL | low | Python WAV-only tools |
| Demucs | Source separation candidate generation | placeholder | TBD official URL | high | Manual stems or skip separation |
| UVR | GUI source separation alternatives | placeholder | TBD official URL | high | Demucs or manual stems |
| DeepFilterNet | Denoise candidate generation | placeholder | TBD official URL | high | REAPER EQ/gate only |
| RNNoise | Light voice noise suppression | placeholder | TBD official URL | medium | Conservative dynamic EQ |
| numpy | QC math support | placeholder | PyPI placeholder | low | Python stdlib summaries |
| scipy | Signal analysis for QC | placeholder | PyPI placeholder | low | Reduced QC |
| soundfile | WAV read/write for QC | placeholder | PyPI placeholder | low | wave module only |
| librosa | Higher-level MIR/spectrum checks | placeholder | PyPI placeholder | medium | scipy/numpy analysis |
| pyloudnorm | Loudness measurement | placeholder | PyPI placeholder | low | Approximate RMS/peak only |
| Bertom Denoiser Classic | Conservative vocal noise reduction | main-computer-only | https://bertomaudio.com/denoiser-classic.html | medium | Skip denoise or use stock EQ/gate |
| TDR Nova | Dynamic EQ and de-fizz | main-computer-only | https://www.tokyodawn.net/tdr-nova/ | low | ReaEQ automation |
| Techivation T-De-Esser 2 | De-ess and harshness control | main-computer-only | https://techivation.com/t-de-esser-plus | low | ReaXcomp/dynamic EQ |
| Voxengo SPAN | Spectrum/correlation QC | main-computer-only | https://www.voxengo.com/product/span/ | low | Python spectrum QC |
| Youlean Loudness Meter | Loudness/true-peak QC | main-computer-only | https://youlean.co/youlean-loudness-meter/ | low | pyloudnorm/ffmpeg ebur128 |
| LoudMax | Preview/final safety limiter | main-computer-only | https://loudmax.blogspot.com/ | medium | REAPER JS limiter |
| Klanghelm IVGI/DC1A/MJUC jr | Body restore and gentle level | main-computer-only | https://klanghelm.com/contents/freeware.html | medium | ReaComp/saturation fallback |
| TAL-Reverb-4 / Valhalla Supermassive | Optional space | manual optional | official vendor pages | medium | REAPER stock reverb/delay |
| GSnap / Graillon | Pitch correction | disabled by default | official vendor pages | high | Manual pitch review only |
| v0.2 Safety Runner | Unified safety and dry-run command entrypoint | repository script | scripts/runner/runner.py | low | Manual safety scripts |
| Candidate Decision Engine | Schema and rules for A/B/C/D decisions | repository docs | decision_engine/ | low | Manual listening notes |

## Knowledge Base Research Tools

| Tool/Layer | Purpose | Install Status | Official Source | Risk | Fallback |
|---|---|---:|---|---|---|
| Source index | Track public resource metadata without copying content | repo-text-only | `knowledge_base/00_source_index/source_index.yml` | low | Manual markdown notes |
| Lesson card schema | Convert source notes into structured original lessons | repo-text-only | `decision_engine/mix_lesson_card_schema.yml` | low | Plain markdown lesson notes |
| REAPER rule schema | Convert lessons into actionable chain rules | repo-text-only | `decision_engine/reaper_rule_card_schema.yml` | low | Manual REAPER checklist |
| QC rule schema | Convert lessons into listening/metering decisions | repo-text-only | `decision_engine/qc_rule_card_schema.yml` | low | Manual QC checklist |
| YouTube source references | Store title, creator, URL, timestamp notes, and original summaries only | no-download | Public video pages | medium | Skip video source |

Knowledge base tools do not install software, download media, process audio, or scrape full content. Their final purpose is REAPER execution and QC: lesson cards must become chain rules, report fields, and rejection conditions.
