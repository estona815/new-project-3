from __future__ import annotations

import json
import zipfile
from pathlib import Path

from tools.build_goal02_final_delivery_package import build_final_delivery


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_audio_fixture(path: Path, label: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"fixture-{label}".encode("utf-8"))
    return path


def decision_fixture(tmp_path: Path, *, decision: str, ready: bool, blockers: list[str] | None = None, profile: str | None = None) -> Path:
    return write_json(
        tmp_path / "reports" / "goal02_user_ab_decision.json",
        {
            "schema": "goal02-user-ab-decision-v1",
            "decision": decision,
            "status": "fixture",
            "approval_state": "recorded" if ready else "missing",
            "ready_for_final_export_prep": ready,
            "safe_to_claim_final_delivery": False,
            "final_export_profile": profile,
            "blockers": blockers or [],
            "review_package_check": {"technical_review_package_ready": True},
        },
    )


def review_package_fixture(tmp_path: Path) -> Path:
    audio_dir = tmp_path / "review_audio"
    rows = []
    for label in ["full_song_loud_wav", "full_song_loud_mp3", "full_song_safe_wav", "full_song_safe_mp3", "full_song_ab_wav"]:
        suffix = ".mp3" if label.endswith("_mp3") else ".wav"
        path = write_audio_fixture(audio_dir / f"{label}{suffix}", label)
        rows.append(
            {
                "label": label,
                "type": "mp3" if suffix == ".mp3" else "wav",
                "absolute_path": str(path),
                "package_path": f"audio/{path.name}",
            }
        )
    evidence = tmp_path / "evidence" / "goal02_lufs_target_package.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("# evidence\n", encoding="utf-8")
    rows.append(
        {
            "label": "goal02_lufs_target_package",
            "type": "evidence",
            "absolute_path": str(evidence),
            "package_path": "evidence/goal02_lufs_target_package.md",
        }
    )
    return write_json(
        tmp_path / "reports" / "goal02_review_package.json",
        {
            "schema": "goal02-review-package-v1",
            "status": "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL",
            "files": rows,
            "loudness_rows": [],
        },
    )


def test_final_delivery_blocks_pending_decision_and_creates_no_zip(tmp_path: Path) -> None:
    decision = decision_fixture(
        tmp_path,
        decision="pending",
        ready=False,
        blockers=["user_loudness_matched_ab_decision_missing"],
        profile=None,
    )
    review = review_package_fixture(tmp_path)

    result = build_final_delivery(
        decision_record_path=decision,
        review_package_path=review,
        output_dir=tmp_path / "delivery",
        report_dir=tmp_path / "reports" / "final",
    )

    assert result["status"] == "BLOCKED_USER_AB_APPROVAL_REQUIRED"
    assert result["safe_to_claim_final_delivery"] is False
    assert "user_loudness_matched_ab_decision_missing" in result["blockers"]
    assert not Path(result["zip_path"]).exists()
    assert (tmp_path / "reports" / "final" / "goal02_final_delivery_gate.md").exists()


def test_final_delivery_builds_approved_loud_and_safe_package_without_ab_audio(tmp_path: Path) -> None:
    decision = decision_fixture(
        tmp_path,
        decision="approve_v04_20s_then_extend_final",
        ready=True,
        profile="loud_reference_and_safe_streaming",
    )
    review = review_package_fixture(tmp_path)

    result = build_final_delivery(
        decision_record_path=decision,
        review_package_path=review,
        output_dir=tmp_path / "delivery",
        report_dir=tmp_path / "reports" / "final",
    )

    assert result["status"] == "FINAL_DELIVERY_PACKAGE_READY"
    assert result["safe_to_claim_final_delivery"] is True
    assert result["zip_test_status"] == "passed"
    with zipfile.ZipFile(result["zip_path"]) as archive:
        names = set(archive.namelist())
    assert "audio/GOAL02_v04_FINAL_LOUD_REFERENCE_24-48.wav" in names
    assert "audio/GOAL02_v04_FINAL_LOUD_REFERENCE_320k.mp3" in names
    assert "audio/GOAL02_v04_FINAL_SAFE_STREAMING_24-48.wav" in names
    assert "audio/GOAL02_v04_FINAL_SAFE_STREAMING_320k.mp3" in names
    assert not any("full_song_ab" in name or "AB_current" in name for name in names)


def test_final_delivery_safe_only_profile_excludes_loud_master(tmp_path: Path) -> None:
    decision = decision_fixture(
        tmp_path,
        decision="approve_safe_only",
        ready=True,
        profile="safe_streaming",
    )
    review = review_package_fixture(tmp_path)

    result = build_final_delivery(
        decision_record_path=decision,
        review_package_path=review,
        output_dir=tmp_path / "delivery",
        report_dir=tmp_path / "reports" / "final",
    )

    assert result["status"] == "FINAL_DELIVERY_PACKAGE_READY"
    with zipfile.ZipFile(result["zip_path"]) as archive:
        names = set(archive.namelist())
    assert "audio/GOAL02_v04_FINAL_SAFE_STREAMING_320k.mp3" in names
    assert "audio/GOAL02_v04_FINAL_LOUD_REFERENCE_320k.mp3" not in names


def test_final_delivery_blocks_revision_decision(tmp_path: Path) -> None:
    decision = decision_fixture(
        tmp_path,
        decision="revise_v04_vocal_forward",
        ready=False,
        blockers=[],
        profile=None,
    )
    data = json.loads(decision.read_text(encoding="utf-8"))
    data["approval_state"] = "revision_requested"
    decision.write_text(json.dumps(data), encoding="utf-8")
    review = review_package_fixture(tmp_path)

    result = build_final_delivery(
        decision_record_path=decision,
        review_package_path=review,
        output_dir=tmp_path / "delivery",
        report_dir=tmp_path / "reports" / "final",
    )

    assert result["status"] == "BLOCKED_USER_REVISION_REQUIRED"
    assert result["safe_to_claim_final_delivery"] is False
    assert not Path(result["zip_path"]).exists()
