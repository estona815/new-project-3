# Suno Vocal Repair Pipeline

## 1. Input

Supported future inputs:

- Full Suno mix
- Suno stems
- User-provided vocal and instrumental
- Existing REAPER session

Public PC mode must not store or process these files.

## 2. Source Separation If Needed

If only a full mix exists, create separation candidates on the main computer:

- Demucs vocal/instrumental split
- UVR alternate vocal split
- Optional manual stem import

Never treat separated stems as perfect. Document bleed and artifacts.

## 3. Vocal Cleanup Candidates

- A: minimal cleanup, almost transparent
- B: balanced denoise and de-fizz
- C: stronger artifact control
- D: emergency salvage, likely audible processing

Avoid destroying consonants, air, vibrato, and identity.

## 4. REAPER FX Chain

Suggested stages:

- Input trim
- Conservative denoise
- Dynamic EQ
- De-ess
- Body restoration
- Gentle compression
- Parallel original vocal blend
- Metering/QC
- Safe preview limiting
- High-pass only if needed
- Dynamic de-fizz
- De-ess
- Resonance control
- Parallel restore bus
- Light saturation or harmonic restore
- Final blend bus

Plugin-aware candidates may use Bertom Denoiser Classic, TDR Nova, Techivation T-De-Esser 2, Klanghelm IVGI/DC1A/MJUC jr, Voxengo SPAN, Youlean, and LoudMax after they are installed and verified on the main computer.

## 4A. Knowledge Base Rule Conversion

Public mixing/mastering sources are collected as metadata and short notes only. They are converted through this chain:

1. Source index entry
2. Copyright-safe lesson card
3. Actionable REAPER rule card
4. Candidate chain or QC checklist item
5. Report field and rejection condition

Do not store full transcripts, full articles, downloaded videos, downloaded audio, or copied manuals. The knowledge base exists to drive REAPER execution and QC decisions, not to archive source content.

## 5. Render Candidates

Render:

- `candidate_A_minimal.wav`
- `candidate_B_balanced.wav`
- `candidate_C_stronger.wav`
- `candidate_D_salvage.wav`
- `final_selected.wav` only after approval

## 6. QC Report

Capture:

- Source/candidate paths
- Loudness and peak
- Spectrum snapshots
- Artifact notes
- Consonant integrity notes
- Stem bleed notes
- Manual listening decision
- Candidate scoring fields from `decision_engine/candidate_scoring_schema.yml`
- Decision rules from `decision_engine/decision_rules.md`

## 7. Final Export

Final export is allowed only on the main trusted computer after:

- A/B/C candidate review
- No severe over-denoise
- No broken consonants
- No unacceptable phase smear
- QC report exists
- Final decision report exists
