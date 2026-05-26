from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
REPORTS = ROOT / "reports"
RENDERS = ROOT / "renders"
REAPER = ROOT / "reaper"
PASS05_RPP = REAPER / "FRESH_MIX_MASTER_PASS_05_CLEAN_MELODY_FORWARD.rpp"
TECHNICAL_REFERENCE = Path("/Users/hantaeheuk/Downloads/발매곡 완성본/동반자살 완성본/동반자살 WAV.wav")


def db(value: float) -> float:
    if value <= 0:
        return -300.0
    return 20.0 * math.log10(value)


def to_float_audio(data: np.ndarray) -> np.ndarray:
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float64, copy=False)
    elif data.dtype == np.int16:
        audio = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        audio = data.astype(np.float64) / 2147483648.0
    else:
        audio = data.astype(np.float64) / float(np.iinfo(data.dtype).max)
    if audio.ndim == 1:
        audio = audio[:, None]
    return np.nan_to_num(audio)


def biquad_highpass(fs: int, f0: float, q: float):
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * q)
    cos_w0 = math.cos(w0)
    b0 = (1 + cos_w0) / 2
    b1 = -(1 + cos_w0)
    b2 = (1 + cos_w0) / 2
    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha
    return np.array([b0 / a0, b1 / a0, b2 / a0]), np.array([1.0, a1 / a0, a2 / a0])


def biquad_high_shelf(fs: int, f0: float, q: float, gain_db: float):
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * q)
    cos_w0 = math.cos(w0)
    sqrt_a = math.sqrt(a)
    b0 = a * ((a + 1) + (a - 1) * cos_w0 + 2 * sqrt_a * alpha)
    b1 = -2 * a * ((a - 1) + (a + 1) * cos_w0)
    b2 = a * ((a + 1) + (a - 1) * cos_w0 - 2 * sqrt_a * alpha)
    a0 = (a + 1) - (a - 1) * cos_w0 + 2 * sqrt_a * alpha
    a1 = 2 * ((a - 1) - (a + 1) * cos_w0)
    a2 = (a + 1) - (a - 1) * cos_w0 - 2 * sqrt_a * alpha
    return np.array([b0 / a0, b1 / a0, b2 / a0]), np.array([1.0, a1 / a0, a2 / a0])


def approximate_lufs(audio: np.ndarray, fs: int) -> float:
    b_hp, a_hp = biquad_highpass(fs, 38.0, 0.5)
    b_hs, a_hs = biquad_high_shelf(fs, 1681.974, 0.707, 4.0)
    weighted = signal.lfilter(b_hp, a_hp, audio, axis=0)
    weighted = signal.lfilter(b_hs, a_hs, weighted, axis=0)
    block = max(1, int(0.400 * fs))
    hop = max(1, int(0.100 * fs))
    energies = []
    for start in range(0, max(1, weighted.shape[0] - block + 1), hop):
        frame = weighted[start : start + block]
        if frame.shape[0] < block:
            break
        energy = float(np.mean(np.sum(frame * frame, axis=1)))
        if energy > 0:
            loud = -0.691 + 10 * math.log10(energy)
            if loud > -70.0:
                energies.append(energy)
    if not energies:
        return -300.0
    preliminary = -0.691 + 10 * math.log10(float(np.mean(energies)))
    gated = [e for e in energies if -0.691 + 10 * math.log10(e) > preliminary - 10.0]
    if not gated:
        gated = energies
    return -0.691 + 10 * math.log10(float(np.mean(gated)))


def estimate_lra(audio: np.ndarray, fs: int) -> float | None:
    block = max(1, int(3.0 * fs))
    hop = max(1, int(1.0 * fs))
    vals = []
    for start in range(0, max(1, audio.shape[0] - block + 1), hop):
        frame = audio[start : start + block]
        if frame.shape[0] < block:
            break
        rms = float(np.sqrt(np.mean(frame * frame)))
        if rms > 1e-8:
            vals.append(db(rms))
    if len(vals) < 4:
        return None
    return float(np.percentile(vals, 95) - np.percentile(vals, 10))


def read_audio(path: Path) -> tuple[int | None, np.ndarray | None]:
    if not path.exists():
        return None, None
    fs, data = wavfile.read(path)
    return int(fs), to_float_audio(data)


def analyze_wav(path: Path) -> dict[str, object]:
    fs, audio = read_audio(path)
    if fs is None or audio is None:
        return {"path": str(path), "exists": False}
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(audio * audio))) if audio.size else 0.0
    corr = None
    if audio.shape[1] >= 2:
        left = audio[:, 0]
        right = audio[:, 1]
        if np.std(left) > 1e-9 and np.std(right) > 1e-9:
            corr = float(np.corrcoef(left, right)[0, 1])
    return {
        "path": str(path),
        "exists": True,
        "sample_rate": fs,
        "channels": int(audio.shape[1]),
        "duration_s": round(audio.shape[0] / fs, 3),
        "sample_peak_dbfs": round(db(peak), 2),
        "rms_dbfs": round(db(rms), 2),
        "crest_db": round(db(peak) - db(rms), 2) if peak > 0 and rms > 0 else None,
        "clip_sample_count": int(np.sum(np.abs(audio) >= 0.999)),
        "approx_lufs_i": round(approximate_lufs(audio, fs), 2),
        "approx_lra_lu": round(estimate_lra(audio, fs) or 0.0, 2),
        "stereo_correlation": round(corr, 3) if corr is not None else None,
    }


def band_rms(audio: np.ndarray, fs: int, low: float, high: float) -> float:
    nyq = fs * 0.5
    if high >= nyq:
        sos = signal.butter(4, low / nyq, btype="highpass", output="sos")
    else:
        sos = signal.butter(4, [low / nyq, high / nyq], btype="bandpass", output="sos")
    filtered = signal.sosfilt(sos, audio, axis=0)
    return db(float(np.sqrt(np.mean(filtered * filtered))))


def band_profile(path: Path) -> dict[str, object]:
    fs, audio = read_audio(path)
    if fs is None or audio is None:
        return {"exists": False, "path": str(path)}
    mono = np.mean(audio, axis=1, keepdims=True)
    if audio.shape[1] >= 2:
        mid = ((audio[:, 0] + audio[:, 1]) * 0.5)[:, None]
        side = ((audio[:, 0] - audio[:, 1]) * 0.5)[:, None]
    else:
        mid = mono
        side = mono * 0
    return {
        "exists": True,
        "path": str(path),
        "sub_20_120_db": round(band_rms(mono, fs, 20, 120), 2),
        "mud_120_350_db": round(band_rms(mono, fs, 120, 350), 2),
        "melody_presence_1k5_4k5_db": round(band_rms(mono, fs, 1500, 4500), 2),
        "sibilance_5k5_9k_db": round(band_rms(mono, fs, 5500, 9000), 2),
        "hiss_air_9k_14k_db": round(band_rms(mono, fs, 9000, 14000), 2),
        "side_150_400_db": round(band_rms(side, fs, 150, 400), 2),
        "mid_150_400_db": round(band_rms(mid, fs, 150, 400), 2),
    }


def quiet_high_noise_proxy(path: Path) -> dict[str, object]:
    fs, audio = read_audio(path)
    if fs is None or audio is None:
        return {"exists": False, "path": str(path)}
    mono = np.mean(audio, axis=1, keepdims=True)
    hi_sos = signal.butter(4, [9000 / (fs * 0.5), 14000 / (fs * 0.5)], btype="bandpass", output="sos")
    hi = signal.sosfilt(hi_sos, mono, axis=0)
    block = max(1, int(0.400 * fs))
    hop = max(1, int(0.200 * fs))
    full_rms = []
    hi_rms = []
    for start in range(0, max(1, mono.shape[0] - block + 1), hop):
        full = mono[start : start + block]
        high = hi[start : start + block]
        if full.shape[0] < block:
            break
        full_rms.append(float(np.sqrt(np.mean(full * full))))
        hi_rms.append(float(np.sqrt(np.mean(high * high))))
    if not full_rms:
        return {"exists": True, "path": str(path), "quiet_hiss_proxy_db": None}
    threshold = float(np.percentile(full_rms, 30))
    selected = [h for f, h in zip(full_rms, hi_rms) if f <= threshold and h > 0]
    if not selected:
        selected = [h for h in hi_rms if h > 0]
    return {
        "exists": True,
        "path": str(path),
        "quiet_window_count": len(selected),
        "quiet_hiss_proxy_db": round(db(float(np.mean(selected))), 2),
    }


def split_track_chunks(rpp_path: Path) -> list[list[str]]:
    if not rpp_path.exists():
        return []
    chunks: list[list[str]] = []
    current: list[str] | None = None
    depth = 0
    for line in rpp_path.read_text(errors="ignore").splitlines():
        stripped = line.strip()
        if current is None and stripped.startswith("<TRACK"):
            current = [line]
            depth = 1
            continue
        if current is None:
            continue
        current.append(line)
        if stripped.startswith("<") and not stripped.startswith("<TRACK"):
            depth += 1
        if stripped == ">":
            depth -= 1
            if depth == 0:
                chunks.append(current)
                current = None
    return chunks


def parse_track_levels(rpp_path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for index, chunk in enumerate(split_track_chunks(rpp_path)):
        name = ""
        vol = 1.0
        pan = 0.0
        mute = False
        item_depth = 0
        for raw in chunk:
            s = raw.strip()
            if s.startswith("<ITEM"):
                item_depth += 1
                continue
            if item_depth > 0:
                if s == ">":
                    item_depth -= 1
                continue
            if s.startswith("NAME ") and not name:
                name = s[5:].strip().strip('"')
            elif s.startswith("VOLPAN "):
                parts = s.split()
                vol = float(parts[1])
                pan = float(parts[2])
            elif s.startswith("MUTESOLO "):
                mute = s.split()[1] == "1"
        if name:
            result[name] = {
                "index": index,
                "volume_db": round(db(vol), 2),
                "pan": round(pan, 3),
                "mute": mute,
            }
    return result


def validation(track_levels: dict[str, dict[str, object]]) -> dict[str, object]:
    failures = []
    for name in [
        "REF_BUS",
        "ARTIFACT_QUARANTINE_BUS",
        "QUARANTINE - 03_FX",
        "QUARANTINE - 08_Guitar",
        "SUNO_000000_CANDIDATE_BUS",
        "SUNO000000 CANDIDATE - Lead Vocals",
        "SUNO000000 CANDIDATE - Drums",
        "SUNO000000 CANDIDATE - Bass",
        "SUNO000000 CANDIDATE - Synth",
        "SUNO000000 CANDIDATE - Other",
    ]:
        if not track_levels.get(name, {}).get("mute"):
            failures.append(f"{name} is not muted")
    if track_levels.get("12_Vocals", {}).get("mute", True):
        failures.append("12_Vocals is muted or missing")
    return {
        "failures": failures,
        "notes": ["PASS05 render safety mute checks passed."] if not failures else [],
    }


def afinfo(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return subprocess.check_output(["afinfo", str(path)], text=True, stderr=subprocess.STDOUT)[:2000]
    except Exception:
        return ""


def metric_table(metrics: dict[str, dict[str, object]], labels: list[str]) -> list[str]:
    rows = ["| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for label in labels:
        m = metrics.get(label, {})
        rows.append(
            f"| {label} | {m.get('exists', False)} | {m.get('sample_peak_dbfs', 'n/a')} | {m.get('approx_lufs_i', 'n/a')} | {m.get('approx_lra_lu', 'n/a')} | {m.get('clip_sample_count', 'n/a')} | {m.get('stereo_correlation', 'n/a')} |"
        )
    return rows


def band_table(bands: dict[str, dict[str, object]], labels: list[str]) -> list[str]:
    keys = ["sub_20_120_db", "mud_120_350_db", "melody_presence_1k5_4k5_db", "sibilance_5k5_9k_db", "hiss_air_9k_14k_db", "side_150_400_db"]
    rows = ["| File | " + " | ".join(keys) + " |", "| --- | " + " | ".join(["---:"] * len(keys)) + " |"]
    for label in labels:
        b = bands.get(label, {})
        rows.append("| " + label + " | " + " | ".join(str(b.get(key, "n/a")) for key in keys) + " |")
    return rows


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    labels = {
        "pass03_master": RENDERS / "PASS03_MASTER_BEAT_FORWARD_LOUD_24bit_48k.wav",
        "pass04_master": RENDERS / "PASS04_MASTER_ALL_INFO_LOUD_24bit_48k.wav",
        "pass05_premaster": RENDERS / "PASS05_PREMASTER_CLEAN_MELODY_FORWARD_24bit_48k.wav",
        "pass05_master": RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_24bit_48k.wav",
        "technical_reference": TECHNICAL_REFERENCE,
    }
    metrics = {label: analyze_wav(path) for label, path in labels.items()}
    bands = {label: band_profile(path) for label, path in labels.items()}
    noise = {label: quiet_high_noise_proxy(path) for label, path in labels.items() if label != "technical_reference"}
    track_levels = parse_track_levels(PASS05_RPP)
    important_tracks = {
        name: track_levels.get(name, {})
        for name in [
            "12_Vocals",
            "MALE_LEAD_VOX_BUS",
            "MUSIC_BUS",
            "04_Synth",
            "07_Keyboard",
            "DRUM_BUS",
            "BASS_808_BUS",
            "FEMALE_BGV_BUS",
            "VOCAL_FX_BUS",
            "FX_BUS",
            "SUNO_000000_CANDIDATE_BUS",
        ]
    }
    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "project": str(PASS05_RPP),
        "metrics": metrics,
        "band_profiles": bands,
        "quiet_high_noise_proxy": noise,
        "track_levels": important_tracks,
        "validation": validation(track_levels),
        "mp3": {
            "path": str(RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_320k.mp3"),
            "exists": (RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_320k.mp3").exists(),
            "afinfo": afinfo(RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_320k.mp3"),
            "note": "MP3 encoder is unavailable in the current REAPER/system setup if this file does not exist.",
        },
        "m4a_preview": {
            "path": str(RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_320k.m4a"),
            "exists": (RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_320k.m4a").exists(),
            "afinfo": afinfo(RENDERS / "PASS05_MASTER_CLEAN_MELODY_FORWARD_320k.m4a"),
        },
    }
    (REPORTS / "pass05_clean_melody_forward_qc.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    pass05 = metrics["pass05_master"]
    pass04_noise = noise.get("pass04_master", {}).get("quiet_hiss_proxy_db")
    pass05_noise = noise.get("pass05_master", {}).get("quiet_hiss_proxy_db")
    noise_delta = None
    if isinstance(pass04_noise, (int, float)) and isinstance(pass05_noise, (int, float)):
        noise_delta = round(pass05_noise - pass04_noise, 2)

    lines = [
        "# Pass 05 Clean Melody-Forward Report",
        "",
        f"Generated: {payload['generated']}",
        "",
        "## User Direction",
        "- Mix/master in REAPER.",
        "- Follow the technical reference as a broad mix compass only.",
        "- Reduce noisy ambience/fizz and make the main melody easier to hear.",
        "",
        "## Executed",
        "- Started from PASS04 and saved a separate PASS05 REAPER project.",
        "- Kept reference, quarantine, guide MIDI, and short Suno candidate stems muted.",
        "- Lowered BGV, general FX, vocal plate, delay, short room, and constant delay bed.",
        "- Raised synth/keyboard melody and added a subtle REAPER JSFX presence tilt.",
        "- Added custom REAPER JSFX high-band noise-floor tamers on vocal, FX, and music buses.",
        "- Used dynamic cut bands for low-mid bloom, high fizz, BGV sibilance, and limiter edge.",
        "- MP3 export was skipped because this REAPER install exposes WAV/AIFF/CAF render sinks only; a 320k AAC M4A preview is provided instead.",
        "",
        "## Metrics",
        "",
        *metric_table(metrics, ["pass03_master", "pass04_master", "pass05_premaster", "pass05_master", "technical_reference"]),
        "",
        "## Tonal / Noise Proxy",
        "",
        *band_table(bands, ["pass03_master", "pass04_master", "pass05_master", "technical_reference"]),
        "",
        "## Interpretation",
        f"- PASS05 master exists: {pass05.get('exists', False)}.",
        f"- PASS05 approximate loudness: {pass05.get('approx_lufs_i', 'n/a')} LUFS-I proxy, peak {pass05.get('sample_peak_dbfs', 'n/a')} dBFS, clips {pass05.get('clip_sample_count', 'n/a')}.",
        f"- Quiet-window 9-14 kHz hiss proxy delta vs PASS04: {noise_delta if noise_delta is not None else 'n/a'} dB. Negative means less high-band noise by this heuristic.",
        "- This is measured QC, not a substitute for listening in REAPER for vocal artifacts, pumping, or taste.",
        "",
        "## Important Track Levels",
        "",
        "| Track | Volume dB | Pan | Muted |",
        "| --- | ---: | ---: | --- |",
    ]
    for name, data in important_tracks.items():
        lines.append(f"| {name} | {data.get('volume_db', 'n/a')} | {data.get('pan', 'n/a')} | {data.get('mute', 'n/a')} |")
    lines.extend(
        [
            "",
            "## Validation",
            "PASS" if not payload["validation"]["failures"] else "BLOCKED",
            *(f"- {note}" for note in payload["validation"]["notes"]),
            *(f"- {failure}" for failure in payload["validation"]["failures"]),
        ]
    )
    (REPORTS / "pass05_clean_melody_forward_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORTS / "pass05_loudness_check.md").write_text(
        "\n".join(
            [
                "# Pass 05 Loudness Check",
                "",
                "ffmpeg ebur128 is unavailable in this shell. This report uses the local Python BS.1770-style approximation plus sample peak and stereo correlation.",
                "",
                *metric_table(metrics, ["pass03_master", "pass04_master", "pass05_premaster", "pass05_master", "technical_reference"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (REPORTS / "pass05_final_qc.md").write_text(
        "\n".join(
            [
                "# Pass 05 Final QC",
                "",
                *metric_table(metrics, ["pass03_master", "pass04_master", "pass05_master", "technical_reference"]),
                "",
                "## Notes",
                "- No sample clipping is acceptable only if the clip count remains 0.",
                "- The main melody lift is done by mix balance and REAPER JSFX presence tilt, not reference melody copying.",
                "- Human ear check remains required for AI vocal/formant artifacts and limiter pumping.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
