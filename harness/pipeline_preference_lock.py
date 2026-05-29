from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


DEFAULT_LOCK = Path("presets/pipeline_contracts/mesi_current_favorite_mix_master_lock.json")


def load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _claim_blob(evidence: dict[str, Any]) -> str:
    fields = [
        evidence.get("actual_classification"),
        evidence.get("project_classification_audit"),
        evidence.get("selected_candidate"),
        evidence.get("claims"),
        _nested(evidence, "processing_report", "claims"),
        _nested(evidence, "processing_report", "classification"),
        _nested(evidence, "classification", "classification"),
    ]
    return " ".join(_text(field) for field in fields).lower()


def _selected_candidate(evidence: dict[str, Any], candidate_qc: dict[str, Any]) -> str:
    return str(
        evidence.get("selected_candidate")
        or _nested(evidence, "rebeat_qc", "selected_candidate")
        or candidate_qc.get("selected_candidate")
        or _nested(candidate_qc, "rebeat_qc", "selected_candidate")
        or ""
    )


def _candidate_by_name(candidate_qc: dict[str, Any], name: str) -> dict[str, Any]:
    for candidate in candidate_qc.get("candidates", []):
        if str(candidate.get("name")) == name:
            return candidate
    return {}


def _metric_summary(evidence: dict[str, Any], candidate_qc: dict[str, Any]) -> dict[str, Any]:
    selected = _selected_candidate(evidence, candidate_qc)
    candidate = _candidate_by_name(candidate_qc, selected)
    return (
        evidence.get("qc_summary")
        or candidate.get("summary")
        or _nested(evidence, "engineering", "comparison", "delta")
        or _nested(evidence, "metrics", "delta")
        or {}
    )


def _metric_value(summary: dict[str, Any], *names: str) -> float | None:
    for name in names:
        if name in summary:
            value = _number(summary.get(name))
            if value is not None:
                return value
    return None


def _collect_warn_plus(payload: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        finding_list = payload.get("findings")
        if isinstance(finding_list, list):
            for finding in finding_list:
                if isinstance(finding, dict) and finding.get("severity") in {"WARN", "FAIL", "BLOCKER"}:
                    results.append(finding)
        for value in payload.values():
            if isinstance(value, (dict, list)):
                results.extend(_collect_warn_plus(value))
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, (dict, list)):
                results.extend(_collect_warn_plus(item))
    return results


def _check_metric_guards(lock: dict[str, Any], summary: dict[str, Any], findings: list[Finding]) -> None:
    guards = lock.get("metric_guards", {})

    duration_delta = _metric_value(summary, "duration_delta_sec", "duration_sec")
    max_duration_delta = _number(guards.get("max_abs_duration_delta_sec"))
    if duration_delta is not None and max_duration_delta is not None and abs(duration_delta) > max_duration_delta:
        add_finding(
            "FAIL",
            "PREFERENCE_LOCK_DURATION_MISMATCH",
            "Favorite pipeline lock requires the render duration to remain aligned with the source.",
            f"duration_delta_sec={duration_delta}, limit={max_duration_delta}",
            "Fix render bounds or source selection before using this locked style.",
            findings,
            failed_assumption="The locked style preserves arrangement length.",
        )

    true_peak = _metric_value(summary, "true_peak_after_dbfs", "peak_after_dbfs", "approx_true_peak_dbfs")
    max_true_peak = _number(guards.get("max_true_peak_dbfs"))
    if true_peak is not None and max_true_peak is not None and true_peak > max_true_peak:
        add_finding(
            "FAIL",
            "PREFERENCE_LOCK_TRUE_PEAK_UNSAFE",
            "Favorite pipeline lock forbids loudness by clipping or unsafe peak level.",
            f"true_peak_after_dbfs={true_peak}, limit={max_true_peak}",
            "Lower limiter/output gain and rerun before/after QC.",
            findings,
            failed_assumption="The locked style is true-peak safe.",
        )

    transient_ratio = _metric_value(summary, "transient_ratio")
    min_transient_ratio = _number(guards.get("min_transient_ratio"))
    if transient_ratio is not None and min_transient_ratio is not None and transient_ratio < min_transient_ratio:
        add_finding(
            "FAIL",
            "PREFERENCE_LOCK_TRANSIENT_LOSS",
            "Favorite pipeline lock preserves punch and transient detail.",
            f"transient_ratio={transient_ratio}, minimum={min_transient_ratio}",
            "Reduce DeAI/compression/limiting intensity and prefer the punch-preserve candidate.",
            findings,
            failed_assumption="Processing did not smear transients.",
            human_listening_required=True,
        )

    punch_delta = _metric_value(summary, "punch_delta_db", "low_band_energy_db")
    min_punch_delta = _number(guards.get("min_punch_delta_db"))
    if punch_delta is not None and min_punch_delta is not None and punch_delta < min_punch_delta:
        add_finding(
            "WARN",
            "PREFERENCE_LOCK_PUNCH_LOSS",
            "Favorite pipeline lock should not trade bass punch for cleanup.",
            f"punch_delta_db={punch_delta}, minimum={min_punch_delta}",
            "Back off DeAI, broadband compression, or limiter drive; rerun QC.",
            findings,
            failed_assumption="Cleanup preserved 45-140 Hz punch.",
            human_listening_required=True,
        )

    air_delta = _metric_value(summary, "air_fizz_delta_db", "air_fizz_band_db")
    min_air_delta = _number(guards.get("min_air_fizz_delta_db"))
    if air_delta is not None and min_air_delta is not None and air_delta < min_air_delta:
        add_finding(
            "WARN",
            "PREFERENCE_LOCK_AIR_OVER_CLEANED",
            "Favorite pipeline lock keeps MP3/Suno fizz control mild enough to preserve air.",
            f"air_fizz_delta_db={air_delta}, minimum={min_air_delta}",
            "Reduce high-side DeAI or de-esser depth; compare against the raw MP3 working WAV.",
            findings,
            failed_assumption="Artifact reduction did not dull the top end.",
            human_listening_required=True,
        )

    side_mid_delta = _metric_value(summary, "side_mid_delta_db", "side_mid_ratio_db")
    max_side_mid_change = _number(guards.get("max_abs_side_mid_delta_db"))
    if side_mid_delta is not None and max_side_mid_change is not None and abs(side_mid_delta) > max_side_mid_change:
        add_finding(
            "WARN",
            "PREFERENCE_LOCK_WIDTH_SHIFT",
            "Favorite pipeline lock allows only mild M/S side-wash control.",
            f"side_mid_delta_db={side_mid_delta}, limit={max_side_mid_change}",
            "Reduce side processing and rerun width/side-mid QC.",
            findings,
            failed_assumption="M/S processing did not collapse or exaggerate width.",
            human_listening_required=True,
        )

    harshness_delta = _metric_value(summary, "harshness_delta_db", "harshness_band_db")
    max_harshness_increase = _number(guards.get("max_harshness_increase_db"))
    if harshness_delta is not None and max_harshness_increase is not None and harshness_delta > max_harshness_increase:
        add_finding(
            "WARN",
            "PREFERENCE_LOCK_HARSHNESS_INCREASE",
            "Favorite pipeline lock should not make upper-mid harshness worse.",
            f"harshness_delta_db={harshness_delta}, limit={max_harshness_increase}",
            "Use dynamic resonance control rather than broad loudness/brightness moves.",
            findings,
            failed_assumption="Processing reduced or preserved harshness.",
            human_listening_required=True,
        )

    vocal_presence_delta = _metric_value(summary, "vocal_presence_delta_db", "vocal_presence_band_db")
    max_presence_shift = _number(guards.get("max_abs_vocal_presence_delta_db"))
    if vocal_presence_delta is not None and max_presence_shift is not None and abs(vocal_presence_delta) > max_presence_shift:
        add_finding(
            "WARN",
            "PREFERENCE_LOCK_VOCAL_CENTER_SHIFT",
            "Favorite pipeline lock protects the main vocal center and intelligibility band.",
            f"vocal_presence_delta_db={vocal_presence_delta}, limit={max_presence_shift}",
            "Reduce fullmix de-essing, mid cuts, or broad presence reshaping.",
            findings,
            failed_assumption="Vocal presence stayed stable.",
            human_listening_required=True,
        )


def evaluate_lock(lock: dict[str, Any], evidence: dict[str, Any], candidate_qc: dict[str, Any] | None = None) -> dict[str, Any]:
    candidate_qc = candidate_qc or {}
    findings: list[Finding] = []
    selected = _selected_candidate(evidence, candidate_qc)
    preferred = _nested(lock, "preferred", "selected_candidate")
    classification = str(evidence.get("actual_classification") or _nested(evidence, "processing_report", "classification") or "")
    claims = _claim_blob(evidence)

    if preferred and selected != preferred:
        add_finding(
            "FAIL",
            "PREFERRED_CANDIDATE_CHANGED",
            "The current favorite mix/master lock requires the punch-preserve candidate as the default selected print.",
            f"selected_candidate={selected}, preferred={preferred}",
            "Select the punch-preserve candidate or update the lock only after user listening approval.",
            findings,
            failed_assumption="The selected candidate still follows the current approved taste.",
            human_listening_required=True,
        )

    for term in lock.get("required_classification_terms", []):
        if str(term).lower() not in classification.lower():
            add_finding(
                "FAIL",
                "PREFERENCE_LOCK_CLASSIFICATION_MISMATCH",
                "Favorite pipeline lock requires honest fullmix rescue, Suno DeAI repair, and master-processing language.",
                f"missing_term={term}, classification={classification}",
                "Downgrade or correct the classification before presenting the render.",
                findings,
                failed_assumption="Classification matches the locked pipeline.",
            )

    for candidate in _nested(lock, "selection_rules", "reject_if_selected",) or []:
        if selected == candidate.get("name"):
            add_finding(
                candidate.get("severity", "FAIL"),
                "PREFERENCE_LOCK_REJECTED_CANDIDATE_SELECTED",
                candidate.get("message", "A rejected candidate was selected."),
                f"selected_candidate={selected}",
                candidate.get("recommendation", "Return to the preferred candidate or add listening-approved evidence."),
                findings,
                failed_assumption="The selected candidate is acceptable under the preference lock.",
                human_listening_required=True,
            )

    if _nested(lock, "source_policy", "expect_lossy_source") and not (
        _bool(evidence.get("source_is_lossy"))
        or str(evidence.get("source_format", "")).lower() == "mp3"
        or _bool(_nested(evidence, "classification", "evidence_summary", "source_lossy"))
    ):
        add_finding(
            "WARN",
            "PREFERENCE_LOCK_SOURCE_POLICY_MISMATCH",
            "This lock was made for a lossy-source processed-print workflow.",
            f"source_format={evidence.get('source_format')}, source_is_lossy={evidence.get('source_is_lossy')}",
            "For lossless stems or a different source, create a new versioned lock instead of reusing this one.",
            findings,
            failed_assumption="The source limitation matches the locked v11 workflow.",
        )

    for phrase in lock.get("forbidden_claims_without_evidence", []):
        if str(phrase).lower() in claims:
            add_finding(
                "FAIL",
                "PREFERENCE_LOCK_FORBIDDEN_CLAIM",
                "The preference lock does not allow this claim without independent evidence.",
                str(phrase),
                "Remove the claim or supply the exact RPP, MIDI/stem, render, and QC evidence.",
                findings,
                failed_assumption="Claim wording is supported by artifacts.",
                human_listening_required=True,
            )

    _check_metric_guards(lock, _metric_summary(evidence, candidate_qc), findings)

    warn_plus = _collect_warn_plus(evidence)
    if warn_plus:
        allowed_codes = set(lock.get("known_warn_plus_allowed", []))
        codes = sorted({str(finding.get("code", "")) for finding in warn_plus if finding.get("code")})
        unknown_codes = [code for code in codes if code not in allowed_codes]
        severity = "WARN" if unknown_codes else "INFO"
        add_finding(
            severity,
            "PREFERENCE_LOCK_WARN_PLUS_SURFACED",
            "Existing WARN/FAIL/BLOCKER evidence remains visible; this lock does not upgrade the render to final-success language.",
            ",".join(codes),
            "Keep WARN+ language in reports; fix unknown WARN+ codes before treating this as a stronger delivery claim.",
            findings,
            failed_assumption="A preferred style lock clears validation limitations.",
            human_listening_required=True,
        )

    status = "locked"
    if max_severity(findings) in {"FAIL", "BLOCKER"}:
        status = "rejected"
    elif max_severity(findings) in {"INFO", "WARN"}:
        status = "locked_with_known_limitations"

    return {
        "schema_version": 1,
        "lock_name": lock.get("name", "unnamed_preference_lock"),
        "locked_song": lock.get("song"),
        "preferred_candidate": preferred,
        "selected_candidate": selected,
        "actual_classification": classification,
        "lock_status": status,
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
        "allowed_language": lock.get("allowed_language", []),
        "forbidden_language": lock.get("forbidden_claims_without_evidence", []),
        "metric_summary": _metric_summary(evidence, candidate_qc),
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Current Favorite Mix/Master Preference Lock",
        "",
        f"- Lock: `{payload.get('lock_name')}`",
        f"- Song: `{payload.get('locked_song')}`",
        f"- Preferred candidate: `{payload.get('preferred_candidate')}`",
        f"- Selected candidate: `{payload.get('selected_candidate')}`",
        f"- Classification: `{payload.get('actual_classification')}`",
        f"- Lock status: `{payload.get('lock_status')}`",
        f"- Max severity: `{payload.get('max_severity')}`",
        "",
        "## Findings",
        "",
        findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
        "",
        "## Metric Summary",
        "",
        "```json",
        json.dumps(payload.get("metric_summary", {}), indent=2, sort_keys=True, ensure_ascii=False),
        "```",
        "",
        "## Allowed Language",
        "",
        *[f"- `{item}`" for item in payload.get("allowed_language", [])],
        "",
        "## Forbidden Language Without Evidence",
        "",
        *[f"- `{item}`" for item in payload.get("forbidden_language", [])],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a render/evidence package against the current preferred mix/master lock.")
    parser.add_argument("--lock", default=str(DEFAULT_LOCK))
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--candidate-qc")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = evaluate_lock(load_json(args.lock), load_json(args.evidence), load_json(args.candidate_qc))
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
