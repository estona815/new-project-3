from __future__ import annotations

import json
import zipfile
from pathlib import Path

from tools.audit_goal02_completion import PATHS, audit_goal02


PROBLEM_BLOCK = """
문제: fixture problem
원인 추정: fixture cause
레퍼런스와의 차이: fixture delta
수정 위치: fixture bus
사용할 플러그인: fixture plugin
권장 시작값: fixture start
A/B 확인법: fixture check
실패 징후: fixture failure
"""

ACTION_PLAN_TEXT = (
    """
## 1. Primary Reference Selection
| Rank | Reference |
| --- | --- |
| 1 | `ref_06` |
| 2 | `ref_07` |
## 2. Reference Common Mix Features
## 3. Target Top 10 Problems
"""
    + "\n".join(PROBLEM_BLOCK for _ in range(10))
    + """
## 4. Chorus 20-Second Revision Order
## 5. Track-Level REAPER FX Chains
### A. Lead Vocal Chain
### B. Lead Vocal Parallel Crush
### C. Doubles / Adlibs
### D. 808 Chain
### E. Drum Bus
### F. Music Bus
### G. Mix Bus / Master Chain
## 6. Starting Parameters
- Lead vocal:
- Parallel crush:
- Doubles/adlibs:
- 808:
- Drums:
- Music:
- Master:
## 7. Loudness-Matched A/B Method
## 8. Master Export Goals
- Loud reference review master: `-9.5 to -8.0 LUFS-I`
- Safer streaming master: `-14.5 to -12.5 LUFS-I`
## 9. Rollback Criteria
## 10. 30-Minute Work Table
## 19. User A/B Decision Intake
## 20. Final Delivery Gate
"""
)

AB_SEQUENCE_ORDER = "Current target -> v04 candidate -> ref_06 -> v04 candidate -> ref_07 -> v04 candidate -> ref_03 -> v04 candidate"


def write_json(root: Path, rel: Path, data: dict) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_text(root: Path, rel: Path, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def trace_fixture() -> dict:
    return {
        "rows": [
            {
                "track": "SOURCE full mix reference muted - not in master",
                "stage": "track config",
                "plugin": "gain_db=-99.000 pan=0.000 muted=true master_send=false",
                "fx_index": -1,
            },
            {
                "track": "REF BUS",
                "stage": "track config",
                "plugin": "gain_db=0.000 pan=0.000 muted=true master_send=false",
                "fx_index": -1,
            },
            {
                "track": "08 MALE_NONHOOK_CENTER",
                "stage": "Codex Vocal AI Artifact Split Tamer FIRST SLOT",
                "plugin": "JS: Codex Vocal AI Artifact Split Tamer",
                "fx_index": 0,
            },
        ]
    }


def write_base_goal02_fixture(root: Path) -> Path:
    write_json(
        root,
        PATHS["reference_match"],
        {
            "summary": {"references_measured": 8},
            "primary_references": [{"id": "ref_06"}, {"id": "ref_07"}, {"id": "ref_03"}],
        },
    )
    reference_keys = [
        "overall_loudness_rms_lufs",
        "true_peak_peak_density",
        "vocal_position_thickness_brightness_proxy",
        "autotune_sibilance_proxy",
        "bass_808_character_proxy",
        "kick_808_relationship_proxy",
        "drum_hihat_proxy",
        "presence_harshness_air",
        "stereo_width_mono_compatibility",
        "reverb_delay_depth_proxy",
        "saturation_clipping_distortion_proxy",
        "master_compression_proxy",
    ]
    references = []
    for index in range(1, 9):
        row = {
            "id": f"ref_{index:02d}",
            "claim_limit": "proxy metrics only; not listening claims",
            "core_mix_features_3": ["dense", "sub-forward", "mono-compatible"],
        }
        for key in reference_keys:
            row[key] = {"read": "fixture"}
        references.append(row)
    write_json(
        root,
        PATHS["reference_mix_features"],
        {
            "status": "REFERENCE_8_TRACK_MIX_FEATURE_REPORT_READY_METRIC_PROXIES",
            "reference_count": 8,
            "primary_reference_ids": ["ref_03", "ref_06", "ref_07"],
            "references": references,
        },
    )
    translation_entries = []
    for ref_id in ["ref_03", "ref_06", "ref_07"]:
        translation_entries.append(
            {
                "id": ref_id,
                "why_reference": ["fixture why"],
                "target_lacks": ["fixture lack"],
                "target_already_ok": ["fixture ok"],
                "must_follow": ["fixture follow"],
                "must_not_copy": ["fixture avoid"],
                "bus_translation_order": ["fixture bus"],
                "plugin_scope": ["fixture plugin"],
                "ab_check": ["fixture ab"],
                "failure_signs": ["fixture failure"],
                "claim_limit": "This entry is not a listening claim.",
            }
        )
    write_json(
        root,
        PATHS["primary_reference_translation_pack"],
        {
            "status": "PRIMARY_REFERENCE_TRANSLATION_PACK_READY",
            "primary_reference_count": 3,
            "primary_reference_ids": ["ref_03", "ref_06", "ref_07"],
            "entries": translation_entries,
        },
    )
    write_json(
        root,
        PATHS["objective_coverage_audit"],
        {
            "status": "OBJECTIVE_COVERAGE_READY_USER_AB_PENDING",
            "non_user_requirements_passed": True,
            "missing_count": 0,
            "items": [
                {"id": "reference_8_song_analysis_categories", "status": "PASS"},
                {"id": "user_ab_success_criteria", "status": "BLOCKED"},
                {"id": "approved_final_delivery_package", "status": "BLOCKED"},
            ],
        },
    )
    write_text(root, PATHS["action_plan"], ACTION_PLAN_TEXT)
    write_json(
        root,
        PATHS["decision_packet"],
        {
            "status": "PREFERRED_20S_CANDIDATE_READY_USER_AB_PENDING",
            "preferred": "v04",
            "rollback_candidate": "v03",
        },
    )
    write_json(root, PATHS["v04_trace"], trace_fixture())
    write_json(root, PATHS["fullsong_trace"], trace_fixture())
    for key in ["v04_lufs", "fullsong_lufs"]:
        write_json(
            root,
            PATHS[key],
            {
                "loudness_rows": [
                    {"label": "safe", "target_pass": True},
                    {"label": "loud", "target_pass": True},
                    {"label": "ab", "target_pass": None},
                ]
            },
        )
    review_zip = root / "delivery" / "review.zip"
    review_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(review_zip, "w") as archive:
        archive.writestr("review.txt", "ok")
        archive.writestr(
            "GOAL02_REVIEW_PLAYER.html",
            f"""
            <h1>GOAL 02 v04 A/B Review</h1>
            <p>This local page does not approve audio.</p>
            <p>{AB_SEQUENCE_ORDER}</p>
            <code>python3 tools/record_goal02_ab_decision.py --decision approve_v04_20s_then_extend_final</code>
            """,
        )
        archive.writestr(
            "GOAL02_USER_AB_REVIEW_CHECKLIST.md",
            f"""
            {AB_SEQUENCE_ORDER}
            python3 tools/record_goal02_ab_decision.py --decision revise_v04_hat_sibilance
            This checklist does not replace the final WAV/MP3/ZIP delivery gate.
            """,
        )
    write_json(
        root,
        PATHS["review_package"],
        {
            "status": "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL",
            "zip_path": str(review_zip),
            "loudness_rows": [
                {"label": "loud_mp3", "review_target_kind": "loud", "review_target_pass": True},
                {"label": "safe_mp3", "review_target_kind": "safe", "review_target_pass": True},
            ],
        },
    )
    return review_zip


def test_goal02_completion_audit_blocks_pending_user_decision(tmp_path: Path) -> None:
    write_base_goal02_fixture(tmp_path)
    write_json(
        tmp_path,
        PATHS["user_decision"],
        {
            "decision": "pending",
            "ready_for_final_export_prep": False,
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )
    write_json(
        tmp_path,
        PATHS["final_delivery"],
        {
            "status": "BLOCKED_USER_AB_APPROVAL_REQUIRED",
            "safe_to_claim_final_delivery": False,
            "zip_path": str(tmp_path / "delivery" / "final.zip"),
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )

    audit = audit_goal02(tmp_path)

    assert audit["complete"] is False
    assert audit["status"] == "GOAL02_INCOMPLETE_BLOCKED_BY_USER_AB_OR_FINAL_DELIVERY"
    statuses = {item["id"]: item["status"] for item in audit["items"]}
    assert statuses["user_ab_approval"] == "BLOCKED"
    assert statuses["final_delivery_package"] == "BLOCKED"
    assert statuses["reference_8_track_feature_report"] == "PASS"
    assert statuses["primary_reference_translation_pack"] == "PASS"
    assert statuses["objective_coverage_audit"] == "PASS"
    assert statuses["top10_problem_format"] == "PASS"
    assert statuses["required_chain_coverage"] == "PASS"
    assert statuses["review_flow_controls"] == "PASS"
    assert audit["pass_count"] == audit["total_count"] - 2


def test_goal02_completion_audit_passes_only_with_approved_final_zip(tmp_path: Path) -> None:
    write_base_goal02_fixture(tmp_path)
    final_zip = tmp_path / "delivery" / "final.zip"
    final_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(final_zip, "w") as archive:
        archive.writestr("audio/final.wav", "ok")
    write_json(
        tmp_path,
        PATHS["user_decision"],
        {
            "decision": "approve_v04_20s_then_extend_final",
            "ready_for_final_export_prep": True,
            "blockers": [],
        },
    )
    write_json(
        tmp_path,
        PATHS["final_delivery"],
        {
            "status": "FINAL_DELIVERY_PACKAGE_READY",
            "safe_to_claim_final_delivery": True,
            "zip_path": str(final_zip),
            "blockers": [],
        },
    )

    audit = audit_goal02(tmp_path)

    assert audit["complete"] is True
    assert audit["status"] == "GOAL02_COMPLETE_VERIFIED"
    assert audit["pass_count"] == audit["total_count"]


def test_goal02_completion_audit_catches_incomplete_objective_plan(tmp_path: Path) -> None:
    write_base_goal02_fixture(tmp_path)
    write_text(tmp_path, PATHS["action_plan"], "## 1. Primary Reference Selection\n")
    write_json(
        tmp_path,
        PATHS["user_decision"],
        {
            "decision": "approve_v04_20s_then_extend_final",
            "ready_for_final_export_prep": True,
            "blockers": [],
        },
    )
    final_zip = tmp_path / "delivery" / "final.zip"
    final_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(final_zip, "w") as archive:
        archive.writestr("audio/final.wav", "ok")
    write_json(
        tmp_path,
        PATHS["final_delivery"],
        {
            "status": "FINAL_DELIVERY_PACKAGE_READY",
            "safe_to_claim_final_delivery": True,
            "zip_path": str(final_zip),
            "blockers": [],
        },
    )

    audit = audit_goal02(tmp_path)
    statuses = {item["id"]: item["status"] for item in audit["items"]}

    assert audit["complete"] is False
    assert audit["status"] == "GOAL02_INCOMPLETE_MISSING_EVIDENCE"
    assert statuses["required_written_plan"] == "MISSING"
    assert statuses["top10_problem_format"] == "MISSING"
    assert statuses["required_chain_coverage"] == "MISSING"


def test_goal02_completion_audit_requires_reference_feature_report(tmp_path: Path) -> None:
    write_base_goal02_fixture(tmp_path)
    (tmp_path / PATHS["reference_mix_features"]).unlink()
    write_json(
        tmp_path,
        PATHS["user_decision"],
        {
            "decision": "pending",
            "ready_for_final_export_prep": False,
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )
    write_json(
        tmp_path,
        PATHS["final_delivery"],
        {
            "status": "BLOCKED_USER_AB_APPROVAL_REQUIRED",
            "safe_to_claim_final_delivery": False,
            "zip_path": str(tmp_path / "delivery" / "final.zip"),
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )

    audit = audit_goal02(tmp_path)
    statuses = {item["id"]: item["status"] for item in audit["items"]}

    assert statuses["reference_8_track_feature_report"] == "MISSING"
    assert audit["missing_count"] == 1


def test_goal02_completion_audit_requires_primary_reference_translation_pack(tmp_path: Path) -> None:
    write_base_goal02_fixture(tmp_path)
    (tmp_path / PATHS["primary_reference_translation_pack"]).unlink()
    write_json(
        tmp_path,
        PATHS["user_decision"],
        {
            "decision": "pending",
            "ready_for_final_export_prep": False,
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )
    write_json(
        tmp_path,
        PATHS["final_delivery"],
        {
            "status": "BLOCKED_USER_AB_APPROVAL_REQUIRED",
            "safe_to_claim_final_delivery": False,
            "zip_path": str(tmp_path / "delivery" / "final.zip"),
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )

    audit = audit_goal02(tmp_path)
    statuses = {item["id"]: item["status"] for item in audit["items"]}

    assert statuses["primary_reference_translation_pack"] == "MISSING"
    assert audit["missing_count"] == 1


def test_goal02_completion_audit_requires_objective_coverage_audit(tmp_path: Path) -> None:
    write_base_goal02_fixture(tmp_path)
    (tmp_path / PATHS["objective_coverage_audit"]).unlink()
    write_json(
        tmp_path,
        PATHS["user_decision"],
        {
            "decision": "pending",
            "ready_for_final_export_prep": False,
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )
    write_json(
        tmp_path,
        PATHS["final_delivery"],
        {
            "status": "BLOCKED_USER_AB_APPROVAL_REQUIRED",
            "safe_to_claim_final_delivery": False,
            "zip_path": str(tmp_path / "delivery" / "final.zip"),
            "blockers": ["user_loudness_matched_ab_decision_missing"],
        },
    )

    audit = audit_goal02(tmp_path)
    statuses = {item["id"]: item["status"] for item in audit["items"]}

    assert statuses["objective_coverage_audit"] == "MISSING"
    assert audit["missing_count"] == 1
