
-- Harness v0.5 supplemental mix-chain notes.
-- Run build_project.lua first. This file is intentionally conservative and non-destructive.
-- If a premium plugin failed insertion, insert the fallback listed in reports/manual_plugin_notes.md.
-- Lead vocal chain: cleanup EQ -> pitch correction -> dynamic EQ -> de-esser -> serial compression -> tone EQ -> light saturation -> sends.
-- MUSIC_BUS: dynamic EQ/M/S EQ for vocal pocket around 1-5 kHz and side low-mid control.
-- VOCAL_PLATE_SEND: 20-35 ms predelay, 0.8-1.6 s decay, HPF 180-250 Hz, LPF 7-10 kHz, ducked.
-- VOCAL_DELAY_SEND: dotted 1/8 or 1/4, HPF 150-250 Hz, LPF 5.5-8 kHz, phrase throws only.
reaper.ShowMessageBox("Apply/check v0.5 mix chains using reports/manual_plugin_notes.md and reports/*_plan.md. No destructive processing was applied.", "Suno REAPER Harness v0.5", 0)
