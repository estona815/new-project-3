# Manual Test Plan Prompt 38

Use user-owned current mix and reference files. Do not insert reference audio
into the final project.

## Reference Intake Tests

1. Missing reference creates a visible warning.
2. Multiple references are recorded with roles.
3. No reference uses target profile only.
4. Reference audio is never copied into final output.

## Target Profile Tests

1. `digicore_hyperpop_hiphop_vocal_forward` exists.
2. `raw_digicore_intense` allows more energy but still limits artifact exposure.
3. `phone_reels_loud_clear` prioritizes vocal audibility and mono compatibility.
4. Safety constraints override profile targets.

## Analyzer Tests

1. Loud reference vs current creates loudness difference.
2. Bright reference with AI fizz blocks high boost.
3. Wide reference with mono risk blocks widening.
4. Stronger low-end reference with muddy current recommends control before boost.
5. Louder reference with limited current blocks more limiting.

## Planner Tests

1. Vocal too low prefers instrumental space before vocal gain.
2. Lead melody too low plans melody space without masking vocal.
3. Drums too soft avoids master clipping first.
4. 808 weak but muddy plans low-end control first.
5. Unsafe adjustments are listed as blocked.

## Draft Safety Tests

1. Original tracks remain untouched.
2. Original master remains untouched.
3. Rollback JSON is created.
4. No pitch correction is inserted.
5. No reference audio is inserted as content.

## Evaluation Tests

1. Missing render fails evaluation.
2. Match improvement with AI fizz increase rejects.
3. Match improvement with vocal harshness rejects.
4. Match improvement with phase worsening rejects.
5. Match improvement with beat impact loss rejects.

## Report Tests

1. `reference_match_report.md` exists.
2. Blocked adjustments are visible.
3. Safety note is present.
4. Final recommendation uses the allowed enum.
5. `project_reference_match_matrix.json` exists.

## Human Review

Accept only if the mix moves toward the target without copying the reference and
without making the song worse at equal loudness.
