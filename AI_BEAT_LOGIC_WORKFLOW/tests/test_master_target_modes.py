from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from master_targets import build_master_chain  # noqa: E402


class MasterTargetModesTests(unittest.TestCase):
    def test_master_ready_headroom_is_conservative(self) -> None:
        chain = build_master_chain("master_ready_headroom")

        self.assertEqual(chain["target_mode"], "master_ready_headroom")
        self.assertEqual(chain["peak_target_range_dbfs"], [-3.0, -1.5])
        self.assertEqual(chain["limiting"], "minimal")

    def test_loud_demo_warns_reduced_headroom(self) -> None:
        chain = build_master_chain("loud_demo")

        self.assertEqual(chain["target_mode"], "loud_demo")
        self.assertIn("reduced headroom", chain["warning"])
        self.assertIn("No clipping.", chain["rules"])


if __name__ == "__main__":
    unittest.main()
