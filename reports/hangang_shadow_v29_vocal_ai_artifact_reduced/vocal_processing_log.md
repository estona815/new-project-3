# Vocal Processing Log

## Final Chosen Chain

- Track: `vocal_processed - male lead 12 Vocals`.
- ReaEQ marker: inserted for stock corrective EQ documentation; broad correction is handled by the configured JS channel polish to avoid unsafe binary parameter guessing.
- ReaComp marker: inserted for stock compression documentation; active compression settings are in `JS: Codex V20 Channel Polish`.
- `JS: Codex V20 Channel Polish`: HPF 90 Hz, mud cut around 285 Hz, slight 3.15 kHz softening, -0.42 dB air shelf around 9.8 kHz, 1.65:1 gentle compression, 18 ms attack, 142 ms release, 1.15 dB drive at 7% mix.
- `JS: Codex Noise Floor Tamer`: high split 7.9 kHz, threshold -51 dB, max high attenuation 1.55 dB, 12 ms attack, 245 ms release, 62% mix. Used instead of hard gating active phrases.
- Dynamic bands: 315 Hz low-mid buildup, 950 Hz plastic/nasal tone, 3.55 kHz harsh attack, 6.8 kHz sandy sibilance, 10.4 kHz digital fizz.
- `JS: Codex Presence Tilt`: 2.6 kHz focus with slight negative presence and 44% blend to avoid underwater dullness.
- Parallel density track: `VOCAL NATURAL DENSITY PARALLEL - no tune`, -24 dB blended, no pitch correction, darkened above 8.2 kHz, 12% saturation mix.
- Ambience support: `VOCAL SHORT ROOM SLAP - dark blend`, 46 ms delayed duplicate, -31 dB in the blended version, HPF 170 Hz, dark air shelf around 7.2 kHz, high-fizz guard. It is muted for the light version and lower in the medium version.
- Vocal bus: extra 4.3 kHz and 9.3 kHz dynamic control, very light compression/saturation.
- Music bus: mild saturation/body, vocal-space dynamic control around 2.3 kHz, high-tail tamer above 8.6 kHz.
- Master print: light glue and clip catch only, then REAPER batch normalize/brickwall for the delivery WAV and level-matched comparison WAVs.

## Bypassed Or Rejected Experiments

- Antares/Auto-Tune: not used.
- ReaTune/heavy pitch correction: not used in v29 because it made the vocal feel less human for this task.
- Hard ReaGate during phrases: rejected; the safer move was high-band noise taming in low-level gaps only.
- Strong ReaFIR subtract profile: rejected as a default because it risked watery/phasey vowel damage.
- Female-double lead support: muted/reference-only; the final target is natural male lead.
- Long or bright reverb returns: rejected because they exaggerated AI fizz above 8 kHz.
- v24-style instrumental bed glue: not used.

## Rendered Versions

- Light: `renders/hangang_shadow_v29_vocal_ai_artifact_reduced/vocal_cleanup_light.wav` (-11.1 LUFS, TP -1.0).
- Medium: `renders/hangang_shadow_v29_vocal_ai_artifact_reduced/vocal_cleanup_medium.wav` (-11.0 LUFS, TP -1.0).
- Blended: `renders/hangang_shadow_v29_vocal_ai_artifact_reduced/vocal_cleanup_blended.wav` (-11.1 LUFS, TP -1.0).
- Final chosen: blended balance, rendered to `renders/hangang_shadow_v29_vocal_ai_artifact_reduced/final_mix_vocal_ai_artifact_reduced.wav` and `renders/hangang_shadow_v29_vocal_ai_artifact_reduced/final_mix_vocal_ai_artifact_reduced_320.mp3`.
- Vocal chain preset: `renders/hangang_shadow_v29_vocal_ai_artifact_reduced/vocal_chain_preset.RfxChain`.
