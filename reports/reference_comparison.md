# Reference Comparison

- Reference use policy: technical direction only, no musical cloning.
- Current/problem source available: true
- Technical reference available: true

## current_problem

- Source: `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip`
- Classification: `problem_reference`
- Note: extracted from /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip
- Format: 48000 Hz, decoded_float32, codec `mp3`, 141.394 s
- LUFS-like proxy: -11.54 dB
- RMS movement: 4.32 dB
- Peak/oversampled proxy: -1.6 / -1.49 dBFS
- Stereo corr / side-mid: 0.878 / -11.83 dB
- Low-end concentration: -3.25 dB
- Harshness risk: -21.42 dB
- QC issue count: 7

## technical_reference

- Source: `/Users/hantaeheuk/Downloads/발매곡 완성본/동반자살 완성본/동반자살 WAV.wav`
- Classification: `technical_mix_reference`
- Note: direct audio
- Format: 48000 Hz, int32, codec `wav`, 185.706 s
- LUFS-like proxy: -10.09 dB
- RMS movement: 2.11 dB
- Peak/oversampled proxy: -0.1 / 1.06 dBFS
- Stereo corr / side-mid: 0.9376 / -14.92 dB
- Low-end concentration: -2.56 dB
- Harshness risk: -17.72 dB
- QC issue count: 11

## Action Translation

- Use the reference as a technical compass only. Do not copy melody, lyric, arrangement, chord movement, topline, artist identity, or musical content.
- Keep MP3/full-master files as problem_reference/reference_only. Production rebuild stays blocked unless WAV stems are present.
- M/S space: side energy is too strong or phasey. Reduce side low-mids and check mono compatibility.
- Lead vocal: build clarity around 3-5 kHz, de-ess only harsh syllables, and keep pitch correction before dynamic EQ.
- Reverb: use filtered plate/room sends with 20-35 ms predelay and ducking under the lead vocal.
- Delay: use tempo-synced throw automation at phrase ends, not constant messy delay under every line.
- Master bus: true peak ceiling -1.0 dBTP, do not chase reference loudness blindly, and avoid over-limiting if vocal stability suffers.
