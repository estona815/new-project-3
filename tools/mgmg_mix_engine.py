from __future__ import annotations

import csv
import json
import math
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3/mgmg_mashup_mix")
STEMS = ROOT / "input_stems"
ANALYSIS = ROOT / "analysis"
RENDERS = ROOT / "renders"
REAPER = ROOT / "reaper"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

ROLE_MAP = {
    "0 Lead Vocals.wav": "lead_vocal",
    "1 Backing Vocals.wav": "backing_vocal",
    "2 Drums.wav": "drums",
    "3 Bass.wav": "bass",
    "4 Keyboard.wav": "keys",
    "5 Percussion.wav": "percussion",
    "6 Synth.wav": "synth",
    "7 Other.wav": "other",
}

ROLE_TARGET_RMS = {
    "lead_vocal": -17.0,
    "backing_vocal": -25.0,
    "drums": -16.2,
    "bass": -17.8,
    "keys": -24.0,
    "percussion": -22.5,
    "synth": -23.5,
    "other": -26.0,
}

ROLE_PAN = {
    "lead_vocal": 0.0,
    "backing_vocal": 0.0,
    "drums": 0.0,
    "bass": 0.0,
    "keys": -0.12,
    "percussion": 0.08,
    "synth": 0.14,
    "other": -0.08,
}

BANDS = {
    "sub_20_80": (20, 80),
    "bass_body_80_200": (80, 200),
    "mud_box_200_700": (200, 700),
    "lead_mid_700_2k": (700, 2000),
    "presence_2_6k": (2000, 6000),
    "sparkle_air_6_16k": (6000, 16000),
}


def db_amp(value: float) -> float:
    return 20.0 * math.log10(max(float(value), 1e-12))


def amp_db(db: float) -> float:
    return 10.0 ** (db / 20.0)


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        scale = max(abs(info.min), info.max)
        y = data.astype(np.float64) / scale
    else:
        y = data.astype(np.float64)
    if y.ndim == 1:
        y = np.column_stack([y, y])
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return sr, y[:, :2]


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(y * y)))


def peak(y: np.ndarray) -> float:
    return float(np.max(np.abs(y)))


def normalize_to_rms(y: np.ndarray, target_db: float) -> np.ndarray:
    current = db_amp(rms(y))
    gain = amp_db(target_db - current)
    return y * gain


def butter_filter(y: np.ndarray, sr: int, kind: str, freq: float, order: int = 3) -> np.ndarray:
    freq = min(max(freq, 5.0), sr * 0.45)
    sos = signal.butter(order, freq, btype=kind, fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y, axis=0)


def bandpass(y: np.ndarray, sr: int, low: float, high: float, order: int = 4) -> np.ndarray:
    high = min(high, sr * 0.45)
    low = max(low, 5.0)
    sos = signal.butter(order, [low, high], btype="bandpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y, axis=0)


def biquad_peaking(y: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
    a = amp_db(gain_db)
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw = math.cos(w0)
    b0 = 1 + alpha * a
    b1 = -2 * cosw
    b2 = 1 - alpha * a
    a0 = 1 + alpha / a
    a1 = -2 * cosw
    a2 = 1 - alpha / a
    b = np.array([b0, b1, b2]) / a0
    acoef = np.array([1, a1 / a0, a2 / a0])
    return signal.lfilter(b, acoef, y, axis=0)


def biquad_shelf(y: np.ndarray, sr: int, freq: float, gain_db: float, high: bool = True) -> np.ndarray:
    # RBJ shelf, S=1.
    a = amp_db(gain_db)
    w0 = 2 * math.pi * freq / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2 * math.sqrt(2)
    sqrt_a = math.sqrt(a)
    if high:
        b0 = a * ((a + 1) + (a - 1) * cosw + 2 * sqrt_a * alpha)
        b1 = -2 * a * ((a - 1) + (a + 1) * cosw)
        b2 = a * ((a + 1) + (a - 1) * cosw - 2 * sqrt_a * alpha)
        a0 = (a + 1) - (a - 1) * cosw + 2 * sqrt_a * alpha
        a1 = 2 * ((a - 1) - (a + 1) * cosw)
        a2 = (a + 1) - (a - 1) * cosw - 2 * sqrt_a * alpha
    else:
        b0 = a * ((a + 1) - (a - 1) * cosw + 2 * sqrt_a * alpha)
        b1 = 2 * a * ((a - 1) - (a + 1) * cosw)
        b2 = a * ((a + 1) - (a - 1) * cosw - 2 * sqrt_a * alpha)
        a0 = (a + 1) + (a - 1) * cosw + 2 * sqrt_a * alpha
        a1 = -2 * ((a - 1) + (a + 1) * cosw)
        a2 = (a + 1) + (a - 1) * cosw - 2 * sqrt_a * alpha
    b = np.array([b0, b1, b2]) / a0
    acoef = np.array([1, a1 / a0, a2 / a0])
    return signal.lfilter(b, acoef, y, axis=0)


def envelope_detector(x: np.ndarray, sr: int, attack_ms: float, release_ms: float) -> np.ndarray:
    x = np.maximum(np.abs(x), 1e-12)
    attack = math.exp(-1.0 / (sr * attack_ms / 1000.0))
    release = math.exp(-1.0 / (sr * release_ms / 1000.0))
    env = np.empty_like(x)
    prev = 0.0
    for i, sample in enumerate(x):
        coeff = attack if sample > prev else release
        prev = coeff * prev + (1 - coeff) * sample
        env[i] = prev
    return env


def compressor(y: np.ndarray, sr: int, threshold_db: float, ratio: float, attack_ms: float, release_ms: float, makeup_db: float = 0.0) -> np.ndarray:
    mono = np.mean(y, axis=1)
    env = envelope_detector(mono, sr, attack_ms, release_ms)
    env_db = np.array([db_amp(v) for v in env])
    over = np.maximum(env_db - threshold_db, 0.0)
    gain_reduction = over * (1.0 - 1.0 / ratio)
    gain = amp_db(makeup_db) * (10.0 ** (-gain_reduction / 20.0))
    return y * gain[:, None]


def dynamic_band_tame(y: np.ndarray, sr: int, low: float, high: float, threshold_db: float, max_cut_db: float, attack_ms: float, release_ms: float) -> np.ndarray:
    band = bandpass(y, sr, low, high, order=3)
    rest = y - band
    mono_band = np.mean(band, axis=1)
    env = envelope_detector(mono_band, sr, attack_ms, release_ms)
    env_db = np.array([db_amp(v) for v in env])
    over = np.maximum(env_db - threshold_db, 0.0)
    cut_db = np.minimum(max_cut_db, over * 0.6)
    gain = 10.0 ** (-cut_db / 20.0)
    return rest + band * gain[:, None]


def saturate(y: np.ndarray, drive_db: float, mix: float = 1.0) -> np.ndarray:
    drive = amp_db(drive_db)
    wet = np.tanh(y * drive) / max(np.tanh(drive), 1e-9)
    return wet * mix + y * (1.0 - mix)


def soft_clip(y: np.ndarray, drive_db: float = 1.5, ceiling: float = 0.98) -> np.ndarray:
    driven = y * amp_db(drive_db)
    clipped = np.tanh(driven) / np.tanh(amp_db(drive_db))
    return np.clip(clipped, -ceiling, ceiling)


def limiter(y: np.ndarray, ceiling_db: float = -0.35) -> np.ndarray:
    ceil = amp_db(ceiling_db)
    p = peak(y)
    if p <= ceil:
        return y
    return y * (ceil / p)


def oversampled_peak_db(y: np.ndarray, factor: int = 4) -> float:
    upsampled = signal.resample_poly(y, factor, 1, axis=0)
    return db_amp(peak(upsampled))


def ms_width(y: np.ndarray, side_gain_db: float) -> np.ndarray:
    mid = (y[:, 0] + y[:, 1]) / 2.0
    side = (y[:, 0] - y[:, 1]) / 2.0 * amp_db(side_gain_db)
    return np.column_stack([mid + side, mid - side])


def pan_stereo(y: np.ndarray, pan: float) -> np.ndarray:
    pan = max(-1.0, min(1.0, pan))
    left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
    right_gain = math.sin((pan + 1.0) * math.pi / 4.0)
    mono = np.mean(y, axis=1)
    return np.column_stack([mono * left_gain * math.sqrt(2), mono * right_gain * math.sqrt(2)])


def delay_send(y: np.ndarray, sr: int, delay_ms: float, feedback: float, wet_db: float, hp_hz: float = 250.0, lp_hz: float = 6500.0) -> np.ndarray:
    delay = int(sr * delay_ms / 1000.0)
    out = np.zeros_like(y)
    if delay <= 0:
        return out
    src = butter_filter(butter_filter(y, sr, "highpass", hp_hz, 2), sr, "lowpass", lp_hz, 2)
    wet = np.zeros_like(src)
    wet[delay:] += src[:-delay]
    repeats = 3
    current = wet.copy()
    for i in range(2, repeats + 1):
        shifted = np.zeros_like(src)
        d = delay * i
        if d < len(src):
            shifted[d:] = src[:-d] * (feedback ** (i - 1))
            current += shifted
    return current * amp_db(wet_db)


def reverb_send(y: np.ndarray, sr: int, decay_s: float, wet_db: float, predelay_ms: float = 18.0, hp_hz: float = 220.0, lp_hz: float = 9000.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(sr * decay_s)
    t = np.arange(n) / sr
    impulse = rng.normal(0.0, 1.0, n) * np.exp(-t / max(decay_s / 3.0, 1e-3))
    impulse[: int(sr * predelay_ms / 1000.0)] = 0.0
    impulse /= max(np.max(np.abs(impulse)), 1e-9)
    impulse *= 0.18
    src = butter_filter(butter_filter(y, sr, "highpass", hp_hz, 2), sr, "lowpass", lp_hz, 2)
    wet_l = signal.fftconvolve(src[:, 0], impulse, mode="full")[: len(src)]
    wet_r = signal.fftconvolve(src[:, 1], np.roll(impulse, int(sr * 0.011)), mode="full")[: len(src)]
    wet = np.column_stack([wet_l, wet_r])
    return wet * amp_db(wet_db)


def sidechain_duck(target: np.ndarray, trigger: np.ndarray, sr: int, amount_db: float = 2.0) -> np.ndarray:
    trig_low = bandpass(trigger, sr, 35, 120, 3)
    env = envelope_detector(np.mean(trig_low, axis=1), sr, 2.0, 95.0)
    env = env / (np.percentile(env, 98) + 1e-12)
    env = np.clip(env, 0.0, 1.0)
    gain = amp_db(-amount_db * env)
    return target * gain[:, None]


def analyze_audio(name: str, role: str, y: np.ndarray, sr: int) -> dict[str, object]:
    mono = np.mean(y, axis=1)
    freq, power = signal.welch(mono, fs=sr, nperseg=min(32768, len(mono)), noverlap=min(16384, max(0, len(mono) // 4)))
    total = 0.0
    values = {}
    for band, (low, high) in BANDS.items():
        mask = (freq >= low) & (freq < high)
        values[band] = float(np.trapezoid(power[mask], freq[mask])) if mask.any() else 0.0
        total += values[band]
    total += 1e-30
    mid = (y[:, 0] + y[:, 1]) / 2.0
    side = (y[:, 0] - y[:, 1]) / 2.0
    corr = float(np.corrcoef(y[:, 0], y[:, 1])[0, 1]) if rms(y[:, 0]) > 1e-9 and rms(y[:, 1]) > 1e-9 else 1.0
    row = {
        "file": name,
        "role": role,
        "duration_s": round(len(y) / sr, 2),
        "sample_rate": sr,
        "peak_dbfs": round(db_amp(peak(y)), 2),
        "rms_dbfs": round(db_amp(rms(y)), 2),
        "crest_db": round(db_amp(peak(y)) - db_amp(rms(y)), 2),
        "corr": round(corr, 4),
        "side_mid_db": round(db_amp(rms(side) / (rms(mid) + 1e-12)), 2),
    }
    for band, value in values.items():
        row[band + "_pct"] = round(100.0 * value / total, 3)
    return row


def process_stem(role: str, y: np.ndarray, sr: int, drums_ref: np.ndarray | None = None) -> tuple[np.ndarray, dict[str, object]]:
    notes = []
    out = y.copy()
    if role in {"lead_vocal", "backing_vocal"}:
        out = butter_filter(out, sr, "highpass", 90 if role == "lead_vocal" else 135, 3)
        out = dynamic_band_tame(out, sr, 220, 520, -25 if role == "lead_vocal" else -30, 2.5, 6, 110)
        out = dynamic_band_tame(out, sr, 5200, 9000, -31, 2.0, 2, 75)
        out = biquad_peaking(out, sr, 2600 if role == "lead_vocal" else 3200, 1.2 if role == "lead_vocal" else -0.6, 0.9)
        out = biquad_shelf(out, sr, 9500, 0.5 if role == "lead_vocal" else -0.4, high=True)
        out = compressor(out, sr, -24 if role == "lead_vocal" else -28, 3.2 if role == "lead_vocal" else 2.2, 5, 80, 1.0)
        out = compressor(out, sr, -18 if role == "lead_vocal" else -23, 1.8, 35, 240, 0.3)
        out = saturate(out, 3.0 if role == "lead_vocal" else 1.8, 0.28)
        out = ms_width(out, 0.0 if role == "lead_vocal" else 2.8)
        notes += ["HPF", "dynamic mud tame", "dynamic de-ess", "fast+LA style compression", "light saturation"]
    elif role == "drums":
        out = butter_filter(out, sr, "highpass", 25, 3)
        out = dynamic_band_tame(out, sr, 250, 520, -22, 1.8, 3, 85)
        out = biquad_peaking(out, sr, 65, 0.9, 0.9)
        out = biquad_peaking(out, sr, 3500, 0.7, 1.1)
        out = compressor(out, sr, -18, 2.2, 12, 90, 0.8)
        out = saturate(out, 2.6, 0.22)
        notes += ["kick body", "low-mid cleanup", "drum bus glue", "light clipping color"]
    elif role == "bass":
        low = butter_filter(out, sr, "lowpass", 135, 4)
        low_mono = np.mean(low, axis=1)
        high = out - low
        high = saturate(high, 5.0, 0.45)
        out = np.column_stack([low_mono, low_mono]) + high
        out = butter_filter(out, sr, "highpass", 24, 3)
        out = dynamic_band_tame(out, sr, 180, 360, -26, 1.6, 6, 140)
        if drums_ref is not None:
            out = sidechain_duck(out, drums_ref, sr, 1.7)
        out = saturate(out, 2.4, 0.2)
        notes += ["mono sub", "harmonic bass saturation", "drum-triggered duck", "low-mid control"]
    elif role in {"keys", "synth", "other"}:
        out = butter_filter(out, sr, "highpass", 95 if role != "other" else 120, 3)
        out = dynamic_band_tame(out, sr, 220, 700, -28, 2.5, 12, 180)
        out = biquad_peaking(out, sr, 2500, -0.5 if role != "synth" else 0.4, 1.0)
        out = biquad_shelf(out, sr, 9000, -0.6 if role == "other" else 0.2, True)
        out = saturate(out, 2.0, 0.18)
        out = ms_width(out, 1.5 if role == "keys" else 2.2)
        notes += ["AI low-mid cleanup", "controlled width", "soft saturation"]
    elif role == "percussion":
        out = butter_filter(out, sr, "highpass", 120, 3)
        out = dynamic_band_tame(out, sr, 6000, 11000, -32, 2.5, 1.5, 55)
        out = biquad_peaking(out, sr, 3500, 0.5, 1.2)
        out = compressor(out, sr, -24, 2.0, 3, 70, 0.2)
        out = ms_width(out, 1.4)
        notes += ["hat/percussion HPF", "dynamic harshness tame", "width"]

    out = pan_stereo(out, ROLE_PAN.get(role, 0.0)) if abs(ROLE_PAN.get(role, 0.0)) > 0.001 else out
    out = normalize_to_rms(out, ROLE_TARGET_RMS[role])
    return out, {"role": role, "target_rms_dbfs": ROLE_TARGET_RMS[role], "moves": "; ".join(notes)}


def master_process(mix: np.ndarray, sr: int) -> np.ndarray:
    out = mix.copy()
    out = butter_filter(out, sr, "highpass", 22, 3)
    out = dynamic_band_tame(out, sr, 210, 520, -18, 1.3, 15, 180)
    out = biquad_peaking(out, sr, 48, 0.45, 0.8)
    out = biquad_peaking(out, sr, 330, -0.7, 0.9)
    out = biquad_peaking(out, sr, 2900, 0.35, 0.9)
    out = biquad_shelf(out, sr, 10500, -0.25, True)
    out = compressor(out, sr, -14.5, 1.45, 28, 180, 0.6)
    out = saturate(out, 1.6, 0.18)
    out = soft_clip(out, 2.3, 0.985)
    out = limiter(out, -0.35)
    return out


def lufs_measure(path: Path) -> dict[str, float | None]:
    cmd = [FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    text = result.stderr
    summary = text[text.rfind("Summary:") :]
    values = {}
    for key, marker in {"integrated_lufs": "I:", "lra_lu": "LRA:", "true_peak_dbfs": "Peak:"}.items():
        values[key] = None
    m = re.search(r"I:\s*([-\d.]+) LUFS", summary)
    if m:
        values["integrated_lufs"] = float(m.group(1))
    m = re.search(r"LRA:\s*([-\d.]+) LU", summary)
    if m:
        values["lra_lu"] = float(m.group(1))
    m = re.search(r"Peak:\s*([-\d.]+) dBFS", summary)
    if m:
        values["true_peak_dbfs"] = float(m.group(1))
    return values


def write_temp_float(path: Path, sr: int, y: np.ndarray) -> None:
    wavfile.write(path, sr, y.astype(np.float32))


def convert_wav_24(src: Path, dst: Path) -> None:
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c:a", "pcm_s24le", "-ar", "48000", str(dst)], check=True)


def convert_mp3(src: Path, dst: Path) -> None:
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c:a", "libmp3lame", "-b:a", "320k", str(dst)], check=True)


def true_peak_safe_loudnorm(src: Path, dst: Path, target_lufs: float = -8.0, true_peak_db: float = -1.0, lra: float = 3.0) -> dict[str, float | None]:
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA={lra}:linear=false:print_format=summary",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(dst),
        ],
        check=True,
    )
    return lufs_measure(dst)


def loudness_normalize_to_target(src_float: np.ndarray, sr: int, target_lufs: float, tmp_path: Path) -> np.ndarray:
    write_temp_float(tmp_path, sr, limiter(src_float, -0.6))
    measured = lufs_measure(tmp_path).get("integrated_lufs")
    if measured is None:
        return src_float
    gain_db = target_lufs - measured
    out = src_float * amp_db(gain_db)
    out = soft_clip(out, 1.1, 0.985)
    return limiter(out, -0.35)


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    REAPER.mkdir(parents=True, exist_ok=True)

    loaded: dict[str, tuple[Path, int, np.ndarray]] = {}
    analysis_rows = []
    max_len = 0
    sr_ref = None
    for path in sorted(STEMS.glob("*.wav")):
        role = ROLE_MAP[path.name]
        sr, y = read_wav(path)
        if sr_ref is None:
            sr_ref = sr
        if sr != sr_ref:
            raise RuntimeError(f"sample-rate mismatch: {path}")
        loaded[role] = (path, sr, y)
        max_len = max(max_len, len(y))
        analysis_rows.append(analyze_audio(path.name, role, y, sr))

    if sr_ref is None:
        raise RuntimeError("No stems found")

    with (ANALYSIS / "stem_initial_metrics.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(analysis_rows[0].keys()))
        writer.writeheader()
        writer.writerows(analysis_rows)

    drums_ref = loaded["drums"][2]
    processed: dict[str, np.ndarray] = {}
    moves = []
    post_rows = []
    for role, (path, sr, y) in loaded.items():
        out, move = process_stem(role, y, sr, drums_ref=drums_ref if role == "bass" else None)
        if len(out) < max_len:
            out = np.pad(out, ((0, max_len - len(out)), (0, 0)))
        processed[role] = out
        moves.append({"file": path.name, **move})
        post_rows.append(analyze_audio(path.name, role, out, sr))

    with (ANALYSIS / "stem_processed_metrics.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(post_rows[0].keys()))
        writer.writeheader()
        writer.writerows(post_rows)

    with (ANALYSIS / "processing_moves.json").open("w", encoding="utf-8") as file:
        json.dump(moves, file, ensure_ascii=False, indent=2)

    mix = np.zeros((max_len, 2), dtype=np.float64)
    for role in ["drums", "bass", "keys", "synth", "percussion", "other", "backing_vocal", "lead_vocal"]:
        mix += processed[role]

    # Commercial-style depth: sends are built from processed tracks and returned to the mix.
    sr = sr_ref
    vox_send = processed["lead_vocal"] + processed["backing_vocal"] * amp_db(-2)
    music_send = processed["keys"] + processed["synth"] + processed["other"] * amp_db(-3)
    mix += reverb_send(vox_send, sr, 1.45, -21.5, predelay_ms=22, seed=11)
    mix += delay_send(processed["lead_vocal"], sr, 145, 0.26, -22.5, 260, 5200)
    mix += reverb_send(music_send, sr, 1.9, -27.0, predelay_ms=12, seed=21)
    mix += delay_send(processed["synth"], sr, 310, 0.22, -28.0, 400, 6200)

    pre = limiter(mix * amp_db(-4.5), -3.0)
    master = master_process(mix * amp_db(-2.3), sr)
    tmp = RENDERS / "_tmp_master_float.wav"
    master = loudness_normalize_to_target(master, sr, -7.0, tmp)
    master = limiter(master, -0.35)

    pre_tmp = RENDERS / "_tmp_pre_float.wav"
    master_tmp = RENDERS / "_tmp_master_final_float.wav"
    write_temp_float(pre_tmp, sr, pre)
    write_temp_float(master_tmp, sr, master)

    pre_wav = RENDERS / "mgmg_mashup_v01_premaster_24-48.wav"
    master_wav = RENDERS / "mgmg_mashup_v01_master_ref_estona_24-48.wav"
    master_mp3 = RENDERS / "mgmg_mashup_v01_master_ref_estona_320k.mp3"
    master_v02_wav = RENDERS / "mgmg_mashup_v02_master_tp_safe_24-48.wav"
    master_v02_mp3 = RENDERS / "mgmg_mashup_v02_master_tp_safe_320k.mp3"
    convert_wav_24(pre_tmp, pre_wav)
    convert_wav_24(master_tmp, master_wav)
    convert_mp3(master_wav, master_mp3)
    true_peak_safe_loudnorm(master_wav, master_v02_wav, target_lufs=-8.0, true_peak_db=-1.0, lra=3.0)
    convert_mp3(master_v02_wav, master_v02_mp3)
    for p in [tmp, pre_tmp, master_tmp]:
        if p.exists():
            p.unlink()

    render_metrics = []
    for label, path in [("premaster", pre_wav), ("master_v01_aggressive", master_wav), ("master_v02_tp_safe", master_v02_wav)]:
        sr2, y2 = read_wav(path)
        row = analyze_audio(path.name, label, y2, sr2)
        row.update(lufs_measure(path))
        row["oversampled_peak_dbfs_4x"] = round(oversampled_peak_db(y2), 2)
        render_metrics.append(row)
    with (ANALYSIS / "render_metrics.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(render_metrics[0].keys()))
        writer.writeheader()
        writer.writerows(render_metrics)

    write_reaper_plan(moves, analysis_rows, post_rows, render_metrics)
    print(pre_wav)
    print(master_wav)
    print(master_mp3)
    print(master_v02_wav)
    print(master_v02_mp3)
    print(ANALYSIS / "render_metrics.csv")
    print(REAPER / "mgmg_mashup_reaper_chain_plan.md")


def write_reaper_plan(moves: list[dict[str, object]], initial: list[dict[str, object]], processed: list[dict[str, object]], renders: list[dict[str, object]]) -> None:
    lines = []
    lines.append("# ㅁㄱㅁㄱ Mashup REAPER Chain Plan\n")
    lines.append("Status: measured v02 processing render. v01 is aggressive, v02 is true-peak-safe for playback/upload.\n")
    lines.append("## Installed commercial/plugin palette\n")
    lines.append("- TDR Nova: dynamic EQ for vocals, music bus, master low-mid control.\n")
    lines.append("- UADx LA-2A Tube Compressor: vocal opto leveling after fast control.\n")
    lines.append("- UADx 1176 FET Compressor or Auto-Tune Vocal Compressor: fast vocal front control.\n")
    lines.append("- TDR Kotelnikov: transparent bus/master glue.\n")
    lines.append("- Soundtoys Decapitator / IVGI2: saturation for AI smoothness reduction.\n")
    lines.append("- ValhallaVintageVerb / ValhallaSupermassive / ReaDelay: room, plate, throws, depth.\n")
    lines.append("- FreeClip: pre-limiter clipping for loudness before final limiter.\n")
    lines.append("\n## Stem moves applied in the processing render\n")
    for move in moves:
        lines.append(f"- `{move['file']}` / `{move['role']}`: target RMS {move['target_rms_dbfs']} dBFS; {move['moves']}.")
    lines.append("\n## REAPER chain translation\n")
    lines.append("### Lead Vocal")
    lines.append("1. TDR Nova: HPF 90 Hz, dynamic 220-520 Hz mud cut, dynamic 5.2-9 kHz de-ess, small 2.6-3.5 kHz front lift.")
    lines.append("2. 1176/Auto-Tune Vocal Compressor: fast 2-4 dB GR for consonant/front control.")
    lines.append("3. UADx LA-2A: 1-3 dB opto leveling for human-like sustain.")
    lines.append("4. Decapitator or IVGI2: light tone, mix below 30%.")
    lines.append("5. Sends: short plate/room, slap/tempo delay, occasional Supermassive throw.")
    lines.append("### Backing Vocal")
    lines.append("TDR Nova HPF 130-150 Hz, tuck 300-500 Hz, less 2-4 kHz than lead, LA-style leveling, wider reverb/delay.")
    lines.append("### Drums")
    lines.append("TDR Nova/stock EQ HPF 25 Hz, 250-520 Hz cleanup, 60-80 Hz punch, Kotelnikov/1176 glue, FreeClip before bus.")
    lines.append("### Bass")
    lines.append("Mono below 135 Hz, harmonic saturation above low band, TDR Nova 180-360 Hz dynamic cleanup, kick/drum-triggered duck.")
    lines.append("### Keys/Synth/Other")
    lines.append("HPF 90-130 Hz, dynamic 220-700 Hz cleanup, controlled side width, Valhalla space mostly side/behind vocals.")
    lines.append("### Premaster/Master")
    lines.append("TDR Nova broad low-mid cleanup, Kotelnikov 1-2 dB glue, FreeClip 1-3 dB, final limiter/Realimit. Keep v02 around -8 LUFS / -1 dBTP for safer upload, then push toward -6.5 LUFS only after ear QC.")
    lines.append("\n## Render metrics\n")
    for row in renders:
        lines.append(f"- `{row['role']}`: LUFS {row.get('integrated_lufs')}, TP {row.get('true_peak_dbfs')} dBFS, RMS {row.get('rms_dbfs')} dBFS, peak {row.get('peak_dbfs')} dBFS, crest {row.get('crest_db')} dB.")
    lines.append("\n## Next listening checklist\n")
    lines.append("- Lead vocal intelligibility against drums/bass.")
    lines.append("- AI smoothness: listen for plastic 2-5 kHz and static vocal sustain.")
    lines.append("- 808/kick fight around 40-80 Hz.")
    lines.append("- Hat/percussion harshness at 6-10 kHz.")
    lines.append("- Reverb/delay depth without washing lead.")
    lines.append("- Mono fold-down below 120 Hz.")
    (REAPER / "mgmg_mashup_reaper_chain_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
