# Antares / Logic Vocal Settings

## Plugin Availability
- Local Antares AU components were found under `/Library/Audio/Plug-Ins/Components`.
- This Python render does not host AU plugins directly, so the WAV render does not claim verified Antares processing.
- `auval` component IDs found:
  - Auto-Tune Pro: `aumf / AT81 / VST `
  - AutoTune Core: `aufx / Core / Antr`
  - Auto-Tune EFX+: `aufx / Vefx / Antr`
- Validation note: the components are registered, but command-line opening failed at `OpenAComponent` in this environment. Logic Pro may still be able to scan/use them if licensing and AU validation are OK inside Logic, but this render cannot truthfully claim Antares was applied.

## Suggested Logic Chain For The Lead
- Auto-Tune Pro or AutoTune: Retune Speed 0-5, Humanize 0-8, Flex-Tune 0, Natural Vibrato near 0, Formant on if available.
- Auto-Tune Vocal EQ: high-pass around 90-120 Hz, small low-mid cleanup around 180-350 Hz, presence lift around 2-4 kHz only if not harsh, air lift around 8-12 kHz.
- Auto-Tune Vocal Compressor or Logic compressor: fast-ish attack, medium release, 3-6 dB gain reduction, then clip gain automation for syllables that disappear.
- De-esser after tuning if the air lift makes consonants sharp.
- Sends: short bright room very low, tempo delay throws only on phrase endings.

## Suggested Doubles
- Keep doubles lower than the lead and wider.
- Tune doubles slightly less aggressively than the lead unless the hook needs a robotic stack.
- High-pass doubles higher than the lead so they do not cloud the center.
