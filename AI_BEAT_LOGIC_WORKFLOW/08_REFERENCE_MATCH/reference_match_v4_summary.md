# Reference Match V4 Summary

## V4 Result
- File: `/Users/hantaeheuk/Documents/New project 3/AI_BEAT_LOGIC_WORKFLOW/05_FINAL_WAV/plugg_reference_matched_v4_24bit_48k.wav`
- RMS: -13.56 dBFS.
- LUFS-like proxy: -16.75 dB.
- Crest: 12.53 dB.
- Side/mid: -10.27 dB.
- Peak: -1.04 dBFS.
- Oversampled peak proxy: -1.0 dBFS.
- Clipping count: 0.
- Format: 48 kHz, 24-bit, stereo PCM WAV.

## Changes From V3
- Added vocal-triggered dynamic EQ for beat presence and low-mid ducking.
- Added JSON-compatible dynamic EQ reports with per-band gain reduction and masking before/after.
- Added harshness-triggered vocal dynamic EQ before restoring air.
- Replaced the harsher synthetic hard-tune color note with level-aware tune gloss and formant-ish low-mid protection.
- Added mid/side EQ, multiband compression, a density bus, and a softer limiter gain stage.
- Reworked sample chops into call-response motifs instead of purely repeated/random chop placements.
- Added QC metrics for spectral deltas, mono compatibility, and vocal/beat masking.
- Refactored the render chain to use reusable Python/NumPy/SciPy modules for dynamic EQ, vocal tone, sample arrangement, masking analysis, and master bus processing.
- Added sqrt(2) mid/side encode-decode, side low-cut safety, conservative upper-side width, and mono fold-down metrics.
- Added native pitch-correction approximation with voiced-frame F0 analysis, note/scale snap, tuned support layer blending, and explicit no-plugin limitations.
- Added Schroeder-style reverb and ducked delay sends with role-based wet amounts for lead, doubles, and adlibs.
- Added improved native saturation, seven-band multiband glue/density, true-peak-proxy limiting, and expanded master metrics.
- Added tone-aware median reference matching with capped corrections, harshness/sibilance protection, clipping safety rejection, and a standalone JSON report.
- Replaced dense sample sprinkling with candidate-scored motif roles, fewer placements, a section plan, and selected-sample JSON outputs.
- Refactored the renderer into explicit beat, sample, lead, double, adlib, FX, music, vocal, premaster, and master buses with metrics JSON output.

## Reference Texture Check
- Reference RMS target range is no longer chased at the expense of tone; this v4 master is quieter but keeps the limiter safer and preserves more crest.
- Reference side/mid target range remains -13.6 to -7.95 dB; v4 lands inside it.
- Bite band is intentionally under the reference average by about 3 dB to avoid cheap harshness after dynamic vocal control.
- Air is also intentionally lower than the reference average after the safer master bus; manual taste checking can decide whether to add more top after playback.
- Sub band remains stronger than the reference average; release use should check small speakers and car playback before final sign-off.
- The tone-aware matcher applied only broad tonal moves and refused bite/air boosts that would have chased harshness rather than musical clarity.
- Sample placement count is now 57 intentional motif placements rather than a busier repeated-chop grid.

## Honesty Notes
- This is a broad texture match, not an exact ycs, SYSTEM SEOUL, Nate Sib, or reference-song clone.
- True Antares Auto-Tune processing was not applied in this Python render; Logic/AU manual processing is still required for verified Antares use.
- The local sample source remains a rights-clearance issue for release use.
