from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from release_metadata import build_release_metadata_payload, normalize_release_metadata, write_release_metadata_files  # noqa: E402


class ReleaseMetadataTests(unittest.TestCase):
    def test_missing_metadata_creates_draft_payload_without_inventing_codes(self) -> None:
        payload = build_release_metadata_payload({"title": "Demo"})

        self.assertFalse(payload["complete"])
        self.assertIn("artist", payload["missing_fields"])
        self.assertEqual(payload["metadata"]["isrc"], "")
        self.assertEqual(payload["metadata"]["upc"], "")

    def test_complete_metadata_requires_explicit_boolean(self) -> None:
        metadata = normalize_release_metadata(
            {
                "title": "Track",
                "artist": "Artist",
                "genre": "digicore",
                "language": "ko",
                "explicit": False,
                "copyright_year": "2026",
                "copyright_owner": "Artist",
                "producer": "Producer",
                "composer": "Composer",
            }
        )
        payload = build_release_metadata_payload(metadata)

        self.assertTrue(payload["complete"])
        self.assertEqual(payload["metadata"]["explicit"], False)

    def test_write_metadata_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = build_release_metadata_payload({"title": "Draft"})
            paths = write_release_metadata_files(tmp, payload)

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            self.assertIn("not provided", paths["markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
