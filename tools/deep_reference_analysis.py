from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw
from scipy import signal
from scipy.io import wavfile


TRACKS = [
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Broken_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Dough_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-IMnK_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Lovee_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Missu_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Phobia_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Stuck in Seoul_MASTER_24-48.wav",
    "/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48./Estona,Nib-Why_MASTER_24-48.wav",
]

OUTDIR = Path("/Users/hantaeheuk/Desktop/reference_analysis_estona_nib_deep")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

EQ_BANDS = [
    ("20_30_sub_floor", 20, 30),
    ("30_50_deep_sub", 30, 50),
    ("50_80_sub_punch", 50, 80),
    ("80_120_bass_body", 80, 120),
    ("120_200_warmth", 120, 200),
    ("200_350_mud", 200, 350),
    ("350_700_low_mid_box", 350, 700),
    ("700_1200_mid_nasal", 700, 1200),
    ("1200_2000_vocal_bite", 1200, 2000),
    ("2000_4000_presence", 2000, 4000),
    ("4000_6000_edge", 4000, 6000),
    ("6000_10000_sparkle", 6000, 10000),
    ("10000_16000_air", 10000, 16000),
]


def db_amp(value: float) -> float:
    return 20.0 * math.log10(max(float(value), 1e-12))


def db_power(value: float) -> float:
    return 10.0 * math.log10(max(float(value), 1e-30))


def clean_track_name(path: Path) -> str:
    return path.stem.replace("Estona,Nib-", "").replace("_MASTER_24-48", "")


def audio_to_float(data: np.ndarray) -> np.ndarray:
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        scale = max(abs(info.min), info.max)
        return data.astype(np.float64) / scale
    return data.astype(np.float64)


def read_audio(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    y = audio_to_float(data)
    if y.ndim == 1:
        y = y[:, None]
    return sr, y


def ebur128(path: Path) -> dict[str, float | None]:
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-filter_complex",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    summary = result.stderr[result.stderr.rfind("Summary:") :]
    patterns = {
        "integrated_lufs": r"I:\s*([\-\d\.]+) LUFS",
        "lra_lu": r"LRA:\s*([\-\d\.]+) LU",
        "true_peak_dbfs": r"Peak:\s*([\-\d\.]+) dBFS",
    }
    values: dict[str, float | None] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, summary)
        values[key] = float(match.group(1)) if match else None
    return values


def welch_power(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    nperseg = min(32768, len(y))
    if nperseg < 1024:
        nperseg = min(1024, len(y))
    return signal.welch(y, fs=sr, nperseg=nperseg, noverlap=nperseg // 2)


def integrate_band(freq: np.ndarray, power: np.ndarray, low: float, high: float) -> float:
    mask = (freq >= low) & (freq < high)
    if not mask.any():
        return 0.0
    return float(np.trapezoid(power[mask], freq[mask]))


def band_table(y: np.ndarray, sr: int) -> list[dict[str, float | str]]:
    mono = y.mean(axis=1)
    mid = (y[:, 0] + y[:, 1]) / 2.0 if y.shape[1] >= 2 else mono
    side = (y[:, 0] - y[:, 1]) / 2.0 if y.shape[1] >= 2 else np.zeros_like(mono)
    freq, p_mono = welch_power(mono, sr)
    _, p_mid = welch_power(mid, sr)
    _, p_side = welch_power(side, sr)
    total = integrate_band(freq, p_mono, 20, 16000) + 1e-30
    rows: list[dict[str, float | str]] = []
    for name, low, high in EQ_BANDS:
        mono_power = integrate_band(freq, p_mono, low, high)
        mid_power = integrate_band(freq, p_mid, low, high)
        side_power = integrate_band(freq, p_side, low, high)
        rows.append(
            {
                "band": name,
                "low_hz": low,
                "high_hz": high,
                "energy_pct": 100.0 * mono_power / total,
                "relative_db": db_power(mono_power / total),
                "mid_power_db": db_power(mid_power),
                "side_power_db": db_power(side_power),
                "side_mid_db": db_power(side_power / (mid_power + 1e-30)),
            }
        )
    return rows


def frame_rms_db(y: np.ndarray, sr: int, seconds: float) -> np.ndarray:
    mono = y.mean(axis=1)
    frame = max(int(sr * seconds), 1)
    usable = len(mono) // frame * frame
    if usable <= 0:
        return np.array([])
    chunks = mono[:usable].reshape(-1, frame)
    rms = np.sqrt(np.mean(chunks * chunks, axis=1))
    return np.array([db_amp(x) for x in rms])


def segment_metrics(track: str, y: np.ndarray, sr: int, segment_seconds: int = 10) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    n = int(sr * segment_seconds)
    total_segments = math.ceil(len(y) / n)
    for index in range(total_segments):
        start = index * n
        end = min((index + 1) * n, len(y))
        if end - start < sr:
            continue
        seg = y[start:end]
        mono = seg.mean(axis=1)
        peak = float(np.max(np.abs(seg)))
        rms = float(np.sqrt(np.mean(seg * seg)))
        crest = db_amp(peak) - db_amp(rms)
        corr = float(np.corrcoef(seg[:, 0], seg[:, 1])[0, 1]) if seg.shape[1] >= 2 else 1.0
        b = {r["band"]: float(r["energy_pct"]) for r in band_table(seg, sr)}
        rows.append(
            {
                "track": track,
                "segment": index + 1,
                "start_s": round(start / sr, 2),
                "end_s": round(end / sr, 2),
                "rms_dbfs": round(db_amp(rms), 2),
                "sample_peak_dbfs": round(db_amp(peak), 2),
                "crest_db": round(crest, 2),
                "stereo_corr": round(corr, 3),
                "sub_20_80_pct": round(b["20_30_sub_floor"] + b["30_50_deep_sub"] + b["50_80_sub_punch"], 2),
                "bass_80_200_pct": round(b["80_120_bass_body"] + b["120_200_warmth"], 2),
                "mud_200_350_pct": round(b["200_350_mud"], 2),
                "presence_2_6k_pct": round(b["2000_4000_presence"] + b["4000_6000_edge"], 2),
                "air_6_16k_pct": round(b["6000_10000_sparkle"] + b["10000_16000_air"], 2),
            }
        )
    return rows


def clipped_sample_stats(y: np.ndarray) -> dict[str, float | int]:
    threshold = 10 ** (-0.1 / 20.0)
    near = np.abs(y) >= threshold
    full = np.abs(y) >= 0.999999
    mono_near = near.any(axis=1)
    runs = 0
    in_run = False
    max_run = 0
    current = 0
    for value in mono_near:
        if value:
            current += 1
            if not in_run:
                runs += 1
                in_run = True
        else:
            max_run = max(max_run, current)
            current = 0
            in_run = False
    max_run = max(max_run, current)
    return {
        "near_fullscale_samples": int(near.sum()),
        "fullscale_samples": int(full.sum()),
        "near_fullscale_frames_pct": 100.0 * float(mono_near.mean()),
        "near_fullscale_runs": runs,
        "max_near_fullscale_run_samples": max_run,
    }


def spectral_descriptors(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = y.mean(axis=1)
    freq, power = welch_power(mono, sr)
    total_power = np.sum(power) + 1e-30
    centroid = float(np.sum(freq * power) / total_power)
    cumsum = np.cumsum(power)
    rolloff85 = float(freq[np.searchsorted(cumsum, 0.85 * cumsum[-1])])
    low = integrate_band(freq, power, 20, 200)
    lowmid = integrate_band(freq, power, 200, 700)
    mid = integrate_band(freq, power, 700, 2000)
    high = integrate_band(freq, power, 2000, 16000)
    return {
        "centroid_hz": centroid,
        "rolloff85_hz": rolloff85,
        "low_20_200_pct": 100.0 * low / (low + lowmid + mid + high + 1e-30),
        "lowmid_200_700_pct": 100.0 * lowmid / (low + lowmid + mid + high + 1e-30),
        "mid_700_2k_pct": 100.0 * mid / (low + lowmid + mid + high + 1e-30),
        "high_2_16k_pct": 100.0 * high / (low + lowmid + mid + high + 1e-30),
        "high_low_db": db_power(high / (low + 1e-30)),
    }


def global_metrics(track: str, path: Path, y: np.ndarray, sr: int) -> dict[str, float | int | str | None]:
    duration = len(y) / sr
    peak = float(np.max(np.abs(y)))
    rms = float(np.sqrt(np.mean(y * y)))
    left_rms = float(np.sqrt(np.mean(y[:, 0] * y[:, 0])))
    right_rms = float(np.sqrt(np.mean(y[:, 1] * y[:, 1]))) if y.shape[1] >= 2 else left_rms
    mid = (y[:, 0] + y[:, 1]) / 2.0 if y.shape[1] >= 2 else y[:, 0]
    side = (y[:, 0] - y[:, 1]) / 2.0 if y.shape[1] >= 2 else np.zeros(len(y))
    mid_rms = float(np.sqrt(np.mean(mid * mid)))
    side_rms = float(np.sqrt(np.mean(side * side)))
    short = frame_rms_db(y, sr, 3.0)
    momentary = frame_rms_db(y, sr, 0.4)
    descriptors = spectral_descriptors(y, sr)
    clips = clipped_sample_stats(y)
    loud = ebur128(path)
    return {
        "track": track,
        "path": str(path),
        "duration_s": round(duration, 2),
        "sample_rate": sr,
        "channels": y.shape[1],
        "sample_peak_dbfs": round(db_amp(peak), 2),
        "rms_dbfs": round(db_amp(rms), 2),
        "crest_db": round(db_amp(peak) - db_amp(rms), 2),
        "l_r_balance_db": round(db_amp(left_rms / (right_rms + 1e-12)), 2),
        "stereo_corr": round(float(np.corrcoef(y[:, 0], y[:, 1])[0, 1]) if y.shape[1] >= 2 else 1.0, 3),
        "side_mid_db": round(db_amp(side_rms / (mid_rms + 1e-12)), 2),
        "short_rms_p10_dbfs": round(float(np.percentile(short, 10)), 2) if len(short) else None,
        "short_rms_p50_dbfs": round(float(np.percentile(short, 50)), 2) if len(short) else None,
        "short_rms_p90_dbfs": round(float(np.percentile(short, 90)), 2) if len(short) else None,
        "momentary_rms_p90_dbfs": round(float(np.percentile(momentary, 90)), 2) if len(momentary) else None,
        "momentary_rms_p99_dbfs": round(float(np.percentile(momentary, 99)), 2) if len(momentary) else None,
        **{k: round(v, 2) for k, v in descriptors.items()},
        **{k: round(v, 4) if isinstance(v, float) else v for k, v in clips.items()},
        **loud,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return float(np.mean(np.array(values, dtype=float)))


def median(values: list[float]) -> float:
    return float(np.median(np.array(values, dtype=float)))


def numeric(rows: list[dict[str, object]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def heatmap(path: Path, tracks: list[str], bands: list[str], matrix: np.ndarray) -> None:
    cell_w = 70
    cell_h = 28
    left = 190
    top = 50
    img = Image.new("RGB", (left + cell_w * len(bands) + 30, top + cell_h * len(tracks) + 45), "white")
    draw = ImageDraw.Draw(img)
    vmax = max(float(np.percentile(matrix, 95)), 1e-9)
    for col, band in enumerate(bands):
        draw.text((left + col * cell_w + 3, 8), band.split("_")[0] + "-" + band.split("_")[1], fill=(0, 0, 0))
    for row, track in enumerate(tracks):
        y = top + row * cell_h
        draw.text((8, y + 7), track, fill=(0, 0, 0))
        for col in range(len(bands)):
            value = matrix[row, col]
            level = max(0.0, min(1.0, value / vmax))
            color = (int(255 * level), int(70 + 120 * (1 - level)), int(255 * (1 - level)))
            x = left + col * cell_w
            draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), fill=color)
            draw.text((x + 5, y + 7), f"{value:.1f}", fill=(0, 0, 0))
    img.save(path)


def recommendation_for_track(row: dict[str, object], band_rows: list[dict[str, object]]) -> list[str]:
    track = row["track"]
    bands = {str(r["band"]): float(r["energy_pct"]) for r in band_rows if r["track"] == track}
    notes: list[str] = []
    sub = bands["20_30_sub_floor"] + bands["30_50_deep_sub"] + bands["50_80_sub_punch"]
    lowmid = bands["200_350_mud"] + bands["350_700_low_mid_box"]
    high = bands["2000_4000_presence"] + bands["4000_6000_edge"] + bands["6000_10000_sparkle"] + bands["10000_16000_air"]
    if sub >= 45:
        notes.append("sub-heavy reference: 30-80 Hz를 중심축으로 두고 킥/808을 mono에 고정")
    elif sub <= 28:
        notes.append("less sub-dominant: 120-2k 악기/보컬 밀도가 더 중요")
    if lowmid >= 20:
        notes.append("low-mid density high: 200-500 Hz 정리가 부족하면 바로 답답해짐")
    if high >= 12:
        notes.append("brighter reference: 2-6 kHz 존재감과 6-10 kHz sparkle 관리 필요")
    else:
        notes.append("top restrained: 하이햇/air를 과하게 올리기보다 중저역 밀도 유지")
    if float(row["side_mid_db"]) > -8:
        notes.append("wide image: side 대역이 강해 mono 호환과 보컬 center를 별도 체크")
    elif float(row["side_mid_db"]) < -13:
        notes.append("center-heavy image: 저역과 핵심 리드가 중앙에 강하게 모이는 타입")
    return notes


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    global_rows: list[dict[str, object]] = []
    band_rows: list[dict[str, object]] = []
    ms_rows: list[dict[str, object]] = []
    segment_rows: list[dict[str, object]] = []

    audio_cache: dict[str, tuple[int, np.ndarray]] = {}
    for raw in TRACKS:
        path = Path(raw)
        track = clean_track_name(path)
        sr, y = read_audio(path)
        audio_cache[track] = (sr, y)
        global_rows.append(global_metrics(track, path, y, sr))
        per_band = band_table(y, sr)
        for band in per_band:
            band_rows.append(
                {
                    "track": track,
                    "band": band["band"],
                    "low_hz": band["low_hz"],
                    "high_hz": band["high_hz"],
                    "energy_pct": round(float(band["energy_pct"]), 4),
                    "relative_db": round(float(band["relative_db"]), 2),
                }
            )
            ms_rows.append(
                {
                    "track": track,
                    "band": band["band"],
                    "low_hz": band["low_hz"],
                    "high_hz": band["high_hz"],
                    "mid_power_db": round(float(band["mid_power_db"]), 2),
                    "side_power_db": round(float(band["side_power_db"]), 2),
                    "side_mid_db": round(float(band["side_mid_db"]), 2),
                }
            )
        segment_rows.extend(segment_metrics(track, y, sr, 10))

    write_csv(OUTDIR / "global_master_metrics.csv", global_rows)
    write_csv(OUTDIR / "eq_band_energy.csv", band_rows)
    write_csv(OUTDIR / "mid_side_band_balance.csv", ms_rows)
    write_csv(OUTDIR / "segment_10s_metrics.csv", segment_rows)

    track_names = [str(r["track"]) for r in global_rows]
    band_names = [b[0] for b in EQ_BANDS]
    matrix = np.array(
        [
            [float(next(r["energy_pct"] for r in band_rows if r["track"] == track and r["band"] == band)) for band in band_names]
            for track in track_names
        ]
    )
    heatmap(OUTDIR / "eq_band_energy_heatmap.png", track_names, band_names, matrix)

    summary_path = OUTDIR / "deep_reference_summary.md"
    target_path = OUTDIR / "reaper_mix_master_target_sheet.md"
    korean_path = OUTDIR / "mix_master_detailed_korean_report.md"
    write_summary(summary_path, global_rows, band_rows, ms_rows, segment_rows)
    write_reaper_targets(target_path, global_rows, band_rows, ms_rows)
    write_korean_report(korean_path, global_rows, band_rows, ms_rows, segment_rows)
    print(summary_path)
    print(target_path)
    print(korean_path)
    print(OUTDIR / "global_master_metrics.csv")
    print(OUTDIR / "eq_band_energy.csv")
    print(OUTDIR / "mid_side_band_balance.csv")
    print(OUTDIR / "segment_10s_metrics.csv")
    print(OUTDIR / "eq_band_energy_heatmap.png")


def write_summary(
    path: Path,
    global_rows: list[dict[str, object]],
    band_rows: list[dict[str, object]],
    ms_rows: list[dict[str, object]],
    segment_rows: list[dict[str, object]],
) -> None:
    lufs = numeric(global_rows, "integrated_lufs")
    true_peaks = numeric(global_rows, "true_peak_dbfs")
    crest = numeric(global_rows, "crest_db")
    side_mid = numeric(global_rows, "side_mid_db")
    corr = numeric(global_rows, "stereo_corr")
    with path.open("w", encoding="utf-8") as f:
        f.write("# Estona,Nib Deep Reference Analysis\n\n")
        f.write("## Reference Fingerprint\n\n")
        f.write(
            f"- Loudness cluster: integrated loudness median {median(lufs):.2f} LUFS, range {min(lufs):.2f} to {max(lufs):.2f} LUFS.\n"
        )
        f.write(
            f"- Peak behavior: true peak median {median(true_peaks):.2f} dBFS, range {min(true_peaks):.2f} to {max(true_peaks):.2f} dBFS. This is a clipped/limited master aesthetic, not a conservative streaming master.\n"
        )
        f.write(
            f"- Density: crest median {median(crest):.2f} dB. These masters are very dense; transient punch comes from clipper shape, not large headroom.\n"
        )
        f.write(
            f"- Stereo: side/mid median {median(side_mid):.2f} dB and correlation median {median(corr):.2f}. The set is mostly center-heavy except Missu.\n\n"
        )

        f.write("## Aggregate EQ Shape\n\n")
        f.write("| Band | Median Energy | Mean Energy | Mix Meaning |\n")
        f.write("|---|---:|---:|---|\n")
        meaning = {
            "20_30_sub_floor": "sub floor, mostly felt; avoid uncontrolled rumble",
            "30_50_deep_sub": "deep 808 weight and room pressure",
            "50_80_sub_punch": "kick/808 impact zone",
            "80_120_bass_body": "bass note body and small-speaker translation",
            "120_200_warmth": "warmth; can become cloudy if stacked",
            "200_350_mud": "mud zone; needs active cleanup",
            "350_700_low_mid_box": "box/body; vocal and synth crowding area",
            "700_1200_mid_nasal": "nasal midrange and melody audibility",
            "1200_2000_vocal_bite": "lead/vocal bite",
            "2000_4000_presence": "vocal/front edge",
            "4000_6000_edge": "sharpness, consonants, aggressive synth edge",
            "6000_10000_sparkle": "hats, fizz, width cues",
            "10000_16000_air": "air; very restrained in this reference set",
        }
        for band, _, _ in EQ_BANDS:
            vals = [float(r["energy_pct"]) for r in band_rows if r["band"] == band]
            f.write(f"| {band} | {median(vals):.2f}% | {mean(vals):.2f}% | {meaning[band]} |\n")

        f.write("\n## Track-by-Track Notes\n\n")
        for row in global_rows:
            track = str(row["track"])
            track_bands = [r for r in band_rows if r["track"] == track]
            sub = sum(float(r["energy_pct"]) for r in track_bands if str(r["band"]).startswith(("20_", "30_", "50_")))
            presence = sum(float(r["energy_pct"]) for r in track_bands if r["band"] in ("2000_4000_presence", "4000_6000_edge"))
            air = sum(float(r["energy_pct"]) for r in track_bands if r["band"] in ("6000_10000_sparkle", "10000_16000_air"))
            f.write(f"### {track}\n\n")
            f.write(
                f"- Loudness {row['integrated_lufs']} LUFS, true peak {row['true_peak_dbfs']} dBFS, RMS {row['rms_dbfs']} dBFS, crest {row['crest_db']} dB.\n"
            )
            f.write(
                f"- Tonal balance: sub 20-80 Hz {sub:.2f}%, presence 2-6 kHz {presence:.2f}%, air/sparkle 6-16 kHz {air:.2f}%.\n"
            )
            f.write(
                f"- Stereo: side/mid {row['side_mid_db']} dB, correlation {row['stereo_corr']}. L/R balance {row['l_r_balance_db']} dB.\n"
            )
            segs = [r for r in segment_rows if r["track"] == track]
            loudest = max(segs, key=lambda r: float(r["rms_dbfs"]))
            brightest = max(segs, key=lambda r: float(r["presence_2_6k_pct"]) + float(r["air_6_16k_pct"]))
            f.write(
                f"- Loudest 10s area: {loudest['start_s']}-{loudest['end_s']}s at {loudest['rms_dbfs']} dBFS RMS.\n"
            )
            f.write(
                f"- Brightest 10s area: {brightest['start_s']}-{brightest['end_s']}s with presence+air {(float(brightest['presence_2_6k_pct']) + float(brightest['air_6_16k_pct'])):.2f}%.\n"
            )
            for note in recommendation_for_track(row, band_rows):
                f.write(f"- Mix implication: {note}.\n")
            f.write("\n")


def write_reaper_targets(
    path: Path,
    global_rows: list[dict[str, object]],
    band_rows: list[dict[str, object]],
    ms_rows: list[dict[str, object]],
) -> None:
    lufs = numeric(global_rows, "integrated_lufs")
    crest = numeric(global_rows, "crest_db")
    side_mid = numeric(global_rows, "side_mid_db")
    with path.open("w", encoding="utf-8") as f:
        f.write("# REAPER Mix/Master Target Sheet\n\n")
        f.write("## Master Bus Target\n\n")
        f.write(f"- Reference loudness center: {median(lufs):.2f} LUFS integrated.\n")
        f.write("- Working target for competitive loud master: -6.5 to -6.0 LUFS integrated.\n")
        f.write("- Safer delivery target: -7.5 to -6.8 LUFS integrated with -0.3 dBTP ceiling.\n")
        f.write(f"- Reference crest target: {min(crest):.1f}-{max(crest):.1f} dB, median {median(crest):.1f} dB.\n")
        f.write("- Practical chain: corrective EQ -> low-end saturation -> glue compression -> hard/soft clipper -> final limiter.\n\n")

        f.write("## EQ Target By Band\n\n")
        f.write("| Band | Reference Median | Practical Mix Target |\n")
        f.write("|---|---:|---|\n")
        targets = {
            "20_30_sub_floor": "high-pass only if rumble blooms; do not erase all energy",
            "30_50_deep_sub": "808 fundamental can live here; keep mono and controlled",
            "50_80_sub_punch": "kick/sub punch zone; strongest low-end anchor",
            "80_120_bass_body": "translation zone; add harmonics if bass vanishes on small speakers",
            "120_200_warmth": "keep warm but avoid stacked synth/vocal mud",
            "200_350_mud": "dynamic EQ or multiband dip when vocal/synth clouds up",
            "350_700_low_mid_box": "cut boxiness on pads/leads before master bus",
            "700_1200_mid_nasal": "use sparingly; too much makes the master cheap",
            "1200_2000_vocal_bite": "lead clarity without harshness",
            "2000_4000_presence": "front edge; automate rather than static boost",
            "4000_6000_edge": "watch sibilance and synth knives",
            "6000_10000_sparkle": "hats/fizz; refs are controlled, not bright EDM",
            "10000_16000_air": "small shelf only; air is restrained in this set",
        }
        for band, _, _ in EQ_BANDS:
            vals = [float(r["energy_pct"]) for r in band_rows if r["band"] == band]
            f.write(f"| {band} | {median(vals):.2f}% | {targets[band]} |\n")

        f.write("\n## Stereo And Mid/Side Target\n\n")
        f.write(f"- Global side/mid median: {median(side_mid):.2f} dB.\n")
        f.write("- Keep sub and kick below 120 Hz almost mono.\n")
        f.write("- Widen upper synths, texture, and reverb returns rather than widening bass.\n")
        f.write("- Missu is the wide outlier; Stuck in Seoul and Why are center-heavy references.\n")
        f.write("- REAPER checks: JS Goniometer, correlation meter, mid/side solo, mono fold-down.\n\n")

        f.write("## Concrete REAPER Moves\n\n")
        f.write("- Start every mix by gain staging the rough master to about -12 to -10 dBFS RMS before mastering.\n")
        f.write("- On kick/808 bus: trim sub resonances, clip peaks before the master, and keep 30-80 Hz stable.\n")
        f.write("- On music bus: clear 200-500 Hz if it masks vocal or lead melody.\n")
        f.write("- On vocal/lead bus: presence lives around 1.2-4 kHz, but the references do not carry excessive 6-16 kHz air.\n")
        f.write("- On master: do not use one limiter to do all loudness. Clip 1-3 dB first, then limit final 1-2 dB.\n")
        f.write("- A/B at matched loudness before pushing final level, then unmatch to test competitive loudness.\n")


def band_median(band_rows: list[dict[str, object]], band: str) -> float:
    return median([float(r["energy_pct"]) for r in band_rows if r["band"] == band])


def track_band_sum(band_rows: list[dict[str, object]], track: str, bands: tuple[str, ...]) -> float:
    return sum(float(r["energy_pct"]) for r in band_rows if r["track"] == track and r["band"] in bands)


def write_korean_report(
    path: Path,
    global_rows: list[dict[str, object]],
    band_rows: list[dict[str, object]],
    ms_rows: list[dict[str, object]],
    segment_rows: list[dict[str, object]],
) -> None:
    lufs = numeric(global_rows, "integrated_lufs")
    rms = numeric(global_rows, "rms_dbfs")
    crest = numeric(global_rows, "crest_db")
    tp = numeric(global_rows, "true_peak_dbfs")
    side_mid = numeric(global_rows, "side_mid_db")
    corr = numeric(global_rows, "stereo_corr")
    with path.open("w", encoding="utf-8") as f:
        f.write("# Estona,Nib 레퍼런스 심층 믹스/마스터 보고서\n\n")
        f.write("이 문서는 8개 완성 마스터 WAV를 실제 REAPER 믹스/마스터 기준으로 쓰기 위해 만든 분석입니다. 숫자는 절대적인 정답이 아니라, 이 레퍼런스 묶음이 공유하는 소리의 지문입니다.\n\n")

        f.write("## 1. 전체 결론\n\n")
        f.write(f"- 이 레퍼런스 세트의 중심 loudness는 거의 `{median(lufs):.2f} LUFS`입니다. 범위도 `{min(lufs):.2f}`에서 `{max(lufs):.2f} LUFS`라 곡마다 큰 차이가 없습니다.\n")
        f.write(f"- RMS 중앙값은 `{median(rms):.2f} dBFS`, crest 중앙값은 `{median(crest):.2f} dB`입니다. 즉 다이내믹을 크게 살린 마스터가 아니라, 클리퍼/리미터로 밀도 있게 누른 상업적 loud master입니다.\n")
        f.write(f"- true peak 중앙값은 `{median(tp):.2f} dBFS`이고 최대 `{max(tp):.2f} dBFS`까지 올라갑니다. 레퍼런스 자체는 intersample peak를 허용하는 뜨거운 마스터입니다. 배포용으로 그대로 복제하면 인코딩 이후 찢어짐 가능성이 있습니다.\n")
        f.write(f"- 스테레오는 전체적으로 넓은 편이 아닙니다. side/mid 중앙값 `{median(side_mid):.2f} dB`, correlation 중앙값 `{median(corr):.2f}`라 핵심 에너지가 중앙에 강하게 모입니다. `Missu`만 넓은 예외입니다.\n")
        f.write("- 톤 밸런스는 밝은 EDM/팝 마스터가 아니라, 30-80 Hz 저역과 80-200 Hz 몸통이 매우 중요한 저역 중심 마스터입니다. 10 kHz 이상의 air는 의외로 절제되어 있습니다.\n\n")

        f.write("## 2. EQ 지문: 전체 평균이 말하는 것\n\n")
        f.write("| 대역 | 중앙값 | 실제 믹스 의미 | 작업 판단 |\n")
        f.write("|---|---:|---|---|\n")
        rows = [
            ("20_30_sub_floor", "초저역 바닥/룸블", "많이 들리는 대역은 아니지만 사라지면 무게가 빠짐", "HPF는 20-25 Hz 근처에서만 조심스럽게"),
            ("30_50_deep_sub", "808 깊이", "이 세트의 핵심 저역 압력", "베이스 fundamental을 여기 세우되 mono 유지"),
            ("50_80_sub_punch", "킥/808 펀치", "체감 타격감의 중심", "킥과 808이 싸우면 여기에서 우선순위 결정"),
            ("80_120_bass_body", "베이스 몸통", "작은 스피커 번역에 필요", "808 harmonics나 bass body를 살림"),
            ("120_200_warmth", "따뜻함/두께", "너무 깎으면 얇아짐", "보컬/패드/베이스 중 누가 차지할지 정리"),
            ("200_350_mud", "먹먹함", "쌓이면 바로 아마추어처럼 들림", "dynamic EQ로 상황별 제어"),
            ("350_700_low_mid_box", "박스톤/몸통", "리드와 보컬이 답답해지는 구간", "패드/신스에서 먼저 정리"),
            ("700_1200_mid_nasal", "코맹맹이 중역", "멜로디 식별에는 필요하지만 과하면 촌스러움", "큰 부스트 금지"),
            ("1200_2000_vocal_bite", "보컬/리드 bite", "전면감의 시작", "보컬/리드만 선택적으로"),
            ("2000_4000_presence", "존재감", "앞으로 튀어나오는 대역", "정적 부스트보다 자동화/병렬 처리"),
            ("4000_6000_edge", "날/치찰/신스 엣지", "공격성은 생기지만 피로도도 큼", "디에서/동적 컷 준비"),
            ("6000_10000_sparkle", "하이햇/스파클", "밝기보다 리듬 질감", "과한 shelf 금지"),
            ("10000_16000_air", "공기감", "이 레퍼런스에서는 매우 적음", "큰 air boost는 레퍼런스에서 벗어남"),
        ]
        for band, label, meaning, move in rows:
            f.write(f"| {label} `{band}` | {band_median(band_rows, band):.2f}% | {meaning} | {move} |\n")
        f.write("\n")

        f.write("## 3. 실제 EQ 작업 규칙\n\n")
        f.write("- 마스터 EQ에서 밝게 만들려고 8-16 kHz를 크게 올리는 방향은 이 레퍼런스와 다릅니다. 이 세트는 고역보다 중저역 밀도와 클리퍼 질감이 먼저입니다.\n")
        f.write("- 30-80 Hz는 절대적으로 중요합니다. 하지만 마스터에서 저역을 올리는 식으로 만들면 리미터가 먼저 무너집니다. 킥/808 버스에서 피크를 정리하고, 필요한 harmonic을 80-200 Hz에 만들어야 합니다.\n")
        f.write("- 200-500 Hz는 가장 위험한 구간입니다. 여기서 보컬, 신스, 베이스 몸통이 같이 쌓이면 -6 LUFS까지 밀 때 바로 답답하고 찌그러집니다.\n")
        f.write("- 1.2-4 kHz는 보컬이나 리드가 앞으로 나오는 구간입니다. 전체 믹스에 광범위하게 올리면 피로하고 얇아집니다. 필요한 파트에만 선택적으로 주는 게 맞습니다.\n")
        f.write("- 6-10 kHz는 하이햇과 디지털 질감이 사는 곳이지만, 레퍼런스 중앙값이 낮습니다. 하이햇이 들리지 않는다면 볼륨/트랜지언트/새츄레이션을 먼저 보고, 마지막에 아주 작은 shelf를 씁니다.\n\n")

        f.write("## 4. 곡별 성향과 레퍼런스 용도\n\n")
        f.write("| 곡 | 용도 | 저역 | 밝기 | 스테레오 | 실제 참고 포인트 |\n")
        f.write("|---|---|---:|---:|---:|---|\n")
        for row in global_rows:
            track = str(row["track"])
            sub = track_band_sum(band_rows, track, ("20_30_sub_floor", "30_50_deep_sub", "50_80_sub_punch"))
            bright = track_band_sum(band_rows, track, ("2000_4000_presence", "4000_6000_edge", "6000_10000_sparkle", "10000_16000_air"))
            sm = float(row["side_mid_db"])
            if track in ("Broken", "Dough", "Lovee", "Why"):
                use = "저역/808 무게 레퍼런스"
            elif track == "IMnK":
                use = "밝기/중역 존재감 레퍼런스"
            elif track == "Missu":
                use = "넓은 stereo 레퍼런스"
            elif track == "Stuck in Seoul":
                use = "중앙 밀도/안정성 레퍼런스"
            else:
                use = "밀도/짧은 다이내믹 레퍼런스"
            if sub >= 50:
                low_note = "매우 강함"
            elif sub >= 42:
                low_note = "강함"
            else:
                low_note = "중간"
            if bright >= 10:
                bright_note = "상대적으로 밝음"
            elif bright >= 6:
                bright_note = "중간"
            else:
                bright_note = "절제"
            if sm > -8:
                stereo_note = "넓음"
            elif sm < -13:
                stereo_note = "중앙 집중"
            else:
                stereo_note = "중간"
            f.write(f"| {track} | {use} | {low_note} `{sub:.1f}%` | {bright_note} `{bright:.1f}%` | {stereo_note} `{sm:.1f} dB` | LUFS {row['integrated_lufs']}, crest {row['crest_db']} dB |\n")
        f.write("\n")

        f.write("## 5. 구간별 분석을 믹스에 쓰는 방법\n\n")
        for row in global_rows:
            track = str(row["track"])
            segs = [r for r in segment_rows if r["track"] == track]
            loudest = max(segs, key=lambda r: float(r["rms_dbfs"]))
            subbest = max(segs, key=lambda r: float(r["sub_20_80_pct"]))
            bright = max(segs, key=lambda r: float(r["presence_2_6k_pct"]) + float(r["air_6_16k_pct"]))
            f.write(f"- `{track}`: 가장 큰 구간 {loudest['start_s']}-{loudest['end_s']}s / 가장 sub 강한 구간 {subbest['start_s']}-{subbest['end_s']}s / 가장 밝은 구간 {bright['start_s']}-{bright['end_s']}s.\n")
        f.write("\n이 구간들은 A/B 기준점입니다. 내가 새 곡을 믹스할 때는 전체 곡 평균만 보지 말고, 후렴 또는 drop이 위 구간들과 비슷한 RMS/저역/밝기 구조를 갖는지 비교해야 합니다.\n\n")

        f.write("## 6. REAPER에서 실제로 적용할 체인\n\n")
        f.write("### Mix Bus 전 단계\n\n")
        f.write("1. 킥/808을 먼저 맞춥니다. 30-80 Hz를 중심으로 한쪽이 주도권을 가져야 하고, 둘 다 같은 순간에 같은 대역을 크게 먹으면 마스터에서 무너집니다.\n")
        f.write("2. 보컬/리드가 있다면 1.2-4 kHz를 확보합니다. 대신 6 kHz 이상을 과하게 열지 않습니다.\n")
        f.write("3. 패드/신스/샘플은 200-700 Hz를 정리합니다. 이 레퍼런스처럼 -6 LUFS까지 밀려면 low-mid 정리가 먼저입니다.\n")
        f.write("4. 리버브와 딜레이는 side에 둬도 되지만, sub와 lead center는 흔들리면 안 됩니다.\n\n")

        f.write("### Master Chain 권장 순서\n\n")
        f.write("1. `Pre EQ`: 20-25 Hz 아래 불필요한 rumble만 정리. 200-350 Hz가 부으면 아주 넓게 -0.5~-1.5 dB.\n")
        f.write("2. `Saturation/Clip`: 킥/808 피크를 먼저 둥글게 만듭니다. 여기서 loudness의 절반을 얻어야 합니다.\n")
        f.write("3. `Glue Comp`: 1-2 dB 정도만. 어택을 너무 빠르게 하면 킥이 죽고, 너무 느리면 리미터가 찢어집니다.\n")
        f.write("4. `Soft/Hard Clipper`: 레퍼런스의 true peak/crest 특성상 필수에 가깝습니다. 단, 808 sustain이 찢어지면 클리퍼 전 저역 EQ로 해결합니다.\n")
        f.write("5. `Final Limiter`: 마지막 1-2 dB만. ceiling은 작업용 비교라면 -0.1 dBFS, 배포 안정성은 -0.3~-1.0 dBTP.\n\n")

        f.write("## 7. 내가 향후 네 곡을 작업할 때 쓸 기준\n\n")
        f.write("- 목표가 이 레퍼런스와 같은 강한 마스터라면 최종 후보는 `-6.5~-6.0 LUFS`, crest `7.3~8.5 dB`, RMS `약 -8~-7 dBFS`입니다.\n")
        f.write("- 하지만 플랫폼 업로드/인코딩 안정성이 중요하면 `-7.5~-6.8 LUFS`, true peak `-0.3 dBTP 이하`로 한 단계 안전하게 갑니다.\n")
        f.write("- EQ는 30-80 Hz를 크게, 200-500 Hz는 정리, 2-4 kHz는 선택적으로, 10 kHz 이상은 절제하는 방향이 이 레퍼런스 세트의 핵심입니다.\n")
        f.write("- 스테레오는 넓게 펼치는 것보다 중앙 밀도를 우선합니다. 넓힘은 6 kHz 이상 질감, 리버브, 일부 신스에만 제한적으로 씁니다.\n")


if __name__ == "__main__":
    main()
