#!/usr/bin/env python3
"""Analyze current/reference audio inputs for REAPER automation planning.

This script extracts only technical mix/master statistics. It does not copy or
infer musical content such as melody, hooks, rhythms, arrangement, or vocal
identity from references.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
EXPECTED_INPUT_DIR = PROJECT_ROOT / "00_AUDIO_INPUT"
MENTIONED_INPUT_DIR = Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48.")
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".aac"}
EPS = 1e-12


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


def run_ffprobe(path: Path) -> dict:
    probe = ffprobe_binary()
    if probe:
        cmd = [
            probe,
            "-hide_banner",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
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


def list_audio_files() -> Tuple[List[Path], List[str]]:
    missing = []
    files: List[Path] = []
    if EXPECTED_INPUT_DIR.exists():
        files.extend(sorted(p for p in EXPECTED_INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS))
    else:
        missing.append(str(EXPECTED_INPUT_DIR))
    if MENTIONED_INPUT_DIR.exists():
        external = sorted(p for p in MENTIONED_INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
        for path in external:
            if path not in files:
                files.append(path)
    return files, missing


def classify_file(path: Path) -> str:
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
    if "master" in name:
        return "candidate_reference_or_current_master"
    return "unknown_audio"


def db_amp(x: float) -> float:
    return 20.0 * math.log10(max(abs(float(x)), EPS))


def db_power(x: float) -> float:
    return 10.0 * math.log10(max(float(x), EPS))


def to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float64)
    return audio.mean(axis=1).astype(np.float64)


def read_audio(path: Path) -> Tuple[np.ndarray, int, sf.SoundFile]:
    data, sr = sf.read(str(path), always_2d=True, dtype="float64")
    info = sf.info(str(path))
    return data, int(sr), info


def frame_rms_db(mono: np.ndarray, sr: int, window_s: float, hop_s: float) -> List[float]:
    win = max(128, int(sr * window_s))
    hop = max(1, int(sr * hop_s))
    if mono.size <= win:
        return [db_power(float(np.mean(mono * mono)))]
    values = []
    for start in range(0, mono.size - win + 1, hop):
        frame = mono[start : start + win]
        values.append(db_power(float(np.mean(frame * frame))))
    return values


def distribution(values: Iterable[float]) -> dict:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return {"min": None, "p10": None, "median": None, "p90": None, "max": None}
    return {
        "min": float(np.min(arr)),
        "p10": float(np.percentile(arr, 10)),
        "median": float(np.median(arr)),
        "p90": float(np.percentile(arr, 90)),
        "max": float(np.max(arr)),
    }


def band_power_db(mono: np.ndarray, sr: int, low: float, high: float) -> float:
    if mono.size < 512:
        return -120.0
    nperseg = min(8192, max(1024, int(sr * 0.17)))
    freqs, pxx = signal.welch(mono, fs=sr, nperseg=nperseg)
    mask = (freqs >= low) & (freqs < high)
    total = float(np.sum(pxx) + EPS)
    band = float(np.sum(pxx[mask]) + EPS)
    return db_power(band / total)


def band_power_linear(mono: np.ndarray, sr: int, low: float, high: float) -> float:
    if mono.size < 512:
        return 0.0
    nperseg = min(8192, max(1024, int(sr * 0.17)))
    freqs, pxx = signal.welch(mono, fs=sr, nperseg=nperseg)
    mask = (freqs >= low) & (freqs < high)
    return float(np.sum(pxx[mask]) + EPS)


def spectral_shape(mono: np.ndarray, sr: int) -> dict:
    nperseg = min(8192, max(1024, int(sr * 0.17)))
    freqs, pxx = signal.welch(mono, fs=sr, nperseg=nperseg)
    mag = np.sqrt(pxx + EPS)
    centroid = float(np.sum(freqs * mag) / (np.sum(mag) + EPS))
    cumsum = np.cumsum(mag)
    rolloff = float(freqs[np.searchsorted(cumsum, cumsum[-1] * 0.85)])
    flatness = float(np.exp(np.mean(np.log(mag + EPS))) / (np.mean(mag) + EPS))
    high_ratio = float(np.sum(pxx[freqs >= 8000]) / (np.sum(pxx) + EPS))
    top_octave_ratio = float(np.sum(pxx[freqs >= 12000]) / (np.sum(pxx) + EPS))
    high_flatness = float(
        np.exp(np.mean(np.log(mag[freqs >= 8000] + EPS))) / (np.mean(mag[freqs >= 8000]) + EPS)
    ) if np.any(freqs >= 8000) else 0.0
    cutoff_risk = bool(top_octave_ratio < 0.0008 and high_ratio < 0.01)
    metallic_hash_score = float(np.clip(high_flatness * 1.7 + high_ratio * 8.0, 0.0, 1.0))
    return {
        "spectral_centroid_hz": centroid,
        "spectral_rolloff_85_hz": rolloff,
        "spectral_flatness": flatness,
        "high_frequency_energy_ratio_8k_20k": high_ratio,
        "top_octave_energy_ratio_12k_20k": top_octave_ratio,
        "high_band_flatness_8k_20k": high_flatness,
        "possible_ai_high_end_hash_score": metallic_hash_score,
        "sudden_high_frequency_cutoff_risk": cutoff_risk,
    }


def stereo_metrics(audio: np.ndarray, sr: int) -> dict:
    if audio.shape[1] < 2:
        return {
            "stereo_correlation": 1.0,
            "mid_side_energy_ratio": None,
            "low_end_mono_compatibility_risk": False,
            "excessive_side_high_frequency_energy": False,
            "unstable_center_image_risk": False,
        }
    left = audio[:, 0]
    right = audio[:, 1]
    corr = 1.0 if np.std(left) < EPS or np.std(right) < EPS else float(np.corrcoef(left, right)[0, 1])
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    mid_energy = float(np.mean(mid * mid) + EPS)
    side_energy = float(np.mean(side * side) + EPS)
    low_side = band_power_linear(side, sr, 20, 120)
    low_mid = band_power_linear(mid, sr, 20, 120)
    high_side = band_power_linear(side, sr, 8000, 20000)
    high_mid = band_power_linear(mid, sr, 8000, 20000)
    return {
        "stereo_correlation": corr,
        "mid_side_energy_ratio": float(mid_energy / side_energy),
        "side_to_mid_db": db_power(side_energy / mid_energy),
        "low_side_to_mid_db_20_120": db_power(low_side / max(low_mid, EPS)),
        "high_side_to_mid_db_8k_20k": db_power(high_side / max(high_mid, EPS)),
        "low_end_mono_compatibility_risk": bool(low_side / max(low_mid, EPS) > 0.25),
        "excessive_side_high_frequency_energy": bool(high_side / max(high_mid, EPS) > 0.8),
        "unstable_center_image_risk": bool(corr < 0.25 or side_energy > mid_energy * 0.75),
    }


def analyze_file(path: Path) -> dict:
    audio, sr, sf_info = read_audio(path)
    mono = to_mono(audio)
    duration = float(len(mono) / sr)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(mono * mono) + EPS))
    meter = pyln.Meter(sr, block_size=0.400)
    try:
        lufs = float(meter.integrated_loudness(audio if audio.shape[1] > 1 else mono))
    except Exception:
        lufs = db_power(rms * rms) - 0.691
    oversampled = signal.resample_poly(audio, up=4, down=1, axis=0)
    true_peak_proxy = db_amp(float(np.max(np.abs(oversampled))))
    short = frame_rms_db(mono, sr, 3.0, 1.0)
    momentary = frame_rms_db(mono, sr, 0.4, 0.1)
    low_signal_ratio = float(np.mean(np.abs(mono) < 1e-5))
    metrics = {
        "path": str(path),
        "filename": path.name,
        "role": classify_file(path),
        "file_size_bytes": path.stat().st_size,
        "format": sf_info.format,
        "subtype": sf_info.subtype,
        "duration_sec": duration,
        "sample_rate": sr,
        "channels": int(audio.shape[1]),
        "bit_depth_or_subtype": sf_info.subtype,
        "metadata": run_ffprobe(path),
        "loudness": {
            "integrated_lufs": lufs,
            "peak_dbfs": db_amp(peak),
            "approx_true_peak_dbfs": true_peak_proxy,
            "true_peak_note": "4x oversampled proxy, not a certified true-peak meter.",
            "rms_dbfs": db_amp(rms),
            "crest_factor_db": db_amp(peak / max(rms, EPS)),
            "dynamic_range_proxy_db": float(np.percentile(momentary, 95) - np.percentile(momentary, 10)),
            "short_term_rms_db_distribution": distribution(short),
            "momentary_rms_db_distribution": distribution(momentary),
            "clipping_risk": bool(db_amp(peak) > -0.2 or true_peak_proxy > -0.1),
            "mp3_overshoot_risk": bool(true_peak_proxy > -1.0),
            "silence_or_headroom_problem": bool(low_signal_ratio > 0.20 or db_amp(peak) < -6.0),
            "near_digital_full_scale_sample_ratio": float(np.mean(np.abs(audio) >= 0.999)),
        },
        "spectral": {
            "low_end_energy_20_60_db": band_power_db(mono, sr, 20, 60),
            "low_end_energy_60_120_db": band_power_db(mono, sr, 60, 120),
            "low_mid_mud_120_350_db": band_power_db(mono, sr, 120, 350),
            "vocal_body_150_500_db": band_power_db(mono, sr, 150, 500),
            "presence_2_5k_db": band_power_db(mono, sr, 2000, 5000),
            "harshness_5_8k_db": band_power_db(mono, sr, 5000, 8000),
            "air_noise_8_20k_db": band_power_db(mono, sr, 8000, 20000),
            **spectral_shape(mono, sr),
        },
        "stereo": stereo_metrics(audio, sr),
    }
    return metrics


def summarize_reference_profile(files: List[dict]) -> dict:
    refs = [f for f in files if f.get("role") == "reference"]
    if not refs:
        return {
            "status": "no_reference_files",
            "message": "No reference files were found in the expected folder or provided external folder.",
        }

    def vals(section: str, key: str) -> List[float]:
        out = []
        for item in refs:
            value = item.get(section, {}).get(key)
            if isinstance(value, (int, float)) and np.isfinite(value):
                out.append(float(value))
        return out

    def med_range(section: str, key: str) -> dict:
        arr = np.asarray(vals(section, key), dtype=float)
        if arr.size == 0:
            return {"median": None, "low": None, "high": None}
        return {
            "median": float(np.median(arr)),
            "low": float(np.percentile(arr, 25)),
            "high": float(np.percentile(arr, 75)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }

    return {
        "status": "ok",
        "reference_count": len(refs),
        "source_files": [r["filename"] for r in refs],
        "target_lufs_range": med_range("loudness", "integrated_lufs"),
        "target_true_peak_ceiling_dbfs": -1.0,
        "target_peak_range": med_range("loudness", "approx_true_peak_dbfs"),
        "low_end_target_behavior": {
            "20_60_db": med_range("spectral", "low_end_energy_20_60_db"),
            "60_120_db": med_range("spectral", "low_end_energy_60_120_db"),
            "guidance": "Keep sub controlled and mono-safe; add 808 harmonics rather than only pushing sub level.",
        },
        "vocal_presence_behavior": {
            "body_150_500_db": med_range("spectral", "vocal_body_150_500_db"),
            "presence_2_5k_db": med_range("spectral", "presence_2_5k_db"),
            "guidance": "Presence should stay readable without a hard 3-8 kHz glare spike.",
        },
        "high_end_smoothness_target": {
            "harshness_5_8k_db": med_range("spectral", "harshness_5_8k_db"),
            "air_noise_8_20k_db": med_range("spectral", "air_noise_8_20k_db"),
            "ai_hash_score": med_range("spectral", "possible_ai_high_end_hash_score"),
            "guidance": "Smooth top first, then add air; avoid bright exciter if hash score is high.",
        },
        "stereo_width_target": {
            "correlation": med_range("stereo", "stereo_correlation"),
            "side_to_mid_db": med_range("stereo", "side_to_mid_db"),
            "guidance": "Music bed can be wide, but low end should stay centered.",
        },
        "saturation_glue_target": {
            "crest_factor_db": med_range("loudness", "crest_factor_db"),
            "dynamic_range_proxy_db": med_range("loudness", "dynamic_range_proxy_db"),
            "spectral_flatness": med_range("spectral", "spectral_flatness"),
            "guidance": "Use controlled saturation/soft clipping for density without flattening transients.",
        },
        "master_density_target": {
            "integrated_lufs": med_range("loudness", "integrated_lufs"),
            "rms_dbfs": med_range("loudness", "rms_dbfs"),
            "guidance": "Reference median is a direction, not a mandate. Do not chase unsafe clipping.",
        },
    }


def compare_current_to_refs(current: Optional[dict], profile: dict) -> List[dict]:
    if not current:
        return [
            {
                "priority": 1,
                "issue": "current_mix.wav missing",
                "evidence": "No current mix was found in 00_AUDIO_INPUT or the provided Desktop directory.",
                "recommendation": "Place the current Suno/AI-assisted mix in 00_AUDIO_INPUT/current_mix.wav, then rerun analysis.",
            }
        ]
    issues = []
    lufs = current["loudness"]["integrated_lufs"]
    target = profile.get("target_lufs_range", {})
    if target.get("median") is not None and lufs < target["low"] - 1.0:
        issues.append({"priority": 1, "issue": "master density below reference range", "evidence": f"{lufs:.2f} LUFS vs reference IQR {target['low']:.2f} to {target['high']:.2f}", "recommendation": "Increase density via mix bus saturation/limiting only after spectral harshness is controlled."})
    if current["spectral"]["possible_ai_high_end_hash_score"] > 0.65:
        issues.append({"priority": 1, "issue": "possible AI high-end hash or metallic fizz", "evidence": f"hash score {current['spectral']['possible_ai_high_end_hash_score']:.2f}", "recommendation": "Dynamic 5-8 kHz control, de-ess, and avoid bright exciters."})
    if current["stereo"]["low_end_mono_compatibility_risk"]:
        issues.append({"priority": 2, "issue": "low-end mono compatibility risk", "evidence": f"low side/mid {current['stereo']['low_side_to_mid_db_20_120']:.2f} dB", "recommendation": "Mono sub below 100-120 Hz with JSFX mono sub guard."})
    if current["loudness"]["clipping_risk"]:
        issues.append({"priority": 1, "issue": "clipping or true-peak risk", "evidence": f"peak {current['loudness']['peak_dbfs']:.2f}, TP proxy {current['loudness']['approx_true_peak_dbfs']:.2f}", "recommendation": "Lower print ceiling and use ReaLimit true peak-aware safety if available."})
    return sorted(issues or [{"priority": 3, "issue": "no major proxy issue detected", "evidence": "Current mix sits within broad proxy checks.", "recommendation": "Still requires listening check."}], key=lambda x: x["priority"])


def vocal_instrument_relationship(files: List[dict]) -> dict:
    vocal = next((f for f in files if f["role"] == "vocal_stem"), None)
    inst = next((f for f in files if f["role"] == "instrumental_stem"), None)
    if not vocal or not inst:
        return {
            "status": "missing_stems",
            "message": "vocal_stem.wav and instrumental_stem.wav were not both found.",
            "available": {"vocal_stem": bool(vocal), "instrumental_stem": bool(inst)},
        }
    ratio = vocal["loudness"]["integrated_lufs"] - inst["loudness"]["integrated_lufs"]
    return {
        "status": "ok",
        "vocal_to_instrument_lufs_db": ratio,
        "vocal_presence_vs_instrument_db": vocal["spectral"]["presence_2_5k_db"] - inst["spectral"]["presence_2_5k_db"],
        "vocal_body_vs_instrument_db": vocal["spectral"]["vocal_body_150_500_db"] - inst["spectral"]["vocal_body_150_500_db"],
        "diagnosis": "vocal likely too upfront/detached" if ratio > 3 else "vocal may be buried" if ratio < -2 else "vocal/instrument balance is within a workable proxy range",
        "automation_friendly_corrections": [
            "Use ReaComp/ReaXcomp dynamic control instead of manual tuning tools.",
            "Use short room/early reflection send for glue if vocal sounds dry.",
            "Use ReaEQ/ReaXcomp to tame 2-8 kHz overlap before adding air.",
        ],
    }


def write_json_report(data: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "reference_analysis.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt_range(r: dict, suffix: str = "") -> str:
    if not isinstance(r, dict) or r.get("median") is None:
        return "n/a"
    return f"median {r['median']:.2f}{suffix}, IQR {r['low']:.2f} to {r['high']:.2f}{suffix}"


def write_markdown_reports(data: dict) -> None:
    files = data["files"]
    refs = [f for f in files if f["role"] == "reference"]
    current = data.get("current_mix")
    profile = data["reference_target_profile"]
    missing = data["missing_expected_inputs"]

    lines = [
        "# Reference Analysis",
        "",
        "This report uses references only for technical mix/master targets. It does not recommend copying melody, hooks, rhythm, arrangement, vocal identity, or copyrighted creative elements.",
        "",
        "## File Inventory",
    ]
    if missing:
        lines.append("Missing expected inputs:")
        for item in missing:
            lines.append(f"- `{item}`")
        lines.append("")
    for f in files:
        lines.append(
            f"- `{f['filename']}`: role `{f['role']}`, {f['duration_sec']:.1f}s, {f['sample_rate']} Hz, {f['channels']} ch, {f['bit_depth_or_subtype']}, {f['file_size_bytes'] / 1024 / 1024:.1f} MB"
        )
    lines += [
        "",
        "## Reference Target Profile",
        f"- Loudness: {fmt_range(profile.get('target_lufs_range', {}), ' LUFS')}",
        f"- True peak ceiling: {profile.get('target_true_peak_ceiling_dbfs', 'n/a')} dBFS target ceiling",
        f"- Low end 20-60 Hz: {fmt_range(profile.get('low_end_target_behavior', {}).get('20_60_db', {}), ' dB share')}",
        f"- Low end 60-120 Hz: {fmt_range(profile.get('low_end_target_behavior', {}).get('60_120_db', {}), ' dB share')}",
        f"- Vocal presence 2-5 kHz: {fmt_range(profile.get('vocal_presence_behavior', {}).get('presence_2_5k_db', {}), ' dB share')}",
        f"- Harshness 5-8 kHz: {fmt_range(profile.get('high_end_smoothness_target', {}).get('harshness_5_8k_db', {}), ' dB share')}",
        f"- Stereo correlation: {fmt_range(profile.get('stereo_width_target', {}).get('correlation', {}), '')}",
        "",
        "## Per-File Technical Notes",
    ]
    for f in files:
        lines += [
            f"### {f['filename']}",
            f"- LUFS {f['loudness']['integrated_lufs']:.2f}, peak {f['loudness']['peak_dbfs']:.2f} dBFS, TP proxy {f['loudness']['approx_true_peak_dbfs']:.2f} dBFS, crest {f['loudness']['crest_factor_db']:.2f} dB.",
            f"- Spectral: centroid {f['spectral']['spectral_centroid_hz']:.0f} Hz, 20-60 {f['spectral']['low_end_energy_20_60_db']:.2f} dB, 2-5k {f['spectral']['presence_2_5k_db']:.2f} dB, 5-8k {f['spectral']['harshness_5_8k_db']:.2f} dB, 8-20k {f['spectral']['air_noise_8_20k_db']:.2f} dB.",
            f"- Stereo: corr {f['stereo']['stereo_correlation']:.2f}, side/mid {f['stereo'].get('side_to_mid_db'):.2f} dB, low mono risk `{f['stereo']['low_end_mono_compatibility_risk']}`.",
        ]
    lines += [
        "",
        "## Metadata Note",
        "ffprobe metadata was logged in `reference_analysis.json`. Metadata is not treated as proof of audio quality.",
    ]
    (REPORTS_DIR / "reference_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    diagnosis = [
        "# Current Mix Diagnosis",
        "",
        "## Status",
    ]
    if not current:
        diagnosis += [
            "No `current_mix.wav` was found in `00_AUDIO_INPUT`, and no file in the provided Desktop directory was safely classifiable as the current Suno/AI-assisted mix.",
            "",
            "I analyzed the available reference WAVs and built a target profile, but I cannot honestly diagnose the current mix without the current mix file.",
        ]
    else:
        diagnosis.append(f"Current mix: `{current['filename']}`")
    diagnosis += [
        "",
        "## Ranked Issues",
    ]
    for issue in data["current_mix_ranked_issues"]:
        diagnosis.append(f"{issue['priority']}. {issue['issue']}: {issue['evidence']} Recommendation: {issue['recommendation']}")
    diagnosis += [
        "",
        "## What Could Sound AI-Like",
        "- Metallic 5-8 kHz glare or fizzy 8-20 kHz hash.",
        "- Vocal that is very dry, too forward, or detached from the instrumental.",
        "- Over-limited master with low crest factor and unstable high-frequency side energy.",
        "- Weak saturation/glue behind the vocal, making the vocal sit on top instead of inside the track.",
        "",
        "These are technical risk categories only. They are not proof of source provenance.",
    ]
    (REPORTS_DIR / "current_mix_diagnosis.md").write_text("\n".join(diagnosis) + "\n", encoding="utf-8")

    plan = [
        "# REAPER Mix/Master Plan",
        "",
        "Automation-friendly only: REAPER stock FX, JSFX, SWS/ReaPack utilities, and Python QC. No Antares. No reference audio should be mixed into the active premaster bus.",
        "",
        "## Vocal Chain",
        "- If `vocal_stem.wav` exists: ReaEQ high-pass around 70-100 Hz, body shaping around 150-500 Hz, dynamic ReaXcomp control around 2-8 kHz, light ReaComp leveling, short room/early reflection send for glue, optional ESTONA anti-harsh JSFX.",
        "- If no vocal stem exists: do not guess vocal tuning changes from the full mix. Use full-mix high-mid repair conservatively.",
        "",
        "## Instrumental Bus Chain",
        "- ReaEQ low-end cleanup: control 120-350 Hz mud without thinning 808.",
        "- JSFX/stock saturation or soft clipper for beat density if transients feel too flat or too clean.",
        "- Mono sub guard below 100-120 Hz; keep wide material mostly above the bass range.",
        "",
        "## Mix Bus Chain",
        "- ReaXcomp: gentle 2-5 kHz and 5-8 kHz dynamic control if current mix exceeds reference harshness target.",
        "- Gentle glue compression only if vocal/instrument feels detached; avoid pumping.",
        "- Soft clipper before limiter for controlled digicore density.",
        "",
        "## Master Chain",
        "- ReaEQ corrective tone only.",
        "- ReaComp or ReaXcomp for tiny broadband control.",
        "- ReaLimit with ceiling around -1.0 dBFS and MP3 safety check.",
        f"- Reference target loudness direction: {fmt_range(profile.get('target_lufs_range', {}), ' LUFS')}. Do not chase unsafe clipping.",
        "",
        "## Optional AI High-End Repair Chain",
        "- ReaXcomp band 5-8 kHz: fast-ish attack, medium release, 1-3 dB dynamic reduction.",
        "- ReaEQ narrow cuts only where harsh resonances are measured.",
        "- De-ess style control around 6-9 kHz if vocal stem exists.",
        "- Avoid bright exciters until high-end hash score is under control.",
        "",
        "## Missing Inputs To Complete Automation",
    ]
    for item in missing:
        plan.append(f"- `{item}`")
    plan += [
        "",
        "## Vocal/Instrument Relationship",
        data["vocal_instrument_relationship"].get("message", "See JSON for measured ratio."),
    ]
    (REPORTS_DIR / "reaper_mix_master_plan.md").write_text("\n".join(plan) + "\n", encoding="utf-8")


def main() -> None:
    files, missing_dirs = list_audio_files()
    expected_names = [
        EXPECTED_INPUT_DIR / "current_mix.wav",
        EXPECTED_INPUT_DIR / "vocal_stem.wav",
        EXPECTED_INPUT_DIR / "instrumental_stem.wav",
        EXPECTED_INPUT_DIR / "reference_01.wav",
        EXPECTED_INPUT_DIR / "reference_02.wav",
        EXPECTED_INPUT_DIR / "reference_03.wav",
    ]
    missing_expected = list(missing_dirs)
    if EXPECTED_INPUT_DIR.exists():
        for path in expected_names:
            if not path.exists():
                missing_expected.append(str(path))
    else:
        missing_expected.extend(str(p) for p in expected_names)
    analyzed = [analyze_file(path) for path in files]
    profile = summarize_reference_profile(analyzed)
    current = next((f for f in analyzed if f["role"] == "current_mix"), None)
    data = {
        "analysis_status": "partial_no_current_mix" if current is None else "ok",
        "project_root": str(PROJECT_ROOT),
        "expected_input_dir": str(EXPECTED_INPUT_DIR),
        "provided_external_dir": str(MENTIONED_INPUT_DIR),
        "safety_policy": {
            "technical_reference_only": True,
            "do_not_copy_creative_elements": True,
            "do_not_remove_provenance_or_metadata_for_deception": True,
            "no_antares": True,
            "no_paid_tools_required": True,
        },
        "missing_expected_inputs": missing_expected,
        "files": analyzed,
        "reference_target_profile": profile,
        "current_mix": current,
        "vocal_instrument_relationship": vocal_instrument_relationship(analyzed),
        "current_mix_ranked_issues": compare_current_to_refs(current, profile),
    }
    write_json_report(data)
    write_markdown_reports(data)
    print(json.dumps({"status": data["analysis_status"], "files_analyzed": len(analyzed), "reports_dir": str(REPORTS_DIR)}, indent=2))


if __name__ == "__main__":
    main()
