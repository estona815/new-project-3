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
- High-pass only if needed
- Dynamic de-fizz
- De-ess
- Resonance control
- Parallel restore bus
- Light saturation or harmonic restore
- Final blend bus

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

## 7. Final Export

Final export is allowed only on the main trusted computer after:

- A/B/C candidate review
- No severe over-denoise
- No broken consonants
- No unacceptable phase smear
- QC report exists

