# Autopilot Architecture

## Purpose

AI_BEAT_LOGIC_WORKFLOW is a local AI Producer Brain for controllable music production planning, audio analysis, Logic Pro guidance, fallback processing, verified exports, and commercial QC.

It is not a Suno-style text-to-song model. It does not generate a complete song from a text prompt. It analyzes user-provided files and turns them into safe, auditable production plans and verified artifacts when rendering/export is actually performed.

## Workflow Modes

### 1. Song-to-Arrangement / Mix / Master

Input: full song, Suno track, stereo WAV/MP3, vocal song, Logic export, or stems.

Output:
- song structure analysis
- arrangement revision plan
- mix/master plan
- Logic manual production checklist
- optional fallback stereo processing
- verified final WAV only after export and completion gate checks

Stereo-only input remains heuristic. It cannot provide true stem-level control.

### 2. Sample-to-Arrangement / Progression

Input: user-provided sample, loop, melody, phrase, or motif.

Output:
- BPM estimate
- pitch/key center estimate
- loop and motif candidates
- transient/onset cues
- section progression
- drum programming guide
- 808/chord/synth guide
- Logic arrangement plan

Exact sample use requires a local owned/cleared source. Without that, sample requests become high-level production traits only.

### 3. Vocal-to-Code

Input: user-provided vocal file.

Output:
- phrase regions
- pitch contour estimates
- rough note candidates
- rhythm/phrase guide
- tuning guide
- vocal mix chain plan
- Logic pitch correction checklist

The system must not claim perfect transcription. It must not claim AutoTune, Flex Pitch, or plugin application unless the operation is actually performed and verified.

### 4. Stems-to-Production

Input: user-provided stems such as drums, 808, bass, melody, synth, lead vocal, adlibs, backing vocals, or master.

Output:
- more direct arrangement and mix plans
- stem-aware section mutes and balance notes
- vocal/beat blend plan
- master plan
- Logic production instructions

Stem-based capability is limited to the provided local files. The system must not claim stem separation unless a real stem separation stage is added and verified.

### 5. Stereo-Only Polish

Input: one stereo file.

Output:
- broad EQ/gain/fade/width/saturation/mastering polish
- heuristic vocal-region, low-end, melody, and arrangement warnings
- manual Logic plan

Not allowed:
- true kick/bass replacement
- true drum rewrite
- guaranteed vocal removal
- stem-level remixing
- exact plugin insertion claims

## Supported Inputs

- WAV, MP3, AIFF, FLAC, M4A source files
- local sample/loop WAVs
- local vocal files
- beat plus vocal pairs
- stems folders or explicitly supplied stem files
- reference audio supplied by the user
- Korean or English natural-language production requests
- text-only reference prompts

Web research, when used, may collect high-level public descriptors only. It must not download copyrighted web audio or scrape lyrics.

## Dependency Levels

### Level 0: Pure Planning

No external audio tools required.

Capabilities:
- parse request intent
- classify workflow mode
- build safety policy
- write plan-only JSON/Markdown
- generate Logic manual checklist

Status: plan-only, never final-WAV-complete.

### Level 1: Python WAV Analysis

Requires Python standard library and local project modules.

Capabilities:
- read WAV metadata
- estimate levels, clipping, RMS
- heuristic sections, vocal regions, sample motifs, and phrase cues
- create guide-only MIDI/region concepts

Status: analysis-backed plan, not a rendered final.

### Level 2: Optional CLI Audio Tools

May use tools such as ffmpeg, ffprobe, afconvert, rubberband, soundstretch, or sox when available.

Capabilities:
- conversion
- fallback stereo processing
- export format verification
- optional pitch/time tooling only when actually available

Status: rendered artifacts require verification before they can support completion.

### Level 3: Logic Pro Manual / Assisted Workflow

Requires macOS, Logic Pro, user permissions, and/or manual action.

Capabilities:
- project setup guidance
- import guidance
- region, mix, plugin, and automation checklists
- possible limited automation status reports

Status: Logic success is never assumed. A Logic project/export must exist and be verified before being claimed.

## Plan-Only vs Final-WAV-Complete

Plan-only means:
- JSON/Markdown plans may exist
- guide data may exist
- analysis may exist
- no final WAV completion is claimed
- no `COMPLETE` output is allowed

Final-WAV-complete means:
- final WAV exists
- final WAV is non-empty
- requested sample rate and 24-bit PCM format are verified
- duration, peak, RMS, and clipping metrics are verified
- `qc_report.md` exists
- required master QC report exists
- completion gate passes
- `src/main.py` prints `COMPLETE` only after `src/completion_gate.py` returns complete

## Stereo-Only Limitations

For one stereo file, all stem-like labels are heuristic. The system may suggest:
- broad EQ
- broad gain staging
- fades and trims
- broad stereo width
- conservative saturation
- mastering polish
- manual Logic layering

The system must not claim:
- stem separation
- isolated vocal control
- real vocal removal
- true kick or 808 replacement
- true drum rewrite
- exact bassline editing
- verified plugin insertion

## Stem-Based Capabilities

With stems, the system can be more specific:
- direct drum balance notes
- 808/bass tuning and mono-sub plan
- synth width and panning plan
- lead vocal/adlib/backing vocal chain plan
- section mute and arrangement suggestions
- mix/master staging

Even with stems, rendered success requires actual processing/export and verification. Manual Logic decisions still require listening.

## Safety / Copyright Policy

Reference prompts become high-level production targets only.

Never copy:
- exact songs
- kick samples
- basslines
- melodies
- lyrics
- drum patterns
- sound recordings
- producer identity
- living artist vocal identity

Korean phrases such as `따와라`, `가져와라`, `똑같이`, and `그대로` are copying-risk signals. Exact use is blocked unless the user provides a local owned/licensed/cleared sample or stem and confirms ownership.

Text-only references are low-confidence. The system must not infer exact sonic details from a title alone.

Commercial quality means technical readiness, arrangement control, mix clarity, and QC discipline. It does not mean guaranteed commercial success or chart success.

## Logic Automation Limits

Logic Pro automation may help with setup, opening Logic, locating files, or writing status. It must not pretend to:
- save a project unless the `.logicx` exists
- insert plugins unless verified
- apply EQ curves unless verified
- tune vocals unless verified
- perform region edits unless verified
- export audio unless the export file exists and passes verification

If automation is unavailable, failed, or partial, the workflow must write manual instructions instead.

## QC / Completion Gate Rules

QC must be honest about what happened:
- fallback means stereo-only fallback
- Logic export means a verified Logic source was used
- final mix/master means the master stage output was used

Completion is centralized:
- `src/completion_gate.py` checks final readiness
- `src/main.py` is the only place that may print `COMPLETE`
- failing verification must return a non-complete state and list blocking reasons

Generated WAV/log/report/MIDI artifacts must not be committed unless intentionally added as fixtures.
