#!/usr/bin/env python3
"""Smoke test policy generation."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> None:
    subprocess.run([sys.executable, script], cwd=str(ROOT), check=True)


if __name__ == "__main__":
    run("08_TESTS/test_feature_extraction.py")
    run("03_POLICY_ENGINE/compare_current_to_reference.py")
    run("03_POLICY_ENGINE/generate_mix_policy.py")
    run("03_POLICY_ENGINE/generate_master_policy.py")
    run("02_ANALYSIS/loudness_codec_qc.py")
    run("04_REAPER_AUTOMATION/create_ab_previews.py")
    for name in ["mix_policy.json", "master_policy.json"]:
        data = json.loads((ROOT / "03_POLICY_ENGINE" / name).read_text(encoding="utf-8"))
        assert data["policy"]
        for key, value in data["policy"].items():
            assert "reason" in value and value["reason"], f"{key} missing reason"
    mp3_check = ROOT / "06_OUTPUTS" / "mp3_check"
    shutil.rmtree(mp3_check, ignore_errors=True)
    run("02_ANALYSIS/loudness_codec_qc.py")
    qc_result = json.loads((ROOT / "06_OUTPUTS" / "logs" / "qc_result.json").read_text(encoding="utf-8"))
    mp3_encode = qc_result.get("mp3_encode", {})
    assert mp3_encode.get("created") or mp3_encode.get("errors") or list(mp3_check.glob("*.mp3")), mp3_encode
    print("policy generation smoke test passed")
