from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from automation_guide import build_automation_guide  # noqa: E402


class AutomationGuideTests(unittest.TestCase):
    def test_automation_guide_covers_required_categories_without_claims(self) -> None:
        guide = build_automation_guide(
            {
                "section_progression_guide": {
                    "sections": [
                        {"name": "intro", "start": 0.0},
                        {"name": "hook_drop", "start": 8.0},
                        {"name": "contrast", "start": 24.0},
                        {"name": "final_hook", "start": 40.0},
                    ]
                }
            }
        )
        text = json.dumps(guide).lower()

        self.assertEqual(guide["schema_version"], "automation_guide.v1")
        self.assertIn("filter movement", text)
        self.assertIn("808 pauses", text)
        self.assertIn("vocal delay throw", text)
        self.assertFalse(guide["claim_guard"]["automation_written_to_logic"])
        self.assertFalse(guide["claim_guard"]["plugins_inserted"])


if __name__ == "__main__":
    unittest.main()
