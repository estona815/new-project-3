from __future__ import annotations

import zipfile
from pathlib import Path

from tools.build_goal02_review_package import annotate_target, copy_file, write_review_checklist, write_review_player
from tools.record_goal02_ab_decision import build_decision_record, verify_review_package


def review_package_fixture(tmp_path: Path) -> dict:
    zip_path = tmp_path / "review.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("GOAL02_USER_AB_REVIEW_CHECKLIST.md", "review")
    return {
        "status": "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL",
        "zip_path": str(zip_path),
        "zip_sha256": "fixture-sha",
        "zip_size_bytes": zip_path.stat().st_size,
        "loudness_rows": [
            {
                "label": "twenty_second_loud_mp3",
                "review_target_kind": "loud",
                "review_target_pass": True,
                "integrated_lufs": -9.29,
                "true_peak_dbtp": -1.01,
            },
            {
                "label": "full_song_safe_mp3",
                "review_target_kind": "safe",
                "review_target_pass": True,
                "integrated_lufs": -12.53,
                "true_peak_dbtp": -1.15,
            },
        ],
    }


def test_review_package_copy_file_is_snapshot_not_hardlink(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    dest = tmp_path / "package" / "source.md"
    source.write_text("first", encoding="utf-8")

    copy_file(source, dest)
    source.write_text("second", encoding="utf-8")

    assert dest.read_text(encoding="utf-8") == "first"


def test_review_package_annotate_target_marks_loud_and_safe_pass() -> None:
    loud = annotate_target({"label": "full_song_loud_mp3", "integrated_lufs": -8.92, "true_peak_dbtp": -2.47})
    safe = annotate_target({"label": "twenty_second_safe_wav", "integrated_lufs": -13.38, "true_peak_dbtp": -2.89})
    failed = annotate_target({"label": "twenty_second_loud_wav", "integrated_lufs": -7.2, "true_peak_dbtp": -0.5})

    assert loud["review_target_kind"] == "loud"
    assert loud["review_target_pass"] is True
    assert safe["review_target_kind"] == "safe"
    assert safe["review_target_pass"] is True
    assert failed["review_target_pass"] is False


def test_review_player_lists_required_mp3_review_assets(tmp_path: Path) -> None:
    rows = []
    for label in [
        "twenty_second_ab_mp3",
        "twenty_second_loud_mp3",
        "twenty_second_safe_mp3",
        "full_song_ab_mp3",
        "full_song_loud_mp3",
        "full_song_safe_mp3",
    ]:
        rows.append(
            {
                "label": label,
                "type": "mp3",
                "package_path": f"audio/mp3/{label}.mp3",
            }
        )
    path = tmp_path / "GOAL02_REVIEW_PLAYER.html"

    write_review_player(
        path,
        {
            "status": "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL",
            "files": rows,
        },
    )

    html = path.read_text(encoding="utf-8")
    assert "GOAL 02 v04 A/B Review" in html
    assert "Current target -> v04 candidate -> ref_06 -> v04 candidate -> ref_07 -> v04 candidate -> ref_03 -> v04 candidate" in html
    assert "audio/mp3/twenty_second_ab_mp3.mp3" in html
    assert "audio/mp3/full_song_safe_mp3.mp3" in html
    assert "python3 tools/record_goal02_ab_decision.py --decision approve_v04_20s_then_extend_final" in html
    assert "approve_v04_20s_then_extend_final" in html
    assert "revise_v04_808_kick" in html
    assert "does not approve audio" in html


def test_review_checklist_includes_ab_order_and_decision_commands(tmp_path: Path) -> None:
    path = tmp_path / "GOAL02_USER_AB_REVIEW_CHECKLIST.md"
    write_review_checklist(
        path,
        {
            "created_at": "2026-06-17T00:00:00Z",
            "status": "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL",
            "files": [
                {
                    "type": "wav",
                    "package_path": "audio/wav/01_20s_AB_current_candidate_primary_refs.wav",
                    "role": "20-second loudness-matched A/B sequence",
                }
            ],
        },
    )

    checklist = path.read_text(encoding="utf-8")
    assert "Current target -> v04 candidate -> ref_06 -> v04 candidate -> ref_07 -> v04 candidate -> ref_03 -> v04 candidate" in checklist
    assert "python3 tools/record_goal02_ab_decision.py --decision pending" in checklist
    assert "python3 tools/record_goal02_ab_decision.py --decision approve_v04_20s_then_extend_final" in checklist
    assert "python3 tools/record_goal02_ab_decision.py --decision revise_v04_hat_sibilance" in checklist
    assert "This checklist does not replace the final WAV/MP3/ZIP delivery gate." in checklist


def test_goal02_pending_decision_keeps_final_delivery_blocked(tmp_path: Path) -> None:
    package = review_package_fixture(tmp_path)
    record = build_decision_record(
        review_package=package,
        decision="pending",
        notes=[],
        reviewed_by="user",
        output_dir=tmp_path,
    )

    assert record["status"] == "USER_AB_DECISION_REQUIRED"
    assert record["ready_for_final_export_prep"] is False
    assert record["safe_to_claim_final_delivery"] is False
    assert "user_loudness_matched_ab_decision_missing" in record["blockers"]


def test_goal02_approval_allows_export_prep_but_not_final_claim(tmp_path: Path) -> None:
    package = review_package_fixture(tmp_path)
    record = build_decision_record(
        review_package=package,
        decision="approve_v04_20s_then_extend_final",
        notes=["A/B accepted by user."],
        reviewed_by="user",
        output_dir=tmp_path,
    )

    assert record["ready_for_final_export_prep"] is True
    assert record["safe_to_claim_final_delivery"] is False
    assert record["final_export_profile"] == "loud_reference_and_safe_streaming"
    assert record["blockers"] == []


def test_goal02_revision_decision_maps_to_vocal_forward_commands(tmp_path: Path) -> None:
    package = review_package_fixture(tmp_path)
    record = build_decision_record(
        review_package=package,
        decision="revise_v04_vocal_forward",
        notes=["Vocal still feels behind."],
        reviewed_by="user",
        output_dir=tmp_path,
    )

    assert record["approval_state"] == "revision_requested"
    assert record["ready_for_final_export_prep"] is False
    assert any("--vocal-gain-offset-db 0.8" in command for command in record["commands"])


def test_goal02_decision_blocks_when_review_package_targets_fail(tmp_path: Path) -> None:
    package = review_package_fixture(tmp_path)
    package["loudness_rows"][0]["review_target_pass"] = False
    check = verify_review_package(package)
    record = build_decision_record(
        review_package=package,
        decision="approve_v04_20s_then_extend_final",
        notes=["Approved despite warning."],
        reviewed_by="user",
        output_dir=tmp_path,
    )

    assert check["technical_review_package_ready"] is False
    assert "review_package_target_checks_failed" in record["blockers"]
    assert record["ready_for_final_export_prep"] is False
