# mesi_1_v11 Processing Plan

## Actual Planned Classification

`fullmix_rescue + Suno_DeAI_repair + master processing`, with a separate `drum_reinforcement` candidate only if QC permits.

## Allowed

- Decode MP3 to working WAV.
- Use fullmix EQ/dynamic EQ/M/S side wash control and conservative DeAI-style artifact reduction.
- Use subtle drum reinforcement if grid/event confidence supports it.
- Render multiple candidates and select by QC, not loudness.

## Forbidden

- No `true_rebeat`; no bass/music MIDI reconstruction exists.
- No `stem rebuild`; discovered stems are reference context, not active source for v11.
- No `vocal tuned`; no isolated vocal/pitch edit evidence is used.
- No `lossless restoration`; source is MP3.

## Tempo/Event Evidence

- Selected BPM: `129.496`
- Grid confidence: `FAIL`
- Event counts: `{"bass": 122, "hat_perc": 1, "kick": 118, "percussion": 0, "snare_clap": 97}`
