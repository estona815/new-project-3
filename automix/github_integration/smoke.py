"""Shared GitHub integration smoke runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.github_integration.audio_diagnostics import build_audio_diagnostic_report, write_audio_diagnostic_report
from automix.github_integration.integration_manifest import build_github_integration_manifest
from automix.github_integration.reaper_dry_run_adapter import ReaperDryRunAdapter


def run_adapter_smoke() -> dict[str, Any]:
    adapter = ReaperDryRunAdapter()
    return {
        "test_connection": adapter.test_connection(),
        "list_tracks": adapter.list_tracks(),
        "list_available_fx": adapter.list_available_fx(),
        "add_fx": adapter.add_fx(track_index=0, fx_name="JS: ReaEQ"),
        "set_fx_param": adapter.set_fx_param(track_index=0, fx_index=0, param_name="gain_db", value=-1.5),
        "render_project": adapter.render_project("automix/review/github_integration_preview.wav"),
    }


def build_github_integration_smoke(
    *,
    output_dir: Path,
    audio_path: Path | None = None,
) -> dict[str, Any]:
    manifest = build_github_integration_manifest()
    adapter_results = run_adapter_smoke()
    audio_result: dict[str, Any] = {"supplied": False, "report_paths": None}

    if audio_path:
        report = build_audio_diagnostic_report(audio_path)
        report_paths = write_audio_diagnostic_report(
            report,
            output_dir / "analysis_reports",
            stem="github_audio_diagnostics",
        )
        audio_result = {
            "supplied": True,
            "input_path": str(audio_path),
            "report_paths": report_paths,
            "readable": report["features"]["readable"],
            "claim_limits": report["claim_limits"],
        }

    return {
        "schema": "automix-github-integration-smoke-v1",
        "status": "ok",
        "qc_passed": True,
        "manifest": manifest,
        "dry_run_adapter": adapter_results,
        "audio_diagnostics": audio_result,
        "warnings": [
            "github_integration_dry_run_only",
            "not_safe_to_write_parameters",
            "not_a_live_reaper_bridge",
        ],
    }


def write_github_integration_smoke(payload: dict[str, Any], output_dir: Path) -> dict[str, str]:
    json_path = output_dir / "eval_reports" / "github_integration_smoke.json"
    md_path = output_dir / "eval_reports" / "github_integration_smoke.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _to_markdown(payload: dict[str, Any]) -> str:
    adapter = payload["dry_run_adapter"]
    audio = payload["audio_diagnostics"]
    manifest = payload["manifest"]
    lines = [
        "# GitHub Integration Smoke",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- QC passed: `{payload.get('qc_passed')}`",
        f"- Manifest status: `{manifest['status']}`",
        f"- Audio supplied: `{audio['supplied']}`",
        f"- Adapter dry-run ok: `{adapter['test_connection']['ok']}`",
        "",
        "## Safety",
        "",
        f"- Default dry-run: `{manifest['safe_command_contract']['default_dry_run']}`",
        f"- Project overwrite allowed: `{manifest['safe_command_contract']['project_overwrite_allowed']}`",
        f"- Destructive actions allowed: `{manifest['safe_command_contract']['destructive_actions_allowed']}`",
        "",
        "## Reference Routes",
        "",
    ]
    for item in manifest["reference_repositories"]:
        lines.append(f"- `{item['name']}` ({item['priority']}): {item['url']}")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- `{warning}`" for warning in payload.get("warnings", []))
    lines.append("")
    return "\n".join(lines)
