#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def schema_fields(root: Path) -> list[str]:
    schema = root / "decision_engine" / "candidate_scoring_schema.yml"
    fields: list[str] = []
    for raw in schema.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- "):
            fields.append(line[2:].strip())
    return fields


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    fields = schema_fields(root)
    examples = [
        {
            "candidate_id": "A",
            "source_type": "dummy",
            "denoise_method": "minimal",
            "dynamic_eq_method": "light",
            "deess_method": "light",
            "body_restore_method": "none",
            "parallel_blend_percent": 15,
            "lufs_integrated": -16.0,
            "true_peak_db": -1.5,
            "rms": -20.0,
            "crest_factor": 10.2,
            "sibilance_energy_6_10k": "low",
            "fizz_energy_12_16k": "medium",
            "low_mid_mud_200_500": "low",
            "spectral_centroid": "placeholder",
            "noise_floor_estimate": "placeholder",
            "phase_risk": "low",
            "vocal_thinning_risk": "low",
            "metallic_artifact_risk": "low",
            "watery_artifact_risk": "low",
            "consonant_damage_risk": "low",
            "subjective_notes": "Dummy candidate retains natural tone.",
            "final_rank": 1,
            "decision": "example_winner",
        }
    ]
    report_dir = root / "examples" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "candidate_score_placeholder.json").write_text(json.dumps({"schema_fields": fields, "candidates": examples}, indent=2) + "\n", encoding="utf-8")
    (report_dir / "candidate_score_placeholder.md").write_text(
        "# Candidate Score Placeholder\n\n"
        "- Data source: dummy values only\n"
        "- Best candidate: A\n"
        "- Decision: example_winner\n"
        "- Real audio scoring must run only on the main computer with local_only inputs.\n",
        encoding="utf-8",
    )
    print("[ok] Wrote placeholder candidate score reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

