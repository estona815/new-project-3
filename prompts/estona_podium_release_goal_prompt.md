# Estona Podium Release Goal Prompt

Use this prompt when the user provides stems and wants a release-ready REAPER mix/master revision with the Estona/Podium reference direction.

```text
Goal mode objective:
Take the provided user-owned stems and create a release-review-ready REAPER mix/master revision that fixes the current dissatisfaction: the whole sound does not feel uniform or cohesive enough. The final result should move toward the Estona/Podium reference direction and be suitable for actual music distribution review, but do not call it delivery-ready unless measured QC, loudness-matched A/B, feedback resolution, and final delivery gates support that claim.

Workspace:
/Users/hantaeheuk/Documents/New project 3

Use skill/workflow:
Use the HPDC REAPER AutoMix Bible / Hangang Shadow REAPER pipeline for versioned stem revisions, reference-informed mix/master work, render QC, and final delivery evidence.

Mandatory reads before planning:
1. `REAPER_REFERENCE_MIX_PIPELINE.md`
2. `MASTERING_QC_STANDARD.md`
3. `USER_FEEDBACK_REVISION_LOOP.md`
4. `docs/user_feedback_revision_loop.md`
5. `docs/automix_runbook.md`
6. `docs/reference_matching_genre_targeting.md`
7. `VOCAL_FIRST_MIXING_STRATEGY.md`
8. `AUDIO_ENGINEERING_NOTES.md`
9. `VOCAL_CLARITY_REPAIR_SYSTEM/docs/qc_checklist.md`
10. If the song is Mesi 1, also read `MESI_1_SINGLE_PIPELINE.md` and do not replace accepted v42 unless explicitly requested.

User inputs for this run:
- Stem folder or files: <USER WILL PROVIDE>
- Current dissatisfaction: "소리 전체가 균일하지 않다. 전체 결, 밀도, 공간, 톤, 에너지, 스템 접착감이 한 음원처럼 붙지 않는다."
- Reference direction: Estona/Podium.
- Desired target: actual music distribution/release registration review quality.
- Previous render/current mix for A/B: <USER WILL PROVIDE OR LOCATE>
- Reference audio path: <USER WILL PROVIDE OR LOCATE>

Interpret the dissatisfaction as first-class feedback blockers:
1. Register the main feedback item:
   - "전체 사운드가 균일하지 않고 응집감이 부족하다."
2. Break it into sub-blockers:
   - stem-to-stem tone mismatch;
   - inconsistent loudness or section energy;
   - vocal does not sit naturally in the beat;
   - music bed width/depth feels uneven;
   - low-end density is not controlled enough;
   - top end or AI-like glare makes the mix feel unpolished;
   - master feels like separate layers being limited together instead of one finished record.
3. Resolve each blocker only with evidence: measured QC, loudness-matched A/B, and human/user review. A plan alone does not clear feedback.

Estona/Podium reference translation:
Use the reference for broad mix traits only. Do not copy melody, lyrics, arrangement, drum pattern, vocal identity, chords, or reference audio content.

Target traits:
1. Controlled low-end density:
   - kick/bass feel weighty and steady;
   - no muddy low-mid bloom;
   - low end remains mono-safe and translatable.
2. Wider music bed:
   - synths/samples/pads feel wider than the centered vocal;
   - side energy is cleaned before widening;
   - no phasey chorus wash or mono collapse.
3. Reduced synthetic top glare:
   - tame harsh 1.5-5 kHz edge where it reads as AI/synthetic;
   - control 6-9 kHz sibilance/harshness;
   - avoid 10 kHz+ fizz spike.
4. Embedded melody clarity:
   - main melodic element is readable;
   - melody stays inside the record, not pasted on top;
   - do resonance taming before broad boosts.
5. Slightly hotter but true-peak-safe final loudness:
   - genre-appropriate loudness may be pursued only after mix cohesion passes;
   - do not chase unsafe clipped reference peaks;
   - preserve crest factor and transient feel.
6. Vocal-forward but not detached:
   - lead vocal stays clear, centered, and emotionally close;
   - vocal placement is achieved with dynamic instrumental space, not only lead gain;
   - doubles/adlibs/support vocals stay tucked unless explicitly authorized.

Release-review target:
The result may be considered `qc_passed_review_ready` only if:
1. Primary WAV exists and is nonzero.
2. WAV is the primary deliverable, MP3 is supporting only.
3. Sample rate, bit depth, channels, duration, clipping, and silence checks are recorded.
4. Loudness and true peak are measured, not guessed.
5. True peak is safe for streaming/distribution and MP3 encode safety is checked if MP3 is exported.
6. Integrated LUFS, short-term behavior, LRA, RMS/crest, stereo correlation, side/mid balance, spectral bands, and low-end stereo risk are documented.
7. Loudness-matched A/B preview exists against the previous/current mix.
8. User dissatisfaction feedback is resolved with evidence or final delivery remains blocked.
9. Final render evidence gate, final QC evidence gate, A/B preview evidence gate, rollback evidence gate, approval readiness, deliverable package evidence gate, final delivery consistency gate, and professional readiness audit pass when a final package is requested.

Do not treat "actual release registration ready" as a marketing claim. Treat it as a strict QC state:
- `review_copy`: useful for listening, not final.
- `qc_passed_review_ready`: measured QC passed, ready for user A/B approval.
- `delivery_ready`: QC, A/B, feedback resolution, human approval, package evidence, consistency, and professional readiness all passed.
- `blocked`: missing stems/reference, failed QC, unresolved feedback, plugin proof missing, or unsafe source condition.

Processing order:
1. Source intake:
   - identify stems, roles, sample rate, bit depth, duration, clipping, silence, alignment, phase, and obvious artifacts;
   - protect original stems and do not overwrite them.
2. Reference intake:
   - locate Estona/Podium reference audio if provided;
   - analyze LUFS, LRA, true peak, RMS/crest, stereo correlation, side/mid level, spectral bands, and low-end profile;
   - if no lawful reference file is available, use `digicore_hyperpop_hiphop_vocal_forward` or `clean_commercial_ai_repair` target-profile-only mode and do not claim reference matching.
3. Feedback registration:
   - record "전체 사운드 균일감/응집감 부족" using `scripts/run_feedback_revision_loop.py`;
   - record any additional user notes as separate feedback items.
4. Mix cohesion pass:
   - balance stems by role and section;
   - stabilize section loudness and energy;
   - carve vocal seat dynamically;
   - control low-mid mud and high-band glare;
   - align ambience depth so vocals, drums, bass, and music bed share one believable space.
5. Vocal-first pass:
   - lead vocal remains the anchor;
   - clear consonants and lyric intelligibility;
   - preserve vocal identity and emotion;
   - no sibilance spike, no 10 kHz+ fizz spike, no reverb/delay wash over consonants.
6. Low-end and groove pass:
   - add kick/bass body with controlled saturation or density where safe;
   - avoid broad low-end gain if mud or phase risk is present;
   - keep sub/low bass mono-compatible.
7. Width/depth pass:
   - clean side-channel harshness before widening;
   - keep lead vocal centered;
   - ensure mono fold-down remains acceptable.
8. Premaster safety:
   - check headroom, transient preservation, crest factor, LRA, phase, clipping, and low-end stereo risk;
   - if mix problems remain, return `mix_revision_required` instead of forcing the master.
9. Master/release pass:
   - apply final EQ/dynamics/limiting conservatively;
   - pursue loudness only after cohesion, vocal clarity, and true peak safety pass;
   - export WAV first, then MP3 preview if useful.
10. QC and evidence:
   - generate final QC metrics;
   - create loudness-matched A/B preview;
   - create decision notes;
   - run final render, final QC, A/B, rollback, approval readiness, deliverable, final consistency, and professional readiness gates as applicable.

Suno/AI vocal rescue gate:
If the stems include Suno/AI vocals, unclear main vocal, AI fizz, watery/robotic tone, or vocal artifact repair:
1. Verify the exact REAPER JSFX registry before final claims.
2. Required first-slot plugin on main vocal:
   - `JS: Codex Vocal AI Artifact Split Tamer`
   - file: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
3. The trace must prove it loaded at `fx_index: 0` on the lead/main vocal track.
4. Fallback plugins do not satisfy this gate.
5. Avoid strong pitch correction, heavy saturation, aggressive widening, Decapitator, Auto-Tune/ReaTune/MAutoPitch/Graillon on the main clean vocal unless the user explicitly re-authorizes after A/B.

Suggested commands to adapt:
1. Feedback:
   `python3 scripts/run_feedback_revision_loop.py --output-dir automix --project-name <project> --pass-id <vNN> --track-name "Full Mix" --feedback "전체 사운드가 균일하지 않고 응집감이 부족하다."`
2. Reference scan:
   `python3 scripts/run_reference_match_workflow.py --project <rpp> --current-mix <current_wav> --reference <estona_podium_reference_wav> --reference-role primary_reference --target-profile digicore_hyperpop_hiphop_vocal_forward --dry-run`
3. Final render evidence:
   `python3 scripts/run_final_render_evidence_gate.py --project-name <project> --output-dir automix`
4. Final QC evidence:
   `python3 scripts/run_final_qc_evidence_gate.py --project-name <project> --output-dir automix`
5. A/B evidence:
   `python3 scripts/run_ab_preview_evidence_gate.py --project-name <project> --output-dir automix`
6. Rollback evidence:
   `python3 scripts/run_rollback_evidence_gate.py --project-name <project> --output-dir automix`
7. Approval readiness:
   `python3 scripts/run_approval_export_readiness.py --project-name <project> --output-dir automix`
8. Deliverable package:
   `python3 scripts/run_deliverable_package_evidence_gate.py --project-name <project> --output-dir automix`
9. Final delivery consistency:
   `python3 scripts/run_final_delivery_consistency_gate.py --project-name <project> --output-dir automix`
10. Professional readiness:
   `python3 scripts/run_professional_readiness_audit.py --project-name <project> --output-dir automix --final-delivery-requested`

Stop rules:
1. If stems are missing, misaligned, clipped beyond repair, or source ownership is unclear, stop and report blockers.
2. If Estona/Podium reference audio is not available, proceed only as target-profile-informed and do not claim reference matching.
3. If overall cohesion is still poor at equal loudness, do not solve it by harder limiting.
4. If loudness makes the mix harsher, flatter, more phasey, less emotional, or more AI-like, revert the master move and mark `mix_revision_required`.
5. If QC fails, output a review copy or blocked report, not a safe final.
6. If user feedback remains unresolved, final delivery is blocked.

Expected deliverables:
- `renders/<slug>/<slug>_FINAL_REVIEW.wav` or project-standard primary WAV name.
- `renders/<slug>/<slug>_FINAL_REVIEW_320k.mp3` if MP3 export is useful.
- `renders/<slug>/<slug>_AB_loudness_matched.mp3` or WAV.
- `renders/<slug>/<slug>_REAPERPRINT_24-48.wav` or equivalent.
- `reports/<slug>/qc_metrics.json`
- `reports/<slug>/qc_metrics.csv`
- `reports/<slug>/reference_comparison.md`
- `reports/<slug>/decision_notes.md`
- `reports/<slug>/actual_reaper_plugin_trace.json` if plugin trace is relevant.
- Final ZIP only if all delivery gates pass.

Final response format:
1. Version slug:
2. Status: `review_copy` / `qc_passed_review_ready` / `delivery_ready` / `blocked`
3. Targeted complaint:
   - 전체 사운드 균일감/응집감 부족
4. Estona/Podium traits applied:
   - controlled low-end density;
   - wider but mono-safe music bed;
   - reduced synthetic top glare;
   - embedded melody clarity;
   - true-peak-safe loudness.
5. What changed:
6. What was intentionally left alone:
7. Deliverable paths:
8. QC headline:
   - integrated LUFS;
   - true peak;
   - sample rate/bit depth;
   - clipping/silence;
   - phase/mono;
   - MP3 true peak if exported.
9. A/B preview path:
10. Remaining risks/blockers:

Use cautious language. Do not claim "perfect", "fully release-ready", "commercially finished", or "reference matched" unless measured evidence and user approval support those exact claims.
```
