# Release Candidate Checklist

This checklist must be completed before calling the plugin release-candidate ready.

## Automated QA

- [ ] `VOCAL_CLARITY_REPAIR_SYSTEM/scripts/run_rc_qa.sh` passes.
- [ ] JSON validation passes.
- [ ] Python compile passes.
- [ ] Direct test runner passes.
- [ ] Factory preset validation passes.
- [ ] Parameter freeze validation passes.
- [ ] Real-time static audit passes.
- [ ] Installed REAPER JSFX copy matches repo.
- [ ] Prompt 7 synthetic/passthrough release gate passes.

## Real Audio QA

- [ ] REAPER renders captured for Preserve.
- [ ] REAPER renders captured for Balanced.
- [ ] REAPER renders captured for AI Metallic Surgical.
- [ ] REAPER renders captured for Hiss / Room Tone Gentle.
- [ ] REAPER renders captured for Voiceover Clean.
- [ ] REAPER renders captured for DSP Only Safe.
- [ ] Strong Test / Repair rendered separately.
- [ ] Original/processed/matched/residual WAVs archived.
- [ ] Prompt 7 external-render evaluation run on real renders.
- [ ] Clean-input do-no-harm passes.
- [ ] Residual source leakage low in Preserve.

## Manual Listening

- [ ] Original listened.
- [ ] Processed loudness-matched listened.
- [ ] Residual listened.
- [ ] Preserve keeps vocal forward.
- [ ] Consonants intact.
- [ ] Air/ambience intact.
- [ ] Transients intact.
- [ ] Stereo width natural.
- [ ] Strong clearly non-default.
- [ ] Listening approval form completed.

## DAW Compatibility

- [ ] REAPER scans plugin.
- [ ] UI opens.
- [ ] Audio passes.
- [ ] Bypass returns dry.
- [ ] DryWet 0 returns dry.
- [ ] Presets can be recalled or manually set.
- [ ] Automation does not crash.
- [ ] Offline render works.
- [ ] Save/reopen works.
- [ ] Duplicate track works.
- [ ] Freeze/bounce works.
- [ ] Close/reopen does not crash.

## Performance And Stability

- [ ] 44.1 kHz / 512 block tested.
- [ ] 48 kHz / 128 block tested.
- [ ] 48 kHz / 1024 block tested.
- [ ] 96 kHz / 512 block tested.
- [ ] Offline large block tested.
- [ ] 10-minute long-run tested.
- [ ] CPU by mode measured.
- [ ] No memory growth observed.
- [ ] No denormal spike observed.

## Packaging

- [ ] Plugin file included.
- [ ] Presets/policy files included if shipping them.
- [ ] Documentation included.
- [ ] Release notes included.
- [ ] No absolute local paths.
- [ ] Version is correct.
- [ ] Unsupported formats are not claimed.
- [ ] Install/update behavior checked.

## Release Blockers

Do not approve RC if any are true:

- fresh default is not Preserve
- Strong is default or auto-selected
- bypass is not dry
- DryWet 0 is not dry
- NaN/Inf reaches output
- invalid model output reaches audio
- Preserve damages clean vocal
- Preserve removes consonants
- Preserve collapses air
- Preserve smears transients
- residual contains strong ghost vocal in default
- stereo image collapses
- automation crashes or severely clicks
- latency causes dry/wet comb filtering
- old sessions/presets break
- documentation overpromises
