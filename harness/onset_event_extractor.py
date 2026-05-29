from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
    from .tempo_grid_analyzer import DEFAULT_PROFILE, load_profile, read_audio
except ImportError:  # pragma: no cover - direct script execution.
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
    from tempo_grid_analyzer import DEFAULT_PROFILE, load_profile, read_audio


EPS = 1e-12


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _band_energy_frames(mono: Any, sample_rate: int, bands: dict[str, tuple[float, float]]) -> tuple[dict[str, Any], float]:
    if np is None:
        return {name: [] for name in bands}, 0.0
    frame = max(512, int(sample_rate * 0.025))
    hop = max(128, int(sample_rate * 0.01))
    if mono.size < frame:
        return {name: np.array([], dtype=np.float64) for name in bands}, hop / sample_rate
    count = 1 + (mono.size - frame) // hop
    window = np.hanning(frame)
    freqs = np.fft.rfftfreq(frame, 1.0 / sample_rate)
    results = {name: np.zeros(count, dtype=np.float64) for name in bands}
    for idx in range(count):
        start = idx * hop
        chunk = mono[start : start + frame] * window
        spectrum = np.abs(np.fft.rfft(chunk))
        power = spectrum * spectrum
        total = float(np.sum(power)) + EPS
        for name, (low, high) in bands.items():
            mask = (freqs >= low) & (freqs < high)
            results[name][idx] = float(np.sum(power[mask])) / total
    for name, values in results.items():
        diff = np.maximum(0.0, np.diff(values, prepend=values[0]))
        if np.max(diff) > 0:
            diff = diff / (float(np.max(diff)) + EPS)
        results[name] = diff
    return results, hop / sample_rate


def _peak_pick(values: Any, hop_sec: float, min_distance_sec: float, threshold: float) -> list[tuple[int, float]]:
    if np is None or values.size < 3:
        return []
    min_distance = max(1, int(min_distance_sec / max(hop_sec, EPS)))
    peaks: list[tuple[int, float]] = []
    last = -min_distance
    adaptive = max(threshold, float(np.median(values) + np.std(values) * 1.2))
    for idx in range(1, values.size - 1):
        value = float(values[idx])
        if value < adaptive or value < values[idx - 1] or value < values[idx + 1]:
            continue
        if idx - last < min_distance:
            if peaks and value > peaks[-1][1]:
                peaks[-1] = (idx, value)
                last = idx
            continue
        peaks.append((idx, value))
        last = idx
    return peaks


def _beat_position(time_sec: float, selected_bpm: float | None) -> float | None:
    if not selected_bpm:
        return None
    return time_sec / (60.0 / selected_bpm)


def _quantized(time_sec: float, selected_bpm: float | None, strength: float) -> tuple[float | None, float | None]:
    if not selected_bpm:
        return None, None
    beat = 60.0 / selected_bpm
    grid = beat / 4.0
    snapped = round(time_sec / grid) * grid
    quantized = time_sec + (snapped - time_sec) * max(0.0, min(1.0, strength))
    return quantized, quantized - time_sec


def extract_onset_events(
    input_path: str | Path,
    *,
    tempo_grid_path: str | Path | None = None,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    findings: list[Finding] = []
    profile = load_profile(profile_path or DEFAULT_PROFILE)
    tempo_grid = _load_json(tempo_grid_path)
    sample_rate, mono = read_audio(input_path, findings)
    selected_bpm = tempo_grid.get("selected_bpm")
    selected_bpm = float(selected_bpm) if selected_bpm else None
    if tempo_grid_path and tempo_grid.get("grid_confidence") in {"FAIL", "BLOCKER"}:
        add_finding(
            "WARN",
            "GRID_NOT_SAFE_FOR_ONSET_QUANTIZE",
            "Tempo/grid report is not safe for quantized MIDI reconstruction.",
            f"grid_confidence={tempo_grid.get('grid_confidence')}",
            "Export events as detection candidates only; do not claim timing correction or rebeat.",
            findings,
            affected_file=str(tempo_grid_path),
            failed_assumption="Grid is safe for event quantization.",
            human_listening_required=True,
        )

    onset_cfg = profile.get("onset", {})
    bands = {
        "kick": tuple(onset_cfg.get("kick_band_hz", [45, 140])),
        "snare_clap": tuple(onset_cfg.get("snare_band_hz", [150, 5000])),
        "hat_perc": tuple(onset_cfg.get("hat_band_hz", [6000, 14000])),
        "bass": tuple(onset_cfg.get("kick_band_hz", [45, 140])),
    }
    band_frames, hop_sec = _band_energy_frames(mono, sample_rate, bands)
    min_distance = float(onset_cfg.get("peak_pick_distance_sec", 0.08))
    min_confidence = float(onset_cfg.get("min_event_confidence", 0.45))
    hat_min = float(onset_cfg.get("hat_min_confidence", 0.7))
    quantize_strength = float(profile.get("midi", {}).get("quantize_strength", 0.3))

    raw_events: dict[int, dict[str, Any]] = {}
    for event_type, values in band_frames.items():
        threshold = hat_min if event_type == "hat_perc" else min_confidence
        for frame_idx, strength in _peak_pick(values, hop_sec, min_distance, threshold):
            time_sec = frame_idx * hop_sec
            current = raw_events.get(frame_idx)
            if current is None or strength > current["confidence"]:
                raw_events[frame_idx] = {
                    "time_sec": round(time_sec, 6),
                    "event_type": event_type,
                    "confidence": round(float(strength), 4),
                    "source_band_evidence": {
                        "kick": round(float(band_frames["kick"][frame_idx]), 4),
                        "snare_clap": round(float(band_frames["snare_clap"][frame_idx]), 4),
                        "hat_perc": round(float(band_frames["hat_perc"][frame_idx]), 4),
                    },
                }

    events = []
    for frame_idx in sorted(raw_events):
        event = raw_events[frame_idx]
        time_sec = float(event["time_sec"])
        quantized, deviation = _quantized(time_sec, selected_bpm, quantize_strength)
        event["beat_position"] = round(_beat_position(time_sec, selected_bpm), 4) if selected_bpm else None
        event["quantized_position_sec"] = round(quantized, 6) if quantized is not None else None
        event["timing_deviation_sec"] = round(deviation, 6) if deviation is not None else None
        event["used_in_midi_reconstruction"] = event["confidence"] >= (hat_min if event["event_type"] == "hat_perc" else min_confidence)
        events.append(event)

    if not events:
        add_finding(
            "WARN",
            "NO_ONSET_EVENTS_EXTRACTED",
            "No onset events met the extraction threshold.",
            f"input={input_path}",
            "Use manual MIDI placement or lower thresholds after checking false-positive risk.",
            findings,
            affected_file=str(input_path),
            failed_assumption="Detected events are available for reinforcement.",
            human_listening_required=True,
        )

    counts: dict[str, int] = {"kick": 0, "snare_clap": 0, "hat_perc": 0, "bass": 0, "percussion": 0}
    for event in events:
        counts[event["event_type"]] = counts.get(event["event_type"], 0) + 1

    payload = {
        "schema_version": 1,
        "input": str(input_path),
        "profile": profile.get("profile_name", "unknown"),
        "tempo_grid": str(tempo_grid_path or ""),
        "selected_bpm": selected_bpm,
        "event_counts": counts,
        "events": events,
        "notes": [
            "Bass onset extraction from fullmix is weak evidence. Do not claim bass MIDI reconstruction from these events alone.",
            "Hat/percussion extraction uses stricter confidence to avoid turning AI fizz into MIDI.",
        ],
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    rows = []
    for event in payload.get("events", [])[:250]:
        rows.append(
            "| {time} | {beat} | {kind} | {conf} | {q} | {dev} | {used} |".format(
                time=event.get("time_sec"),
                beat=event.get("beat_position"),
                kind=event.get("event_type"),
                conf=event.get("confidence"),
                q=event.get("quantized_position_sec"),
                dev=event.get("timing_deviation_sec"),
                used=event.get("used_in_midi_reconstruction"),
            )
        )
    if not rows:
        rows.append("| - | - | - | - | - | - | - |")
    return "\n".join(
        [
            "# Onset Event Extraction",
            "",
            f"- Input: `{payload.get('input')}`",
            f"- Selected BPM: `{payload.get('selected_bpm')}`",
            f"- Max severity: `{payload.get('max_severity')}`",
            f"- Event counts: `{json.dumps(payload.get('event_counts'), sort_keys=True)}`",
            "",
            "## Events",
            "",
            "| Time sec | Beat | Type | Confidence | Quantized sec | Timing deviation | Used in MIDI |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract kick/snare/hat/percussion onset events for drum reinforcement.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--tempo-grid")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = extract_onset_events(args.input, tempo_grid_path=args.tempo_grid, profile_path=args.profile)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
