from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


DEFAULT_CONTRACT = Path("presets/pipeline_contracts/mesi_v10_evidence_contract.json")


def load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _find_nested(payload: dict[str, Any], *keys: str) -> Any:
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
        evidence.get("claim"),
        evidence.get("claims"),
        evidence.get("allowed_claims"),
        _find_nested(evidence, "classification", "classification"),
        _find_nested(evidence, "classification", "allowed_claims"),
    ]
    return " ".join(_text(field) for field in fields).lower()


def _warn_plus_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for key in ("findings",):
        for finding in payload.get(key, []) if isinstance(payload.get(key), list) else []:
            if finding.get("severity") in {"WARN", "FAIL", "BLOCKER"}:
                results.append(finding)
    for section in ("engineering", "classification", "final_validation"):
        data = payload.get(section)
        if isinstance(data, dict) and data:
            results.extend(_warn_plus_from_payload(data))
    return results


def _source_is_lossy(evidence: dict[str, Any]) -> bool:
    source_format = (
        evidence.get("source_format")
        or _find_nested(evidence, "source", "source_format")
        or _find_nested(evidence, "source_audit", "source_format")
        or _find_nested(evidence, "classification", "evidence_summary", "source_lossy")
    )
    selected_source = evidence.get("selected_source") or _find_nested(evidence, "discovery", "selected_source")
    if isinstance(selected_source, dict):
        if _bool(selected_source.get("lossy")):
            return True
        source_format = source_format or selected_source.get("format")
    return _bool(evidence.get("source_is_lossy")) or str(source_format).lower() in {"mp3", "aac", "m4a", "ogg", "opus", "true"}


def _true_rebeat_roles(evidence: dict[str, Any]) -> dict[str, bool]:
    summary = _find_nested(evidence, "classification", "evidence_summary") or evidence.get("evidence_summary") or {}
    return {
        "drums": _bool(summary.get("has_drum_reconstruction") or evidence.get("has_drum_reconstruction")),
        "bass": _bool(summary.get("has_bass_reconstruction") or evidence.get("has_bass_reconstruction")),
        "music": _bool(summary.get("has_music_reconstruction") or evidence.get("has_music_reconstruction")),
        "bus_renders": _bool(summary.get("bus_renders_complete") or evidence.get("bus_renders_complete")),
    }


def _grid_ok(evidence: dict[str, Any]) -> bool:
    summary = _find_nested(evidence, "classification", "evidence_summary") or evidence.get("evidence_summary") or {}
    confidence = str(summary.get("grid_confidence") or evidence.get("grid_confidence") or "").upper()
    return confidence == "PASS" or (confidence == "WARN" and _bool(evidence.get("grid_warn_justified")))


def evaluate_contract(contract: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    findings: list[Finding] = []
    claims = _claim_blob(evidence)
    warn_plus = _warn_plus_from_payload(evidence)
    forbidden_claims = set(contract.get("forbidden_claims", []))
    allowed_claims = set(contract.get("allowed_claims", []))

    if _source_is_lossy(evidence):
        add_finding(
            "WARN",
            "LOSSY_SOURCE_LANGUAGE_REQUIRED",
            "Lossy-source language is required for this evidence package.",
            "source_is_lossy=true or source_format=mp3",
            "Use processed-print language and do not claim lossless restoration.",
            findings,
            failed_assumption="MP3-derived processing can be presented as lossless restoration.",
        )
        forbidden_claims.add("lossless restoration")

    for phrase in contract.get("always_forbidden_without_evidence", []):
        if str(phrase).lower() in claims:
            add_finding(
                "FAIL",
                "FORBIDDEN_CLAIM_PRESENT",
                "A forbidden claim appears in the evidence/claim text.",
                str(phrase),
                "Remove the claim or add the exact required project/render/QC evidence.",
                findings,
                failed_assumption="Claim wording is supported by artifacts.",
            )

    true_rebeat_claimed = any(token in claims for token in ("true_rebeat", "true rebeat", "비트 다 새로"))
    roles = _true_rebeat_roles(evidence)
    if true_rebeat_claimed and not (roles["drums"] and roles["bass"] and roles["music"] and roles["bus_renders"] and _grid_ok(evidence)):
        add_finding(
            "FAIL",
            "TRUE_REBEAT_CLAIM_BLOCKED",
            "True rebeat claim lacks required drum/bass/music/grid/bus evidence.",
            json.dumps(roles, sort_keys=True),
            "Downgrade to fullmix rescue, drum reinforcement candidate, or partial rebuild wording.",
            findings,
            failed_assumption="True rebeat evidence is complete.",
            human_listening_required=True,
        )
        forbidden_claims.add("true_rebeat")
        forbidden_claims.add("비트 다 새로 찍음")

    selected = str(evidence.get("selected_candidate") or "").lower()
    actual = str(evidence.get("actual_classification") or "").lower()
    if selected and "drum_reinforcement" not in selected and "drum_reinforcement" in actual:
        add_finding(
            "WARN",
            "DRUM_REINFORCEMENT_NOT_SELECTED",
            "Drum reinforcement exists as a candidate/audit artifact but was not selected for the final render.",
            f"selected_candidate={selected}, actual_classification={actual}",
            "Use candidate/audit wording only, not selected-final drum replacement wording.",
            findings,
            failed_assumption="A rendered candidate automatically describes the selected final.",
            human_listening_required=True,
        )

    if _bool(evidence.get("reaper_render_fallback")) or any(item.get("code") == "REAPER_RENDER_FALLBACK" for item in warn_plus):
        add_finding(
            "WARN",
            "REAPER_RENDER_NOT_PROVEN",
            "REAPER project evidence exists, but REAPER-app render evidence is not proven.",
            "REAPER_RENDER_FALLBACK present",
            "Run REAPER renderproject/batch render before saying REAPER rendered the final WAV.",
            findings,
            failed_assumption="RPP creation is the same as REAPER audio rendering.",
            human_listening_required=True,
        )

    final_claimed = any(token in claims for token in ("completed", "완료", "final success", "professional final master", "마스터 완료"))
    if warn_plus and final_claimed:
        add_finding(
            "FAIL",
            "WARN_PLUS_FINAL_CLAIM_BLOCKED",
            "Final-success language is blocked while WARN/FAIL/BLOCKER findings exist.",
            ",".join(sorted({item.get("code", "") for item in warn_plus})),
            "Clear WARN+ findings or state that human listening/next patch is required.",
            findings,
            failed_assumption="WARN+ evidence can still support final success wording.",
            human_listening_required=True,
        )

    if warn_plus:
        surfaced_severity = max_severity(warn_plus)
        add_finding(
            surfaced_severity,
            "WARN_PLUS_SURFACED",
            "Evidence package contains WARN/FAIL/BLOCKER findings that must remain visible.",
            ",".join(sorted({item.get("code", "") for item in warn_plus})),
            "Keep every WARN+ item in the final report and do not upgrade claims.",
            findings,
            human_listening_required=True,
        )

    payload = {
        "schema_version": 1,
        "contract_name": contract.get("name", "unnamed_contract"),
        "quoted_requirements": contract.get("quoted_requirements", []),
        "allowed_claims": sorted(allowed_claims),
        "forbidden_claims": sorted(forbidden_claims),
        "max_severity": max_severity(findings),
        "claim_status": "not_final_warn_plus" if max_severity(findings) in {"WARN", "FAIL", "BLOCKER"} else "eligible_no_warn_plus",
        "findings": findings_to_dicts(findings),
    }
    return payload


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Pipeline Claim Contract Check",
        "",
        f"- Contract: `{payload.get('contract_name')}`",
        f"- Max severity: `{payload.get('max_severity')}`",
        f"- Claim status: `{payload.get('claim_status')}`",
        "",
        "## Quoted Requirements",
        "",
    ]
    for item in payload.get("quoted_requirements", []):
        quote = item.get("quote") if isinstance(item, dict) else str(item)
        lines.append(f"> {quote}")
        if isinstance(item, dict) and item.get("source"):
            lines.append(f"- Source: `{item['source']}`")
        lines.append("")
    lines.extend(
        [
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
            "## Allowed Claims",
            "",
            *[f"- `{claim}`" for claim in payload.get("allowed_claims", [])],
            "",
            "## Forbidden Claims",
            "",
            *[f"- `{claim}`" for claim in payload.get("forbidden_claims", [])],
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check music pipeline claims against a quote-backed evidence contract.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = evaluate_contract(load_json(args.contract), load_json(args.evidence))
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
