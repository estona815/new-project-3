from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import ensure_folder_structure  # noqa: E402
from style_translation import run_reference_targeting  # noqa: E402
from web_reference_research import collect_web_reference_sources, render_web_reference_summary  # noqa: E402


class WebReferenceResearchTests(unittest.TestCase):
    def test_unavailable_web_research_degrades_to_low_confidence(self) -> None:
        research = collect_web_reference_sources("Nate Sib vocal", web_access_available=False)

        self.assertFalse(research["web_access_available"])
        self.assertTrue(research["web_reference_research_unavailable"])
        self.assertEqual(research["combined_confidence"], "low")
        self.assertEqual(research["sources"], [])
        self.assertFalse(research["trait_inference_allowed"])
        self.assertIn("web access unavailable", " ".join(research["source_limitations"]))

    def test_candidate_sources_are_policy_scored_without_exact_copying(self) -> None:
        research = collect_web_reference_sources(
            "Love Blur drums",
            web_access_available=True,
            source_candidates=[
                {
                    "title": "Official artist profile",
                    "url_or_id": "https://artist.example/official",
                    "source_type": "official_artist",
                    "relevant_claims": ["energetic digital drums with bright hats"],
                },
                {
                    "title": "Remake tutorial",
                    "url_or_id": "https://video.example/remake-tutorial",
                    "source_type": "tutorial",
                    "relevant_claims": ["copy this pattern exactly", "punchy 808 and digital snare"],
                },
            ],
            retrieved_at="2026-05-17T00:00:00+00:00",
        )

        self.assertTrue(research["web_access_available"])
        self.assertFalse(research["web_reference_research_unavailable"])
        self.assertEqual(research["combined_confidence"], "medium")
        self.assertTrue(research["trait_inference_allowed"])
        self.assertEqual(research["sources"][0]["source_type"], "official_artist")
        as_text = json.dumps(research, ensure_ascii=False)
        self.assertNotIn("copy this pattern exactly", as_text)
        self.assertIn("No copyrighted audio", " ".join(research["notes"]))
        self.assertIn("not canonical", render_web_reference_summary(research))

    def test_run_reference_targeting_writes_web_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)

            paths = run_reference_targeting(
                {
                    "reference_text": "내 목소리를 Nate Sib처럼",
                    "web_access_available": True,
                    "web_reference_sources": [
                        {
                            "title": "Interview",
                            "url_or_id": "https://music.example/interview",
                            "source_type": "interview",
                            "relevant_claims": ["bright forward vocal and energetic hyperpop production"],
                        }
                    ],
                },
                project_root,
            )

            self.assertTrue(paths["web_reference_sources"].exists())
            self.assertTrue(paths["web_reference_summary"].exists())
            profile = json.loads(paths["reference_target_profile"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")
            self.assertEqual(profile["source"]["confidence"], "medium")
            self.assertEqual(profile["source"]["support"], "web-informed")
            self.assertIn("vocal", profile["reference_traits"]["target_elements"])
            self.assertFalse(profile["reference_traits"]["vocal"]["identity_clone_allowed"])
            self.assertIn("Evidence Used", translation)
            self.assertIn("No living artist vocal identity clone", translation)

    def test_mock_web_sources_priority_confidence_and_limitations_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)

            paths = run_reference_targeting(
                {
                    "reference_text": "Love Blur 느낌 드럼",
                    "web_access_available": True,
                    "web_reference_sources": [
                        {
                            "title": "Remake tutorial",
                            "url_or_id": "https://video.example/love-blur-remake",
                            "source_type": "tutorial",
                            "relevant_claims": ["copy this pattern exactly", "punchy digital drums and saturated 808"],
                        },
                        {
                            "title": "Official artist page",
                            "url_or_id": "https://artist.example/official",
                            "source_type": "official_artist",
                            "relevant_claims": ["energetic digital drums and bright hook production"],
                        },
                        {
                            "title": "Reputable review",
                            "url_or_id": "https://music.example/review",
                            "source_type": "review",
                            "relevant_claims": ["underground hyperpop energy with active hats"],
                        },
                    ],
                },
                project_root,
            )

            research = json.loads(paths["web_reference_sources"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")
            summary = paths["web_reference_summary"].read_text(encoding="utf-8")

            self.assertEqual(research["sources"][0]["source_type"], "official_artist")
            self.assertEqual(research["sources"][-1]["source_type"], "tutorial")
            self.assertEqual(research["sources"][-1]["confidence"], "low")
            self.assertEqual(research["combined_confidence"], "medium")
            self.assertTrue(research["trait_inference_allowed"])
            self.assertTrue(paths["web_reference_sources"].exists())
            self.assertIn("not a direct audio analysis", translation)
            self.assertIn("not enough evidence for exact sound", translation)
            self.assertIn("web trait inference allowed: true", translation)
            self.assertIn("tutorial/remake source is not canonical", summary)
            self.assertNotIn("copy this pattern exactly", json.dumps(research, ensure_ascii=False))

    def test_westwood_track_existence_does_not_infer_kick_or_bass_from_web_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)

            paths = run_reference_targeting(
                {
                    "reference_text": "웨스트우드 Just Touched Down 킥 베이스 느낌",
                    "web_access_available": True,
                    "web_reference_sources": [
                        {
                            "title": "Westwood - JUST TOUCHED DOWN",
                            "url_or_id": "https://open.spotify.com/track/example",
                            "source_type": "official_streaming",
                            "relevant_claims": ["track exists on streaming profile"],
                        }
                    ],
                },
                project_root,
            )

            research = json.loads(paths["web_reference_sources"].read_text(encoding="utf-8"))
            profile = json.loads(paths["reference_target_profile"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")

            self.assertEqual(research["combined_confidence"], "medium")
            self.assertFalse(research["trait_inference_allowed"])
            self.assertEqual(profile["source"]["confidence"], "low")
            self.assertEqual(profile["source"]["support"], "web-metadata-only")
            self.assertIn("existence only", " ".join(profile["reference_traits"]["evidence_summary"]))
            self.assertIn("reference audio needed for accurate matching: true", translation)
            self.assertIn("source only proves artist/track existence", translation)

    def test_2hollis_system_seoul_ycs_web_descriptors_are_broad_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)

            paths = run_reference_targeting(
                {
                    "reference_text": "좀 더 2hollis처럼, ycs, SYSTEM SEOUL처럼 바꿔줘",
                    "web_access_available": True,
                    "web_reference_sources": [
                        {
                            "title": "2hollis review",
                            "url_or_id": "https://music.example/review",
                            "source_type": "review",
                            "relevant_claims": ["internet-driven hyperpop, off-kilter club, futuristic digital rage rap energy"],
                        },
                        {
                            "title": "SYSTEM SEOUL interview",
                            "url_or_id": "https://music.example/interview",
                            "source_type": "interview",
                            "relevant_claims": ["Korean internet culture nostalgia, 2000s online game meme-influenced digital pop"],
                        },
                        {
                            "title": "ycs social clip",
                            "url_or_id": "https://tiktok.example/ycs",
                            "source_type": "social",
                            "relevant_claims": ["bright digital hooks and playful but controlled chaos"],
                        },
                    ],
                },
                project_root,
            )

            profile = json.loads(paths["reference_target_profile"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")
            self.assertEqual(profile["source"]["support"], "web-informed")
            self.assertEqual(profile["source"]["confidence"], "medium")
            self.assertIn("whole_style", profile["reference_traits"]["target_elements"])
            self.assertFalse(profile["reference_traits"]["vocal"]["identity_clone_allowed"])
            self.assertIn("No exact artist/producer clone", translation)
            self.assertIn("web trait inference allowed: true", translation)

    def test_placeholder_reference_does_not_lookup_or_raise_confidence(self) -> None:
        research = collect_web_reference_sources("ㅇㅇㅇ", web_access_available=True)

        self.assertTrue(research["web_access_available"])
        self.assertEqual(research["sources"], [])
        self.assertEqual(research["combined_confidence"], "low")
        self.assertFalse(research["trait_inference_allowed"])
        self.assertIn("placeholder", " ".join(research["source_limitations"]))

    def test_reference_targeting_uses_temp_project_root_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)

            paths = run_reference_targeting({"reference_text": "ㅇㅇㅇ 느낌 드럼으로 수정"}, project_root)

            for path in paths.values():
                self.assertTrue(str(path).startswith(str(project_root)))
            self.assertFalse((PROJECT_ROOT / "08_REFERENCE_MATCH" / "web_reference_sources.json").exists())
            self.assertFalse((PROJECT_ROOT / "08_REFERENCE_MATCH" / "web_reference_summary.md").exists())


if __name__ == "__main__":
    unittest.main()
