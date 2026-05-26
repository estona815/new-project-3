from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (
    FFMPEG,
    amp_db,
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
    convert_wav_24,
    db_amp,
    delay_samples,
    delay_throw,
    detect_phrase_endings,
    dynamic_band_tame,
    limiter,
    make_throw_gate,
    ms_width,
    normalize_to_rms,
    pan_stereo,
    peak,
    process_instrument,
    process_vocal,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    smooth_envelope,
    soft_clip,
    write_float_wav,
)


WORK = ROOT / "thin_shadow_reaper_mix"
STEMS = WORK / "stems"
INTERMEDIATE = WORK / "intermediate_v02"
RENDERS = WORK / "renders"
ANALYSIS = WORK / "analysis"
NOTES = WORK / "thin_shadow_v02_commercial_mix_notes.md"

PREMASTER_FLOAT = INTERMEDIATE / "thin_shadow_v02_commercial_premaster_float.wav"
PREMASTER_WAV = RENDERS / "thin_shadow_v02_commercial_PREMASTER_no_final_limiter_24-48.wav"
FEMALE_LAYER_WAV = RENDERS / "thin_shadow_v02_female_tone_layer_24-48.wav"
VOCAL_CLEAN_WAV = RENDERS / "thin_shadow_v02_noise_reduced_lead_vocal_24-48.wav"
LOUD_MASTER = RENDERS / "thin_shadow_v02_commercial_MASTER_loud_24-48.wav"
CLUB_MASTER = RENDERS / "thin_shadow_v02_commercial_MASTER_club_loud_24-48.wav"
CLEAN_MASTER = RENDERS / "thin_shadow_v02_commercial_MASTER_clean_24-48.wav"
LOUD_MP3 = RENDERS / "thin_shadow_v02_commercial_MASTER_loud_320k.mp3"
CLUB_MP3 = RENDERS / "thin_shadow_v02_commercial_MASTER_club_loud_320k.mp3"
CLEAN_MP3 = RENDERS / "thin_shadow_v02_commercial_MASTER_clean_320k.mp3"
BATCH_LOUD = WORK / "reaper" / "batch_master_v02_commercial_loud.txt"
BATCH_CLUB = WORK / "reaper" / "batch_master_v02_commercial_club_loud.txt"
BATCH_CLEAN = WORK / "reaper" / "batch_master_v02_commercial_clean.txt"
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")

STEM_NAMES = {
    "reference": "0 얇은 Shadow.wav",
    "lead": "11 Vocals.wav",
    "backing_a": "10 Backing_Vocals.wav",
    "backing_b": "12 Backing Vocals.wav",
    "synth": "3 Synth.wav",
    "keyboard": "6 Keyboard.wav",
    "bass": "8 Bass.wav",
    "drums": "9 Drums.wav",
}


def ensure_dirs() -> None:
    for folder in (INTERMEDIATE, RENDERS, ANALYSIS, WORK / "reaper"):
        folder.mkdir(parents=True, exist_ok=True)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32)
    if len(y) > length:
        return y[:length].astype(np.float32)
    return np.pad(y, ((0, length - len(y)), (0, 0))).astype(np.float32)


def active_fraction(y: np.ndarray, threshold: float = 1e-5) -> float:
    return float(np.mean(np.max(np.abs(y), axis=1) > threshold))


def usable(y: np.ndarray, rms_floor_db: float = -75.0) -> bool:
    return float(db_amp(rms(y))) > rms_floor_db and peak(y) > 1e-5


def load_stems() -> tuple[int, dict[str, np.ndarray], list[dict[str, object]]]:
    loaded: dict[str, np.ndarray] = {}
    rows: list[dict[str, object]] = []
    sample_rate = 48000
    for role, name in STEM_NAMES.items():
        path = STEMS / name
        sr, y, dtype = read_wav(path)
        sample_rate = sr
        loaded[role] = y
        rows.append(
            {
                "role": role,
                "file": name,
                "dtype": dtype,
                "duration_s": round(len(y) / sr, 3),
                "rms_dbfs": round(float(db_amp(rms(y))), 2),
                "peak_dbfs": round(float(db_amp(peak(y))), 2),
                "active_pct": round(active_fraction(y) * 100, 2),
                "used": role not in {"reference", "backing_a"} and usable(y),
            }
        )
    return sample_rate, loaded, rows


def spectral_denoise(y: np.ndarray, sr: int, strength: float, min_gain: float, percentile: float) -> np.ndarray:
    # Gentle spectral subtraction from quiet-bin noise estimate.
    out = np.zeros_like(y, dtype=np.float32)
    nperseg = 2048
    noverlap = 1536
    for ch in range(2):
        freqs, times, zxx = signal.stft(y[:, ch], fs=sr, nperseg=nperseg, noverlap=noverlap, boundary="zeros")
        mag = np.abs(zxx)
        phase = np.exp(1j * np.angle(zxx))
        noise = np.percentile(mag, percentile, axis=1, keepdims=True)
        gain = 1.0 - strength * (noise / (mag + 1e-9))
        gain = np.clip(gain, min_gain, 1.0)
        _, cleaned = signal.istft(mag * gain * phase, fs=sr, nperseg=nperseg, noverlap=noverlap, input_onesided=True)
        out[:, ch] = pad_or_trim(cleaned.reshape(-1, 1), len(y))[:, 0]
    return out.astype(np.float32)


def downward_expand(y: np.ndarray, sr: int, amount_db: float, percentile: float, smooth_ms: float) -> np.ndarray:
    env = smooth_envelope(np.mean(y, axis=1), sr, smooth_ms)
    active = env[env > 1e-8]
    if not len(active):
        return y.astype(np.float32)
    threshold = float(np.percentile(active, percentile))
    top = float(np.percentile(active, 96))
    norm = np.clip((env - threshold) / (top - threshold + 1e-9), 0.0, 1.0)
    reduction = amount_db * np.power(1.0 - norm, 1.7)
    gain = amp_db(-reduction).astype(np.float32)
    return (y * gain[:, None]).astype(np.float32)


def clean_lead_vocal(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = spectral_denoise(y, sr, strength=0.58, min_gain=0.32, percentile=18)
    moves.append({"stage": "spectral_denoise", "strength": 0.58, "min_gain": 0.32})
    out = downward_expand(out, sr, amount_db=13.0, percentile=19, smooth_ms=82)
    moves.append({"stage": "downward_expander", "max_reduction_db": 13.0})
    out, base_moves = process_vocal("lead_vocal", out, sr)
    moves.extend(base_moves)
    for low, high, cut, pct, smooth, name in [
        (190, 390, 1.5, 72, 150, "extra mud removal"),
        (2300, 4800, 1.8, 74, 90, "metallic AI edge control"),
        (5600, 9300, 3.0, 68, 55, "stronger de-ess"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth, slope=0.52)
        stats["stage"] = name
        moves.append(stats)
    out = biquad_peaking(out, sr, 3100, 0.9, 0.9)
    out = biquad_shelf(out, sr, 11800, 0.65, True)
    out = compressor(out, sr, threshold_db=-20.5, ratio=1.65, smooth_ms=110, makeup_db=0.25)
    out = saturate(out, drive_db=1.05, mix=0.07)
    out = normalize_to_rms(out, -16.0)
    moves.append({"stage": "commercial lead lift", "presence_db": 0.9, "air_db": 0.65, "target_rms_dbfs": -16.0})
    return out.astype(np.float32), moves


def clean_backing(y: np.ndarray, sr: int) -> np.ndarray:
    out = spectral_denoise(y, sr, strength=0.62, min_gain=0.28, percentile=20)
    out = downward_expand(out, sr, amount_db=16.0, percentile=24, smooth_ms=120)
    out, _ = process_vocal("backing_vocal", out, sr)
    out, _ = dynamic_band_tame(out, sr, 5200, 9200, 2.8, 70, 70, slope=0.5)
    return normalize_to_rms(out, -25.5).astype(np.float32)


def pitch_shift_ffmpeg(y: np.ndarray, sr: int, semitones: float, label: str) -> np.ndarray:
    src = INTERMEDIATE / f"_{label}_source.wav"
    dst = INTERMEDIATE / f"_{label}_pitch_{semitones:+.1f}.wav"
    write_float_wav(src, sr, y)
    factor = 2.0 ** (semitones / 12.0)
    tempo = 1.0 / factor
    filt = f"asetrate={sr * factor:.8f},aresample={sr},atempo={tempo:.8f}"
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", filt, "-c:a", "pcm_f32le", "-ar", str(sr), str(dst)],
        check=True,
    )
    shifted_sr, shifted, _ = read_wav(dst)
    if shifted_sr != sr:
        raise RuntimeError(f"Unexpected pitch-shift sample rate: {shifted_sr}")
    return pad_or_trim(shifted, len(y))


def make_activity_mask(source: np.ndarray, sr: int, floor_percentile: float = 34.0) -> np.ndarray:
    env = smooth_envelope(np.mean(source, axis=1), sr, 95)
    active = env[env > 1e-8]
    if not len(active):
        return np.zeros(len(source), dtype=np.float32)
    threshold = float(np.percentile(active, floor_percentile))
    top = float(np.percentile(active, 96))
    mask = np.clip((env - threshold) / (top - threshold + 1e-9), 0.0, 1.0)
    fade = max(int(sr * 0.04), 1)
    kernel = np.hanning(fade * 2 + 1).astype(np.float32)
    kernel /= float(np.sum(kernel))
    mask = np.convolve(mask, kernel, mode="same")
    return np.clip(mask, 0.0, 1.0).astype(np.float32)


def make_female_tone_layer(lead: np.ndarray, backing: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    source = normalize_to_rms(backing, -25.0) * float(amp_db(1.5)) + normalize_to_rms(lead, -24.0) * float(amp_db(-5.5))
    shifted = pitch_shift_ffmpeg(source, sr, 3.8, "female_tone")
    shifted = spectral_denoise(shifted, sr, strength=0.48, min_gain=0.35, percentile=18)
    shifted = butter_filter(shifted, sr, "highpass", 170, 3)
    shifted = butter_filter(shifted, sr, "lowpass", 12500, 3)
    shifted, _ = dynamic_band_tame(shifted, sr, 450, 900, 1.7, 72, 125, slope=0.45)
    shifted, _ = dynamic_band_tame(shifted, sr, 5400, 9200, 2.7, 70, 62, slope=0.48)
    shifted = biquad_peaking(shifted, sr, 2400, 0.55, 1.0)
    shifted = biquad_shelf(shifted, sr, 9300, 0.45, True)
    shifted = saturate(shifted, drive_db=0.7, mix=0.05)

    mask = make_activity_mask(lead + backing * 0.4, sr, 31)
    left = pan_stereo(delay_samples(shifted, int(sr * 0.012)), -0.62)
    right = pan_stereo(delay_samples(shifted, int(sr * 0.027)), 0.62)
    center_shadow = shifted * float(amp_db(-12.0))
    layer = (left + right) * float(amp_db(-3.2)) + center_shadow
    layer = layer * mask[:, None]
    layer = ms_width(layer, 1.4)
    layer = normalize_to_rms(layer, -24.2)
    moves = [
        {"stage": "female_tone_pitch_layer", "source": "backing vocal plus low lead shadow", "pitch_shift_semitones": 3.8},
        {"stage": "female_layer_width", "delays_ms": [12, 27], "pan": [-0.62, 0.62], "target_rms_dbfs": -24.2},
    ]
    return layer.astype(np.float32), moves


def commercial_music_bus(stems: dict[str, np.ndarray], sr: int, vocal_trigger: np.ndarray) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    drums, drum_moves = process_instrument("drums", stems["drums"], sr, drums=None, vocal=None)
    bass, bass_moves = process_instrument("bass", stems["bass"], sr, drums=drums, vocal=None)
    keys, key_moves = process_instrument("keys", stems["keyboard"], sr, drums=drums, vocal=vocal_trigger)
    synth, synth_moves = process_instrument("synth", stems["synth"], sr, drums=drums, vocal=vocal_trigger)
    moves.extend([{"role": "drums", "moves": drum_moves}, {"role": "bass", "moves": bass_moves}, {"role": "keys", "moves": key_moves}, {"role": "synth", "moves": synth_moves}])

    keys = spectral_denoise(keys, sr, strength=0.28, min_gain=0.55, percentile=14)
    synth = spectral_denoise(synth, sr, strength=0.32, min_gain=0.52, percentile=14)
    drums, _ = dynamic_band_tame(drums, sr, 6200, 10500, 1.2, 78, 70, slope=0.35)
    music = drums * float(amp_db(-0.6)) + bass * float(amp_db(-1.0)) + keys * float(amp_db(2.2)) + synth * float(amp_db(0.8))
    music, _ = dynamic_band_tame(music, sr, 240, 620, 1.0, 78, 180, slope=0.38)
    music, _ = dynamic_band_tame(music, sr, 1800, 4200, 1.0, 77, 120, slope=0.32)
    music = ms_width(music, 0.75)
    moves.append({"role": "music_bus", "note": "near-silent stems skipped to avoid raising noise floor"})
    return music.astype(np.float32), moves


def master_bus_polish_v02(mix: np.ndarray, sr: int) -> np.ndarray:
    out = butter_filter(mix, sr, "highpass", 22, 3)
    out, _ = dynamic_band_tame(out, sr, 210, 520, 0.9, 79, 180, slope=0.4)
    out, _ = dynamic_band_tame(out, sr, 2600, 5600, 0.75, 82, 115, slope=0.32)
    out, _ = dynamic_band_tame(out, sr, 6500, 9800, 0.8, 84, 80, slope=0.28)
    out = biquad_peaking(out, sr, 62, 0.35, 0.85)
    out = biquad_peaking(out, sr, 330, -0.25, 1.0)
    out = biquad_shelf(out, sr, 11500, 0.15, True)
    out = compressor(out, sr, threshold_db=-15.8, ratio=1.28, smooth_ms=140, makeup_db=0.25)
    out = saturate(out, drive_db=0.8, mix=0.075)
    out = soft_clip(out, drive_db=0.65, ceiling=0.88)
    return limiter(out, -3.0).astype(np.float32)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_batch(path: Path, source: Path, dest: Path, lufs: float) -> None:
    path.write_text(
        "\n".join(
            [
                f"{source}\t{dest}",
                "<CONFIG",
                "  SRATE 48000",
                "  NCH 2",
                "  DITHER 3",
                f"  NORMALIZE 3 {lufs:.1f} 0",
                "  BRICKWALL 2 -1.0",
                ">",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_reaper_batch(path: Path) -> None:
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-batchconvert", str(path)], check=True)


def markdown_table(rows: list[dict[str, object]], keys: list[str]) -> list[str]:
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join(["---"] * len(keys)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")
    return lines


def write_notes(stem_rows: list[dict[str, object]], metrics: list[dict[str, object]], moves: dict[str, object]) -> None:
    lines: list[str] = [
        "# Thin Shadow v02 Commercial Mix Notes",
        "",
        "## Summary",
        "",
        "- Goal: cleaner noise-reduced vocal, more commercial density, added female-tone vocal layer, louder master.",
        "- Method: source stems remain untouched; Python DSP cleanup/render plus REAPER batch converter loudness/brickwall pass.",
        "- Status: genre_based_draft. This is not reference matched because no lawful reference audio was analyzed.",
        "",
        "## Deliverables",
        "",
        f"- Loud master WAV: `{LOUD_MASTER.relative_to(WORK)}`",
        f"- Loud master MP3: `{LOUD_MP3.relative_to(WORK)}`",
        f"- Club loud master WAV: `{CLUB_MASTER.relative_to(WORK)}`",
        f"- Club loud master MP3: `{CLUB_MP3.relative_to(WORK)}`",
        f"- Clean master WAV: `{CLEAN_MASTER.relative_to(WORK)}`",
        f"- Clean master MP3: `{CLEAN_MP3.relative_to(WORK)}`",
        f"- Premaster: `{PREMASTER_WAV.relative_to(WORK)}`",
        f"- Female-tone layer stem: `{FEMALE_LAYER_WAV.relative_to(WORK)}`",
        f"- Noise-reduced lead vocal stem: `{VOCAL_CLEAN_WAV.relative_to(WORK)}`",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(markdown_table(metrics, ["label", "file", "integrated_lufs", "lra_lu", "true_peak_dbfs", "peak_dbfs", "rms_dbfs", "stereo_corr", "side_mid_db"]))
    lines.extend(["", "## Stem Use", ""])
    lines.extend(markdown_table(stem_rows, ["role", "file", "rms_dbfs", "peak_dbfs", "active_pct", "used"]))
    lines.extend(
        [
            "",
            "## Processing Moves",
            "",
            "- Noise removal: spectral denoise and downward expansion on lead/backing vocals; near-silent stems skipped instead of boosted.",
            "- Vocal: high-pass, mud/formant cleanup, metallic edge control, stronger de-ess, light compression, harmonic density, presence/air lift.",
            "- Female tone: generated from the provided backing vocal plus a low lead shadow, pitch shifted +3.8 semitones, widened with 12/27 ms doubles, de-essed and tucked.",
            "- Music: drums, bass, keys, and synth only; vocal presence pocket and low-mid cleanup before the master bus.",
            "- Space: short filtered reverb and phrase-delay throws ducked under the dry vocal.",
            "- Master: bus EQ/glue/saturation/soft clip, then REAPER batch converter LUFS normalize and -1.0 dB brickwall.",
            "",
            "## Revision Knobs",
            "",
            "- Female layer too much: lower the female layer by 1.5-2.5 dB.",
            "- Vocal still buried: raise lead vocal by +0.6 dB before mastering.",
            "- Master too aggressive: use the clean master or target -9.2 LUFS instead of -8.4.",
        ]
    )
    (ANALYSIS / "processing_moves_v02.json").write_text(json.dumps(moves, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    sr, stems, stem_rows = load_stems()
    length = len(stems["lead"])
    for key in list(stems):
        stems[key] = pad_or_trim(stems[key], length)

    lead, lead_moves = clean_lead_vocal(stems["lead"], sr)
    backing_source = stems["backing_b"] if usable(stems["backing_b"], -70.0) else stems["lead"] * float(amp_db(-18.0))
    backing = clean_backing(backing_source, sr)
    female_layer, female_moves = make_female_tone_layer(lead, backing, sr)
    music, music_moves = commercial_music_bus(stems, sr, lead)

    endings = detect_phrase_endings(lead, sr)
    throw_gate = make_throw_gate(length, sr, endings, pre_ms=60, post_ms=560, fade_ms=45)
    vocal_fx_source = lead + female_layer * float(amp_db(-2.0))
    reverb = reverb_send(vocal_fx_source, sr, decay_s=0.85, wet_db=-17.5, predelay_ms=28, hp_hz=240, lp_hz=8200, seed=22)
    reverb = sidechain_duck_full(reverb, lead, sr, amount_db=3.2, release_ms=190, threshold_percentile=55)
    delay = delay_throw(vocal_fx_source, sr, delay_ms=322, feedback=0.32, wet_db=-14.5, hp_hz=310, lp_hz=6100, pingpong=True)
    delay = delay * throw_gate[:, None]

    vocal_bus = lead * float(amp_db(0.8)) + backing * float(amp_db(-4.8)) + female_layer * float(amp_db(-1.6))
    vocal_bus = compressor(vocal_bus, sr, threshold_db=-15.5, ratio=1.32, smooth_ms=135, makeup_db=0.15)
    music = sidechain_duck_full(music, vocal_bus, sr, amount_db=0.85, release_ms=120, threshold_percentile=58)
    mix = music * float(amp_db(0.3)) + vocal_bus + reverb + delay
    premaster = master_bus_polish_v02(mix, sr)

    write_float_wav(PREMASTER_FLOAT, sr, premaster)
    convert_wav_24(PREMASTER_FLOAT, PREMASTER_WAV)
    write_float_wav(INTERMEDIATE / "thin_shadow_v02_female_tone_layer_float.wav", sr, female_layer)
    write_float_wav(INTERMEDIATE / "thin_shadow_v02_noise_reduced_lead_vocal_float.wav", sr, lead)
    convert_wav_24(INTERMEDIATE / "thin_shadow_v02_female_tone_layer_float.wav", FEMALE_LAYER_WAV)
    convert_wav_24(INTERMEDIATE / "thin_shadow_v02_noise_reduced_lead_vocal_float.wav", VOCAL_CLEAN_WAV)

    write_batch(BATCH_LOUD, PREMASTER_WAV, LOUD_MASTER, -8.4)
    write_batch(BATCH_CLUB, PREMASTER_WAV, CLUB_MASTER, -7.6)
    write_batch(BATCH_CLEAN, PREMASTER_WAV, CLEAN_MASTER, -11.5)
    run_reaper_batch(BATCH_LOUD)
    run_reaper_batch(BATCH_CLUB)
    run_reaper_batch(BATCH_CLEAN)
    convert_mp3(LOUD_MASTER, LOUD_MP3)
    convert_mp3(CLUB_MASTER, CLUB_MP3)
    convert_mp3(CLEAN_MASTER, CLEAN_MP3)

    metrics = [
        audio_metrics(PREMASTER_WAV, "v02_premaster"),
        audio_metrics(CLEAN_MASTER, "v02_clean_master"),
        audio_metrics(LOUD_MASTER, "v02_loud_master"),
        audio_metrics(CLUB_MASTER, "v02_club_loud_master"),
        audio_metrics(LOUD_MP3, "v02_loud_mp3"),
        audio_metrics(CLUB_MP3, "v02_club_loud_mp3"),
    ]
    write_csv(ANALYSIS / "render_audit_v02_commercial.csv", metrics)
    (ANALYSIS / "render_audit_v02_commercial.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    moves = {
        "lead_moves": lead_moves,
        "female_moves": female_moves,
        "music_moves": music_moves,
        "phrase_endings_detected": len(endings),
        "delay_throws_enabled": sum(1 for item in endings if item.get("throw")),
    }
    write_notes(stem_rows, metrics, moves)
    print(json.dumps({"club_loud_master": str(CLUB_MASTER), "club_loud_mp3": str(CLUB_MP3), "loud_master": str(LOUD_MASTER), "loud_mp3": str(LOUD_MP3), "notes": str(NOTES)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
