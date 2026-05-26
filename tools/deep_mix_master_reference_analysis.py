#!/usr/bin/env python3
"""Deep reference/master analysis for ESTONA REAPER automation.

The script is deliberately technical-only. It extracts mix/master target ranges
from available WAV/AIFF/FLAC/MP3 files and never recommends copying melodies,
hooks, rhythms, arrangement fingerprints, vocal identity, or copyrighted
creative elements.

When only mastered references are available, stem-specific conclusions are
reported as unavailable. Full-mix proxies are still useful for EQ, dynamic EQ,
M/S EQ, saturation density, stereo safety, and master QC targets.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
EXPECTED_INPUT_DIR = PROJECT_ROOT / "00_AUDIO_INPUT"
MENTIONED_INPUT_DIR = Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48.")
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a"}
EPS = 1e-12


DETAILED_BANDS: List[Tuple[str, float, float, str]] = [
    ("sub_floor_20_40", 20, 40, "sub rumble/floor"),
    ("sub_weight_40_60", 40, 60, "808/kick fundamental weight"),
    ("bass_body_60_90", 60, 90, "bass body"),
    ("bass_punch_90_120", 90, 120, "kick/808 punch"),
    ("mud_120_180", 120, 180, "low-mid mud start"),
    ("warmth_180_250", 180, 250, "body/warmth"),
    ("box_250_350", 250, 350, "boxiness/mud"),
    ("vocal_body_350_500", 350, 500, "vocal/instrument body"),
    ("low_mid_read_500_800", 500, 800, "low-mid readability"),
    ("nasal_800_1200", 800, 1200, "nasal/forwardness"),
    ("presence_floor_1200_2000", 1200, 2000, "presence foundation"),
    ("presence_2000_3500", 2000, 3500, "vocal lead presence"),
    ("bite_3500_5000", 3500, 5000, "bite/edge"),
    ("harsh_5000_6500", 5000, 6500, "harshness"),
    ("sibilance_6500_8000", 6500, 8000, "sibilance"),
    ("air_edge_8000_10000", 8000, 10000, "air edge/hash"),
    ("air_10000_12000", 10000, 12000, "air"),
    ("fizz_12000_16000", 12000, 16000, "fizz/noise"),
    ("top_16000_20000", 16000, 20000, "top octave"),
]


def ffmpeg_binary() -> str:
    env = os.environ.get("FFMPEG_PATH")
    if env and Path(env).exists():
        return env
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def ffprobe_binary() -> Optional[str]:
    return shutil.which("ffprobe")


def ffprobe(path: Path) -> dict:
    probe = ffprobe_binary()
    if probe:
        try:
            out = subprocess.check_output(
                [
                    probe,
                    "-hide_banner",
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(path),
                ],
                text=True,
            )
            return json.loads(out)
        except Exception as exc:
            return {"backend": "ffprobe", "error": str(exc)}
    try:
        proc = subprocess.run(
            [ffmpeg_binary(), "-hide_banner", "-i", str(path), "-f", "null", "-"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return {"backend": "ffmpeg_stderr_fallback", "raw_summary": proc.stderr[:4000]}
    except Exception as exc:
        return {"backend": "metadata_unavailable", "error": str(exc)}


def find_audio_files() -> Tuple[List[Path], List[str]]:
    files: List[Path] = []
    missing: List[str] = []
    if EXPECTED_INPUT_DIR.exists():
        files.extend(p for p in EXPECTED_INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    else:
        missing.append(str(EXPECTED_INPUT_DIR))
    if MENTIONED_INPUT_DIR.exists():
        files.extend(p for p in MENTIONED_INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    seen = set()
    unique = []
    for path in sorted(files):
        if path.resolve() not in seen:
            seen.add(path.resolve())
            unique.append(path)
    return unique, missing


def classify(path: Path) -> str:
    name = path.name.lower()
    if name == "current_mix.wav" or "current_mix" in name:
        return "current_mix"
    if "vocal_stem" in name or ("vocal" in name and "stem" in name):
        return "vocal_stem"
    if "instrumental_stem" in name or "instrumental" in name:
        return "instrumental_stem"
    if name.startswith("reference_") or "reference" in name:
        return "reference"
    if "estona,nib" in name and "master" in name:
        return "reference"
    return "unknown_audio"


def db_amp(value: float) -> float:
    return 20.0 * math.log10(max(abs(float(value)), EPS))


def db_power(value: float) -> float:
    return 10.0 * math.log10(max(float(value), EPS))


def dist(values: Iterable[float]) -> dict:
    arr = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    if arr.size == 0:
        return {"median": None, "low": None, "high": None, "min": None, "max": None}
    return {
        "median": float(np.median(arr)),
        "low": float(np.percentile(arr, 25)),
        "high": float(np.percentile(arr, 75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def to_mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1).astype(np.float64) if audio.ndim == 2 else audio.astype(np.float64)


def load(path: Path) -> Tuple[np.ndarray, int, sf.SoundFile]:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float64")
    return audio, int(sr), sf.info(str(path))


def welch_power(x: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    nperseg = min(16384, max(2048, int(sr * 0.25)))
    return signal.welch(x, fs=sr, nperseg=nperseg, noverlap=nperseg // 2)


def band_power_from_psd(freqs: np.ndarray, pxx: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    return float(np.sum(pxx[mask]) + EPS)


def spectral_band_table(mono: np.ndarray, sr: int) -> Tuple[dict, np.ndarray, np.ndarray]:
    freqs, pxx = welch_power(mono, sr)
    total = float(np.sum(pxx) + EPS)
    table = {}
    for key, low, high, purpose in DETAILED_BANDS:
        p = band_power_from_psd(freqs, pxx, low, high)
        table[key] = {
            "low_hz": low,
            "high_hz": high,
            "purpose": purpose,
            "relative_power_db": db_power(p / total),
            "absolute_power_db": db_power(p),
        }
    mag = np.sqrt(pxx + EPS)
    table["shape"] = {
        "spectral_centroid_hz": float(np.sum(freqs * mag) / (np.sum(mag) + EPS)),
        "spectral_rolloff_85_hz": float(freqs[np.searchsorted(np.cumsum(mag), np.cumsum(mag)[-1] * 0.85)]),
        "spectral_flatness": float(np.exp(np.mean(np.log(mag + EPS))) / (np.mean(mag) + EPS)),
        "high_ratio_8k_20k": float(np.sum(pxx[freqs >= 8000]) / total),
        "top_ratio_12k_20k": float(np.sum(pxx[freqs >= 12000]) / total),
    }
    return table, freqs, pxx


def ms_band_table(audio: np.ndarray, sr: int) -> dict:
    if audio.shape[1] < 2:
        return {"status": "mono"}
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    f_mid, p_mid = welch_power(mid, sr)
    f_side, p_side = welch_power(side, sr)
    table = {"status": "stereo", "bands": {}}
    for key, low, high, purpose in DETAILED_BANDS:
        m = band_power_from_psd(f_mid, p_mid, low, high)
        s = band_power_from_psd(f_side, p_side, low, high)
        table["bands"][key] = {
            "purpose": purpose,
            "mid_power_db": db_power(m),
            "side_power_db": db_power(s),
            "side_minus_mid_db": db_power(s / max(m, EPS)),
            "mono_risk_if_low_band": bool(high <= 120 and s / max(m, EPS) > 0.25),
            "side_hash_risk_if_high_band": bool(low >= 8000 and s / max(m, EPS) > 0.8),
        }
    mid_e = float(np.mean(mid * mid) + EPS)
    side_e = float(np.mean(side * side) + EPS)
    corr = 1.0 if np.std(audio[:, 0]) < EPS or np.std(audio[:, 1]) < EPS else float(np.corrcoef(audio[:, 0], audio[:, 1])[0, 1])
    table["summary"] = {
        "stereo_correlation": corr,
        "side_to_mid_db": db_power(side_e / mid_e),
        "mid_to_side_ratio": float(mid_e / side_e),
    }
    return table


def stft_band_dynamics(mono: np.ndarray, sr: int) -> dict:
    freqs, times, zxx = signal.stft(mono, fs=sr, nperseg=4096, noverlap=3072, boundary=None)
    power = np.abs(zxx) ** 2
    total_by_frame = np.sum(power, axis=0) + EPS
    out = {}
    for key, low, high, purpose in DETAILED_BANDS:
        mask = (freqs >= low) & (freqs < high)
        band = np.sum(power[mask], axis=0) + EPS
        rel_db = 10 * np.log10(band / total_by_frame)
        abs_db = 10 * np.log10(band)
        out[key] = {
            "purpose": purpose,
            "median_relative_db": float(np.median(rel_db)),
            "p90_relative_db": float(np.percentile(rel_db, 90)),
            "p10_relative_db": float(np.percentile(rel_db, 10)),
            "dynamic_range_db": float(np.percentile(rel_db, 90) - np.percentile(rel_db, 10)),
            "burstiness_db": float(np.percentile(abs_db, 95) - np.percentile(abs_db, 50)),
            "dynamic_eq_watch": bool(
                (low >= 120 and high <= 350 and np.percentile(rel_db, 90) > -8)
                or (low >= 2000 and high <= 8000 and np.percentile(rel_db, 90) > -12)
                or (low >= 8000 and np.percentile(rel_db, 90) > -14)
            ),
        }
    return out


def envelope_metrics(mono: np.ndarray, sr: int) -> dict:
    frame = max(512, int(sr * 0.05))
    hop = max(128, int(sr * 0.025))
    if len(mono) <= frame:
        rms = np.array([np.sqrt(np.mean(mono * mono) + EPS)])
    else:
        rms = np.array([
            np.sqrt(np.mean(mono[i : i + frame] ** 2) + EPS)
            for i in range(0, len(mono) - frame + 1, hop)
        ])
    rms_db = 20 * np.log10(rms + EPS)
    diff = np.diff(rms, prepend=rms[0])
    threshold = max(float(np.percentile(diff, 95)), float(np.mean(diff) + np.std(diff) * 2))
    transients = np.where(diff > threshold)[0]
    tails = []
    hits = []
    for idx in transients:
        hit = rms[idx]
        tail = rms[idx + 4 : idx + 14]
        if tail.size:
            hits.append(hit)
            tails.append(float(np.mean(tail)))
    tail_ratio_db = db_amp(np.median(tails) / max(float(np.median(hits)) if hits else EPS, EPS)) if tails else None
    return {
        "transient_density_per_sec": float(len(transients) / max(len(mono) / sr, EPS)),
        "frame_rms_dynamic_range_db": float(np.percentile(rms_db, 95) - np.percentile(rms_db, 10)),
        "transient_to_median_sustain_db": float(np.percentile(rms_db, 95) - np.percentile(rms_db, 50)),
        "ambient_tail_proxy_db_after_transient": tail_ratio_db,
        "low_level_sustain_ratio": float(np.mean((rms_db > np.percentile(rms_db, 15)) & (rms_db < np.percentile(rms_db, 55)))),
        "reverb_inference_limit": "Full-mix proxy only. Reverb amount/decay cannot be isolated without stems or dry vocal.",
    }


def resonance_candidates(freqs: np.ndarray, pxx: np.ndarray) -> List[dict]:
    mask = (freqs >= 120) & (freqs <= 12000)
    f = freqs[mask]
    db = 10 * np.log10(pxx[mask] + EPS)
    if f.size < 20:
        return []
    smooth = signal.medfilt(db, kernel_size=31 if db.size > 31 else max(3, db.size // 2 * 2 + 1))
    prominence = db - smooth
    peaks, props = signal.find_peaks(prominence, height=3.5, distance=8)
    rows = []
    for idx in peaks:
        rows.append({"freq_hz": float(f[idx]), "prominence_db": float(prominence[idx]), "band_level_db": float(db[idx])})
    return sorted(rows, key=lambda x: x["prominence_db"], reverse=True)[:12]


def loudness_metrics(audio: np.ndarray, mono: np.ndarray, sr: int) -> dict:
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(mono * mono) + EPS))
    meter = pyln.Meter(sr, block_size=0.400)
    try:
        lufs = float(meter.integrated_loudness(audio if audio.shape[1] > 1 else mono))
    except Exception:
        lufs = db_amp(rms) - 0.691
    true_peak_proxy = float(np.max(np.abs(signal.resample_poly(audio, up=4, down=1, axis=0))))
    return {
        "integrated_lufs": lufs,
        "sample_peak_dbfs": db_amp(peak),
        "approx_true_peak_dbfs": db_amp(true_peak_proxy),
        "rms_dbfs": db_amp(rms),
        "crest_factor_db": db_amp(peak / max(rms, EPS)),
        "near_full_scale_sample_ratio": float(np.mean(np.abs(audio) > 0.999)),
        "clipping_or_codec_risk": bool(db_amp(peak) > -0.2 or db_amp(true_peak_proxy) > -1.0),
    }


def saturation_metrics(loudness: dict, spectral: dict, envelope: dict) -> dict:
    flatness = spectral["shape"]["spectral_flatness"]
    high_ratio = spectral["shape"]["high_ratio_8k_20k"]
    crest = loudness["crest_factor_db"]
    transient = envelope["transient_density_per_sec"]
    density = float(np.clip((8.5 - crest) / 4.0 + flatness * 0.9 + high_ratio * 2.0, 0.0, 1.0))
    shortage = float(np.clip((crest - 8.0) / 5.0 + max(0.0, 0.25 - flatness), 0.0, 1.0))
    harsh_drive_risk = float(np.clip(high_ratio * 6.0 + max(0.0, flatness - 0.32), 0.0, 1.0))
    return {
        "master_density_proxy": density,
        "saturation_shortage_proxy": shortage,
        "overbright_saturation_risk": harsh_drive_risk,
        "transient_preservation_proxy": float(np.clip(transient / 8.0, 0.0, 1.0)),
        "interpretation": "Proxy only: estimates density/drive from crest, flatness, high ratio, and transient activity.",
    }


def analyze_file(path: Path) -> dict:
    audio, sr, info = load(path)
    mono = to_mono(audio)
    spectral, freqs, pxx = spectral_band_table(mono, sr)
    env = envelope_metrics(mono, sr)
    loud = loudness_metrics(audio, mono, sr)
    sat = saturation_metrics(loud, spectral, env)
    return {
        "path": str(path),
        "filename": path.name,
        "role": classify(path),
        "file_inventory": {
            "format": info.format,
            "subtype": info.subtype,
            "duration_sec": float(len(mono) / sr),
            "sample_rate": sr,
            "channels": int(audio.shape[1]),
            "file_size_bytes": path.stat().st_size,
        },
        "metadata": ffprobe(path),
        "loudness_dynamics": loud,
        "detailed_eq_bands": spectral,
        "dynamic_eq_band_activity": stft_band_dynamics(mono, sr),
        "ms_eq_bands": ms_band_table(audio, sr),
        "transient_reverb_proxy": env,
        "saturation_density": sat,
        "resonance_candidates": resonance_candidates(freqs, pxx),
    }


def get_nested(item: dict, path: List[str]) -> Optional[float]:
    cur = item
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return float(cur) if isinstance(cur, (int, float)) and np.isfinite(cur) else None


def target_profile(items: List[dict]) -> dict:
    refs = [x for x in items if x["role"] == "reference"]
    profile = {"status": "ok" if refs else "no_references", "reference_count": len(refs)}
    paths = {
        "integrated_lufs": ["loudness_dynamics", "integrated_lufs"],
        "approx_true_peak_dbfs": ["loudness_dynamics", "approx_true_peak_dbfs"],
        "crest_factor_db": ["loudness_dynamics", "crest_factor_db"],
        "master_density_proxy": ["saturation_density", "master_density_proxy"],
        "saturation_shortage_proxy": ["saturation_density", "saturation_shortage_proxy"],
        "overbright_saturation_risk": ["saturation_density", "overbright_saturation_risk"],
        "transient_density_per_sec": ["transient_reverb_proxy", "transient_density_per_sec"],
        "ambient_tail_proxy_db_after_transient": ["transient_reverb_proxy", "ambient_tail_proxy_db_after_transient"],
    }
    profile["summary_targets"] = {
        key: dist(v for r in refs if (v := get_nested(r, path)) is not None)
        for key, path in paths.items()
    }
    profile["eq_band_targets"] = {}
    profile["dynamic_eq_targets"] = {}
    profile["ms_eq_targets"] = {}
    for key, _, _, purpose in DETAILED_BANDS:
        profile["eq_band_targets"][key] = {
            "purpose": purpose,
            "relative_power_db": dist(get_nested(r, ["detailed_eq_bands", key, "relative_power_db"]) for r in refs),
        }
        profile["dynamic_eq_targets"][key] = {
            "purpose": purpose,
            "median_relative_db": dist(get_nested(r, ["dynamic_eq_band_activity", key, "median_relative_db"]) for r in refs),
            "dynamic_range_db": dist(get_nested(r, ["dynamic_eq_band_activity", key, "dynamic_range_db"]) for r in refs),
            "burstiness_db": dist(get_nested(r, ["dynamic_eq_band_activity", key, "burstiness_db"]) for r in refs),
        }
        profile["ms_eq_targets"][key] = {
            "purpose": purpose,
            "side_minus_mid_db": dist(get_nested(r, ["ms_eq_bands", "bands", key, "side_minus_mid_db"]) for r in refs),
        }
    profile["automation_guidance"] = {
        "eq": "Compare current mix band shares against eq_band_targets; use ReaEQ for broad static correction only.",
        "dynamic_eq": "Use ReaXcomp/TDR Nova if installed for bands whose current p90 or burstiness exceeds target high range.",
        "ms_eq": "Use mid/side routing or JSFX M/S tools only when side-minus-mid is outside target range. Keep 20-120 Hz mostly mono.",
        "reverb": "Use ambient_tail_proxy only as a rough full-mix clue. Real reverb decisions need vocal/instrument stems.",
        "saturation": "Match density with parallel saturation/soft clipping. Avoid bright drive if overbright_saturation_risk is high.",
    }
    return profile


def build_reaper_recipe(profile: dict, current: Optional[dict]) -> dict:
    def target(key: str) -> dict:
        return profile.get("summary_targets", {}).get(key, {})

    recipe = {
        "status": "template_no_current_mix" if current is None else "current_mix_ready",
        "copyright_safety": "Technical target matching only; do not copy creative elements.",
        "no_antares": True,
        "requires_paid_tools": False,
        "reference_targets": {
            "lufs": target("integrated_lufs"),
            "crest_factor_db": target("crest_factor_db"),
            "density": target("master_density_proxy"),
            "ambient_tail_proxy": target("ambient_tail_proxy_db_after_transient"),
        },
        "chains": {
            "vocal_chain_when_stem_exists": [
                {"fx": "ReaEQ", "purpose": "HPF 70-100 Hz, body 150-500 Hz shaping, remove resonances only after stem analysis"},
                {"fx": "ReaXcomp", "purpose": "dynamic 2-5 kHz presence and 5-8 kHz harshness control"},
                {"fx": "ReaComp", "purpose": "gentle leveling, avoid flattening consonants"},
                {"fx": "JSFX estona_Vocal_AntiAI_Harsh", "purpose": "anti-glare/de-ess proxy"},
                {"fx": "short room send", "purpose": "glue/dryness repair if vocal sounds detached"},
            ],
            "instrumental_bus": [
                {"fx": "ReaEQ", "purpose": "120-350 Hz mud control, preserve 40-120 Hz weight"},
                {"fx": "JSFX saturation/soft clip", "purpose": "restore harmonic body without broad gain pushing"},
                {"fx": "MonoSub Guard", "purpose": "20-120 Hz side reduction"},
            ],
            "mix_bus": [
                {"fx": "ReaXcomp", "purpose": "broad dynamic EQ on mud/presence/harsh/air bands"},
                {"fx": "Vocal_Beat_Glue JSFX", "purpose": "gentle glue only if stems/current comparison proves detachment"},
                {"fx": "DigiClip JSFX", "purpose": "soft clip before limiter for density"},
            ],
            "master_chain": [
                {"fx": "ReaEQ", "purpose": "small broad correction from current-vs-reference band deltas"},
                {"fx": "ReaLimit", "purpose": "ceiling -1.0 dBFS, do not chase unsafe reference true peaks"},
                {"fx": "Python QC", "purpose": "measure WAV and MP3 after encode"},
            ],
            "ai_high_end_repair": [
                {"fx": "ReaXcomp", "band": "5-8 kHz", "purpose": "dynamic harshness control"},
                {"fx": "ReaXcomp or de-ess JSFX", "band": "6.5-9 kHz", "purpose": "sibilance/hash control"},
                {"fx": "ReaEQ", "band": "8-20 kHz", "purpose": "avoid air boost until hash/fizz score is under control"},
            ],
        },
        "current_specific_actions": [],
    }
    if current is None:
        recipe["current_specific_actions"].append("No current_mix.wav found, so no gain/EQ cut amounts are safe to apply yet.")
    return recipe


def md_range(value: dict, unit: str = "") -> str:
    if not isinstance(value, dict) or value.get("median") is None:
        return "n/a"
    return f"{value['median']:.2f}{unit} (IQR {value['low']:.2f} to {value['high']:.2f}{unit})"


def write_reports(data: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "deep_reference_mix_analysis.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (REPORTS_DIR / "reaper_automation_targets.json").write_text(
        json.dumps(data["reaper_recipe"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    profile = data["detailed_reference_target_profile"]
    lines = [
        "# Deep Reference Mix Analysis",
        "",
        "## 중요한 정정",
        "현재 자료는 mastered reference WAV뿐입니다. 그래서 stem별 보컬/비트/리버브를 실제로 분리 측정했다고 말할 수 없습니다.",
        "이번 deep 분석은 full-mix reference에서 가능한 EQ, dynamic EQ, M/S EQ, saturation, transient, high-end hash proxy를 최대한 세분화한 것입니다.",
        "",
        "## 분석 파일",
    ]
    for item in data["files"]:
        inv = item["file_inventory"]
        lines.append(f"- `{item['filename']}`: {item['role']}, {inv['duration_sec']:.1f}s, {inv['sample_rate']} Hz, {inv['channels']} ch, {inv['subtype']}")

    lines += [
        "",
        "## Reference Master Targets",
        f"- LUFS: {md_range(profile['summary_targets']['integrated_lufs'], ' LUFS')}",
        f"- Crest factor: {md_range(profile['summary_targets']['crest_factor_db'], ' dB')}",
        f"- Density proxy: {md_range(profile['summary_targets']['master_density_proxy'])}",
        f"- Transient density: {md_range(profile['summary_targets']['transient_density_per_sec'], '/sec')}",
        f"- Ambient/reverb tail proxy: {md_range(profile['summary_targets']['ambient_tail_proxy_db_after_transient'], ' dB')}",
        "",
        "## EQ Target Bands",
    ]
    key_bands = [
        "sub_weight_40_60",
        "bass_punch_90_120",
        "mud_120_180",
        "box_250_350",
        "presence_2000_3500",
        "bite_3500_5000",
        "harsh_5000_6500",
        "sibilance_6500_8000",
        "air_edge_8000_10000",
        "fizz_12000_16000",
    ]
    for key in key_bands:
        band = profile["eq_band_targets"][key]
        dyn = profile["dynamic_eq_targets"][key]
        ms = profile["ms_eq_targets"][key]
        lines.append(
            f"- `{key}` ({band['purpose']}): static {md_range(band['relative_power_db'], ' dB share')}, dynamic range {md_range(dyn['dynamic_range_db'], ' dB')}, side-mid {md_range(ms['side_minus_mid_db'], ' dB')}"
        )
    lines += [
        "",
        "## What This Enables",
        "- ReaEQ: current mix가 들어오면 band target 대비 과한 대역을 broad cut/boost로 계산 가능.",
        "- ReaXcomp/dynamic EQ: p90/burstiness가 높은 mud/presence/harsh/air band를 자동 후보로 지정 가능.",
        "- M/S EQ: side-minus-mid target으로 저역 side 위험과 고역 side hash를 판단 가능.",
        "- Saturation: crest/flatness/high-ratio 기반으로 drive 부족과 과한 bright drive 위험을 분리 가능.",
        "- Reverb: stem이 없으므로 tail proxy까지만 가능. 실제 vocal reverb 판단은 vocal stem 필요.",
    ]
    (REPORTS_DIR / "deep_reference_mix_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    recipe = data["reaper_recipe"]
    plan = [
        "# Detailed REAPER Automation Plan",
        "",
        "이 계획은 현재 자료만으로 가능한 자동화 설계입니다. 현재 mix/stem이 없으므로 구체적인 dB cut/boost는 아직 target range 형태입니다.",
        "",
        "## Status",
        f"- `{recipe['status']}`",
        "- No Antares.",
        "- Paid tools not required.",
        "- Reference audio is not mixed into premaster.",
        "",
        "## Chain Templates",
    ]
    for chain, steps in recipe["chains"].items():
        plan.append(f"### {chain}")
        for step in steps:
            extra = f" ({step.get('band')})" if step.get("band") else ""
            plan.append(f"- {step['fx']}{extra}: {step['purpose']}")
    plan += [
        "",
        "## Missing For True Stem Analysis",
        "- `00_AUDIO_INPUT/current_mix.wav`",
        "- `00_AUDIO_INPUT/vocal_stem.wav`",
        "- `00_AUDIO_INPUT/instrumental_stem.wav`",
        "",
        "## Next Code Task",
        "When current/stems exist, compute per-band deltas against `deep_reference_mix_analysis.json` and emit an exact `reaper_mix_recipe.json` with ReaEQ/ReaXcomp/JSFX values.",
    ]
    (REPORTS_DIR / "reaper_detailed_automation_plan.md").write_text("\n".join(plan) + "\n", encoding="utf-8")

    limitations = [
        "# Analysis Limitations With Current Materials",
        "",
        "현재 사용 가능한 자료는 mastered reference WAV 8개뿐입니다.",
        "",
        "## 가능한 것",
        "- reference loudness/dynamics target",
        "- full-mix EQ band target",
        "- full-mix dynamic EQ watch bands",
        "- full-mix M/S EQ target",
        "- low-end mono safety target",
        "- saturation/density proxy target",
        "- high-end hash/fizz proxy target",
        "- REAPER chain template design",
        "",
        "## 불가능한 것",
        "- 실제 stem별 보컬/비트/808/드럼 레벨 진단",
        "- 보컬 리버브 양/프리딜레이/디케이 확정",
        "- 보컬 튠 경직감의 원인 확정",
        "- instrumental saturation 부족량 확정",
        "- 현재곡의 구체적인 EQ cut/boost dB 자동 산출",
        "",
        "이 항목들은 `current_mix.wav` 또는 stems가 들어오면 계산할 수 있습니다.",
    ]
    (REPORTS_DIR / "analysis_limitations_current_materials.md").write_text("\n".join(limitations) + "\n", encoding="utf-8")


def main() -> None:
    files, missing_dirs = find_audio_files()
    expected_missing = list(missing_dirs)
    for name in ["current_mix.wav", "vocal_stem.wav", "instrumental_stem.wav"]:
        path = EXPECTED_INPUT_DIR / name
        if not path.exists():
            expected_missing.append(str(path))
    analyzed = [analyze_file(path) for path in files]
    current = next((x for x in analyzed if x["role"] == "current_mix"), None)
    profile = target_profile(analyzed)
    recipe = build_reaper_recipe(profile, current)
    data = {
        "status": "reference_only_deep_analysis" if current is None else "current_and_reference_deep_analysis",
        "project_root": str(PROJECT_ROOT),
        "input_dirs": [str(EXPECTED_INPUT_DIR), str(MENTIONED_INPUT_DIR)],
        "missing_expected_inputs": expected_missing,
        "files": analyzed,
        "detailed_reference_target_profile": profile,
        "reaper_recipe": recipe,
        "safety": {
            "technical_analysis_only": True,
            "do_not_copy_creative_elements": True,
            "do_not_remove_provenance_or_metadata_for_deception": True,
        },
    }
    write_reports(data)
    print(json.dumps({"status": data["status"], "files_analyzed": len(analyzed), "reports": ["deep_reference_mix_analysis.md", "reaper_detailed_automation_plan.md"]}, indent=2))


if __name__ == "__main__":
    main()
