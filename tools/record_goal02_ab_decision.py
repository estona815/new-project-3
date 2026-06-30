#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_PACKAGE = ROOT / "reports" / "goal02_v04_user_ab_review" / "goal02_v04_review_package.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "goal02_user_ab_decision"


DECISION_PROFILES: dict[str, dict[str, Any]] = {
    "pending": {
        "status": "USER_AB_DECISION_REQUIRED",
        "approval_state": "missing",
        "final_export_profile": None,
        "ready_for_final_export_prep": False,
        "summary": "No user A/B decision has been recorded.",
        "next_actions": [
            "Review the 20-second A/B sequence first.",
            "Record one explicit decision after matched-loudness review.",
        ],
    },
    "approve_v04_20s_then_extend_final": {
        "status": "USER_APPROVED_V04_20S_READY_FOR_FINAL_EXPORT_PREP",
        "approval_state": "recorded",
        "final_export_profile": "loud_reference_and_safe_streaming",
        "ready_for_final_export_prep": True,
        "summary": "User approved v04 20-second A/B direction; prepare final full-song export package next.",
        "next_actions": [
            "Use the v04 full-song draft as the final-export source candidate.",
            "Build final approved WAV and MP3 from the approved profile.",
            "Run final QC, encoded MP3 check, package evidence, and final delivery consistency gates.",
        ],
    },
    "approve_safe_only": {
        "status": "USER_APPROVED_SAFE_STREAMING_ONLY_READY_FOR_FINAL_EXPORT_PREP",
        "approval_state": "recorded",
        "final_export_profile": "safe_streaming",
        "ready_for_final_export_prep": True,
        "summary": "User approved only the safer streaming profile; do not use the loud reference master as final.",
        "next_actions": [
            "Use the full-song safe streaming candidate as the final-export source candidate.",
            "Build final approved WAV and MP3 from the safe profile only.",
            "Run final QC, encoded MP3 check, package evidence, and final delivery consistency gates.",
        ],
    },
    "rollback_to_v03_low_end": {
        "status": "USER_REJECTED_V04_ROLLBACK_TO_V03_REQUIRED",
        "approval_state": "revision_requested",
        "final_export_profile": None,
        "ready_for_final_export_prep": False,
        "summary": "User reported v04 low-end is too thick, masks vocal, or loses attack; rollback to v03 low-end offset.",
        "next_actions": [
            "Render a full-song v03 rollback draft with bass offset 2.5 dB.",
            "Build a new LUFS target package and review ZIP for that rollback.",
            "Do not add master limiting to fix the low-end complaint.",
        ],
        "commands": [
            "python3 tools/render_goal02_chorus_reaper.py --slug goal02_fullsong_reaper_v03_rollback --window-mode full-song --bass-gain-offset-db 2.5 --build-timeout 300 --render-timeout 600",
            "python3 tools/build_goal02_lufs_target_package.py --runtime-summary reports/goal02_fullsong_reaper_v03_rollback/goal02_fullsong_reaper_v03_rollback_runtime_summary.json --render-dir renders/goal02_fullsong_lufs_target_v03_rollback --report-dir reports/goal02_fullsong_lufs_target_v03_rollback --output-slug goal02_fullsong_lufs_target_v03_rollback",
        ],
    },
    "revise_v04_vocal_forward": {
        "status": "USER_REQUESTED_V04_VOCAL_FORWARD_REVISION",
        "approval_state": "revision_requested",
        "final_export_profile": None,
        "ready_for_final_export_prep": False,
        "summary": "User reported vocal is still behind or too thin; revise lead/VOX before master pressure.",
        "next_actions": [
            "Render v05 with a small center lead-vocal gain offset first.",
            "If the user complaint is clarity rather than level, adjust VOX BUS dynamic EQ/de-ess before increasing loudness.",
            "Rebuild 20-second LUFS A/B before extending full song.",
        ],
        "commands": [
            "python3 tools/render_goal02_chorus_reaper.py --slug goal02_chorus_reaper_v05_vocal_forward --bass-gain-offset-db 3.0 --vocal-gain-offset-db 0.8 --build-timeout 300 --render-timeout 600",
            "python3 tools/build_goal02_lufs_target_package.py --runtime-summary reports/goal02_chorus_reaper_v05_vocal_forward/goal02_chorus_reaper_v05_vocal_forward_runtime_summary.json --render-dir renders/goal02_chorus_lufs_target_v05_vocal_forward --report-dir reports/goal02_chorus_lufs_target_v05_vocal_forward --output-slug goal02_lufs_target_v05_vocal_forward",
        ],
    },
    "revise_v04_hat_sibilance": {
        "status": "USER_REQUESTED_V04_HAT_SIBILANCE_REVISION",
        "approval_state": "revision_requested",
        "final_export_profile": None,
        "ready_for_final_export_prep": False,
        "summary": "User reported hats, sibilance, or 7-12 kHz energy still read as fizz/metallic glare.",
        "next_actions": [
            "Revise VOX BUS and DRUM BUS high guard before adding or removing master air.",
            "Use TDR Nova/Air Guard dynamic reduction around 6-12 kHz and keep consonants intelligible.",
            "Rebuild 20-second LUFS A/B before extending full song.",
        ],
    },
    "revise_v04_808_kick": {
        "status": "USER_REQUESTED_V04_808_KICK_REVISION",
        "approval_state": "revision_requested",
        "final_export_profile": None,
        "ready_for_final_export_prep": False,
        "summary": "User reported 808/kick relationship still fails; revise 808/BASS before master pressure.",
        "next_actions": [
            "If 808 is too weak, test a small additional bass offset or harmonic layer.",
            "If 808 masks vocal, use the v03 rollback path instead.",
            "Rebuild 20-second LUFS A/B before extending full song.",
        ],
        "commands": [
            "python3 tools/render_goal02_chorus_reaper.py --slug goal02_chorus_reaper_v05_808_kick --bass-gain-offset-db 3.4 --build-timeout 300 --render-timeout 600",
            "python3 tools/build_goal02_lufs_target_package.py --runtime-summary reports/goal02_chorus_reaper_v05_808_kick/goal02_chorus_reaper_v05_808_kick_runtime_summary.json --render-dir renders/goal02_chorus_lufs_target_v05_808_kick --report-dir reports/goal02_chorus_lufs_target_v05_808_kick --output-slug goal02_lufs_target_v05_808_kick",
        ],
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_review_package(package: dict[str, Any], *, test_zip: bool = True) -> dict[str, Any]:
    zip_path = Path(package.get("zip_path", ""))
    blockers: list[str] = []
    warnings: list[str] = []
    if package.get("status") != "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL":
        blockers.append("review_package_status_not_ready")
    if not zip_path.exists():
        blockers.append("review_zip_missing")
    elif test_zip:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                bad = archive.testzip()
        except zipfile.BadZipFile:
            blockers.append("review_zip_invalid")
        else:
            if bad:
                blockers.append(f"review_zip_bad_member:{bad}")
    rows = package.get("loudness_rows", [])
    target_rows = [row for row in rows if row.get("review_target_kind")]
    if not target_rows:
        blockers.append("review_package_target_loudness_rows_missing")
    failed_targets = [row.get("label") for row in target_rows if row.get("review_target_pass") is not True]
    if failed_targets:
        blockers.append("review_package_target_checks_failed")
        warnings.extend(f"target_check_failed:{label}" for label in failed_targets)
    return {
        "zip_path": str(zip_path),
        "zip_exists": zip_path.exists(),
        "zip_tested": test_zip,
        "target_rows_total": len(target_rows),
        "target_rows_passed": len(target_rows) - len(failed_targets),
        "technical_review_package_ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
    }


def build_decision_record(
    *,
    review_package: dict[str, Any],
    decision: str,
    notes: list[str],
    reviewed_by: str,
    output_dir: Path,
    test_zip: bool = True,
) -> dict[str, Any]:
    profile = DECISION_PROFILES[decision]
    package_check = verify_review_package(review_package, test_zip=test_zip)
    blockers = list(package_check["blockers"])
    if decision == "pending":
        blockers.append("user_loudness_matched_ab_decision_missing")
    elif not package_check["technical_review_package_ready"]:
        blockers.append("cannot_prepare_final_export_from_unverified_review_package")
    final_export_prep_ready = bool(profile["ready_for_final_export_prep"]) and not blockers
    return {
        "schema": "goal02-user-ab-decision-v1",
        "created_at": now_utc(),
        "decision": decision,
        "status": profile["status"],
        "approval_state": profile["approval_state"],
        "reviewed_by": reviewed_by,
        "notes": notes,
        "review_package": {
            "report_path": str(DEFAULT_REVIEW_PACKAGE),
            "zip_path": review_package.get("zip_path"),
            "zip_sha256": review_package.get("zip_sha256"),
            "zip_size_bytes": review_package.get("zip_size_bytes"),
            "status": review_package.get("status"),
        },
        "review_package_check": package_check,
        "summary": profile["summary"],
        "next_actions": profile["next_actions"],
        "commands": profile.get("commands", []),
        "final_export_profile": profile["final_export_profile"],
        "ready_for_final_export_prep": final_export_prep_ready,
        "safe_to_claim_final_delivery": False,
        "blockers": blockers,
        "warnings": package_check["warnings"],
        "remaining_gates": [
            "final approved full-song WAV exists",
            "final approved 320k MP3 exists",
            "final QC and route gates pass",
            "final delivery ZIP/package evidence exists",
        ],
        "output_dir": str(output_dir),
    }


def write_report(path: Path, record: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 User A/B Decision Record",
        "",
        f"- Created UTC: `{record['created_at']}`",
        f"- Decision: `{record['decision']}`",
        f"- Status: `{record['status']}`",
        f"- Approval state: `{record['approval_state']}`",
        f"- Ready for final export prep: `{record['ready_for_final_export_prep']}`",
        f"- Safe to claim final delivery: `{record['safe_to_claim_final_delivery']}`",
        "",
        "## Review Package",
        "",
        f"- ZIP: `{record['review_package'].get('zip_path')}`",
        f"- ZIP SHA256: `{record['review_package'].get('zip_sha256')}`",
        f"- Technical review package ready: `{record['review_package_check']['technical_review_package_ready']}`",
        f"- Target rows passed: `{record['review_package_check']['target_rows_passed']}` / `{record['review_package_check']['target_rows_total']}`",
        "",
        "## Notes",
        "",
    ]
    if record["notes"]:
        lines.extend(f"- {note}" for note in record["notes"])
    else:
        lines.append("- No user notes recorded yet.")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in record["next_actions"])
    if record["commands"]:
        lines.extend(["", "## Suggested Commands", ""])
        lines.extend(f"```bash\n{command}\n```" for command in record["commands"])
    lines.extend(["", "## Blockers", ""])
    if record["blockers"]:
        lines.extend(f"- `{item}`" for item in record["blockers"])
    else:
        lines.append("- None for final-export prep; final delivery gates still remain.")
    lines.extend(["", "## Remaining Final Delivery Gates", ""])
    lines.extend(f"- {item}" for item in record["remaining_gates"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    package = load_json(args.review_package)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    record = build_decision_record(
        review_package=package,
        decision=args.decision,
        notes=args.note,
        reviewed_by=args.reviewed_by,
        output_dir=output_dir,
        test_zip=not args.skip_zip_test,
    )
    json_path = output_dir / "goal02_user_ab_decision.json"
    md_path = output_dir / "goal02_user_ab_decision.md"
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(md_path, record)
    record["json_path"] = str(json_path)
    record["report_path"] = str(md_path)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the Goal 02 v04 user loudness-matched A/B decision.")
    parser.add_argument("--review-package", type=Path, default=DEFAULT_REVIEW_PACKAGE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--decision", choices=sorted(DECISION_PROFILES), default="pending")
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--reviewed-by", default="user")
    parser.add_argument("--skip-zip-test", action="store_true")
    args = parser.parse_args()
    record = run(args)
    print(
        json.dumps(
            {
                "status": record["status"],
                "decision": record["decision"],
                "ready_for_final_export_prep": record["ready_for_final_export_prep"],
                "safe_to_claim_final_delivery": record["safe_to_claim_final_delivery"],
                "blockers": record["blockers"],
                "report_path": record["report_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if record["decision"] != "pending" and not record["blockers"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
