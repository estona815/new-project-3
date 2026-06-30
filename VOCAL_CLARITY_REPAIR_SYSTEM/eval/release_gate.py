from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .audio_metrics import save_json
from .preset_policy import RELEASE_POLICY_PATH, load_release_policy


CRITICAL_SAFETY_TAGS = {"nan_inf", "clipping", "plugin_crash", "invalid_model_output"}


def _scores(files: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for entry in files:
        score = entry.get("scores", {}).get(key)
        if isinstance(score, (int, float)):
            values.append(float(score))
    return values


def summarize_run(report: dict[str, Any]) -> dict[str, Any]:
    files = list(report.get("files", []))
    score_keys = sorted({key for entry in files for key in entry.get("scores", {})})
    average_scores = {key: mean(_scores(files, key)) for key in score_keys if _scores(files, key)}
    worst_scores = {key: min(_scores(files, key)) for key in score_keys if _scores(files, key)}
    failure_tags = sorted({tag for entry in files for tag in entry.get("failures", [])})
    warning_tags = sorted({tag for entry in files for tag in entry.get("warnings", [])})
    categories = sorted({entry.get("category", "unknown") for entry in files})
    return {
        "preset": report.get("preset", "unknown"),
        "file_count": len(files),
        "summary": report.get("summary", {}),
        "average_scores": average_scores,
        "worst_scores": worst_scores,
        "failure_tags": failure_tags,
        "warning_tags": warning_tags,
        "categories": categories
    }


def evaluate_run_report(report: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_release_policy()
    summary = summarize_run(report)
    preset = summary["preset"]
    gate = policy.get("preset_gates", {}).get(preset)
    blockers: list[str] = []
    warnings: list[str] = []

    if gate is None:
        blockers.append(f"unknown_preset:{preset}")
        gate = {}

    quality_report_only = bool(gate.get("quality_report_only"))
    safety_only = preset == policy.get("strong_preset") or quality_report_only

    if summary["file_count"] <= 0:
        blockers.append("no_eval_files")

    fail_count = int(summary.get("summary", {}).get("fail_count", 0) or 0)
    if fail_count > 0 and not safety_only:
        blockers.append("evaluation_failures_present")
    elif fail_count > 0:
        warnings.append("quality_failures_reported_for_strong_mode")

    critical_tags = sorted(CRITICAL_SAFETY_TAGS.intersection(summary["failure_tags"]))
    if critical_tags:
        blockers.extend(f"safety_failure:{tag}" for tag in critical_tags)

    for score_key, required in gate.get("minimum_average_scores", {}).items():
        actual = summary["average_scores"].get(score_key)
        if actual is None:
            blockers.append(f"missing_average_score:{score_key}")
        elif actual < float(required):
            blockers.append(f"average_{score_key}_below_gate:{actual:.1f}<{float(required):.1f}")

    for score_key, required in gate.get("minimum_worst_scores", {}).items():
        actual = summary["worst_scores"].get(score_key)
        if actual is None:
            blockers.append(f"missing_worst_score:{score_key}")
        elif actual < float(required):
            blockers.append(f"worst_{score_key}_below_gate:{actual:.1f}<{float(required):.1f}")

    if preset == policy.get("default_preset") and "clean_input_damage" in summary["warning_tags"]:
        blockers.append("default_clean_input_damage_warning")

    if preset == policy.get("strong_preset"):
        warnings.append("strong_mode_quality_report_only")

    return {
        "preset": preset,
        "status": "pass" if not blockers else "fail",
        "quality_report_only": quality_report_only,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "summary": summary
    }


def evaluate_release_candidate(reports: list[dict[str, Any]], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_release_policy()
    by_preset = {report.get("preset"): report for report in reports}
    required_presets = list(policy.get("release_presets", []))
    missing = [preset for preset in required_presets if preset not in by_preset]
    run_results = [
        evaluate_run_report(report, policy)
        for preset, report in sorted(by_preset.items())
        if preset in required_presets or preset == policy.get("strong_preset")
    ]
    blockers = [f"missing_report:{preset}" for preset in missing]
    for result in run_results:
        if result["status"] != "pass" and not result.get("quality_report_only"):
            blockers.extend(f"{result['preset']}:{blocker}" for blocker in result["blockers"])
        elif result["preset"] == policy.get("strong_preset"):
            blockers.extend(
                f"{result['preset']}:{blocker}"
                for blocker in result["blockers"]
                if blocker.startswith("safety_failure") or "safety" in blocker
            )

    return {
        "schema": "codex-vocal-release-gate-result-v1",
        "status": "pass" if not blockers else "fail",
        "blockers": sorted(set(blockers)),
        "runs": run_results,
        "required_presets": required_presets,
        "strong_preset": policy.get("strong_preset")
    }


def write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Release Candidate Gate",
        "",
        f"- Status: `{result['status']}`",
        f"- Required presets: `{', '.join(result.get('required_presets', []))}`",
        f"- Strong preset: `{result.get('strong_preset', '')}`",
        "",
        "## Blockers",
        ""
    ]
    if result.get("blockers"):
        lines.extend(f"- `{blocker}`" for blocker in result["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Runs", "", "| Preset | Status | Avg Preservation | Worst Preservation | Blockers |", "| --- | --- | ---: | ---: | --- |"])
    for run in result.get("runs", []):
        summary = run["summary"]
        avg = summary["average_scores"].get("source_preservation", 0.0)
        worst = summary["worst_scores"].get("source_preservation", 0.0)
        blockers = ", ".join(run.get("blockers", [])) or "none"
        lines.append(f"| {run['preset']} | {run['status']} | {avg:.1f} | {worst:.1f} | {blockers} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Prompt 8 release-candidate preset gates.")
    parser.add_argument("--policy", type=Path, default=RELEASE_POLICY_PATH)
    parser.add_argument("--reports", type=Path, nargs="+", required=True, help="Prompt 7 run_metrics.json files.")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    policy = load_release_policy(args.policy)
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.reports]
    result = evaluate_release_candidate(reports, policy)
    if args.output_json:
        save_json(args.output_json, result)
    if args.output_md:
        write_markdown_report(args.output_md, result)
    if not args.output_json and not args.output_md:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
