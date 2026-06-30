# Artifact Signal Audit

- Project: `project`
- Created UTC: `2026-06-02T15:39:29Z`
- Artifact signal established: `False`
- Safe to run artifact suppression: `False`
- Usable source signals: `0`
- Usable metric signals: `0`
- Usable feedback signal: `False`

This report is evidence triage only. It does not claim artifact removal or audio improvement.

## Blockers

- `artifact_signal_not_established`
- `measured_artifact_metrics_not_established`

## Warnings

- `no_user_artifact_feedback_recorded`
- `some_artifact_metric_reports_are_report_only`
- `source_map_does_not_classify_ai_or_source_separated_vocals`

## Metric Observations

- `final_qc.vocal_preservation.ai_fizz_score` value=`0.0` usable=`False` report_only=`False`
- `final_qc.vocal_preservation.metallic_artifact_score` value=`0.0` usable=`False` report_only=`False`
- `final_qc.vocal_preservation.sibilance_splatter_score` value=`0.0` usable=`False` report_only=`False`
- `premaster.ai_artifact_risk_profile.high_fizz_risk` value=`0.0` usable=`False` report_only=`True`
- `premaster.ai_artifact_risk_profile.metallic_harshness_risk` value=`0.0` usable=`False` report_only=`True`
- `premaster.ai_artifact_risk_profile.sibilance_splatter_risk` value=`0.0` usable=`False` report_only=`True`

## Feedback Observation

- AI artifact feedback count: `0`
- Baseline status: `no_feedback_recorded`

## Source Observations

- `ai_or_already_processed_vocals` count=`0` usable=`False`
- `source_separated_vocals` count=`0` usable=`False`
- `V37 LEAD VOCAL CLARITY MAX GUARDED` group=`safe_vocal_candidates` class=`raw_vocal` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 BACKGROUND DOUBLE SUPPORT L/R` group=`safe_vocal_candidates` class=`raw_vocal` ai=`0.0` source_sep=`0.0` usable=`False`
- `SOURCE full mix reference muted` group=`stem_required_tracks` class=`full_mix` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 INSTRUMENTAL BUS free EQ pocket` group=`stem_required_tracks` class=`full_mix` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 PRINTED VOCAL REVERB SEND` group=`unknown_tracks` class=`unknown` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 PRINTED VOCAL DELAY SEND` group=`unknown_tracks` class=`unknown` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 RETURN ReaVerbate dark send` group=`unknown_tracks` class=`unknown` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 RETURN ReaDelay filtered throw` group=`unknown_tracks` class=`unknown` ai=`0.0` source_sep=`0.0` usable=`False`
- `SOURCE full mix reference muted` group=`high_risk_tracks` class=`full_mix` ai=`0.0` source_sep=`0.0` usable=`False`
- `V37 INSTRUMENTAL BUS free EQ pocket` group=`high_risk_tracks` class=`full_mix` ai=`0.0` source_sep=`0.0` usable=`False`
