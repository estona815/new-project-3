# Vocal Clarity Repair System

Purpose: remove low-mid fog, improve lead-vocal diction, keep AI/Suno fizz controlled, and keep the lead centered/forward without turning it into a brittle pop vocal.

Workflow:
1. Run `python3 scripts/analyze_vocal_stem.py <vocal-file>`.
2. Run `python3 scripts/generate_reaper_fx_chains.py` to refresh `.RfxChain` templates.
3. In REAPER, run `scripts/apply_vocal_clarity_chain.lua`.
4. Render with `scripts/render_vocal_clarity_pass.lua`.
5. Run `python3 scripts/qc_vocal_clarity.py <before> <after>`.

Main adjustment points if the vocal fails QC:
- Too thin: reduce De-Mud max reduction or HPF frequency.
- Too sharp: lower presence boost or raise harsh guard.
- Too AI/fizzy: disable air lift and increase air guard.
- Too far back: lower reverb send and add a small instrumental 2-4 kHz pocket.
