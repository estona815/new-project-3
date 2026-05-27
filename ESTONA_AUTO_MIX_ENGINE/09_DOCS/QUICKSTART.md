# QUICKSTART

```sh
cd ESTONA_AUTO_MIX_ENGINE
python3 08_TESTS/test_json_schema.py
```

That command generates dummy WAVs, extracts features, creates reference/current profiles, produces mix/master policies, writes QC reports, and verifies every policy item has a `reason`.

After the smoke test, inspect:

- `00_REFERENCES/reference_profiles/estona_reference_profile.json`
- `02_ANALYSIS/current_song_analysis.json`
- `03_POLICY_ENGINE/mix_policy.json`
- `03_POLICY_ENGINE/master_policy.json`
- `07_REPORTS/mix_policy_report.md`
- `07_REPORTS/qc_report.md`
