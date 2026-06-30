# QC Targets

QC reports are written to `work/qc/qc_report.json` and `reports/QC_REPORT.md`.

## Targets

- Integrated LUFS: -10.5 to -8.0 LUFS
- True peak: <= -1.0 dBTP when true-peak measurement is available
- Sample peak: <= -1.0 dBFS recommended
- L/R RMS difference: <= 0.5 dB
- Stereo correlation: >= 0.25
- Mono fold-down peak: <= -1.0 dBFS
- Mono loudness delta: within +/- 1.0 dB recommended
- Harshness band 2.5 kHz to 6 kHz: not excessive versus full-spectrum energy
- Sibilance band 5 kHz to 10 kHz: not excessive versus full-spectrum energy
- Male active segment RMS must not fall below the configured threshold
- Female vocal must be at least 5 dB below male lead over comparable active segments

Unavailable metrics must be explicit `null` values with a reason. Approximate metrics must be marked approximate.

## Inspection-Stage Retention Policy

- During inspection or user review, retain one latest stem folder per song under
  the latest `audio_work/<project_version>/processed_stems` path.
- During inspection or user review, retain one latest review/master `mp3` per
  song under `renders/`.
- Default retained review export is the `mp3` copy. Do not keep review `wav`,
  ZIP, loudness-variant bundles, or A/B package audio unless the user
  explicitly asks for them.
- If a `wav` export is requested later, generate it from the retained stem
  folder and document that request in QC instead of keeping dormant `wav`
  renders by default.
- QC must still record the retained `mp3` path, measured loudness/peak values,
  and the stem folder used to produce or review that export.
