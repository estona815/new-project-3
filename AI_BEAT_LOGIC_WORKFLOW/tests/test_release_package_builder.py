from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from completion_gate import check_completion_status  # noqa: E402
from export_audio import write_float_wav  # noqa: E402
from release_package_builder import build_and_write_release_package, build_release_manifest  # noqa: E402


def complete_metadata() -> dict[str, object]:
    return {
        "title": "Release Track",
        "artist": "Artist",
        "version": "final",
        "genre": "digicore",
        "language": "ko",
        "explicit": False,
        "isrc": "",
        "upc": "",
        "copyright_year": "2026",
        "copyright_owner": "Artist",
        "producer": "Producer",
        "composer": "Composer",
        "lyricist": "",
        "featured_artists": [],
    }


def clear_rights() -> dict[str, object]:
    return {
        "contains_samples": False,
        "source_ownership_confirmed": True,
        "vocal_performer_consent": True,
        "featured_artist_metadata_complete": True,
        "explicit_content_flag_set": True,
    }


class ReleasePackageBuilderTests(unittest.TestCase):
    def test_builds_ready_release_package_with_verified_final_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "05_FINAL_WAV" / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)

            result = build_and_write_release_package(
                root,
                final_master_path=final,
                metadata=complete_metadata(),
                rights=clear_rights(),
                requested_format="wav24_48k",
            )
            manifest = result["manifest"]
            manifest_path = result["paths"]["manifest"]
            written = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertTrue(manifest["release_ready"])
            self.assertEqual(written["schema_version"], "release_manifest.v1")
            self.assertTrue(Path(written["final_master"]["path"]).exists())
            self.assertEqual(written["final_master"]["sample_rate"], 48000)
            self.assertEqual(written["final_master"]["bit_depth"], 24)
            self.assertEqual(written["final_master"]["channels"], 2)
            self.assertEqual(written["final_master"]["clipping_count"], 0)
            self.assertTrue((root / "10_RELEASE_PACKAGE" / "deliverables" / "final_master.wav").exists())
            self.assertTrue(result["paths"]["release_qc_report"].exists())
            self.assertTrue((root / "10_RELEASE_PACKAGE" / "cover_art_requirements.md").exists())

    def test_missing_metadata_generates_draft_package_not_release_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)

            result = build_and_write_release_package(
                root,
                final_master_path=final,
                metadata={"title": "Draft"},
                rights=clear_rights(),
            )

            self.assertFalse(result["manifest"]["release_ready"])
            self.assertIn("required release metadata is incomplete", result["manifest"]["qc"]["blocking_issues"])
            self.assertTrue(result["paths"]["metadata_json"].exists())
            self.assertTrue(result["paths"]["distribution_checklist"].exists())

    def test_unclear_sample_rights_blocks_release_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)

            manifest = build_release_manifest(
                package_dir=root / "10_RELEASE_PACKAGE",
                final_master_path=final,
                metadata=complete_metadata(),
                rights={**clear_rights(), "contains_samples": True, "all_samples_owned_or_cleared": None},
            )

            self.assertFalse(manifest["release_ready"])
            self.assertIn("samples are used", " ".join(manifest["qc"]["blocking_issues"]))

    def test_completion_gate_reads_release_qc_blockers_from_new_manifest_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            qc = root / "qc_report.md"
            master = root / "master_qc_report.md"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            qc.write_text("qc\n", encoding="utf-8")
            master.write_text("master qc\n", encoding="utf-8")
            result = build_and_write_release_package(root, final_master_path=final, metadata={"title": "Draft"}, rights=clear_rights())

            status = check_completion_status(
                final_wav_path=final,
                qc_report_path=qc,
                requested_format="wav24_48k",
                require_master_qc=True,
                master_qc_report_path=master,
                require_release_package=True,
                release_package_manifest_path=result["paths"]["manifest"],
                release_qc_report_path=result["paths"]["release_qc_report"],
            )

            self.assertFalse(status.complete)
            self.assertIn("required release metadata is incomplete", " ".join(status.blocking_reasons))


if __name__ == "__main__":
    unittest.main()
