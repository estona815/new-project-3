# Prompt 18: Build Suno Vocal Repair Playbook

You are Codex building a Suno-specific vocal repair playbook from existing knowledge base rules.

Use:

- `knowledge_base/07_rule_cards/`
- `knowledge_base/08_reaper_translation/reaper_vocal_chain_translation.md`
- `knowledge_base/09_qc_rules/qc_listening_checklist.md`
- `decision_engine/reaper_rule_card_schema.yml`
- `decision_engine/qc_rule_card_schema.yml`

Build a playbook that covers:

- Common Suno vocal artifacts
- Conservative cleanup candidates
- Dynamic EQ and de-ess decisions
- Body restoration
- Parallel original blend
- Vocal bus trim
- Full-mix comparison
- Candidate rejection
- Release-ready, demo-ready, repair-more, or regenerate-needed decisions

Constraints:

- Do not process audio on a public/shared computer.
- Do not claim plugin availability unless verified.
- Do not turn notes into passive documentation only; every lesson must become a workflow step or rejection rule.
