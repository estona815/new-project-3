# Mixbus And Master Rules

These rules keep mixbus and preview-master decisions conservative.

## Rules

- Mixbus processing should be conservative. It should polish a working mix, not rescue a broken one.
- Meter before limiting so gain staging, low-end pressure, and true peak risk are visible early.
- Use Youlean and SPAN as QC tools, not tone plugins.
- LoudMax is a safety and preview limiter only unless a trusted main-computer mastering pass confirms the result.
- Do not master a bad mix into sounding fixed. Repair vocal balance, low-end masking, or harshness upstream.
- Preserve transient energy. Reject masters that become loud but flat, smeared, or fatiguing.

## REAPER Translation

- Place meters before and after limiter candidates.
- Print preview masters only after checking the unmastered mix.
- Report limiter role, loudness target, true peak behavior, and audible tradeoffs.
