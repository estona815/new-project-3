# mesi_1 v12 Codex Tune/EQ Substitute Final Report

- Actual classification: `vocal_repair_chain_prepared + Codex_tune_EQ_substitute_session`
- RPP: `reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp`
- Session report: `reports/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_codex_tune_eq_substitute_session.json`
- Overall status: `WARN_PLUS_PRESENT`

## What Was Actually Done

- Created a v12 REAPER session from the latest preferred `mesi_1` vocal-stem workflow.
- Inserted the no-paid-plugin substitute chain on the active lead vocal track:
  - `Codex Vocal Pitch Monitor`
  - `ReaTune`
  - `Codex Pro Dynamic MS EQ`
  - `Codex Dynamic EQ Band`
  - `Codex Noise Floor Tamer`
  - `Codex v20 Channel Polish` on the vocal bus
- Audited the RPP text and confirmed the inserted FX are present.
- Ran plugin audit and MIDI/rebeat audit.

## What Was Not Claimed

- Not claimed as `vocal tuned`.
- Not claimed as Antares Auto-Tune quality.
- Not claimed as FabFilter Pro-Q quality.
- Not claimed as `true_rebeat`.
- Not claimed as final mastered audio.

## Evidence

- Session build max severity: `PASS`
- RPP audit max severity: `PASS`
- Plugin audit max severity: `WARN`
- MIDI reconstruction audit max severity: `WARN`
- RPP audit confirmed FX:
  - `JS: codex_fresh_mix/codex_vocal_pitch_monitor.jsfx`
  - `VST: ReaTune (Cockos)`
  - `JS: codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx`
  - `JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx`
  - `JS: codex_fresh_mix/codex_noise_floor_tamer.jsfx`
  - `JS: codex_fresh_mix/codex_v20_channel_polish.jsfx`

## WARN+ Findings

- `WARN JSFX_SMOKE_WARN`: `ESTONA_AUTO_MIX_ENGINE/00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts_Templates/JSFX/GFX/spk77_Basic GFX text.jsfx` has no `desc:` line. This is an external reference JSFX smoke warning, not one of the v12 inserted Codex substitute plugins.
- `WARN REBEAT_BUS_RENDERS_MISSING`: v12 has no drums/bass/music/mix/master bus renders. This blocks any `true_rebeat` or full rebeat claim.

## Exact Next Patch

1. Open the v12 RPP in REAPER.
2. Set ReaTune key/scale/correction parameters deliberately.
3. Render a before/after vocal or mix preview.
4. Run before/after QC and human A/B.
5. Only then allow a limited `vocal tuning applied` claim if the rendered evidence supports it.

## Exact Commands

```bash
python3 -m harness.reaper_project_audit \
  --project reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp \
  --mode vocal_repair \
  --json
```

```bash
python3 -m harness.plugin_audit \
  --project-root . \
  --mode vocal_repair \
  --project reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp \
  --json
```

```bash
python3 -m unittest \
  tests.test_tune_eq_substitute \
  tests.test_harness_smoke \
  tests.test_pipeline_claim_contract \
  tests.test_pipeline_preference_lock
```

