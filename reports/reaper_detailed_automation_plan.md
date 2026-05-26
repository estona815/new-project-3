# Detailed REAPER Automation Plan

이 계획은 현재 자료만으로 가능한 자동화 설계입니다. 현재 mix/stem이 없으므로 구체적인 dB cut/boost는 아직 target range 형태입니다.

## Status
- `template_no_current_mix`
- No Antares.
- Paid tools not required.
- Reference audio is not mixed into premaster.

## Chain Templates
### vocal_chain_when_stem_exists
- ReaEQ: HPF 70-100 Hz, body 150-500 Hz shaping, remove resonances only after stem analysis
- ReaXcomp: dynamic 2-5 kHz presence and 5-8 kHz harshness control
- ReaComp: gentle leveling, avoid flattening consonants
- JSFX estona_Vocal_AntiAI_Harsh: anti-glare/de-ess proxy
- short room send: glue/dryness repair if vocal sounds detached
### instrumental_bus
- ReaEQ: 120-350 Hz mud control, preserve 40-120 Hz weight
- JSFX saturation/soft clip: restore harmonic body without broad gain pushing
- MonoSub Guard: 20-120 Hz side reduction
### mix_bus
- ReaXcomp: broad dynamic EQ on mud/presence/harsh/air bands
- Vocal_Beat_Glue JSFX: gentle glue only if stems/current comparison proves detachment
- DigiClip JSFX: soft clip before limiter for density
### master_chain
- ReaEQ: small broad correction from current-vs-reference band deltas
- ReaLimit: ceiling -1.0 dBFS, do not chase unsafe reference true peaks
- Python QC: measure WAV and MP3 after encode
### ai_high_end_repair
- ReaXcomp (5-8 kHz): dynamic harshness control
- ReaXcomp or de-ess JSFX (6.5-9 kHz): sibilance/hash control
- ReaEQ (8-20 kHz): avoid air boost until hash/fizz score is under control

## Missing For True Stem Analysis
- `00_AUDIO_INPUT/current_mix.wav`
- `00_AUDIO_INPUT/vocal_stem.wav`
- `00_AUDIO_INPUT/instrumental_stem.wav`

## Next Code Task
When current/stems exist, compute per-band deltas against `deep_reference_mix_analysis.json` and emit an exact `reaper_mix_recipe.json` with ReaEQ/ReaXcomp/JSFX values.
