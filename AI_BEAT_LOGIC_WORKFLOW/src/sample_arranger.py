from __future__ import annotations

from typing import Any

import numpy as np
from scipy import signal

from audio_metrics import band_eq, bandpass, db_to_linear, linear_to_db, mono, normalize_peak, pan_mono, rms, rms_db


def pitch_variant(chop: np.ndarray, semitones: float) -> np.ndarray:
    if semitones == 0.0 or chop.shape[0] < 8:
        return chop.astype(np.float32, copy=False)
    semitones = float(np.clip(semitones, -3.0, 3.0))
    factor = 2.0 ** (semitones / 12.0)
    target = max(8, int(chop.shape[0] / factor))
    shifted = signal.resample(mono(chop), target).astype(np.float32)
    if shifted.shape[0] < chop.shape[0]:
        shifted = np.pad(shifted, (0, chop.shape[0] - shifted.shape[0]))
    shifted = shifted[: chop.shape[0], None]
    shifted, _ = normalize_peak(shifted, -9.2, max_gain_db=6.0)
    return shifted.astype(np.float32)


def _transient_density(samples: np.ndarray, sample_rate: int) -> float:
    mono_audio = mono(samples)
    frame = max(128, int(sample_rate * 0.015))
    hop = max(64, frame // 2)
    if mono_audio.shape[0] < frame:
        return 0.0
    values = []
    for start in range(0, mono_audio.shape[0] - frame + 1, hop):
        values.append(float(np.sqrt(np.mean(np.square(mono_audio[start : start + frame], dtype=np.float64)))))
    envelope = np.asarray(values, dtype=np.float32)
    if envelope.size < 3:
        return 0.0
    diff = np.maximum(np.diff(envelope), 0.0)
    threshold = float(np.median(diff) + np.std(diff) * 1.25)
    return round(float(np.sum(diff > threshold)) / max(mono_audio.shape[0] / sample_rate, 1e-9), 3)


def _boundary_click_risk(samples: np.ndarray) -> float:
    mono_audio = mono(samples)
    if mono_audio.shape[0] < 16:
        return 1.0
    edge = max(8, min(256, mono_audio.shape[0] // 12))
    body = float(np.sqrt(np.mean(np.square(mono_audio, dtype=np.float64)))) + 1e-12
    start_risk = abs(float(mono_audio[0]) - float(np.mean(mono_audio[:edge]))) / body
    end_risk = abs(float(mono_audio[-1]) - float(np.mean(mono_audio[-edge:]))) / body
    return round(float(np.clip((start_risk + end_risk) * 0.5, 0.0, 3.0)), 3)


def _loopability(samples: np.ndarray) -> float:
    mono_audio = mono(samples)
    if mono_audio.shape[0] < 512:
        return 0.0
    edge = min(2048, mono_audio.shape[0] // 4)
    start = mono_audio[:edge]
    end = mono_audio[-edge:]
    denom = float(np.linalg.norm(start) * np.linalg.norm(end)) + 1e-12
    corr = float(np.dot(start, end) / denom)
    edge_delta = abs(float(np.mean(start)) - float(np.mean(end)))
    return round(float(np.clip((corr + 1.0) * 0.5 - edge_delta * 2.0, 0.0, 1.0)), 3)


def _tonal_stability(samples: np.ndarray, sample_rate: int) -> float:
    mono_audio = mono(samples)
    frame = max(512, int(sample_rate * 0.04))
    hop = frame // 2
    if mono_audio.shape[0] < frame * 2:
        return 0.5
    centroids = []
    freqs = np.fft.rfftfreq(frame, 1.0 / sample_rate)
    for start in range(0, mono_audio.shape[0] - frame + 1, hop):
        windowed = mono_audio[start : start + frame] * np.hanning(frame)
        spectrum = np.abs(np.fft.rfft(windowed)) + 1e-12
        centroids.append(float(np.sum(freqs * spectrum) / np.sum(spectrum)))
    if not centroids:
        return 0.5
    spread = float(np.std(centroids) / (np.mean(centroids) + 1e-12))
    return round(float(np.clip(1.0 - spread * 2.5, 0.0, 1.0)), 3)


def _brightness(samples: np.ndarray, sample_rate: int) -> float:
    mono_audio = mono(samples)[:, None]
    full = rms(mono_audio) + 1e-12
    bright = rms(bandpass(mono_audio, 4_500.0, 14_000.0, sample_rate)) + 1e-12
    return round(linear_to_db(bright / full), 2)


def _frequency_conflict(samples: np.ndarray, context: np.ndarray | None, sample_rate: int) -> float:
    if context is None or context.size == 0:
        return 0.0
    sample_presence = rms(bandpass(mono(samples)[:, None], 1_200.0, 5_000.0, sample_rate)) + 1e-12
    context_presence = rms(bandpass(mono(context)[:, None], 1_200.0, 5_000.0, sample_rate)) + 1e-12
    return round(float(np.clip(linear_to_db(sample_presence / context_presence) + 12.0, 0.0, 24.0)) / 24.0, 3)


def analyze_sample_candidates(
    samples: list[np.ndarray],
    sample_rate: int,
    beat_context: np.ndarray | None = None,
    vocal_context: np.ndarray | None = None,
    ownership_status: str = "unknown",
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        level = rms_db(sample)
        brightness = _brightness(sample, sample_rate)
        transients = _transient_density(sample, sample_rate)
        loop = _loopability(sample)
        click = _boundary_click_risk(sample)
        tonal = _tonal_stability(sample, sample_rate)
        beat_conflict = _frequency_conflict(sample, beat_context, sample_rate)
        vocal_conflict = _frequency_conflict(sample, vocal_context, sample_rate)
        motif = (
            tonal * 0.3
            + loop * 0.22
            + max(0.0, 1.0 - click / 2.0) * 0.18
            + float(np.clip(transients / 10.0, 0.0, 1.0)) * 0.14
            + max(0.0, 1.0 - vocal_conflict) * 0.16
        )
        candidates.append(
            {
                "index": index,
                "duration_seconds": round(sample.shape[0] / sample_rate, 3),
                "level_dbfs": round(level, 2),
                "spectral_brightness_db": brightness,
                "transient_density_per_sec": transients,
                "loopability": loop,
                "boundary_click_risk": click,
                "tonal_stability_proxy": tonal,
                "motif_score": round(float(motif), 3),
                "frequency_conflict": {"beat": beat_conflict, "vocal": vocal_conflict},
                "ownership_safety_status": ownership_status,
            }
        )
    return candidates


def select_sample_roles(candidates: list[dict[str, Any]], policy_blocks_unknown: bool = False) -> dict[str, Any]:
    if policy_blocks_unknown and any(candidate.get("ownership_safety_status") == "unknown" for candidate in candidates):
        return {
            "blocked": True,
            "reason": "ownership unknown and policy blocks direct sample use",
            "selected": {},
        }
    ranked = sorted(candidates, key=lambda item: (item["motif_score"], -item["boundary_click_risk"], item["tonal_stability_proxy"]), reverse=True)
    selected: dict[str, Any] = {}
    if not ranked:
        return {"blocked": False, "selected": selected}
    selected["main_motif"] = ranked[0]
    selected["response_motif"] = next((item for item in ranked[1:] if item["index"] != selected["main_motif"]["index"]), ranked[0])
    selected["texture_chop"] = min(candidates, key=lambda item: (item["frequency_conflict"]["vocal"], -item["spectral_brightness_db"]))
    selected["transition_chop"] = max(candidates, key=lambda item: (item["transient_density_per_sec"], -item["boundary_click_risk"]))
    return {"blocked": False, "selected": selected}


def build_section_sample_plan(selection: dict[str, Any], key_confidence: float = 0.0) -> list[dict[str, Any]]:
    if selection.get("blocked"):
        return []
    selected = selection.get("selected", {})
    main = selected.get("main_motif", {}).get("index", 0)
    response = selected.get("response_motif", {}).get("index", main)
    texture = selected.get("texture_chop", {}).get("index", main)
    transition = selected.get("transition_chop", {}).get("index", response)
    key_note = "small pitch variants only; by-ear confirmation needed" if key_confidence < 0.6 else "small pitch variants stay near estimated key"
    return [
        {"section": "intro", "bars": [0, 4], "role": "filtered_motif_or_stab", "chop_index": main, "density": "low", "beat_offsets": [0.0, 2.0], "gain_db": -11.5, "pitch_semitones": 0.0, "note": key_note},
        {"section": "hook", "bars": [4, 12], "role": "main_motif_full", "chop_index": main, "density": "medium", "beat_offsets": [0.0, 2.0], "gain_db": -7.8, "pitch_semitones": 0.0, "note": "main motif defines hook identity"},
        {"section": "verse", "bars": [12, 20], "role": "texture_support", "chop_index": texture, "density": "low", "beat_offsets": [1.5], "gain_db": -14.0, "pitch_semitones": 0.0, "note": "reduced density to avoid random chop clutter"},
        {"section": "pre_hook", "bars": [20, 24], "role": "response_motif", "chop_index": response, "density": "medium_low", "beat_offsets": [1.0, 3.0], "gain_db": -10.2, "pitch_semitones": 1.0, "note": "call-response setup before hook"},
        {"section": "bridge_transition", "bars": [24, 28], "role": "transition_chop", "chop_index": transition, "density": "intentional", "beat_offsets": [0.0, 2.75], "gain_db": -9.8, "pitch_semitones": -1.0, "note": "transition hit, not random glitch"},
        {"section": "final_hook", "bars": [28, 44], "role": "main_plus_response_width", "chop_index": main, "response_chop_index": response, "density": "medium_high", "beat_offsets": [0.0, 2.0], "response_offsets": [3.0], "gain_db": -7.4, "response_gain_db": -11.2, "pitch_semitones": 0.0, "response_pitch_semitones": 1.0, "note": "main plus response, slightly wider"},
        {"section": "outro", "bars": [44, 999], "role": "clean_tail", "chop_index": texture, "density": "low", "beat_offsets": [0.0], "gain_db": -15.0, "pitch_semitones": 0.0, "note": "clean tail"},
    ]


def _place_chop(mix: np.ndarray, chop: np.ndarray, frame: int, sample_rate: int, gain_db: float, pan: float, semitones: float, high_lift: bool = False) -> None:
    if frame >= mix.shape[0]:
        return
    variant = pitch_variant(chop, semitones)
    if high_lift:
        variant = band_eq(variant, 8_500.0, 13_500.0, 1.1, sample_rate)
    stereo = pan_mono(variant, pan)
    count = min(stereo.shape[0], mix.shape[0] - frame)
    mix[frame : frame + count] += stereo[:count] * db_to_linear(gain_db)


def apply_section_sample_plan(mix: np.ndarray, samples: list[np.ndarray], section_plan: list[dict[str, Any]], sample_rate: int, bpm: float) -> list[dict[str, Any]]:
    beat_frames = int((60.0 / bpm) * sample_rate)
    placements: list[dict[str, Any]] = []
    pan_cycle = [-0.32, 0.28, -0.16, 0.34]
    for section in section_plan:
        start_bar, end_bar = section["bars"]
        step = 4 if section["density"] == "low" else 2
        if section["section"] == "final_hook":
            step = 2
        for bar in range(int(start_bar), min(int(end_bar), 96), step):
            for idx, beat_offset in enumerate(section.get("beat_offsets", [])):
                chop_index = int(section.get("chop_index", 0)) % max(1, len(samples))
                frame = int((bar * 4.0 + float(beat_offset)) * beat_frames)
                pan = pan_cycle[idx % len(pan_cycle)]
                if section["section"] == "final_hook":
                    pan *= 1.35
                _place_chop(mix, samples[chop_index], frame, sample_rate, float(section["gain_db"]), pan, float(section.get("pitch_semitones", 0.0)), section["section"] in {"intro", "final_hook"})
                phrase_role = "response" if "response" in str(section["role"]) else "call"
                placements.append({"section": section["section"], "bar": bar, "beat_offset": beat_offset, "chop_index": chop_index, "phrase_role": phrase_role, "motif_role": section["role"], "gain_db": section["gain_db"], "pan": round(pan, 3)})
            for idx, beat_offset in enumerate(section.get("response_offsets", [])):
                chop_index = int(section.get("response_chop_index", section.get("chop_index", 0))) % max(1, len(samples))
                frame = int((bar * 4.0 + float(beat_offset)) * beat_frames)
                pan = 0.42 if idx % 2 == 0 else -0.42
                _place_chop(mix, samples[chop_index], frame, sample_rate, float(section.get("response_gain_db", section["gain_db"] - 2.0)), pan, float(section.get("response_pitch_semitones", 0.0)), True)
                placements.append({"section": section["section"], "bar": bar, "beat_offset": beat_offset, "chop_index": chop_index, "phrase_role": "response", "motif_role": "response_motif", "gain_db": section.get("response_gain_db", section["gain_db"] - 2.0), "pan": pan})
    return placements


def arrange_samples_musically(
    mix: np.ndarray,
    samples: list[np.ndarray],
    sample_rate: int,
    bpm: float,
    beat_context: np.ndarray | None = None,
    vocal_context: np.ndarray | None = None,
    ownership_status: str = "unknown",
    policy_blocks_unknown: bool = False,
    key_confidence: float = 0.0,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    candidates = analyze_sample_candidates(samples, sample_rate, beat_context, vocal_context, ownership_status)
    selection = select_sample_roles(candidates, policy_blocks_unknown=policy_blocks_unknown)
    section_plan = build_section_sample_plan(selection, key_confidence=key_confidence)
    placements: list[dict[str, Any]] = []
    if samples and not selection.get("blocked"):
        placements = apply_section_sample_plan(mix, samples, section_plan, sample_rate, bpm)
    report = {
        "candidate_analysis": candidates,
        "selected_samples": selection,
        "section_sample_plan": section_plan,
        "placement_count": len(placements),
        "arrangement_rules": [
            "fewer stronger motifs over many random chops",
            "main motif defines hook",
            "response motif creates call-response",
            "texture chop supports verse/breakdown",
            "transitions are intentional",
            "small pitch variants only unless musical",
        ],
        "key_note": "key confidence low; by-ear confirmation needed" if key_confidence < 0.6 else "key confidence sufficient for small variants",
    }
    return placements, report, selection, section_plan


def add_call_response_motif(mix: np.ndarray, chops: list[np.ndarray], sample_rate: int, bpm: float) -> list[dict[str, object]]:
    placements, _report, _selection, _plan = arrange_samples_musically(mix, chops, sample_rate, bpm)
    return placements
