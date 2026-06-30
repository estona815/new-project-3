# Source Acceptance Request

- Project: `project`
- Template: `automix/review/source_acceptance_manifest_template.json`

Fill the template with user-owned WAV candidates after listening review.

Required before a source can be used for final export:

- WAV source exists and is readable.
- `human_accepted` is true only after explicit user listening acceptance.
- Final export stage is one of the accepted final export stages.
- Full-mix/reference material is not used as automatic processing input.

Current blockers:

- `source_acceptance_candidates_missing`
