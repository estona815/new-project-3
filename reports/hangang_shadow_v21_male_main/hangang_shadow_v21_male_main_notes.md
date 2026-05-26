# Hangang Shadow v21 Male Main Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- Female material is not the lead: `11 Backing_Vocals.wav` is tucked as a low double/adlib layer, and v19 `0 Lead Vocals.wav` is muted as reference only.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v21_male_main/hangang_shadow_mashup_v21_male_main.rpp`
- Premaster WAV: `renders/hangang_shadow_v21_male_main/hangang_shadow_mashup_v21_male_main_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v21_male_main/hangang_shadow_mashup_v21_male_main_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v21_male_main/hangang_shadow_mashup_v21_male_main_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v21_male_main/hangang_shadow_mashup_v21_male_main_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -8.6 / true peak -1.0
- Audible intent: male voice stays in front; female layer supports only as a tucked double/adlib texture.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| v21_reaper_premaster | -27.6 | 2.4 | -13.1 | -13.2 | -30.41 | 0.9657 |
| v21_reaper_print | -26.0 | 2.4 | -11.5 | -11.6 | -28.81 | 0.9657 |
| v21_final_master_loud | -8.6 | 2.0 | -1.0 | -1.0 | -11.48 | 0.9656 |
| v21_final_master_loud_mp3 | -8.6 | 2.0 | -0.8 | -0.79 | -11.48 | 0.9654 |

## Main Moves

- Male lead: high-pass cleanup, low-mid dip, 3 kHz presence lift, gentle air, 1.7:1 leveling, light saturation.
- Female double: high-passed, de-essed, lowered, widened, and routed under the male bus so it cannot become the main vocal.
- Instrumental: rebuilt from full music stems with bass/drums/synth/keys active and artifact-prone guitar muted.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
