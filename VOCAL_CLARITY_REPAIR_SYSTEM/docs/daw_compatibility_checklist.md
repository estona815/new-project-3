# DAW And Plugin Format Compatibility Checklist

Current validated format in this repository: REAPER JSFX.

Do not claim compatibility with VST3, AU, AAX, standalone, Logic, Ableton, FL Studio, Studio One, Cubase/Nuendo, or Pro Tools until that format/host has been built, scanned, opened, automated, rendered, saved, reopened, and documented.

## Host Matrix

| Host | Format | Scan | UI opens | Audio passes | Bypass dry | Presets load | Automation | Offline render | Save/reopen | Freeze/bounce | Latency | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REAPER | JSFX | pending manual scan | pending | pending real render | pending | pending | pending | pending | pending | pending | no declared latency | installed file validated only |
| Logic Pro | AU | not built | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | unsupported/unclaimed |
| Ableton Live | VST3/AU | not built | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | unsupported/unclaimed |
| FL Studio | VST3 | not built | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | unsupported/unclaimed |
| Studio One | VST3/AU | not built | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | unsupported/unclaimed |
| Cubase/Nuendo | VST3 | not built | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | unsupported/unclaimed |
| Pro Tools | AAX | not built | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | not tested | unsupported/unclaimed |

## REAPER JSFX Manual Pass

For the actual RC, verify:

- REAPER scans the JSFX folder.
- Plugin appears as `JS: Codex Vocal AI Artifact Split Tamer`.
- UI sliders show Preserve defaults.
- Audio passes in mono and stereo.
- Bypass returns dry.
- `Processing Enabled` off returns dry.
- Dry/Wet 0 returns dry.
- Residual Monitor Off/Processed/Residual routes correctly.
- M/S enabled and disabled are safe.
- Preserve, Balanced, Surgical, Hiss, Voiceover, DSP Only Safe, Side Noise Cleanup, Artifact Focus Low Denoise, and Strong Test settings can be recalled.
- Strong is not used as the default.
- Offline render works at 44.1 kHz, 48 kHz, and 96 kHz if supported by the session.
- Project save/reopen restores slider values safely.
- Duplicate track, freeze/bounce, close, and reopen do not crash.

## Plugin Format Validation

For any future VST3/AU/AAX build, verify:

- build artifact exists
- plugin scans in validator and host
- product name/vendor/version are correct
- bus layout is correct
- parameter list and order are stable
- factory presets are packaged
- model/resources are included if required
- release build has no debug logging from audio thread
- signing/notarization is completed where required
- installer contains no absolute local paths

Formats not listed as validated must remain unclaimed in release notes.
