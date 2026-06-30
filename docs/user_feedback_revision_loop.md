# User Feedback Revision Loop

This workflow turns user listening notes into traceable revision evidence. It
does not make audio changes by itself.

## Purpose

Users often report issues such as cloudy vocals, remaining Suno-like fizz,
harsh 3-5 kHz tone, too much reverb, low-end masking, or a flat master. Prompt
45 records those comments and creates a conservative action plan for the next
pass.

The correct language is artifact reduction, artifact suppression, conservative
restoration, and human review required. Do not claim total AI artifact removal.

## Command

Initialize the baseline when no listening feedback has been received yet:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --initialize-baseline
```

This writes an empty revision memory and QC integration report with
`baseline_status=no_feedback_recorded`. It is only an audit marker and does not
fabricate a listening review.

Record actual feedback:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --pass-id v01 \
  --track-name "Lead Vocal" \
  --feedback "보컬이 뿌옇고 10kHz 이상 Suno fizz가 남아 있다."
```

Multiple `--feedback` values are allowed. A `--feedback-file` may also be used;
each non-empty line becomes a feedback item.

## Outputs

- `automix/review/user_feedback_revision_memory.json`
- `automix/eval_reports/user_feedback_action_plan.json`
- `automix/eval_reports/user_feedback_revision_report.md`
- `automix/eval_reports/user_feedback_qc_integration.json`
- `automix/eval_reports/user_feedback_qc_integration.md`
- `automix/eval_reports/global_qc_summary.json` includes feedback status when
  global QC is rebuilt.
- `automix/export/final_export_state.json` includes feedback status when final
  export state is resolved.

## Resolving Feedback

Feedback is not cleared by intent or by writing a plan. Resolve a feedback ID
only after the relevant next pass has evidence:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --pass-id v02 \
  --resolve-feedback-id feedback_abc123456789 \
  --resolution-notes "Loudness-matched A/B and final QC passed." \
  --evidence-path automix/eval_reports/final_qc_metrics.json \
  --human-reviewed \
  --measured-qc-passed \
  --loudness-matched-ab-reviewed
```

The resolver accepts the closure only when all of these are true:

- the feedback ID exists in revision memory;
- at least one evidence path exists on disk;
- measured QC passed;
- loudness-matched A/B was reviewed;
- human review was completed.

If any requirement is missing, the resolution record is saved as incomplete and
the feedback remains unresolved.

## QC Integration Report

`user_feedback_qc_integration` links each feedback item to:

- likely diagnostic causes from the action plan;
- planned dry-run actions and any recorded applied actions;
- relevant QC metric values when they exist;
- loudness-matched A/B preview status;
- resolution records and remaining risks.

The report uses cautious language. A resolved item means the required evidence
and human review were recorded; it is not a standalone claim that the sound is
preferred by every listener.

## Safety Rules

- Feedback creates dry-run plans only.
- Human review is required for every feedback item.
- Repeated categories are elevated in priority so the same problem is not lost
  across passes.
- Unresolved feedback blocks final delivery in both final export state
  resolution and global QC.
- Resolution requires existing evidence files, measured QC, loudness-matched
  A/B review, and human review.
- Final delivery with feedback requires the QC integration report so the
  feedback-to-evidence chain is inspectable.
- Master limiter pushes are blocked as a response to mix problems.
- Strong tuning, strong saturation, blind stereo widening, and total artifact
  cleanup claims are blocked as automatic responses.

## Typical Mappings

- Cloudy vocal: check 200-500 Hz mud, 2-5 kHz intelligibility, reverb distance,
  and vocal/instrument masking.
- Vocal behind the beat: prefer dynamic music-bus carving and send ducking
  before lead gain.
- Suno fizz or watery smear: run conservative artifact suppression planning and
  require the exact first-slot rescue plugin trace before final claims.
- Flat master: audit limiter gain reduction, crest factor, LRA, short-term LUFS,
  and true peak before loudness changes.
- Mono or phase collapse: check correlation, mono fold-down, low-end side
  energy, and side-channel hash before widening.

## Acceptance

A feedback item is not resolved just because a plan exists. Resolution requires
evidence from the relevant next pass: measured QC, loudness-matched A/B, plugin
trace where applicable, and user review.

Final export remains blocked until unresolved feedback IDs are cleared or a
later workflow writes stronger review evidence that the feedback was addressed.
