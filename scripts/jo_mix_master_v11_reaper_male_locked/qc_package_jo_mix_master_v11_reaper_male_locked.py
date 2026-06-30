#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import wave
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SLUG = "jo_mix_master_v11_reaper_male_locked"
AUDIO_WORK = PROJECT_ROOT / "audio_work" / SLUG
REAPER_DIR = PROJECT_ROOT / "reaper" / SLUG
RENDER_DIR = PROJECT_ROOT / "renders" / SLUG
REPORT_DIR = PROJECT_ROOT / "reports" / SLUG
RPP = REAPER_DIR / "jo_mix_master_v11_REAPER_MALE_LOCKED.rpp"
REAPER_RENDER = RENDER_DIR / "jo_mix_master_v11_REAPERPRINT_male_locked_24-48.wav"
FINAL_24 = RENDER_DIR / f"{SLUG}_FINAL_REAPER_24bit_48k.wav"
FINAL_16 = RENDER_DIR / f"{SLUG}_FINAL_REAPER_16bit_44k.wav"
PREVIEW_M4A = RENDER_DIR / f"{SLUG}_FINAL_REAPER_preview_256k.m4a"
ZIP_PATH = RENDER_DIR / f"{SLUG}_DELIVERY_PACKAGE.zip"
TRACE = REPORT_DIR / "actual_reaper_plugin_trace.json"
QC_JSON = REPORT_DIR / f"{SLUG}_qc_report.json"
QC_MD = REPORT_DIR / f"{SLUG}_qc_report.md"

HELPER_PATH = PROJECT_ROOT / "scripts" / "jo_mix_master_v10" / "process_jo_mix_master_v10.py"
FINAL_LIMITER_INTERNAL_TARGET_LUFS = -8.2
FINAL_LIMITER_MEASURED_GOAL_LUFS = -10.8

MALE_SCHEDULE = [
    (0.0, 15.0, 1.6 + 3.0),
    (15.0, 34.0, 1.6 + 2.0),
    (34.0, 80.0, 1.6 + 1.8),
    (80.0, 88.0, 1.6 + 3.7),
    (88.0, 92.0, 1.6 + 2.3),
    (92.0, 128.416, 1.6 + 3.2),
]
FEMALE_SCHEDULE = [
    (0.0, 15.0, -15.5 - 7.5),
    (15.0, 34.0, -15.5 - 4.5),
    (34.0, 80.0, -15.5 - 1.8),
    (80.0, 88.0, -15.5 - 7.5),
    (88.0, 92.0, -15.5 - 6.0),
    (92.0, 128.416, -15.5 - 8.5),
]
SECTION_WINDOWS = {
    "early_hook_0_15": (0.0, 15.0),
    "post_15_support": (15.0, 34.0),
    "middle_verse": (34.0, 80.0),
    "male_83s_boost": (80.0, 88.0),
    "pre_final_turn": (88.0, 92.0),
    "final_hook": (92.0, 128.416),
}


def load_helper():
    spec = importlib.util.spec_from_file_location("jo_mix_master_v10_helper", HELPER_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not import helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db_to_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(str(path))
    data = np.asarray(data)
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float32)
    else:
        info = np.iinfo(data.dtype)
        audio = data.astype(np.float32) / float(max(abs(info.min), abs(info.max)))
    if audio.ndim == 1:
        audio = audio[:, None]
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if audio.shape[1] > 2:
        audio = audio[:, :2]
    return int(sr), np.nan_to_num(audio.astype(np.float32))


def read_mono(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(str(path))
    data = np.asarray(data)
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float32)
    else:
        info = np.iinfo(data.dtype)
        audio = data.astype(np.float32) / float(max(abs(info.min), abs(info.max)))
    if audio.ndim > 1:
        audio = audio[:, 0]
    return int(sr), np.nan_to_num(audio.astype(np.float32))


def write_pcm_wav(path: Path, audio: np.ndarray, sr: int, bit_depth: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.clip(np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0), -1.0, 1.0)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(audio.shape[1])
        wf.setframerate(sr)
        if bit_depth == 24:
            wf.setsampwidth(3)
            scaled = np.round(audio * ((2**23) - 1)).astype(np.int32)
            packed = bytearray()
            for sample in scaled.reshape(-1):
                if sample < 0:
                    sample += 1 << 24
                packed.extend(int(sample).to_bytes(3, "little", signed=False))
            wf.writeframes(bytes(packed))
        elif bit_depth == 16:
            wf.setsampwidth(2)
            scaled = np.round(audio * ((2**15) - 1)).astype("<i2")
            wf.writeframes(scaled.tobytes())
        else:
            raise ValueError(f"Unsupported bit depth: {bit_depth}")


def scheduled_stereo(asset: np.ndarray, sr: int, schedule: list[tuple[float, float, float]], pan: float) -> np.ndarray:
    out = np.zeros((len(asset), 2), dtype=np.float32)
    mono = asset[:, 0] if asset.ndim == 2 else asset
    for start, end, db in schedule:
        a = max(0, int(round(start * sr)))
        b = min(len(mono), int(round(end * sr)))
        if b <= a:
            continue
        chunk = mono[a:b] * db_to_gain(db)
        if pan <= -0.999:
            out[a:b, 0] += chunk
        elif pan >= 0.999:
            out[a:b, 1] += chunk
        else:
            out[a:b, 0] += chunk
            out[a:b, 1] += chunk
    return out


def rms_db(audio: np.ndarray) -> float:
    if audio.size == 0:
        return -120.0
    return float(20.0 * math.log10(float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))) + 1.0e-12)))


def mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float32)
    return audio.mean(axis=1).astype(np.float32)


def section_balance(male_bus: np.ndarray, female_bus: np.ndarray, sr: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, (start, end) in SECTION_WINDOWS.items():
        a = max(0, int(round(start * sr)))
        b = min(len(male_bus), int(round(end * sr)))
        m = mono(male_bus[a:b])
        f = mono(female_bus[a:b])
        mdb = rms_db(m)
        fdb = rms_db(f)
        corr = 0.0
        if b > a:
            l = female_bus[a:b, 0].astype(np.float64) - float(np.mean(female_bus[a:b, 0]))
            r = female_bus[a:b, 1].astype(np.float64) - float(np.mean(female_bus[a:b, 1]))
            corr = float(np.sum(l * r) / (math.sqrt(float(np.sum(l * l) * np.sum(r * r))) + 1.0e-20))
        result[name] = {
            "start_seconds": start,
            "end_seconds": round(b / sr, 3),
            "male_dbFS": round(mdb, 3),
            "female_dbFS": round(fdb, 3),
            "male_minus_female_db": round(mdb - fdb, 3),
            "female_stereo_correlation": round(corr, 6),
        }
    return result


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def maybe_make_preview() -> str | None:
    afconvert = shutil.which("afconvert")
    if not afconvert:
        return None
    cmd = [afconvert, "-f", "m4af", "-d", "aac", "-b", "256000", str(FINAL_24), str(PREVIEW_M4A)]
    subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return str(PREVIEW_M4A) if PREVIEW_M4A.exists() else None


def run_gate() -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "tools" / "validate_reaper_vocal_chain_gate.py"),
        "--trace",
        str(TRACE),
        "--script",
        str(REAPER_DIR / "build_jo_mix_master_v11_reaper_male_locked.lua"),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"passed": False, "raw_stdout": proc.stdout, "raw_stderr": proc.stderr}
    payload["returncode"] = proc.returncode
    return payload


def write_md(payload: dict[str, Any]) -> None:
    final = payload["final_qc"]
    reaper_print = payload["reaper_print_qc"]
    balance = payload["vocal_role_qc"]["section_balance"]
    lines = [
        f"# {SLUG} QC Report",
        "",
        "## Source Stance",
        "- Actual REAPER project/render pass; earlier offline-only route is not treated as this final.",
        "- Track 0 full mix is muted and master-send disabled in the REAPER session.",
        "- 9 Vocals.wav is the male center lead; 8 Vocals.wav is split into L/R female shadow layers only.",
        "",
        "## Final REAPER Render",
        f"- WAV: `{payload['deliverables']['wav_24_48']}`",
        f"- Integrated LUFS estimate: {final['integrated_lufs']}",
        f"- True peak estimate dBTP: {final['true_peak_dbTP_est']}",
        f"- Sample peak dBFS: {final['sample_peak_dbFS']}",
        f"- Stereo correlation: {final['stereo_correlation']}",
        f"- Source REAPER print LUFS before final brickwall pass: {reaper_print['integrated_lufs']}",
        "",
        "## Vocal Role QC",
        "| Section | Male dBFS | Female dBFS | Male minus female | Female corr |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for section, row in balance.items():
        lines.append(
            f"| {section} | {row['male_dbFS']} | {row['female_dbFS']} | {row['male_minus_female_db']} | {row['female_stereo_correlation']} |"
        )
    lines += [
        "",
        "## Plugin Gate",
        f"- Main vocal Suno/AI first-slot gate passed: {payload['plugin_gate'].get('passed')}",
        f"- Trace: `{payload['deliverables']['plugin_trace']}`",
        "",
        "## Notes",
        "- Female layer is intentionally low and panned; it is a double/harmony shadow, not a lead replacement.",
        "- Delay/reverb support is a tucked phrase-end print, plus REAPER mix/master plugin processing.",
    ]
    QC_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def package(files: list[Path]) -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            if path.exists():
                zf.write(path, arcname=path.name)


def main() -> int:
    if not REAPER_RENDER.exists():
        raise FileNotFoundError(REAPER_RENDER)
    helper = load_helper()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    sr, reaper_audio = read_wav(REAPER_RENDER)
    if sr != 48000:
        raise RuntimeError(f"Expected REAPER render at 48 kHz, got {sr}")
    reaper_print_qc = helper.analyze_audio(reaper_audio, sr)
    reaper_print_qc.update(
        {
            "integrated_lufs": round(helper.integrated_lufs(reaper_audio, sr), 3),
            "true_peak_dbTP_est": round(helper.true_peak_db(reaper_audio, sr), 3),
            "lra_proxy": round(helper.lra_proxy(reaper_audio, sr), 3),
        }
    )

    final_audio, final_loudness_pass = helper.normalize_master(
        reaper_audio,
        sr,
        target_lufs=FINAL_LIMITER_INTERNAL_TARGET_LUFS,
        ceiling_db=-1.0,
    )
    final_loudness_pass["measured_goal_lufs"] = FINAL_LIMITER_MEASURED_GOAL_LUFS
    final_loudness_pass["source"] = str(REAPER_RENDER)
    final_loudness_pass["method"] = "measured final brickwall/loudness pass from the actual REAPER print"
    write_pcm_wav(FINAL_24, final_audio, sr, 24)
    final_44 = helper.resample_audio(final_audio, sr, 44100)
    write_pcm_wav(FINAL_16, final_44, 44100, 16)
    preview = maybe_make_preview()

    final_qc = helper.analyze_audio(final_audio, sr)
    final_qc.update(
        {
            "integrated_lufs": round(helper.integrated_lufs(final_audio, sr), 3),
            "true_peak_dbTP_est": round(helper.true_peak_db(final_audio, sr), 3),
            "lra_proxy": round(helper.lra_proxy(final_audio, sr), 3),
        }
    )

    male_sr, male_asset = read_mono(AUDIO_WORK / "male_lead_center_role_asset.wav")
    fl_sr, female_l = read_mono(AUDIO_WORK / "female_shadow_L_role_asset.wav")
    fr_sr, female_r = read_mono(AUDIO_WORK / "female_shadow_R_role_asset.wav")
    if len({male_sr, fl_sr, fr_sr}) != 1:
        raise RuntimeError("Role assets have mismatched sample rates")
    male_bus = scheduled_stereo(male_asset[:, None], male_sr, MALE_SCHEDULE, 0.0)
    female_bus = scheduled_stereo(female_l[:, None], fl_sr, FEMALE_SCHEDULE, -1.0)
    female_bus += scheduled_stereo(female_r[:, None], fr_sr, FEMALE_SCHEDULE, 1.0)
    role_qc = {
        "basis": "REAPER item/track gain schedule before plugin coloration",
        "male_schedule_db": MALE_SCHEDULE,
        "female_schedule_db_per_side": FEMALE_SCHEDULE,
        "section_balance": section_balance(male_bus, female_bus, male_sr),
        "window_balance": helper.male_female_window_report(male_bus, female_bus, male_sr, target_margin_db=18.0, female_active_floor_db=-80.0),
    }

    gate = run_gate()
    deliverables = {
        "reaper_project": str(RPP),
        "reaper_raw_render": str(REAPER_RENDER),
        "wav_24_48": str(FINAL_24),
        "wav_16_44": str(FINAL_16),
        "preview_m4a": preview,
        "zip_package": str(ZIP_PATH),
        "plugin_trace": str(TRACE),
        "qc_json": str(QC_JSON),
        "qc_md": str(QC_MD),
        "asset_report": str(REPORT_DIR / f"{SLUG}_asset_report.json"),
        "sha256_wav_24_48": sha256(FINAL_24),
    }
    payload = {
        "schema": "jo-mix-master-reaper-v11-qc",
        "created_at": now_utc(),
        "slug": SLUG,
        "rendered_through_reaper": True,
        "final_master_source": "actual REAPER print plus measured final brickwall/loudness pass",
        "source_zip": "/Users/hantaeheuk/Downloads/ㅈㅇ.zip",
        "status": {
            "reference_matched": False,
            "reason_reference_matched_false": "No external lawful reference audio was supplied.",
            "human_ab_required_for_final_approval": True,
            "male_lead_role_locked": True,
            "female_layer_role_locked": True,
            "plugin_gate_passed": bool(gate.get("passed")),
        },
        "deliverables": deliverables,
        "final_qc": final_qc,
        "reaper_print_qc": reaper_print_qc,
        "final_loudness_pass": final_loudness_pass,
        "vocal_role_qc": role_qc,
        "plugin_gate": gate,
    }
    QC_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(payload)
    package(
        [
            FINAL_24,
            FINAL_16,
            PREVIEW_M4A,
            RPP,
            QC_JSON,
            QC_MD,
            TRACE,
            REPORT_DIR / f"{SLUG}_asset_report.json",
            REPORT_DIR / f"{SLUG}_cumulative_qc_summary.json",
            REPORT_DIR / f"{SLUG}_cumulative_qc_summary.md",
            REAPER_DIR / "build_jo_mix_master_v11_reaper_male_locked.lua",
            REAPER_DIR / "render_jo_mix_master_v11_reaper_male_locked.lua",
        ]
    )
    payload["deliverables"]["zip_sha256"] = sha256(ZIP_PATH)
    QC_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(payload)
    print(json.dumps({"ok": True, "deliverables": payload["deliverables"], "final_qc": final_qc, "plugin_gate": gate}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
