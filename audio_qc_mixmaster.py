#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import struct
import wave
import zlib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parent
DEFAULT_MWOLLA_STEMS = ROOT / "audio_work" / "mwolla_v16b_source_stem_repair_reference_density_master" / "source_stems"
DEFAULT_REFERENCE_ZIP = Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48..zip")
DEFAULT_MASTER_RENDER = (
    ROOT
    / "renders"
    / "mwolla_v16b_source_stem_repair_reference_density_master"
    / "mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER.wav"
)

AUDIO_EXTS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3"}
BANDS = {
    "sub_20_60": (20.0, 60.0),
    "bass_60_120": (60.0, 120.0),
    "lowmid_120_250": (120.0, 250.0),
    "mud_250_500": (250.0, 500.0),
    "boxy_nasal_500_1200": (500.0, 1200.0),
    "presence_1200_4000": (1200.0, 4000.0),
    "presence_1500_5000": (1500.0, 5000.0),
    "harsh_4000_7000": (4000.0, 7000.0),
    "sibilance_5000_9000": (5000.0, 9000.0),
    "air_10000_16000": (10000.0, 16000.0),
}


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def list_audio_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        p
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS and not p.name.startswith("._")
    )


def choose_stem_dir(requested: Path) -> tuple[Path, str]:
    candidates = [requested, ROOT / "input" / "stems", DEFAULT_MWOLLA_STEMS]
    for candidate in candidates:
        files = [p for p in list_audio_files(candidate) if not p.name.startswith("__missing")]
        if files:
            if candidate == requested:
                return candidate, "requested"
            if candidate == ROOT / "input" / "stems":
                return candidate, "fallback_input_stems"
            return candidate, "fallback_current_v16b_source_stems"
    return requested, "blocked_no_audio_files"


def wav_bit_depth(path: Path) -> int | None:
    if path.suffix.lower() not in {".wav", ".wave"}:
        return None
    try:
        with wave.open(str(path), "rb") as handle:
            return int(handle.getsampwidth() * 8)
    except Exception:
        return None


def normalize_audio(data: np.ndarray) -> np.ndarray:
    if data.ndim == 1:
        data = data[:, None]
    if np.issubdtype(data.dtype, np.integer):
        peak = float(np.iinfo(data.dtype).max)
        y = data.astype(np.float32) / max(peak, 1.0)
    else:
        y = data.astype(np.float32)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return np.nan_to_num(y.astype(np.float32))


def read_wav_file(path: Path) -> tuple[int, np.ndarray, int | None]:
    sr, data = wavfile.read(path)
    return int(sr), normalize_audio(data), wav_bit_depth(path)


def read_wav_from_zip(zip_path: Path, member: str) -> tuple[int, np.ndarray, int | None]:
    with zipfile.ZipFile(zip_path) as archive:
        payload = archive.read(member)
    bio = io.BytesIO(payload)
    sr, data = wavfile.read(bio)
    return int(sr), normalize_audio(data), None


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y, dtype=np.float64)) + 1e-12))


def peak(y: np.ndarray) -> float:
    return float(np.max(np.abs(y))) if len(y) else 0.0


def lufs_approx(y: np.ndarray) -> float:
    # This is a deterministic fallback, not full BS.1770 gating.
    mono = np.mean(y, axis=1)
    loudness = -0.691 + 10.0 * math.log10(float(np.mean(mono * mono)) + 1e-12)
    return round(loudness, 2)


def window_loudness(y: np.ndarray, sr: int, window_s: float, hop_s: float) -> list[dict[str, float]]:
    mono = np.mean(y, axis=1)
    frame = max(1, int(round(window_s * sr)))
    hop = max(1, int(round(hop_s * sr)))
    rows: list[dict[str, float]] = []
    for start in range(0, max(0, len(mono) - frame + 1), hop):
        chunk = mono[start : start + frame]
        rows.append(
            {
                "start_s": round(start / sr, 3),
                "end_s": round((start + frame) / sr, 3),
                "lufs": round(-0.691 + 10.0 * math.log10(float(np.mean(chunk * chunk)) + 1e-12), 2),
            }
        )
    return rows


def true_peak_db(y: np.ndarray) -> float:
    try:
        up = signal.resample_poly(y, 4, 1, axis=0).astype(np.float32)
        return round(float(amp_to_db(peak(up))), 2)
    except Exception:
        return round(float(amp_to_db(peak(y))), 2)


def butter(y: np.ndarray, sr: int, kind: str, freq: float | tuple[float, float], order: int = 3) -> np.ndarray:
    if isinstance(freq, tuple):
        low = max(5.0, float(freq[0]))
        high = min(sr * 0.45, float(freq[1]))
        if high <= low:
            return np.zeros_like(y)
        sos = signal.butter(order, [low, high], btype=kind, fs=sr, output="sos")
    else:
        sos = signal.butter(order, min(max(5.0, float(freq)), sr * 0.45), btype=kind, fs=sr, output="sos")
    return signal.sosfilt(sos, y, axis=0).astype(np.float32)


def band_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    return round(float(amp_to_db(rms(butter(y, sr, "bandpass", (low, high))))), 2)


def stereo_correlation(y: np.ndarray) -> float | None:
    if y.shape[1] < 2:
        return None
    step = max(1, len(y) // 500000)
    left = y[::step, 0]
    right = y[::step, 1]
    if float(np.std(left)) < 1e-9 or float(np.std(right)) < 1e-9:
        return None
    return round(float(np.corrcoef(left, right)[0, 1]), 6)


def side_mid_ratio_db(y: np.ndarray) -> float | None:
    if y.shape[1] < 2:
        return None
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5
    return round(float(amp_to_db(rms(side)) - amp_to_db(rms(mid))), 2)


def lr_imbalance_db(y: np.ndarray) -> float:
    if y.shape[1] < 2:
        return 0.0
    return round(float(amp_to_db(rms(y[:, 0])) - amp_to_db(rms(y[:, 1]))), 2)


def silent_head_tail(y: np.ndarray, sr: int, threshold: float = 1e-4) -> tuple[float, float]:
    mono = np.max(np.abs(y), axis=1)
    active = np.where(mono > threshold)[0]
    if not len(active):
        return round(len(y) / sr, 3), round(len(y) / sr, 3)
    return round(float(active[0] / sr), 3), round(float((len(y) - active[-1] - 1) / sr), 3)


def role_from_name(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("0 ") or "full" in name or "몰라" in name:
        return "Beat 2track / Full Mix Reference"
    if "9 vocals" in name or "lead" in name or "main" in name:
        return "Lead Vocal"
    if "10 vocals" in name or "layer" in name or "double" in name:
        return "Double / Layer Vocal"
    if "backing" in name:
        return "Backing Vocal"
    if "adlib" in name:
        return "Adlib"
    if "drum" in name:
        return "Drum Bus"
    if "bass" in name or "808" in name:
        return "808 / Bass"
    if "kick" in name:
        return "Kick"
    if "snare" in name or "clap" in name:
        return "Snare / Clap"
    if "hat" in name or "perc" in name:
        return "Hat / Perc"
    if "synth" in name or "string" in name or "keyboard" in name or "guitar" in name:
        return "Melody / Instrument"
    if "fx" in name:
        return "FX"
    return "Other"


def status_rank(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(status, 0)


def add_finding(findings: list[dict[str, Any]], severity: str, item: str, problem: str, evidence: str, recommendation: str) -> None:
    findings.append(
        {
            "severity": severity,
            "item": item,
            "problem": problem,
            "evidence": evidence,
            "recommendation": recommendation,
        }
    )


@dataclass
class AnalysisResult:
    path: str
    file: str
    role: str
    duration_s: float
    sample_rate: int
    bit_depth: int | None
    channels: int
    peak_dbfs: float
    true_peak_dbtp: float
    lufs_i: float
    short_term_lufs_avg: float
    momentary_lufs_max: float
    momentary_lufs_max_start_s: float
    rms_dbfs: float
    crest_factor_db: float
    lra: float
    dc_offset: float
    clipping_samples: int
    intersample_peak_risk: bool
    silent_head_s: float
    silent_tail_s: float
    lr_imbalance_db: float
    stereo_correlation: float | None
    mono_fold_down_delta_db: float
    low_end_side_mid_db: float | None
    low_end_stereo_width_risk: bool
    phase_polarity_risk: bool
    band_db: dict[str, float]
    qc_status: str
    notes: list[str]


def analyze_array(path_label: str, file_name: str, role: str, sr: int, y: np.ndarray, bit_depth: int | None) -> AnalysisResult:
    duration = len(y) / sr
    sample_peak_db = round(float(amp_to_db(peak(y))), 2)
    tp = true_peak_db(y)
    li = lufs_approx(y)
    st = window_loudness(y, sr, 3.0, 1.0)
    mo = window_loudness(y, sr, 0.4, 0.1)
    st_values = np.array([row["lufs"] for row in st], dtype=np.float32) if st else np.array([li], dtype=np.float32)
    mo_max = max(mo, key=lambda row: row["lufs"]) if mo else {"lufs": li, "start_s": 0.0}
    r = round(float(amp_to_db(rms(y))), 2)
    crest = round(sample_peak_db - r, 2)
    lra_values = st_values[st_values > max(-70.0, li - 20.0)]
    if not len(lra_values):
        lra_values = st_values
    lra = round(float(np.percentile(lra_values, 95) - np.percentile(lra_values, 10)), 2) if len(lra_values) else 0.0
    dc = round(float(np.mean(y)), 8)
    clips = int(np.sum(np.abs(y) >= 0.999))
    head, tail = silent_head_tail(y, sr)
    corr = stereo_correlation(y)
    mono = np.mean(y, axis=1, keepdims=True)
    mono_delta = round(float(amp_to_db(rms(np.repeat(mono, 2, axis=1))) - amp_to_db(rms(y))), 2)
    low = butter(y, sr, "lowpass", 120.0, order=3)
    low_side_mid = side_mid_ratio_db(low)
    band_map = {name: band_db(y, sr, lo, hi) for name, (lo, hi) in BANDS.items()}

    notes: list[str] = []
    status = "PASS"
    if sample_peak_db >= -0.05 or clips > 0:
        status = "FAIL"
        notes.append("0 dBFS clipping or near-clipping detected.")
    elif sample_peak_db > -1.0:
        status = "WARN"
        notes.append("Peak above -1 dBFS; headroom risk.")
    if tp > -1.0:
        status = "WARN" if status != "FAIL" else status
        notes.append("True peak above -1 dBTP; inter-sample risk.")
    if li > -8.0 and crest < 8.0:
        status = "FAIL" if role in {"Beat 2track / Full Mix Reference"} else "WARN"
        notes.append("Very high loudness with low crest factor; over-compression suspected.")
    if role in {"Lead Vocal", "Double / Layer Vocal", "Backing Vocal"} and crest < 8.0:
        status = "WARN" if status != "FAIL" else status
        notes.append("Vocal crest factor is low; compression or printed dynamics may be heavy.")
    if abs(lr_imbalance_db(y)) > 1.0:
        status = "WARN" if status != "FAIL" else status
        notes.append("Sustained L/R level imbalance above 1 dB.")
    if corr is not None and corr < 0.0:
        status = "WARN" if status != "FAIL" else status
        notes.append("Average stereo correlation below 0; mono compatibility risk.")
    low_width_risk = bool(low_side_mid is not None and low_side_mid > -12.0 and role not in {"Lead Vocal", "Kick", "808 / Bass"})
    if low_width_risk:
        status = "WARN" if status != "FAIL" else status
        notes.append("120 Hz 이하 side energy가 높음; low-end mono check 권장.")
    phase_risk = bool(corr is not None and corr < 0.15)
    if not notes:
        notes.append("No critical numeric issue detected by automated QC.")

    return AnalysisResult(
        path=path_label,
        file=file_name,
        role=role,
        duration_s=round(duration, 3),
        sample_rate=sr,
        bit_depth=bit_depth,
        channels=y.shape[1],
        peak_dbfs=sample_peak_db,
        true_peak_dbtp=tp,
        lufs_i=li,
        short_term_lufs_avg=round(float(np.mean(st_values)), 2),
        momentary_lufs_max=round(float(mo_max["lufs"]), 2),
        momentary_lufs_max_start_s=round(float(mo_max["start_s"]), 3),
        rms_dbfs=r,
        crest_factor_db=crest,
        lra=lra,
        dc_offset=dc,
        clipping_samples=clips,
        intersample_peak_risk=bool(tp > -1.0 or tp - sample_peak_db > 0.5),
        silent_head_s=head,
        silent_tail_s=tail,
        lr_imbalance_db=lr_imbalance_db(y),
        stereo_correlation=corr,
        mono_fold_down_delta_db=mono_delta,
        low_end_side_mid_db=low_side_mid,
        low_end_stereo_width_risk=low_width_risk,
        phase_polarity_risk=phase_risk,
        band_db=band_map,
        qc_status=status,
        notes=notes,
    )


def analyze_file(path: Path) -> tuple[AnalysisResult, np.ndarray, int]:
    sr, y, bits = read_wav_file(path)
    result = analyze_array(rel(path), path.name, role_from_name(path), sr, y, bits)
    return result, y, sr


def collect_reference_entries(reference_dir: Path, reference_zip: Path | None) -> list[tuple[str, str, Path | None, str | None]]:
    entries: list[tuple[str, str, Path | None, str | None]] = []
    for p in list_audio_files(reference_dir):
        entries.append((p.name, rel(p), p, None))
    zpath = reference_zip if reference_zip and reference_zip.exists() else DEFAULT_REFERENCE_ZIP
    if not entries and zpath.exists():
        with zipfile.ZipFile(zpath) as archive:
            for member in archive.namelist():
                if member.startswith("__MACOSX/") or member.endswith("/"):
                    continue
                if Path(member).suffix.lower() == ".wav":
                    entries.append((Path(member).name, f"{zpath}::{member}", zpath, member))
    return entries


def mix_group(files: list[Path], role_filter: set[str], target_sr: int | None = None) -> tuple[int, np.ndarray] | None:
    loaded: list[tuple[int, np.ndarray]] = []
    max_len = 0
    sr0 = target_sr
    for p in files:
        role = role_from_name(p)
        if role not in role_filter:
            continue
        sr, y, _ = read_wav_file(p)
        if sr0 is None:
            sr0 = sr
        if sr != sr0:
            continue
        loaded.append((sr, y))
        max_len = max(max_len, len(y))
    if not loaded or sr0 is None:
        return None
    mix = np.zeros((max_len, 2), dtype=np.float32)
    for _, y in loaded:
        mix[: len(y)] += y
    p = peak(mix)
    if p > 0.99:
        mix *= 0.99 / p
    return sr0, mix.astype(np.float32)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def bus_overcompression_note(m: AnalysisResult | None) -> str:
    if m is None:
        return "No dedicated mix-bus print was found. Use a no-limiter premaster for final judgment."
    if m.lufs_i > -8.5 and m.crest_factor_db < 8.0:
        return f"WARN/FAIL risk: LUFS-I {m.lufs_i}, crest {m.crest_factor_db} dB. Printed bus compression/limiting may be too heavy."
    if m.lra < 2.0 and m.crest_factor_db < 10.0:
        return f"WARN risk: LRA {m.lra} and crest {m.crest_factor_db} dB suggest flattened movement."
    return f"PASS estimate: LUFS-I {m.lufs_i}, crest {m.crest_factor_db} dB, LRA {m.lra}; no numeric evidence of severe mix-bus overcompression."


def master_limiter_note(m: AnalysisResult | None) -> str:
    if m is None:
        return "No master render was measured in this run, so limiter/clipper overuse is unverified."
    if m.true_peak_dbtp > -0.8:
        return f"WARN: true peak {m.true_peak_dbtp} dBTP is too close to ceiling for MP3/AAC safety."
    if m.lufs_i > -8.0 and m.crest_factor_db < 7.5:
        return f"WARN/FAIL risk: LUFS-I {m.lufs_i}, crest {m.crest_factor_db} dB. Limiter/clipper may be overused."
    return f"PASS estimate: true peak {m.true_peak_dbtp} dBTP, LUFS-I {m.lufs_i}, crest {m.crest_factor_db} dB; no numeric limiter-overuse flag."


def plugin_chain_rows() -> list[list[str]]:
    return [
        [
            "FabFilter Pro-Q 3",
            "Corrective EQ and dynamic sidechain pockets",
            "Lead Vocal first EQ, Music Bus before compression, Mix Bus corrective only",
            "HPF vocal 70-100 Hz; mud 250-500 Hz -1.5 to -4 dB; vocal pocket 1.5-5 kHz",
            "Dynamic band range 1-3 dB, Q 1.2-3.0, external sidechain from lead vocal on Music Bus",
            "1-3 dB dynamic cut",
            "Too much cut makes stems thin, disconnected, or lispy",
            "Kirchhoff EQ / TDR Nova / ReaEQ",
        ],
        [
            "FabFilter Pro-C 2",
            "Transparent compression and vocal leveling",
            "Lead Vocal after cleanup EQ, optional Music Bus or Mix Bus",
            "Full-band",
            "Vocal ratio 3:1-4:1, attack 5-15 ms, release 50-120 ms; Mix Bus ratio 2:1, attack 10-30 ms, release Auto/100 ms",
            "Vocal 2-5 dB, Mix Bus 0.5-2 dB",
            "Fast attack kills consonants and drum transient; slow release pumps",
            "1176 / SSL G Bus / ReaComp",
        ],
        [
            "FabFilter Pro-MB",
            "Multiband separation for kick/808 and low-mid control",
            "Bass Bus, Drum Bus, Music Bus before glue compression",
            "40-120 Hz kick/808 overlap; 250-500 Hz mud; 1.5-5 kHz vocal pocket",
            "Ratio 1.5:1-3:1, attack 10-40 ms, release 80-200 ms, range 1-3 dB",
            "1-3 dB per active band",
            "Overuse creates phase smear, dull punch, and moving tonal balance",
            "TDR Nova / ReaXcomp / Pro-Q 3 dynamic bands",
        ],
        [
            "FabFilter Pro-L 2",
            "Final true-peak-safe limiting only after mix fixes",
            "Last slot on Master Bus after clipper if clipper is used",
            "Full-band",
            "Ceiling -1.0 dBTP, oversampling 4x-8x, Style Transparent/Modern, lookahead default",
            "Average 1-3 dB; sustained 5 dB is return-to-mix",
            "Hard push makes vocal dip, cymbal splash, and low-end pump",
            "Ozone Maximizer / Limitless / ReaLimit",
        ],
        [
            "FabFilter Pro-DS",
            "Sibilance control without dulling the whole vocal",
            "Lead Vocal after compression, before reverb sends",
            "5-9 kHz, sometimes 4.5-7 kHz for harsh AI edges",
            "Wide Band or Split Band, threshold for 2-6 dB gain reduction, range 3-6 dB",
            "2-6 dB on sibilants",
            "Too low threshold creates lisp and removes Korean consonant clarity",
            "Soothe2 / TDR Nova dynamic band / ReaXcomp",
        ],
        [
            "Oeksound Soothe2",
            "Resonance and AI metallic edge control",
            "Lead Vocal after cleanup EQ, Music Bus pre-compression for resonant synths",
            "Vocal 2.5-9 kHz; Music Bus 1.5-5 kHz and 6-10 kHz",
            "Depth 1-3, Sharpness medium, Selectivity medium, mix 30-70%",
            "1-4 dB resonance reduction",
            "Too much makes vocal watery, phasey, and less intelligible",
            "Pro-Q 3 dynamic EQ / TDR Nova / Gullfoss tame",
        ],
        [
            "Soundtheory Gullfoss",
            "Broad tonal recovery/taming after surgical fixes",
            "Music Bus or Mix Bus before limiter, not first repair tool",
            "Full-band with Recover/Tame focus; avoid heavy low-end action",
            "Recover 5-15%, Tame 5-20%, Bias near 0, Brighten below 10%",
            "Program-dependent 0.5-2 dB tonal action",
            "Can separate stems unnaturally or exaggerate top fizz",
            "Pro-Q 3 broad shelves / Ozone Stabilizer / manual EQ",
        ],
        [
            "Trackspacer",
            "Automatic vocal pocket in the beat",
            "Music Bus keyed from Lead Vocal, before Music Bus compression",
            "Filter sidechain to 1.5-5 kHz, optionally 250-500 Hz if muddy",
            "Amount 5-15%, attack 5-20 ms, release 80-180 ms, low cut 120 Hz, high cut 6-8 kHz",
            "1-3 dB effective duck",
            "Too much makes the beat breathe, vanish, or sound disconnected",
            "Pro-Q 3 dynamic sidechain / TDR Nova sidechain / Soothe2 sidechain",
        ],
        [
            "Soundtoys Decapitator",
            "Harmonic density for 808, drums, or tucked vocal excitement",
            "Parallel Bass Bus, Drum Bus, or vocal parallel aux",
            "Emphasis 100-700 Hz for bass audibility; avoid uncontrolled 5-9 kHz fizz",
            "Drive 1-3, Tone neutral/dark, Mix 5-20%, HPF/LPF around the aux if needed",
            "No GR; level-match output within 0.5 dB",
            "Too much adds harsh AI grit and masks consonants",
            "FabFilter Saturn / SDRR / Softube Saturation Knob",
        ],
        [
            "Soundtoys EchoBoy",
            "Tempo delays and hook space without drowning lead",
            "Vocal delay aux, post-fader send",
            "HPF 150-250 Hz, LPF 5-8 kHz",
            "1/8 or 1/4 dotted, feedback 8-22%, mix 100% on aux, duck return 1-4 dB from vocal",
            "Return duck 1-4 dB",
            "Unducked delay blurs lyric timing and pushes vocal behind beat",
            "ReaDelay / Valhalla Delay / H-Delay",
        ],
        [
            "Valhalla VintageVerb",
            "Vocal depth and glue",
            "Vocal reverb aux, after de-esser and delay sends",
            "HPF 180-300 Hz, LPF 6-10 kHz",
            "Plate/Room, decay 0.8-1.8 s, pre-delay 20-60 ms, mix 100% on aux, duck 1-3 dB",
            "Return duck 1-3 dB",
            "Too much reverb buries lead and worsens 1.5-5 kHz masking",
            "Pro-R / ReaVerbate / Seventh Heaven",
        ],
        [
            "SSL G Bus Compressor",
            "Mix Bus glue after balance is correct",
            "Mix Bus or Drum Bus, before limiter/clipper",
            "Full-band",
            "Ratio 2:1, attack 10-30 ms, release Auto or 100 ms, threshold for 0.5-2 dB GR",
            "0.5-2 dB",
            "More than 3 dB sustained GR narrows punch and pulls vocal down",
            "API 2500 / Pro-C 2 Bus mode / ReaComp",
        ],
        [
            "API 2500",
            "Punch glue for drums or aggressive mix bus",
            "Drum Bus or Mix Bus before final limiter",
            "Full-band",
            "Ratio 1.5:1-2:1, attack 10-30 ms, release 100-300 ms, thrust medium, old/new by taste",
            "1-3 dB drums, 0.5-2 dB mix",
            "Too much clamps transient and exaggerates low-mid density",
            "SSL G Bus / Pro-C 2 / ReaComp",
        ],
        [
            "1176",
            "Fast vocal peak catching and attitude",
            "Lead Vocal after cleanup EQ, before LA-2A",
            "Full-band, de-ess after if 5-9 kHz rises",
            "Ratio 4:1, attack 3-5, release 5-7 on classic scale",
            "3-7 dB on peaks",
            "Too fast/too much makes vocal spitty, flat, and noisy",
            "Pro-C 2 Vocal mode / CLA-76 / ReaComp",
        ],
        [
            "LA-2A",
            "Slow leveling after peak compression",
            "Lead Vocal after 1176, before de-ess or after de-ess depending sibilance",
            "Full-band",
            "Peak reduction for 1-4 dB GR, gain matched",
            "1-4 dB",
            "Too much hides transients and makes words sink",
            "CL 1B / R-Vox / Pro-C 2 Opto",
        ],
        [
            "Ozone Maximizer",
            "Alternative final limiter",
            "Last Master Bus slot",
            "Full-band",
            "IRC IV Modern/Transparent, ceiling -1.0 dBTP, Character moderate, Transient Emphasis low",
            "1-3 dB average",
            "Overuse causes pumping, smeared hats, and vocal level modulation",
            "Pro-L 2 / Limitless / ReaLimit",
        ],
        [
            "Ozone Imager",
            "Stereo width after mono-safe low-end cleanup",
            "Music Bus or Master Bus before limiter",
            "Mono below 100-140 Hz; widen only 3-10 kHz if needed",
            "Low band width 0; high band +5 to +20 max; stereoize off unless checked",
            "No GR; width delta only",
            "Wide low-end creates mono loss and phase smear",
            "bx_control / Utility / MSED",
        ],
        [
            "StandardCLIP / KClip",
            "Controlled peak shaving before limiter",
            "Drum Bus for transient control or Master Bus before limiter",
            "Full-band or high-pass sidechain if available",
            "Oversampling 4x-8x, soft/transparent mode, shave 0.5-2 dB max",
            "0.5-2 dB clipped peaks",
            "Too much adds grain, collapses punch, and creates encoded true-peak risk",
            "Kazrog KClip / Newfangled Saturate / JS soft clipper",
        ],
        [
            "Youlean Loudness Meter",
            "Integrated loudness and true peak verification",
            "Metering last on Master Bus and on reference bus",
            "N/A",
            "Measure Integrated LUFS, Short-Term LUFS, LRA, True Peak, export log if possible",
            "Meter only",
            "Wrong reset point gives false integrated LUFS",
            "iZotope Insight / dpMeter / ReaLoud",
        ],
        [
            "Voxengo SPAN",
            "Spectrum and low-mid/air comparison",
            "Metering on stems, buses, master, and reference",
            "250-500 Hz mud, 1.5-5 kHz vocal presence, 5-9 kHz harshness, 10-16 kHz air",
            "Block 4096-8192, Avg mode, slope 4.5 dB/oct, match level before comparing",
            "Meter only",
            "Unmatched levels make brighter/louder tracks look falsely better",
            "TDR Prism / FabFilter Pro-Q 3 analyzer / Ozone Tonal Balance",
        ],
        [
            "Metric AB",
            "Level-matched reference comparison",
            "Monitor/Metering chain only, never active premaster processing",
            "Full-band plus band focus",
            "Match reference within 0.2-0.5 dB perceived loudness, loop chorus and dense sections",
            "Meter only",
            "Unmatched A/B causes loudness bias and unsafe reference chasing",
            "ADPTR Streamliner / manual reference track muted from master path",
        ],
    ]


def rgb_png(path: Path, width: int, height: int, pixels: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(b"\x00" + pixels[y].astype(np.uint8).tobytes() for y in range(height))
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def simple_bar_png(path: Path, values: list[float], colors: list[tuple[int, int, int]], baseline: float | None = None) -> None:
    width, height = 960, 520
    img = np.full((height, width, 3), 250, dtype=np.uint8)
    margin = 60
    chart_w = width - margin * 2
    chart_h = height - margin * 2
    if not values:
        rgb_png(path, width, height, img)
        return
    vals = np.array(values, dtype=np.float32)
    min_v = float(min(np.min(vals), baseline if baseline is not None else np.min(vals), 0.0))
    max_v = float(max(np.max(vals), baseline if baseline is not None else np.max(vals), 1.0))
    if abs(max_v - min_v) < 1e-6:
        max_v = min_v + 1.0
    img[height - margin, margin : width - margin] = (40, 40, 40)
    img[margin : height - margin, margin] = (40, 40, 40)
    bar_w = max(2, int(chart_w / max(1, len(values)) * 0.68))
    zero_y = int(height - margin - (0.0 - min_v) / (max_v - min_v) * chart_h)
    zero_y = max(margin, min(height - margin, zero_y))
    img[zero_y : zero_y + 2, margin : width - margin] = (150, 150, 150)
    for i, value in enumerate(values):
        x0 = margin + int((i + 0.16) * chart_w / len(values))
        x1 = min(width - margin, x0 + bar_w)
        y = int(height - margin - (float(value) - min_v) / (max_v - min_v) * chart_h)
        y = max(margin, min(height - margin, y))
        c = colors[i % len(colors)]
        if y < zero_y:
            img[y:zero_y, x0:x1] = c
        else:
            img[zero_y:y, x0:x1] = c
    rgb_png(path, width, height, img)


def write_plots(plot_dir: Path, metrics: list[AnalysisResult], band_rows: list[dict[str, Any]], masking: dict[str, Any], refs: list[AnalysisResult]) -> None:
    palette = [(34, 92, 145), (217, 119, 6), (26, 127, 55), (180, 58, 58), (102, 92, 170)]
    simple_bar_png(plot_dir / "stem_loudness_comparison.png", [m.lufs_i for m in metrics], palette)
    simple_bar_png(plot_dir / "stem_peak_truepeak_comparison.png", [m.true_peak_dbtp for m in metrics], palette, baseline=-1.0)
    simple_bar_png(plot_dir / "stem_crest_factor_comparison.png", [m.crest_factor_db for m in metrics], palette)
    simple_bar_png(plot_dir / "stereo_correlation_by_stem.png", [m.stereo_correlation or 0.0 for m in metrics], palette, baseline=0.0)
    simple_bar_png(plot_dir / "low_end_energy_comparison.png", [m.band_db["sub_20_60"] for m in metrics], palette)
    simple_bar_png(plot_dir / "frequency_balance_by_stem.png", [row.get("presence_1500_5000", -120.0) for row in band_rows], palette)
    simple_bar_png(plot_dir / "vocal_vs_beat_masking.png", [masking.get("lead_presence_db", 0.0), masking.get("instrument_presence_db", 0.0)], palette)
    if refs:
        simple_bar_png(plot_dir / "reference_vs_mix_tonal_balance.png", [refs[0].band_db["bass_60_120"], metrics[0].band_db["bass_60_120"]], palette)
    else:
        simple_bar_png(plot_dir / "reference_vs_mix_tonal_balance.png", [0.0], palette)


def build_reports(
    report_dir: Path,
    deliverable_dir: Path,
    plot_dir: Path,
    project_name: str,
    genre: str,
    target: str,
    stem_source_policy: str,
    stem_dir: Path,
    metrics: list[AnalysisResult],
    references: list[AnalysisResult],
    findings: list[dict[str, Any]],
    masking: dict[str, Any],
    master_print: AnalysisResult | None,
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    deliverable_dir.mkdir(parents=True, exist_ok=True)
    (deliverable_dir / "premaster").mkdir(parents=True, exist_ok=True)
    (deliverable_dir / "master").mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    balance_rows = []
    for m in metrics:
        row = {
            "file": m.file,
            "path": m.path,
            "role": m.role,
            "duration_s": m.duration_s,
            "sample_rate": m.sample_rate,
            "bit_depth": m.bit_depth,
            "channels": m.channels,
            "peak_dbfs": m.peak_dbfs,
            "true_peak_dbtp": m.true_peak_dbtp,
            "lufs_i_approx": m.lufs_i,
            "short_term_lufs_avg_approx": m.short_term_lufs_avg,
            "momentary_lufs_max_approx": m.momentary_lufs_max,
            "momentary_lufs_max_start_s": m.momentary_lufs_max_start_s,
            "rms_dbfs": m.rms_dbfs,
            "crest_factor_db": m.crest_factor_db,
            "lra_approx": m.lra,
            "dc_offset": m.dc_offset,
            "clipping_samples": m.clipping_samples,
            "intersample_peak_risk": m.intersample_peak_risk,
            "silent_head_s": m.silent_head_s,
            "silent_tail_s": m.silent_tail_s,
            "lr_imbalance_db": m.lr_imbalance_db,
            "stereo_correlation": m.stereo_correlation,
            "mono_fold_down_delta_db": m.mono_fold_down_delta_db,
            "low_end_side_mid_db": m.low_end_side_mid_db,
            "low_end_stereo_width_risk": m.low_end_stereo_width_risk,
            "phase_polarity_risk": m.phase_polarity_risk,
            "qc_status": m.qc_status,
            "notes": " ".join(m.notes),
        }
        row.update(m.band_db)
        metric_rows.append(row)
        balance = {"file": m.file, "role": m.role, "lufs_i_approx": m.lufs_i, "rms_dbfs": m.rms_dbfs, "qc_status": m.qc_status}
        balance.update(m.band_db)
        balance_rows.append(balance)

    write_json(
        report_dir / "stem_metrics.json",
        {
            "schema": "audio-qc-mixmaster-v1",
            "project_name": project_name,
            "genre": genre,
            "target": target,
            "stem_dir": rel(stem_dir),
            "stem_source_policy": stem_source_policy,
            "lufs_note": "LUFS values are deterministic approximations because pyloudnorm is not available in the active Python environment.",
            "metrics": [m.__dict__ for m in metrics],
            "references": [r.__dict__ for r in references],
            "master_print": master_print.__dict__ if master_print else None,
            "masking": masking,
            "findings": findings,
        },
    )
    write_csv(report_dir / "stem_metrics.csv", metric_rows)
    write_csv(report_dir / "stem_balance_table.csv", balance_rows)
    write_csv(report_dir / "qc_findings.csv", findings)

    top = sorted(findings, key=lambda x: status_rank(x["severity"]), reverse=True)[:5]
    stem_rows = [
        [
            m.file,
            m.role,
            m.peak_dbfs,
            m.true_peak_dbtp,
            m.lufs_i,
            m.rms_dbfs,
            m.crest_factor_db,
            m.lra,
            m.stereo_correlation,
            m.clipping_samples,
            m.dc_offset,
            m.phase_polarity_risk,
            m.qc_status,
            "<br>".join(m.notes[:2]),
        ]
        for m in metrics
    ]
    fail_rows = [f for f in findings if f["severity"] == "FAIL"]
    warn_rows = [f for f in findings if f["severity"] == "WARN"]
    full_mix_metric = next((m for m in metrics if m.role == "Beat 2track / Full Mix Reference"), None)

    qc_md = [
        "# QC REPORT",
        "",
        "## 1. Executive Summary",
        f"- Project: `{project_name}`",
        f"- Genre/target: `{genre}` / `{target}`",
        f"- Stem source: `{rel(stem_dir)}` (`{stem_source_policy}`)",
        "- Listening note: no listening claims are made. Subjective mix judgments below are marked as measurement-derived estimates.",
        "- Measurement note: LUFS/LRA are deterministic approximations because pyloudnorm/BS.1770 gating is not installed in this environment.",
        "- Most important measured issue: vocal clarity is likely limited by instrument/melody energy in the 1.5-5 kHz presence range and by residual low-mid buildup.",
        "- Mastering blocker: do not try to solve vocal masking, low-mid buildup, or printed stem compression with harder limiting.",
        "- Priority: vocal pocket and gain staging first, then kick/808 separation, then stereo/space, then loudness.",
        "",
        "## 2. Stem Inventory",
        md_table(["File", "Role", "Peak", "True Peak", "LUFS-I", "RMS", "Crest", "LRA", "Stereo Corr", "Clipping", "DC Offset", "Phase Risk", "QC", "Notes"], stem_rows),
        "",
        "## 3. Critical Failures",
    ]
    if fail_rows:
        qc_md += [f"- `{f['item']}`: {f['problem']} Evidence: {f['evidence']} Fix: {f['recommendation']}" for f in fail_rows]
    else:
        qc_md.append("- No automated FAIL items. Remaining issues are WARN-level or mix-balance estimates.")
    qc_md += ["", "## 4. Warnings"]
    qc_md += [f"- `{f['item']}`: {f['problem']} Evidence: {f['evidence']} Fix: {f['recommendation']}" for f in warn_rows] or ["- No WARN items."]
    qc_md += [
        "",
        "## 5. Vocal Clarity Diagnosis",
        f"- Lead presence 1.5-5 kHz: `{masking.get('lead_presence_db')}` dBFS approx; instrument presence 1.5-5 kHz: `{masking.get('instrument_presence_db')}` dBFS approx; vocal-over-instrument: `{masking.get('vocal_over_instrument_presence_db')}` dB.",
        f"- Vocal level vs instrument bus: `{masking.get('vocal_over_instrument_lufs_db')}` dB approx.",
        "- Estimate: if vocal-over-instrument presence is below +3 dB, raise vocal clarity by carving the instrument bus first, not by pushing the vocal fader alone.",
        "- Automation need: phrase-level clip gain and volume automation should be done before compression.",
        "",
        "## 6. Frequency Masking Bands",
        md_table(
            ["Band", "Lead Vocal", "Instrument Bus", "Diagnosis", "DAW Action"],
            [
                ["250-500 Hz mud", masking.get("lead_mud_250_500_db"), masking.get("instrument_mud_250_500_db"), masking.get("mud_diagnosis"), "Pro-Q 3 or Pro-MB, -1.5 to -4 dB on offending stem/bus"],
                ["1.5-5 kHz vocal presence", masking.get("lead_presence_db"), masking.get("instrument_presence_db"), masking.get("presence_diagnosis"), "Trackspacer or Pro-Q 3 sidechain, 1-3 dB duck on Music Bus"],
                ["5-9 kHz sibilance/harshness", masking.get("lead_sibilance_5000_9000_db"), masking.get("instrument_sibilance_5000_9000_db"), masking.get("sibilance_diagnosis"), "Pro-DS/Soothe2, 2-6 dB on sibilants or harsh resonances"],
                ["10-16 kHz air", masking.get("lead_air_10000_16000_db"), masking.get("instrument_air_10000_16000_db"), masking.get("air_diagnosis"), "Only after de-harshing: high shelf +0.5 to +2 dB or Gullfoss Recover 5-10%"],
            ],
        ),
        "",
        "## 7. Beat / Instrument Diagnosis",
        "- The instrument bus should receive lead-vocal sidechain dynamic EQ in 1.5-5 kHz, 1-3 dB reduction, attack 5-30 ms, release 80-250 ms.",
        "- 808/Bass and Drum Bus should be checked in 40-120 Hz. If their band levels are within ~3 dB, use kick/808 dynamic EQ or sidechain separation.",
        "- Melody/Synth/Guitar/Keyboard should be cleaned in 250-500 Hz before adding top-end or master brightness.",
        "",
        "## 8. Mix Bus Diagnosis",
        f"- Full-mix/2track print check: {bus_overcompression_note(full_mix_metric)}",
        "- Mix bus should be printed without limiter/maximizer/hard clipper for premaster review.",
        "- Keep mix-bus compression gain reduction around 0.5-2 dB. Sustained 3 dB+ GR means the stem balance needs revision.",
        "- Master bus processing cannot reliably repair buried vocal or low-end masking.",
        "",
        "## 9. Master Bus Limiter / Clipper Diagnosis",
        f"- Master print check: {master_limiter_note(master_print)}",
        "- If final limiter or clipper exceeds 3 dB average gain reduction, return to mix balance instead of raising loudness.",
        "- Master limiter must not be used to solve vocal audibility, kick/808 collision, or 250-500 Hz buildup.",
        "",
        "## 10. Stereo / Phase Diagnosis",
        "- Keep 120 Hz 이하 mono or near-mono except intentional stereo FX.",
        "- Any stem with stereo correlation below 0 or mono fold-down loss below -3 dB requires mono compatibility review.",
        "- L/R imbalance above 1 dB should be corrected before bus compression.",
        "",
        "## 11. Corrective Action Plan",
        md_table(
            ["Problem", "Cause", "Fix", "Plugin", "Setting", "Priority"],
            [
                ["Vocal buried estimate", "Instrument bus presence overlap", "Sidechain dynamic EQ pocket", "Trackspacer / Pro-Q 3 / TDR Nova", "1.5-5 kHz, 1-3 dB duck, 80-180 ms release", "P1"],
                ["Low-mid buildup", "Bass/melody mud overlap", "Stem EQ before bus", "Pro-Q 3 / Kirchhoff / ReaEQ", "250-500 Hz, -1.5 to -4 dB where measured", "P1"],
                ["Kick/808 masking", "40-120 Hz overlap", "Dynamic EQ or sidechain", "Pro-MB / TDR Nova / ReaComp sidechain", "1-3 dB duck on overlap band", "P1"],
                ["Over-compression risk", "Printed loud stems or bus limiting", "Remove limiter from premaster", "Meter only", "Premaster peak around -6 dBFS", "P1"],
                ["Stereo phase risk", "Wide low-end/FX sides", "Mono low band, narrow unsafe sides", "bx_control / Ozone Imager / Utility", "Mono below 100-140 Hz", "P2"],
            ],
        ),
        "",
        "## 12. Mastering vs Mix-Only Separation",
        md_table(
            ["Issue", "Resolve In Mix", "Resolve In Master"],
            [
                ["Vocal buried by beat", "Yes: clip gain, vocal level, Music Bus sidechain 1.5-5 kHz", "No: limiter will make masking pump"],
                ["Kick/808 collision", "Yes: 40-120 Hz dynamic EQ or sidechain before premaster", "Only tiny broad low shelf after collision is fixed"],
                ["250-500 Hz muddy buildup", "Yes: remove from offending stems/buses", "Small -0.5 to -1 dB broad cut only if mix is already balanced"],
                ["5-9 kHz harshness/sibilance", "Mostly mix: de-ess vocal and tame synth resonance", "Light dynamic EQ 0.5-1.5 dB if global"],
                ["10-16 kHz air 부족", "Partly mix: restore vocal/instrument air after de-harshing", "Yes: +0.5 to +2 dB shelf if no sibilance risk"],
                ["Overall loudness", "Premaster must have headroom and no clipping", "Yes: final limiter/clipper 1-3 dB GR max"],
            ],
        ),
        "",
        "## 13. Final Recommendation",
        "- First fix gain staging, vocal pocket, low-end separation, and low-mid buildup in the mix.",
        "- Do not push the limiter harder to create clarity.",
        "- Premaster handoff target: peak near -6 dBFS, true peak -6 to -3 dBTP, no limiter, 24-bit or 32-float WAV.",
        "- Mastering can proceed only after vocal-over-instrument masking and low-end overlap are reduced at stem/bus level.",
    ]
    (report_dir / "QC_REPORT.md").write_text("\n".join(qc_md) + "\n", encoding="utf-8")

    masking_md = [
        "# Masking Report",
        "",
        f"- Lead vocal file: `{masking.get('lead_file', 'not_found')}`",
        f"- Instrument bus presence 1.5-5 kHz: `{masking.get('instrument_presence_db')}` dBFS approx",
        f"- Lead presence 1.5-5 kHz: `{masking.get('lead_presence_db')}` dBFS approx",
        f"- Vocal-over-instrument presence: `{masking.get('vocal_over_instrument_presence_db')}` dB",
        f"- Bass vs drums 40-120 Hz delta: `{masking.get('bass_drums_low_delta_db')}` dB",
        "",
        "## Band Decisions",
        md_table(
            ["Band", "Measured Evidence", "QC Decision", "Fix"],
            [
                ["250-500 Hz muddy", f"Lead {masking.get('lead_mud_250_500_db')} dBFS, Instrument {masking.get('instrument_mud_250_500_db')} dBFS", masking.get("mud_diagnosis"), "Cut the source bus first: Pro-Q 3 or Pro-MB -1.5 to -4 dB, Q 1.0-2.5"],
                ["1.5-5 kHz vocal presence masking", f"Lead {masking.get('lead_presence_db')} dBFS, Instrument {masking.get('instrument_presence_db')} dBFS, delta {masking.get('vocal_over_instrument_presence_db')} dB", masking.get("presence_diagnosis"), "Trackspacer/Pro-Q 3 sidechain on Music Bus, 1-3 dB range, release 80-180 ms"],
                ["5-9 kHz sibilance/harshness", f"Lead {masking.get('lead_sibilance_5000_9000_db')} dBFS, Instrument {masking.get('instrument_sibilance_5000_9000_db')} dBFS", masking.get("sibilance_diagnosis"), "Pro-DS/Soothe2 range 2-6 dB only on active sibilants/resonances"],
                ["10-16 kHz air", f"Lead {masking.get('lead_air_10000_16000_db')} dBFS, Instrument {masking.get('instrument_air_10000_16000_db')} dBFS", masking.get("air_diagnosis"), "After de-harshing, add +0.5 to +2 dB high shelf or Gullfoss Recover 5-10%"],
            ],
        ),
        "",
        "Primary recommendation: use lead-vocal sidechain dynamic EQ on Melody/Instrument Bus before increasing vocal level. Start with 1.5-5 kHz, 1-3 dB maximum reduction.",
    ]
    (report_dir / "masking_report.md").write_text("\n".join(masking_md) + "\n", encoding="utf-8")

    phase_rows = [[m.file, m.role, m.stereo_correlation, m.lr_imbalance_db, m.mono_fold_down_delta_db, m.low_end_side_mid_db, m.low_end_stereo_width_risk, m.phase_polarity_risk] for m in metrics]
    (report_dir / "phase_stereo_report.md").write_text(
        "# Phase / Stereo Report\n\n"
        + md_table(["File", "Role", "Corr", "L/R dB", "Mono Delta", "Low Side/Mid", "Low Width Risk", "Phase Risk"], phase_rows)
        + "\n\nRule: correlation below 0 or low-end side/mid above -12 dB should be checked in mono before mastering.\n",
        encoding="utf-8",
    )

    plugin_md = [
        "# Plugin Chain Recommendation",
        "",
        "This table is an operational DAW work order. Apply after clip gain, routing, and phase checks. All moves must be gain-matched for A/B.",
        "",
        md_table(
            ["Plugin", "Purpose", "Insert Position", "Frequency", "Threshold/Range/Ratio/Attack/Release", "Expected GR", "Misuse Side Effect", "Alternative"],
            plugin_chain_rows(),
        ),
    ]
    (report_dir / "plugin_chain_recommendation.md").write_text("\n".join(plugin_md) + "\n", encoding="utf-8")

    (report_dir / "revision_mix_notes.md").write_text(
        "# Revision Mix Notes\n\n"
        "## Priority Order\n\n"
        "1. Gain-stage stems so pre-insert peaks sit around -12 to -6 dBFS. Do not normalize everything to the same LUFS.\n"
        "2. Lead Vocal clip gain first: quiet words +1 to +3 dB, loud words -1 to -4 dB. Then use 1176 3-7 dB peak GR into LA-2A 1-4 dB leveling.\n"
        "3. Music Bus vocal pocket: Trackspacer or Pro-Q 3 external sidechain from Lead Vocal, 1.5-5 kHz, max 1-3 dB duck, attack 5-20 ms, release 80-180 ms.\n"
        "4. Mud cleanup: Pro-Q 3/Pro-MB on Melody/Synth/Guitar/Keyboard around 250-500 Hz, -1.5 to -4 dB only where the stem contributes measurable buildup.\n"
        "5. Kick/808 separation: Pro-MB or dynamic EQ in 40-120 Hz. Keep ducking 1-3 dB; if more is needed, rebalance source levels.\n"
        "6. Sibilance/harshness: Pro-DS/Soothe2 on Lead Vocal 5-9 kHz, 2-6 dB active reduction. Do not brighten air before this pass.\n"
        "7. Air recovery: after harshness passes, add +0.5 to +2 dB high shelf at 10-16 kHz or Gullfoss Recover 5-10%, level-matched.\n"
        "8. Stereo safety: mono or narrow below 100-140 Hz on non-bass/non-kick stereo stems, especially FX and melodic support.\n"
        "9. Print a no-limiter premaster at peak around -6 to -3 dBFS before loud master processing.\n",
        encoding="utf-8",
    )

    (report_dir / "mastering_plan.md").write_text(
        "# Mastering Plan\n\n"
        "Mastering starts only after mix-stage masking is reduced. The master chain must preserve vocal intelligibility and low-end separation instead of forcing them with loudness.\n\n"
        "## Master Chain Order\n\n"
        "1. Metering/reference: Youlean Loudness Meter, Voxengo SPAN, Metric AB. Level-match references within 0.2-0.5 dB.\n"
        "2. Corrective EQ: Pro-Q 3 broad moves only, 250-500 Hz -0.5 to -1.0 dB if global mud remains; 5-9 kHz -0.5 to -1.5 dB dynamic only if harshness is global.\n"
        "3. Glue compression: SSL G Bus or API 2500, ratio 2:1, attack 10-30 ms, release Auto/100 ms, target 0.5-1.5 dB GR, hard ceiling 2 dB GR.\n"
        "4. Dynamic tone: Pro-MB or Soothe2, max 0.5-1.5 dB in problem bands. Do not replace stem repair.\n"
        "5. Stereo: Ozone Imager only above 3 kHz if needed; keep below 100-140 Hz mono.\n"
        "6. Clipper: StandardCLIP/KClip 4x-8x oversampling, 0.5-2 dB peak shave max.\n"
        "7. Limiter: Pro-L 2 or Ozone Maximizer, ceiling -1.0 dBTP, average 1-3 dB GR. Sustained 5 dB+ means return to mix.\n\n"
        "## Targets\n\n"
        "- Streaming target: -14 to -11 LUFS-I, true peak ceiling -1.0 dBTP.\n"
        "- Modern hip-hop/pop loud target: -10 to -8 LUFS-I only if pumping, vocal ducking, and harshness remain controlled.\n"
        "- Premaster handoff: no limiter, peak -6 to -3 dBFS, 24-bit or 32-float WAV.\n\n"
        "## Mix-Only Problems\n\n"
        "- Buried vocal caused by 1.5-5 kHz Music Bus masking.\n"
        "- Kick/808 collision in 40-120 Hz.\n"
        "- Stem-specific 250-500 Hz mud or stereo low-end phase risk.\n\n"
        "## Mastering-Appropriate Problems\n\n"
        "- Small full-mix tonal tilt below 1 dB.\n"
        "- Final loudness and true-peak ceiling.\n"
        "- Very light high-band width or air recovery after sibilance is controlled.\n",
        encoding="utf-8",
    )

    (report_dir / "final_delivery_checklist.md").write_text(
        "# Final Delivery Checklist\n\n"
        "- [ ] Premaster no limiter 24-bit WAV exists.\n"
        "- [ ] Premaster no limiter 32-float WAV exists.\n"
        "- [ ] Instrumental and acapella bounces exist.\n"
        "- [ ] Master WAV/MP3 exports exist.\n"
        "- [ ] True peak checked after WAV and MP3 encoding.\n"
        "- [ ] Vocal masking checked against Instrument Bus 1.5-5 kHz.\n"
        "- [ ] 250-500 Hz mud checked on Melody/Synth/Guitar/Keyboard and Music Bus.\n"
        "- [ ] 5-9 kHz sibilance/harshness checked before adding 10-16 kHz air.\n"
        "- [ ] Kick/808 40-120 Hz overlap checked and ducking kept within 1-3 dB.\n"
        "- [ ] 120 Hz 이하 mono compatibility checked.\n"
        "- [ ] Mix Bus compression average GR is 0.5-2 dB, not sustained above 3 dB.\n"
        "- [ ] Final limiter/clipper combined gain reduction is normally 1-3 dB, not sustained above 5 dB.\n"
        "- [ ] No final claim of reference match without user listening approval.\n",
        encoding="utf-8",
    )

    (deliverable_dir / "DELIVERABLE_STATUS.md").write_text(
        "# Deliverable Status\n\n"
        "This run generated QC reports and a revision plan only. New premaster/master audio deliverables were not rendered because the request is an analysis and work-order pass, not an approved new mix print. Use the checklist in `reports/final_delivery_checklist.md` for the next render pass.\n",
        encoding="utf-8",
    )

    write_plots(plot_dir, metrics, balance_rows, masking, references)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stem-dir", default="stems")
    parser.add_argument("--reference-dir", default="references")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--project-name", default="Mwolla")
    parser.add_argument("--genre", default="Hip-hop / Digicore / Hyperpop")
    parser.add_argument("--target", default="streaming / youtube / shorts")
    parser.add_argument("--reference-zip", default="")
    parser.add_argument("--master-render", default=str(DEFAULT_MASTER_RENDER))
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    report_dir = output_dir / "reports"
    plot_dir = report_dir / "plots"
    deliverable_dir = output_dir / "deliverables"
    stem_dir, stem_policy = choose_stem_dir((ROOT / args.stem_dir).resolve() if not Path(args.stem_dir).is_absolute() else Path(args.stem_dir))
    stem_files = [p for p in list_audio_files(stem_dir) if not p.name.startswith("__missing")]
    if not stem_files:
        raise SystemExit(f"No audio stems found in {stem_dir}")

    metrics: list[AnalysisResult] = []
    findings: list[dict[str, Any]] = []
    for path in stem_files:
        if path.suffix.lower() != ".wav":
            continue
        m, _, _ = analyze_file(path)
        metrics.append(m)
        for note in m.notes:
            if m.qc_status != "PASS":
                add_finding(findings, m.qc_status, m.file, note, f"peak={m.peak_dbfs} dBFS, TP={m.true_peak_dbtp} dBTP, crest={m.crest_factor_db} dB", "Revise gain staging or stem processing before mastering.")

    reference_zip = Path(args.reference_zip).expanduser() if args.reference_zip else None
    reference_entries = collect_reference_entries(Path(args.reference_dir), reference_zip)
    references: list[AnalysisResult] = []
    for name, label, path, member in reference_entries:
        try:
            if path is not None and member:
                sr, y, bits = read_wav_from_zip(path, member)
            elif path is not None:
                sr, y, bits = read_wav_file(path)
            else:
                continue
            references.append(analyze_array(label, name, "Reference Master", sr, y, bits))
        except Exception as exc:
            add_finding(findings, "WARN", name, "Reference file analysis failed", str(exc), "Verify reference audio path or archive integrity.")

    master_print: AnalysisResult | None = None
    master_render_path = Path(args.master_render).expanduser() if args.master_render else Path("")
    if args.master_render and master_render_path.exists() and master_render_path.suffix.lower() == ".wav":
        try:
            sr, y, bits = read_wav_file(master_render_path)
            master_print = analyze_array(rel(master_render_path), master_render_path.name, "Master Print", sr, y, bits)
            if master_print.true_peak_dbtp > -0.8:
                add_finding(
                    findings,
                    "WARN",
                    "Master Print",
                    "Master true peak is too close to delivery ceiling",
                    f"TP={master_print.true_peak_dbtp} dBTP, LUFS-I={master_print.lufs_i}, crest={master_print.crest_factor_db} dB",
                    "Set final limiter ceiling to -1.0 dBTP and re-check encoded MP3/AAC true peak.",
                )
            if master_print.lufs_i > -8.0 and master_print.crest_factor_db < 7.5:
                add_finding(
                    findings,
                    "WARN",
                    "Master Print",
                    "Limiter/clipper overuse risk",
                    f"LUFS-I={master_print.lufs_i}, crest={master_print.crest_factor_db} dB",
                    "Reduce final limiter/clipper GR and repair mix balance upstream.",
                )
        except Exception as exc:
            add_finding(findings, "WARN", "Master Print", "Master render analysis failed", str(exc), "Verify --master-render path.")

    lead = next((p for p in stem_files if role_from_name(p) == "Lead Vocal"), None)
    instrument_roles = {"Melody / Instrument", "FX", "Drum Bus", "808 / Bass", "Kick", "Snare / Clap", "Hat / Perc"}
    masking: dict[str, Any] = {"lead_file": lead.name if lead else "not_found"}
    if lead:
        lead_sr, lead_y, _ = read_wav_file(lead)
        inst_group = mix_group(stem_files, instrument_roles, lead_sr)
        bass_group = mix_group(stem_files, {"808 / Bass"}, lead_sr)
        drums_group = mix_group(stem_files, {"Drum Bus", "Kick"}, lead_sr)
        if inst_group:
            _, inst_y = inst_group
            n = min(len(lead_y), len(inst_y))
            lead_y = lead_y[:n]
            inst_y = inst_y[:n]
            lead_mud = band_db(lead_y, lead_sr, 250, 500)
            inst_mud = band_db(inst_y, lead_sr, 250, 500)
            lead_presence = band_db(lead_y, lead_sr, 1500, 5000)
            inst_presence = band_db(inst_y, lead_sr, 1500, 5000)
            lead_sibilance = band_db(lead_y, lead_sr, 5000, 9000)
            inst_sibilance = band_db(inst_y, lead_sr, 5000, 9000)
            lead_air = band_db(lead_y, lead_sr, 10000, 16000)
            inst_air = band_db(inst_y, lead_sr, 10000, 16000)
            presence_delta = round(lead_presence - inst_presence, 2)
            mud_diagnosis = "PASS: no strong 250-500 Hz bus buildup flag from this comparison."
            if inst_mud - inst_presence > 4.0:
                mud_diagnosis = "WARN: 250-500 Hz instrument energy is elevated versus presence; beat can read muddy/boxy."
            presence_diagnosis = "PASS: vocal has at least +3 dB presence lead over instrument bus."
            if presence_delta < 3.0:
                presence_diagnosis = "WARN: vocal presence margin is below +3 dB; vocal can sit behind the beat."
            sibilance_diagnosis = "PASS: 5-9 kHz does not exceed the local presence-risk threshold."
            if lead_sibilance - lead_presence > -2.0:
                sibilance_diagnosis = "WARN: vocal 5-9 kHz is close to presence band; de-ess/anti-harsh pass required before air boost."
            elif inst_sibilance - inst_presence > -1.0:
                sibilance_diagnosis = "WARN: instrument 5-9 kHz is hot relative to presence; synth/hat harshness may mask consonants."
            air_diagnosis = "PASS: no numeric air-deficit flag."
            if lead_air - lead_presence < -16.0:
                air_diagnosis = "WARN: lead 10-16 kHz is low relative to presence; air recovery may help after de-essing."
            masking.update(
                {
                    "lead_mud_250_500_db": lead_mud,
                    "instrument_mud_250_500_db": inst_mud,
                    "lead_presence_db": lead_presence,
                    "instrument_presence_db": inst_presence,
                    "vocal_over_instrument_presence_db": presence_delta,
                    "lead_sibilance_5000_9000_db": lead_sibilance,
                    "instrument_sibilance_5000_9000_db": inst_sibilance,
                    "lead_air_10000_16000_db": lead_air,
                    "instrument_air_10000_16000_db": inst_air,
                    "lead_lufs_approx": lufs_approx(lead_y),
                    "instrument_lufs_approx": lufs_approx(inst_y),
                    "vocal_over_instrument_lufs_db": round(lufs_approx(lead_y) - lufs_approx(inst_y), 2),
                    "mud_diagnosis": mud_diagnosis,
                    "presence_diagnosis": presence_diagnosis,
                    "sibilance_diagnosis": sibilance_diagnosis,
                    "air_diagnosis": air_diagnosis,
                }
            )
            if inst_mud - inst_presence > 4.0:
                add_finding(
                    findings,
                    "WARN",
                    "Instrument Bus 250-500 Hz",
                    "Beat/instrument bus muddy buildup risk",
                    f"Instrument 250-500 Hz={inst_mud} dBFS, 1.5-5 kHz={inst_presence} dBFS",
                    "Cut 250-500 Hz on offending melody/synth/guitar/keyboard stems by -1.5 to -4 dB before master processing.",
                )
            if presence_delta < 3.0:
                add_finding(
                    findings,
                    "WARN",
                    "Lead Vocal vs Instrument Bus",
                    "Lead vocal presence is likely masked by the instrument bus",
                    f"Lead 1.5-5 kHz={lead_presence} dBFS, Instrument 1.5-5 kHz={inst_presence} dBFS, delta={presence_delta} dB",
                    "Apply vocal-sidechain dynamic EQ on Instrument Bus around 1.5-5 kHz, 1-3 dB max reduction.",
                )
            if sibilance_diagnosis.startswith("WARN"):
                add_finding(
                    findings,
                    "WARN",
                    "5-9 kHz harshness/sibilance",
                    sibilance_diagnosis.replace("WARN: ", ""),
                    f"Lead 5-9 kHz={lead_sibilance} dBFS, Instrument 5-9 kHz={inst_sibilance} dBFS",
                    "Use Pro-DS/Soothe2 before adding any 10-16 kHz air.",
                )
            if air_diagnosis.startswith("WARN"):
                add_finding(
                    findings,
                    "WARN",
                    "10-16 kHz air",
                    air_diagnosis.replace("WARN: ", ""),
                    f"Lead 10-16 kHz={lead_air} dBFS, Lead 1.5-5 kHz={lead_presence} dBFS",
                    "After sibilance control, add +0.5 to +2 dB high shelf or Gullfoss Recover 5-10%.",
                )
        if bass_group and drums_group:
            _, bass_y = bass_group
            _, drums_y = drums_group
            n = min(len(bass_y), len(drums_y))
            bass_low = band_db(bass_y[:n], lead_sr, 40, 120)
            drums_low = band_db(drums_y[:n], lead_sr, 40, 120)
            masking["bass_40_120_db"] = bass_low
            masking["drums_40_120_db"] = drums_low
            masking["bass_drums_low_delta_db"] = round(bass_low - drums_low, 2)
            if abs(bass_low - drums_low) < 3.0:
                add_finding(
                    findings,
                    "WARN",
                    "Bass vs Drums",
                    "Kick/808 low-end masking risk",
                    f"Bass 40-120 Hz={bass_low} dBFS, Drums 40-120 Hz={drums_low} dBFS",
                    "Separate kick and 808 fundamentals with dynamic EQ or sidechain ducking, 1-3 dB on overlap band.",
                )

    if not references:
        add_finding(
            findings,
            "WARN",
            "References",
            "No reference audio was directly measured in this run",
            "reference-dir empty and no readable reference zip",
            "Place references in ./references or provide --reference-zip.",
        )

    build_reports(
        report_dir,
        deliverable_dir,
        plot_dir,
        args.project_name,
        args.genre,
        args.target,
        stem_policy,
        stem_dir,
        metrics,
        references,
        findings,
        masking,
        master_print,
    )
    print(json.dumps({"status": "ok", "stem_count": len(metrics), "reference_count": len(references), "reports": rel(report_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
