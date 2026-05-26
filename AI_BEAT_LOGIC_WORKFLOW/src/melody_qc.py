from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np

from hook_motif_generator import motif_repetition_report
from simple_synth_renderer import note_to_midi


def _lead_motif(plan: dict[str, Any]) -> dict[str, Any]:
    motifs = list(plan.get("motifs", []))
    return next((motif for motif in motifs if motif.get("motif_id") == "lead_A"), motifs[0] if motifs else {})


def _duration_beats(value: str) -> float:
    return {
        "1/16": 0.25,
        "1/8": 0.5,
        "1/4": 1.0,
        "1/2": 2.0,
        "1": 4.0,
    }.get(str(value), 0.5)


def _bar_fill_ratios(notes: list[dict[str, Any]], bars: int) -> list[float]:
    fill = [0.0 for _ in range(max(1, bars))]
    for note in notes:
        bar_index = max(0, min(len(fill) - 1, int(note.get("bar", 1)) - 1))
        fill[bar_index] += _duration_beats(str(note.get("duration", "1/8")))
    return [min(1.0, value / 4.0) for value in fill]


def _pitch_metrics(notes: list[dict[str, Any]]) -> dict[str, Any]:
    midi_notes: list[int] = []
    invalid_notes: list[str] = []
    for note in notes:
        try:
            midi_notes.append(note_to_midi(str(note.get("note", ""))))
        except (TypeError, ValueError):
            invalid_notes.append(str(note.get("note", "")))
    intervals = [abs(right - left) for left, right in zip(midi_notes, midi_notes[1:])]
    return {
        "invalid_notes": invalid_notes,
        "pitch_range_semitones": max(midi_notes) - min(midi_notes) if midi_notes else 0,
        "large_jump_count": sum(1 for interval in intervals if interval > 12),
        "unique_note_count": len(set(midi_notes)),
        "midi_notes": midi_notes,
    }


def qc_lead_melody_plan(plan: dict[str, Any]) -> dict[str, Any]:
    motifs = list(plan.get("motifs", []))
    lead = _lead_motif(plan)
    notes = list(lead.get("notes", []))
    bars = int(lead.get("bars", 0) or 0)
    note_count = len(notes)
    repetition = motif_repetition_report(motifs) if motifs else {
        "has_repetition": False,
        "has_variation": False,
        "repeated_rhythm_positions": 0,
        "variation_notes": 0,
        "note_count": 0,
    }
    pitch = _pitch_metrics(notes)
    fill_ratios = _bar_fill_ratios(notes, bars or 1)
    density = note_count / max(1, bars)
    issues: list[str] = []

    if plan.get("schema_version") != "lead_melody_plan.v1":
        issues.append("lead_melody_plan schema_version is missing or unsupported")
    if not notes:
        issues.append("lead_A has no notes")
    if bars < 2:
        issues.append("lead_A should be at least 2 bars")
    if not repetition["has_repetition"]:
        issues.append("lead_A needs a recognizable repeated rhythm or contour")
    if not repetition["has_variation"]:
        issues.append("lead_A repeats without a clear variation")
    if pitch["invalid_notes"]:
        issues.append("lead_A contains invalid note names")
    if density > 7.0:
        issues.append("lead_A is too dense and may read as random note soup")
    if pitch["large_jump_count"] > max(1, note_count // 3):
        issues.append("lead_A has too many large jumps for a singable hook")
    if fill_ratios and min(fill_ratios) > 0.9:
        issues.append("lead_A has almost no rests")
    if (plan.get("safety") or {}).get("exact_reference_melody_copy") is True:
        issues.append("safety flag indicates exact reference melody copying")
    if (plan.get("safety") or {}).get("artist_melody_imitation_claimed") is True:
        issues.append("safety flag indicates artist melody imitation claim")

    plan_pass = not issues
    return {
        "schema_version": "melody_qc.v1",
        "status": "PASS" if plan_pass else "NEEDS_REVISION",
        "plan_pass": plan_pass,
        "issues": issues,
        "metrics": {
            "motif_count": len(motifs),
            "lead_note_count": note_count,
            "lead_bars": bars,
            "notes_per_bar": round(density, 3),
            "bar_fill_ratios": [round(value, 3) for value in fill_ratios],
            "repetition": repetition,
            "pitch_range_semitones": pitch["pitch_range_semitones"],
            "large_jump_count": pitch["large_jump_count"],
            "unique_note_count": pitch["unique_note_count"],
        },
        "safety": {
            "proposed_motif_not_final_composition": True,
            "exact_reference_melody_copy": bool((plan.get("safety") or {}).get("exact_reference_melody_copy", False)),
            "artist_melody_imitation_claimed": bool((plan.get("safety") or {}).get("artist_melody_imitation_claimed", False)),
        },
    }


def _read_wav_samples(path: Path) -> tuple[dict[str, Any], np.ndarray]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)
    if sample_width != 2:
        raise ValueError("Only PCM16 WAV render QC is supported")
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32)
    if channels > 0:
        samples = samples.reshape(-1, channels)
    samples /= 32768.0
    return {
        "path": str(path),
        "channels": channels,
        "sample_rate": sample_rate,
        "bit_depth": sample_width * 8,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate if sample_rate else 0.0,
    }, samples


def qc_rendered_wav(path: str | Path) -> dict[str, Any]:
    wav_path = Path(path)
    issues: list[str] = []
    if not wav_path.exists():
        return {
            "schema_version": "rendered_melody_wav_qc.v1",
            "render_pass": False,
            "issues": [f"rendered WAV not found: {wav_path}"],
            "metrics": {"path": str(wav_path)},
        }
    try:
        metadata, samples = _read_wav_samples(wav_path)
    except (OSError, EOFError, ValueError) as exc:
        return {
            "schema_version": "rendered_melody_wav_qc.v1",
            "render_pass": False,
            "issues": [str(exc)],
            "metrics": {"path": str(wav_path)},
        }

    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    clipping_count = int(np.sum(np.abs(samples) >= 0.999969))
    if metadata["duration_seconds"] <= 0:
        issues.append("rendered WAV has no duration")
    if metadata["sample_rate"] != 48_000:
        issues.append("rendered WAV should be 48 kHz")
    if metadata["channels"] != 2:
        issues.append("rendered WAV should be stereo")
    if clipping_count > 0:
        issues.append("rendered WAV clips")
    if peak <= 0.0001:
        issues.append("rendered WAV is effectively silent")
    if peak > 0.98:
        issues.append("rendered WAV leaves no practical headroom")

    render_pass = not issues
    return {
        "schema_version": "rendered_melody_wav_qc.v1",
        "render_pass": render_pass,
        "issues": issues,
        "metrics": {
            **metadata,
            "peak_linear": round(peak, 6),
            "clipping_count": clipping_count,
        },
    }


def run_melody_qc(lead_plan: dict[str, Any], rendered_paths: list[str | Path] | None = None) -> dict[str, Any]:
    render_reports = [qc_rendered_wav(path) for path in (rendered_paths or [])]
    plan_report = qc_lead_melody_plan(lead_plan)
    return {
        "schema_version": "melody_qc_bundle.v1",
        "status": "PASS" if plan_report["plan_pass"] and all(report["render_pass"] for report in render_reports) else "NEEDS_REVISION",
        "plan_qc": plan_report,
        "render_qc": render_reports,
    }
