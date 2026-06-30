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
SLUG = "jo_mix_master_v18_center_male_rebuild"
AUDIO_WORK = PROJECT_ROOT / "audio_work" / SLUG
REAPER_DIR = PROJECT_ROOT / "reaper" / SLUG
RENDER_DIR = PROJECT_ROOT / "renders" / SLUG
REPORT_DIR = PROJECT_ROOT / "reports" / SLUG
RPP = REAPER_DIR / "jo_mix_master_v18_center_male_rebuild.rpp"
REAPER_RENDER = RENDER_DIR / "jo_mix_master_v18_REAPERPRINT_center_male_rebuild_24-48.wav"
FINAL_24 = RENDER_DIR / f"{SLUG}_FINAL_REAPER_24bit_48k.wav"
FINAL_16 = RENDER_DIR / f"{SLUG}_FINAL_REAPER_16bit_44k.wav"
FINAL_MP3 = RENDER_DIR / f"{SLUG}_FINAL_REAPER_320k.mp3"
PREVIEW_M4A = RENDER_DIR / f"{SLUG}_FINAL_REAPER_preview_256k.m4a"
ZIP_PATH = RENDER_DIR / f"{SLUG}_DELIVERY_PACKAGE.zip"
TRACE = REPORT_DIR / "actual_reaper_plugin_trace.json"
QC_JSON = REPORT_DIR / f"{SLUG}_qc_report.json"
QC_MD = REPORT_DIR / f"{SLUG}_qc_report.md"
CUM_JSON = REPORT_DIR / f"{SLUG}_cumulative_qc_summary.json"
CUM_MD = REPORT_DIR / f"{SLUG}_cumulative_qc_summary.md"

HELPER_PATH = PROJECT_ROOT / "scripts" / "jo_mix_master_v10" / "process_jo_mix_master_v10.py"
FINAL_TARGET_LUFS = -8.2
FINAL_CEILING_DBTP = -1.2
FINAL_SIDE_GAIN = 1.08

MALE_SCHEDULE = [
    (0.0, 15.0, -80.0),
    (15.0, 34.0, 8.2),
    (34.0, 80.0, 7.6),
    (80.0, 88.0, -80.0),
    (88.0, 92.0, -80.0),
    (92.0, 128.416, -80.0),
]
MALE_RESIDUAL_HOOK_SCHEDULE = [
    (0.0, 15.0, 10.0),
    (80.0, 88.0, 13.6),
    (88.0, 92.0, 11.0),
    (92.0, 128.416, 12.7),
]
MALE_LOWMID_SUPPORT_SCHEDULE = [
    (0.0, 15.0, -80.0),
    (15.0, 80.0, -80.0),
    (80.0, 88.0, 8.0),
    (88.0, 92.0, -80.0),
    (92.0, 128.416, 5.9),
]
FEMALE_L_SCHEDULE = [
    (0.0, 15.0, 8.0),
    (15.0, 34.0, 6.0),
    (34.0, 80.0, 7.6),
    (80.0, 88.0, 14.0),
    (88.0, 92.0, 25.0),
    (92.0, 128.416, 8.8),
]
FEMALE_R_SCHEDULE = [
    (0.0, 15.0, 7.7),
    (15.0, 34.0, 5.7),
    (34.0, 80.0, 7.3),
    (80.0, 88.0, 13.7),
    (88.0, 92.0, 24.7),
    (92.0, 128.416, 8.5),
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
        female_l_db = rms_db(female_bus[a:b, 0])
        female_r_db = rms_db(female_bus[a:b, 1])
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
            "female_l_dbFS": round(female_l_db, 3),
            "female_r_dbFS": round(female_r_db, 3),
            "female_lr_delta_db": round(female_l_db - female_r_db, 3),
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


def maybe_make_mp3() -> str | None:
    afconvert = shutil.which("afconvert")
    if not afconvert:
        return None
    cmd = [afconvert, "-f", "MPG3", "-d", ".mp3", "-b", "320000", str(FINAL_24), str(FINAL_MP3)]
    subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return str(FINAL_MP3) if FINAL_MP3.exists() else None


def apply_ms_width(audio: np.ndarray, side_gain: float) -> np.ndarray:
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5 * side_gain
    widened = np.stack([mid + side, mid - side], axis=1).astype(np.float32)
    peak = float(np.max(np.abs(widened)) + 1.0e-12)
    if peak > 0.98:
        widened *= 0.98 / peak
    return widened.astype(np.float32)


def run_gate() -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "tools" / "validate_reaper_vocal_chain_gate.py"),
        "--trace",
        str(TRACE),
        "--script",
        str(REAPER_DIR / "build_jo_mix_master_v18_center_male_rebuild.lua"),
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
        "- Hook male lead is the derived full-mix residual rescue stem, not the high/female-like hook regions of 9 Vocals.wav.",
        "- 9 Vocals.wav stays as center support outside hooks; 8 Vocals.wav is panned L/R 75 and held behind the male.",
        "",
        "## Final REAPER Render",
        f"- WAV: `{payload['deliverables']['wav_24_48']}`",
        f"- Integrated LUFS estimate: {final['integrated_lufs']}",
        f"- True peak estimate dBTP: {final['true_peak_dbTP_est']}",
        f"- Sample peak dBFS: {final['sample_peak_dbFS']}",
        f"- Stereo correlation: {final['stereo_correlation']}",
        f"- Mono fold-down LUFS delta: {final['mono_fold_down_loudness_delta_db']}",
        f"- REAPER print LUFS: {reaper_print['integrated_lufs']}",
        f"- Final safety pass: {payload['final_loudness_pass']}",
        "",
        "## Vocal Role QC",
        "| Section | Male dBFS | Female mono dBFS | Male minus female | Female L | Female R | L-R |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for section, row in balance.items():
        lines.append(
            f"| {section} | {row['male_dbFS']} | {row['female_dbFS']} | {row['male_minus_female_db']} | {row['female_l_dbFS']} | {row['female_r_dbFS']} | {row['female_lr_delta_db']} |"
        )
    lines += [
        "",
        "## Plugin Gate",
        f"- Main vocal Suno/AI first-slot gate passed: {payload['plugin_gate'].get('passed')}",
        f"- Trace: `{payload['deliverables']['plugin_trace']}`",
        "",
        "## Pass Flags",
        f"- Overall QC passed: {payload['pass_flags']['overall_passed']}",
        f"- Flags: `{json.dumps(payload['pass_flags'], ensure_ascii=False)}`",
        "",
        "## Notes",
        "- Female layer is intentionally audible and panned L/R 75, but held below the male center main.",
        "- v18 uses UADx LA-2A/1176 where available, TDR Kotelnikov/Nova for light bus/master control, and no OTT.",
        "- The final WAV is the REAPER print through a measured true-peak/loudness safety pass, not an unmeasured brickwall push.",
        "- v18 keeps the suspected high/female-like 9-stem hook regions muted as male source, while 8 Vocals.wav is panned and kept roughly -5 dB from the main.",
        "- v18 derives that rescue from the supplied full mix after fitting/subtracting instruments plus the 8/9 vocal candidates; the raw full mix itself remains muted.",
        "- Delay/reverb support is a very tucked male-only phrase-end print, plus REAPER mix/master plugin processing.",
    ]
    QC_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cumulative_summary(payload: dict[str, Any]) -> None:
    final = payload["final_qc"]
    balance = payload["vocal_role_qc"]["section_balance"]
    summary = {
        "schema": "jo-mix-master-v18-cumulative-qc-summary",
        "created_at": payload["created_at"],
        "slug": SLUG,
        "user_feedback_locked_in": [
            "Male vocal must stay the main vocal from the front through the hooks.",
            "Latest feedback: female vocal must be panned L/R and about 5 dB lower than the centered male main, never leading.",
            "Hook regions previously sounded unchanged even after boosting 9 Vocals.wav, so 9 hook source identity had to stay de-prioritized for male rescue.",
            "Noise-lifting OTT/offline brickwall direction remains avoided after the v11 noise complaint.",
            "Final render must be an actual REAPER print, with the developed AI vocal artifact plugin first on lead vocal traces.",
        ],
        "v18_decision": {
            "root_cause": "Source audit showed the 9 Vocals.wav hook regions measured high/female-like; boosting them could not reveal a missing male hook.",
            "rescue_source": "Derived center male hook rescue from the supplied full mix residual after fitting/subtracting instruments and 8/9 vocal candidates.",
            "raw_full_mix_status": "Muted reference track only; master send disabled.",
            "hook_9_stem_status": "Muted in hook regions and retained only as non-hook center support.",
            "female_hook_status": "Hard-panned 8 Vocals.wav L/R assets are kept audible but about 5 dB under the male main where source exists.",
        },
        "measured_final_qc": {
            "integrated_lufs": final["integrated_lufs"],
            "true_peak_dbTP_est": final["true_peak_dbTP_est"],
            "sample_peak_dbFS": final["sample_peak_dbFS"],
            "stereo_correlation": final["stereo_correlation"],
            "l_minus_r_rms_db": final["l_minus_r_rms_db"],
        },
        "measured_vocal_role_qc": balance,
        "deliverables": payload["deliverables"],
    }
    CUM_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# {SLUG} Cumulative QC Summary",
        "",
        "## Locked Feedback",
    ]
    lines += [f"- {item}" for item in summary["user_feedback_locked_in"]]
    lines += [
        "",
        "## v18 Decision",
        f"- Root cause: {summary['v18_decision']['root_cause']}",
        f"- Rescue source: {summary['v18_decision']['rescue_source']}",
        f"- Raw full mix: {summary['v18_decision']['raw_full_mix_status']}",
        f"- 9 stem hook: {summary['v18_decision']['hook_9_stem_status']}",
        f"- Female hook: {summary['v18_decision']['female_hook_status']}",
        "",
        "## Final Metrics",
        f"- Integrated LUFS: {final['integrated_lufs']}",
        f"- True peak estimate dBTP: {final['true_peak_dbTP_est']}",
        f"- Sample peak dBFS: {final['sample_peak_dbFS']}",
        f"- Stereo correlation: {final['stereo_correlation']}",
        "",
        "## Hook Role Check",
        "| Section | Male dBFS | Female L | Female R | Male minus female mono |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for section in ("early_hook_0_15", "male_83s_boost", "pre_final_turn", "final_hook"):
        row = balance[section]
        lines.append(f"| {section} | {row['male_dbFS']} | {row['female_l_dbFS']} | {row['female_r_dbFS']} | {row['male_minus_female_db']} |")
    CUM_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def package(files: list[Path]) -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            if path.exists():
                zf.write(path, arcname=path.name)


def add_mono_fold_qc(helper: Any, final_qc: dict[str, Any], audio: np.ndarray, sr: int) -> None:
    mono = ((audio[:, 0] + audio[:, 1]) * 0.5).astype(np.float32)
    mono_stereo = np.repeat(mono[:, None], 2, axis=1)
    final_lufs = float(final_qc["integrated_lufs"])
    mono_lufs = round(helper.integrated_lufs(mono_stereo, sr), 3)
    final_qc["mono_fold_down_peak_dbFS"] = round(20.0 * math.log10(float(np.max(np.abs(mono))) + 1.0e-12), 3)
    final_qc["mono_fold_down_lufs"] = mono_lufs
    final_qc["mono_fold_down_loudness_delta_db"] = round(mono_lufs - final_lufs, 3)


def build_pass_flags(final_qc: dict[str, Any], role_qc: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    balance = role_qc["section_balance"]
    active_male_rows = [row for row in balance.values() if row["male_dbFS"] > -80.0]
    active_female_rows = [row for row in balance.values() if row["female_dbFS"] > -90.0]
    flags = {
        "integrated_lufs_target": -9.5 <= final_qc["integrated_lufs"] <= -8.8,
        "true_peak_safe": final_qc["true_peak_dbTP_est"] <= -1.2,
        "lr_balance": abs(final_qc["l_minus_r_rms_db"]) <= 0.5,
        "stereo_correlation_range": 0.35 <= final_qc["stereo_correlation"] <= 0.90,
        "male_active_segment_rms": all(row["male_dbFS"] >= -12.5 for row in active_male_rows),
        "female_below_male": all(row["male_minus_female_db"] >= 5.0 for row in active_female_rows),
        "harshness_proxy": final_qc["band_energy_share"]["harshness_2k5_6k"] <= 0.08,
        "mono_fold_down_safe_peak": final_qc["mono_fold_down_peak_dbFS"] <= final_qc["sample_peak_dbFS"] + 1.5,
        "plugin_gate": bool(gate.get("passed")),
        "limiter_gr_unavailable": None,
    }
    flags["overall_passed"] = all(value is True or value is None for value in flags.values())
    return flags


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

    widened_audio = apply_ms_width(reaper_audio, FINAL_SIDE_GAIN)
    final_audio, loudness_meta = helper.normalize_master(widened_audio, sr, FINAL_TARGET_LUFS, FINAL_CEILING_DBTP)
    final_loudness_pass = {
        "applied": True,
        "source": str(REAPER_RENDER),
        "method": "measured safety pass: mild M/S side gain, gain trim, soft clip/true-peak limiter",
        "ms_side_gain": FINAL_SIDE_GAIN,
        **loudness_meta,
    }
    write_pcm_wav(FINAL_24, final_audio, sr, 24)
    final_44 = helper.resample_audio(final_audio, sr, 44100)
    write_pcm_wav(FINAL_16, final_44, 44100, 16)
    mp3 = maybe_make_mp3()
    preview = maybe_make_preview()

    final_qc = helper.analyze_audio(final_audio, sr)
    final_qc.update(
        {
            "integrated_lufs": round(helper.integrated_lufs(final_audio, sr), 3),
            "true_peak_dbTP_est": round(helper.true_peak_db(final_audio, sr), 3),
            "lra_proxy": round(helper.lra_proxy(final_audio, sr), 3),
        }
    )
    add_mono_fold_qc(helper, final_qc, final_audio, sr)

    male_sr, male_asset = read_mono(AUDIO_WORK / "male_lead_center_role_asset.wav")
    residual_sr, residual_asset = read_mono(AUDIO_WORK / "male_hook_residual_rescue_center.wav")
    lowmid_sr, lowmid_asset = read_mono(AUDIO_WORK / "male_hook_lowmid_support_asset.wav")
    fl_sr, female_l = read_mono(AUDIO_WORK / "female_shadow_L_role_asset.wav")
    fr_sr, female_r = read_mono(AUDIO_WORK / "female_shadow_R_role_asset.wav")
    if len({male_sr, residual_sr, lowmid_sr, fl_sr, fr_sr}) != 1:
        raise RuntimeError("Role assets have mismatched sample rates")
    male_bus = scheduled_stereo(male_asset[:, None], male_sr, MALE_SCHEDULE, 0.0)
    male_bus += scheduled_stereo(residual_asset[:, None], residual_sr, MALE_RESIDUAL_HOOK_SCHEDULE, 0.0)
    male_bus += scheduled_stereo(lowmid_asset[:, None], lowmid_sr, MALE_LOWMID_SUPPORT_SCHEDULE, 0.0)
    female_bus = scheduled_stereo(female_l[:, None], fl_sr, FEMALE_L_SCHEDULE, -1.0)
    female_bus += scheduled_stereo(female_r[:, None], fr_sr, FEMALE_R_SCHEDULE, 1.0)
    role_qc = {
        "basis": "REAPER item/track gain schedule before plugin coloration; hook male uses residual rescue asset",
        "male_9_stem_non_hook_schedule_db": MALE_SCHEDULE,
        "male_residual_hook_schedule_db": MALE_RESIDUAL_HOOK_SCHEDULE,
        "male_lowmid_support_schedule_db": MALE_LOWMID_SUPPORT_SCHEDULE,
        "female_l_schedule_db": FEMALE_L_SCHEDULE,
        "female_r_schedule_db": FEMALE_R_SCHEDULE,
        "section_balance": section_balance(male_bus, female_bus, male_sr),
        "window_balance": helper.male_female_window_report(male_bus, female_bus, male_sr, target_margin_db=5.0, female_active_floor_db=-90.0),
    }

    gate = run_gate()
    pass_flags = build_pass_flags(final_qc, role_qc, gate)
    deliverables = {
        "reaper_project": str(RPP),
        "reaper_raw_render": str(REAPER_RENDER),
        "wav_24_48": str(FINAL_24),
        "wav_16_44": str(FINAL_16),
        "mp3_320": mp3,
        "preview_m4a": preview,
        "zip_package": str(ZIP_PATH),
        "plugin_trace": str(TRACE),
        "qc_json": str(QC_JSON),
        "qc_md": str(QC_MD),
        "cumulative_qc_json": str(CUM_JSON),
        "cumulative_qc_md": str(CUM_MD),
        "asset_report": str(REPORT_DIR / f"{SLUG}_asset_report.json"),
        "sha256_wav_24_48": sha256(FINAL_24),
    }
    payload = {
        "schema": "jo-mix-master-reaper-v18-qc",
        "created_at": now_utc(),
        "slug": SLUG,
        "rendered_through_reaper": True,
        "final_master_source": "actual REAPER print plus measured true-peak/loudness safety pass",
        "source_zip": "/Users/hantaeheuk/Downloads/ㅈㅇ.zip",
        "status": {
            "reference_matched": False,
            "reason_reference_matched_false": "No external lawful reference audio was supplied.",
            "human_ab_required_for_final_approval": True,
            "male_lead_role_locked": True,
            "female_layer_role_locked": True,
            "hook_male_source": "derived full-mix residual rescue, because 9 Vocals hook measured high/female-like in source audit",
            "female_lr_minus5_requested": True,
            "plugin_gate_passed": bool(gate.get("passed")),
        },
        "deliverables": deliverables,
        "final_qc": final_qc,
        "reaper_print_qc": reaper_print_qc,
        "final_loudness_pass": final_loudness_pass,
        "vocal_role_qc": role_qc,
        "plugin_gate": gate,
        "pass_flags": pass_flags,
    }
    QC_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(payload)
    write_cumulative_summary(payload)
    package(
        [
            FINAL_24,
            FINAL_16,
            FINAL_MP3,
            PREVIEW_M4A,
            RPP,
            QC_JSON,
            QC_MD,
            TRACE,
            REPORT_DIR / f"{SLUG}_asset_report.json",
            REPORT_DIR / f"{SLUG}_cumulative_qc_summary.json",
            REPORT_DIR / f"{SLUG}_cumulative_qc_summary.md",
            AUDIO_WORK / "DIAG_residual_male_hook_rescue_early_hook_0_15.wav",
            AUDIO_WORK / "DIAG_residual_male_hook_rescue_male_83s_80_88.wav",
            AUDIO_WORK / "DIAG_residual_male_hook_rescue_final_hook_92_end.wav",
            AUDIO_WORK / "DIAG_9_male_candidate_early_hook_0_15.wav",
            AUDIO_WORK / "DIAG_8_female_candidate_early_hook_0_15.wav",
            AUDIO_WORK / "DIAG_9_male_candidate_male_83s_80_88.wav",
            AUDIO_WORK / "DIAG_8_female_candidate_male_83s_80_88.wav",
            AUDIO_WORK / "DIAG_9_male_candidate_final_hook_92_end.wav",
            AUDIO_WORK / "DIAG_8_female_candidate_final_hook_92_end.wav",
            REAPER_DIR / "build_jo_mix_master_v18_center_male_rebuild.lua",
            REAPER_DIR / "render_jo_mix_master_v18_center_male_rebuild.lua",
        ]
    )
    payload["deliverables"]["zip_sha256"] = sha256(ZIP_PATH)
    QC_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(payload)
    write_cumulative_summary(payload)
    print(json.dumps({"ok": True, "deliverables": payload["deliverables"], "final_qc": final_qc, "plugin_gate": gate}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
