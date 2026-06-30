# Release Notes - 0.9.0 RC Lock

Status: automated QA lock prepared. This is not a final shipping approval until real DAW rendering, manual listening sign-off, and packaging validation are complete.

## Headline Changes

- Preservation-first default locked to Preserve.
- Factory preset policy added for Preserve, Balanced, AI Metallic Surgical, Hiss / Room Tone Gentle, Voiceover Clean, Strong Test / Repair, DSP Only Safe, Side Noise Cleanup, and Artifact Focus Low Denoise.
- Strong mode isolated from fresh defaults, migration, and default release scoring.
- Residual Monitor policy documented as a trust/listening feature.
- Prompt 7 A/B harness extended for Prompt 8/9 preset and synthetic regression categories.
- Prompt 9 RC QA runner added.

## Audio Policy

This plugin reduces AI artifacts and noise while preserving the source. It is not a maximum noise-removal tool and does not reconstruct missing clarity. Some noise may remain when removing it would damage vocal tone, consonants, high-frequency air, transients, ambience, or stereo width.

No exciter, high-shelf clarity compensation, automatic mastering, or new denoise model was added in this RC lock pass.

## Known Limitations

- Current validated plugin format is REAPER JSFX only.
- No VST3, AU, AAX, or standalone build artifact exists in this repository.
- No model backend is present; model version is `none` and model mode is documented as DSP Only safe path.
- Synthetic/passthrough automated checks do not replace real REAPER renders.
- Manual residual listening is still required before release.
- Strong Test / Repair can affect source tone and must not be used as the default demo mode.

## Migration Notes

- Existing JSFX slider order is preserved.
- Missing new preset parameters use safe defaults.
- Invalid values are clamped to absolute ranges.
- Strong mode is never selected automatically.
- Parameter IDs must remain frozen after RC branch cut unless migration is explicitly added.

## RC Verification

Run:

```sh
VOCAL_CLARITY_REPAIR_SYSTEM/scripts/run_rc_qa.sh
```

The script writes JSON and Markdown reports to `/tmp/codex_vocal_rc_qa` unless `CODEX_VOCAL_RC_QA_DIR` is set.
