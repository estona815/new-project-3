# REAPER Vocal Chain Translation

This document translates the initial lesson rules into REAPER chain logic. It is a planning layer, not proof that any plugin is installed or any audio has been processed.

## Default Vocal Chain

1. Gain staging
2. High-pass
3. Light denoise candidate
4. Dynamic EQ
5. De-ess
6. Body restore saturation
7. Gentle compression
8. Parallel original blend
9. Vocal bus trim
10. QC meter

## Chain Logic

### 1. Gain Staging

- Trim the vocal before corrective processing.
- Leave enough headroom for dynamic EQ, de-essing, compression, and candidate rendering.
- Do not use clipping or limiting as input gain control.

Plugin candidates: REAPER track trim, item gain, ReaEQ output trim.

### 2. High-Pass

- Remove only unusable low rumble.
- Avoid thinning the vocal body.
- Recheck in full mix, not solo only.

Plugin candidates: ReaEQ, TDR Nova.

### 3. Light Denoise Candidate

- Start with the least audible denoise setting.
- Reject if the vocal becomes watery, metallic, phasey, or less intelligible.
- Prefer bypass comparison before printing.

Plugin candidates: ReaFIR, Bertom Denoiser Classic.

### 4. Dynamic EQ

- Target harshness, resonance, and AI fizz only when audible.
- Prefer dynamic bands over static broad cuts when the problem is intermittent.

Plugin candidates: TDR Nova, ReaXcomp, ReaEQ automation.

### 5. De-Ess

- Control 6-10 kHz sibilance without breaking consonants.
- Reject if S, T, K, or breath details become lisped or dull.

Plugin candidates: T-De-Esser 2, TDR Nova, ReaXcomp.

### 6. Body Restore Saturation

- Restore density only after cleanup has removed body.
- Keep saturation light and compare against the original emotional tone.

Plugin candidates: Klanghelm IVGI, DC1A, ReaComp.

### 7. Gentle Compression

- Stabilize the vocal so it sits in the beat.
- Avoid flattening phrasing or making breaths jump forward.

Plugin candidates: ReaComp, DC1A.

### 8. Parallel Original Blend

- Blend a quiet original or lightly processed parallel track when cleanup removes realism.
- Keep the blend low enough that noise and artifacts do not return as the dominant feature.

Plugin candidates: REAPER routing, folder track blend, send trim.

### 9. Vocal Bus Trim

- Adjust final vocal bus level after cleanup, dynamics, and space decisions.
- Do not solve masking with volume alone.

Plugin candidates: REAPER fader, automation, trim plugin.

### 10. QC Meter

- Meter the vocal bus and full mix for spectral balance, loudness, and peak risk.
- Use meters to guide questions, not to replace listening.

Plugin candidates: SPAN, Youlean, LoudMax for preview safety only.

## Plugin Candidate List

- ReaEQ
- ReaFIR
- ReaComp
- ReaXcomp
- Bertom Denoiser Classic
- TDR Nova
- T-De-Esser 2
- Klanghelm IVGI
- DC1A
- SPAN
- Youlean
- LoudMax
