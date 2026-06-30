from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


FIXTURE_COVERAGE_SCHEMA = "automix-fixture-coverage-audit-v1"

AUDIT_REL_PATH = Path("eval_reports/fixture_coverage_audit.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/fixture_coverage_audit.md")

REQUIRED_FIXTURE_CATEGORIES: list[dict[str, str]] = [
    {"category": "clean_vocal", "source": "audio", "description": "clean vocal baseline"},
    {"category": "buried_vocal", "source": "audio", "description": "vocal buried by instrumental masking"},
    {"category": "muddy_vocal", "source": "audio", "description": "low-mid/boxy vocal cleanup target"},
    {"category": "harsh_vocal", "source": "audio", "description": "harsh vocal tone"},
    {"category": "sibilant_vocal", "source": "audio", "description": "sibilance guard"},
    {"category": "suno_high_fizz", "source": "audio", "description": "AI/Suno-like high fizz"},
    {"category": "watery_smear", "source": "audio", "description": "source-separated watery smear"},
    {"category": "fake_stereo_halo", "source": "audio", "description": "fake stereo halo or wide AI smear"},
    {"category": "over_limited_master", "source": "audio", "description": "over-limited master-like fixture"},
    {"category": "low_end_buildup", "source": "audio", "description": "low-end buildup"},
    {"category": "phase_issue", "source": "audio", "description": "phase or mono-compatibility issue"},
    {"category": "missing_plugin", "source": "analysis", "description": "missing or uncertain plugin mapping"},
    {"category": "corrupted_config", "source": "analysis", "description": "corrupted configuration/error fixture"},
    {"category": "dry_run", "source": "analysis", "description": "dry-run only behavior"},
    {"category": "rollback", "source": "analysis", "description": "rollback metadata requirement"},
    {"category": "render_failure", "source": "analysis", "description": "render failure handling"},
    {"category": "feedback_mapping", "source": "analysis", "description": "user feedback to safe action mapping"},
]

INFERENCE_PATTERNS: list[tuple[str, str]] = [
    ("clean_vocal", "clean vocal|raw_vocal"),
    ("buried_vocal", "buried|masking"),
    ("muddy_vocal", "muddy|boxy|low-mid|low_mid"),
    ("harsh_vocal", "harsh"),
    ("sibilant_vocal", "sibilance|sibilant"),
    ("suno_high_fizz", "suno|fizz|thin ai|ai_like|already_tuned"),
    ("watery_smear", "watery|source separated|source-separated|smear"),
    ("fake_stereo_halo", "fake stereo|halo|wide ai"),
    ("over_limited_master", "over-limited|over_limited|limited master"),
    ("low_end_buildup", "low-end|low_end|buildup|sub"),
    ("phase_issue", "phase|mono compatibility|mono-compatibility"),
    ("missing_plugin", "missing plugin|plugin_mapping|adapter_confidence|semantic_control|missing control"),
    ("corrupted_config", "corrupt|parse_error|bad config|bad.json"),
    ("dry_run", "dry-run|dry_run|draft"),
    ("rollback", "rollback"),
    ("render_failure", "render failure|render_failed|render_status"),
    ("feedback_mapping", "feedback|revision"),
]


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return {}, f"read_error:{path}:{exc}"
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{path}:{exc}"


def _normalize_tag(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _as_tags(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_tag(value)} if value.strip() else set()
    if isinstance(value, list):
        return {_normalize_tag(item) for item in value if str(item).strip()}
    return set()


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _infer_tags(*values: Any) -> set[str]:
    text = " ".join(_flatten_text(value) for value in values).lower()
    tags: set[str] = set()
    for tag, pattern in INFERENCE_PATTERNS:
        if re.search(pattern, text):
            tags.add(tag)
    return tags


def _fixture_path(raw_path: str, fixture_root: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return fixture_root / path


def _add_evidence(category_evidence: dict[str, list[dict[str, str]]], category: str, evidence: dict[str, str]) -> None:
    category_evidence.setdefault(category, []).append(evidence)


def _collect_audio_evidence(fixture_root: Path, category_evidence: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    manifest_path = fixture_root / "audio_fixture_manifest.json"
    manifest, error = _load_json(manifest_path)
    missing_audio_files: list[str] = []
    invalid_audio_fixtures: list[str] = []
    if not isinstance(manifest, dict):
        error = error or f"json_type_error:{manifest_path}:expected_object"
        fixtures = []
    else:
        fixtures = manifest.get("fixtures", []) if isinstance(manifest.get("fixtures"), list) else []
    for item in fixtures:
        if not isinstance(item, dict):
            invalid_audio_fixtures.append("non_dict_audio_fixture")
            continue
        raw_path = str(item.get("path", ""))
        path = _fixture_path(raw_path, fixture_root) if raw_path else Path("")
        if not raw_path or not path.exists():
            missing_audio_files.append(str(path) if raw_path else "<missing path>")
        tags = _as_tags(item.get("coverage_tags")) | _infer_tags(item.get("path"), item.get("expected"), item)
        evidence = {
            "source": "audio",
            "path": str(path),
            "name": path.name or str(item.get("path", "")),
            "expected": str(item.get("expected", "")),
        }
        for tag in tags:
            _add_evidence(category_evidence, tag, evidence)
    return {
        "manifest_path": str(manifest_path),
        "manifest_found": manifest_path.exists(),
        "manifest_error": error,
        "fixtures_checked": len(fixtures),
        "missing_audio_files": sorted(set(missing_audio_files)),
        "invalid_audio_fixtures": invalid_audio_fixtures,
    }


def _collect_analysis_evidence(fixture_root: Path, category_evidence: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    analysis_dir = fixture_root / "analysis_json"
    paths = sorted(path for path in analysis_dir.glob("*.json") if path.is_file()) if analysis_dir.exists() else []
    invalid_analysis_fixtures: list[str] = []
    for path in paths:
        data, error = _load_json(path)
        if error:
            invalid_analysis_fixtures.append(error)
            continue
        if not isinstance(data, dict):
            invalid_analysis_fixtures.append(f"json_type_error:{path}:expected_object")
            continue
        tags = _as_tags(data.get("coverage_tags")) | _infer_tags(path.name, data)
        evidence = {
            "source": "analysis",
            "path": str(path),
            "name": str(data.get("name", path.stem)),
            "expected_decision": str(data.get("expected_decision", "")),
        }
        for tag in tags:
            _add_evidence(category_evidence, tag, evidence)
    return {
        "analysis_dir": str(analysis_dir),
        "analysis_dir_found": analysis_dir.exists(),
        "fixtures_checked": len(paths),
        "invalid_analysis_fixtures": invalid_analysis_fixtures,
    }


def build_fixture_coverage_audit(
    *,
    project_name: str,
    output_dir: Path,
    fixture_root: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    fixture_root = Path(fixture_root) if fixture_root else Path("tests/automix_validation/fixtures")
    required_categories = [item["category"] for item in REQUIRED_FIXTURE_CATEGORIES]
    category_evidence: dict[str, list[dict[str, str]]] = {category: [] for category in required_categories}
    audio_summary = _collect_audio_evidence(fixture_root, category_evidence)
    analysis_summary = _collect_analysis_evidence(fixture_root, category_evidence)
    covered_categories = sorted(category for category in required_categories if category_evidence.get(category))
    missing_categories = sorted(category for category in required_categories if not category_evidence.get(category))
    blockers: list[str] = []
    warnings: list[str] = []
    if not audio_summary["manifest_found"]:
        blockers.append(f"audio_fixture_manifest_missing:{audio_summary['manifest_path']}")
    if audio_summary.get("manifest_error"):
        blockers.append(str(audio_summary["manifest_error"]))
    for path in audio_summary.get("missing_audio_files", []):
        blockers.append(f"audio_fixture_file_missing:{path}")
    for item in audio_summary.get("invalid_audio_fixtures", []):
        blockers.append(f"invalid_audio_fixture:{item}")
    if not analysis_summary["analysis_dir_found"]:
        blockers.append(f"analysis_fixture_dir_missing:{analysis_summary['analysis_dir']}")
    for item in analysis_summary.get("invalid_analysis_fixtures", []):
        blockers.append(f"invalid_analysis_fixture:{item}")
    for category in missing_categories:
        blockers.append(f"required_fixture_category_missing:{category}")
    if not blockers:
        warnings.append("fixture_coverage_complete_static_only")
    audit = {
        "schema": FIXTURE_COVERAGE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "fixture_root": str(fixture_root),
        "required_categories": REQUIRED_FIXTURE_CATEGORIES,
        "covered_categories": covered_categories,
        "missing_categories": missing_categories,
        "category_evidence": category_evidence,
        "audio": audio_summary,
        "analysis": analysis_summary,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "passed": not blockers,
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_fixture_coverage_report(audit, output_dir)
    return audit


def write_fixture_coverage_report(audit: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Fixture Coverage Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Passed: `{audit.get('passed')}`",
        f"- Fixture root: `{audit.get('fixture_root')}`",
        f"- Audio fixtures checked: `{audit.get('audio', {}).get('fixtures_checked')}`",
        f"- Analysis fixtures checked: `{audit.get('analysis', {}).get('fixtures_checked')}`",
        f"- Categories covered: `{len(audit.get('covered_categories', []))}/{len(audit.get('required_categories', []))}`",
        "",
        "This report audits fixture coverage only. It does not prove audio quality, render quality, or user acceptance.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Missing Categories", ""])
    lines.extend([f"- `{item}`" for item in audit.get("missing_categories", [])] or ["- none"])
    lines.extend(["", "## Category Evidence", ""])
    evidence = audit.get("category_evidence", {})
    for required in audit.get("required_categories", []):
        category = required.get("category")
        items = evidence.get(category, [])
        label = required.get("description", category)
        lines.extend([f"### {category}", "", f"- Description: `{label}`"])
        if not items:
            lines.extend(["- Evidence: `missing`", ""])
            continue
        for item in items[:4]:
            lines.append(f"- `{item.get('source')}` `{item.get('name')}`")
        if len(items) > 4:
            lines.append(f"- plus `{len(items) - 4}` more")
        lines.append("")
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
