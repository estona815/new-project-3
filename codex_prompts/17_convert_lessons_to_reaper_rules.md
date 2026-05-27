# Prompt 17: Convert Lessons To REAPER Rules

You are Codex converting lesson cards into actionable REAPER rule cards.

Inputs:

- `decision_engine/mix_lesson_card_schema.yml`
- `decision_engine/reaper_rule_card_schema.yml`
- Existing lesson cards from the knowledge base

For each lesson or cluster of lessons:

1. Identify the REAPER context.
2. Choose target track type: lead vocal, backing vocal, instrumental, 808/bass, mixbus, master, or QC bus.
3. Select plugin candidates from installed/verified tools or documented future candidates.
4. Write reversible action steps.
5. Require render candidate and bypass comparison unless the rule is documentation-only.
6. Define expected improvement.
7. Define rejection conditions.
8. Define report fields for QC.

Do not invent plugin availability. If a plugin has not been verified on the main computer, mark it as a candidate only.

Output original rule cards only. Do not copy source text.
