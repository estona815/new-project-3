from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


CLAIM_LANGUAGE_SCHEMA = "automix-claim-language-guard-v1"

SCAN_SUFFIXES = {".md", ".txt", ".json"}

ROOT_DOCS_TO_SCAN = [
    "README.md",
    "QUICKSTART.md",
    "PIPELINE_ARCHITECTURE.md",
    "AUDIO_ENGINEERING_NOTES.md",
    "SUNO_AI_ARTIFACT_STRATEGY.md",
    "VOCAL_FIRST_MIXING_STRATEGY.md",
    "MASTERING_QC_STANDARD.md",
    "USER_FEEDBACK_REVISION_LOOP.md",
    "TESTING_AND_HARNESS.md",
    "PLUGIN_FALLBACKS.md",
    "TROUBLESHOOTING.md",
    "CHANGELOG.md",
]

OUTPUT_SCAN_DIRS = [
    "analysis_reports",
    "eval_reports",
    "review",
    "export",
]

SAFE_CONTEXT_MARKERS = [
    "do not",
    "don't",
    "avoid",
    "must not",
    "cannot",
    "not ",
    "unsupported",
    "blocked",
    "금지",
    "피하",
    "하지 말",
    "아님",
]

CLAIM_PATTERNS = [
    {
        "claim_id": "total_artifact_removal_claim",
        "severity": "blocker",
        "phrases": [
            "100% removed",
            "100 percent removed",
            "remove all ai",
            "all ai artifacts removed",
            "total artifact removal",
            "perfect cleanup",
            "완전 제거",
            "전부 제거",
            "100% 제거",
        ],
    },
    {
        "claim_id": "unsupported_commercial_master_claim",
        "severity": "blocker",
        "phrases": [
            "commercial master quality achieved",
            "guaranteed commercial",
            "commercially finished",
            "상업음원 수준 완성",
            "상업음원처럼 완성",
        ],
    },
    {
        "claim_id": "unsupported_reference_match_claim",
        "severity": "blocker",
        "phrases": [
            "identical reference match",
            "reference matched perfectly",
            "same as the reference",
            "레퍼런스와 동일",
            "레퍼런스 완전 일치",
        ],
    },
    {
        "claim_id": "unsupported_listening_claim",
        "severity": "blocker",
        "phrases": [
            "listening approved",
            "user approved final",
            "human approved final",
            "청감 승인 완료",
            "사용자 승인 완료",
        ],
    },
]

GENERATED_AUDIT_FILES_TO_SKIP = {
    "claim_language_guard.json",
    "claim_language_guard.md",
    "professional_readiness_audit.json",
    "professional_readiness_audit.md",
}


def _safe_context(line_lc: str) -> bool:
    return any(marker in line_lc for marker in SAFE_CONTEXT_MARKERS)


def _scan_file(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return findings
    for index, line in enumerate(lines, start=1):
        line_lc = line.lower()
        if _safe_context(line_lc):
            continue
        for pattern in CLAIM_PATTERNS:
            for phrase in pattern["phrases"]:
                if phrase.lower() in line_lc:
                    findings.append(
                        {
                            "claim_id": pattern["claim_id"],
                            "severity": pattern["severity"],
                            "phrase": phrase,
                            "path": str(path),
                            "line": index,
                            "excerpt": line.strip()[:220],
                        }
                    )
    return findings


def _candidate_files(*, workspace_root: Path, output_dir: Path) -> list[Path]:
    files: list[Path] = []
    for rel in ROOT_DOCS_TO_SCAN:
        path = workspace_root / rel
        if path.exists():
            files.append(path)
    for rel in OUTPUT_SCAN_DIRS:
        directory = output_dir / rel
        if not directory.exists():
            continue
        files.extend(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and path.suffix.lower() in SCAN_SUFFIXES
            and path.name not in GENERATED_AUDIT_FILES_TO_SKIP
        )
    return sorted(set(files))


def run_claim_language_guard(*, workspace_root: Path, output_dir: Path) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    output_dir = Path(output_dir)
    files = _candidate_files(workspace_root=workspace_root, output_dir=output_dir)
    findings = [finding for path in files for finding in _scan_file(path)]
    blockers = sorted({finding["claim_id"] for finding in findings if finding.get("severity") == "blocker"})
    result = {
        "schema": CLAIM_LANGUAGE_SCHEMA,
        "created_at": now_utc(),
        "workspace_root": str(workspace_root),
        "output_dir": str(output_dir),
        "files_scanned": len(files),
        "findings": findings,
        "blockers": blockers,
        "passed": not blockers,
    }
    write_json(output_dir / "eval_reports" / "claim_language_guard.json", result)
    write_claim_language_guard_report(result, output_dir)
    return result


def write_claim_language_guard_report(result: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Claim Language Guard",
        "",
        f"- Created UTC: `{result.get('created_at')}`",
        f"- Passed: `{result.get('passed')}`",
        f"- Files scanned: `{result.get('files_scanned')}`",
        "",
        "This report detects unsupported delivery claims. It does not prove audio quality or user acceptance.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in result.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Findings", ""])
    findings = result.get("findings", [])
    if not findings:
        lines.append("- none")
    for finding in findings:
        lines.append(
            f"- `{finding.get('claim_id')}` `{finding.get('path')}` line `{finding.get('line')}` phrase `{finding.get('phrase')}`"
        )
    path = Path(output_dir) / "eval_reports" / "claim_language_guard.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
