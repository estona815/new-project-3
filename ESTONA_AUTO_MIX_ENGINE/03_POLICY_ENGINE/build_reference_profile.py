#!/usr/bin/env python3
"""Wrapper for building the estona reference profile."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_ANALYSIS"))

from reference_feature_extractor import build_reference_features


if __name__ == "__main__":
    result = build_reference_features()
    print(f"built reference profile: {result.get('status')}")
