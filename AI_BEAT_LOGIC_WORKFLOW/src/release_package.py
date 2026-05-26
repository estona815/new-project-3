from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from production_intent_resolver import RELEASE_READY_LIMITATION


REQUIRED_RELEASE_FILES = (
    "final_wav",
    "qc_report",
    "master_qc_report",
    "audio_render_manifest",
    "autopilot_qc_report",
    "commercial_readiness_report",
    "release_qc_report",
    "release_metadata",
    "release_checklist",
    "safety_notes",
)


def _exists(path: str | Path | None) -> bool:
    return bool(path) and Path(path).exists() and Path(path).stat().st_size > 0


def build_release_package(
    *,
    final_wav_path: str | Path,
    qc_report_path: str | Path,
    master_qc_report_path: str | Path,
    audio_render_manifest_path: str | Path,
    autopilot_qc: dict[str, Any],
    autopilot_qc_paths: dict[str, Path],
    production_intent: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
    completion_gate: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verification = verification or {}
    gate = completion_gate or {}
    files = {
        "final_wav": str(final_wav_path),
        "qc_report": str(qc_report_path),
        "master_qc_report": str(master_qc_report_path),
        "audio_render_manifest": str(audio_render_manifest_path),
        "autopilot_qc_report": str(autopilot_qc_paths.get("autopilot_qc_report", "")),
        "commercial_readiness_report": str(autopilot_qc_paths.get("commercial_readiness_report", "")),
        "release_qc_report": None,
        "release_metadata": None,
        "release_checklist": None,
        "safety_notes": None,
    }
    file_status = {name: _exists(path) for name, path in files.items() if path}
    commercial = autopilot_qc.get("commercial_readiness_qc", {})
    false_claim = commercial.get("false_claim_risk", {})
    safety = commercial.get("safety", {})
    blocking = []
    if not bool(verification.get("ok") or verification.get("passed")):
        blocking.append("final WAV verification did not pass")
    if false_claim.get("high"):
        blocking.append("false-claim risk is high")
    if not safety.get("safe", True):
        blocking.append("commercial safety QC is not safe")
    if commercial.get("status") not in {"FINAL_PASS", "PLAN_PASS"}:
        blocking.append(f"commercial readiness status is {commercial.get('status')}")
    if not gate.get("complete"):
        blocking.append("base completion gate has not passed before release packaging")
    return {
        "schema_version": "release_package.v1",
        "release_ready": not blocking,
        "release_ready_definition": RELEASE_READY_LIMITATION,
        "not_distribution_approval": True,
        "not_commercial_success_guarantee": True,
        "workflow": (options or {}).get("workflow"),
        "mode": (options or {}).get("mode"),
        "files": files,
        "file_status": file_status,
        "verification_summary": {
            "sample_rate": verification.get("sample_rate"),
            "bit_depth": verification.get("bit_depth"),
            "peak_dbfs": verification.get("peak_dbfs"),
            "rms_dbfs": verification.get("rms_dbfs"),
            "clipping_count": verification.get("clipping_count"),
            "format_verified": bool(verification.get("format_verified")),
        },
        "commercial_readiness_status": commercial.get("status"),
        "completion_gate_complete": bool(gate.get("complete")),
        "production_intent_summary": {
            "target_elements": (production_intent or {}).get("target_elements", []),
            "copying_risk": ((production_intent or {}).get("safety") or {}).get("copying_risk"),
            "exact_copy_allowed": bool(((production_intent or {}).get("safety") or {}).get("exact_copy_allowed")),
        },
        "blocking_reasons": blocking,
        "remaining_limitations": [
            RELEASE_READY_LIMITATION,
            "A human listening pass is still recommended before public release.",
            "Distribution-platform acceptance, rights clearance, and commercial performance are outside this local QC gate.",
            "Any Logic/plugin/stem claims require verified artifacts, not just plans.",
        ],
    }


def render_release_checklist(package: dict[str, Any]) -> str:
    lines = [
        "# Release-Ready Checklist",
        "",
        f"- release-ready package pass: {str(bool(package.get('release_ready'))).lower()}",
        f"- commercial readiness status: {package.get('commercial_readiness_status')}",
        f"- completion gate complete before packaging: {str(bool(package.get('completion_gate_complete'))).lower()}",
        f"- meaning: {package.get('release_ready_definition')}",
        "",
        "## Files",
    ]
    for name in REQUIRED_RELEASE_FILES:
        status = package.get("file_status", {}).get(name, False)
        path = package.get("files", {}).get(name)
        lines.append(f"- {name}: {'present' if status else 'missing'} ({path or 'not written yet'})")
    blocking = [f"- {item}" for item in package.get("blocking_reasons", [])] or ["- none"]
    lines.extend(
        [
            "",
            "## Remaining Limitations",
            *[f"- {item}" for item in package.get("remaining_limitations", [])],
            "",
            "## Blocking Reasons",
            *blocking,
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_safety_notes(package: dict[str, Any]) -> str:
    summary = package.get("production_intent_summary", {})
    return "\n".join(
        [
            "# Release Safety Notes",
            "",
            "- Reference prompts are high-level production targets only.",
            "- Exact songs, kick samples, basslines, melodies, lyrics, drum patterns, sound recordings, and living artist vocal identity are not copied.",
            "- Stereo-only processing does not claim stem-level remixing, guaranteed vocal removal, true kick/bass replacement, true drum rewrite, true stem separation, or plugin insertion.",
            "- Logic Pro automation/plugin success is not claimed without verified artifacts.",
            f"- Copying risk: {summary.get('copying_risk') or 'not provided'}",
            f"- Exact copy allowed: {str(bool(summary.get('exact_copy_allowed'))).lower()}",
            f"- Release-ready scope: {package.get('release_ready_definition')}",
        ]
    ).rstrip() + "\n"


def render_release_qc_report(package: dict[str, Any]) -> str:
    verification = package.get("verification_summary", {})
    return "\n".join(
        [
            "# Release QC Report",
            "",
            f"- release package ready: {str(bool(package.get('release_ready'))).lower()}",
            f"- commercial readiness status: {package.get('commercial_readiness_status')}",
            f"- completion gate complete before package: {str(bool(package.get('completion_gate_complete'))).lower()}",
            f"- sample rate: {verification.get('sample_rate')}",
            f"- bit depth: {verification.get('bit_depth')}",
            f"- peak dBFS: {verification.get('peak_dbfs')}",
            f"- RMS dBFS: {verification.get('rms_dbfs')}",
            f"- clipping count: {verification.get('clipping_count')}",
            f"- format verified: {str(bool(verification.get('format_verified'))).lower()}",
            "",
            "## Scope",
            f"- {package.get('release_ready_definition')}",
            "- This local release QC does not guarantee distribution approval, rights clearance, playlist placement, sales, charting, or commercial success.",
            "",
            "## Blocking Reasons",
            *([f"- {item}" for item in package.get("blocking_reasons", [])] or ["- none"]),
            "",
            "## Remaining Limitations",
            *[f"- {item}" for item in package.get("remaining_limitations", [])],
        ]
    ).rstrip() + "\n"


def write_release_package(
    project_root: str | Path,
    package: dict[str, Any],
) -> dict[str, Path]:
    root = Path(project_root)
    report_dir = root / "06_QC_REPORT"
    report_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": report_dir / "release_package_manifest.json",
        "metadata": report_dir / "release_metadata.json",
        "checklist": report_dir / "release_checklist.md",
        "safety_notes": report_dir / "release_safety_notes.md",
        "release_qc_report": report_dir / "release_qc_report.md",
    }
    package = {
        **package,
        "files": {
            **package.get("files", {}),
            "release_metadata": str(paths["metadata"]),
            "release_checklist": str(paths["checklist"]),
            "safety_notes": str(paths["safety_notes"]),
            "release_qc_report": str(paths["release_qc_report"]),
        },
    }
    paths["metadata"].write_text(
        json.dumps(
            {
                "schema_version": "release_metadata.v1",
                "workflow": package.get("workflow"),
                "mode": package.get("mode"),
                "release_ready_definition": package.get("release_ready_definition"),
                "verification_summary": package.get("verification_summary", {}),
                "not_distribution_approval": True,
                "not_commercial_success_guarantee": True,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["safety_notes"].write_text(render_safety_notes(package), encoding="utf-8")
    paths["release_qc_report"].write_text(render_release_qc_report(package), encoding="utf-8")
    anticipated_status = {name: _exists(path) for name, path in package["files"].items() if path}
    anticipated_status["release_checklist"] = True
    package["file_status"] = anticipated_status
    package["release_ready"] = bool(package.get("release_ready") and all(anticipated_status.get(name) for name in REQUIRED_RELEASE_FILES))
    if not package["release_ready"] and "release package files are incomplete" not in package.get("blocking_reasons", []):
        missing = [name for name in REQUIRED_RELEASE_FILES if not package["file_status"].get(name)]
        if missing:
            package.setdefault("blocking_reasons", []).append(f"release package files are incomplete: {', '.join(missing)}")
    paths["checklist"].write_text(render_release_checklist(package), encoding="utf-8")
    package["file_status"] = {name: _exists(path) for name, path in package["files"].items() if path}
    paths["manifest"].write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return paths
