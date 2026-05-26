from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rescue_qc import build_rescue_qc, render_rescue_qc_markdown, write_rescue_qc_report  # noqa: E402


def good_diagnosis() -> dict[str, object]:
    return {
        "input": {"mode": "full_song_stereo", "path": "/tmp/source.wav"},
        "MIX_ONLY_NOT_ENOUGH": True,
        "decision": "ARRANGEMENT_REBUILD_REQUIRED",
        "rescue_decision": {
            "mix_only_not_enough": True,
            "lead_melody_required": True,
            "hook_identity_required": True,
            "arrangement_rebuild_required": True,
            "vocal_texture_cleanup_required": True,
        },
        "stereo_claim_guard": {
            "stem_level_remix_claimed": False,
            "vocal_removal_claimed": False,
            "plugin_insertion_claimed": False,
        },
    }


def good_arrangement() -> dict[str, object]:
    return {
        "schema_version": "rescue_arrangement_plan.v1",
        "length_mode": "short_30sec",
        "target_duration_seconds": 30.0,
        "hook_appears_by_seconds": 4.0,
        "sections": [
            {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3},
            {"name": "main_hook", "start_time": 4.0, "duration": 8.0, "energy": 5},
            {"name": "verse_groove", "start_time": 12.0, "duration": 8.0, "energy": 2},
            {"name": "hook_return", "start_time": 20.0, "duration": 8.0, "energy": 5},
            {"name": "clean_outro_or_loop", "start_time": 28.0, "duration": 2.0, "energy": 1},
        ],
        "remove_or_reduce": ["random glitch fills", "repeated AI loop blocks"],
        "manual_logic_required": [
            "True stem-level rewrite requires stems or manual Logic editing.",
            "New lead MIDI/synth may need manual confirmation.",
        ],
    }


def good_lead() -> dict[str, object]:
    return {
        "schema_version": "lead_melody_plan.v1",
        "status": "LEAD_MELODY_PLAN_READY",
        "motifs": [
            {"motif_id": "lead_A", "notes": [{"note": "F#4"}]},
            {"motif_id": "response_B", "notes": [{"note": "A4"}]},
        ],
        "hook_motif_summary": {
            "primary_motif_id": "lead_A",
            "repetition": {"has_repetition": True, "has_variation": True},
        },
    }


def good_hook() -> dict[str, object]:
    return {
        "schema_version": "hook_identity_plan.v1",
        "status": "HOOK_IDENTITY_PLAN_READY",
        "motif_repetition_quality": "structured_repeat_with_variation",
    }


def good_vocal_plan() -> dict[str, object]:
    return {
        "schema_version": "vocal_texture_rescue_plan.v1",
        "detected_issues": [{"start": 1.0, "end": 2.0, "issue": "fake_vocal_chop_dominates_lead"}],
        "actions": [{"type": "demote_texture"}],
        "limitations": ["Stereo-only source cannot fully remove vocal texture."],
        "claim_guard": {"vocal_removal_claimed": False, "stem_level_control_from_stereo_claimed": False},
    }


def good_sample_plan() -> dict[str, object]:
    return {
        "schema_version": "sample_motif_rebuild_plan.v1",
        "status": "SAMPLE_MOTIF_REBUILD_PLAN_READY",
        "selected_samples": [
            {"sample_id": "sample_01", "role": "main_motif"},
            {"sample_id": "sample_02", "role": "response_motif"},
        ],
        "quality_gates": {"main_motif_returns_in_hook": True, "no_random_chop_spam": True},
    }


def good_mix() -> dict[str, object]:
    return {
        "bus_reports": {
            "source_music_bus": {"restructure_applied": True},
            "generated_lead_bus": {"new_lead_hook_rendered": True},
            "sample_motif_bus": {"created": True},
            "vocal_texture_bus": {"created": True},
            "mid_side": {"created": True},
        },
        "metrics": {"peak_dbfs": -3.2, "rms_dbfs": -14.0, "clipping_count": 0, "side_mid_db": -16.0},
        "claim_guard": {
            "stem_level_remix_claimed": False,
            "vocal_removal_claimed": False,
            "plugin_insertion_claimed": False,
            "logic_automation_success_claimed": False,
        },
    }


def demo_verification() -> dict[str, object]:
    return {"exists": True, "sample_rate": 48000, "channels": 2, "bit_depth": 24, "peak_dbfs": -3.1, "clipping_count": 0}


def final_verification(ok: bool = True) -> dict[str, object]:
    return {
        "exists": True,
        "ok": ok,
        "format_verified": ok,
        "sample_rate": 48000 if ok else 44100,
        "bit_depth": 24 if ok else 16,
        "channels": 2,
        "peak_dbfs": -1.2,
        "rms_dbfs": -13.0,
        "clipping_count": 0,
        "errors": [] if ok else ["wrong format"],
    }


def base_kwargs() -> dict[str, object]:
    return {
        "diagnosis": good_diagnosis(),
        "arrangement_plan": good_arrangement(),
        "lead_plan": good_lead(),
        "hook_plan": good_hook(),
        "vocal_texture_plan": good_vocal_plan(),
        "sample_motif_plan": good_sample_plan(),
        "mix_report": good_mix(),
    }


class RescueQCTests(unittest.TestCase):
    def test_plan_ready_has_no_complete_without_final_wav(self) -> None:
        qc = build_rescue_qc(**base_kwargs(), qc_report_exists=True)

        self.assertEqual(qc["verdict"], "RESCUE_PLAN_READY")
        self.assertFalse(qc["complete_allowed"])
        self.assertIn("plan exists", " ".join(qc["blocking_reasons"]))

    def test_demo_ready_is_distinct_from_final_pass(self) -> None:
        qc = build_rescue_qc(**base_kwargs(), demo_verification=demo_verification(), qc_report_exists=True)

        self.assertEqual(qc["verdict"], "RESCUE_DEMO_READY")
        self.assertFalse(qc["complete_allowed"])
        self.assertTrue(qc["technical"]["demo_verified"])
        self.assertFalse(qc["technical"]["final_verified"])

    def test_final_rescue_pass_requires_final_verification_qc_and_gate(self) -> None:
        qc = build_rescue_qc(
            **base_kwargs(),
            demo_verification=demo_verification(),
            final_verification=final_verification(True),
            completion_gate=SimpleNamespace(complete=True, blocking_reasons=[]),
            qc_report_exists=True,
        )

        self.assertEqual(qc["verdict"], "FINAL_RESCUE_PASS")
        self.assertTrue(qc["complete_allowed"])
        self.assertTrue(qc["technical"]["final_verified"])

    def test_qc_blocks_pass_if_no_lead_hook_improvement(self) -> None:
        weak_lead = {"schema_version": "lead_melody_plan.v1", "motifs": []}
        weak_hook = {"schema_version": "hook_identity_plan.v1", "motif_repetition_quality": "needs_revision"}
        weak_mix = good_mix()
        weak_mix["bus_reports"]["generated_lead_bus"] = {"new_lead_hook_rendered": False}
        qc = build_rescue_qc(
            **{**base_kwargs(), "lead_plan": weak_lead, "hook_plan": weak_hook, "mix_report": weak_mix},
            final_verification=final_verification(True),
            completion_gate=SimpleNamespace(complete=True, blocking_reasons=[]),
            qc_report_exists=True,
        )

        self.assertEqual(qc["verdict"], "NEEDS_RECOMPOSITION")
        self.assertFalse(qc["complete_allowed"])
        self.assertIn("lead/hook still weak", qc["blocking_reasons"])

    def test_unsafe_claims_fail_reprocess(self) -> None:
        unsafe_mix = good_mix()
        unsafe_mix["claim_guard"]["vocal_removal_claimed"] = True
        qc = build_rescue_qc(
            **{**base_kwargs(), "mix_report": unsafe_mix},
            demo_verification=demo_verification(),
            qc_report_exists=True,
        )

        self.assertEqual(qc["verdict"], "FAIL_REPROCESS")
        self.assertFalse(qc["complete_allowed"])
        self.assertIn("vocal_removal_claimed", qc["unsafe_claims"])

    def test_stereo_only_blocked_vocal_rewrite_needs_manual_logic(self) -> None:
        bad_vocal = {
            "detected_issues": [{"issue": "fake_vocal_chop_dominates_lead", "start": 0, "end": 4}],
            "actions": [],
            "limitations": ["Stereo-only source cannot fully remove vocal texture."],
        }
        no_demote_mix = good_mix()
        no_demote_mix["bus_reports"]["vocal_texture_bus"] = {"created": False}
        qc = build_rescue_qc(
            **{**base_kwargs(), "vocal_texture_plan": bad_vocal, "mix_report": no_demote_mix},
            demo_verification=demo_verification(),
            qc_report_exists=True,
        )

        self.assertEqual(qc["verdict"], "NEEDS_MANUAL_LOGIC")
        self.assertIn("stereo-only source prevents needed rewrite", qc["blocking_reasons"])

    def test_report_contains_required_questions(self) -> None:
        qc = build_rescue_qc(**base_kwargs(), demo_verification=demo_verification(), qc_report_exists=True)
        report = render_rescue_qc_markdown(qc, rendered_files=["/tmp/rescue_demo.wav"])

        self.assertIn("Did the result gain a clear lead?", report)
        self.assertIn("Did the hook appear early?", report)
        self.assertIn("Did sections become intentional?", report)
        self.assertIn("Did weird vocal texture stop dominating?", report)
        self.assertIn("Did sample motif feel like a hook rather than random chop?", report)
        self.assertIn("Did mix/master pass technical checks?", report)
        self.assertIn("What Remains Manual", report)

    def test_write_rescue_qc_report_outputs_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = write_rescue_qc_report(
                project_root=temp_dir,
                **base_kwargs(),
                demo_verification=demo_verification(),
                rendered_files=["/tmp/rescue_demo.wav"],
            )

            self.assertTrue(result["report_path"].exists())
            self.assertTrue(result["json_path"].exists())
            self.assertEqual(result["qc"]["verdict"], "RESCUE_DEMO_READY")


if __name__ == "__main__":
    unittest.main()
