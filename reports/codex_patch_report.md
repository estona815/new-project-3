
# Codex Patch Report

- Harness patched to v0.5 for Suno Studio stem/MIDI to REAPER production workflow.
- Changed/added classifier, QC, plugin inventory, reference comparison, MIDI cleanup, REAPER session generation, prompt payload, and planning reports.
- Plugin behavior: scans safe REAPER/AU/VST locations when available; uses configured preferred plugins if detected; falls back to REAPER stock/JS/ffmpeg options without hard failure.
- Fallback roles this run: compressor_clean, multiband_compressor, reverb_plate, reverb_room, delay, limiter, loudness_meter, noise_reduction.
- Source classification: MP3/master/fullmix files are `problem_reference` or `reference_only`; WAV stems can be production tracks unless named master/fullmix/reference; MIDI is `guide_midi`; AI vocal chops are quarantined.
- Reference comparison: current available `true`, technical reference available `false`.
- Audio QC: 208 issues detected; high/critical or marker-flagged issues become REAPER markers.
- Vocal repair strategy: centered lead, pitch correction before dynamic EQ, de-essing around 5.5-9 kHz, serial compression, tone EQ, light saturation, filtered sends.
- Autotune strategy: use detected pitch plugin or ReaTune fallback; lock key only when reliable; severe AI pitch/formant artifacts require regeneration or manual re-recording.
- Dynamic EQ strategy: control mud, harshness, sibilance, and music masking around 1-5 kHz without dull static cuts.
- Reverb/delay strategy: send-based plate, short room, tempo-synced delay throws, filtered and ducked.
- M/S EQ strategy: mono low end below 120 Hz, reduce side low-mids, keep lead/bass mid, widen only safe synth/BGV ranges.
- Mix/master strategy: premaster first, conservative master second, true peak target -1.0 dBTP, avoid crushed LRA 2-3 style masters.
- Render targets: `renders/PREMASTER_24bit_48k.wav`, `renders/MASTER_24bit_48k.wav`, optional `renders/MASTER_320k.mp3`.
- Known limitations: Codex generated scripts and reports but did not run REAPER or verify a REAPER render in this patch. Premium plugin insertion cannot be claimed until verified inside REAPER.
- Manual next steps: run `reaper/launch_reaper.sh`, inspect plugin insertions, check QC markers, tune the lead vocal, confirm sends, render premaster/master, then update `reports/render_report.md`.
