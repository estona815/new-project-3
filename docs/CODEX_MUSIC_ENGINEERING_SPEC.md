# Codex Music Engineering Spec

This repository must behave like a cautious music worker. A render is not final just because a file exists. Claims such as rebeat, remix, tuned, mastered, DeAI, noise removed, or final require project evidence, render evidence, and QC evidence.

## Production Classifications

| Classification | Allowed source path | Required evidence | Claim boundary |
| --- | --- | --- | --- |
| `fullmix_rescue` | Original stereo/fullmix is the main source. | Before/after WAV QC, project or script notes showing EQ/dynamics/repair/mastering path, source file hash or manifest. | May say fullmix rescue or repair pass. Must not say rebeat, stem rebuild, or remix. |
| `stem_rebuild` | Real stems are imported and actively mixed. Fullmix may be muted/reference-only or low support if disclosed. | REAPER project with active stem tracks, source media refs, routing, render, and QC. | May say stem-assisted rebuild only when stems drive the result. |
| `true_rebeat` | Beat/music elements are placed or regenerated as MIDI/audio items. | BPM/grid evidence, drum/bass/music MIDI or audio items on timeline, separate bus or solo renders, RPP audit showing MIDI/items. | May say rebeat only when REAPER timeline evidence exists. |
| `mix_repair` | Existing stems or fullmix are corrected without changing the arrangement claim. | Project notes and before/after QC showing targeted fixes. | May say mix repair, not new mix unless stems were actively mixed. |
| `master_only` | Already mixed stereo print is processed on the master path. | Before/after QC, loudness/true-peak report, master chain notes. | May say master or mastering pass only if true peak, loudness, crest, stereo, and transient guards pass. |
| `vocal_repair` | Vocal stem or vocal-forward fullmix is repaired/tuned. | Vocal source, processing path, pitch/timing evidence when claimed, before/after vocal QC, human A/B where required. | May say vocal repair only for measured repair. May say tuning only with pitch/edit evidence. |
| `suno_artifact_reduction` | Suno/AI artifact cleanup is attempted. | Candidate set, raw reference, before/after metrics, brightness/transient/intelligibility guard, human A/B. | May say attempted DeAI/artifact reduction. May say noise removed only after WARN+ is clear and user listening accepts tradeoff. |

## Allowed Claim Rules

- `rebeat`: allowed only when the RPP contains actual reconstructed drum, bass, and music MIDI/audio items and the audit can show them.
- `mix`: allowed when multiple active sources are routed and balanced in the project. A fullmix-only chain is not a mix.
- `master`: allowed only with a rendered WAV, plausible duration, loudness or loudness-unavailable warning, peak/true-peak guard, crest, stereo, and transient checks.
- `DeAI`: allowed only when the custom or declared DeAI path is present, plugin availability is verified, and QC does not show unacceptable brightness, transient, stereo, or intelligibility loss.
- `vocal repair`: allowed when the vocal source, processing path, and before/after evidence exist. Tuning requires key/pitch contour plus edit/take/MIDI evidence.
- `final`: allowed only when all required reports exist and the maximum severity is PASS or INFO. Any WARN, FAIL, or BLOCKER downgrades the claim to not final.

## Forbidden Claims

- Do not call a fullmix rescue a rebeat, remix, stem rebuild, or new mix.
- Do not call reference matching real when only broad spectral similarity was checked.
- Do not call pitch correction complete without detected pitch/key, edit evidence, and before/after validation.
- Do not call DeAI/noise removal successful if brightness, punch, stereo width, or intelligibility is damaged beyond profile guards.
- Do not call a render mastered when true peak, clipping, duration, loudness, or report evidence is missing.
- Do not call any REAPER project valid if required tracks/items/routing cannot be audited.

## Objective Metric Targets

Default guards are conservative and may be tightened by `presets/mix_profiles/*.json`.

| Metric | Default target |
| --- | --- |
| Duration delta | `max(0.50 sec, 1 percent of source duration)` |
| Sample peak | Below `-0.05 dBFS` |
| Approx true peak | At or below `-1.0 dBFS` unless profile says otherwise |
| Integrated loudness | Must be measured with `pyloudnorm` or explicitly WARN as unavailable |
| Crest factor | Suspicious if profile target is missed or collapse is unexplained |
| Air/fizz brightness loss | WARN if more than `3.0 dB` lower than before |
| Transient proxy loss | WARN if more than `30 percent` lower than before |
| Side/mid ratio change | WARN if absolute change is more than `3.0 dB` |
| De-essing | Must define detection band, max gain reduction, target source, and brightness guard |
| Resonance control | Prefer narrow/dynamic attenuation. Broad EQ is not a resonance-control substitute |
| M/S EQ | Low sides controlled; mid vocal/kick/snare protected; side harshness reduced without width collapse |

## Required Report Language

Every final report must separate:

- What was actually done.
- What was attempted.
- What failed.
- What needs human listening.
- Which claims are allowed and which claims are downgraded.

Any WARN+ finding must include severity, affected file, failed assumption, evidence, exact next patch, exact rerun command, and whether human listening is required.

