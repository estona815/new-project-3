# Pass 04 Suno 000000 Stem Download Report

Generated: 2026-05-24T18:42:42

## Result
- Selected Suno voice: `000000`.
- Generated 2 candidates; extracted all detected stems from the longer 0:39 candidate.
- Credits used for this 000000 pass: 10 generation + 50 all detected stems = 60.
- Observed credit balance after extraction: 9200.
- Downloaded ZIP: `/Users/hantaeheuk/Documents/New project 3/downloads/suno_pass04/pass04_000000_voice_male_lead_A_all_detected_stems.zip`.
- Extracted stems directory: `/Users/hantaeheuk/Documents/New project 3/downloads/suno_pass04/stems`.

## Download Error Analysis
- Chrome blocked the Suno render download domain with `ERR_BLOCKED_BY_CLIENT`.
- The UI-generated download URL itself was valid; downloading the same URL through `curl` succeeded.
- This points to a Chrome client/extension block, not a failed Suno stem extraction.

## Important Limitation
- The candidate is only about 39.92s long.
- The Chrome text input path stripped Korean characters in the lyrics field, so the generated lyric content is incomplete.
- Therefore these stems are imported into REAPER muted as a `000000` candidate/reference, not used as active production replacement.

## Suno Candidate Links
- https://suno.com/song/6da5749b-9e26-49d3-a4cc-0eb738891537
- https://suno.com/song/0ed0460d-42dc-42e9-b29d-33ee30a366d8
