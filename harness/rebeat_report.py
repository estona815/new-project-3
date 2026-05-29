from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, findings_to_markdown
except ImportError:  # pragma: no cover
    from severity import Finding, findings_to_markdown


def _load(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_rebeat_report(
    *,
    classification: dict[str, Any],
    discovery: dict[str, Any] | None = None,
    tempo_grid: dict[str, Any] | None = None,
    events: dict[str, Any] | None = None,
    midi_audit: dict[str, Any] | None = None,
    qc: dict[str, Any] | None = None,
    deliverables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    discovery = discovery or {}
    tempo_grid = tempo_grid or {}
    events = events or {}
    midi_audit = midi_audit or {}
    qc = qc or {}
    deliverables = deliverables or {}
    all_findings = []
    for payload in (classification, discovery, tempo_grid, events, midi_audit, qc):
        all_findings.extend(payload.get("findings", []) if isinstance(payload, dict) else [])

    return {
        "schema_version": 1,
        "actual_classification": classification.get("classification", "unknown"),
        "true_rebeat_possible": classification.get("true_rebeat_possible", False),
        "forbidden_classification_note": _forbidden_note(classification),
        "source_evidence": {
            "selected_source": discovery.get("selected_source") or discovery.get("source"),
            "source_format": discovery.get("source_format"),
            "source_is_lossy": classification.get("evidence_summary", {}).get("source_lossy"),
            "available_stems": discovery.get("available_stems") or discovery.get("stems", []),
            "available_midi": discovery.get("available_midi") or discovery.get("midi_files", []),
            "available_rpp": discovery.get("available_rpp") or discovery.get("rpp_files", []),
        },
        "tempo_grid_evidence": {
            "bpm_candidates": tempo_grid.get("bpm_candidates", []),
            "selected_bpm": tempo_grid.get("selected_bpm"),
            "grid_confidence": tempo_grid.get("grid_confidence"),
            "downbeat_confidence": tempo_grid.get("downbeat_confidence"),
            "half_double_time_alternatives": tempo_grid.get("half_double_time_alternatives", []),
        },
        "midi_event_evidence": {
            "event_counts": events.get("event_counts", {}),
            "kick_note_count": midi_audit.get("kick_note_count", 0),
            "snare_note_count": midi_audit.get("snare_note_count", 0),
            "hat_note_count": midi_audit.get("hat_note_count", 0),
            "bass_note_count": midi_audit.get("bass_note_count", 0),
            "music_note_count": midi_audit.get("music_note_count", 0),
            "has_separate_bus_renders": midi_audit.get("has_separate_bus_renders", False),
        },
        "reaper_evidence": {
            "rpp": midi_audit.get("rpp"),
            "track_count": midi_audit.get("track_count"),
            "tracks": [track.get("name") for track in midi_audit.get("tracks", [])],
            "bus_renders": midi_audit.get("bus_renders", {}),
        },
        "candidate_qc": qc.get("candidate_results", []),
        "deliverables": deliverables,
        "allowed_claims": classification.get("allowed_claims", []),
        "forbidden_claims": classification.get("forbidden_claims", []),
        "missing_evidence_for_true_rebeat": classification.get("missing_evidence_for_true_rebeat", []),
        "findings": all_findings,
        "rerun_commands": {
            "tempo_grid": "python3 harness/tempo_grid_analyzer.py --input PATH_TO_WORKING_WAV --profile presets/rebeat_profiles/dnb_rebeat.json --out-json reports/song_vNEXT_tempo_grid.json --out-md reports/song_vNEXT_tempo_grid.md",
            "onset_events": "python3 harness/onset_event_extractor.py --input PATH_TO_WORKING_WAV --tempo-grid reports/song_vNEXT_tempo_grid.json --out-json reports/song_vNEXT_onset_events.json --out-md reports/song_vNEXT_onset_events.md",
            "midi_audit": "python3 harness/midi_reconstruction_audit.py --rpp PATH_TO_PROJECT.rpp --bus-render-dir renders/song_vNEXT --out-json reports/song_vNEXT_midi_reconstruction_audit.json --out-md reports/song_vNEXT_midi_reconstruction_audit.md",
            "rebeat_qc": "python3 harness/rebeat_qc.py --candidate-report reports/song_vNEXT_rebeat_candidates.json --profile presets/rebeat_profiles/dnb_rebeat.json --out-json reports/song_vNEXT_rebeat_qc.json --out-md reports/song_vNEXT_rebeat_qc.md",
            "classification": "python3 harness/rebeat_classification.py --discovery reports/song_vNEXT_rebeat_discovery.json --tempo-grid reports/song_vNEXT_tempo_grid.json --events reports/song_vNEXT_onset_events.json --rpp-audit reports/song_vNEXT_rpp_audit.json --midi-audit reports/song_vNEXT_midi_reconstruction_audit.json --qc reports/song_vNEXT_rebeat_qc.json --out-json reports/song_vNEXT_rebeat_classification.json --out-md reports/song_vNEXT_rebeat_classification.md",
        },
    }


def _forbidden_note(classification: dict[str, Any]) -> str:
    if classification.get("classification") == "true_rebeat":
        return "true_rebeat is allowed by supplied evidence."
    missing = classification.get("missing_evidence_for_true_rebeat", [])
    if missing:
        return "Not true_rebeat because missing: " + "; ".join(missing)
    return "Not true_rebeat by current classification."


def markdown_report(payload: dict[str, Any]) -> str:
    finding_objs = []
    for finding in payload.get("findings", []):
        if isinstance(finding, dict) and "severity" in finding:
            finding_objs.append(Finding(**finding))
    return "\n".join(
        [
            "# Rebeat Report",
            "",
            f"- Actual classification: `{payload.get('actual_classification')}`",
            f"- True rebeat possible: `{payload.get('true_rebeat_possible')}`",
            f"- Forbidden classification note: {payload.get('forbidden_classification_note')}",
            "",
            "## Source Evidence",
            "",
            "```json",
            json.dumps(payload.get("source_evidence", {}), indent=2, sort_keys=True),
            "```",
            "",
            "## Tempo/Grid Evidence",
            "",
            "```json",
            json.dumps(payload.get("tempo_grid_evidence", {}), indent=2, sort_keys=True),
            "```",
            "",
            "## MIDI/Event Evidence",
            "",
            "```json",
            json.dumps(payload.get("midi_event_evidence", {}), indent=2, sort_keys=True),
            "```",
            "",
            "## Allowed Claims",
            "",
            *[f"- `{claim}`" for claim in payload.get("allowed_claims", [])],
            "",
            "## Forbidden Claims",
            "",
            *[f"- `{claim}`" for claim in payload.get("forbidden_claims", [])],
            "",
            "## WARN/FAIL/BLOCKER Findings",
            "",
            findings_to_markdown(finding_objs),
            "",
            "## Rerun Commands",
            "",
            *[f"- `{command}`" for command in payload.get("rerun_commands", {}).values()],
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble a final rebeat evidence report from harness artifacts.")
    parser.add_argument("--classification", required=True)
    parser.add_argument("--discovery")
    parser.add_argument("--tempo-grid")
    parser.add_argument("--events")
    parser.add_argument("--midi-audit")
    parser.add_argument("--qc")
    parser.add_argument("--deliverables")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = build_rebeat_report(
        classification=_load(args.classification),
        discovery=_load(args.discovery),
        tempo_grid=_load(args.tempo_grid),
        events=_load(args.events),
        midi_audit=_load(args.midi_audit),
        qc=_load(args.qc),
        deliverables=_load(args.deliverables),
    )
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
