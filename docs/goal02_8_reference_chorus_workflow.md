# GOAL 02 8-Reference Chorus Match Workflow

This workflow prepares a measured 20-second chorus comparison for the REAPER mix/master harness. It does not listen or claim a finished master. It reports file-derived metrics, safe mix-stage recommendations, and an optional Python DSP preview package for REAPER transfer.

## Input Contract

- Put the current mix or exported chorus print at `input/target/target_chorus.wav`, or update `configs/goal02_8_reference_manifest.json`.
- Put exactly eight user-owned reference files at `input/reference/ref_01.wav` through `input/reference/ref_08.wav`, or update the manifest paths.
- If a supplied file is a full song, either set `analysis_window.start_seconds` to the chorus entry or set `analysis_window.selection` to `auto_loudest_20s_per_file` and keep `duration_seconds` at `20.0`.
- If target stems are available, set `target_stems.path`; the analyzer will measure each stem over the target 20-second window.
- Keep reference/full-mix material out of the audible master path. Reference tracks must stay muted with master send disabled.

## Run

```bash
python3 tools/analyze_goal02_reference_match.py \
  --manifest configs/goal02_8_reference_manifest.json \
  --output-dir reports/goal02_8_reference_match
```

The tool writes:

- `goal02_reference_features.csv`
- `goal02_reference_8_track_mix_features.json`
- `goal02_target_stem_features.csv`
- `goal02_audio_candidate_inventory.csv`
- `goal02_reference_match.json`
- `GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md`
- `GOAL02_REFERENCE_8_TRACK_MIX_FEATURES.md`
- `GOAL02_PRIMARY_REFERENCE_TRANSLATION_PACK.md`

To build or refresh the per-reference 8-track mix feature proxy report, run:

```bash
python3 tools/build_goal02_reference_mix_feature_report.py
```

This report covers all eight references with measured/proxy fields for density,
peak behavior, vocal/tune/sibilance proxies, 808/kick/drum/high-band proxies,
stereo compatibility, saturation/clipping, and master compression. It does not
claim isolated vocal, drum, bass, reverb, or autotune listening results from
stereo references.

To translate the three primary references into direct REAPER follow/avoid
rules, bus order, plugin scope, and A/B checks, run:

```bash
python3 tools/build_goal02_primary_reference_translation_pack.py
```

This writes `GOAL02_PRIMARY_REFERENCE_TRANSLATION_PACK.md` and
`goal02_primary_reference_translation_pack.json`. The pack covers `ref_03`,
`ref_06`, and `ref_07` only, using measured/proxy language and preserving the
user A/B approval gate.

To audit the full Goal 02 objective text against the current evidence, run:

```bash
python3 tools/audit_goal02_objective_coverage.py
```

This writes `reports/goal02_objective_coverage/goal02_objective_coverage_audit.md`
and `.json`. It must show `non_user_requirements_passed=true`; user A/B success
and approved final delivery remain separate blocked gates until the review is
complete.

To create the non-final preview A/B package from the measured window and
available stems, run:

```bash
python3 tools/render_goal02_chorus_candidate.py \
  --manifest configs/goal02_8_reference_manifest.json \
  --analysis reports/goal02_8_reference_match/goal02_reference_match.json \
  --render-dir renders/goal02_chorus_v01 \
  --report-dir reports/goal02_chorus_v01
```

The preview tool writes:

- `goal02_chorus_v01_CURRENT_TARGET_20s.wav`
- `goal02_chorus_v01_PYDSP_PREVIEW_20s.wav`
- `goal02_chorus_v01_REF_06_RMS_MATCHED_TO_CANDIDATE_20s.wav`
- `goal02_chorus_v01_REF_07_RMS_MATCHED_TO_CANDIDATE_20s.wav`
- `goal02_chorus_v01_REF_03_RMS_MATCHED_TO_CANDIDATE_20s.wav`
- `goal02_chorus_v01_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav`
- `goal02_chorus_v01_metrics.csv`
- `goal02_chorus_v01_qc.json`
- `goal02_chorus_v01_qc_report.md`
- `goal02_chorus_v01_pydsp_processing_trace.json`

To build the actual REAPER runtime project, collect plugin-load trace evidence,
render the 20-second print, and create loud/safe review candidates, run:

```bash
python3 tools/render_goal02_chorus_reaper.py
```

The REAPER runtime tool writes:

- `reaper/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01.rpp`
- `reports/goal02_chorus_reaper_v01/actual_reaper_plugin_trace.json`
- `renders/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01_REAPERPRINT_24-48.wav`
- `renders/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01_REAPERPRINT_SAFE_STREAMING_20s.wav`
- `renders/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01_REAPERPRINT_LOUD_REFERENCE_20s.wav`
- `renders/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01_AB_CURRENT_LOUDMASTER_PRIMARY_REFS.wav`
- `reports/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01_metrics.csv`
- `reports/goal02_chorus_reaper_v01/goal02_chorus_reaper_v01_runtime_report.md`

After the REAPER runtime pass, validate the main vocal first-slot gate:

```bash
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/goal02_chorus_reaper_v01/actual_reaper_plugin_trace.json \
  --main-track '08 MALE_NONHOOK_CENTER'
```

Then measure the runtime package with FFmpeg `loudnorm`:

```bash
python3 tools/analyze_goal02_runtime_loudness.py
```

If the runtime loud/safe exports miss their LUFS/TP targets, build the corrected
LUFS-target package:

```bash
python3 tools/build_goal02_lufs_target_package.py
```

The corrected LUFS package writes:

- `renders/goal02_chorus_lufs_target_v01/goal02_lufs_target_v01_REAPER_SAFE_STREAMING_-13p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v01/goal02_lufs_target_v01_REAPER_LOUD_REFERENCE_-9p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v01/goal02_lufs_target_v01_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav`
- `reports/goal02_chorus_lufs_target_v01/goal02_lufs_target_package.md`

For the intermediate low-end-focused v02 review candidate, rebuild the REAPER pass
with a controlled 808/BASS stem offset instead of increasing master pressure:

```bash
python3 tools/render_goal02_chorus_reaper.py \
  --slug goal02_chorus_reaper_v02 \
  --bass-gain-offset-db 1.5

python3 tools/analyze_goal02_runtime_loudness.py \
  --runtime-summary reports/goal02_chorus_reaper_v02/goal02_chorus_reaper_v02_runtime_summary.json \
  --report-dir reports/goal02_chorus_reaper_v02

python3 tools/build_goal02_lufs_target_package.py \
  --runtime-summary reports/goal02_chorus_reaper_v02/goal02_chorus_reaper_v02_runtime_summary.json \
  --render-dir renders/goal02_chorus_lufs_target_v02 \
  --report-dir reports/goal02_chorus_lufs_target_v02 \
  --output-slug goal02_lufs_target_v02
```

The v02 LUFS review package writes:

- `renders/goal02_chorus_lufs_target_v02/goal02_lufs_target_v02_REAPER_SAFE_STREAMING_-13p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v02/goal02_lufs_target_v02_REAPER_LOUD_REFERENCE_-9p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v02/goal02_lufs_target_v02_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav`
- `reports/goal02_chorus_lufs_target_v02/goal02_lufs_target_package.md`

For the intermediate v03 review candidate, use a slightly stronger but still
bus-level 808/BASS offset:

```bash
python3 tools/render_goal02_chorus_reaper.py \
  --slug goal02_chorus_reaper_v03 \
  --bass-gain-offset-db 2.5

python3 tools/analyze_goal02_runtime_loudness.py \
  --runtime-summary reports/goal02_chorus_reaper_v03/goal02_chorus_reaper_v03_runtime_summary.json \
  --report-dir reports/goal02_chorus_reaper_v03

python3 tools/build_goal02_lufs_target_package.py \
  --runtime-summary reports/goal02_chorus_reaper_v03/goal02_chorus_reaper_v03_runtime_summary.json \
  --render-dir renders/goal02_chorus_lufs_target_v03 \
  --report-dir reports/goal02_chorus_lufs_target_v03 \
  --output-slug goal02_lufs_target_v03
```

The v03 LUFS review package writes:

- `renders/goal02_chorus_lufs_target_v03/goal02_lufs_target_v03_REAPER_SAFE_STREAMING_-13p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v03/goal02_lufs_target_v03_REAPER_LOUD_REFERENCE_-9p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v03/goal02_lufs_target_v03_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav`
- `reports/goal02_chorus_lufs_target_v03/goal02_lufs_target_package.md`

For the current preferred v04 review candidate, use the final measured
808/BASS-only sweep:

```bash
python3 tools/render_goal02_chorus_reaper.py \
  --slug goal02_chorus_reaper_v04 \
  --bass-gain-offset-db 3.0

python3 tools/analyze_goal02_runtime_loudness.py \
  --runtime-summary reports/goal02_chorus_reaper_v04/goal02_chorus_reaper_v04_runtime_summary.json \
  --report-dir reports/goal02_chorus_reaper_v04

python3 tools/build_goal02_lufs_target_package.py \
  --runtime-summary reports/goal02_chorus_reaper_v04/goal02_chorus_reaper_v04_runtime_summary.json \
  --render-dir renders/goal02_chorus_lufs_target_v04 \
  --report-dir reports/goal02_chorus_lufs_target_v04 \
  --output-slug goal02_lufs_target_v04

python3 tools/build_goal02_candidate_decision_report.py
```

The current preferred v04 LUFS review package writes:

- `renders/goal02_chorus_lufs_target_v04/goal02_lufs_target_v04_REAPER_SAFE_STREAMING_-13p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v04/goal02_lufs_target_v04_REAPER_LOUD_REFERENCE_-9p5LUFS_20s.wav`
- `renders/goal02_chorus_lufs_target_v04/goal02_lufs_target_v04_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav`
- `reports/goal02_chorus_lufs_target_v04/goal02_lufs_target_package.md`
- `reports/goal02_candidate_decision_v04/goal02_candidate_decision.md`

After the v04 20-second candidate is prepared, an approval-pending full-song
draft can be rendered with the same bus-level settings. This is not a final
delivery master until user A/B and full-song review pass:

```bash
python3 tools/render_goal02_chorus_reaper.py \
  --slug goal02_fullsong_reaper_v04_draft \
  --window-mode full-song \
  --bass-gain-offset-db 3.0

python3 tools/analyze_goal02_runtime_loudness.py \
  --runtime-summary reports/goal02_fullsong_reaper_v04_draft/goal02_fullsong_reaper_v04_draft_runtime_summary.json \
  --report-dir reports/goal02_fullsong_reaper_v04_draft

python3 tools/build_goal02_lufs_target_package.py \
  --runtime-summary reports/goal02_fullsong_reaper_v04_draft/goal02_fullsong_reaper_v04_draft_runtime_summary.json \
  --render-dir renders/goal02_fullsong_lufs_target_v04_draft \
  --report-dir reports/goal02_fullsong_lufs_target_v04_draft \
  --output-slug goal02_fullsong_lufs_target_v04_draft
```

The full-song draft package writes:

- `renders/goal02_fullsong_lufs_target_v04_draft/goal02_fullsong_lufs_target_v04_draft_REAPER_SAFE_STREAMING_-13p5LUFS_FULL_SONG.wav`
- `renders/goal02_fullsong_lufs_target_v04_draft/goal02_fullsong_lufs_target_v04_draft_REAPER_LOUD_REFERENCE_-9p5LUFS_FULL_SONG.wav`
- `renders/goal02_fullsong_lufs_target_v04_draft/goal02_fullsong_lufs_target_v04_draft_AB_CURRENT_CANDIDATE_PRIMARY_REFS_FULL_SONG.wav`
- `reports/goal02_fullsong_lufs_target_v04_draft/goal02_lufs_target_package.md`

After the 20-second and full-song draft packages exist, build the user A/B
review package:

```bash
python3 tools/build_goal02_review_package.py
```

The review package writes:

- `delivery/goal02_v04_user_ab_review/goal02_v04_user_ab_review_USER_AB_PENDING.zip`
- `delivery/goal02_v04_user_ab_review/GOAL02_USER_AB_REVIEW_CHECKLIST.md`
- `delivery/goal02_v04_user_ab_review/GOAL02_REVIEW_PLAYER.html`
- `reports/goal02_v04_user_ab_review/goal02_v04_review_package.md`
- 20-second and full-song WAV review copies.
- 320k MP3 device-check copies.
- Current ZIP size: `596271070` bytes.
- Current ZIP SHA256: `51d11268cc8e863f6b31bb6132574e7a339ab58630b311de336d1999775f55c0`.

This package is not a final delivery ZIP. It only prepares the files needed for
user loudness-matched A/B approval and device translation review.

The checklist and local HTML player now show this exact first-pass A/B order:

```text
Current target -> v04 candidate -> ref_06 -> v04 candidate -> ref_07 -> v04 candidate -> ref_03 -> v04 candidate
```

Record the user decision separately:

```bash
python3 tools/record_goal02_ab_decision.py --decision pending
```

When the user gives an explicit matched-loudness A/B decision, rerun it with one
of:

- `--decision approve_v04_20s_then_extend_final`
- `--decision approve_safe_only`
- `--decision rollback_to_v03_low_end`
- `--decision revise_v04_vocal_forward`
- `--decision revise_v04_hat_sibilance`
- `--decision revise_v04_808_kick`

The checklist/player include full command examples for those decisions. Only
`approve_v04_20s_then_extend_final` and `approve_safe_only` can unlock
final-export preparation; revision decisions keep the final delivery gate
blocked.

The decision record writes:

- `reports/goal02_user_ab_decision/goal02_user_ab_decision.json`
- `reports/goal02_user_ab_decision/goal02_user_ab_decision.md`

The current pending record verifies the review package technically ready
(`8/8` loud/safe target rows pass) but keeps final export blocked until the user
A/B decision exists.

The final delivery gate is approval-gated:

```bash
python3 tools/build_goal02_final_delivery_package.py
```

With the current pending decision this writes:

- `reports/goal02_final_delivery/goal02_final_delivery_gate.json`
- `reports/goal02_final_delivery/goal02_final_delivery_gate.md`

Current status is `BLOCKED_USER_AB_APPROVAL_REQUIRED`; no final delivery ZIP is
created while the blocker is `user_loudness_matched_ab_decision_missing`.
After an approval decision is recorded, the same command can create
`delivery/goal02_final_delivery/goal02_FINAL_DELIVERY_APPROVED_ONLY.zip`.
The final ZIP excludes A/B reference sequences and includes only approved
full-song final audio plus evidence files.

Run the completion audit before claiming the goal is done:

```bash
python3 tools/audit_goal02_completion.py
```

Current audit output:

- `reports/goal02_completion_audit/goal02_completion_audit.json`
- `reports/goal02_completion_audit/goal02_completion_audit.md`
- Status: `GOAL02_INCOMPLETE_BLOCKED_BY_USER_AB_OR_FINAL_DELIVERY`
- Pass: `17 / 19`
- Missing evidence: `0`
- Blocked: `user_ab_approval`, `final_delivery_package`

The audit must show `complete=true` before any finished-master or final-delivery
claim is allowed.

## Decision Rules

- Fewer than eight measured references means the reference-match stage is blocked, not guessed.
- Missing target audio means the REAPER chain plan can only remain a template.
- High-air or sibilance excess becomes a source/bus cleanup instruction, not a master high-shelf boost.
- Weak 808, drum, or vocal metrics are fixed on their own buses before PREMASTER.
- Master-bus processing that needs sustained reduction over 2 dB is a mix-balance failure signal.
- Automatically selected windows are reproducible metric proxies, not proof that the user-approved chorus timestamp is correct.
- The Python DSP preview is a transfer sketch only; final approval still needs an actual REAPER render, plugin trace, LUFS/true-peak metering, and user A/B review.
- The REAPER runtime pass can satisfy render and plugin-trace gates, but LUFS-I/certified true peak and user A/B approval remain separate gates.
- The FFmpeg LUFS-target package can satisfy file-derived LUFS/TP target checks, but user A/B approval remains separate.
- v04 is preferred over v03 for review when the goal is closer 808/sub transfer without extra master limiting; roll back to v03 if user A/B says the 808 masks the vocal or feels too thick.
- Full-song draft exports can prepare the next step, but they do not replace 20-second chorus A/B approval.
- The v04 review ZIP can satisfy review-file packaging and MP3 device-check evidence, but it does not satisfy final user approval or final delivery.
- The user decision record can verify the review package is technically ready, but `pending` explicitly keeps final delivery blocked.
- The final delivery builder must return `BLOCKED_USER_AB_APPROVAL_REQUIRED` and create no ZIP until the user decision record is an approval state.
- The primary-reference translation pack must exist before review-package rebuilds so `ref_03`, `ref_06`, and `ref_07` have explicit follow/avoid/bus/plugin/A-B controls.
- The objective coverage audit must show `non_user_requirements_passed=true` before treating the package as ready for user A/B.
- The completion audit must return `complete=true`; the current `17/19` pass state is not enough for final claims.

## Practical REAPER Order

1. Import references to `REF BUS`; keep them muted and master-send disabled.
2. Import target/stems and route to `VOX BUS`, `DRUM BUS`, `808/BASS BUS`, and `MUSIC BUS`.
3. Run the Goal 02 analysis on the same 20-second chorus window.
4. Build the primary-reference translation pack so each primary ref has explicit follow/avoid rules before any new A/B package.
5. Run the objective coverage audit so the full user objective is checked before review.
6. Optionally render the Python DSP preview to narrow the first REAPER pass.
7. Build/render the actual REAPER runtime pass with `tools/render_goal02_chorus_reaper.py`.
8. Run FFmpeg loudness evidence and build the LUFS-target package when needed.
9. Fix vocal/808/drum deltas at bus level if the runtime metrics still miss the primary references.
10. Use `--bass-gain-offset-db` for conservative 808/BASS revisions before touching master pressure.
11. Only then adjust `MIX BUS` and `PREMASTER`, with gain-matched A/B checks.
12. Render a full-song draft only after the 20-second candidate has measured evidence.
13. Build the `USER_AB_PENDING` review package and check the included 320k MP3 copies.
14. Record the user A/B decision with `tools/record_goal02_ab_decision.py`.
15. Run `tools/build_goal02_final_delivery_package.py`; it must block until approval, then build the approved-only final ZIP.
16. Run `tools/audit_goal02_completion.py` and require `complete=true`.
17. Collect full-song review, final approved MP3 check, and final delivery package evidence.
