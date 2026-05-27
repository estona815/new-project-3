#!/usr/bin/env python3
"""Optional Matchering design experiment placeholder.

This script intentionally does not call Matchering by default. The audited
Matchering repo is GPL-3.0, so ESTONA uses it as study-only design input unless
the user explicitly opts into a separate experiment and accepts license review.
"""

from audio_utils import resolve_path, write_json


def write_experiment_plan() -> dict:
    plan = {
        "status": "study_only_not_executed",
        "reason": "Matchering is useful for reference/target architecture, but GPL-3.0 code is not merged into ESTONA.",
        "possible_experiment": [
            "Compare reference and target frequency-response curves.",
            "Store delta curves as abstract profile data.",
            "Do not render final masters through Matchering by default.",
            "Do not copy musical content from reference tracks.",
        ],
        "output_if_enabled_later": "02_ANALYSIS/matchering_reference_experiment_result.json",
    }
    write_json(resolve_path("02_ANALYSIS", "matchering_reference_experiment_plan.json"), plan)
    return plan


if __name__ == "__main__":
    print(f"matchering experiment: {write_experiment_plan().get('status')}")
