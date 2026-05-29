from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


CLASSIFICATIONS = (
    "master_only",
    "fullmix_rescue",
    "drum_reinforcement",
    "stem_assisted_rebuild",
    "partial_rebeat",
    "true_rebeat",
)


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _source_lossy(discovery: dict[str, Any], processing_report: dict[str, Any]) -> bool:
    source = discovery.get("selected_source", discovery.get("source", {}))
    if not isinstance(source, dict):
        source = {}
    fmt = _text(source.get("format") or discovery.get("source_format") or processing_report.get("source_format")).lower()
    return _bool(source.get("lossy") or discovery.get("source_is_lossy") or processing_report.get("source_is_lossy")) or fmt in {
        "mp3",
        "aac",
        "m4a",
        "ogg",
        "opus",
        "lossy",
    }


def _available_stems(discovery: dict[str, Any], rpp_audit: dict[str, Any], midi_audit: dict[str, Any]) -> list[Any]:
    stems = []
    stems.extend(_list(discovery.get("available_stems")))
    stems.extend(_list(discovery.get("stems")))
    if _bool(rpp_audit.get("has_stem_tracks")) or _bool(midi_audit.get("has_stem_tracks")):
        stems.append({"source": "rpp_audit", "role": "stem_track"})
    return stems


def _active_stem_tracks(rpp_audit: dict[str, Any], midi_audit: dict[str, Any]) -> bool:
    return _bool(rpp_audit.get("has_stem_tracks")) or _bool(midi_audit.get("has_stem_tracks"))


def _machine_separated_stems(stems: list[Any], discovery: dict[str, Any]) -> bool:
    if _bool(discovery.get("machine_separated_stems")):
        return True
    for stem in stems:
        text = _text(stem).lower()
        if any(term in text for term in ("machine", "separated", "demucs", "uvr", "roformer", "spleeter", "separator")):
            return True
    return False


def _bus_renders_complete(midi_audit: dict[str, Any], qc: dict[str, Any]) -> bool:
    if _bool(midi_audit.get("has_separate_bus_renders")):
        return True
    bus = qc.get("bus_renders", {})
    if isinstance(bus, dict):
        return all(bus.get(role) for role in ("drums", "bass", "music", "mix", "master"))
    return False


def _qc_failed(qc: dict[str, Any]) -> bool:
    if qc.get("max_severity") in {"FAIL", "BLOCKER"}:
        return True
    for result in _list(qc.get("candidate_results")):
        if isinstance(result, dict) and result.get("status") == "reject":
            return True
    return False


def _has_processing(processing_report: dict[str, Any]) -> bool:
    if not processing_report:
        return False
    if processing_report.get("processing_moves") or processing_report.get("moves"):
        return True
    blob = _text(processing_report).lower()
    return any(term in blob for term in ("eq", "deai", "compress", "limit", "master", "m/s", "dynamic"))


def _claim_blob(processing_report: dict[str, Any]) -> str:
    fields = []
    for key in ("claim", "claims", "classification", "summary", "final_claim"):
        if key in processing_report:
            fields.append(_text(processing_report[key]))
    return " ".join(fields).lower()


def classify_rebeat_evidence(
    *,
    discovery: dict[str, Any] | None = None,
    tempo_grid: dict[str, Any] | None = None,
    events: dict[str, Any] | None = None,
    rpp_audit: dict[str, Any] | None = None,
    midi_audit: dict[str, Any] | None = None,
    qc: dict[str, Any] | None = None,
    processing_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    discovery = discovery or {}
    tempo_grid = tempo_grid or {}
    events = events or {}
    rpp_audit = rpp_audit or {}
    midi_audit = midi_audit or {}
    qc = qc or {}
    processing_report = processing_report or {}
    findings: list[Finding] = []

    requested_mode = _text(processing_report.get("requested_mode") or processing_report.get("mode") or discovery.get("requested_mode")).lower()
    claims = _claim_blob(processing_report)
    source_lossy = _source_lossy(discovery, processing_report)
    stems = _available_stems(discovery, rpp_audit, midi_audit)
    stems_available = bool(stems)
    has_stems = _active_stem_tracks(rpp_audit, midi_audit)
    machine_stems = _machine_separated_stems(stems, discovery)
    has_midi_files = bool(discovery.get("available_midi") or discovery.get("midi_files"))
    fullmix_active = _bool(midi_audit.get("original_fullmix_active") or rpp_audit.get("original_fullmix_active"))
    if "source" in discovery and isinstance(discovery["source"], dict):
        fullmix_active = fullmix_active or discovery["source"].get("channels") in {1, 2}
    has_drum = _bool(midi_audit.get("has_drum_midi") or midi_audit.get("has_drum_audio_support"))
    has_bass = _bool(midi_audit.get("has_bass_midi") or midi_audit.get("has_bass_audio_support"))
    has_music = _bool(midi_audit.get("has_music_midi") or midi_audit.get("has_music_audio_support"))
    event_counts = events.get("event_counts", {}) if isinstance(events.get("event_counts", {}), dict) else {}
    has_drum_events = any(int(event_counts.get(key, 0) or 0) > 0 for key in ("kick", "snare_clap", "hat_perc", "percussion"))
    bus_complete = _bus_renders_complete(midi_audit, qc)
    grid_confidence = _text(tempo_grid.get("grid_confidence")).upper()
    grid_score = float(tempo_grid.get("grid_confidence_score") or 0.0)
    grid_warn_justified = _bool(tempo_grid.get("warn_justified") or processing_report.get("grid_warn_justified"))
    qc_failed = _qc_failed(qc)
    rpp_present = bool(rpp_audit or midi_audit)

    if source_lossy:
        add_finding(
            "WARN",
            "LOSSY_SOURCE_REBEAT_LIMITATION",
            "Source is lossy; MP3-derived processing cannot be called lossless restoration.",
            "source_is_lossy=true",
            "Use lossy-source processed print language and avoid lossless restoration claims.",
            findings,
            affected_file=_text(discovery.get("selected_source") or processing_report.get("source")),
            failed_assumption="Lossy source can support lossless restoration language.",
        )

    if stems_available and not has_stems:
        add_finding(
            "INFO",
            "STEMS_DISCOVERED_NOT_ACTIVE",
            "Stems were discovered, but the audited REAPER project does not show active stem tracks.",
            json.dumps(stems, sort_keys=True),
            "Use stem-assisted rebuild language only after stems are imported/routed and the RPP audit confirms them.",
            findings,
            failed_assumption="Discovered stems are automatically active in the current render.",
        )

    if machine_stems:
        add_finding(
            "WARN",
            "MACHINE_SEPARATED_STEMS_NOT_ORIGINAL",
            "Machine-separated stems are not original stems.",
            json.dumps(stems, sort_keys=True),
            "Label stems as machine-separated and do not claim clean stem rebuild unless quality/QC supports it.",
            findings,
            failed_assumption="Source-separated stems are original production stems.",
            human_listening_required=True,
        )

    if not rpp_present and ("true_rebeat" in requested_mode or "true rebeat" in claims):
        add_finding(
            "FAIL",
            "RPP_AUDIT_REQUIRED_FOR_TRUE_REBEAT",
            "True rebeat requires RPP/MIDI reconstruction audit evidence.",
            "rpp_audit and midi_audit are missing.",
            "Run MIDI reconstruction audit against the REAPER project.",
            findings,
            failed_assumption="True rebeat can be claimed without RPP audit.",
            command_to_rerun="python3 harness/midi_reconstruction_audit.py --rpp PATH_TO_PROJECT.rpp --bus-render-dir renders/song_vNEXT --out-json reports/song_vNEXT_midi_reconstruction_audit.json --out-md reports/song_vNEXT_midi_reconstruction_audit.md",
        )

    if grid_confidence in {"WARN", "FAIL", "BLOCKER"}:
        severity = "WARN" if grid_confidence == "WARN" else "FAIL"
        add_finding(
            severity,
            f"GRID_CONFIDENCE_{grid_confidence or 'MISSING'}",
            "Tempo/grid confidence limits rebeat claims.",
            f"grid_confidence={grid_confidence}, grid_score={grid_score:.3f}",
            "Use manual tempo map or light reinforcement only; do not hard-quantize or claim true rebeat unless justified.",
            findings,
            affected_file=_text(tempo_grid.get("input")),
            failed_assumption="Detected grid is safe for reconstruction.",
            human_listening_required=True,
        )

    if "true_rebeat" in requested_mode or "true rebeat" in claims or "비트 다" in claims:
        if not (has_drum and has_bass and has_music):
            add_finding(
                "WARN",
                "TRUE_REBEAT_REQUEST_DOWNGRADED",
                "Requested true_rebeat is missing required reconstructed roles.",
                f"has_drum={has_drum}, has_bass={has_bass}, has_music={has_music}",
                "Downgrade to drum_reinforcement, partial_rebeat, stem_assisted_rebuild, or fullmix_rescue.",
                findings,
                failed_assumption="All true-rebeat role evidence exists.",
                human_listening_required=True,
            )
        if not bus_complete:
            add_finding(
                "FAIL",
                "TRUE_REBEAT_BUS_RENDERS_MISSING",
                "True rebeat requires separate drums/bass/music/mix/master bus renders.",
                f"bus_complete={bus_complete}",
                "Render required buses and rerun classification.",
                findings,
                failed_assumption="True-rebeat bus render evidence exists.",
                command_to_rerun="python3 harness/rebeat_classification.py --discovery reports/song_vNEXT_rebeat_discovery.json --tempo-grid reports/song_vNEXT_tempo_grid.json --events reports/song_vNEXT_onset_events.json --rpp-audit reports/song_vNEXT_rpp_audit.json --midi-audit reports/song_vNEXT_midi_reconstruction_audit.json --qc reports/song_vNEXT_rebeat_qc.json --out-json reports/song_vNEXT_rebeat_classification.json --out-md reports/song_vNEXT_rebeat_classification.md",
            )

    true_grid_ok = grid_confidence == "PASS" or (grid_confidence == "WARN" and grid_warn_justified)
    true_allowed = bool(
        has_drum
        and has_bass
        and has_music
        and bus_complete
        and true_grid_ok
        and not qc_failed
        and rpp_present
        and not (fullmix_active and midi_audit.get("fullmix_dependency_level") == "high")
    )

    if true_allowed:
        classification = "true_rebeat"
    elif has_stems and not (has_drum or has_bass or has_music):
        classification = "stem_assisted_rebuild"
    elif has_stems and (has_drum or has_bass or has_music):
        classification = "partial_rebeat" if not (has_bass and has_music and has_drum) else "stem_assisted_rebuild"
    elif has_drum and fullmix_active and not (has_bass or has_music):
        classification = "drum_reinforcement"
    elif has_drum or has_bass or has_music:
        classification = "partial_rebeat"
    elif has_drum_events and fullmix_active:
        classification = "fullmix_rescue"
        add_finding(
            "INFO",
            "ONSET_EVENTS_ARE_NOT_RECONSTRUCTION",
            "Detected onset events do not count as MIDI/audio reconstruction until placed in REAPER.",
            json.dumps(event_counts, sort_keys=True),
            "Create MIDI/audio items and audit the RPP before claiming drum reinforcement.",
            findings,
        )
    elif fullmix_active and _has_processing(processing_report):
        classification = "fullmix_rescue"
    elif fullmix_active:
        classification = "fullmix_rescue"
    else:
        classification = "master_only"

    if qc_failed:
        add_finding(
            "FAIL",
            "REBEAT_QC_FAILED",
            "Rebeat/drum reinforcement QC has FAIL/BLOCKER or rejected candidate.",
            f"qc_max_severity={qc.get('max_severity')}",
            "Fix rejected candidates before selecting a final or making reconstruction claims.",
            findings,
            failed_assumption="Candidate QC passed.",
            human_listening_required=True,
        )

    allowed = [classification]
    if classification == "drum_reinforcement":
        allowed.extend(["kick/snare support layer", "partial drum MIDI reconstruction"])
    if classification == "partial_rebeat":
        roles = []
        if has_drum:
            roles.append("drums")
        if has_bass:
            roles.append("bass")
        if has_music:
            roles.append("music")
        allowed.append("partial_rebeat: " + ", ".join(roles or ["unspecified"]))
    if classification == "stem_assisted_rebuild":
        allowed.append("stem-assisted rebuild")
    if source_lossy:
        allowed.append("lossy-source processed print")

    forbidden = [
        "비트 다 새로 찍음",
        "beat fully re-created",
        "full MIDI reconstruction",
        "remade instrumental",
        "새 beat print",
        "professional final master",
    ]
    if classification != "true_rebeat":
        forbidden.append("true_rebeat")
    if not has_stems:
        forbidden.append("stem rebuild")
    if source_lossy:
        forbidden.append("lossless restoration")
    pitch = processing_report.get("pitch_correction", {})
    pitch_validated = bool(pitch.get("validated", False)) if isinstance(pitch, dict) else False
    if not pitch_validated:
        forbidden.append("vocal tuned")

    missing = []
    if not has_drum:
        missing.append("drum MIDI/audio reconstruction")
    if not has_bass:
        missing.append("bass MIDI/audio reconstruction")
    if not has_music:
        missing.append("music/chord/lead MIDI/audio support")
    if not bus_complete:
        missing.append("separate drums/bass/music/mix/master bus renders")
    if not rpp_present:
        missing.append("RPP/MIDI audit")
    if not true_grid_ok:
        missing.append("PASS tempo grid or justified WARN")

    payload = {
        "schema_version": 1,
        "classification": classification,
        "true_rebeat_possible": classification == "true_rebeat",
        "allowed_claims": sorted(set(allowed)),
        "forbidden_claims": sorted(set(forbidden)),
        "missing_evidence_for_true_rebeat": missing,
        "evidence_summary": {
            "source_lossy": source_lossy,
            "has_stems": has_stems,
            "stems_available": stems_available,
            "machine_separated_stems": machine_stems,
            "has_midi_files": has_midi_files,
            "fullmix_active": fullmix_active,
            "has_drum_reconstruction": has_drum,
            "has_bass_reconstruction": has_bass,
            "has_music_reconstruction": has_music,
            "bus_renders_complete": bus_complete,
            "grid_confidence": grid_confidence or "MISSING",
            "qc_failed": qc_failed,
        },
        "next_actions": _next_actions(missing, classification),
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }
    return payload


def _next_actions(missing: list[str], classification: str) -> list[str]:
    actions = []
    for item in missing:
        if "drum" in item:
            actions.append("Create or import drum MIDI/audio items, then rerun MIDI reconstruction audit.")
        elif "bass" in item:
            actions.append("Add bass MIDI/audio support only from reliable pitch/stem/MIDI evidence.")
        elif "music" in item:
            actions.append("Import MIDI/stems or manually place chord/lead support; do not fabricate dense fullmix transcription.")
        elif "bus" in item:
            actions.append("Run render_rebeat_buses.lua to produce drums, bass, music, mix, and master bus renders.")
        elif "RPP" in item:
            actions.append("Run harness/midi_reconstruction_audit.py on the REAPER project.")
        elif "tempo" in item or "grid" in item:
            actions.append("Run tempo_grid_analyzer.py or create a manual tempo map before quantized reconstruction.")
    if not actions:
        actions.append(f"Proceed with {classification} wording and attach all audit artifacts.")
    return actions


def markdown_report(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Rebeat Classification",
            "",
            f"- Classification: `{payload.get('classification')}`",
            f"- True rebeat possible: `{payload.get('true_rebeat_possible')}`",
            f"- Max severity: `{payload.get('max_severity')}`",
            "",
            "## Allowed Claims",
            "",
            *[f"- `{claim}`" for claim in payload.get("allowed_claims", [])],
            "",
            "## Forbidden Claims",
            "",
            *[f"- `{claim}`" for claim in payload.get("forbidden_claims", [])],
            "",
            "## Missing Evidence For True Rebeat",
            "",
            *[f"- {item}" for item in payload.get("missing_evidence_for_true_rebeat", [])],
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
            "## Next Actions",
            "",
            *[f"- {action}" for action in payload.get("next_actions", [])],
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify rebeat/drum reinforcement claims from evidence artifacts.")
    parser.add_argument("--discovery")
    parser.add_argument("--tempo-grid")
    parser.add_argument("--events")
    parser.add_argument("--rpp-audit")
    parser.add_argument("--midi-audit")
    parser.add_argument("--qc")
    parser.add_argument("--processing-report")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = classify_rebeat_evidence(
        discovery=_load_json(args.discovery),
        tempo_grid=_load_json(args.tempo_grid),
        events=_load_json(args.events),
        rpp_audit=_load_json(args.rpp_audit),
        midi_audit=_load_json(args.midi_audit),
        qc=_load_json(args.qc),
        processing_report=_load_json(args.processing_report),
    )
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
