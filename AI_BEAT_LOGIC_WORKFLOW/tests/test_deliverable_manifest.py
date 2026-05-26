from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from deliverable_manifest import build_deliverable_manifest, deliverable_by_type  # noqa: E402
from export_audio import write_float_wav  # noqa: E402


class DeliverableManifestTests(unittest.TestCase):
    def test_copies_only_available_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.wav"
            preview = root / "preview.mp3"
            write_float_wav(source, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            preview.write_bytes(b"mp3-preview")

            manifest = build_deliverable_manifest(
                package_dir=root / "10_RELEASE_PACKAGE",
                final_master_path=source,
                optional_deliverables={"mp3_preview": preview, "acapella": root / "missing.wav"},
            )

            final_item = deliverable_by_type(manifest, "final_master")
            preview_item = deliverable_by_type(manifest, "mp3_preview")
            acapella_item = deliverable_by_type(manifest, "acapella")
            self.assertTrue(final_item["available"])
            self.assertTrue(Path(final_item["path"]).exists())
            self.assertTrue(preview_item["available"])
            self.assertFalse(acapella_item["available"])

    def test_missing_final_master_is_required_but_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_deliverable_manifest(package_dir=Path(tmp) / "pkg", final_master_path=None)
            final_item = deliverable_by_type(manifest, "final_master")

            self.assertTrue(final_item["required"])
            self.assertFalse(final_item["available"])


if __name__ == "__main__":
    unittest.main()
