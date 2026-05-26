from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from production_todo_generator import TODO_ORDER, build_production_todo, render_production_todo  # noqa: E402


class ProductionTodoGeneratorTests(unittest.TestCase):
    def test_todo_order_matches_required_production_flow(self) -> None:
        package = {
            "status": "PRODUCTION_PACKAGE_READY",
            "capabilities": {"stereo_only": True, "stems_available": False},
            "sample_chop_guide": {"direct_sample_use_allowed": False},
            "master_target": "streaming_safe",
            "plugin_requirements": ["Manual plugin insert required"],
        }
        tasks = build_production_todo(package)

        self.assertEqual([task["id"] for task in tasks], [task_id for task_id, _title in TODO_ORDER])
        self.assertEqual(tasks[3]["title"], "program drums")
        self.assertEqual(tasks[4]["title"], "program 808")
        self.assertEqual(tasks[-1]["title"], "build release package")

    def test_stereo_and_plugin_limits_are_marked_manual(self) -> None:
        package = {
            "capabilities": {"stereo_only": True, "stems_available": False},
            "sample_chop_guide": {"direct_sample_use_allowed": False},
            "plugin_requirements": ["Manual plugin insert required unless verified"],
        }
        tasks = build_production_todo(package)
        rendered = render_production_todo({**package, "production_todo": tasks})

        self.assertEqual(tasks[3]["status"], "manual_stems_required")
        self.assertEqual(tasks[5]["status"], "blocked_without_ownership")
        self.assertEqual(tasks[7]["status"], "manual_insert_required")
        self.assertIn("No Logic automation", rendered)


if __name__ == "__main__":
    unittest.main()
