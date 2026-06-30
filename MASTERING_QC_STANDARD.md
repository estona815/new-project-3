# Mastering QC Standard

Mastering is not a rescue stage for unresolved mix problems. If the vocal is
buried, harsh, phasey, or artifact-heavy, the correct result may be
`mix_revision_required`.

## Mastering Priorities

1. Translation
2. Vocal clarity
3. True peak safety
4. Crest factor and transient preservation
5. Mono compatibility
6. Low-end control
7. Loudness target

## Profiles

- Conservative Streaming Master: vocal clarity, true peak safety, dynamics.
- Loud Reels Preview Master: short-form loudness with controlled peak and
  high-end risk.
- AI Source Repair Master: minimal added compression or limiting, artifact risk
  reduction, tonal balance.
- Stem Rebeat Master: bus balance and vocal-seat carving before final polish.

## Default Master Chain

Use one EQ lane, one glue lane, one clip lane, one limiter, and one meter/output
lane unless the pass report explains the overlap.

1. `Ozone 12 Equalizer` or `ReaEQ`: corrective tonal trim only.
2. `TDR Kotelnikov`: transparent glue, normally 0.5-2 dB gain reduction.
3. `JS: Codex V20 Master Glue`: optional repo JSFX glue when code is installed
   and traced; otherwise log missing.
4. `FreeClip`: peak shave only; do not use it to fix drum/808 imbalance.
5. `ReaLimit`: final ceiling, default -1.0 dBFS proxy until true peak is
   measured.
6. `mvMeter2`, `ClearMaster Audit`, or `Vocal Clarity Output Guard`: metering
   and output guard only.

## Targets

- Loud reference master: -9.5 to -8.0 LUFS-I, true peak <= -1.0 dBTP, intended
  for loud A/B or short preview when the mix is already stable.
- Safer streaming master: -14.5 to -12.5 LUFS-I, true peak <= -1.0 dBTP,
  intended as the default shareable review copy.
- If the master chain sustains more than 2 dB of gain reduction, mark
  `mix_revision_required` and fix vocals, 808/bass, or drums before pushing the
  master harder.

## Final QC Checks

- final WAV exists and is nonzero;
- WAV is primary deliverable;
- MP3 is optional and never the only final;
- final render manifest has no failures and points to an existing primary WAV;
- delivery ZIP manifest is complete and the ZIP exists;
- project state manifest confirms original tracks are protected;
- plugin mapping summary exists and records limitations;
- loudness-matched A/B preview exists for review;
- global rollback registry validates original track and master protection;
- sample rate and bit depth match profile;
- clipping and silence checks pass;
- true peak proxy and loudness are safe;
- phase and low-end stereo risk are visible;
- final QC records warnings and failures;
- human approval and warning acknowledgment exist;
- unresolved user feedback is cleared with evidence;
- recorded feedback has a feedback-QC integration report;
- fixture coverage and requirements traceability audits are inspectable;
- open risk register has no unresolved delivery blockers;
- risk remediation plan documents dry-run next actions when risks remain;
- path hygiene audit has no source-code hardcoded local path blockers;
- intent classification exists and is inspectable;
- processing policy audit passes for included chain plans;
- professional readiness audit passes when final delivery is requested.

## Unsafe Outputs

Unsafe override may create review copies only. It must not produce files named
as safe finals.

## Readiness Audit

Run:

```sh
python3 scripts/run_professional_readiness_audit.py \
  --project-name project \
  --output-dir automix \
  --final-delivery-requested
```

The audit reads final export state, final render manifest, delivery package
manifest, project state manifest, plugin mapping summary, final QC, A/B preview
manifest, global QC, final human approval, rollback registry, feedback revision
memory, feedback-QC integration, intent classification, claim-language guard
results, fixture coverage, requirements traceability, processing policy audit,
open risk register, and required documentation/script files. It is
delivery-ready only when all blockers are clear.

When blockers remain, `scripts/run_risk_remediation_plan.py` produces a dry-run
operator plan. That plan explains evidence to collect and unsafe actions to
avoid; it is not delivery approval.

`scripts/run_path_hygiene_audit.py` checks source-code hardcoded local paths and
flags generated report paths for handoff review.
