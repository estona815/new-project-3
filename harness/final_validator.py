from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .audio_qc import analyze_file
    from .midi_reconstruction_audit import audit_reaper_midi_reconstruction
    from .reaper_project_audit import audit_project
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from audio_qc import analyze_file
    from midi_reconstruction_audit import audit_reaper_midi_reconstruction
    from reaper_project_audit import audit_project
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


REQUIRED_REPORT_SUFFIXES = (
    "project_discovery.md",
    "source_audit.md",
    "plugin_audit.md",
    "processing_plan.md",
    "tempo_grid.md",
    "onset_events.md",
    "candidate_qc.md",
    "engineering_rule_check.md",
    "rpp_audit.md",
    "midi_reconstruction_audit.md",
    "final_classification.md",
    "final_validation.md",
    "final_report.md",
)


def validate_final(project_root: str | Path, final_wav: str | Path, rpp: str | Path, reports_dir: str | Path) -> dict:
    findings: list[Finding] = []
    root = Path(project_root).resolve()
    final_path = Path(final_wav)
    if not final_path.is_absolute():
        final_path = root / final_path
    rpp_path = Path(rpp)
    if not rpp_path.is_absolute():
        rpp_path = root / rpp_path
    report_root = Path(reports_dir)
    if not report_root.is_absolute():
        report_root = root / report_root

    if not final_path.exists():
        add_finding(
            "FAIL",
            "FINAL_WAV_MISSING",
            "Final WAV is missing.",
            str(final_path),
            "Render/export the final WAV and rerun validation.",
            findings,
            affected_file=str(final_path),
            failed_assumption="Final WAV exists.",
        )
        wav_metrics = None
    else:
        wav_metrics = analyze_file(final_path, findings)
        if float(wav_metrics.get("duration_sec") or 0.0) <= 0:
            add_finding(
                "FAIL",
                "FINAL_WAV_DURATION_INVALID",
                "Final WAV duration is invalid.",
                str(wav_metrics.get("duration_sec")),
                "Re-render the full song bounds.",
                findings,
                affected_file=str(final_path),
                failed_assumption="Final WAV duration is plausible.",
            )

    if not rpp_path.exists():
        add_finding(
            "FAIL",
            "RPP_MISSING",
            "REAPER project is missing.",
            str(rpp_path),
            "Create/save the REAPER project and rerun validation.",
            findings,
            affected_file=str(rpp_path),
            failed_assumption="RPP exists.",
        )
        rpp_audit = None
        midi_audit = None
    else:
        rpp_findings: list[Finding] = []
        rpp_audit = audit_project(rpp_path, rpp_findings, mode="auto", enforce_contract=False)
        findings.extend(rpp_findings)
        midi_audit = audit_reaper_midi_reconstruction(rpp_path, bus_render_dir=final_path.parent)
        findings.extend(Finding(**finding) for finding in midi_audit.get("findings", []))

    existing_reports = [path.name for path in report_root.glob("*.md")] if report_root.exists() else []
    missing = []
    for suffix in REQUIRED_REPORT_SUFFIXES:
        if not any(name.endswith(suffix) for name in existing_reports):
            missing.append(suffix)
    if missing:
        add_finding(
            "WARN",
            "VALIDATION_REPORT_SET_INCOMPLETE",
            "Some expected Markdown reports are missing.",
            ", ".join(missing),
            "Write the missing report files before delivery approval.",
            findings,
            affected_file=str(report_root),
            failed_assumption="Required report set exists.",
        )

    payload = {
        "schema_version": 1,
        "project_root": str(root),
        "final_wav": str(final_path),
        "rpp": str(rpp_path),
        "reports_dir": str(report_root),
        "wav_metrics": wav_metrics,
        "rpp_audit": rpp_audit,
        "midi_audit": midi_audit,
        "missing_report_suffixes": missing,
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }
    return payload


def markdown(payload: dict) -> str:
    return "\n".join(
        [
            "# Final Validation",
            "",
            f"- Final WAV: `{payload.get('final_wav')}`",
            f"- RPP: `{payload.get('rpp')}`",
            f"- Max severity: `{payload.get('max_severity')}`",
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate final REAPER/music pipeline deliverables.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--final-wav", required=True)
    parser.add_argument("--rpp", required=True)
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = validate_final(args.project_root, args.final_wav, args.rpp, args.reports_dir)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
