from __future__ import annotations

import argparse
import json
import math
import wave
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover - minimal Python installs.
    np = None  # type: ignore[assignment]

try:
    from scipy.io import wavfile as scipy_wavfile
except Exception:  # pragma: no cover - optional dependency.
    scipy_wavfile = None  # type: ignore[assignment]

try:
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover - direct script execution.
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "presets" / "rebeat_profiles" / "fullmix_drum_reinforcement.json"
EPS = 1e-12


def load_profile(path: str | Path | None = None) -> dict[str, Any]:
    profile_path = Path(path) if path else DEFAULT_PROFILE
    if not profile_path.exists():
        candidate = ROOT / "presets" / "rebeat_profiles" / f"{profile_path}.json"
        if candidate.exists():
            profile_path = candidate
    with profile_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_audio(path: str | Path, findings: list[Finding] | None = None) -> tuple[int, Any]:
    findings = findings if findings is not None else []
    audio_path = Path(path)
    if not audio_path.exists():
        add_finding(
            "BLOCKER",
            "SOURCE_AUDIO_MISSING",
            "Source audio is missing.",
            str(audio_path),
            "Provide a valid source audio path and rerun tempo/grid analysis.",
            findings,
            affected_file=str(audio_path),
            failed_assumption="Tempo/grid source exists.",
        )
        raise FileNotFoundError(audio_path)

    if np is None:
        add_finding(
            "BLOCKER",
            "NUMPY_REQUIRED_FOR_TEMPO_GRID",
            "Tempo/grid analysis requires numpy.",
            "numpy import failed.",
            "Run in an environment with numpy available.",
            findings,
            affected_file=str(audio_path),
            failed_assumption="Numerical audio analysis dependencies are available.",
        )
        raise RuntimeError("numpy is required")

    try:
        with wave.open(str(audio_path), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            raw = handle.readframes(handle.getnframes())
        if width == 1:
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            data = (data - 128.0) / 128.0
        elif width == 2:
            data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif width == 3:
            bytes_data = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            signed = (
                bytes_data[:, 0].astype(np.int32)
                | (bytes_data[:, 1].astype(np.int32) << 8)
                | (bytes_data[:, 2].astype(np.int32) << 16)
            )
            signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
            data = signed.astype(np.float32) / 8388608.0
        elif width == 4:
            data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"unsupported WAV sample width: {width}")
        if len(data) % channels:
            data = data[: len(data) - (len(data) % channels)]
        samples = data.reshape((-1, channels))
    except Exception as exc:
        if scipy_wavfile is None:
            add_finding(
                "BLOCKER",
                "AUDIO_READ_FAILED",
                "Audio could not be read as WAV and scipy fallback is unavailable.",
                str(exc),
                "Convert to PCM WAV or install scipy, then rerun tempo/grid analysis.",
                findings,
                affected_file=str(audio_path),
                failed_assumption="Input audio is readable.",
            )
            raise
        sample_rate, scipy_data = scipy_wavfile.read(str(audio_path))
        samples = scipy_data.astype(np.float32, copy=False)
        if np.issubdtype(scipy_data.dtype, np.integer):
            info = np.iinfo(scipy_data.dtype)
            samples = samples / float(max(abs(info.min), info.max))
        if samples.ndim == 1:
            samples = samples.reshape((-1, 1))
        add_finding(
            "INFO",
            "SCIPY_AUDIO_READ_FALLBACK",
            "Read audio through scipy fallback.",
            str(exc),
            "No action needed if tempo/grid confidence passes.",
            findings,
            affected_file=str(audio_path),
        )

    mono = np.mean(samples, axis=1).astype(np.float64, copy=False)
    mono = np.nan_to_num(mono)
    if mono.size < sample_rate * 0.25:
        add_finding(
            "FAIL",
            "SOURCE_TOO_SHORT_FOR_GRID",
            "Source is too short for reliable tempo/grid analysis.",
            f"duration_sec={mono.size / max(1, sample_rate):.3f}",
            "Provide a longer section or full song source.",
            findings,
            affected_file=str(audio_path),
            failed_assumption="Source duration is sufficient for tempo analysis.",
        )
    return int(sample_rate), mono


def _frame_rms(mono: Any, sample_rate: int, frame_sec: float = 0.0232, hop_sec: float = 0.0116) -> tuple[Any, float]:
    frame = max(256, int(sample_rate * frame_sec))
    hop = max(64, int(sample_rate * hop_sec))
    if mono.size < frame:
        return np.array([], dtype=np.float64), hop / sample_rate
    count = 1 + (mono.size - frame) // hop
    energy = np.empty(count, dtype=np.float64)
    window = np.hanning(frame)
    for idx in range(count):
        start = idx * hop
        chunk = mono[start : start + frame] * window
        energy[idx] = math.sqrt(float(np.mean(chunk * chunk)) + EPS)
    return energy, hop / sample_rate


def onset_envelope(mono: Any, sample_rate: int) -> tuple[Any, float]:
    energy, hop_sec = _frame_rms(mono, sample_rate)
    if energy.size < 3:
        return energy, hop_sec
    envelope = np.maximum(0.0, np.diff(energy, prepend=energy[0]))
    if np.max(envelope) > 0:
        envelope = envelope / (float(np.max(envelope)) + EPS)
    return envelope, hop_sec


def peak_pick(envelope: Any, hop_sec: float, min_distance_sec: float = 0.08, threshold_scale: float = 1.4) -> list[dict[str, float]]:
    if np is None or envelope.size < 3:
        return []
    min_distance = max(1, int(min_distance_sec / max(hop_sec, EPS)))
    threshold = float(np.median(envelope) + np.std(envelope) * threshold_scale)
    threshold = max(threshold, float(np.percentile(envelope, 75)) * 0.5)
    events: list[dict[str, float]] = []
    last_index = -min_distance
    for idx in range(1, envelope.size - 1):
        value = float(envelope[idx])
        if value < threshold or value < envelope[idx - 1] or value < envelope[idx + 1]:
            continue
        if idx - last_index < min_distance:
            if events and value > events[-1]["strength"]:
                events[-1] = {"time_sec": idx * hop_sec, "strength": value}
                last_index = idx
            continue
        events.append({"time_sec": idx * hop_sec, "strength": value})
        last_index = idx
    return events


def _normalize_bpm(bpm: float, low: float, high: float) -> float:
    while bpm < low and bpm * 2 <= high * 1.2:
        bpm *= 2.0
    while bpm > high and bpm / 2 >= low * 0.8:
        bpm /= 2.0
    return bpm


def _candidate_bpms(onsets: list[dict[str, float]], profile: dict[str, Any]) -> list[dict[str, float]]:
    if len(onsets) < 3 or np is None:
        return []
    times = np.array([event["time_sec"] for event in onsets], dtype=np.float64)
    diffs = []
    for span in range(1, min(5, len(times))):
        diff = times[span:] - times[:-span]
        diff = diff[(diff >= 0.18) & (diff <= 1.5)]
        diffs.extend(float(value / span) for value in diff)
    if not diffs:
        return []
    low, high = [float(value) for value in profile.get("tempo_bpm_range", [70, 190])]
    raw_bpms = [_normalize_bpm(60.0 / diff, low, high) for diff in diffs if diff > 0]
    bins: dict[int, list[float]] = {}
    for bpm in raw_bpms:
        rounded = int(round(bpm))
        bins.setdefault(rounded, []).append(bpm)
    candidates = []
    total = max(1, len(raw_bpms))
    for rounded, values in sorted(bins.items(), key=lambda item: len(item[1]), reverse=True)[:8]:
        bpm = float(np.median(values))
        candidates.append({"bpm": round(bpm, 3), "score": round(len(values) / total, 4), "support_count": len(values)})
    return candidates


def _grid_fit_score(onsets: list[dict[str, float]], bpm: float) -> tuple[float, float, list[float]]:
    if not onsets or bpm <= 0 or np is None:
        return 0.0, 0.0, []
    beat = 60.0 / bpm
    subdivisions = [beat, beat / 2.0, beat / 4.0]
    best_score = 0.0
    best_dev = []
    best_subdivision = subdivisions[0]
    times = np.array([event["time_sec"] for event in onsets], dtype=np.float64)
    for subdivision in subdivisions:
        offsets = []
        for candidate_offset in times[: min(8, len(times))]:
            phase = np.mod(times - candidate_offset + subdivision / 2.0, subdivision) - subdivision / 2.0
            offsets.append((float(np.median(np.abs(phase))), phase))
        if not offsets:
            continue
        median_dev, phase = min(offsets, key=lambda item: item[0])
        score = max(0.0, 1.0 - median_dev / max(subdivision * 0.32, EPS))
        if score > best_score:
            best_score = score
            best_dev = [float(value) for value in phase]
            best_subdivision = subdivision
    median_deviation = float(np.median(np.abs(best_dev))) if best_dev else 0.0
    return best_score, median_deviation, [round(value, 5) for value in best_dev[:200]]


def _section_hints(duration: float) -> list[dict[str, float | str]]:
    if duration < 16:
        return []
    section_len = 16.0
    hints = []
    current = 0.0
    index = 1
    while current < duration:
        hints.append({"label": f"section_{index:02d}", "time_sec": round(current, 3)})
        current += section_len
        index += 1
    return hints


def analyze_tempo_grid(input_path: str | Path, profile_path: str | Path | None = None) -> dict[str, Any]:
    findings: list[Finding] = []
    profile = load_profile(profile_path)
    sample_rate, mono = read_audio(input_path, findings)
    duration = float(mono.size / max(1, sample_rate))
    envelope, hop_sec = onset_envelope(mono, sample_rate)
    onsets = peak_pick(
        envelope,
        hop_sec,
        min_distance_sec=float(profile.get("onset", {}).get("peak_pick_distance_sec", 0.08)),
    )
    candidates = _candidate_bpms(onsets, profile)

    selected = candidates[0] if candidates else None
    grid_score = 0.0
    median_dev = None
    deviations: list[float] = []
    if selected:
        fit_score, median_dev_value, deviations = _grid_fit_score(onsets, float(selected["bpm"]))
        selected["grid_fit_score"] = round(fit_score, 4)
        selected["median_timing_deviation_sec"] = round(median_dev_value, 5)
        grid_score = min(1.0, (float(selected["score"]) * 0.45) + (fit_score * 0.55))
        median_dev = median_dev_value

    qc = profile.get("qc", {})
    pass_score = float(qc.get("grid_pass_score", 0.68))
    warn_score = float(qc.get("grid_warn_score", 0.42))
    if not candidates:
        grid_confidence = "FAIL"
        add_finding(
            "FAIL",
            "NO_USABLE_TEMPO_ESTIMATE",
            "No usable BPM candidate was detected.",
            f"onset_count={len(onsets)}",
            "Use manual BPM/downbeat entry or provide stems/MIDI before claiming beat correction or rebeat.",
            findings,
            affected_file=str(input_path),
            failed_assumption="Tempo can be estimated from the source.",
        )
    elif grid_score >= pass_score:
        grid_confidence = "PASS"
    elif grid_score >= warn_score:
        grid_confidence = "WARN"
        add_finding(
            "WARN",
            "GRID_CONFIDENCE_WARN",
            "Tempo/grid estimate is usable but ambiguous.",
            f"grid_score={grid_score:.3f}, selected_bpm={selected['bpm'] if selected else 'none'}",
            "Use light quantization and require human listening before beat/rebeat claims.",
            findings,
            affected_file=str(input_path),
            failed_assumption="Detected grid is unambiguous.",
            human_listening_required=True,
        )
    else:
        grid_confidence = "FAIL"
        add_finding(
            "FAIL",
            "GRID_CONFIDENCE_FAIL",
            "Tempo/grid confidence is too low for beat correction or rebeat claims.",
            f"grid_score={grid_score:.3f}, selected_bpm={selected['bpm'] if selected else 'none'}",
            "Do not quantize/rebeat; use manual tempo map or stems/MIDI.",
            findings,
            affected_file=str(input_path),
            failed_assumption="Detected grid is safe for reconstruction.",
            human_listening_required=True,
        )

    bpm_values = [candidate["bpm"] for candidate in candidates[:4]]
    alternatives = []
    if selected:
        bpm = float(selected["bpm"])
        alternatives = [
            {"label": "half_time", "bpm": round(bpm / 2.0, 3)},
            {"label": "double_time", "bpm": round(bpm * 2.0, 3)},
        ]
        if len(candidates) > 1 and abs(float(candidates[1]["bpm"]) - bpm) > 3:
            add_finding(
                "WARN",
                "MULTIPLE_BPM_CANDIDATES",
                "Multiple plausible BPM candidates were detected.",
                f"candidates={bpm_values}",
                "Report half/double-time ambiguity and avoid hard quantization until verified.",
                findings,
                affected_file=str(input_path),
                failed_assumption="One BPM candidate is clearly dominant.",
                human_listening_required=True,
            )

    density = len(onsets) / max(duration, EPS)
    downbeat_confidence = min(1.0, grid_score + 0.1) if selected and onsets else 0.0
    tempo_stability = max(0.0, min(1.0, 1.0 - (float(median_dev or 0.0) / 0.08)))
    quantization_safe = grid_confidence == "PASS" or (grid_confidence == "WARN" and tempo_stability > 0.6)

    likely_kicks = [event for event in onsets[:200] if event["strength"] > 0.45][::2]
    likely_snares = [event for event in onsets[:200] if event["strength"] > 0.35][1::2]

    payload = {
        "schema_version": 1,
        "input": str(input_path),
        "profile": profile.get("profile_name", "unknown"),
        "sample_rate_hz": sample_rate,
        "duration_sec": round(duration, 6),
        "onset_count": len(onsets),
        "transient_density_per_sec": round(density, 5),
        "bpm_candidates": candidates,
        "selected_bpm": selected["bpm"] if selected else None,
        "half_double_time_alternatives": alternatives,
        "downbeat_confidence": round(downbeat_confidence, 4),
        "tempo_stability": round(tempo_stability, 4),
        "grid_confidence": grid_confidence,
        "grid_confidence_score": round(grid_score, 4),
        "onset_timing_distribution": {
            "median_deviation_sec": round(float(median_dev or 0.0), 5),
            "deviations_sec_sample": deviations,
        },
        "likely_kick_positions_sec": [round(event["time_sec"], 5) for event in likely_kicks[:128]],
        "likely_snare_positions_sec": [round(event["time_sec"], 5) for event in likely_snares[:128]],
        "section_boundaries": _section_hints(duration),
        "quantization_safe": quantization_safe,
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Tempo/Grid Analysis",
            "",
            f"- Input: `{payload.get('input')}`",
            f"- Profile: `{payload.get('profile')}`",
            f"- Duration: `{payload.get('duration_sec')}` sec",
            f"- Selected BPM: `{payload.get('selected_bpm')}`",
            f"- Grid confidence: `{payload.get('grid_confidence')}` (`{payload.get('grid_confidence_score')}`)",
            f"- Quantization safe: `{payload.get('quantization_safe')}`",
            f"- Onset count: `{payload.get('onset_count')}`",
            f"- Transient density/sec: `{payload.get('transient_density_per_sec')}`",
            "",
            "## BPM Candidates",
            "",
            *[
                f"- `{candidate.get('bpm')}` bpm score `{candidate.get('score')}` support `{candidate.get('support_count')}`"
                for candidate in payload.get("bpm_candidates", [])
            ],
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate tempo/grid evidence for rebeat and drum reinforcement.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = analyze_tempo_grid(args.input, args.profile)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
