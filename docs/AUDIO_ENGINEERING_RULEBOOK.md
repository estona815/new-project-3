# Audio Engineering Rulebook

This rulebook is the repo-local contract for automated REAPER mix, repair, Suno DeAI, vocal rescue, and mastering work. It does not claim that automation can hear like a person. It defines what automation may attempt, what it must measure, and what it must refuse to claim without evidence.

## Classification Gate

Every run must classify the work before processing:

- `fullmix_rescue`: the stereo mix is the main source. Use EQ, dynamic EQ, M/S repair, DeAI, compression, limiting, and conservative vocal-focused fullmix processing. Do not claim stem rebuild, true rebeat, or vocal tuning.
- `stem-assisted rebuild`: stems exist, are imported, and are active in the REAPER project. Report the stem roles, active stem tracks, and stem render or audit evidence.
- `true_rebeat`: drums, bass, and music elements are reconstructed as MIDI/audio items on the REAPER timeline. Report MIDI/audio item counts, `rebuild_roles` for drums/bass/music, grid/BPM evidence, and separate bus render or audit evidence. Stems alone do not prove true rebeat.
- `drum_reinforcement`: kick, snare, hat, or percussion support is detected and placed. This is not true rebeat.
- `vocal_repair`: vocal-targeted repair from an isolated vocal or a clearly labeled fullmix-derived vocal path. Pitch correction requires pitch contour, edit evidence, and validation.
- `master_only`: final-bus processing only. Do not claim mix reconstruction.

## Allowed Language

Use exact, bounded phrases:

- `fullmix rescue`
- `stem-assisted rebuild`
- `drum reinforcement`
- `master bus processing`
- `fullmix-derived vocal-focused processing`
- `lossy-source processed print`
- `M/S side wash control`
- `dynamic resonance control`
- `candidate requires human listening`

## Forbidden Claims Without Evidence

- `true rebeat`: only allowed with auditable drum, bass, and music reconstruction items in REAPER.
- `beat fully re-created`: only allowed with placed reconstruction items and separate bus evidence.
- `vocal fully tuned`: only allowed with pitch contour, edit/take evidence, and before/after validation.
- `stem mix`: only allowed with active stem tracks and stem audit evidence.
- `lossless restoration`: forbidden for MP3 or other lossy sources.
- `noise completely removed`: forbidden. Report reduction and remaining risk instead.
- `professional final master`: requires passing QC plus human listening approval.
- `reference matched perfectly`: forbidden. Reference matching is advisory.

## Objective Guards

Defaults live in `presets/engineering_rules/default_engineering_rules.json` and may be tightened by genre profile.

- Brightness loss: WARN if 10-16 kHz air/fizz drops more than 1.0 dB without clear artifact benefit; FAIL candidate at 2.5 dB when clarity worsens.
- Transient preservation: WARN below 95 percent of the before transient proxy; FAIL below 90 percent unless an explicit repair note justifies it.
- Side/mid stability: WARN beyond 1.5 dB side/mid change; FAIL beyond 3.0 dB or when width collapses.
- Punch preservation: WARN if 45-140 Hz punch proxy drops more than 0.75 dB; FAIL at 1.5 dB, with tighter DnB limits.
- Loudness safety: true peak should usually be at or below -1.0 dBTP. Clipping is never a loudness strategy.
- Duration: output duration must match source unless an edit or stretch is documented.

## Processing Report Requirement

Every processing report must say:

- what was actually done
- what was attempted
- what failed
- what was bypassed or unavailable
- what plugins were verified or missing
- what claims are allowed and forbidden
- whether human listening is required

If any rule checker result is WARN, FAIL, or BLOCKER, the report must not claim final success.
