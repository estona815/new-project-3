# Logic Rescue Plan

- status: RESCUE_PLAN_READY
- execution: manual Logic Pro plan only
- verified Logic automation success: false

## Marker Pass
- create marker `intro_hook_hint` at 0.0s; end 4.0s
- create marker `main_hook` at 4.0s; end 20.0s
- create marker `verse_groove` at 20.0s; end 36.0s
- create marker `hook_return` at 36.0s; end 52.0s
- create marker `breakdown_filtered_lead` at 52.0s; end 68.0s
- create marker `final_hook` at 68.0s; end 88.0s
- create marker `clean_outro_or_loop` at 88.0s; end 100.0s

## Lead / Hook Pass
- primary lead motif: lead_A
- response motif: response_B
- hook return strategy: repeat lead_A with a small variation, then answer with response_B
- keep the core melody centered; use width only on support layers
- do not copy exact reference melodies or artist vocal identity

## Vocal Texture Pass
- demote_texture: dynamic_eq_or_volume_automation on 300Hz-3kHz; manual_logic_required=true
- center_band_soft_attenuation: mid_side_center_band_demotion on center-heavy 300Hz-3kHz vocal-like band; manual_logic_required=true
- preserve_atmosphere: avoid_destructive_removal on usable emotional texture; manual_logic_required=false

## Sample / Synth Motif Pass
- main_motif: 01_02._-___Shippo 0.0-1.8s; most recognizable motif candidate
- response_motif: 02_05._-___Shippo 0.0-1.8s; contrasts main motif while staying repeatable
- texture_layer: 03_06._Chinese_Tea 0.0-1.8s; usable atmosphere at low density
- transition_element: 04_06._-___Shippo 0.0-1.8s; short intentional transition element, not random glitch

## Section Usage
- intro_hook_hint: main_motif_filtered / density low
- main_hook: main_motif_full / density high
- verse_groove: texture_only / density low
- hook_return: main_motif_full / density high
- breakdown_filtered_lead: response_motif_filtered / density low
- final_hook: main_motif_full_plus_response / density high
- clean_outro_or_loop: texture_tail / density low

## Mix Handoff
- start mix/master only after the lead and hook identity survive a mute test
- stereo-only source may be ducked or demoted, but is not stem-level remixing
- no vocal removal, kick replacement, 808 rewrite, drum rewrite, plugin insertion, or Logic automation success is claimed
