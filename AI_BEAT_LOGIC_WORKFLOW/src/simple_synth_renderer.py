from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal


NOTE_TO_PC = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "BB": 10,
    "B": 11,
}


def note_to_midi(note: str) -> int:
    text = str(note).strip().replace("♯", "#").replace("♭", "b")
    if len(text) < 2:
        raise ValueError(f"Invalid note: {note}")
    if len(text) >= 3 and text[1] in {"#", "b"}:
        name = text[0].upper() + text[1]
        octave_text = text[2:]
    else:
        name = text[:1].upper()
        octave_text = text[1:]
    if name not in NOTE_TO_PC:
        raise ValueError(f"Invalid note name: {note}")
    octave = int(octave_text)
    return (octave + 1) * 12 + NOTE_TO_PC[name]


def note_to_frequency(note: str) -> float:
    midi = note_to_midi(note)
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def duration_to_beats(value: str) -> float:
    return {
        "1/16": 0.25,
        "1/8": 0.5,
        "1/4": 1.0,
        "1/2": 2.0,
        "1": 4.0,
    }.get(str(value), 0.5)


def oscillator(frequency: float, seconds: float, sample_rate: int, waveform: str = "square", phase: float = 0.0) -> np.ndarray:
    frames = max(1, int(seconds * sample_rate))
    t = np.arange(frames, dtype=np.float32) / sample_rate
    angle = 2.0 * math.pi * frequency * t + phase
    if waveform == "sine":
        return np.sin(angle).astype(np.float32)
    if waveform == "saw":
        return signal.sawtooth(angle).astype(np.float32)
    if waveform == "triangle":
        return signal.sawtooth(angle, width=0.5).astype(np.float32)
    return signal.square(angle).astype(np.float32)


def adsr(length: int, sample_rate: int, attack: float = 0.006, decay: float = 0.045, sustain: float = 0.56, release: float = 0.055) -> np.ndarray:
    if length <= 0:
        return np.zeros(0, dtype=np.float32)
    env = np.ones(length, dtype=np.float32) * sustain
    a = min(length, max(1, int(attack * sample_rate)))
    d = min(max(0, length - a), max(1, int(decay * sample_rate)))
    r = min(length, max(1, int(release * sample_rate)))
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    if d > 0:
        env[a : a + d] = np.linspace(1.0, sustain, d, dtype=np.float32)
    env[-r:] *= np.linspace(1.0, 0.0, r, dtype=np.float32)
    return env


def _lead_type_to_waveform(lead_type: str) -> str:
    return {
        "digital_pluck": "square",
        "bright_square": "square",
        "soft_saw": "saw",
        "bell_pluck": "sine",
    }.get(lead_type, "square")


def _lowpass(audio: np.ndarray, sample_rate: int, cutoff: float = 8_800.0) -> np.ndarray:
    if audio.size == 0 or cutoff >= sample_rate / 2:
        return audio.astype(np.float32)
    sos = signal.butter(2, cutoff, fs=sample_rate, btype="lowpass", output="sos")
    return signal.sosfilt(sos, audio, axis=0).astype(np.float32)


def _highpass(audio: np.ndarray, sample_rate: int, cutoff: float = 160.0) -> np.ndarray:
    if audio.size == 0:
        return audio.astype(np.float32)
    sos = signal.butter(2, cutoff, fs=sample_rate, btype="highpass", output="sos")
    return signal.sosfilt(sos, audio, axis=0).astype(np.float32)


def _pan_mono(samples: np.ndarray, pan: float) -> np.ndarray:
    angle = (max(-1.0, min(1.0, pan)) + 1.0) * math.pi / 4.0
    return np.column_stack((samples * math.cos(angle), samples * math.sin(angle))).astype(np.float32)


def _add(buf: np.ndarray, start_frame: int, clip: np.ndarray) -> None:
    if start_frame >= len(buf):
        return
    if start_frame < 0:
        clip = clip[-start_frame:]
        start_frame = 0
    end = min(len(buf), start_frame + len(clip))
    if end > start_frame:
        buf[start_frame:end] += clip[: end - start_frame]


def motif_duration_seconds(motif: dict[str, Any], bpm: float) -> float:
    beats = float(motif.get("bars", 1)) * 4.0
    return beats * 60.0 / max(1.0, bpm)


def render_motifs_to_audio(
    motifs: list[dict[str, Any]],
    *,
    tempo_bpm: float,
    sound_design: dict[str, Any] | None = None,
    sample_rate: int = 48_000,
    repeat_hook: int = 1,
) -> np.ndarray:
    design = sound_design or {}
    waveform = _lead_type_to_waveform(str(design.get("lead_type", "digital_pluck")))
    beat_seconds = 60.0 / max(1.0, float(tempo_bpm))
    total_bars = sum(int(motif.get("bars", 1)) for motif in motifs) * max(1, repeat_hook)
    total_seconds = total_bars * 4.0 * beat_seconds + 0.7
    audio = np.zeros((int(total_seconds * sample_rate), 2), dtype=np.float32)
    cursor_bars = 0
    for _repeat in range(max(1, repeat_hook)):
        for motif_index, motif in enumerate(motifs):
            motif_start = cursor_bars * 4.0 * beat_seconds
            for note_index, note in enumerate(motif.get("notes", [])):
                frequency = note_to_frequency(str(note["note"]))
                duration_seconds = duration_to_beats(str(note.get("duration", "1/8"))) * beat_seconds
                mono = oscillator(frequency, duration_seconds, sample_rate, waveform, phase=note_index * 0.17)
                if design.get("lead_type") in {"digital_pluck", "bright_square"}:
                    detuned = oscillator(frequency * 1.006, duration_seconds, sample_rate, waveform, phase=0.4) * 0.18
                    mono = mono * 0.82 + detuned
                mono *= adsr(len(mono), sample_rate)
                mono = np.tanh(mono * 1.25).astype(np.float32) * 0.23
                bar = int(note.get("bar", 1)) - 1
                beat = float(note.get("beat", 1.0)) - 1.0
                start = motif_start + (bar * 4.0 + beat) * beat_seconds
                pan = 0.0 if motif.get("role") == "main_hook" else (-0.18 if note_index % 2 else 0.18)
                stereo = _pan_mono(mono, pan)
                if design.get("stereo_width") == "medium" and motif_index == 0:
                    upper = oscillator(frequency * 2.0, duration_seconds, sample_rate, "sine", phase=0.2)
                    upper *= adsr(len(upper), sample_rate, attack=0.004, decay=0.035, sustain=0.35, release=0.05)
                    stereo += _pan_mono(upper * 0.045, -0.45 if note_index % 2 else 0.45)
                _add(audio, int(start * sample_rate), stereo)
            cursor_bars += int(motif.get("bars", 1))
    audio = _highpass(_lowpass(audio, sample_rate), sample_rate)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.86:
        audio *= 0.86 / peak
    return np.clip(audio, -0.98, 0.98).astype(np.float32)


def write_wav16(path: str | Path, audio: np.ndarray, sample_rate: int = 48_000) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(2 if pcm.ndim == 2 else 1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return output


def render_lead_plan_to_wav(
    lead_plan: dict[str, Any],
    output_path: str | Path,
    *,
    motif_ids: list[str] | None = None,
    sample_rate: int = 48_000,
) -> dict[str, Any]:
    selected_ids = set(motif_ids or [motif.get("motif_id") for motif in lead_plan.get("motifs", [])])
    motifs = [motif for motif in lead_plan.get("motifs", []) if motif.get("motif_id") in selected_ids]
    audio = render_motifs_to_audio(
        motifs,
        tempo_bpm=float(lead_plan.get("tempo_bpm", 148)),
        sound_design=lead_plan.get("sound_design", {}),
        sample_rate=sample_rate,
    )
    path = write_wav16(output_path, audio, sample_rate)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    clipped = int(np.sum(np.abs(audio) >= 0.999969))
    return {
        "path": str(path),
        "rendered": True,
        "sample_rate": sample_rate,
        "duration_seconds": round(len(audio) / sample_rate, 3),
        "motif_ids": [str(motif.get("motif_id")) for motif in motifs],
        "oscillator": _lead_type_to_waveform(str((lead_plan.get("sound_design") or {}).get("lead_type", "digital_pluck"))),
        "clipping_count": clipped,
        "peak": round(peak, 6),
        "render_note": "Simple synth lead stem rendered from generated melody plan; not a final composition claim.",
    }
