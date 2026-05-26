from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reference_source_policy import (  # noqa: E402
    classify_source,
    combined_confidence,
    normalize_source,
    sanitize_claim,
    trait_inference_allowed_from_sources,
)


class ReferenceSourcePolicyTests(unittest.TestCase):
    def test_classifies_source_priority(self) -> None:
        self.assertEqual(classify_source("https://artist.example/official", "Official artist page"), "official_artist")
        self.assertEqual(classify_source("https://example.com/remake-tutorial", "808 remake tutorial"), "tutorial")
        self.assertEqual(classify_source("https://pitchfork.com/reviews/albums/test", "review"), "review")

    def test_sanitizes_to_high_level_claims_only(self) -> None:
        self.assertEqual(sanitize_claim("bright digital drums and punchy 808"), "bright digital drums and punchy 808")
        self.assertIsNone(sanitize_claim("lyrics: a very specific quoted line"))
        self.assertIsNone(sanitize_claim("copy this pattern exactly"))

    def test_tutorial_sources_are_lower_confidence_non_canonical(self) -> None:
        source = normalize_source(
            {
                "title": "Love Blur remake tutorial",
                "url_or_id": "https://video.example/tutorial",
                "source_type": "tutorial",
                "relevant_claims": ["punchy digital drums and bright hats"],
            },
            "2026-05-17T00:00:00+00:00",
        )

        self.assertEqual(source["confidence"], "low")
        self.assertIn("tutorial/remake source is not canonical", source["limitations"])
        self.assertEqual(combined_confidence([source]), "low")

    def test_official_streaming_existence_only_does_not_allow_trait_inference(self) -> None:
        source = normalize_source(
            {
                "title": "Westwood - JUST TOUCHED DOWN",
                "url_or_id": "https://open.spotify.com/track/example",
                "source_type": "official_streaming",
                "relevant_claims": ["track exists on streaming profile"],
            },
            "2026-05-17T00:00:00+00:00",
        )

        self.assertEqual(source["confidence"], "medium")
        self.assertTrue(source["existence_only"])
        self.assertEqual(source["relevant_claims"], [])
        self.assertIn("source only proves artist/track existence", " ".join(source["limitations"]))
        self.assertFalse(trait_inference_allowed_from_sources([source]))

    def test_review_broad_descriptors_allow_medium_trait_inference(self) -> None:
        source = normalize_source(
            {
                "title": "2hollis review",
                "url_or_id": "https://music.example/review",
                "source_type": "review",
                "relevant_claims": ["internet-driven hyperpop and futuristic digital rage rap energy"],
            },
            "2026-05-17T00:00:00+00:00",
        )

        self.assertEqual(source["confidence"], "medium")
        self.assertTrue(trait_inference_allowed_from_sources([source]))


if __name__ == "__main__":
    unittest.main()
