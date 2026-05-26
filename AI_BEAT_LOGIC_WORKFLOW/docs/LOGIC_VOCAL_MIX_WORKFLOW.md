# Logic Vocal Mix Workflow

This document is a manual Logic Pro workflow for vocal songs and reference-inspired productions. It does not claim AppleScript can fully mix vocals automatically. Automation can help with setup/import/status, but vocal tone, plugin settings, clip gain, tuning taste, balance, and final judgment require a human listening pass.

## A. Session Setup

- Import beat and vocal files.
- Set project sample rate to export target.
- Keep raw vocal muted as backup.
- Route lead vocal, adlibs, and backing vocals to separate buses.
- Route all vocals to a vocal bus.
- Route instrumental to an instrumental bus.
- Route all audio to a pre-master bus.

## B. Vocal Gain Staging

- Clip gain phrases before compression.
- Reduce loud spikes manually.
- Raise quiet phrases only enough for consistent delivery.
- Avoid normalizing destructively.

## C. Lead Vocal Chain

Suggested chain:

1. Channel EQ high-pass
2. Subtractive EQ for mud/boxiness
3. Resonance control
4. Pitch correction/tuning if requested
5. Compressor for leveling
6. De-esser
7. Saturation if requested
8. Second compressor if needed for tone
9. Presence/air EQ if needed
10. De-ess again if saturation or brightness raises sibilance
11. Send to reverb
12. Send to delay throws

## C2. Plugin-Aware Vocal FX Requests

- Treat `오토튠`, `auto tune`, `하드튠`, `튠 세게`, `피치 보정`, `로봇틱하게`, and `자연스럽게 튠` as pitch-correction intent ranging from subtle to hard effect.
- Treat `디카페이터`, `데카피테이터`, `Decapitator`, `사운드토이즈`, `saturation`, `새츄레이션`, `따뜻하게`, `거칠게`, `찢어지게`, and `살짝 디스토션` as saturation intent.
- For AutoTune + Decapitator requests, use this insert order: cleanup EQ, pitch correction, compression, saturation/Decapitator, de-esser after saturation if needed, tone EQ, reverb/delay sends.
- If Soundtoys Decapitator is installed, manual Logic insertion is still required unless automation/render logs verify insertion.
- If Soundtoys Decapitator is not detected, write: `Insert Soundtoys Decapitator on the vocal bus if installed.`
- If Logic automation cannot insert plugins, mark `manual_required`.
- Fallback processing must be reported as `generic saturation approximation`, not `Decapitator applied`.
- Keep the user's voice identity and do not clone 2hollis, Nate Sib, ycs, or any artist voice.

## D. Rap-Forward Vocal

- Keep vocal dry and upfront.
- Use less reverb.
- Use delay throws at phrase endings.
- Compress enough for consistency but avoid lifeless flattening.

## E. Hyperpop / Digicore Vocal

- Use brighter presence carefully.
- Use tuning/formant effects only if requested.
- Make adlibs wider than lead.
- Keep lead intelligible.
- Avoid harsh sibilance.

## F. Adlibs / Backings

- Lower than lead.
- Wider than lead.
- More reverb/delay than lead.
- High-pass more aggressively if muddy.
- Do not mask the hook.

## G. Beat vs Vocal Balance

- Lower beat slightly where vocal enters if needed.
- Use automation around hooks.
- Prevent 808 from masking low vocal body.
- Prevent synth leads from fighting vocal presence.

## H. Reference-Inspired Drum Direction

- Translate user references into drum density, transient shape, 808 tone, and arrangement energy.
- Do not copy exact drum patterns from the reference.
- If only stereo beat exists, use broad treatment or manual layering.
- If stems/MIDI exist, adjust kick/snare/hat/808 programming more directly.

## I. Pre-Master

- Check vocal intelligibility at low volume.
- Check sibilance on headphones.
- Check 808 on small speakers and sub-capable speakers.
- Leave headroom.
- Export with normalize off.
