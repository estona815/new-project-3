#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURE_REPORT_JSON = (
    ROOT / "reports" / "goal02_8_reference_match" / "goal02_reference_8_track_mix_features.json"
)
DEFAULT_CANDIDATE_DECISION_JSON = (
    ROOT / "reports" / "goal02_candidate_decision_v04" / "goal02_candidate_decision.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "goal02_8_reference_match"

PRIMARY_REFERENCE_IDS = ["ref_03", "ref_06", "ref_07"]
STATUS_READY = "PRIMARY_REFERENCE_TRANSLATION_PACK_READY"
CLAIM_POLICY = (
    "Metrics and measured proxies only; no listening claims; no isolated reference "
    "vocal/drum/bass assertions; user loudness-matched A/B remains required."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value: Any, digits: int = 3) -> str:
    number = parse_float(value)
    if number is None:
        return "unavailable"
    return f"{number:.{digits}f}"


def delta(left: Any, right: Any, digits: int = 3) -> str:
    left_number = parse_float(left)
    right_number = parse_float(right)
    if left_number is None or right_number is None:
        return "unavailable"
    return f"{left_number - right_number:+.{digits}f}"


def metric(row: dict[str, Any], field: str) -> float | None:
    metrics = row.get("metrics", {})
    if isinstance(metrics, dict) and field in metrics:
        return parse_float(metrics.get(field))
    return parse_float(row.get(field))


def preferred_candidate(decision: dict[str, Any]) -> dict[str, Any]:
    preferred = decision.get("preferred")
    if isinstance(preferred, dict):
        return preferred
    for candidate in decision.get("candidates", []):
        if candidate.get("version") == "v04":
            return candidate
    candidates = decision.get("candidates", [])
    return candidates[0] if candidates else {}


def candidate_metrics(decision: dict[str, Any]) -> dict[str, Any]:
    candidate = preferred_candidate(decision)
    metrics = candidate.get("candidate_metrics", {})
    return metrics if isinstance(metrics, dict) else {}


def candidate_version(decision: dict[str, Any]) -> str:
    candidate = preferred_candidate(decision)
    return str(candidate.get("version") or decision.get("preferred") or "unknown")


def reference_by_id(feature_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    refs = feature_report.get("references", [])
    return {str(ref.get("id")): ref for ref in refs if isinstance(ref, dict)}


def ratio_sentence(label: str, field: str, ref: dict[str, Any], v04: dict[str, Any], original: dict[str, Any]) -> str:
    return (
        f"{label}: original target `{fmt(original.get(field))}`, "
        f"v04 `{fmt(v04.get(field))}`, reference `{fmt(metric(ref, field))}`, "
        f"v04-ref delta `{delta(v04.get(field), metric(ref, field))}`."
    )


def shared_bus_order(ref_id: str) -> list[str]:
    if ref_id == "ref_03":
        return [
            "808/BASS BUS: hold the v04 20-120 Hz contour close to ref_03 before touching master loudness.",
            "DRUM BUS: recover transient readability only if the A/B sequence feels flatter than ref_03.",
            "VOX BUS: keep de-ess and AI artifact split ahead of any brightening.",
            "MIX BUS/PREMASTER: verify true peak and mono correlation after bus changes, not as the main correction point.",
        ]
    if ref_id == "ref_06":
        return [
            "808/BASS BUS: compare sub density against ref_06, but add harmonic support before adding raw level.",
            "MUSIC BUS: keep center-stable width and avoid side-only widening that lowers mono correlation.",
            "VOX BUS: protect 5-10 kHz from extra fizz because v04 is already brighter than ref_06 on high-band share.",
            "PREMASTER: use compression/clip only as final containment; sustained >2 dB gain reduction means return to buses.",
        ]
    return [
        "808/BASS BUS: use ref_07 as the second low-end density anchor after ref_06.",
        "VOX BUS: keep the lead present enough that extra low-end does not tuck the center vocal.",
        "DRUM BUS: preserve transient density without copying excess top-band hash.",
        "MIX BUS/PREMASTER: check mono correlation and loud/safe export targets after bus-level fixes.",
    ]


def plugin_scope(ref_id: str) -> list[str]:
    common = [
        "Use Codex Vocal AI Artifact Split Tamer first on the main vocal; fallback first-slot plugins do not satisfy the gate.",
        "Use TDR Nova/ReaXcomp/Codex Dynamic EQ for targeted dynamic correction before broad EQ boosts.",
        "Use Ozone Imager 2 or Codex Pro Dynamic MS EQ only after mono-correlation checks.",
        "Use FreeClip/ReaLimit only for final peak containment, not to manufacture missing bus balance.",
    ]
    if ref_id == "ref_03":
        return common + [
            "Use ReaEQ/Ozone EQ on 808/BASS for contour; avoid adding Fresh Air or wide high shelf to chase ref_03 air.",
        ]
    if ref_id == "ref_06":
        return common + [
            "Use BYOD/Decapitator/IVGI2 only as light 808 harmonic support if the trace documents the insert; avoid hardcoded external parameter writes.",
        ]
    return common + [
        "Use Codex MS Melody Tuck only as a small music-bed pocket; do not over-tuck the lead vocal to imitate density.",
    ]


def build_entry(ref: dict[str, Any], target: dict[str, Any], v04: dict[str, Any]) -> dict[str, Any]:
    ref_id = str(ref.get("id"))
    low = metric(ref, "low_energy_ratio_20_120")
    high = metric(ref, "high_energy_ratio_2500_16000")
    corr = metric(ref, "stereo_correlation")
    transient = metric(ref, "transient_density_per_second")
    sibilance = metric(ref, "sibilance_energy_ratio_5000_10000")
    ref_peak = metric(ref, "sample_peak_dbfs")
    v04_low = v04.get("low_energy_ratio_20_120")
    v04_high = v04.get("high_energy_ratio_2500_16000")
    v04_corr = v04.get("stereo_correlation")
    v04_transient = v04.get("transient_density_per_second")
    v04_sibilance = v04.get("sibilance_energy_ratio_5000_10000")

    if ref_id == "ref_03":
        why_reference = [
            f"Low-band contour anchor: ref_03 20-120 Hz ratio `{fmt(low)}` is nearly identical to v04 `{fmt(v04_low)}`.",
            f"High-band guardrail: ref_03 high ratio `{fmt(high)}` and sibilance proxy `{fmt(sibilance)}` are above v04 `{fmt(v04_high)}` / `{fmt(v04_sibilance)}`.",
            f"Transient contrast point: ref_03 transient density `{fmt(transient)}` exceeds v04 `{fmt(v04_transient)}`.",
        ]
        target_lacks = [
            ratio_sentence("Original low-end share", "low_energy_ratio_20_120", ref, v04, target),
            ratio_sentence("Original stereo correlation", "stereo_correlation", ref, v04, target),
            f"Compared with ref_03, v04 still has lower transient density by `{delta(v04_transient, transient)}`.",
        ]
        target_already_ok = [
            f"v04 low ratio `{fmt(v04_low)}` is within `{delta(v04_low, low)}` of ref_03.",
            f"v04 stereo correlation `{fmt(v04_corr)}` is positive and close to ref_03 `{fmt(corr)}`.",
            f"v04 sibilance proxy `{fmt(v04_sibilance)}` stays below ref_03 `{fmt(sibilance)}`, so do not brighten blindly.",
        ]
        must_follow = [
            "Follow the low-end contour and positive mono-correlation behavior.",
            "Use ref_03 for transient-readability checking after 808/BASS changes.",
            "Keep the main correction at 808/BASS and DRUM buses before master limiting.",
        ]
        must_not_copy = [
            "Do not copy ref_03 high-band or sibilance proxy as an air target.",
            "Do not use extra Fresh Air/high shelf to force ref_03 brightness.",
            "Do not chase ref_03 sample-peak behavior as a loudness target.",
        ]
    elif ref_id == "ref_06":
        why_reference = [
            f"Primary density/mono anchor: ref_06 stereo correlation `{fmt(corr)}` is the highest among the primary references.",
            f"Sub-density target: ref_06 20-120 Hz ratio `{fmt(low)}` is above v04 `{fmt(v04_low)}` without requiring more top-band energy.",
            f"Brightness restraint: ref_06 high ratio `{fmt(high)}` is below v04 `{fmt(v04_high)}`.",
        ]
        target_lacks = [
            ratio_sentence("Original low-end share", "low_energy_ratio_20_120", ref, v04, target),
            ratio_sentence("Original stereo correlation", "stereo_correlation", ref, v04, target),
            f"v04 remains below ref_06 low share by `{delta(v04_low, low)}` while already exceeding ref_06 high share by `{delta(v04_high, high)}`.",
        ]
        target_already_ok = [
            f"v04 correlation `{fmt(v04_corr)}` is now positive and close enough to use mono checks instead of wide rescue.",
            f"v04 loud candidate true-peak target is already guarded in the LUFS package; do not add more limiter pressure for ref_06.",
            f"v04 transient density `{fmt(v04_transient)}` is not below ref_06 `{fmt(transient)}`.",
        ]
        must_follow = [
            "Follow ref_06 for mono-safe low-end density and center stability.",
            "Keep high-band restraint; if more density is needed, add low/harmonic support rather than air.",
            "Use it as the first A/B reference after the current target and v04 candidate.",
        ]
        must_not_copy = [
            f"Do not chase ref_06 sample peak `{fmt(ref_peak)}` or clipped-master behavior.",
            "Do not widen the music bed if stereo correlation drops or mono loses center.",
            "Do not add 5-16 kHz energy to imitate density; ref_06 is not the bright-air target.",
        ]
    else:
        why_reference = [
            f"Second low-density anchor: ref_07 20-120 Hz ratio `{fmt(low)}` is above v04 `{fmt(v04_low)}`.",
            f"Mono-safety target: ref_07 correlation `{fmt(corr)}` confirms positive-correlation reference behavior.",
            f"Top-band restraint check: ref_07 high ratio `{fmt(high)}` is below v04 `{fmt(v04_high)}`.",
        ]
        target_lacks = [
            ratio_sentence("Original low-end share", "low_energy_ratio_20_120", ref, v04, target),
            ratio_sentence("Original stereo correlation", "stereo_correlation", ref, v04, target),
            f"v04 is below ref_07 low share by `{delta(v04_low, low)}` while already above ref_07 high share by `{delta(v04_high, high)}`.",
        ]
        target_already_ok = [
            f"v04 sibilance proxy `{fmt(v04_sibilance)}` is close to ref_07 `{fmt(sibilance)}`.",
            f"v04 transient density `{fmt(v04_transient)}` is close to ref_07 `{fmt(transient)}`.",
            f"v04 positive correlation `{fmt(v04_corr)}` keeps the center from the original negative-correlation state.",
        ]
        must_follow = [
            "Follow ref_07 as the second check that low-end can be denser without making the top harsher.",
            "Keep lead vocal decisions on VOX BUS before master loudness decisions.",
            "Use ref_07 to catch over-tucked vocal or over-wide music-bed revisions in user A/B.",
        ]
        must_not_copy = [
            "Do not lower the lead vocal just to make the instrumental feel denser.",
            "Do not copy any side-width impression if mono correlation or center vocal weakens.",
            "Do not add master compression if the low-end problem is still bus-level.",
        ]

    return {
        "id": ref_id,
        "file": ref.get("file"),
        "role": ref.get("role"),
        "measurement_scope": ref.get("measurement_scope"),
        "metrics": ref.get("metrics", {}),
        "why_reference": why_reference,
        "target_lacks": target_lacks,
        "target_already_ok": target_already_ok,
        "must_follow": must_follow,
        "must_not_copy": must_not_copy,
        "bus_translation_order": shared_bus_order(ref_id),
        "plugin_scope": plugin_scope(ref_id),
        "ab_check": [
            "Use the packaged order: Current target -> v04 candidate -> ref_06 -> v04 candidate -> ref_07 -> v04 candidate -> ref_03 -> v04 candidate.",
            "Compare at the packaged LUFS target only; do not use un-matched loudness as evidence.",
            "If master gain reduction would stay above 2 dB, return to VOX, 808/BASS, DRUM, or MUSIC BUS.",
        ],
        "failure_signs": [
            "Lead vocal feels pushed behind the reference at matched loudness; revise VOX/MUSIC pocket before limiting.",
            "808 or kick masks the center vocal; revise 808/BASS BUS before master chain.",
            "Hats/sibilance read as metallic glare; revise 5-12 kHz dynamic control before air boosts.",
            "Mono check loses center or low end; remove widening or side-only processing before export.",
        ],
        "claim_limit": (
            "This entry translates measured stereo-master proxies into REAPER actions. "
            "It is not a listening claim and does not prove isolated vocal/drum/bass behavior."
        ),
    }


def build_pack(feature_report: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    refs = reference_by_id(feature_report)
    target_metrics = feature_report.get("target_metrics", {})
    v04_metrics = candidate_metrics(decision)
    entries = [build_entry(refs[ref_id], target_metrics, v04_metrics) for ref_id in PRIMARY_REFERENCE_IDS]
    return {
        "schema": "goal02-primary-reference-translation-pack-v1",
        "created_at": now_utc(),
        "status": STATUS_READY,
        "claim_policy": CLAIM_POLICY,
        "source_feature_report": str(DEFAULT_FEATURE_REPORT_JSON),
        "source_candidate_decision": str(DEFAULT_CANDIDATE_DECISION_JSON),
        "candidate_version": candidate_version(decision),
        "primary_reference_ids": PRIMARY_REFERENCE_IDS,
        "primary_reference_count": len(entries),
        "original_target_metrics": target_metrics,
        "candidate_metrics": v04_metrics,
        "entries": entries,
    }


def write_markdown(path: Path, pack: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 Primary Reference Translation Pack",
        "",
        f"- Created UTC: `{pack['created_at']}`",
        f"- Status: `{pack['status']}`",
        f"- Candidate: `{pack['candidate_version']}`",
        f"- Primary references: `{', '.join(pack['primary_reference_ids'])}`",
        f"- Claim policy: `{pack['claim_policy']}`",
        "",
        "## Current Candidate Anchor",
        "",
        "| Metric | Original Target | v04 Candidate |",
        "| --- | ---: | ---: |",
    ]
    original = pack["original_target_metrics"]
    candidate = pack["candidate_metrics"]
    for field in [
        "low_energy_ratio_20_120",
        "high_energy_ratio_2500_16000",
        "sibilance_energy_ratio_5000_10000",
        "transient_density_per_second",
        "stereo_correlation",
        "rms_dbfs",
    ]:
        lines.append(f"| `{field}` | `{fmt(original.get(field))}` | `{fmt(candidate.get(field))}` |")

    for entry in pack["entries"]:
        lines.extend(
            [
                "",
                f"## {entry['id']} Translation",
                "",
                f"- File: `{entry.get('file')}`",
                f"- Role: `{entry.get('role')}`",
                f"- Measurement scope: `{entry.get('measurement_scope')}`",
                f"- Claim limit: `{entry.get('claim_limit')}`",
                "",
                "### Why This Reference",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in entry["why_reference"])
        for heading, key in [
            ("Target Lacks", "target_lacks"),
            ("Target Already OK", "target_already_ok"),
            ("Must Follow", "must_follow"),
            ("Must Not Copy", "must_not_copy"),
            ("Bus Translation Order", "bus_translation_order"),
            ("Plugin Scope", "plugin_scope"),
            ("A/B Check", "ab_check"),
            ("Failure Signs", "failure_signs"),
        ]:
            lines.extend(["", f"### {heading}", ""])
            lines.extend(f"- {item}" for item in entry[key])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    feature_report = load_json(args.feature_report_json)
    decision = load_json(args.candidate_decision_json)
    missing = [ref_id for ref_id in PRIMARY_REFERENCE_IDS if ref_id not in reference_by_id(feature_report)]
    if missing:
        raise ValueError(f"missing primary references in feature report: {', '.join(missing)}")
    pack = build_pack(feature_report, decision)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "goal02_primary_reference_translation_pack.json"
    md_path = args.output_dir / "GOAL02_PRIMARY_REFERENCE_TRANSLATION_PACK.md"
    json_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, pack)
    pack["json_path"] = str(json_path)
    pack["report_path"] = str(md_path)
    return pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Goal 02 primary-reference translation pack.")
    parser.add_argument("--feature-report-json", type=Path, default=DEFAULT_FEATURE_REPORT_JSON)
    parser.add_argument("--candidate-decision-json", type=Path, default=DEFAULT_CANDIDATE_DECISION_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    pack = run(args)
    print(
        json.dumps(
            {
                "status": pack["status"],
                "primary_reference_count": pack["primary_reference_count"],
                "report_path": pack["report_path"],
                "json_path": pack["json_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
