from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .audio_qc import compare_before_after
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from audio_qc import compare_before_after
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


DEFAULT_THRESHOLDS = {
    "flam_warn_sec": 0.025,
    "flam_fail_sec": 0.045,
    "punch_improvement_target_db": 0.25,
    "harshness_increase_warn_db": 0.8,
    "true_peak_target_dbfs": -1.0,
    "side_mid_change_warn_db": 1.5,
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _profile_thresholds(profile_path: str | Path | None) -> dict[str, float]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if profile_path and Path(profile_path).exists():
        profile = _load_json(profile_path)
        thresholds.update(profile.get("qc", {}))
    return thresholds


def evaluate_candidate(candidate: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
    findings: list[Finding] = []
    name = str(candidate.get("name") or candidate.get("id") or "candidate")
    metrics = candidate.get("metrics", {}) if isinstance(candidate.get("metrics", {}), dict) else candidate
    flam = _number(metrics.get("flam_risk_sec") or metrics.get("flam_risk_proxy_sec"))
    true_peak = _number(metrics.get("approx_true_peak_dbfs") or metrics.get("true_peak_dbfs"), -99.0)
    peak = _number(metrics.get("peak_dbfs"), -99.0)
    punch_delta = _number(metrics.get("punch_delta_db") or metrics.get("low_band_energy_db_delta"))
    harsh_delta = _number(metrics.get("harshness_delta_db") or metrics.get("harshness_band_db_delta"))
    side_mid_delta = _number(metrics.get("side_mid_delta_db") or metrics.get("side_mid_ratio_db_delta"))
    low_end_delta = _number(metrics.get("low_end_delta_db") or metrics.get("sub_delta_db"))
    clipping = bool(metrics.get("clipping") or peak >= -0.05 or true_peak > _number(thresholds["true_peak_target_dbfs"]))

    rejected = False
    human_listening_required = False
    if flam >= _number(thresholds["flam_fail_sec"]):
        rejected = True
        add_finding(
            "FAIL",
            "FLAM_RISK_REJECT",
            "Candidate has high flam/double-hit risk.",
            f"flam_risk_sec={flam:.4f}, fail={thresholds['flam_fail_sec']:.4f}",
            "Realign or remove reinforcement hits, then rerender and rerun rebeat QC.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Reinforcement hits align with source transients.",
            human_listening_required=True,
        )
    elif flam >= _number(thresholds["flam_warn_sec"]):
        human_listening_required = True
        add_finding(
            "WARN",
            "FLAM_RISK_WARN",
            "Candidate has measurable flam timing risk.",
            f"flam_risk_sec={flam:.4f}, warn={thresholds['flam_warn_sec']:.4f}",
            "Check A/B for double-hit feel and reduce quantization or offset MIDI.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Reinforcement groove is clean.",
            human_listening_required=True,
        )

    if clipping:
        rejected = True
        add_finding(
            "FAIL",
            "REBEAT_CANDIDATE_CLIPPING",
            "Candidate clips or exceeds true-peak safety.",
            f"peak_dbfs={peak:.2f}, true_peak_dbfs={true_peak:.2f}, target={thresholds['true_peak_target_dbfs']:.2f}",
            "Lower support layers/limiter ceiling and rerender.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Punch improvement is not caused by unsafe clipping.",
            human_listening_required=True,
        )

    if punch_delta < _number(thresholds["punch_improvement_target_db"]) and candidate.get("classification") == "drum_reinforcement":
        add_finding(
            "WARN",
            "DRUM_REINFORCEMENT_NO_PUNCH_GAIN",
            "Drum reinforcement did not improve punch enough to justify the layer.",
            f"punch_delta_db={punch_delta:.2f}, target={thresholds['punch_improvement_target_db']:.2f}",
            "Prefer no-reinforcement or reduce/realign drum support.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Reinforcement improves punch.",
            human_listening_required=True,
        )

    if low_end_delta < -0.25 and candidate.get("classification") == "drum_reinforcement":
        rejected = True
        add_finding(
            "FAIL",
            "KICK_SUPPORT_WEAKENS_LOW_END",
            "Low-end energy decreased after drum/kick support.",
            f"low_end_delta_db={low_end_delta:.2f}",
            "Check phase/polarity/offset or remove the kick support layer.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Kick reinforcement improves low-end impact.",
            human_listening_required=True,
        )

    if harsh_delta > _number(thresholds["harshness_increase_warn_db"]):
        add_finding(
            "WARN",
            "DRUM_SUPPORT_HARSHNESS_INCREASE",
            "Candidate increased harshness beyond profile guard.",
            f"harshness_delta_db={harsh_delta:.2f}, warn={thresholds['harshness_increase_warn_db']:.2f}",
            "Lower hats/snare brightness or reject the candidate if listening confirms splash.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Drum support did not add harshness.",
            human_listening_required=True,
        )

    if abs(side_mid_delta) > _number(thresholds["side_mid_change_warn_db"]):
        add_finding(
            "WARN",
            "REBEAT_SIDE_MID_CHANGE",
            "Candidate changed side/mid ratio beyond profile guard.",
            f"side_mid_delta_db={side_mid_delta:.2f}, warn={thresholds['side_mid_change_warn_db']:.2f}",
            "Audit stereo reinforcement and M/S processing before final selection.",
            findings,
            affected_file=str(candidate.get("render_file", "")),
            failed_assumption="Rebeat support preserves stereo image.",
            human_listening_required=True,
        )

    status = "reject" if rejected else "warn_listen" if any(f.severity == "WARN" for f in findings) else "pass"
    return {
        "name": name,
        "classification": candidate.get("classification", "unknown"),
        "render_file": candidate.get("render_file", ""),
        "status": status,
        "human_listening_required": human_listening_required or status != "pass",
        "metrics": metrics,
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }


def evaluate_rebeat_qc(payload: dict[str, Any], profile_path: str | Path | None = None) -> dict[str, Any]:
    thresholds = _profile_thresholds(profile_path)
    candidates = payload.get("candidates", [])
    if isinstance(candidates, dict):
        candidates = list(candidates.values())
    candidate_results = [evaluate_candidate(candidate, thresholds) for candidate in candidates]
    findings = [Finding(**finding) for result in candidate_results for finding in result.get("findings", [])]
    selected = None
    for result in candidate_results:
        if result["status"] == "pass":
            selected = result["name"]
            break
    if selected is None and candidate_results:
        selected = candidate_results[0]["name"]

    return {
        "schema_version": 1,
        "thresholds": thresholds,
        "candidate_results": candidate_results,
        "selected_candidate": selected,
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }


def run_before_after_qc(
    before: str | Path,
    after: str | Path,
    *,
    candidate_name: str = "candidate",
    classification: str = "unknown",
) -> dict[str, Any]:
    findings: list[Finding] = []
    comparison = compare_before_after(before, after, findings)
    delta = comparison.get("delta", {})
    after_metrics = comparison.get("after", {})
    candidate = {
        "name": candidate_name,
        "classification": classification,
        "render_file": str(after),
        "metrics": {
            "punch_delta_db": delta.get("low_band_energy_db", 0.0),
            "harshness_delta_db": delta.get("harshness_band_db", 0.0),
            "side_mid_delta_db": delta.get("side_mid_ratio_db", 0.0),
            "approx_true_peak_dbfs": after_metrics.get("approx_true_peak_dbfs", -99.0),
            "peak_dbfs": after_metrics.get("peak_dbfs", -99.0),
            "flam_risk_sec": 0.0,
        },
    }
    qc_payload = evaluate_rebeat_qc({"candidates": [candidate]})
    qc_payload["audio_comparison"] = comparison
    qc_payload["findings"].extend(findings_to_dicts(findings))
    qc_payload["max_severity"] = max_severity([Finding(**finding) for finding in qc_payload["findings"]])
    return qc_payload


def markdown_report(payload: dict[str, Any]) -> str:
    rows = []
    for result in payload.get("candidate_results", []):
        rows.append(
            f"| {result.get('name')} | {result.get('classification')} | {result.get('status')} | {result.get('max_severity')} | {result.get('render_file') or '-'} |"
        )
    if not rows:
        rows.append("| - | - | - | - | - |")
    return "\n".join(
        [
            "# Rebeat QC",
            "",
            f"- Selected candidate: `{payload.get('selected_candidate')}`",
            f"- Max severity: `{payload.get('max_severity')}`",
            "",
            "| Candidate | Classification | Status | Max severity | Render |",
            "| --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run rebeat/drum reinforcement QC gates.")
    parser.add_argument("--candidate-report", help="JSON with a candidates list and metrics.")
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--candidate-name", default="candidate")
    parser.add_argument("--classification", default="unknown")
    parser.add_argument("--profile")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    if args.before and args.after:
        payload = run_before_after_qc(args.before, args.after, candidate_name=args.candidate_name, classification=args.classification)
    elif args.candidate_report:
        payload = evaluate_rebeat_qc(_load_json(args.candidate_report), args.profile)
    else:
        raise SystemExit("Provide --candidate-report or --before/--after.")

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
