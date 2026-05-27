# Prompt 16: Extract Lesson Cards

You are Codex converting public source references into copyright-safe lesson cards.

Inputs:

- `knowledge_base/00_source_index/source_index.yml`
- `decision_engine/mix_lesson_card_schema.yml`
- Source links and short notes only

Rules:

- Do not copy large passages.
- Do not store full transcripts.
- Do not download audio or video.
- Use short paraphrases and original workflow conclusions.
- Include timestamps for YouTube lessons when useful, but never transcript dumps.

For each useful source, create lesson cards using the schema fields:

- lesson_id
- source_id
- topic
- problem_addressed
- core_idea
- plugin_type
- suggested_chain_position
- rough_parameter_range
- genre_relevance
- suno_relevance
- reaper_translation
- failure_modes
- qc_check
- confidence_level
- notes

Only keep lessons that can become REAPER workflow rules, plugin-chain rules, QC rules, or Suno vocal repair rules.
