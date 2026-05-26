# Plugg Digicore Mix QC

## Status
- final master verification ok: true
- final master: /Users/hantaeheuk/Documents/New project 3/AI_BEAT_LOGIC_WORKFLOW/05_FINAL_WAV/plugg_reference_matched_v4_24bit_48k.wav
- pre-master: /Users/hantaeheuk/Documents/New project 3/AI_BEAT_LOGIC_WORKFLOW/09_MIX_MASTER/plugg_reference_matched_v4_pre_master.wav
- AAC preview: /Users/hantaeheuk/Documents/New project 3/AI_BEAT_LOGIC_WORKFLOW/05_FINAL_WAV/plugg_reference_matched_v4_preview.m4a
- metrics JSON: /Users/hantaeheuk/Documents/New project 3/AI_BEAT_LOGIC_WORKFLOW/06_QC_REPORT/plugg_reference_matched_v4_metrics.json
- duration: 95.93s
- sample rate: 48000
- bit depth: 24
- peak: -1.04 dBFS
- rms: -13.56 dBFS
- clipping count: 0

## Extended Metrics
- crest: 12.53 dB
- side/mid: -10.27 dB
- one-second RMS p10/p50/p90: [-24.02, -12.92, -11.62]
- mono level delta: -0.39 dB
- L/R correlation: 0.8283
- M/S low side-mid below 150 Hz: -27.19 dB
- mono fold peak/RMS change: -0.03 / -0.39 dB
- masking score low-mid/mid/presence: 6.03, -1.59, 0.89 dB

## Spectral Delta vs Reference Average
- sub_20_60: +1.41 dB
- bass_60_150: -0.28 dB
- low_mid_150_400: -1.32 dB
- mid_400_1500: -0.68 dB
- presence_1500_4500: -2.73 dB
- bite_4500_8000: -3.32 dB
- air_8000_16000: -3.72 dB

## Mix Moves
- original beat was section-arranged with intro filtering, hooks, bridge drop, and outro tail
- v4 keeps the broad reference texture target but avoids exact artist or song cloning
- vocal-triggered dynamic EQ ducks beat presence and low-mid bands only when the vocal needs space
- harshness-triggered dynamic EQ catches vocal bite spikes before air is restored
- mid/side EQ keeps low-end center stable while widening upper texture
- multiband compression and density bus replace the flatter static EQ/clip-only master feel
- lead and doubles were made vocal-forward with smoother tune gloss and less comb-like hard-tune color
- doubles aligned against the lead using envelope cross-correlation when confidence was usable
- sample chops were reworked into call-response motifs so the hook has its own identity
- master tonal match controls sub-only weight while preserving bass, bite, and air bands
- tone-aware reference matcher applies capped broad-band correction and rejects harshness/clipping regressions
- master bus now uses low cleanup, seven-band glue/density, subtle native saturation, M/S safety, and an oversampled lookahead limiter
- reference analysis: /Users/hantaeheuk/Documents/New project 3/AI_BEAT_LOGIC_WORKFLOW/08_REFERENCE_MATCH/reference_texture_analysis.json

## Bus Architecture
- buses: beat_bus, sample_bus, lead_vocal_bus, double_vocal_bus, adlib_or_girl_double_bus, vocal_fx_return, delay_return, music_bus, vocal_bus, premaster_bus, master_bus
- order: ingest/convert/resample -> align vocals and beat -> gain staging -> sample arrangement -> lead vocal rider -> native pitch-correction approximation / tuned support layer -> vocal tone chain -> doubles/adlibs tone + width -> reverb/delay sends -> beat dynamic EQ ducked by vocal -> sample/synth width -> music bus saturation/glue -> vocal bus compression/de-ess -> premaster balance -> reference tone matching, gentle -> master bus -> final 24-bit 48k WAV export -> verification -> QC report

## Actually Applied
- native Python/NumPy/SciPy vocal tone chain
- vocal-triggered beat dynamic EQ
- sample arrangement section plan
- bus-level vocal de-ess/compression
- music bus saturation/glue
- tone-aware reference correction
- oversampled limiter and final WAV verification

## Approximated / Not Applied
- approximated: native pitch-correction approximation / tuned support layer
- approximated: LUFS-like loudness proxy
- approximated: true-peak proxy via oversampling
- Antares applied: false

## Dynamic EQ / De-Ess / Pitch Stats
- beat ducking bands: 3
- beat ducking gain reductions: [(200.0, 400.0, -1.32, -2.3), (1000.0, 4000.0, -2.48, -3.2), (6000.0, 10000.0, -1.09, -1.6)]
- sample pocket max gain reduction: -2.4 dB
- vocal bus de-ess sibilance delta: -0.59 dB
- track de-ess reports: 5
- pitch approximation reports: 5

## Reference Matching
- correction amounts: [{'band': 'sub_20_60', 'low_hz': 20.0, 'high_hz': 60.0, 'gain_db': -0.88}, {'band': 'bass_60_150', 'low_hz': 60.0, 'high_hz': 150.0, 'gain_db': 0.14}, {'band': 'low_mid_150_400', 'low_hz': 150.0, 'high_hz': 400.0, 'gain_db': 1.35}, {'band': 'mid_400_1500', 'low_hz': 400.0, 'high_hz': 1500.0, 'gain_db': 0.38}, {'band': 'presence_1500_4500', 'low_hz': 1500.0, 'high_hz': 4500.0, 'gain_db': 1.5}]
- warnings: ['ignored bite_4500_8000 boost to avoid harsher/sibilant top-end chasing', 'ignored air_8000_16000 boost to avoid harsher/sibilant top-end chasing', 'width differences reported only; no fake widening applied by reference matcher']

## Arrangement
- 0-4 bars: intro filtered low, sample leads, beat gain -13 dB
- 4-12 bars: hook with light gated beat under sample melody, beat gain -7.8 dB
- 12-20 bars: verse pocket, vocal center stays clear, beat gain -8.9 dB
- 20-24 bars: pre-bridge filtered break, beat gain -12 dB
- 24-28 bars: sample bridge, original beat heavily reduced, beat gain -18 dB
- 28-36 bars: second hook with wider top, beat gain -7.9 dB
- 36-44 bars: sample-forward final hook, beat gain -8.2 dB
- 44-999 bars: outro tail, beat gain -11 dB

## Vocal Stem Balancing
- main2_1.wav: gain 2.5 dB, pan 0.0, shift 0.0 ms, align score 0.0, tune-gloss blend 0.16
- main 1_1.wav: gain -1.8 dB, pan 0.04, shift 0.0 ms, align score -0.2568, tune-gloss blend 0.1
- doub_1.wav: gain -6.4 dB, pan -0.28, shift 0.0 ms, align score 0.247, tune-gloss blend 0.0
- doub1 girl_1.wav: gain -8.8 dB, pan 0.52, shift 0.0 ms, align score 0.0432, tune-gloss blend 0.0
- doub2 girl_1.wav: gain -9.0 dB, pan -0.5, shift 10.0 ms, align score 0.309, tune-gloss blend 0.0

## Sample Motif
- source: /Users/hantaeheuk/Desktop/음악샘플/15_U.N.Owen_source.mp3
- decoded: true
- chops used: 6
- motif placements: 57

## Limits / Honesty Notes
- true pitch correction applied: false
- hard-tune style layer applied: false
- tune gloss layer applied: true
- pitch note: No verified Auto-Tune plugin or note-by-note pitch editor is available here; this render uses a native pitch-correction approximation as a low-blend tuned support layer, level-aware tune gloss, harshness control, formant-ish low-mid protection, doubled width, and timing alignment without claiming true pitch correction.
- rights note: Local sample file was used for a demo render; release use still needs sample/license clearance.
- limitation: Antares/Auto-Tune was not applied because no verified command-line plugin processing is available
- limitation: source beat is a stereo mix, so beat processing is bus-level rather than stem-level
- limitation: local sample source still requires rights clearance for release use
- limitation: native pitch correction is an approximation, not professional note-by-note tuning
- exact System Seoul/Nate Sib/artist clone claimed: false

## Verification Errors
- none
