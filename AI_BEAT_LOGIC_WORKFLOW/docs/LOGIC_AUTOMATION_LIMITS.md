# Logic Automation Limits

Logic Pro automation is optional and may be limited by macOS permissions, Logic Pro UI state, project templates, and AppleScript support.

## What The Pipeline Can Try

- Detect macOS.
- Check whether `/Applications/Logic Pro.app` exists.
- Check whether `osascript` is available.
- Open Logic Pro.
- Reveal or prepare `04_PROCESSED_AUDIO/working_input.wav` for import.
- Ask the user to save or verify `03_LOGIC_PROJECT/suno_humanized_project.logicx`.
- Always write `03_LOGIC_PROJECT/logic_automation_status.md`.

## What It Must Not Pretend

- It must not claim a Logic project was saved unless the `.logicx` file/package exists.
- It must not claim full mix automation succeeded.
- It must not claim plugin insertion, EQ curves, automation curves, region edits, or export happened unless those outputs are verified.

## Known Limits

- AppleScript may not control every Logic Pro mixing function.
- Plugin insertion, exact EQ moves, automation curves, crossfades, and region edits often require manual action.
- UI scripting may require Accessibility permissions and can fail depending on the active Logic window.
- Logic may open a startup dialog or template chooser that blocks automation.

## Required Fallback

The pipeline must still generate:

- `02_EDIT_PLAN/edit_plan.md`
- fallback processing outputs in later stages
- export/QC reports in later stages

If Logic automation is unavailable, failed, or partial, follow the manual checklist in `02_EDIT_PLAN/edit_plan.md` and the status file.

