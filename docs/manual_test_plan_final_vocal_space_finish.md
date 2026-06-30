# Manual Test Plan: Final Vocal Space Finish

Run the workflow on a saved copy of a REAPER project or with existing AutoMix reports only.

## Required Cases

- Missing `accepted_recovery_sources.json` blocks placement.
- Empty accepted recovery list blocks placement.
- A later rejected recovery source blocks placement.
- `accepted_light` selects `fragile_ai_vocal_space`.
- Dry-run creates reports and modifies no REAPER project.
- Placement draft metadata never marks original tracks as modified.
- Pitch correction remains blocked.
- No pitch plugin insertions or pitch parameter writes are reported.
- Master is untouched before premaster.
- Premaster is blocked before accepted placement review.
- Final export is blocked.
- Missing A/B renders keep evaluation failed.
- Review package folder and ZIP do not contain `FINAL` in the package type.
- Rollback metadata exists for placement and premaster drafts.

## Example Dry Run

```sh
python3 scripts/run_final_vocal_space_finish.py \
  --project reaper/mesi_1_v37_vocal_clarity_max_guarded/mesi_1_v37_VOCAL_CLARITY_FINAL.rpp \
  --dry-run \
  --make-review-package \
  --strict-protection
```

## Expected Output

- `automix/eval_reports/finalizing_vocal_space_and_review_package_report.md`
- `automix/analysis_reports/final_vocal_space_analysis.json`
- `automix/chain_plans/final_vocal_space_carving_chain_plan.json`
- `automix/eval_reports/final_vocal_space_protection_report.json`
- `automix/review/final_vocal_space_review_form.md`
- `deliverables/*_REVIEW_PACKAGE_vXX/`
