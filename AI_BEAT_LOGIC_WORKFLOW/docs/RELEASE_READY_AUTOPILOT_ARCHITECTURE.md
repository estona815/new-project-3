# Release-Ready Autopilot Architecture

## Purpose

The release-ready autopilot turns a rough Korean or English production request plus local audio inputs into an auditable local production workflow:

1. intent parsing
2. composition idea generation
3. sample, vocal, song, and stem analysis
4. arrangement plan
5. MIDI, region, and automation guide
6. Logic Pro manual production plan
7. mix/master plan
8. optional demo or fallback render
9. verified final WAV export
10. release package generation
11. release QC
12. completion gate

This is a local AI Producer Brain, not a distribution service and not a guarantee of commercial success. Release-ready means verified local audio deliverables, metadata/checklist files, safety notes, QC reports, and clear remaining limitations.

## Supported Workflows

### `song_to_mix_master`

Input:
- full stereo song
- Suno-style stereo render
- Logic export
- vocal song stereo file
- stems when supplied

Output:
- rough request interpretation
- song structure analysis
- arrangement and hook plan
- Logic manual production plan
- source-aware mix/master plan
- optional fallback/demo render
- verified final WAV when export succeeds
- release package and release QC when final verification passes

### `sample_to_arrangement`

Input:
- local user-provided sample, loop, melody, phrase, or motif
- optional vocal guide
- rough request

Output:
- sample MIR analysis
- ownership/safety policy
- chord, melody, bass/808, drum, section, and sample-chop guides
- MIDI/region/automation guide
- Logic manual arrangement plan

This workflow is plan-first. It must not claim final audio completion unless it later passes the final render/export path.

### `vocal_to_code`

Input:
- local vocal file
- optional rough vocal FX request

Output:
- phrase regions
- rough pitch contour
- rhythm grid cues
- tuning guide
- vocal mix chain guidance
- Logic pitch correction checklist

It must not claim perfect transcription, AutoTune application, Flex Pitch edits, or plugin insertion unless those actions are actually performed and verified.

### `stems_to_production`

Input:
- local stem folder or explicit stem files
- rough production request

Output:
- stem-aware arrangement plan
- direct balance and routing guidance for provided stems
- vocal/beat blend plan
- mix/master plan
- Logic manual package

Stem mode has more direct control than stereo-only mode, but it is limited to the stems actually supplied.

## Status Model

Statuses must distinguish production planning from final delivery:

- `PLAN_ONLY`: text/JSON plans exist, no audio export claim.
- `INTENT_READY`: rough request has been parsed and safety policy is available.
- `ANALYSIS_READY`: local audio analysis exists.
- `ARRANGEMENT_PLAN_READY`: arrangement and guide files exist.
- `MIDI_GUIDE_READY`: MIDI/region guide files exist, but no Logic import is claimed.
- `LOGIC_MANUAL_REQUIRED`: Logic production steps are documented for human execution.
- `DEMO_RENDER_EXPORTED`: a fallback or preview render exists, not a final master.
- `FINAL_WAV_EXPORTED_UNVERIFIED`: final WAV exists but verification is incomplete or failed.
- `FINAL_WAV_EXPORTED_VERIFIED`: final WAV format and audio metrics passed.
- `RELEASE_PACKAGE_READY`: final WAV, reports, metadata, checklist, safety notes, and release QC exist.
- `COMPLETE`: only printed by `src/main.py` after `src/completion_gate.py` passes all required checks.

## Plan-Only vs Final WAV

Plan-only outputs may include:
- production intent JSON/Markdown
- creative brief
- arrangement plan
- MIDI/region guide
- Logic manual plan
- mix/master plan
- QC of plan readiness

Plan-only outputs are useful milestones, but they are not final audio. They must not print `COMPLETE`.

Final WAV means:
- audio file exists
- file is non-empty
- requested sample rate is verified
- requested 24-bit PCM format is verified
- duration, peak, RMS, and clipping metrics are read
- QC report exists
- required master QC exists
- completion gate passes

## Demo Render vs Final Master

A demo render may be:
- fallback stereo processing
- rough preview
- short-form audition export
- guide render for listening decisions

A demo render may support review but must not be treated as a final master unless it goes through final export verification and QC.

A final master must:
- use the requested export format
- pass final WAV verification
- pass master QC
- avoid clipping
- preserve honest source-type language
- be referenced in the release package

## Final Master vs Release Package

A final master is the verified WAV.

A release package is the verified WAV plus:
- release metadata sheet
- rights/safety checklist
- release QC report
- commercial readiness report
- audio render manifest
- safety notes
- remaining limitations
- optional alternate deliverables when available

The release package does not guarantee distribution approval, rights clearance, playlist placement, sales, charting, or commercial success.

## Stereo-Only Limitations

Stereo-only processing can support:
- broad EQ
- broad gain staging
- trims and fades
- conservative saturation
- broad stereo width
- heuristic section and texture analysis
- manual Logic layering suggestions
- mastering-style polish

Stereo-only processing must not claim:
- stem-level remixing
- guaranteed vocal removal
- true kick/bass replacement
- true drum rewrite
- true stem separation
- exact bassline editing
- verified plugin insertion
- Logic automation success

## Stem Mode Capabilities

Stem mode can provide more specific guidance:
- direct stem balance notes
- drum bus and 808/bass treatment
- vocal/adlib/backing chain plan
- melody/synth width and panning plan
- section mute/arrangement instructions
- cleaner mix/master staging

Even in stem mode, completion still requires actual rendered audio, verified final WAV, QC reports, release package files, and completion gate approval.

## Logic Manual Requirements

Logic Pro work remains manual unless automation produces verified artifacts.

Manual requirements include:
- creating markers
- importing or aligning stems
- writing regions
- inserting plugins
- setting automation
- checking mono compatibility
- bouncing final WAV
- listening and revising

Logic automation success must not be faked. A Logic project, export, or automation status is only successful if the expected artifact exists and passes the relevant status check.

## Plugin Limitations

Plugin references such as AutoTune, Flex Pitch, Decapitator, saturation, widening, and mastering tools are planning targets unless processing is actually applied and verified.

Detected plugins are availability hints only. The system must not claim:
- AutoTune was applied
- Decapitator was applied
- plugin automation succeeded
- plugin insertion happened in Logic

unless the pipeline has a verified processing artifact or verified Logic state.

## Exact-Copy And Voice-Clone Policy

Reference prompts are high-level production targets only.

The system must not copy:
- exact songs
- kick samples
- basslines
- melodies
- lyrics
- drum patterns
- sound recordings
- producer identity
- living artist vocal identity

Korean phrases such as `따와라`, `가져와라`, `똑같이`, and `그대로` are copying-risk signals. Exact use is blocked unless the user supplies a local owned/licensed/cleared sample or stem and confirms that use.

Artist vocal references may be translated to production traits such as brightness, tuning amount, compression, delay, saturation, and adlib space. They must not become living artist voice cloning.

## Completion Integrity

`COMPLETE` is allowed only when:
- final WAV verification passes
- QC report exists
- required master QC exists
- release package manifest exists and passes
- safety/false-claim checks do not block
- `src/completion_gate.py` returns complete
- `src/main.py` is the only place that prints the literal completion token

Any failure keeps the workflow in a clear non-complete status with blocking reasons.
