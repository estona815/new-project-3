from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from release_master_targets import build_release_master_target, normalize_release_master_target, release_master_verified  # noqa: E402


class ReleaseMasterTargetsTests(unittest.TestCase):
    def test_release_ready_defaults_to_streaming_safe(self) -> None:
        self.assertEqual(normalize_release_master_target(None, release_ready=True), "streaming_safe")
        target = build_release_master_target("streaming_safe", release_ready=True)

        self.assertEqual(target["character"], "safe peak target")
        self.assertIn("no clipping", " ".join(target["rules"]))

    def test_loud_demo_warns_not_default_release_master(self) -> None:
        target = build_release_master_target("loud_demo")

        self.assertFalse(target["default_for_release"])
        self.assertIn("Reduced headroom", target["warning"])

    def test_release_master_verified_requires_final_verify_and_reports(self) -> None:
        failed = release_master_verified(
            final_verify_result={"ok": False, "format_verified": False, "clipping_count": 0},
            qc_report_exists=False,
            release_checklist_exists=False,
            require_release_checklist=True,
        )
        passed = release_master_verified(
            final_verify_result={"ok": True, "format_verified": True, "clipping_count": 0},
            qc_report_exists=True,
            release_checklist_exists=True,
            require_release_checklist=True,
        )

        self.assertFalse(failed["verified"])
        self.assertIn("final_verify", " ".join(failed["blocking_reasons"]))
        self.assertTrue(passed["verified"])


if __name__ == "__main__":
    unittest.main()
