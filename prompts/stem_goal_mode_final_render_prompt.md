# Stem Goal Mode Final Render Prompt

Use this prompt when the user provides stem files and wants a focused final mix/master render revision based on listening dissatisfaction.

## Copy/Paste Prompt

```text
Goal mode objective:
Create a final review-ready REAPER mix/master revision from the provided user-owned stems, explicitly addressing the user's dissatisfaction items, and do not call the render "final" unless the project pipeline and QC evidence gates support it.

Workspace:
/Users/hantaeheuk/Documents/New project 3

Mandatory project context before planning or editing:
1. Check whether `prompts/video_reels_base.md` or `video_reels_base.md` exists if the task includes reel, lyric video, music video, subtitle sync, visualizer, FFmpeg, DaVinci Resolve, CapCut, or video generation. If found, read it first.
2. Read `REAPER_REFERENCE_MIX_PIPELINE.md`.
3. Read `MASTERING_QC_STANDARD.md`.
4. Read `USER_FEEDBACK_REVISION_LOOP.md` and `docs/user_feedback_revision_loop.md`.
5. Read `docs/automix_runbook.md`.
6. Read `VOCAL_CLARITY_REPAIR_SYSTEM/docs/qc_checklist.md`.
7. If this is Mesi 1, read `MESI_1_SINGLE_PIPELINE.md` and do not replace accepted v42 unless explicitly requested.

User-provided inputs:
- Song/project name:
- Stem folder or file paths:
- Current/previous render to compare against, if any:
- Reference track/folder, if any:
- Delivery target: loud reels preview / conservative streaming master / AI source repair / stem rebeat master
- User dissatisfaction notes:
  - 

Treat the dissatisfaction notes as first-class feedback blockers:
1. Record each concrete complaint as feedback using the local feedback revision workflow.
2. Translate each note into a diagnostic/action category before processing.
3. Do not clear a feedback item by intent, taste language, or a plan alone.
4. Resolve feedback only after measured QC, loudness-matched A/B review, and human/user review evidence exist.

Common complaint mapping:
- "보컬이 뿌옇다/잘 안 들린다": inspect 200-500 Hz mud, 2-5 kHz intelligibility, vocal/instrument masking, reverb distance.
- "보컬이 뒤에 있다": prefer dynamic music-bus carving, send ducking, and presence pockets before plain vocal gain.
- "보컬이 너무 앞으로 튄다": tuck lead slightly, preserve consonants, avoid making doubles/adlibs dominate.
- "Suno fizz/AI 티/물먹은 보컬": run the Suno/AI vocal noise rescue gate; use conservative artifact suppression language only.
- "치찰음/10 kHz 이상 쏜다": de-ess and post-OTT/top-end guard; PASS requires no 10 kHz+ fizz spike.
- "저역이 약하다": improve kick/bass body with controlled saturation/density and low-end control, not broad clipping.
- "마스터가 납작하다": audit limiter pressure, crest factor, LRA, transient loss, true peak, and A/B before loudness pushes.
- "스테레오/위상이 이상하다": check correlation, mono fold-down, low-end side energy, and M/S cleanup.
- "악기/멜로디가 묻힌다": tame resonances first, then add embedded M/S presence; do not destroy vocal seat.

Operating rules:
1. Start from the latest timing-approved session or the provided stems, not merely the loudest render.
2. Preserve song timing and arrangement unless the user explicitly asks for edits.
3. Protect original stems, original tracks, routing, and master state.
4. Build a new versioned slug: `<song_slug>_vNN_<short_revision_reason>`.
5. Use:
   - `reaper/<slug>/` for the REAPER project.
   - `audio_work/<slug>/` for processed side assets.
   - `renders/<slug>/` for WAV/MP3/A-B renders.
   - `reports/<slug>/` for QC, decisions, plugin trace, and notes.
6. Keep reference/full-mix tracks muted and out of the active premaster bus.
7. Do scan-only/dry-run planning before destructive or hard-to-rollback changes.
8. Do not claim listening, reference matching, plugin loading, commercial finish, or artifact removal unless backed by measured evidence and user review.

Suno/AI vocal cleanup gate:
If the request involves AI vocal noise, unclear main vocal, Suno fizz, robotic/watery tone, or vocal artifact repair:
1. Verify the actual REAPER JSFX registry before building the session.
2. Required developed plugin:
   - Display name: `JS: Codex Vocal AI Artifact Split Tamer`
   - File: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
   - Local path: `~/Library/Application Support/REAPER/Effects/Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
3. The main vocal's first inserted FX slot must be this plugin.
4. Fallback is not acceptable for this first slot.
5. Before final delivery, run the local vocal-chain validation against `reports/<slug>/actual_reaper_plugin_trace.json`.
6. Avoid main-vocal pitch correction, heavy saturation, Decapitator, Auto-Tune/ReaTune/MAutoPitch/Graillon, or aggressive widening unless the user explicitly re-authorizes after hearing a clean pass.

Processing priorities:
1. Source/stem audit and alignment.
2. Vocal clarity and artifact risk.
3. Vocal placement through masking control, not only gain.
4. Kick/bass/body and low-end translation.
5. Phase/mono compatibility.
6. Controlled loudness and true peak safety.
7. Final polish only after mix problems are solved.

Render path:
1. Create the versioned REAPER session.
2. Render premaster and REAPER print first.
3. Run loudness/limiter/brickwall conversion only after premaster safety checks.
4. Export primary WAV first. MP3 is optional/supporting and never the only final.
5. Create loudness-matched A/B preview against the current/previous render or provided original.
6. Create deliverable ZIP only after measured QC passes.

Minimum deliverables:
- Primary final WAV under `renders/<slug>/`.
- 320k MP3 preview/export when useful.
- Loudness-matched A/B preview.
- REAPER print or premaster audit render when applicable.
- Vocal solo or diagnostic render if the core complaint is vocal clarity.
- `reports/<slug>/qc_metrics.json` and `.csv` or equivalent final QC metrics.
- `reports/<slug>/decision_notes.md` explaining changes, non-changes, plugin trace, failed/fallback attempts, and remaining limitations.
- Deliverable ZIP only when all gates pass.

QC pass requirements:
- Final WAV exists, is nonzero, and is the primary deliverable.
- Sample rate, bit depth, channels, duration, clipping, and silence checks are recorded.
- Loudness and true peak are measured, not guessed.
- MP3 true peak safety is checked when MP3 is exported.
- Vocal clarity PASS requires less mud, enough presence, centered lead, no sibilance spike, no 10 kHz+ fizz spike, no clipping, and no reverb/delay wash over consonants.
- Phase, mono fold-down, low-end stereo risk, side/mid balance, and translation risks are visible.
- Reference/full-mix tracks remained muted and outside premaster.
- User feedback blockers are either unresolved and delivery-blocking, or resolved with evidence.
- Final render evidence, final QC evidence, A/B preview evidence, rollback evidence, approval readiness, deliverable package evidence, final delivery consistency, and professional readiness are run where scripts exist and a final package is requested.

Suggested local gate commands, adapted to the actual project paths:
- `python3 scripts/run_feedback_revision_loop.py --output-dir automix --project-name <project> --pass-id <vNN> --track-name "<track>" --feedback "<user complaint>"`
- `python3 scripts/run_final_render_evidence_gate.py --project-name <project> --output-dir automix`
- `python3 scripts/run_final_qc_evidence_gate.py --project-name <project> --output-dir automix`
- `python3 scripts/run_ab_preview_evidence_gate.py --project-name <project> --output-dir automix`
- `python3 scripts/run_rollback_evidence_gate.py --project-name <project> --output-dir automix`
- `python3 scripts/run_approval_export_readiness.py --project-name <project> --output-dir automix`
- `python3 scripts/run_deliverable_package_evidence_gate.py --project-name <project> --output-dir automix`
- `python3 scripts/run_final_delivery_consistency_gate.py --project-name <project> --output-dir automix`
- `python3 scripts/run_professional_readiness_audit.py --project-name <project> --output-dir automix --final-delivery-requested`

Stop rules:
1. If a stem/source is missing, clipped beyond repair, misaligned, or not user-owned, stop before final claims and request the missing/clean source.
2. If the required first-slot AI vocal rescue plugin cannot be proven loaded for AI vocal cleanup, do not render a deliverable final.
3. If final QC fails, produce a review copy or blocked report, not a safe final.
4. If the user dissatisfaction remains unresolved in listening notes or evidence, final delivery is blocked.
5. If a master push makes the mix flatter, harsher, phasey, or more artifact-heavy, revert and treat it as `mix_revision_required`.

Final response contract:
Report:
- Version slug.
- What user complaints were targeted.
- What changed and what was intentionally left alone.
- Exact deliverable paths.
- QC headline: LUFS, true peak, sample rate/bit depth, MP3 true peak if exported, clipping/silence/phase notes.
- A/B preview path.
- Remaining risks or blockers.
- Whether it is `review_copy`, `qc_passed_review_ready`, `delivery_ready`, or `blocked`.

Do not use words like "perfect", "fully removed", "commercially finished", or "reference matched" unless the evidence and user approval support that exact claim.
```

## Quick Fill Format For The User

```text
스템 경로:

현재 불만:
- 

비교할 이전 렌더:

레퍼런스:

원하는 방향:

절대 하면 안 되는 것:
```
