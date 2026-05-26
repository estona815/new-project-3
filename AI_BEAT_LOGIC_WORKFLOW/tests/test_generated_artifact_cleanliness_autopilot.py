from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from autopilot_qc_report import build_autopilot_qc, write_autopilot_qc_reports  # noqa: E402


class GeneratedArtifactCleanlinessAutopilotTests(unittest.TestCase):
    def test_autopilot_reports_written_in_temp_dir_do_not_dirty_repo_status(self) -> None:
        before = subprocess.run(["git", "status", "--short", "--", "06_QC_REPORT", "09_MIX_MASTER", "tests/fixtures"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True).stdout
        with tempfile.TemporaryDirectory() as tmp:
            payload = build_autopilot_qc(arrangement_plan={}, mix_master_plan={})
            paths = write_autopilot_qc_reports(tmp, payload)
            self.assertTrue(paths["autopilot_qc_report"].exists())
        after = subprocess.run(["git", "status", "--short", "--", "06_QC_REPORT", "09_MIX_MASTER", "tests/fixtures"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True).stdout

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
