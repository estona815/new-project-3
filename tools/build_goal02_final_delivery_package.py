#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECISION_RECORD = ROOT / "reports" / "goal02_user_ab_decision" / "goal02_user_ab_decision.json"
DEFAULT_REVIEW_PACKAGE = ROOT / "reports" / "goal02_v04_user_ab_review" / "goal02_v04_review_package.json"
DEFAULT_OUTPUT_DIR = ROOT / "delivery" / "goal02_final_delivery"
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_final_delivery"
DEFAULT_ZIP_NAME = "goal02_FINAL_DELIVERY_APPROVED_ONLY.zip"


FINAL_PROFILES = {
    "loud_reference_and_safe_streaming": [
        ("full_song_loud_wav", "audio/GOAL02_v04_FINAL_LOUD_REFERENCE_24-48.wav", "final loud reference WAV"),
        ("full_song_loud_mp3", "audio/GOAL02_v04_FINAL_LOUD_REFERENCE_320k.mp3", "final loud reference MP3"),
        ("full_song_safe_wav", "audio/GOAL02_v04_FINAL_SAFE_STREAMING_24-48.wav", "final safe streaming WAV"),
        ("full_song_safe_mp3", "audio/GOAL02_v04_FINAL_SAFE_STREAMING_320k.mp3", "final safe streaming MP3"),
    ],
    "safe_streaming": [
        ("full_song_safe_wav", "audio/GOAL02_v04_FINAL_SAFE_STREAMING_24-48.wav", "final safe streaming WAV"),
        ("full_song_safe_mp3", "audio/GOAL02_v04_FINAL_SAFE_STREAMING_320k.mp3", "final safe streaming MP3"),
    ],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def copy_file(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def review_files_by_label(review_package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("label")): row for row in review_package.get("files", [])}


def is_approval_decision(decision: dict[str, Any]) -> bool:
    return (
        decision.get("decision") in {"approve_v04_20s_then_extend_final", "approve_safe_only"}
        and decision.get("ready_for_final_export_prep") is True
        and not decision.get("blockers")
    )


def blocker_status(decision: dict[str, Any]) -> str:
    if decision.get("decision") == "pending":
        return "BLOCKED_USER_AB_APPROVAL_REQUIRED"
    if decision.get("approval_state") == "revision_requested":
        return "BLOCKED_USER_REVISION_REQUIRED"
    return "BLOCKED_FINAL_EXPORT_PREP_NOT_READY"


def package_rows_for_profile(review_package: dict[str, Any], profile: str, output_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    lookup = review_files_by_label(review_package)
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    for label, package_path, role in FINAL_PROFILES.get(profile, []):
        source_row = lookup.get(label)
        if not source_row:
            blockers.append(f"review_package_label_missing:{label}")
            continue
        source = Path(str(source_row.get("absolute_path") or ""))
        if not source.exists():
            blockers.append(f"review_package_file_missing:{label}")
            continue
        dest = output_dir / package_path
        copy_file(source, dest)
        rows.append(
            {
                "label": label,
                "role": role,
                "type": "audio",
                "source_path": str(source),
                "package_path": package_path,
                "absolute_path": str(dest),
                "size_bytes": dest.stat().st_size,
                "sha256": sha256(dest),
            }
        )
    return rows, blockers


def evidence_rows(decision_record_path: Path, review_package_path: Path, review_package: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sources: list[Path] = [decision_record_path, review_package_path]
    for path in [decision_record_path.with_suffix(".md"), review_package_path.with_suffix(".md")]:
        if path.exists():
            sources.append(path)
    for row in review_package.get("files", []):
        if row.get("type") == "evidence":
            path = Path(str(row.get("absolute_path") or ""))
            if path.exists():
                sources.append(path)
    seen: set[Path] = set()
    for source in sources:
        source = source.resolve()
        if source in seen:
            continue
        seen.add(source)
        dest_name = source.name
        dest = output_dir / "evidence" / dest_name
        if dest.exists():
            dest = output_dir / "evidence" / f"{source.stem}_{len(rows) + 1}{source.suffix}"
        copy_file(source, dest)
        rows.append(
            {
                "label": dest.stem,
                "role": "final delivery evidence",
                "type": "evidence",
                "source_path": str(source),
                "package_path": str(dest.relative_to(output_dir)),
                "absolute_path": str(dest),
                "size_bytes": dest.stat().st_size,
                "sha256": sha256(dest),
            }
        )
    return rows


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 Final Delivery Gate",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        f"- Decision: `{result['decision'].get('decision')}`",
        f"- Final export profile: `{result.get('final_export_profile')}`",
        f"- ZIP: `{result.get('zip_path', '')}`",
        f"- ZIP test: `{result.get('zip_test_status', '')}`",
        f"- Safe to claim final delivery: `{result['safe_to_claim_final_delivery']}`",
        "- Claim policy: `requires explicit user A/B approval plus final package evidence`",
        "",
        "## Blockers",
        "",
    ]
    if result["blockers"]:
        lines.extend(f"- `{item}`" for item in result["blockers"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Files", "", "| type | package path | bytes | sha256 |", "| --- | --- | ---: | --- |"])
    for row in result.get("files", []):
        lines.append(f"| `{row['type']}` | `{row['package_path']}` | `{row['size_bytes']}` | `{row['sha256']}` |")
    lines.extend(["", "## Notes", ""])
    if result["status"].startswith("BLOCKED"):
        lines.append("- No final delivery ZIP was created because the approval/revision gate is not satisfied.")
    else:
        lines.append("- Final ZIP contains approved full-song audio only; A/B reference sequences are excluded from final delivery.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip(output_dir: Path, zip_path: Path) -> tuple[str, int, str | None]:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            archive.write(path, path.relative_to(output_dir))
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
    return ("passed" if bad is None else "failed"), zip_path.stat().st_size, bad


def build_final_delivery(
    *,
    decision_record_path: Path,
    review_package_path: Path,
    output_dir: Path,
    report_dir: Path,
    zip_name: str = DEFAULT_ZIP_NAME,
) -> dict[str, Any]:
    decision = load_json(decision_record_path)
    review_package = load_json(review_package_path)
    output_dir = output_dir.resolve()
    report_dir = report_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    for stale in [
        output_dir / "audio",
        output_dir / "evidence",
        output_dir / "checksums.sha256",
        output_dir / "goal02_final_delivery_manifest.json",
        output_dir / "goal02_final_delivery_manifest.csv",
    ]:
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()

    blockers: list[str] = []
    final_export_profile = decision.get("final_export_profile")
    if not is_approval_decision(decision):
        blockers.extend(decision.get("blockers") or ["user_ab_approval_not_recorded"])
        status = blocker_status(decision)
        files: list[dict[str, Any]] = []
        zip_path = output_dir / zip_name
    elif final_export_profile not in FINAL_PROFILES:
        blockers.append(f"unsupported_final_export_profile:{final_export_profile}")
        status = "BLOCKED_UNSUPPORTED_FINAL_EXPORT_PROFILE"
        files = []
        zip_path = output_dir / zip_name
    else:
        status = "FINAL_DELIVERY_PACKAGE_READY"
        files, blockers = package_rows_for_profile(review_package, str(final_export_profile), output_dir)
        if blockers:
            status = "BLOCKED_FINAL_AUDIO_SOURCE_MISSING"
        else:
            files.extend(evidence_rows(decision_record_path, review_package_path, review_package, output_dir))
        zip_path = output_dir / zip_name

    result: dict[str, Any] = {
        "schema": "goal02-final-delivery-package-v1",
        "created_at": now_utc(),
        "status": status,
        "decision": decision,
        "review_package_status": review_package.get("status"),
        "final_export_profile": final_export_profile,
        "output_dir": str(output_dir),
        "report_dir": str(report_dir),
        "zip_path": str(zip_path),
        "safe_to_claim_final_delivery": status == "FINAL_DELIVERY_PACKAGE_READY",
        "blockers": blockers,
        "files": files,
    }

    if status == "FINAL_DELIVERY_PACKAGE_READY":
        manifest_path = output_dir / "goal02_final_delivery_manifest.json"
        csv_path = output_dir / "goal02_final_delivery_manifest.csv"
        checksums_path = output_dir / "checksums.sha256"
        write_csv(csv_path, files)
        files.append(
            {
                "label": "manifest_csv",
                "role": "final delivery file table",
                "type": "manifest",
                "source_path": "",
                "package_path": str(csv_path.relative_to(output_dir)),
                "absolute_path": str(csv_path),
                "size_bytes": csv_path.stat().st_size,
                "sha256": sha256(csv_path),
            }
        )
        checksums_path.write_text("".join(f"{row['sha256']}  {row['package_path']}\n" for row in files), encoding="utf-8")
        files.append(
            {
                "label": "checksums",
                "role": "final delivery checksums",
                "type": "manifest",
                "source_path": "",
                "package_path": "checksums.sha256",
                "absolute_path": str(checksums_path),
                "size_bytes": checksums_path.stat().st_size,
                "sha256": sha256(checksums_path),
            }
        )
        result["files"] = files
        result["manifest_json_note"] = "Manifest JSON is self-describing and not included in checksums."
        manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        zip_status, zip_size, bad = build_zip(output_dir, zip_path)
        result["zip_test_status"] = zip_status
        result["zip_bad_file"] = bad
        result["zip_size_bytes"] = zip_size
        result["zip_sha256"] = sha256(zip_path)
    else:
        result["zip_test_status"] = "not_created"
        result["zip_bad_file"] = None
        result["zip_size_bytes"] = 0
        result["zip_sha256"] = None

    report_json = report_dir / "goal02_final_delivery_gate.json"
    report_md = report_dir / "goal02_final_delivery_gate.md"
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(report_md, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Goal 02 final delivery package only after explicit A/B approval.")
    parser.add_argument("--decision-record", type=Path, default=DEFAULT_DECISION_RECORD)
    parser.add_argument("--review-package", type=Path, default=DEFAULT_REVIEW_PACKAGE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--zip-name", default=DEFAULT_ZIP_NAME)
    args = parser.parse_args()
    result = build_final_delivery(
        decision_record_path=args.decision_record,
        review_package_path=args.review_package,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        zip_name=args.zip_name,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "safe_to_claim_final_delivery": result["safe_to_claim_final_delivery"],
                "blockers": result["blockers"],
                "zip_path": result.get("zip_path"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["status"] == "FINAL_DELIVERY_PACKAGE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
