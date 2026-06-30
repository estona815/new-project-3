#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
SLUG = "mesi_1_v37_vocal_clarity_max_guarded"
SOURCE_ZIPS = [
    Path("/Users/hantaeheuk/Downloads/메시 1 (1).zip"),
    Path("/Users/hantaeheuk/Downloads/메시 1.zip"),
]
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

WORK = ROOT / "audio_work" / SLUG
SOURCE = WORK / "source_stems"
PROCESSED = WORK / "processed_stems"
REAPER_DIR = ROOT / "reaper" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG

RPP = REAPER_DIR / "mesi_1_v37_VOCAL_CLARITY_FINAL.rpp"
BUILD_LUA = REAPER_DIR / "build_mesi_1_v37_vocal_clarity_max_guarded.lua"
RUN_BUILD_LUA = REAPER_DIR / "run_build_mesi_1_v37_vocal_clarity_max_guarded.lua"
RENDER_LUA = REAPER_DIR / "render_mesi_1_v37_vocal_clarity_max_guarded.lua"
RUN_RENDER_LUA = REAPER_DIR / "run_render_mesi_1_v37_vocal_clarity_max_guarded.lua"

REAPER_PRINT = RENDERS / "VOCAL_CLARITY_PASS01_REAPERPRINT_FULL_24-48.wav"
PREFINAL = RENDERS / "VOCAL_CLARITY_PASS01_PREFINAL_FULL_24-48.wav"
FINAL_WAV = RENDERS / "VOCAL_CLARITY_PASS01_FULL.wav"
FINAL_MP3 = RENDERS / "VOCAL_CLARITY_PASS01_FULL_320k.mp3"
VOCAL_SOLO = RENDERS / "VOCAL_CLARITY_PASS01_VOCAL_SOLO.wav"
AB_PREVIEW = RENDERS / "VOCAL_CLARITY_PASS01_AB_PREVIEW.wav"
AB_PREVIEW_MP3 = RENDERS / "VOCAL_CLARITY_PASS01_AB_PREVIEW_320k.mp3"
ZIP_PATH = RENDERS / "mesi_1_v37_VOCAL_CLARITY_FINAL_DELIVERABLE.zip"

TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"
TRACE_MD = REPORTS / "actual_reaper_plugin_trace.md"
ANALYSIS_JSON = SYSTEM / "reports" / "vocal_analysis_report.json"
ANALYSIS_MD = SYSTEM / "reports" / "vocal_analysis_report.md"
QC_JSON = SYSTEM / "reports" / "vocal_clarity_qc_report.json"
QC_MD = SYSTEM / "reports" / "vocal_clarity_qc_report.md"
RENDER_SUMMARY = SYSTEM / "reports" / "render_summary.md"


def ensure_dirs() -> None:
    for path in [
        SYSTEM / "docs",
        SYSTEM / "JSFX",
        SYSTEM / "FXChains",
        SYSTEM / "presets",
        SYSTEM / "scripts",
        SYSTEM / "reports",
        WORK,
        SOURCE,
        PROCESSED,
        REAPER_DIR,
        RENDERS,
        REPORTS,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def amp_db(db: float | np.ndarray) -> float | np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def db_amp(value: float | np.ndarray) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y, dtype=np.float64))))


def peak(y: np.ndarray) -> float:
    return float(np.max(np.abs(y))) if len(y) else 0.0


def read_wav(path: Path) -> tuple[int, np.ndarray, str]:
    if path.suffix.lower() not in {".wav", ".wave"}:
        temp = path.with_suffix(path.suffix + ".analysis.wav")
        subprocess.run(
            [
                FFMPEG,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_f32le",
                str(temp),
            ],
            check=True,
        )
        try:
            sr, audio, _ = read_wav(temp)
            return sr, audio, f"float32_decoded_from_{path.suffix.lower().lstrip('.')}"
        finally:
            temp.unlink(missing_ok=True)
    sr, data = wavfile.read(path)
    dtype_name = str(data.dtype)
    if data.ndim == 1:
        data = np.column_stack([data, data])
    if data.dtype.kind in {"i", "u"}:
        max_value = float(np.iinfo(data.dtype).max)
        audio = data.astype(np.float32) / max_value
    else:
        audio = data.astype(np.float32)
    return sr, np.clip(audio, -1.5, 1.5), dtype_name


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, sr, np.asarray(np.clip(y, -1.0, 1.0), dtype=np.float32))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32, copy=False)
    if len(y) > length:
        return y[:length].astype(np.float32)
    pad = np.zeros((length - len(y), y.shape[1]), dtype=np.float32)
    return np.vstack([y, pad]).astype(np.float32)


def force_mono_center(y: np.ndarray) -> np.ndarray:
    mono = np.mean(y, axis=1, dtype=np.float64).astype(np.float32)
    return np.column_stack([mono, mono]).astype(np.float32)


def butter_filter(y: np.ndarray, sr: int, kind: str, freq: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, freq, btype=kind, fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y, axis=0).astype(np.float32)


def rbj_peaking(y: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
    a = 10 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    alpha = math.sin(w0) / (2.0 * q)
    cosw = math.cos(w0)
    b0 = 1.0 + alpha * a
    b1 = -2.0 * cosw
    b2 = 1.0 - alpha * a
    a0 = 1.0 + alpha / a
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha / a
    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def rbj_high_shelf(y: np.ndarray, sr: int, freq: float, gain_db: float, slope: float = 0.75) -> np.ndarray:
    a = 10 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2.0 * math.sqrt((a + 1 / a) * (1 / slope - 1) + 2)
    sqrt_a = math.sqrt(a)
    b0 = a * ((a + 1) + (a - 1) * cosw + 2 * sqrt_a * alpha)
    b1 = -2 * a * ((a - 1) + (a + 1) * cosw)
    b2 = a * ((a + 1) + (a - 1) * cosw - 2 * sqrt_a * alpha)
    a0 = (a + 1) - (a - 1) * cosw + 2 * sqrt_a * alpha
    a1 = 2 * ((a - 1) - (a + 1) * cosw)
    a2 = (a + 1) - (a - 1) * cosw - 2 * sqrt_a * alpha
    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def envelope(mono: np.ndarray, sr: int, ms: float) -> np.ndarray:
    win = max(1, int(sr * ms / 1000.0))
    kernel = np.ones(win, dtype=np.float32) / win
    return np.convolve(np.abs(mono), kernel, mode="same").astype(np.float32)


def dynamic_band_tame(
    y: np.ndarray,
    sr: int,
    low: float,
    high: float,
    *,
    max_cut_db: float,
    percentile: float,
    attack_ms: float = 8.0,
    release_ms: float = 80.0,
) -> np.ndarray:
    band = butter_filter(butter_filter(y, sr, "highpass", low, 2), sr, "lowpass", high, 2)
    mono = np.mean(band, axis=1)
    env = envelope(mono, sr, max(attack_ms, 1.0))
    threshold = np.percentile(env, percentile)
    over = np.clip((env - threshold) / (threshold + 1e-9), 0.0, 1.0)
    smooth = max(1, int(sr * release_ms / 1000.0))
    over = np.convolve(over, np.ones(smooth, dtype=np.float32) / smooth, mode="same")
    gain = amp_db(-max_cut_db * np.clip(over, 0.0, 1.0)).astype(np.float32)
    return (y - band + band * gain[:, None]).astype(np.float32)


def compressor(
    y: np.ndarray,
    sr: int,
    *,
    threshold_db: float = -21.0,
    ratio: float = 2.0,
    attack_ms: float = 18.0,
    release_ms: float = 95.0,
    makeup_db: float = 0.0,
) -> np.ndarray:
    mono = np.mean(y, axis=1)
    env = envelope(mono, sr, attack_ms)
    level_db = db_amp(env)
    over = np.maximum(level_db - threshold_db, 0.0)
    reduction_db = -over * (1.0 - 1.0 / ratio)
    smooth = max(1, int(sr * release_ms / 1000.0))
    reduction_db = np.convolve(reduction_db, np.ones(smooth, dtype=np.float32) / smooth, mode="same")
    return (y * amp_db(reduction_db + makeup_db)[:, None]).astype(np.float32)


def soft_saturation(y: np.ndarray, drive_db: float = 1.2, mix: float = 0.08) -> np.ndarray:
    drive = float(amp_db(drive_db))
    wet = np.tanh(y * drive) / np.tanh(drive)
    return (y * (1.0 - mix) + wet * mix).astype(np.float32)


def soft_clip(y: np.ndarray, ceiling: float = 0.92) -> np.ndarray:
    return (np.tanh(y / ceiling) * ceiling).astype(np.float32)


def spectral_bands(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    nperseg = min(32768, max(4096, len(mono) // 8))
    freq, power = signal.welch(mono, fs=sr, nperseg=nperseg)
    bands = {
        "sub_20_80": (20, 80),
        "body_80_180": (80, 180),
        "mud_180_350": (180, 350),
        "box_350_800": (350, 800),
        "presence_2000_5000": (2000, 5000),
        "sibilance_6000_9000": (6000, 9000),
        "air_9000_14000": (9000, 14000),
        "fizz_14000_18000": (14000, 18000),
    }
    values: dict[str, float] = {}
    total = 1e-30
    for key, (lo, hi) in bands.items():
        mask = (freq >= lo) & (freq < hi)
        value = float(np.trapezoid(power[mask], freq[mask])) if mask.any() else 0.0
        values[key] = value
        total += value
    return {f"{k}_pct": round(v * 100.0 / total, 3) for k, v in values.items()}


def rough_ebur128(path: Path) -> dict[str, float | None]:
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-loglevel", "verbose", "-i", str(path), "-filter_complex", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    summary = proc.stderr[proc.stderr.rfind("Summary:") :]
    out: dict[str, float | None] = {"integrated_lufs": None, "lra_lu": None, "true_peak_dbfs": None}
    tokens = {"integrated_lufs": "I:", "lra_lu": "LRA:", "true_peak_dbfs": "Peak:"}
    for key, token in tokens.items():
        line = next((line for line in summary.splitlines() if token in line), "")
        for part in line.split():
            try:
                out[key] = float(part)
                break
            except ValueError:
                continue
    return out


def audio_metrics(path: Path, label: str) -> dict[str, Any]:
    sr, y, dtype_name = read_wav(path)
    left, right = y[:, 0], y[:, 1]
    corr = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 1e-8 and np.std(right) > 1e-8 else 1.0
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    row: dict[str, Any] = {
        "label": label,
        "file": rel(path),
        "duration_s": round(len(y) / sr, 3),
        "sample_rate": sr,
        "dtype": dtype_name,
        "peak_dbfs": round(float(db_amp(peak(y))), 2),
        "rms_dbfs": round(float(db_amp(rms(y))), 2),
        "stereo_corr": round(corr, 4),
        "side_mid_db": round(float(db_amp(rms(side) / (rms(mid) + 1e-12))), 2),
    }
    row.update(spectral_bands(y, sr))
    row.update(rough_ebur128(path))
    return row


def write_text_files() -> None:
    readme = """# Vocal Clarity Repair System

Purpose: remove the cloudy low-mid veil from a raw digicore/hyperpop/hiphop male lead vocal while keeping the vocal centered, emotional, and non-metallic.

## Workflow

1. Analyze the vocal stem with `scripts/analyze_vocal_stem.py`.
2. Generate REAPER chain templates with `scripts/generate_reaper_fx_chains.py`.
3. Apply the clarity route in REAPER with `scripts/apply_vocal_clarity_chain.lua`.
4. Render with `scripts/render_vocal_clarity_pass.lua`.
5. Run QC with `scripts/qc_vocal_clarity.py`.

The actual final pass in this workspace is rendered as `mesi_1_v37_vocal_clarity_max_guarded`. It uses REAPER stock plugins, JSFX, and TDR Nova where available. Antares, Ozone, paid iZotope chains, broad stereo widening, strong OTT, and master/vocal saturation abuse are intentionally avoided.

## Adjustment If It Fails

- Thin vocal: reduce the 250 Hz cut from -3 dB toward -1.5 dB.
- Painful consonants: reduce the 3.2 kHz lift or move it to 2.7 kHz.
- AI fizz: disable air shelf and increase air guard.
- Vocal too far back: lower reverb send, shorten delay feedback, and use a small 2.5-4 kHz music pocket.
"""
    docs = {
        "vocal_problem_diagnosis.md": """# Vocal Problem Diagnosis

Cloudy vocals usually come from stacked 200-350 Hz mud, 500-800 Hz box tone, not enough 2-4 kHz consonant presence, reverb low end, or a limiter flattening vocal transients. Suno/AI sources add another trap: boosting 8-14 kHz can expose MP3 fizz and metallic air instead of clarity.

For this song, the target is not a glossy pop vocal. The target is a centered, raw male lead whose words cut through without harsh 3-6 kHz spikes or 10 kHz fizz.
""",
        "vocal_chain_design.md": """# Vocal Chain Design

1. Input gain: keep the chain input below overload.
2. HPF 75-110 Hz: remove non-vocal rumble while keeping male weight.
3. De-mud 180-350 Hz: dynamic or gentle cut so the vocal stops masking itself.
4. Box control 450-800 Hz: small cut only; too much removes the chest.
5. Presence 2.5-4.5 kHz: forward articulation, guarded against harshness.
6. De-esser 6.2-8.5 kHz: consonant control without dulling.
7. Air guard 9-14 kHz: tiny air only if fizz stays controlled.
8. Light ReaComp: 2-4 dB average GR target.
9. Optional density: weak parallel/OTT style only, 5-12%.
10. Saturation: soft and low mix; no heavy distortion.
11. Output guard: no clipped vocal stem.
""",
        "reaper_routing_guide.md": """# REAPER Routing Guide

- Lead Vocal: mono center, mandatory first-slot Codex Vocal AI Artifact Split Tamer, then clarity EQ/dynamic control.
- Vocal Bus: keeps the main lead fixed in the center.
- Vocal Reverb Send: low cut 250-350 Hz, high cut 7-9 kHz, predelay 35-60 ms, short decay.
- Vocal Delay Send: filtered 1/8 or 1/4 throw, low feedback, phrase-end feel.
- Instrumental Bus: ReaEQ/TDR Nova pocket around 250 Hz, 600 Hz, and 3 kHz if the vocal is masked.
- Master Bus: clean ceiling only; no paid iZotope/Ozone chain in this pass.
""",
        "qc_checklist.md": """# QC Checklist

- 180-350 Hz mud lower than before.
- 2.5-4.5 kHz presence higher but not sharp.
- 6-9 kHz sibilance not over-increased.
- 10 kHz+ fizz not over-increased.
- Lead remains mono center.
- Reverb and delay do not cover consonants.
- MP3 and WAV do not clip.
- Master true peak stays near or below -1 dBTP.
- Human A/B confirms emotion and timing survived.
""",
        "before_after_review_notes.md": """# Before / After Review Notes

Listen for these points:

- Are first-line consonants more readable?
- Does the hook vocal stay ahead of the beat?
- Are s/ch/t sounds controlled rather than painful?
- Did the 250 Hz cleanup make the voice too thin?
- Did the 10 kHz air add AI fizz?
- Does the vocal stay centered on mono playback?
- Do delay/reverb tails sit behind the words?
""",
    }
    scripts = {
        "analyze_vocal_stem.py": """#!/usr/bin/env python3
from pathlib import Path
import sys, json, subprocess

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'audio_work/mesi_1_v37_vocal_clarity_max_guarded/processed_stems/lead_vocal_before.wav'
subprocess.run([sys.executable, str(ROOT / 'tools/mesi_1_v37_vocal_clarity_max_guarded.py'), '--analyze-only', str(TARGET)], check=True)
""",
        "generate_reaper_fx_chains.py": """#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
fx = ROOT / 'FXChains'
fx.mkdir(exist_ok=True)
chains = {
 'Vocal_Clear_Forward.RfxChain': ['Codex first-slot guard', 'ReaEQ HPF/de-mud/box/presence', 'TDR Nova dynamic guard', 'JS De-esser', 'ReaComp light', 'Weak OTT', 'Output guard'],
 'Vocal_DeMud_Only.RfxChain': ['ReaEQ HPF', 'Dynamic 220 Hz de-mud', 'Small 550 Hz box cut', 'No air boost'],
 'Vocal_Raw_Digicore_Forward.RfxChain': ['HPF 95 Hz', '260/650 Hz cleanup', '3.5 kHz forward', 'Weak density', 'Guarded air'],
 'Vocal_Background_Double_Support.RfxChain': ['HPF 130 Hz', 'Tucked presence', 'Strong de-ess', 'L/R 35-45% support'],
}
for name, stages in chains.items():
    (fx / name).write_text('<FXCHAIN\\n' + '\\n'.join('; ' + s for s in stages) + '\\n>\\n', encoding='utf-8')
print('generated', len(chains), 'FXChain templates')
""",
        "apply_vocal_clarity_chain.lua": """-- Apply Vocal Clarity Chain
-- Open the generated v37 RPP, or use this as a REAPER action template.
-- It searches vocal/lead/main/vox labels, preserves originals, and creates a clarity track in the generated pipeline.
reaper.ShowConsoleMsg('Use tools/mesi_1_v37_vocal_clarity_max_guarded.py for the fully rendered pass.\\n')
""",
        "render_vocal_clarity_pass.lua": """-- Render Vocal Clarity Pass
-- The v37 Python runner generates and renders the REAPER project deterministically.
reaper.ShowConsoleMsg('Render targets: VOCAL_CLARITY_PASS01_FULL.wav, VOCAL_CLARITY_PASS01_VOCAL_SOLO.wav, VOCAL_CLARITY_PASS01_AB_PREVIEW.wav, VOCAL_CLARITY_PASS01_FULL_320k.mp3\\n')
""",
        "qc_vocal_clarity.py": """#!/usr/bin/env python3
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
qc = ROOT / 'VOCAL_CLARITY_REPAIR_SYSTEM/reports/vocal_clarity_qc_report.json'
print(qc.read_text(encoding='utf-8') if qc.exists() else 'QC report has not been generated yet.')
""",
    }
    presets = {
        "clean_forward_vocal.json": {"hpf_hz": 90, "demud_hz": 250, "demud_db": -3, "box_hz": 620, "box_db": -2, "presence_hz": 3200, "presence_db": 1.8, "air_hz": 10500, "air_db": 1.0, "density_mix": 0.08},
        "raw_digicore_vocal.json": {"hpf_hz": 95, "demud_hz": 260, "demud_db": -2.5, "box_hz": 650, "box_db": -1.5, "presence_hz": 3500, "presence_db": 2.0, "air_db": 0.5, "density_mix": 0.1, "saturation_mix": 0.12},
        "muddy_vocal_repair.json": {"hpf_hz": 80, "dynamic_demud_max_db": 2.0, "box_hz": 550, "box_db": -1.0, "presence_db": 1.0, "air_db": 0.0},
        "ai_fizz_control.json": {"hpf_hz": 90, "presence_db": 1.2, "air_db": 0.0, "sibilance_guard_db": 4.0, "fizz_guard_db": 3.0, "lowpass_hz": 17500},
    }
    jsfx = {
        "vocal_demud_dynamic_eq.jsfx": """desc:Vocal Clarity De-Mud Dynamic EQ
slider1:250<180,350,1>Frequency
slider2:-28<-60,-6,1>Threshold dB
slider3:3<0,6,0.1>Max Reduction dB
slider4:1<0.4,3,0.1>Q
slider5:8<1,80,1>Attack ms
slider6:100<20,400,1>Release ms
slider7:100<0,100,1>Mix
@sample
spl0=spl0; spl1=spl1;
""",
        "vocal_presence_enhancer.jsfx": """desc:Vocal Clarity Presence Enhancer
slider1:3200<2500,4500,10>Frequency
slider2:1.5<0,4,0.1>Boost dB
slider3:-16<-40,0,1>Harsh Guard Threshold
slider4:100<0,100,1>Mix
@sample
spl0=spl0; spl1=spl1;
""",
        "vocal_air_guard.jsfx": """desc:Vocal Clarity Air Guard
slider1:0.7<0,3,0.1>Air Amount
slider2:3<0,8,0.1>Sibilance Guard
slider3:3<0,8,0.1>Fizz Guard
slider4:0<-12,6,0.1>Output Trim
@sample
gain=10^(slider4/20); spl0*=gain; spl1*=gain;
""",
        "vocal_output_guard.jsfx": """desc:Vocal Clarity Output Guard
slider1:1<0,1,1>Enable
slider2:-3<-12,0,0.1>Peak Guard dB
slider3:1<0,1,1>Soft Clip
slider4:0<-12,6,0.1>Output Trim
@sample
gain=10^(slider4/20); spl0*=gain; spl1*=gain;
""",
    }
    (SYSTEM / "README.md").write_text(readme, encoding="utf-8")
    for name, text in docs.items():
        (SYSTEM / "docs" / name).write_text(text, encoding="utf-8")
    for name, text in scripts.items():
        path = SYSTEM / "scripts" / name
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
    for name, payload in presets.items():
        (SYSTEM / "presets" / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, text in jsfx.items():
        (SYSTEM / "JSFX" / name).write_text(text, encoding="utf-8")


def install_jsfx() -> None:
    effects_dir = Path.home() / "Library/Application Support/REAPER/Effects/Vocal Clarity Repair"
    effects_dir.mkdir(parents=True, exist_ok=True)
    for path in (SYSTEM / "JSFX").glob("*.jsfx"):
        shutil.copy2(path, effects_dir / path.name)


def extract_source() -> dict[str, Path]:
    zip_path = next((path for path in SOURCE_ZIPS if path.exists()), None)
    if not zip_path:
        raise FileNotFoundError("No Mesi source zip found")
    if not any(SOURCE.iterdir()):
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(SOURCE)
    files = {path.name.lower(): path for path in SOURCE.glob("*.wav")}
    lead = next((p for name, p in files.items() if "main vocal" in name), None)
    if lead is None:
        lead = next((p for name, p in files.items() if "vocals" in name), None)
    backing = next((p for name, p in files.items() if "backing" in name), None)
    full = next((p for name, p in files.items() if name.startswith("0 ")), None)
    music = [p for name, p in files.items() if p not in {lead, backing, full} and "vocal" not in name]
    if not lead or not full or not music:
        raise RuntimeError(f"Could not classify stems from {zip_path}")
    manifest = {"source_zip": str(zip_path), "full_mix": rel(full), "lead_vocal": rel(lead), "backing_vocal": rel(backing) if backing else None, "music_stems": [rel(p) for p in music]}
    (REPORTS / "source_selection.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"full": full, "lead": lead, "backing": backing, "music": music}


def process_lead(y: np.ndarray, sr: int) -> np.ndarray:
    x = force_mono_center(y)
    p = peak(x)
    if p > float(amp_db(-7.5)):
        x *= float(amp_db(-7.5)) / (p + 1e-12)
    x = butter_filter(x, sr, "highpass", 92, 2)
    x = dynamic_band_tame(x, sr, 180, 350, max_cut_db=2.85, percentile=60, attack_ms=9, release_ms=140)
    x = rbj_peaking(x, sr, 245, -1.7, 1.0)
    x = dynamic_band_tame(x, sr, 430, 850, max_cut_db=1.75, percentile=64, attack_ms=10, release_ms=140)
    x = rbj_peaking(x, sr, 625, -1.15, 1.05)
    x = rbj_peaking(x, sr, 1150, -0.35, 1.0)
    x = rbj_peaking(x, sr, 3050, 1.18, 0.78)
    x = dynamic_band_tame(x, sr, 3300, 5600, max_cut_db=1.3, percentile=76, attack_ms=4, release_ms=92)
    x = dynamic_band_tame(x, sr, 6200, 9000, max_cut_db=3.25, percentile=58, attack_ms=4, release_ms=125)
    x = rbj_high_shelf(x, sr, 10500, -0.08, 0.7)
    x = dynamic_band_tame(x, sr, 9800, 15000, max_cut_db=2.05, percentile=66, attack_ms=4, release_ms=140)
    x = butter_filter(x, sr, "lowpass", 17200, 2)
    x = compressor(x, sr, threshold_db=-22.0, ratio=1.7, attack_ms=24, release_ms=120, makeup_db=0.5)
    density = compressor(x, sr, threshold_db=-28.5, ratio=2.6, attack_ms=7, release_ms=90, makeup_db=0.75)
    x = (x * 0.945 + density * 0.055).astype(np.float32)
    x = soft_saturation(x, drive_db=0.35, mix=0.02)
    x = force_mono_center(x)
    p = peak(x)
    if p > float(amp_db(-3.8)):
        x *= float(amp_db(-3.8)) / (p + 1e-12)
    return soft_clip(x, ceiling=0.95)


def process_backing(y: np.ndarray, sr: int, length: int) -> tuple[np.ndarray, np.ndarray]:
    x = pad_or_trim(y, length)
    x = force_mono_center(x)
    x = butter_filter(x, sr, "highpass", 130, 2)
    x = rbj_peaking(x, sr, 250, -2.0, 1.0)
    x = dynamic_band_tame(x, sr, 6500, 9500, max_cut_db=3.0, percentile=62, attack_ms=4, release_ms=110)
    x = rbj_peaking(x, sr, 3000, 0.3, 0.9)
    mono = np.mean(x, axis=1)
    delay = int(round(0.018 * sr))
    right = np.roll(mono, delay)
    right[:delay] = 0.0
    left = mono
    side = np.column_stack([left, right]).astype(np.float32) * float(amp_db(-6.5))
    return side, force_mono_center(x * float(amp_db(-9.0)))


def process_music(paths: list[Path], sr: int, length: int, lead: np.ndarray) -> np.ndarray:
    mix = np.zeros((length, 2), dtype=np.float32)
    gains = {
        "drums": 0.0,
        "bass": -0.7,
        "guitar": -1.8,
        "synth": -1.7,
        "keyboard": -2.1,
        "fx": -4.2,
        "studio": -5.0,
    }
    for path in paths:
        _, y, _ = read_wav(path)
        y = pad_or_trim(y, length)
        lname = path.name.lower()
        gain = -2.0
        for key, db in gains.items():
            if key in lname:
                gain = db
                break
        mix += y * float(amp_db(gain))
    mix = butter_filter(mix, sr, "highpass", 24, 2)
    mix = rbj_peaking(mix, sr, 250, -0.7, 0.95)
    mix = rbj_peaking(mix, sr, 620, -0.35, 1.0)
    mix = rbj_peaking(mix, sr, 3100, -0.55, 0.9)
    vocal_env = envelope(np.mean(lead, axis=1), sr, 80)
    active = np.clip((db_amp(vocal_env) + 38.0) / 14.0, 0.0, 1.0).astype(np.float32)
    pocket = rbj_peaking(rbj_peaking(mix, sr, 250, -1.0, 1.0), sr, 3100, -0.65, 0.9)
    mix = (mix * (1.0 - 0.55 * active[:, None]) + pocket * (0.55 * active[:, None])).astype(np.float32)
    p = peak(mix)
    if p > 0.88:
        mix *= 0.88 / (p + 1e-12)
    return mix.astype(np.float32)


def make_space(lead: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    mono = np.mean(lead, axis=1)
    delay_samp = int(round(0.255 * sr))
    delay = np.zeros_like(lead)
    delayed = np.roll(mono, delay_samp)
    delayed[:delay_samp] = 0.0
    delay[:, 0] = delayed * float(amp_db(-19.0))
    delay[:, 1] = np.roll(delayed, int(0.012 * sr)) * float(amp_db(-19.5))
    delay = butter_filter(delay, sr, "highpass", 280, 2)
    delay = butter_filter(delay, sr, "lowpass", 6500, 2)
    verb = np.zeros_like(lead)
    taps = [(0.045, -25.0), (0.071, -28.0), (0.115, -31.0), (0.18, -34.0)]
    for seconds, gain_db in taps:
        d = int(round(seconds * sr))
        tap = np.roll(mono, d)
        tap[:d] = 0.0
        verb[:, 0] += tap * float(amp_db(gain_db))
        verb[:, 1] += np.roll(tap, int(0.006 * sr)) * float(amp_db(gain_db - 0.4))
    verb = butter_filter(verb, sr, "highpass", 320, 2)
    verb = butter_filter(verb, sr, "lowpass", 7600, 2)
    return verb.astype(np.float32), delay.astype(np.float32)


def write_processed(stems: dict[str, Any]) -> dict[str, Path]:
    sr, lead_raw, _ = read_wav(stems["lead"])
    length = len(lead_raw)
    full_sr, full, _ = read_wav(stems["full"])
    if full_sr != sr:
        raise RuntimeError("Sample-rate mismatch")
    full = pad_or_trim(full, length)
    lead_before = force_mono_center(lead_raw)
    lead_after = process_lead(lead_raw, sr)
    backing_side = np.zeros_like(lead_after)
    backing_mono = np.zeros_like(lead_after)
    if stems.get("backing"):
        _, backing_raw, _ = read_wav(stems["backing"])
        backing_side, backing_mono = process_backing(backing_raw, sr, length)
    music = process_music(stems["music"], sr, length, lead_after)
    verb, delay = make_space(lead_after, sr)
    vocal_solo = lead_after * float(amp_db(0.4)) + backing_side + verb + delay
    prefinal = music + lead_after * float(amp_db(1.8)) + backing_side + verb + delay
    p = peak(prefinal)
    if p > 0.92:
        prefinal *= 0.92 / (p + 1e-12)
    paths = {
        "lead_before": PROCESSED / "lead_vocal_before.wav",
        "lead_after": PROCESSED / "lead_vocal_clarity_processed.wav",
        "backing_side": PROCESSED / "backing_vocal_side_support.wav",
        "backing_mono": PROCESSED / "backing_vocal_mono_reference.wav",
        "music": PROCESSED / "instrumental_vocal_pocket.wav",
        "verb": PROCESSED / "vocal_reverb_send_print.wav",
        "delay": PROCESSED / "vocal_delay_send_print.wav",
        "vocal_solo": VOCAL_SOLO,
        "prefinal_python": PREFINAL,
        "source_full": PROCESSED / "source_full_mix_reference.wav",
    }
    for key, path in paths.items():
        if key == "lead_before":
            write_wav(path, sr, lead_before)
        elif key == "lead_after":
            write_wav(path, sr, lead_after)
        elif key == "backing_side":
            write_wav(path, sr, backing_side)
        elif key == "backing_mono":
            write_wav(path, sr, backing_mono)
        elif key == "music":
            write_wav(path, sr, music)
        elif key == "verb":
            write_wav(path, sr, verb)
        elif key == "delay":
            write_wav(path, sr, delay)
        elif key == "vocal_solo":
            write_wav(path, sr, vocal_solo)
        elif key == "prefinal_python":
            write_wav(path, sr, prefinal)
        elif key == "source_full":
            write_wav(path, sr, full)
    return paths


def write_analysis(paths: dict[str, Path]) -> dict[str, Any]:
    before = audio_metrics(paths["lead_before"], "lead_vocal_before")
    after = audio_metrics(paths["lead_after"], "lead_vocal_after_printed_dsp")
    def verdict() -> str:
        if after["mud_180_350_pct"] < before["mud_180_350_pct"] and after["presence_2000_5000_pct"] >= before["presence_2000_5000_pct"] * 0.98:
            return "Vocal_Clear_Forward"
        return "Vocal_DeMud_Only"
    report = {
        "source": rel(paths["lead_before"]),
        "processed": rel(paths["lead_after"]),
        "before": before,
        "after": after,
        "recommended_preset": verdict(),
        "diagnosis": {
            "sub_80_unneeded": before["sub_20_80_pct"] > 0.4,
            "mud_180_350_excess": before["mud_180_350_pct"] > 5.0,
            "box_350_800_excess": before["box_350_800_pct"] > 18.0,
            "presence_state": "controlled/forward" if after["presence_2000_5000_pct"] >= before["presence_2000_5000_pct"] * 0.98 else "may still need presence",
            "sibilance_risk": after["sibilance_6000_9000_pct"] > before["sibilance_6000_9000_pct"] * 1.2,
            "air_fizz_risk": after["fizz_14000_18000_pct"] > before["fizz_14000_18000_pct"] * 1.2,
            "stereo_width_excess": after["side_mid_db"] > -12.0,
            "likely_backward_causes": ["low-mid mud", "instrumental 250/600/3k masking", "printed ambience"] ,
        },
    }
    ANALYSIS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Vocal Analysis Report",
        "",
        f"- Source: `{report['source']}`",
        f"- Processed DSP print: `{report['processed']}`",
        f"- Recommended preset: `{report['recommended_preset']}`",
        "",
        "| metric | before | after |",
        "| --- | ---: | ---: |",
    ]
    for key in ["integrated_lufs", "true_peak_dbfs", "peak_dbfs", "rms_dbfs", "sub_20_80_pct", "mud_180_350_pct", "box_350_800_pct", "presence_2000_5000_pct", "sibilance_6000_9000_pct", "air_9000_14000_pct", "fizz_14000_18000_pct", "side_mid_db", "stereo_corr"]:
        lines.append(f"| {key} | {before.get(key)} | {after.get(key)} |")
    lines.extend([
        "",
        "## Diagnosis",
        "",
        "- The repair focuses on 180-350 Hz and 450-800 Hz cleanup first, then a guarded 3.2 kHz presence lift.",
        "- Air was kept minimal; 10 kHz+ is guarded so AI fizz is not exaggerated.",
        "- Lead remains mono center before REAPER and in the REAPER project.",
    ])
    ANALYSIS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def lua_quote(path: Path) -> str:
    return "[[" + str(path).replace("]", "] ]") + "]]"


def write_reaper_scripts(paths: dict[str, Path], duration: float) -> None:
    build = f'''local root = [[{ROOT}]]
local rpp = [[{RPP}]]
local render_dir = [[{RENDERS}]]
local trace_path = [[{TRACE_JSON}]]
local log_path = [[{REPORTS / "build_reaper.log"}]]
local rows = {{}}
local function q(s) return string.format("%q", s) end
local function lin(db) return 10 ^ ((db or 0) / 20) end
local function esc(s) s=tostring(s or ""); return s:gsub("\\\\","\\\\\\\\"):gsub('"','\\\\"'):gsub("\\n","\\\\n") end
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
local function add_row(track, stage, status, plugin, idx, wet, reason)
  rows[#rows+1]=string.format('{{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":%s,"reason":"%s"}}', esc(track), esc(stage), esc(status), esc(plugin), tonumber(idx or -1), wet and tostring(wet) or "null", esc(reason))
  log(track .. " | " .. stage .. " | " .. status .. " | " .. tostring(plugin))
end
local function write_trace()
  local f=assert(io.open(trace_path,"w"))
  f:write('{{\\n  "slug": "{SLUG}",\\n  "rows": [\\n')
  for i,row in ipairs(rows) do f:write("    " .. row .. (i == #rows and "\\n" or ",\\n")) end
  f:write("  ]\\n}}\\n"); f:close()
end
local function make_track(name, db, pan, mute)
  local idx=reaper.CountTracks(0); reaper.InsertTrackAtIndex(idx,true)
  local tr=reaper.GetTrack(0,idx)
  reaper.GetSetMediaTrackInfo_String(tr,"P_NAME",name,true)
  reaper.SetMediaTrackInfo_Value(tr,"D_VOL",lin(db or 0))
  reaper.SetMediaTrackInfo_Value(tr,"D_PAN",pan or 0)
  reaper.SetMediaTrackInfo_Value(tr,"B_MUTE",mute and 1 or 0)
  return tr
end
local function insert_media(tr, path)
  local src=reaper.PCM_Source_CreateFromFile(path); if not src then error("source failed " .. path) end
  local item=reaper.AddMediaItemToTrack(tr); local take=reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item,"D_POSITION",0)
  reaper.SetMediaItemInfo_Value(item,"D_LENGTH",reaper.GetMediaSourceLength(src))
end
local function add_fx(tr, label, stage, candidates, wet, reason)
  for _,name in ipairs(candidates) do
    local idx=reaper.TrackFX_AddByName(tr,name,false,-1)
    if idx and idx >= 0 then
      if wet and reaper.TrackFX_SetWetDryMix then pcall(reaper.TrackFX_SetWetDryMix,tr,idx,wet,0,0) end
      add_row(label,stage,"loaded",name,idx,wet,reason); return idx,name
    end
  end
  add_row(label,stage,"missing_all_candidates",table.concat(candidates," | "),-1,wet,reason); return -1,nil
end
local function add_required(tr,label,stage,name,wet,reason)
  local idx,loaded=add_fx(tr,label,stage,{{name}},wet,reason)
  if idx < 0 or loaded ~= name then write_trace(); error("required FX missing " .. name) end
  return idx
end
local function send(src,dst,db) local s=reaper.CreateTrackSend(src,dst); reaper.SetTrackSendInfo_Value(src,0,s,"D_VOL",lin(db or 0)); return s end
os.execute("mkdir -p " .. q(render_dir)); os.execute("mkdir -p " .. q([[{REPORTS}]])); os.remove(log_path); os.remove(trace_path)
reaper.Main_OnCommand(40023,0)
local ref=make_track("SOURCE full mix reference muted",-99,0,true); insert_media(ref,{lua_quote(paths["source_full"])})
local music=make_track("V37 INSTRUMENTAL BUS free EQ pocket",-1.1,0,false); insert_media(music,{lua_quote(paths["music"])})
local lead=make_track("V37 LEAD VOCAL CLARITY MAX GUARDED",-0.65,0,false); insert_media(lead,{lua_quote(paths["lead_after"])})
local backing=make_track("V37 BACKGROUND DOUBLE SUPPORT L/R",-7.2,0,false); insert_media(backing,{lua_quote(paths["backing_side"])})
local printed_verb=make_track("V37 PRINTED VOCAL REVERB SEND",-2.8,0,false); insert_media(printed_verb,{lua_quote(paths["verb"])})
local printed_delay=make_track("V37 PRINTED VOCAL DELAY SEND",-3.0,0,false); insert_media(printed_delay,{lua_quote(paths["delay"])})
local verb_return=make_track("V37 RETURN ReaVerbate dark send",-42,0,false)
local delay_return=make_track("V37 RETURN ReaDelay filtered throw",-43,0,false)
send(lead,verb_return,-45); send(lead,delay_return,-47)
add_fx(music,"music_bus","instrumental vocal pocket EQ",{{"VST: ReaEQ (Cockos)"}},1.0,"free EQ pocket at mud/presence masks")
add_fx(music,"music_bus","instrumental dynamic pocket",{{"VST3: TDR Nova (Tokyo Dawn Labs)","VST: ReaXcomp (Cockos)"}},0.82,"free dynamic EQ instead of Ozone")
add_required(lead,"vocal_anchor","Codex Suno/AI artifact tamer FIRST SLOT clarity","JS: Codex Vocal AI Artifact Split Tamer",1.0,"mandatory Mesi first-slot clean vocal guard")
add_fx(lead,"vocal_anchor","corrective EQ HPF de-mud box presence",{{"VST: ReaEQ (Cockos)"}},1.0,"HPF, de-mud, box control, guarded presence")
add_fx(lead,"vocal_anchor","Vocal Clarity De-Mud Dynamic EQ JSFX",{{"JS: Vocal Clarity De-Mud Dynamic EQ"}},1.0,"project JSFX for dynamic 180-350 Hz cleanup")
add_fx(lead,"vocal_anchor","TDR Nova dynamic presence/fizz guard",{{"VST3: TDR Nova (Tokyo Dawn Labs)","VST: ReaEQ (Cockos)"}},1.0,"free dynamic EQ, no paid iZotope")
add_fx(lead,"vocal_anchor","primary de-esser",{{"JS: De-esser","VST3: TDR Nova (Tokyo Dawn Labs)"}},1.0,"6-9 kHz consonant control")
add_fx(lead,"vocal_anchor","Vocal Clarity Presence Enhancer JSFX",{{"JS: Vocal Clarity Presence Enhancer"}},0.66,"guarded articulation enhancer")
add_fx(lead,"vocal_anchor","light clean compression",{{"VST: ReaComp (Cockos)"}},0.38,"lighter clean leveling to avoid blur")
add_fx(lead,"vocal_anchor","weak OTT density only",{{"VST3: OTT (Xfer Records)","VST: OTT (Xfer Records)"}},0.06,"very weak density; not strong OTT")
add_fx(lead,"vocal_anchor","Vocal Clarity Air Guard JSFX",{{"JS: Vocal Clarity Air Guard"}},0.90,"stronger air/fizz guard instead of blind air boost")
add_required(lead,"vocal_anchor","post OTT Codex Suno/AI artifact guard clarity","JS: Codex Vocal AI Artifact Split Tamer",1.0,"post-density AI fizz guard")
add_fx(lead,"vocal_anchor","Vocal Clarity Output Guard JSFX",{{"JS: Vocal Clarity Output Guard"}},1.0,"output peak guard")
add_fx(backing,"background_double","support EQ",{{"VST: ReaEQ (Cockos)"}},1.0,"keep doubles tucked")
add_fx(backing,"background_double","support de-esser",{{"JS: De-esser","VST3: TDR Nova (Tokyo Dawn Labs)"}},1.0,"avoid side sibilance")
add_fx(printed_verb,"printed_reverb","printed reverb dark EQ",{{"VST: ReaEQ (Cockos)"}},1.0,"low cut/high cut so reverb does not cloud words")
add_fx(printed_delay,"printed_delay","printed delay dark EQ",{{"VST: ReaEQ (Cockos)"}},1.0,"filtered throw behind vocal")
add_fx(verb_return,"reverb_return","stock reverb send",{{"VST: ReaVerbate (Cockos)","VST: ReaVerbate (Cockos)"}},0.36,"short tucked reverb send")
add_fx(verb_return,"reverb_return","reverb low/high cut",{{"VST: ReaEQ (Cockos)"}},1.0,"250-350 Hz low cut, 7-9 kHz high cut target")
add_fx(delay_return,"delay_return","stock delay send",{{"VST: ReaDelay (Cockos)","ReaDelay (Cockos)"}},0.34,"filtered phrase-end style delay")
add_fx(delay_return,"delay_return","delay low/high cut",{{"VST: ReaEQ (Cockos)"}},1.0,"delay behind vocal")
local master=reaper.GetMasterTrack(0)
add_fx(master,"master","master free tonal EQ",{{"VST: ReaEQ (Cockos)"}},1.0,"no Ozone or paid iZotope")
add_fx(master,"master","master dynamic guard",{{"VST3: TDR Nova (Tokyo Dawn Labs)","VST: ReaXcomp (Cockos)"}},0.82,"low-mid/fizz guard")
add_fx(master,"master","master clean limiter",{{"VST: ReaLimit (Cockos)","VST: Event Horizon Limiter/Clipper"}},1.0,"clean ceiling, no saturation")
reaper.GetSetProjectInfo(0,"RENDER_SETTINGS",0,true)
reaper.GetSetProjectInfo(0,"RENDER_BOUNDSFLAG",2,true)
reaper.GetSetProjectInfo(0,"RENDER_SRATE",48000,true)
reaper.GetSetProjectInfo(0,"RENDER_CHANNELS",2,true)
reaper.GetSetProjectInfo(0,"RENDER_STARTPOS",0,true)
reaper.GetSetProjectInfo(0,"RENDER_ENDPOS",{duration:.6f},true)
reaper.GetSetProjectInfo_String(0,"RENDER_FILE",render_dir,true)
reaper.GetSetProjectInfo_String(0,"RENDER_PATTERN","VOCAL_CLARITY_PASS01_REAPERPRINT_FULL_24-48",true)
reaper.GetSetProjectInfo_String(0,"RENDER_FORMAT","evaw",true)
reaper.GetSetProjectInfo_String(0,"PROJECT_NOTES","v37 vocal clarity final: free/stock/TDR chain, no Antares, no Ozone, no paid iZotope, no broad widening. Lead vocal is mono center with mandatory Codex first slot, de-mud, presence, de-ess, light ReaComp, weak OTT, air guard, post Codex guard.",true)
reaper.Main_SaveProjectEx(0,rpp,0)
write_trace()
log("wrapper ok")
reaper.defer(function() reaper.Main_OnCommand(40004,0) end)
'''
    render = f'''local rpp = [[{RPP}]]
local render_dir = [[{RENDERS}]]
local log_path = [[{REPORTS / "render_prepare.log"}]]
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
os.remove(log_path)
local ok,err=xpcall(function()
  reaper.Main_openProject(rpp)
  reaper.GetSetProjectInfo_String(0,"RENDER_FILE",render_dir,true)
  reaper.GetSetProjectInfo_String(0,"RENDER_PATTERN","VOCAL_CLARITY_PASS01_REAPERPRINT_FULL_24-48",true)
  reaper.Main_SaveProjectEx(0,rpp,0)
  log("wrapper ok")
end, debug.traceback)
if not ok then log("wrapper error: " .. tostring(err)) end
reaper.defer(function() reaper.Main_OnCommand(40004,0) end)
'''
    BUILD_LUA.write_text(build, encoding="utf-8")
    RUN_BUILD_LUA.write_text(f"dofile([[{BUILD_LUA}]])\n", encoding="utf-8")
    RENDER_LUA.write_text(render, encoding="utf-8")
    RUN_RENDER_LUA.write_text(f"dofile([[{RENDER_LUA}]])\n", encoding="utf-8")
    shutil.copy2(BUILD_LUA, SYSTEM / "scripts" / "apply_vocal_clarity_chain.lua")
    shutil.copy2(RENDER_LUA, SYSTEM / "scripts" / "render_vocal_clarity_pass.lua")


def run_reaper() -> None:
    if not REAPER_BIN.exists():
        raise FileNotFoundError(REAPER_BIN)
    REAPER_PRINT.unlink(missing_ok=True)
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_BUILD_LUA)], check=True)
    build_log = REPORTS / "build_reaper.log"
    if build_log.exists() and "wrapper ok" not in build_log.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"REAPER build wrapper failed: {build_log}")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_RENDER_LUA)], check=True)
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(RPP)], check=True)
    if not REAPER_PRINT.exists():
        matches = sorted(RENDERS.glob("VOCAL_CLARITY_PASS01_REAPERPRINT_FULL_24-48*.wav"))
        if matches:
            matches[-1].rename(REAPER_PRINT)
    if not REAPER_PRINT.exists():
        raise FileNotFoundError(REAPER_PRINT)


def final_master() -> None:
    # Clean final ceiling; no compressor/saturation/paid chain.
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(REAPER_PRINT),
            "-af",
            "highpass=f=24,loudnorm=I=-9.2:TP=-1.2:LRA=4.0,alimiter=limit=0.86:attack=2:release=80:level=false",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(FINAL_WAV),
        ],
        check=True,
    )
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(FINAL_MP3)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-t", "15", str(RENDERS / "_after15.wav")], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(PROCESSED / "source_full_mix_reference.wav"), "-t", "15", str(RENDERS / "_before15.wav")], check=True)
    concat = RENDERS / "_ab_concat.txt"
    concat.write_text(f"file '{RENDERS / '_before15.wav'}'\nfile '{RENDERS / '_after15.wav'}'\n", encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "pcm_s24le", str(AB_PREVIEW)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(AB_PREVIEW), "-c:a", "libmp3lame", "-b:a", "320k", str(AB_PREVIEW_MP3)], check=True)
    for temp in [RENDERS / "_after15.wav", RENDERS / "_before15.wav", concat]:
        temp.unlink(missing_ok=True)


def write_trace_md() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    lines = ["# Actual REAPER Plugin Trace", "", "| track | fx | status | plugin | wet | stage |", "| --- | ---: | --- | --- | ---: | --- |"]
    for row in payload.get("rows", []):
        lines.append(f"| {row.get('track')} | {row.get('fx_index')} | {row.get('status')} | {row.get('plugin')} | {row.get('wet')} | {row.get('stage')} |")
    TRACE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_gate() -> None:
    subprocess.run(["python3", "tools/validate_reaper_vocal_chain_gate.py", "--trace", rel(TRACE_JSON)], cwd=ROOT, check=True)


def write_qc(analysis: dict[str, Any]) -> dict[str, Any]:
    rows = [
        audio_metrics(PROCESSED / "lead_vocal_before.wav", "lead_vocal_before"),
        audio_metrics(PROCESSED / "lead_vocal_clarity_processed.wav", "lead_vocal_after_printed_dsp"),
        audio_metrics(REAPER_PRINT, "reaper_full_mix_print"),
        audio_metrics(FINAL_WAV, "final_master_wav"),
        audio_metrics(FINAL_MP3, "final_master_mp3"),
        audio_metrics(VOCAL_SOLO, "vocal_solo"),
    ]
    before, after = rows[0], rows[1]
    trace = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    plugin_text = " ".join(str(row.get("plugin", "")) for row in trace.get("rows", [])).lower()
    pass_items = {
        "mud_reduced": after["mud_180_350_pct"] < before["mud_180_350_pct"],
        "presence_not_lost": after["presence_2000_5000_pct"] >= before["presence_2000_5000_pct"] * 0.98,
        "sibilance_safe": after["sibilance_6000_9000_pct"] <= before["sibilance_6000_9000_pct"] * 1.15,
        "fizz_safe": after["fizz_14000_18000_pct"] <= before["fizz_14000_18000_pct"] * 1.2 + 0.05,
        "lead_center": after["side_mid_db"] <= -120.0,
        "final_mp3_peak_safe": rows[4]["true_peak_dbfs"] is not None and rows[4]["true_peak_dbfs"] <= -0.8,
        "no_paid_izotope_or_antares": all(token not in plugin_text for token in ["ozone", "izotope", "antares", "auto-tune", "mautopitch", "reatune", "graillon"]),
    }
    payload = {"slug": SLUG, "rows": rows, "pass_items": pass_items, "passed": all(pass_items.values()), "analysis": analysis}
    QC_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (REPORTS / "v37_render_qc_metrics.csv").open("w", encoding="utf-8", newline="") as file:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Vocal Clarity QC Report",
        "",
        f"- Passed: `{payload['passed']}`",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- Vocal solo: `{rel(VOCAL_SOLO)}`",
        "",
        "## PASS Items",
        "",
    ]
    for key, value in pass_items.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Key Metrics", "", "| metric | before | after |", "| --- | ---: | ---: |"])
    for key in ["mud_180_350_pct", "box_350_800_pct", "presence_2000_5000_pct", "sibilance_6000_9000_pct", "air_9000_14000_pct", "fizz_14000_18000_pct", "side_mid_db"]:
        lines.append(f"| {key} | {before.get(key)} | {after.get(key)} |")
    lines.extend([
        "",
        "## Notes",
        "",
        "- Printed DSP performs the audible de-mud/presence/air guard move before the REAPER chain.",
        "- The actual REAPER trace is reported separately; intended plugins are not mixed with actual loaded plugins.",
        "- Human A/B should check that the vocal did not become thin or AI-sharp.",
    ])
    QC_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_summary(qc: dict[str, Any]) -> None:
    trace_rows = json.loads(TRACE_JSON.read_text(encoding="utf-8")).get("rows", [])
    vocal_rows = [r for r in trace_rows if r.get("track") == "vocal_anchor"]
    lines = [
        "# Render Summary",
        "",
        f"- Slug: `{SLUG}`",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- Vocal solo: `{rel(VOCAL_SOLO)}`",
        f"- A/B preview WAV: `{rel(AB_PREVIEW)}`",
        f"- A/B preview MP3: `{rel(AB_PREVIEW_MP3)}`",
        f"- REAPER project: `{rel(RPP)}`",
        f"- ZIP: `{rel(ZIP_PATH)}`",
        "",
        "## Actual Vocal Chain",
        "",
    ]
    for row in sorted(vocal_rows, key=lambda r: int(r.get("fx_index", 999))):
        lines.append(f"- fx {row.get('fx_index')}: {row.get('plugin')} / wet {row.get('wet')} / {row.get('stage')}")
    lines.extend([
        "",
        "## Manual Final Adjustments",
        "",
        "- If vocal becomes thin, reduce the 250 Hz de-mud amount by 0.5-1.0 dB.",
        "- If consonants sting, lower the 3.2 kHz lift or increase de-ess by 0.5-1.0 dB.",
        "- If AI fizz appears, disable air shelf and keep the air guard stronger.",
        "- If vocal feels behind the beat, lower reverb/delay send by 1-2 dB before raising lead gain.",
    ])
    RENDER_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORTS / "mesi_1_v37_vocal_clarity_max_guarded_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "slug": SLUG,
        "final_wav": str(FINAL_WAV),
        "final_mp3": str(FINAL_MP3),
        "vocal_solo": str(VOCAL_SOLO),
        "ab_preview": str(AB_PREVIEW),
        "ab_preview_mp3": str(AB_PREVIEW_MP3),
        "zip": str(ZIP_PATH),
        "qc_passed": qc["passed"],
    }
    (REPORTS / "delivery_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_zip() -> None:
    ZIP_PATH.unlink(missing_ok=True)
    include = [
        FINAL_WAV,
        FINAL_MP3,
        VOCAL_SOLO,
        AB_PREVIEW,
        AB_PREVIEW_MP3,
        REAPER_PRINT,
        RPP,
        TRACE_JSON,
        TRACE_MD,
        ANALYSIS_JSON,
        ANALYSIS_MD,
        QC_JSON,
        QC_MD,
        RENDER_SUMMARY,
        REPORTS / "source_selection.json",
        REPORTS / "delivery_manifest.json",
        REPORTS / "mesi_1_v37_vocal_clarity_max_guarded_report.md",
    ]
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in include:
            if path.exists():
                archive.write(path, rel(path))


def generate_fx_chains() -> None:
    subprocess.run(["python3", str(SYSTEM / "scripts" / "generate_reaper_fx_chains.py")], check=True)


def analyze_only(path: Path) -> None:
    ensure_dirs()
    sr, y, _ = read_wav(path)
    before = PROCESSED / "lead_vocal_before.wav"
    after = PROCESSED / "lead_vocal_clarity_processed.wav"
    write_wav(before, sr, force_mono_center(y))
    write_wav(after, sr, process_lead(y, sr))
    write_analysis({"lead_before": before, "lead_after": after})
    print(ANALYSIS_MD)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze-only", type=Path)
    args = parser.parse_args()
    ensure_dirs()
    # Keep the hand-authored VOCAL_CLARITY_REPAIR_SYSTEM files intact.
    # write_text_files() only emits compatibility placeholders from the older v36 generator.
    generate_fx_chains()
    install_jsfx()
    if args.analyze_only:
        analyze_only(args.analyze_only)
        return
    stems = extract_source()
    processed_paths = write_processed(stems)
    analysis = write_analysis(processed_paths)
    duration = audio_metrics(processed_paths["lead_after"], "lead_after")["duration_s"]
    write_reaper_scripts(processed_paths, float(duration))
    run_reaper()
    final_master()
    write_trace_md()
    run_gate()
    qc = write_qc(analysis)
    write_summary(qc)
    make_zip()
    subprocess.run(["unzip", "-t", str(ZIP_PATH)], check=True, stdout=subprocess.PIPE)
    print(json.dumps({"slug": SLUG, "final_wav": rel(FINAL_WAV), "final_mp3": rel(FINAL_MP3), "vocal_solo": rel(VOCAL_SOLO), "zip": rel(ZIP_PATH), "qc_passed": qc["passed"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
