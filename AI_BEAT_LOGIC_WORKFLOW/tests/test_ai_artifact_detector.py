from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from ai_artifact_detector import detect_over_compressed_sections, detect_repeated_ai_loops  # noqa: E402
from transition_detector import detect_abrupt_transitions  # noqa: E402


class AiArtifactDetectorTests(unittest.TestCase):
    def test_repeated_loop_and_transition_candidates(self) -> None:
        features = [
            {"start": 0.0, "end": 2.0, "energy": 0.05, "onset_density": 0.01, "novelty": 0.01},
            {"start": 2.0, "end": 4.0, "energy": 0.051, "onset_density": 0.011, "novelty": 0.001},
            {"start": 4.0, "end": 6.0, "energy": 0.3, "onset_density": 0.03, "novelty": 0.25},
        ]

        repeated = detect_repeated_ai_loops(features)
        transitions = detect_abrupt_transitions(features)

        self.assertTrue(repeated)
        self.assertTrue(transitions)
        self.assertIn("possible repeated AI loop", repeated[0]["reason"])

    def test_over_compressed_section_schema(self) -> None:
        features = [
            {"start": 0.0, "end": 2.0, "energy": 0.3, "onset_density": 0.01, "novelty": 0.0},
            {"start": 2.0, "end": 4.0, "energy": 0.29, "onset_density": 0.01, "novelty": 0.0},
        ]

        candidates = detect_over_compressed_sections(features)

        self.assertTrue(candidates)
        self.assertIn("over-compressed", candidates[0]["reason"])


if __name__ == "__main__":
    unittest.main()
