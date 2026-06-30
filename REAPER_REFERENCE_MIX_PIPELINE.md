# REAPER Reference Mix Pipeline

Use this route for future user-owned REAPER mix/master revisions in this workspace, especially Hangang Shadow-style stem work.

## Default Route

1. Start from the latest timing-approved session, not the loudest or newest render.
2. Inspect source stems, previous render notes, alignment reports, and current user complaints before changing sound.
3. Preserve song timing and arrangement unless the user explicitly asks for edits.
4. Keep reference/full-mix tracks muted and out of the active premaster bus.
5. Build a new versioned REAPER folder under `reaper/<song_slug_vNN>`.
6. Put processed side assets under `audio_work/<song_slug_vNN>`.
7. Render into `renders/<song_slug_vNN>`.
8. Write QC and decision notes under `reports/<song_slug_vNN>`.
9. Render premaster and REAPER print first, then run loudness/brickwall conversion and MP3 export.
10. Create a final deliverable ZIP only after measured QC passes.

## Current User-Approved Mwolla Baseline

For future `mwolla` revisions, start from the approved v14 baseline unless the
user explicitly asks to roll back or rebuild from another version.

- Approved slug: `mwolla_v14_no_chop_max_clarity_hook_reprise_master`
- Approval state: `USER_APPROVED_BASELINE`, recorded on `2026-06-19`
- Harness entrypoint: `tools/mwolla_current_approved_master.py`
- Manifest: `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/approved_baseline_manifest.json`
- Final MP3: `renders/mwolla_v14_no_chop_max_clarity_hook_reprise_master/mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER_320k.mp3`
- Final WAV: `renders/mwolla_v14_no_chop_max_clarity_hook_reprise_master/mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER.wav`

Accepted traits to preserve:

- v13 no-chop continuity repair remains active, and printed vocal gap
  attenuation remains disabled.
- v14 vocal placement is the current preference: lead vocal forward/clear,
  layer vocal audible but tucked, and music bus slightly carved/tucked.
- Hook reprise is part of the accepted arrangement: processed vocal hook
  `0.0-16.0s` is copied to `54.0-70.0s`.
- Final stage is no-loudness-push: no loudnorm, no limiter push, peak guard
  only. Accepted metrics were `-14.1 LUFS`, WAV true peak `-1.2 dBFS`, and MP3
  true peak `-1.1 dBFS`.
- `JS: Codex Vocal AI Artifact Split Tamer` must remain first FX slot on
  `10 MAIN_VOCAL_CENTER`.
- `MAIN_VOCAL_BUS -> MUSIC_BUS` sidechain must remain source `1/2` into
  destination `3/4`.

Regression checks:

```sh
python3 tools/mwolla_current_approved_master.py --verify-existing
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/actual_reaper_plugin_trace.json \
  --main-track '10 MAIN_VOCAL_CENTER'
```

## Current Mwolla Reference-Density Candidate

Use this only as a newer candidate for A/B review; it does not replace the v14
user-approved baseline until the user explicitly approves it.

- Candidate slug: `mwolla_v16b_source_stem_repair_reference_density_master`
- Entry script: `tools/mwolla_v16b_source_stem_repair_reference_density_master.py`
- Final MP3: `renders/mwolla_v16b_source_stem_repair_reference_density_master/mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER_320k.mp3`
- Final WAV: `renders/mwolla_v16b_source_stem_repair_reference_density_master/mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER.wav`
- Deliverable ZIP: `renders/mwolla_v16b_source_stem_repair_reference_density_master/mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER_DELIVERABLE.zip`
- Candidate diagnostic: `reports/mwolla_v16b_reference_density_diagnostics/goal02_reference_match.json`

Housekeeping:

- Prior v15/v16A candidate render/report/reaper/audio_work/config outputs were
  deleted before v16B generation at user request.
- v14 approved baseline, source zip, reference audio, and automation scripts
  were preserved.

Measured intent versus v14:

- Preserve v14 no-chop continuity, hook reprise, first-slot vocal rescue plugin,
  and no-loudness-push final stage.
- Improve source/stem density upstream instead of solving on PREMASTER:
  bass/drum band-limited parallel density, stronger 120-350 Hz repair, and
  lead-aware melody/FX/support demasking.
- Keep music/FX separation high-side-only above the low band.
- Keep `MAIN_VOCAL_BUS -> MUSIC_BUS` sidechain source `1/2` into destination
  `3/4`; fail future variants that change this to `1/2 -> 1/2`.
- Do not add Ozone, OTT, clippers, or PREMASTER limiter push for this candidate.

Measured reference deltas from the v16B diagnostic:

- Low energy ratio improved from v14 `0.217060` to v16B `0.460790`;
  reference average is `0.752659`.
- Low-mid ratio moved from v14 `0.174818` to v16B `0.225753`;
  reference average is `0.126892`, so this remains above reference.
- Mid ratio moved from v14 `0.477023` to v16B `0.223133`;
  reference average is `0.087496`.
- Stereo correlation moved from v14 `0.935192` to v16B `0.952994`;
  reference average is `0.945688`.
- Transient density moved from v14 `14.2/s` to v16B `19.9/s`;
  reference average is `23.9625/s`.

Regression checks:

```sh
python3 tools/mwolla_v16b_source_stem_repair_reference_density_master.py
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/mwolla_v16b_source_stem_repair_reference_density_master/actual_reaper_plugin_trace.json \
  --main-track '10 MAIN_VOCAL_CENTER'
python3 tools/analyze_goal02_reference_match.py \
  --manifest configs/mwolla_v16b_reference_density_manifest.json \
  --output-dir reports/mwolla_v16b_reference_density_diagnostics
unzip -t renders/mwolla_v16b_source_stem_repair_reference_density_master/mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER_DELIVERABLE.zip
```

## Current Mwolla Clean Vocal Pocket Candidate

Use this as the newest A/B candidate after the `2026-06-21` stem-QC work order.
It does not replace the v14 user-approved baseline until the user explicitly
approves it after listening.

- Candidate slug: `mwolla_v18_clean_vocal_pocket_master`
- Entry script: `tools/mwolla_v18_clean_vocal_pocket_master.py`
- Final MP3: `renders/mwolla_v18_clean_vocal_pocket_master/mwolla_v18_CLEAN_VOCAL_POCKET_MASTER_320k.mp3`
- Final WAV: `renders/mwolla_v18_clean_vocal_pocket_master/mwolla_v18_CLEAN_VOCAL_POCKET_MASTER.wav`
- Deliverable ZIP: `renders/mwolla_v18_clean_vocal_pocket_master/mwolla_v18_CLEAN_VOCAL_POCKET_MASTER_DELIVERABLE.zip`

Rationale:

- `mwolla_v17_qc_demask_lowend_phase_master` rendered and passed core delivery
  gates, but independent processed-stem QC showed additional phase warnings and
  did not improve the 1.5-5 kHz stem-level proxy, so v17 remains diagnostic.
- v18 keeps the v16B printed stem repair chain and changes only REAPER
  routing/gain pocket: `10 MAIN_VOCAL_CENTER +0.13 dB`, `MUSIC_BUS -0.06 dB`,
  and `MAIN_VOCAL_BUS -> MUSIC_BUS` sidechain send `-1.4 dB` to `-1.1 dB`.
- v18 preserves no-loudness-push final stage, first-slot vocal rescue plugin,
  hook reprise, muted source reference routing, and sidechain source `1/2` into
  destination `3/4`.

Measured v18 gates:

- `qc_summary.passed`: `true`
- Final loudness/TP: `-13.6 LUFS`, WAV true peak `-1.2 dBFS`, MP3 true peak
  `-1.2 dBFS`
- Vocal chain gate: passed
- No-chop timestamp QC: passed
- Hook reprise QC: passed
- Deliverable ZIP integrity: passed
- Known residual: `final_level_consistency_audit` still fails on the
  pre-existing 78-90s low-window structure; this also failed in v14/v16B and is
  not a new v18 regression.

Regression checks:

```sh
python3 tools/mwolla_v18_clean_vocal_pocket_master.py
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/mwolla_v18_clean_vocal_pocket_master/actual_reaper_plugin_trace.json \
  --main-track '10 MAIN_VOCAL_CENTER'
unzip -t renders/mwolla_v18_clean_vocal_pocket_master/mwolla_v18_CLEAN_VOCAL_POCKET_MASTER_DELIVERABLE.zip
```

## Current Mwolla Louder Clear Vocal OTT-Style Candidate

Use this as the louder/clearer A/B candidate after the user approved the v18
direction and then requested a little more loudness, less blur, and light vocal
OTT-style saturation. It does not replace the v14 user-approved baseline, and it
should be compared directly against v18 before becoming a new user-approved
baseline.

- Candidate slug: `mwolla_v19_louder_clear_vocal_ott_saturation_master`
- Entry script: `tools/mwolla_v19_louder_clear_vocal_ott_saturation_master.py`
- Final MP3: `renders/mwolla_v19_louder_clear_vocal_ott_saturation_master/mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER_320k.mp3`
- Final WAV: `renders/mwolla_v19_louder_clear_vocal_ott_saturation_master/mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER.wav`
- A/B MP3: `renders/mwolla_v19_louder_clear_vocal_ott_saturation_master/mwolla_v19_AB_v18_to_louder_clear_vocal_ott_saturation_320k.mp3`
- Deliverable ZIP: `renders/mwolla_v19_louder_clear_vocal_ott_saturation_master/mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER_DELIVERABLE.zip`

Rationale:

- v19 preserves the v18 vocal pocket and the v16B printed stem-repair route,
  then adds a controlled final loudness lift instead of hard PREMASTER limiting.
- Vocal OTT is printed as deterministic parallel DSP, not an external OTT plugin
  parameter write: mid-band `170-5000 Hz`, high-band `5000-12000 Hz`, parallel
  mid delta mix `0.11`, high delta mix `0.065`, saturation drive `0.62 dB`,
  saturation mix `0.035`.
- Post-OTT anti-fizz is printed at `5200-9200 Hz` with max cut `0.46 dB`;
  measured lead presence rose `+0.26 dB` in `1.5-5 kHz`, sibilance rose
  `+0.53 dB` in `5-9 kHz`, and air rose `+0.56 dB` in `10-16 kHz`.
- Final stage target is moderate: loudnorm target `-12.6 LUFS`, true-peak target
  `-1.3 dBTP`, and limiter guard `ffmpeg alimiter limit=0.86`.
- `MAIN_VOCAL_BUS -> MUSIC_BUS` sidechain must remain source `1/2` into
  destination `3/4`; fail future variants that change this to `1/2 -> 1/2`.

Measured v19 gates:

- `qc_summary.passed`: `true`
- Final loudness/TP: `-12.4 LUFS`, WAV true peak `-1.3 dBFS`, MP3 true peak
  `-1.2 dBFS`
- Vocal chain gate: passed
- No-chop timestamp QC: passed
- Hook reprise QC: passed on `54.0-70.0s`
- Deliverable ZIP integrity: passed
- Known residual: `final_level_consistency_audit` flags low 1.5 s windows at
  `52.5-54.0s`, `78.0-84.0s`, and warns through the tail to `90.63s`; treat as
  section-level consistency, not a dropout/chop failure.

Regression checks:

```sh
python3 tools/mwolla_v19_louder_clear_vocal_ott_saturation_master.py
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/mwolla_v19_louder_clear_vocal_ott_saturation_master/actual_reaper_plugin_trace.json \
  --main-track '10 MAIN_VOCAL_CENTER'
unzip -t renders/mwolla_v19_louder_clear_vocal_ott_saturation_master/mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER_DELIVERABLE.zip
```

## Current Mwolla Full Stem Harmony Candidate

Use this as the strongest "last-resort" fullness candidate after the user asked
for the whole stem set to feel harmonically full, similar to raising each stem
about 1 dB, while avoiding breakup. It does not replace v14, v18, or v19 until
the user explicitly approves it after A/B review.

- Candidate slug: `mwolla_v20_full_stem_harmony_master`
- Entry script: `tools/mwolla_v20_full_stem_harmony_master.py`
- Final MP3: `renders/mwolla_v20_full_stem_harmony_master/mwolla_v20_FULL_STEM_HARMONY_MASTER_320k.mp3`
- Final WAV: `renders/mwolla_v20_full_stem_harmony_master/mwolla_v20_FULL_STEM_HARMONY_MASTER.wav`
- A/B MP3: `renders/mwolla_v20_full_stem_harmony_master/mwolla_v20_AB_v19_to_full_stem_harmony_320k.mp3`
- Deliverable ZIP: `renders/mwolla_v20_full_stem_harmony_master/mwolla_v20_FULL_STEM_HARMONY_MASTER_DELIVERABLE.zip`
- Stem report: `reports/mwolla_v20_full_stem_harmony_master/v20_stem_harmony_fullness_report.json`

Rationale:

- v20 preserves v19 vocal OTT-style density and anti-fizz guard, then adds
  printed per-stem active-RMS lifts with peak caps instead of a single broad
  master gain push.
- Active stems were lifted adaptively: bass `+0.41 dB`, drums `+0.54 dB`,
  synth `+0.82 dB`, strings `+0.61 dB`, keyboard `+1.04 dB`, guitar `+0.70 dB`,
  FX `+0.48 dB`, female vocal `+0.22 dB`, backing vocals `+0.37 dB`, reverb
  `+0.18 dB`, and delay `+0.20 dB`.
- Smooth stem-fill envelopes were printed at `52.5-54.0s` `+0.28 dB`,
  `78.0-84.0s` `+0.42 dB`, and `88.5-90.63s` `+0.30 dB` before final
  mastering; this is upstream stem fill, not post-final gain riding.
- Music group active RMS moved from `-17.63` to `-17.28 dB`; support group moved
  from `-20.63` to `-20.40 dB`.
- Final stage target remains controlled: loudnorm target `-12.1 LUFS`,
  true-peak target `-1.3 dBTP`, and limiter guard `ffmpeg alimiter limit=0.86`.
- `MAIN_VOCAL_BUS -> MUSIC_BUS` sidechain must remain source `1/2` into
  destination `3/4`; fail future variants that change this to `1/2 -> 1/2`.

Measured v20 gates:

- `qc_summary.passed`: `true`
- Final loudness/TP: `-11.9 LUFS`, WAV true peak `-1.2 dBFS`, MP3 true peak
  `-1.0 dBFS`
- Vocal chain gate: passed
- No-chop timestamp QC: passed
- Hook reprise QC: passed on `54.0-70.0s`
- Deliverable ZIP integrity: passed
- Known residual: `final_level_consistency_audit` still flags `81.0-84.0s` as
  two low 1.5 s windows around `-2.0 dB` versus active median; treat as a
  remaining arrangement/section density limitation, not dropout/chop.

Regression checks:

```sh
python3 tools/mwolla_v20_full_stem_harmony_master.py
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/mwolla_v20_full_stem_harmony_master/actual_reaper_plugin_trace.json \
  --main-track '10 MAIN_VOCAL_CENTER'
unzip -t renders/mwolla_v20_full_stem_harmony_master/mwolla_v20_FULL_STEM_HARMONY_MASTER_DELIVERABLE.zip
```

## Stem QC Mix/Master Analysis Automation

Use `audio_qc_mixmaster.py` when the user asks whether the stems can produce a
clearer, less blurry, more reference-informed mix before another REAPER render.
This is an evidence-only analysis pass; it does not print premaster or master
audio and must not replace the render/QC gates above.

Command used on `2026-06-21`:

```sh
python3 audio_qc_mixmaster.py \
  --stem-dir stems \
  --reference-dir references \
  --output-dir . \
  --project-name Mwolla \
  --genre "Hip-hop / Digicore / Hyperpop" \
  --target "streaming / youtube / shorts" \
  --reference-zip "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48..zip" \
  --master-render "renders/mwolla_v16b_source_stem_repair_reference_density_master/mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER.wav"
```

Observed source fallback:

- Requested `./stems` was not populated, so analysis used
  `audio_work/mwolla_v16b_source_stem_repair_reference_density_master/source_stems`.
- Reference folder was not populated, so analysis used the Estona reference zip
  at `/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48..zip`.

Generated reports:

- `reports/QC_REPORT.md`
- `reports/stem_metrics.csv`
- `reports/stem_metrics.json`
- `reports/qc_findings.csv`
- `reports/stem_balance_table.csv`
- `reports/masking_report.md`
- `reports/phase_stereo_report.md`
- `reports/plugin_chain_recommendation.md`
- `reports/revision_mix_notes.md`
- `reports/mastering_plan.md`
- `reports/final_delivery_checklist.md`
- `deliverables/DELIVERABLE_STATUS.md`

Measured findings from the pass:

- No automated FAIL items were found in the source-stem numeric QC.
- Lead vocal presence over instrument bus in `1.5-5 kHz` measured only
  `+1.66 dB` approximately, so vocal clarity should be improved through an
  instrument-bus sidechain dynamic EQ pocket before raising the vocal level.
- Bass and drums in `40-120 Hz` were within `1.83 dB`, so kick/808 separation
  should be handled upstream before mastering.
- The measured master print candidate showed true peak `-1.24 dBTP`,
  approximate LUFS-I `-17.52`, and crest `15.34 dB`, so no numeric limiter or
  clipper overuse flag was raised.
- FX, synth, strings, keyboard, guitar, and backing vocals showed elevated
  low-band side energy risk; check mono compatibility below `100-140 Hz`.
- `3 Strings.wav` showed sustained L/R imbalance above `1 dB`.

## Suno AI Vocal Noise Rescue Gate

This gate is mandatory for any Suno/AI vocal noise, AI fizz, vocal artifact repair, or "main vocal is not clean" request.

1. Verify the actual REAPER JSFX registry before building a session. The required developed plugin is:
   - Display name: `JS: Codex Vocal AI Artifact Split Tamer`
   - File: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
   - Local path: `~/Library/Application Support/REAPER/Effects/Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
2. Do not use guessed names such as `JS: estona_SunoNoiseGuard`, `JS: estona_DeAI_NoiseReducer`, or `JS: estona_Vocal_AntiAI_Harsh` as proof that the developed Suno noise plugin loaded. Those names are not the current registered plugin names.
3. On the main vocal track, the first inserted FX slot must be the developed Suno/AI artifact plugin. The plugin trace must show `fx_index: 0` on `vocal_anchor`, `main_vocal`, or `lead_vocal`.
4. Fallback is not allowed for this required first-slot rescue plugin. If REAPER loads `TDR Nova`, `ReaXcomp`, `ReaEQ`, or any other fallback in that slot, stop and fix the plugin name/path before rendering.
5. Do not claim "our developed noise plugin was used" unless `actual_reaper_plugin_trace.json` proves the exact plugin loaded.
6. For clean-main-vocal rescue, do not insert `MAutoPitch`, `ReaTune`, `Graillon`, Antares, Auto-Tune, Decapitator, or heavy saturation on the main vocal unless the user explicitly re-authorizes it after hearing the clean pass.
7. OTT may be used only after the first-slot noise rescue and corrective/dynamic control; follow it with post-OTT anti-fizz/de-ess guarding.
8. Before final delivery, run:

```sh
python3 tools/validate_reaper_vocal_chain_gate.py --trace reports/<slug>/actual_reaper_plugin_trace.json
```

The render is not deliverable if this gate fails.

## Main Vocal Clarity Triage

When the main vocal is cloudy, cracked, robotic, watery, or not clear enough, diagnose these in order before changing levels:

1. Source condition: compare raw/selected cleanup stem against the processed vocal and identify whether the problem is source artifact, timing layer smear, clipping, or processing.
2. Chain order: developed Suno/AI artifact plugin first, then corrective EQ, dynamic EQ/M-S EQ, de-ess, light compression if needed, OTT only if required, then post-OTT guard.
3. Tune artifacts: remove live pitch/tune inserts from the main clean vocal unless explicitly requested; pitch correction can make AI water/robot artifacts more obvious.
4. Saturation artifacts: keep Decapitator and aggressive saturators off the main vocal during clean rescue; use density on music bus/master only if it does not add vocal grit.
5. Layer smear: keep doubles/adlibs tucked, panned, and dynamically filtered so they blur around the lead instead of masking consonants.
6. Masking: use music-bus M/S and dynamic EQ pockets around vocal presence instead of simply pushing vocal level.
7. Verification: final notes must separate actual inserted plugins, failed/fallback plugin attempts, printed DSP, and listening-risk limitations.

## Hangang Shadow Defaults

- Male lead is the main vocal when `12 Vocals.wav` is present.
- Female vocal is never the lead by default. Use it only as a quiet panned adlib/double layer where timing and pitch overlap pass alignment checks.
- Remove or mute female regions that are off-grid, off-pitch, or feel like intro chops.
- Do not repeat the rejected v24 direction: do not activate the new female instrumental bed to glue the beat.
- Favor the v23/v25/v27 timing-safe structure for revisions.
- Keep vocal slightly tucked if the user says the vocal feels over-forward.
- Improve kick/bass with controlled saturation/body, not broad level pushing.
- Make the main melody clearer by taming resonances first, then adding embedded M/S presence.
- Reduce synthetic AI-like top glare before boosting air.

## Reference-Informed Pass

When the user provides a reference folder or track:

1. Treat the reference as user-provided context and analyze the actual audio before changing the mix.
2. Measure at least LUFS, LRA, true peak, RMS/crest, stereo correlation, side-mid level, and spectral bands.
3. Compare the current approved master to the reference median or selected reference track.
4. Translate traits conservatively. Do not chase clipped true peaks or claim an identical match.
5. Keep status as `genre_based_draft` unless lawful source/reference analysis plus user listening feedback supports stronger claims.

For the Estona/Nib reference-set pass, the useful translation was:

- Slightly louder but true-peak-safe final master.
- More low-end density and kick/bass saturation.
- Wider music bed.
- Less 1.5-5 kHz and upper-air glare.
- Melody readable but still embedded.

## REAPER Execution Pattern

Use a deterministic wrapper sequence:

1. `run_build_<slug>.lua` opens REAPER and builds/saves the versioned `.rpp`.
2. `run_render_<slug>_premaster.lua` prepares a premaster render project with print FX disabled.
3. `REAPER -newinst -nosplash -renderproject /tmp/..._PREMASTER_RENDER.rpp`
4. `run_render_<slug>_master.lua` prepares a REAPER print render project with print FX enabled.
5. `REAPER -newinst -nosplash -renderproject /tmp/..._REAPERPRINT_RENDER.rpp`
6. `tools/<slug>_qc.py` runs final loudness/brickwall conversion, MP3 export, metrics, CSV/JSON audit, notes, and optional final ZIP.

Wait for wrapper logs to show `wrapper ok` before rendering. If a wrapper logs an error, fix the script before continuing.

## QC Gate

Before delivering, confirm:

- Final WAV exists.
- Final MP3 exists when requested or useful.
- True peak is safe after WAV and encoded MP3 checks.
- Loudness target is measured, not guessed.
- Reference/full-mix tracks remained muted.
- The Suno AI Vocal Noise Rescue Gate passes when vocal cleanup is involved.
- Notes explain what changed, what did not change, actual inserted plugins, fallback attempts, and remaining limitations.

Do not say the result is commercially finished or reference-matched unless those claims are supported by measured analysis and user listening approval.
