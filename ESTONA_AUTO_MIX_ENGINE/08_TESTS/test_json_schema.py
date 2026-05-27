#!/usr/bin/env python3
"""Validate generated policies against required reason-bearing structure."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_policy(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("engine") == "ESTONA_AUTO_MIX_ENGINE"
    assert data.get("mode") in {"conservative", "normal", "aggressive"}
    assert isinstance(data.get("policy"), dict) and data["policy"]
    for key, spec in data["policy"].items():
        assert isinstance(spec, dict), key
        assert "value" in spec, key
        assert isinstance(spec.get("reason"), str) and spec["reason"].strip(), key


if __name__ == "__main__":
    subprocess.run([sys.executable, "08_TESTS/test_policy_generation.py"], cwd=str(ROOT), check=True)
    for path in (ROOT / "03_POLICY_ENGINE").glob("*policy*.json"):
        if path.name == "policy_schema.json":
            continue
        validate_policy(path)
    print("json schema smoke test passed")
