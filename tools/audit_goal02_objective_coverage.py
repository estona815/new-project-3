#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_objective_coverage"

ACTION_PLAN = Path("reports/goal02_8_reference_match/GOAL02_REAPER_ACTION_PLAN.md")
REFERENCE_FEATURES = Path("reports/goal02_8_reference_match/goal02_reference_8_track_mix_features.json")
PRIMARY_TRANSLATION = Path("reports/goal02_8_reference_match/goal02_primary_reference_translation_pack.json")
REVIEW_PACKAGE = Path("reports/goal02_v04_user_ab_review/goal02_v04_review_package.json")
USER_DECISION = Path("reports/goal02_user_ab_decision/goal02_user_ab_decision.json")
FINAL_DELIVERY = Path("reports/goal02_final_delivery/goal02_final_delivery_gate.json")
V04_TRACE = Path("reports/goal02_chorus_reaper_v04/actual_reaper_plugin_trace.json")
FULLSONG_TRACE = Path("reports/goal02_fullsong_reaper_v04_draft/actual_reaper_plugin_trace.json")

AB_SEQUENCE_ORDER = (
    "Current target -> v04 candidate -> ref_06 -> v04 candidate -> "
    "ref_07 -> v04 candidate -> ref_03 -> v04 candidate"
)

REFERENCE_OBJECTIVE_CATEGORIES = {
    "overall_loudness_rms_lufs": "전체 loudness / RMS / LUFS 성향",
    "true_peak_peak_density": "true peak / peak density",
    "vocal_position_thickness_brightness_proxy": "보컬 위치, 두께, 밝기, nasal/airy 성향",
    "autotune_sibilance_proxy": "오토튠 강도와 치찰 처리",
    "bass_808_character_proxy": "808 sub/harmonic 성향",
    "kick_808_relationship_proxy": "킥과 808 관계",
    "drum_hihat_proxy": "드럼 transient와 하이햇 밝기/거칠기",
    "presence_harshness_air": "2-5 kHz presence와 6-12 kHz harshness/air",
    "stereo_width_mono_compatibility": "stereo width / mono compatibility",
    "reverb_delay_depth_proxy": "reverb/delay 깊이",
    "saturation_clipping_distortion_proxy": "saturation / clipping / distortion 질감",
    "master_compression_proxy": "master compression 느낌",
    "core_mix_features_3": "곡별 핵심 믹스 특징 3개",
}

FINAL_OUTPUT_SECTIONS = [
    "Primary Reference 선정 결과",
    "레퍼런스 8곡 공통 믹스 특징",
    "타겟 곡이 가장 부족한 TOP 10",
    "후렴 20초 수정 순서",
    "트랙별 REAPER FX Chain",
    "각 플러그인 starting parameter",
    "loudness-matched A/B 체크 방법",
    "master export 목표값",
    "실패했을 때 되돌아갈 기준",
    "오늘 바로 실행할 30분 작업표",
]

CHAIN_NEEDLES = [
    "Lead Vocal Chain",
    "Lead Vocal Parallel Crush",
    "Doubles / Adlibs",
    "808 Chain",
    "Drum Bus",
    "Music Bus",
    "Mix Bus / Master Chain",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(root: Path, rel: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = root / rel
    if not path.exists():
        return None, f"missing:{rel}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"invalid_json:{rel}:{exc}"


def load_text(root: Path, rel: Path) -> tuple[str | None, str | None]:
    path = root / rel
    if not path.exists():
        return None, f"missing:{rel}"
    try:
        return path.read_text(encoding="utf-8"), None
    except Exception as exc:
        return None, f"invalid_text:{rel}:{exc}"


def add_item(
    items: list[dict[str, Any]],
    item_id: str,
    requirement: str,
    status: str,
    evidence: str,
    notes: str = "",
) -> None:
    items.append(
        {
            "id": item_id,
            "requirement": requirement,
            "status": status,
            "evidence": evidence,
            "notes": notes,
        }
    )


def action_plan_problem_count(text: str) -> int:
    match = re.search(r"^## 3\. Target Top 10 Problems(?P<body>.*?)^## 4\.", text, re.S | re.M)
    if not match:
        return 0
    return len(re.findall(r"^### \d+\. ", match.group("body"), re.M))


def reference_feature_coverage(report: dict[str, Any]) -> tuple[bool, str]:
    refs = report.get("references", [])
    if len(refs) != 8:
        return False, f"reference_count={len(refs)}"
    weak: list[str] = []
    for ref in refs:
        ref_id = ref.get("id")
        for key in REFERENCE_OBJECTIVE_CATEGORIES:
            if key not in ref:
                weak.append(f"{ref_id}:missing:{key}")
        if len(ref.get("core_mix_features_3", [])) != 3:
            weak.append(f"{ref_id}:core_mix_features_3_count")
    if weak:
        return False, "; ".join(weak)
    return True, "all 8 references cover the requested proxy categories"


def primary_translation_coverage(pack: dict[str, Any]) -> tuple[bool, str]:
    required = {"ref_03", "ref_06", "ref_07"}
    entries = pack.get("entries", [])
    ids = {entry.get("id") for entry in entries}
    if ids != required:
        return False, f"entry_ids={','.join(sorted(str(item) for item in ids))}"
    fields = ["why_reference", "target_lacks", "target_already_ok", "must_follow", "must_not_copy"]
    weak: list[str] = []
    for entry in entries:
        for field in fields:
            if not entry.get(field):
                weak.append(f"{entry.get('id')}:missing:{field}")
    if weak:
        return False, "; ".join(weak)
    return True, "ref_03/ref_06/ref_07 include why/lacks/ok/follow/avoid"


def route_gate(trace: dict[str, Any]) -> tuple[bool, str]:
    rows = trace.get("rows", [])
    first_slot = any(
        row.get("track") == "08 MALE_NONHOOK_CENTER"
        and row.get("fx_index") == 0
        and row.get("plugin") == "JS: Codex Vocal AI Artifact Split Tamer"
        for row in rows
    )
    muted_refs = []
    for track in ["REF BUS", "SOURCE full mix reference muted - not in master"]:
        ok = any(
            row.get("track") == track
            and row.get("stage") == "track config"
            and "muted=true" in str(row.get("plugin", ""))
            and "master_send=false" in str(row.get("plugin", ""))
            for row in rows
        )
        muted_refs.append(ok)
    ok = first_slot and all(muted_refs)
    return ok, f"first_slot={first_slot}; muted_no_master_refs={all(muted_refs)}"


def review_package_coverage(package: dict[str, Any]) -> tuple[bool, str]:
    if package.get("status") != "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL":
        return False, f"status={package.get('status')}"
    zip_path = Path(str(package.get("zip_path", "")))
    if not zip_path.exists():
        return False, f"zip_missing={zip_path}"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return False, "zip_invalid"
    if bad:
        return False, f"zip_bad_file={bad}"
    needed = {
        "audio/wav/01_20s_AB_current_candidate_primary_refs.wav",
        "audio/mp3/01_20s_AB_current_candidate_primary_refs_320k.mp3",
        "GOAL02_REVIEW_PLAYER.html",
        "GOAL02_USER_AB_REVIEW_CHECKLIST.md",
        "evidence/GOAL02_PRIMARY_REFERENCE_TRANSLATION_PACK.md",
    }
    missing = sorted(needed - names)
    if missing:
        return False, "missing package members: " + ", ".join(missing)
    target_rows = [row for row in package.get("loudness_rows", []) if row.get("review_target_kind")]
    failed = [row.get("label") for row in target_rows if row.get("review_target_pass") is not True]
    if failed:
        return False, "failed target rows: " + ", ".join(str(row) for row in failed)
    return True, f"zip valid; {len(target_rows)} loud/safe target rows pass; objective evidence included"


def audit_objective_coverage(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    items: list[dict[str, Any]] = []

    action_text, action_error = load_text(root, ACTION_PLAN)
    reference_report, reference_error = load_json(root, REFERENCE_FEATURES)
    primary_pack, primary_error = load_json(root, PRIMARY_TRANSLATION)
    review_package, review_error = load_json(root, REVIEW_PACKAGE)
    user_decision, user_error = load_json(root, USER_DECISION)
    final_delivery, final_error = load_json(root, FINAL_DELIVERY)
    v04_trace, v04_error = load_json(root, V04_TRACE)
    fullsong_trace, fullsong_error = load_json(root, FULLSONG_TRACE)

    if reference_error:
        add_item(items, "reference_8_song_analysis_categories", "Analyze all 8 references across the requested mix/master categories.", "MISSING", str(REFERENCE_FEATURES), reference_error)
    else:
        ok, notes = reference_feature_coverage(reference_report)
        add_item(items, "reference_8_song_analysis_categories", "Analyze all 8 references across the requested mix/master categories.", "PASS" if ok else "MISSING", str(REFERENCE_FEATURES), notes)

    if primary_error:
        add_item(items, "primary_reference_selection_and_translation", "Select 2-3 primary references and explain why/follow/avoid for each.", "MISSING", str(PRIMARY_TRANSLATION), primary_error)
    else:
        ok, notes = primary_translation_coverage(primary_pack)
        count_ok = primary_pack.get("primary_reference_count") in {2, 3}
        add_item(
            items,
            "primary_reference_selection_and_translation",
            "Select 2-3 primary references and explain why/follow/avoid for each.",
            "PASS" if ok and count_ok else "MISSING",
            str(PRIMARY_TRANSLATION),
            f"{notes}; primary_reference_count={primary_pack.get('primary_reference_count')}",
        )

    if action_error:
        for item_id, requirement in [
            ("target_top10_problem_diagnosis", "Write the target TOP 10 problem diagnosis in the required fields."),
            ("final_output_10_section_coverage", "Cover the requested final output sections 1-10."),
            ("required_reaper_chain_coverage", "Document chains A-G."),
            ("chorus_20s_revision_order", "Keep the first pass focused on the 20-second chorus and ordered vocal -> 808/kick -> drums/hats -> music -> master."),
            ("minimal_chain_and_bus_first_policy", "Document bus-first correction and avoid master-only compensation/plugin stacking."),
        ]:
            add_item(items, item_id, requirement, "MISSING", str(ACTION_PLAN), action_error)
    else:
        problem_count = action_plan_problem_count(action_text)
        field_counts = {
            field: action_text.count(field)
            for field in ["문제:", "원인 추정:", "레퍼런스와의 차이:", "수정 위치:", "사용할 플러그인:", "권장 시작값:", "A/B 확인법:", "실패 징후:"]
        }
        weak_fields = [f"{key}={value}" for key, value in field_counts.items() if value < 10]
        add_item(
            items,
            "target_top10_problem_diagnosis",
            "Write the target TOP 10 problem diagnosis in the required fields.",
            "PASS" if problem_count == 10 and not weak_fields else "MISSING",
            str(ACTION_PLAN),
            f"problem_count={problem_count}; weak_fields={','.join(weak_fields) or 'none'}",
        )

        section_checks = {
            "Primary Reference 선정 결과": "Primary Reference Selection",
            "레퍼런스 8곡 공통 믹스 특징": "Reference Common Mix Features",
            "타겟 곡이 가장 부족한 TOP 10": "Target Top 10 Problems",
            "후렴 20초 수정 순서": "Chorus 20-Second Revision Order",
            "트랙별 REAPER FX Chain": "Track-Level REAPER FX Chains",
            "각 플러그인 starting parameter": "Starting Parameters",
            "loudness-matched A/B 체크 방법": "Loudness-Matched A/B Method",
            "master export 목표값": "Master Export Goals",
            "실패했을 때 되돌아갈 기준": "Rollback Criteria",
            "오늘 바로 실행할 30분 작업표": "30-Minute Work Table",
        }
        missing_sections = [label for label, needle in section_checks.items() if needle not in action_text]
        add_item(
            items,
            "final_output_10_section_coverage",
            "Cover the requested final output sections 1-10.",
            "PASS" if not missing_sections else "MISSING",
            str(ACTION_PLAN),
            "covered: " + ", ".join(section for section in FINAL_OUTPUT_SECTIONS if section not in missing_sections) if not missing_sections else "missing: " + ", ".join(missing_sections),
        )

        missing_chains = [needle for needle in CHAIN_NEEDLES if needle not in action_text]
        add_item(
            items,
            "required_reaper_chain_coverage",
            "Document chains A-G.",
            "PASS" if not missing_chains else "MISSING",
            str(ACTION_PLAN),
            "all A-G chains present" if not missing_chains else "missing: " + ", ".join(missing_chains),
        )

        chorus_needles = [
            "87.5s-107.5s",
            "Build lead vocal density",
            "Raise and saturate 808/BASS BUS",
            "Clip/shape DRUM BUS",
            "Cut music-bus",
            "MIX BUS glue/clip only after",
        ]
        missing_chorus = [needle for needle in chorus_needles if needle not in action_text]
        add_item(
            items,
            "chorus_20s_revision_order",
            "Keep the first pass focused on the 20-second chorus and ordered vocal -> 808/kick -> drums/hats -> music -> master.",
            "PASS" if not missing_chorus else "MISSING",
            str(ACTION_PLAN),
            "chorus order present" if not missing_chorus else "missing: " + ", ".join(missing_chorus),
        )

        policy_needles = [
            "VOX/808/DRUM buses first",
            "sustained master GR over `2 dB`",
            "Do not copy",
            "not a final full-song master without user A/B approval",
        ]
        missing_policy = [needle for needle in policy_needles if needle not in action_text]
        add_item(
            items,
            "minimal_chain_and_bus_first_policy",
            "Document bus-first correction and avoid master-only compensation/plugin stacking.",
            "PASS" if not missing_policy else "MISSING",
            str(ACTION_PLAN),
            "bus-first and no-copy policies present" if not missing_policy else "missing: " + ", ".join(missing_policy),
        )

    for key, trace, error, evidence in [
        ("v04_runtime_route_and_first_slot_gate", v04_trace, v04_error, V04_TRACE),
        ("fullsong_runtime_route_and_first_slot_gate", fullsong_trace, fullsong_error, FULLSONG_TRACE),
    ]:
        if error:
            add_item(items, key, "Prove first-slot AI artifact JSFX and muted/no-master reference routing.", "MISSING", str(evidence), error)
        else:
            ok, notes = route_gate(trace)
            add_item(items, key, "Prove first-slot AI artifact JSFX and muted/no-master reference routing.", "PASS" if ok else "MISSING", str(evidence), notes)

    if review_error:
        add_item(items, "loudness_matched_review_package", "Build a loudness-matched A/B review package with primary references and decision controls.", "MISSING", str(REVIEW_PACKAGE), review_error)
    else:
        ok, notes = review_package_coverage(review_package)
        add_item(items, "loudness_matched_review_package", "Build a loudness-matched A/B review package with primary references and decision controls.", "PASS" if ok else "MISSING", str(REVIEW_PACKAGE), notes)

    if user_error:
        add_item(items, "user_ab_success_criteria", "Record user loudness-matched A/B approval or revision against the success criteria.", "BLOCKED", str(USER_DECISION), user_error)
    else:
        decision = user_decision.get("decision")
        ready = bool(user_decision.get("ready_for_final_export_prep"))
        passed = decision in {"approve_v04_20s_then_extend_final", "approve_safe_only"} and ready
        add_item(
            items,
            "user_ab_success_criteria",
            "Record user loudness-matched A/B approval or revision against the success criteria.",
            "PASS" if passed else "BLOCKED",
            str(USER_DECISION),
            f"decision={decision}; ready_for_final_export_prep={ready}; blockers={user_decision.get('blockers')}",
        )

    if final_error:
        add_item(items, "approved_final_delivery_package", "Create approved-only final WAV/MP3/ZIP after user approval.", "BLOCKED", str(FINAL_DELIVERY), final_error)
    else:
        zip_path = Path(str(final_delivery.get("zip_path", "")))
        passed = (
            final_delivery.get("status") == "FINAL_DELIVERY_PACKAGE_READY"
            and final_delivery.get("safe_to_claim_final_delivery") is True
            and zip_path.exists()
        )
        add_item(
            items,
            "approved_final_delivery_package",
            "Create approved-only final WAV/MP3/ZIP after user approval.",
            "PASS" if passed else "BLOCKED",
            str(FINAL_DELIVERY),
            f"status={final_delivery.get('status')}; zip_exists={zip_path.exists()}; blockers={final_delivery.get('blockers')}",
        )

    pass_count = sum(1 for item in items if item["status"] == "PASS")
    missing = [item for item in items if item["status"] == "MISSING"]
    blocked = [item for item in items if item["status"] == "BLOCKED"]
    non_user_requirements_passed = not missing
    complete = not missing and not blocked
    if complete:
        status = "OBJECTIVE_COVERAGE_COMPLETE_VERIFIED"
    elif missing:
        status = "OBJECTIVE_COVERAGE_INCOMPLETE_MISSING_EVIDENCE"
    else:
        status = "OBJECTIVE_COVERAGE_READY_USER_AB_PENDING"

    return {
        "schema": "goal02-objective-coverage-audit-v1",
        "created_at": now_utc(),
        "root": str(root),
        "status": status,
        "complete": complete,
        "non_user_requirements_passed": non_user_requirements_passed,
        "pass_count": pass_count,
        "total_count": len(items),
        "missing_count": len(missing),
        "blocked_count": len(blocked),
        "items": items,
        "claim_policy": "Objective coverage only; no listening or final-master claim without user A/B approval and final delivery evidence.",
    }


def write_report(path: Path, audit: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 Objective Coverage Audit",
        "",
        f"- Created UTC: `{audit['created_at']}`",
        f"- Status: `{audit['status']}`",
        f"- Complete: `{audit['complete']}`",
        f"- Non-user requirements passed: `{audit['non_user_requirements_passed']}`",
        f"- Pass: `{audit['pass_count']}` / `{audit['total_count']}`",
        f"- Missing: `{audit['missing_count']}`",
        f"- Blocked: `{audit['blocked_count']}`",
        f"- Claim policy: `{audit['claim_policy']}`",
        "",
        "## Coverage Items",
        "",
        "| id | status | evidence | notes |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["items"]:
        notes = str(item.get("notes", "")).replace("|", "\\|")
        lines.append(f"| `{item['id']}` | `{item['status']}` | `{item['evidence']}` | {notes} |")
    lines.extend(["", "## Remaining Proof", ""])
    blocked = [item for item in audit["items"] if item["status"] == "BLOCKED"]
    if blocked:
        lines.extend(f"- `{item['id']}`: {item['requirement']}" for item in blocked)
    else:
        lines.append("- No blocked coverage items remain.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    audit = audit_objective_coverage(args.root)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / "goal02_objective_coverage_audit.json"
    md_path = args.report_dir / "goal02_objective_coverage_audit.md"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(md_path, audit)
    audit["json_path"] = str(json_path)
    audit["report_path"] = str(md_path)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Goal 02 against the full user objective.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()
    audit = run(args)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "complete": audit["complete"],
                "non_user_requirements_passed": audit["non_user_requirements_passed"],
                "pass_count": audit["pass_count"],
                "total_count": audit["total_count"],
                "missing_count": audit["missing_count"],
                "blocked_count": audit["blocked_count"],
                "report_path": audit["report_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if audit["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
