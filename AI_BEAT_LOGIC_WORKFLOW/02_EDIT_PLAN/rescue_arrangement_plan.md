# Rescue Arrangement Plan

- status: RESCUE_PLAN_READY
- length mode: under_2min
- target duration: 100.0s
- hook appears by: 0.0s
- mix only not enough: false

## Source Problem
- mix_only_not_enough: false
- missing_lead: false
- missing_hook: false
- weak_arrangement: false
- weird_vocal_texture: true

## Sections
- intro_hook_hint 0.0s +4.0s energy 3
  - Introduce the new lead motif immediately.
  - Use filtered sample/synth motif.
  - Avoid long AI intro.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.
- main_hook 4.0s +16.0s energy 5
  - Full drums/808 enter.
  - Lead melody becomes central.
  - Vocal texture must not dominate lead.
  - Add wide upper synth layer, sub stays mono.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.
- verse_groove 20.0s +16.0s energy 3
  - Reduce lead density but keep motif fragments audible.
  - Use one call-response phrase.
  - Remove repeated AI loop blocks.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.
- hook_return 36.0s +16.0s energy 5
  - Return to the same hook identity.
  - Add one controlled variation, not a new random idea.
  - Keep transition clean and intentional.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.
- breakdown_filtered_lead 52.0s +16.0s energy 2
  - Filter the lead or sample motif.
  - Push weird vocal texture behind the motif.
  - Do not add random risers unless they announce the final hook.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.
- final_hook 68.0s +20.0s energy 5
  - Bring back full hook with final lift.
  - Use stronger drums/808 without masking lead.
  - Resolve sample/synth motif clearly.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.
- clean_outro_or_loop 88.0s +12.0s energy 2
  - End quickly or make a loopable ending.
  - Avoid dead outro.
  - Do not extend generated material.
  - Push vocal texture back or replace it with synth/sample lead.
  - Use the strongest sample motif only if ownership/clearance allows direct use.

## Remove Or Reduce
- long weak intro
- unmotivated vocal textures
- repeated AI loop blocks
- dead outro
- overextended sections
- decorative fills that do not support hook

## Add Or Create
- hook return
- call-response phrase
- 4-8 bar variation
- clean transition
- final hook lift

## Manual Logic Required
- True stem-level rewrite requires stems or manual Logic editing.
- New lead MIDI/synth may need manual confirmation.
- Stereo-only rescue cannot claim vocal removal, kick replacement, 808 rewrite, or drum rewrite.
