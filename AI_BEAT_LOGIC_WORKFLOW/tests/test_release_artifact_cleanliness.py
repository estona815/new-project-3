from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from release_package_builder import build_and_write_release_package  # noqa: E402
from test_release_ready_workflow_integration import clear_rights  # noqa: E402


class ReleaseArtifactCleanlinessTests(unittest.TestCase):
    def test_release_package_builder_writes_only_inside_temp_root(self) -> None:
        before = _repo_generated_artifacts()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = build_and_write_release_package(root, final_master_path=None, metadata={"title": "Draft"}, rights=clear_rights())
            self.assertTrue(package["paths"]["manifest"].is_relative_to(root))
            self.assertTrue((root / "10_RELEASE_PACKAGE" / "release_manifest.json").exists())
        after = _repo_generated_artifacts()

        self.assertEqual(before, after)


def _repo_generated_artifacts() -> list[str]:
    patterns = ("*.wav", "*.aif", "*.aiff", "*.mp3", "*.mid", "*.midi", "*.log")
    found: list[str] = []
    for pattern in patterns:
        found.extend(str(path.relative_to(PROJECT_ROOT)) for path in PROJECT_ROOT.rglob(pattern) if ".git" not in path.parts)
    found.extend(
        str(path.relative_to(PROJECT_ROOT))
        for path in PROJECT_ROOT.rglob("*report*.json")
        if ".git" not in path.parts and ".test_artifacts" not in path.parts
    )
    found.extend(str(path.relative_to(PROJECT_ROOT)) for path in PROJECT_ROOT.rglob(".test_artifacts") if ".git" not in path.parts)
    return sorted(found)


if __name__ == "__main__":
    unittest.main()
