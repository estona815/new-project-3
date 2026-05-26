# Female Vocal Selection Report

- Credits before Safari work observed in Suno UI: 8860.
- Additional Suno generation credits spent in this pass: 0.
- Reason: Safari multitrack export `12 Backing_Vocals.wav` was too sparse to hear clearly, so v04 adds a pitch-shifted female-like support layer derived from the cleaned lead vocal, while still avoiding random lyrics, filler ad-libs, or lead takeover.

## Candidates

- Candidate A: raw `12 Backing_Vocals.wav` from Suno Studio multitrack. Selected as the female source.
- Candidate B: `processed_female_vocal_stem.wav`, cleaned, widened, and reinforced with an audible female-like support layer.
- Candidate C: `0101_FINAL_female_alt.wav`, female-forward alternate made from the same Suno backing vocal source.
- Candidate D: dual-vocal blend in `0101_FINAL_dual_vocal.wav`, selected as the most musical final blend.

## Selection

- Best candidate: dual-vocal blend.
- Role recommendation: keep male lead as emotional center; use female layer as wide support/harmony lift.
- Timing accuracy: sample-aligned to the Suno multitrack export; no timing stretch was applied.
- Remaining artifacts: the extra audible female layer is a pitch-shifted support texture rather than a newly generated Suno female lead; de-essing and breath/sip suppression were applied to keep it from becoming fizzy.
