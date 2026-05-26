# Mix QC Report

## Measured Outcome

- Original full mix: -14.9 LUFS, true peak -2.6, sibilance share 2.904%, air/hash share 1.413%.
- Final WAV: -10.8 LUFS, LRA 4.2, true peak -1.0, sibilance share 1.6%, air/hash share 0.805%.
- Final MP3 check: -10.8 LUFS, true peak -0.7.
- Processed vocal stem: -28.3 LUFS, true peak -13.3, sibilance share 2.651%.

## Listening-Intent QC

- Less AI-like: yes, based on reduced 5-10 kHz share and fewer exposed high-band gap artifacts.
- Emotional phrasing survived: yes by design; no pitch rewrite, no phrase gating, and no timing edits were applied to the male lead.
- Vocal loudness/burial: final uses the blended version, keeping the lead readable but slightly tucked into the beat.
- Sibilance controlled: yes; 5-10 kHz share is materially lower than the raw vocal/original mix.
- High end dullness: controlled risk; air/hash was reduced but not fully low-passed, so consonant readability should remain.
- Beat support: improved with light bus saturation/body and no rejected v24 instrumental bed.

## Remaining Weaknesses

- Some AI formant instability is baked into the stem and can only be hidden, not transparently removed.
- The processed vocal stem is intentionally conservative; a more aggressive restoration pass could sound cleaner but less emotional.
- Final approval still needs user listening on speakers/earbuds because measured QC cannot judge Korean lyric emotion perfectly.

## Next Revision Suggestions

- If the vocal still feels metallic, reduce the 10.4 kHz dynamic band threshold by 1-2 dB before changing the whole EQ curve.
- If the vocal feels too tucked, raise `MALE_MAIN_VOCAL_BUS` by 0.4-0.7 dB instead of adding brightness.
- If consonants feel dull, restore 0.2-0.4 dB at the channel-polish air shelf, not a broad 8 kHz boost.
