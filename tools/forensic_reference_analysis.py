from __future__ import annotations

import csv
import math
from pathlib import Path

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

OUTDIR = Path("/Users/hantaeheuk/Desktop/reference_analysis_estona_nib_forensic")

BANDS = [
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

MACRO_BANDS = [
    ("sub_20_80", ("20_30_sub_floor", "30_50_deep_sub", "50_80_sub_punch")),
    ("bass_body_80_200", ("80_120_bass_body", "120_200_warmth")),
    ("mud_box_200_700", ("200_350_mud", "350_700_low_mid_box")),
    ("lead_mid_700_2k", ("700_1200_mid_nasal", "1200_2000_vocal_bite")),
    ("presence_2_6k", ("2000_4000_presence", "4000_6000_edge")),
    ("sparkle_air_6_16k", ("6000_10000_sparkle", "10000_16000_air")),
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


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x * x)))


def stereo_rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(y * y)))


def welch(y: np.ndarray, sr: int, nperseg: int = 32768) -> tuple[np.ndarray, np.ndarray]:
    n = min(nperseg, len(y))
    n = max(1024, n)
    return signal.welch(y, fs=sr, nperseg=n, noverlap=n // 2)


def integrate(freq: np.ndarray, power: np.ndarray, low: float, high: float) -> float:
    mask = (freq >= low) & (freq < high)
    if not mask.any():
        return 0.0
    return float(np.trapezoid(power[mask], freq[mask]))


def band_energy_dict(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = y.mean(axis=1)
    freq, power = welch(mono, sr)
    total = integrate(freq, power, 20, 16000) + 1e-30
    return {name: 100.0 * integrate(freq, power, low, high) / total for name, low, high in BANDS}


def macro_from_bands(bands: dict[str, float]) -> dict[str, float]:
    return {name: sum(bands[b] for b in band_names) for name, band_names in MACRO_BANDS}


def band_filter(x: np.ndarray, sr: int, low: float, high: float) -> np.ndarray:
    nyq = sr / 2.0
    low = max(low, 1.0)
    high = min(high, nyq * 0.95)
    sos = signal.butter(4, [low, high], btype="bandpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def band_stereo_phase(track: str, y: np.ndarray, sr: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    full_stereo = stereo_rms(y)
    for name, low, high in BANDS:
        filtered = band_filter(y, sr, low, high)
        left = filtered[:, 0]
        right = filtered[:, 1] if filtered.shape[1] > 1 else filtered[:, 0]
        mid = (left + right) / 2.0
        side = (left - right) / 2.0
        corr = float(np.corrcoef(left, right)[0, 1]) if rms(left) > 1e-9 and rms(right) > 1e-9 else 1.0
        mid_rms = rms(mid)
        side_rms = rms(side)
        mono = mid
        mono_loss_db = db_amp((rms(mono) + 1e-12) / (stereo_rms(filtered) + 1e-12))
        rows.append(
            {
                "track": track,
                "band": name,
                "low_hz": low,
                "high_hz": high,
                "corr": round(corr, 4),
                "side_mid_db": round(db_amp(side_rms / (mid_rms + 1e-12)), 2),
                "mono_fold_vs_band_stereo_db": round(mono_loss_db, 2),
                "band_rms_dbfs": round(db_amp(stereo_rms(filtered)), 2),
                "band_rms_vs_full_db": round(db_amp((stereo_rms(filtered) + 1e-12) / (full_stereo + 1e-12)), 2),
            }
        )
    return rows


def peak_density(track: str, y: np.ndarray, sr: int) -> dict[str, object]:
    abs_y = np.abs(y)
    peak = float(abs_y.max())
    rows: dict[str, object] = {
        "track": track,
        "sample_peak_dbfs": round(db_amp(peak), 3),
        "abs_p95_dbfs": round(db_amp(float(np.percentile(abs_y, 95))), 2),
        "abs_p99_dbfs": round(db_amp(float(np.percentile(abs_y, 99))), 2),
        "abs_p999_dbfs": round(db_amp(float(np.percentile(abs_y, 99.9))), 2),
        "positive_peak": round(float(y.max()), 6),
        "negative_peak": round(float(y.min()), 6),
    }
    for db in (-0.1, -0.5, -1, -2, -3, -6):
        threshold = 10 ** (db / 20.0)
        rows[f"samples_above_{db:g}dbfs_pct"] = round(100.0 * float((abs_y >= threshold).mean()), 5)
        frame_hit = (abs_y >= threshold).any(axis=1)
        rows[f"frames_above_{db:g}dbfs_pct"] = round(100.0 * float(frame_hit.mean()), 5)
    mono_hit = (abs_y >= 10 ** (-0.5 / 20.0)).any(axis=1)
    runs = []
    current = 0
    for value in mono_hit:
        if value:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    rows["near_clip_runs_minus_0_5db"] = len(runs)
    rows["near_clip_longest_run_ms"] = round(1000.0 * (max(runs) if runs else 0) / sr, 3)
    return rows


def frame_view(x: np.ndarray, frame: int, hop: int) -> np.ndarray:
    if len(x) < frame:
        return x.reshape(1, -1)
    starts = np.arange(0, len(x) - frame + 1, hop)
    return np.stack([x[s : s + frame] for s in starts], axis=0)


def transient_flux(track: str, y: np.ndarray, sr: int) -> dict[str, object]:
    mono = y.mean(axis=1)
    frame = 2048
    hop = 512
    frames = frame_view(mono, frame, hop)
    window = signal.windows.hann(frame, sym=False)
    spec = np.abs(np.fft.rfft(frames * window[None, :], axis=1))
    diff = np.diff(spec, axis=0)
    flux = np.sqrt(np.sum(np.maximum(diff, 0.0) ** 2, axis=1))
    flux = flux / (np.mean(spec[:-1]) + 1e-12)
    rms_frames = np.sqrt(np.mean(frames * frames, axis=1))
    peak_frames = np.max(np.abs(frames), axis=1)
    crest_frames = np.array([db_amp(p) - db_amp(r) for p, r in zip(peak_frames, rms_frames)])
    return {
        "track": track,
        "flux_mean": round(float(np.mean(flux)), 4),
        "flux_p90": round(float(np.percentile(flux, 90)), 4),
        "flux_p99": round(float(np.percentile(flux, 99)), 4),
        "frame_crest_median_db": round(float(np.median(crest_frames)), 2),
        "frame_crest_p90_db": round(float(np.percentile(crest_frames, 90)), 2),
        "frame_crest_p99_db": round(float(np.percentile(crest_frames, 99)), 2),
    }


def low_frequency_peaks(track: str, y: np.ndarray, sr: int) -> list[dict[str, object]]:
    mono = y.mean(axis=1)
    freq, power = welch(mono, sr, 65536)
    mask = (freq >= 20) & (freq <= 200)
    f = freq[mask]
    p = power[mask]
    if len(p) == 0:
        return []
    smoothed = signal.medfilt(p, kernel_size=5)
    peaks, props = signal.find_peaks(smoothed, prominence=np.max(smoothed) * 0.005, distance=4)
    order = sorted(peaks, key=lambda i: smoothed[i], reverse=True)[:8]
    max_power = float(smoothed[order[0]]) if order else float(np.max(smoothed))
    rows = []
    for rank, idx in enumerate(order, 1):
        rows.append(
            {
                "track": track,
                "rank": rank,
                "freq_hz": round(float(f[idx]), 2),
                "relative_to_strongest_db": round(db_power(float(smoothed[idx]) / (max_power + 1e-30)), 2),
                "power_db": round(db_power(float(smoothed[idx])), 2),
            }
        )
    return rows


def five_second_segments(track: str, y: np.ndarray, sr: int) -> list[dict[str, object]]:
    rows = []
    segment = 5 * sr
    count = math.ceil(len(y) / segment)
    for idx in range(count):
        start = idx * segment
        end = min((idx + 1) * segment, len(y))
        if end - start < sr:
            continue
        seg = y[start:end]
        bands = band_energy_dict(seg, sr)
        macros = macro_from_bands(bands)
        left = seg[:, 0]
        right = seg[:, 1] if seg.shape[1] > 1 else seg[:, 0]
        mid = (left + right) / 2.0
        side = (left - right) / 2.0
        seg_rms = stereo_rms(seg)
        peak = float(np.max(np.abs(seg)))
        rows.append(
            {
                "track": track,
                "segment": idx + 1,
                "start_s": round(start / sr, 2),
                "end_s": round(end / sr, 2),
                "rms_dbfs": round(db_amp(seg_rms), 2),
                "peak_dbfs": round(db_amp(peak), 2),
                "crest_db": round(db_amp(peak) - db_amp(seg_rms), 2),
                "corr": round(float(np.corrcoef(left, right)[0, 1]), 4),
                "side_mid_db": round(db_amp(rms(side) / (rms(mid) + 1e-12)), 2),
                **{k: round(v, 3) for k, v in macros.items()},
            }
        )
    return rows


def decision_matrix(global_rows: list[dict[str, object]], peak_rows: list[dict[str, object]], flux_rows: list[dict[str, object]], band_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_peak = {r["track"]: r for r in peak_rows}
    by_flux = {r["track"]: r for r in flux_rows}
    band_by_track = {}
    for r in band_rows:
        band_by_track.setdefault(r["track"], {})[r["band"]] = float(r["energy_pct"])
    rows = []
    for g in global_rows:
        track = str(g["track"])
        bands = band_by_track[track]
        macros = macro_from_bands(bands)
        role = []
        if macros["sub_20_80"] >= 52:
            role.append("sub/808 anchor")
        if macros["presence_2_6k"] + macros["sparkle_air_6_16k"] >= 10:
            role.append("bright/presence anchor")
        if float(g["side_mid_db"]) > -8:
            role.append("wide stereo outlier")
        if float(g["side_mid_db"]) < -13:
            role.append("center-density anchor")
        if not role:
            role.append("balanced loudness reference")
        rows.append(
            {
                "track": track,
                "best_reference_role": ", ".join(role),
                "sub_20_80_pct": round(macros["sub_20_80"], 2),
                "mud_box_200_700_pct": round(macros["mud_box_200_700"], 2),
                "presence_air_2_16k_pct": round(macros["presence_2_6k"] + macros["sparkle_air_6_16k"], 2),
                "side_mid_db": g["side_mid_db"],
                "clip_density_frames_above_minus_0_5db_pct": by_peak[track]["frames_above_-0.5dbfs_pct"],
                "flux_p90": by_flux[track]["flux_p90"],
                "mix_use": usage_sentence(track, macros, float(g["side_mid_db"])),
            }
        )
    return rows


def usage_sentence(track: str, macros: dict[str, float], side_mid: float) -> str:
    if macros["sub_20_80"] >= 52:
        return "저역 기준으로 삼되, 이만큼의 sub를 마스터 EQ로 올리지 말고 킥/808 소스와 클리퍼에서 만들어야 함"
    if macros["presence_2_6k"] + macros["sparkle_air_6_16k"] >= 10:
        return "밝기와 lead/vocal 전면감을 비교할 기준. 이 곡보다 밝으면 피로할 가능성이 큼"
    if side_mid > -8:
        return "폭 기준 outlier. 전체 곡을 이 폭으로 밀기보다 특정 파트/후렴만 참고"
    if side_mid < -13:
        return "중앙 밀도와 mono 안정성 기준. sub, lead, snare 중심 위치 비교에 유용"
    return "전체 loudness와 균형 기준"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def heatmap(path: Path, row_labels: list[str], col_labels: list[str], matrix: np.ndarray, title: str, center_zero: bool = False) -> None:
    cell_w = 70
    cell_h = 26
    left = 170
    top = 64
    width = left + cell_w * len(col_labels) + 20
    height = top + cell_h * len(row_labels) + 30
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), title, fill=(0, 0, 0))
    values = matrix[np.isfinite(matrix)]
    if len(values) == 0:
        values = np.array([0.0])
    vmin = float(np.percentile(values, 5))
    vmax = float(np.percentile(values, 95))
    if center_zero:
        span = max(abs(vmin), abs(vmax), 1e-9)
        vmin, vmax = -span, span
    for col, label in enumerate(col_labels):
        draw.text((left + col * cell_w + 2, 35), label[:10], fill=(0, 0, 0))
    for row, label in enumerate(row_labels):
        y = top + row * cell_h
        draw.text((8, y + 7), label[:22], fill=(0, 0, 0))
        for col in range(len(col_labels)):
            value = float(matrix[row, col])
            if center_zero:
                level = (value - vmin) / (vmax - vmin + 1e-12)
                if value >= 0:
                    color = (int(255 * level), int(245 - 80 * level), int(245 - 180 * level))
                else:
                    color = (int(245 - 180 * (1 - level)), int(245 - 70 * (1 - level)), int(255 * (1 - level)))
            else:
                level = max(0.0, min(1.0, (value - vmin) / (vmax - vmin + 1e-12)))
                color = (int(245 * level + 20), int(245 - 130 * level), int(255 - 230 * level))
            x = left + col * cell_w
            draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), fill=color)
            draw.text((x + 5, y + 6), f"{value:.1f}", fill=(0, 0, 0))
    img.save(path)


def load_existing_global() -> list[dict[str, object]]:
    path = Path("/Users/hantaeheuk/Desktop/reference_analysis_estona_nib_deep/global_master_metrics.csv")
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as file:
        for row in csv.DictReader(file):
            converted: dict[str, object] = {}
            for key, value in row.items():
                if key in ("track", "path"):
                    converted[key] = value
                else:
                    try:
                        converted[key] = float(value)
                    except ValueError:
                        converted[key] = value
            rows.append(converted)
    return rows


def write_report(
    path: Path,
    global_rows: list[dict[str, object]],
    peak_rows: list[dict[str, object]],
    flux_rows: list[dict[str, object]],
    low_peak_rows: list[dict[str, object]],
    band_rows: list[dict[str, object]],
    band_phase_rows: list[dict[str, object]],
    segment_rows: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
) -> None:
    phase_by_track = {}
    for r in band_phase_rows:
        phase_by_track.setdefault(r["track"], []).append(r)
    low_by_track = {}
    for r in low_peak_rows:
        low_by_track.setdefault(r["track"], []).append(r)
    peak_by_track = {r["track"]: r for r in peak_rows}
    flux_by_track = {r["track"]: r for r in flux_rows}
    band_by_track = {}
    for r in band_rows:
        band_by_track.setdefault(r["track"], {})[r["band"]] = float(r["energy_pct"])
    decision_by_track = {r["track"]: r for r in matrix_rows}
    with path.open("w", encoding="utf-8") as f:
        f.write("# Estona,Nib 레퍼런스 포렌식 분석 추가 보고서\n\n")
        f.write("이 추가 보고서는 기존 LUFS/EQ 분석에서 더 들어가서, 실제 믹스 판단에 필요한 숨은 요소를 봅니다: 피크 밀도, 클리핑/리미터 흔적, 저역 주파수 중심, 대역별 스테레오/위상, mono 호환성, 5초 단위 arrangement 변화입니다.\n\n")
        f.write("## 1. 전체적으로 새로 확인한 사실\n\n")
        f.write("- 이 레퍼런스의 loudness는 단순히 limiter로 큰 것이 아니라, 샘플 피크 근처에 머무는 밀도가 매우 높습니다. 특히 `Dough`, `Lovee`는 -0.5 dBFS 이상에 닿는 frame 비율이 높아서 clipping/limiting 미학이 강합니다.\n")
        f.write("- 대부분의 곡은 sub와 kick/body가 중앙에 강하게 묶여 있습니다. `Missu`만 side 에너지가 분명히 넓고, 따라서 stereo reference로는 outlier입니다.\n")
        f.write("- 저역 peak는 트랙마다 다릅니다. 새 곡의 808 root가 어디에 있느냐에 따라 `Dough/Lovee/Why`를 같은 저역 레퍼런스로 무작정 쓰면 안 됩니다. 특정 root 대역을 맞춰 비교해야 합니다.\n")
        f.write("- 10 kHz 이상 air가 적은 이유는 고역이 없는 게 아니라, 고역이 limiter 앞에서 과하게 튀지 않도록 정리되어 있기 때문입니다. 밝게 만들고 싶어도 2-6 kHz front와 6-10 kHz texture를 분리해서 봐야 합니다.\n\n")

        f.write("## 2. 곡별 포렌식 노트\n\n")
        for g in global_rows:
            track = str(g["track"])
            bands = band_by_track[track]
            macros = macro_from_bands(bands)
            low_peaks = low_by_track.get(track, [])[:4]
            peak = peak_by_track[track]
            flux = flux_by_track[track]
            decision = decision_by_track[track]
            f.write(f"### {track}\n\n")
            f.write(f"- 레퍼런스 역할: {decision['best_reference_role']}.\n")
            f.write(f"- 사용법: {decision['mix_use']}.\n")
            f.write(f"- Macro EQ: sub 20-80 `{macros['sub_20_80']:.2f}%`, bass/body 80-200 `{macros['bass_body_80_200']:.2f}%`, mud/box 200-700 `{macros['mud_box_200_700']:.2f}%`, lead mid 700-2k `{macros['lead_mid_700_2k']:.2f}%`, presence 2-6k `{macros['presence_2_6k']:.2f}%`, sparkle/air 6-16k `{macros['sparkle_air_6_16k']:.2f}%`.\n")
            if low_peaks:
                peak_text = ", ".join(f"{p['freq_hz']} Hz ({p['relative_to_strongest_db']} dB)" for p in low_peaks)
                f.write(f"- 저역 주요 peak: {peak_text}.\n")
            f.write(f"- Peak density: -0.5 dBFS 이상 frame `{peak['frames_above_-0.5dbfs_pct']}%`, -1 dBFS 이상 frame `{peak['frames_above_-1dbfs_pct']}%`, 가장 긴 near-clip run `{peak['near_clip_longest_run_ms']} ms`.\n")
            f.write(f"- Transient/flux: flux p90 `{flux['flux_p90']}`, flux p99 `{flux['flux_p99']}`, frame crest median `{flux['frame_crest_median_db']} dB`.\n")
            risky_phase = sorted(phase_by_track[track], key=lambda r: float(r["side_mid_db"]), reverse=True)[:3]
            phase_text = ", ".join(f"{r['band']} side/mid {r['side_mid_db']} dB corr {r['corr']}" for r in risky_phase)
            f.write(f"- 가장 넓은 대역: {phase_text}.\n")
            segs = [r for r in segment_rows if r["track"] == track]
            loudest = max(segs, key=lambda r: float(r["rms_dbfs"]))
            subbest = max(segs, key=lambda r: float(r["sub_20_80"]))
            widest = max(segs, key=lambda r: float(r["side_mid_db"]))
            f.write(f"- 5초 구간 기준: loudest `{loudest['start_s']}-{loudest['end_s']}s`, sub 최대 `{subbest['start_s']}-{subbest['end_s']}s`, stereo 최대 `{widest['start_s']}-{widest['end_s']}s`.\n\n")

        f.write("## 3. 새 믹스를 비교할 때의 체크리스트\n\n")
        f.write("- 먼저 새 곡의 808/root peak를 찾고, 같은 low root를 가진 레퍼런스와 비교합니다. root가 40 Hz인 곡과 70 Hz인 곡은 같은 sub percentage여도 체감이 다릅니다.\n")
        f.write("- 후렴/drop의 5초 구간 RMS가 레퍼런스 loudest 구간에 비해 2 dB 이상 낮으면, 마스터 전에 편곡/소스 밀도부터 보강합니다.\n")
        f.write("- -0.5 dBFS 이상 frame 비율이 레퍼런스보다 너무 낮으면 loudness가 약하게 느껴질 수 있고, 너무 높으면 찢어짐/납작함이 먼저 납니다.\n")
        f.write("- 200-700 Hz macro가 레퍼런스보다 높으면 마스터에서 loudness를 밀수록 탁해집니다. 이 구간은 마스터 EQ보다 트랙 EQ/버스 EQ에서 정리합니다.\n")
        f.write("- side/mid가 `Missu`처럼 높지 않은 이상, 전체 믹스를 억지로 넓히지 않습니다. sub와 lead center가 기준입니다.\n")
        f.write("- 10 kHz 이상 air가 부족하다고 느껴도 바로 shelf를 올리지 말고, 2-6 kHz front, 6-10 kHz texture, transient를 따로 확인합니다.\n")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    global_rows = load_existing_global()
    if not global_rows:
        raise SystemExit("Run deep_reference_analysis.py first to create global metrics.")

    band_rows = []
    phase_rows = []
    peak_rows = []
    flux_rows = []
    low_peak_rows = []
    segment_rows = []

    for raw in TRACKS:
        path = Path(raw)
        track = clean_track_name(path)
        sr, y = read_audio(path)
        bands = band_energy_dict(y, sr)
        for name, value in bands.items():
            low, high = next((lo, hi) for n, lo, hi in BANDS if n == name)
            band_rows.append({"track": track, "band": name, "low_hz": low, "high_hz": high, "energy_pct": round(value, 5)})
        phase_rows.extend(band_stereo_phase(track, y, sr))
        peak_rows.append(peak_density(track, y, sr))
        flux_rows.append(transient_flux(track, y, sr))
        low_peak_rows.extend(low_frequency_peaks(track, y, sr))
        segment_rows.extend(five_second_segments(track, y, sr))

    matrix_rows = decision_matrix(global_rows, peak_rows, flux_rows, band_rows)

    write_csv(OUTDIR / "forensic_eq_band_energy.csv", band_rows)
    write_csv(OUTDIR / "forensic_band_stereo_phase.csv", phase_rows)
    write_csv(OUTDIR / "forensic_peak_density.csv", peak_rows)
    write_csv(OUTDIR / "forensic_transient_flux.csv", flux_rows)
    write_csv(OUTDIR / "forensic_low_frequency_peaks.csv", low_peak_rows)
    write_csv(OUTDIR / "forensic_5s_segments.csv", segment_rows)
    write_csv(OUTDIR / "forensic_decision_matrix.csv", matrix_rows)
    write_report(OUTDIR / "forensic_korean_report.md", global_rows, peak_rows, flux_rows, low_peak_rows, band_rows, phase_rows, segment_rows, matrix_rows)

    tracks = [clean_track_name(Path(p)) for p in TRACKS]
    band_names = [b[0] for b in BANDS]
    side_matrix = np.array(
        [[float(next(r["side_mid_db"] for r in phase_rows if r["track"] == track and r["band"] == band)) for band in band_names] for track in tracks]
    )
    heatmap(OUTDIR / "forensic_side_mid_by_band.png", tracks, [b.replace("_", " ") for b in band_names], side_matrix, "Side/Mid dB by band", center_zero=True)

    corr_matrix = np.array(
        [[float(next(r["corr"] for r in phase_rows if r["track"] == track and r["band"] == band)) for band in band_names] for track in tracks]
    )
    heatmap(OUTDIR / "forensic_correlation_by_band.png", tracks, [b.replace("_", " ") for b in band_names], corr_matrix, "L/R correlation by band")

    macro_names = [m[0] for m in MACRO_BANDS]
    macro_matrix = []
    for track in tracks:
        bands = {r["band"]: float(r["energy_pct"]) for r in band_rows if r["track"] == track}
        macros = macro_from_bands(bands)
        macro_matrix.append([macros[m] for m in macro_names])
    heatmap(OUTDIR / "forensic_macro_eq_heatmap.png", tracks, macro_names, np.array(macro_matrix), "Macro EQ energy percent")

    peak_cols = ["frames_above_-0.5dbfs_pct", "frames_above_-1dbfs_pct", "frames_above_-2dbfs_pct", "frames_above_-3dbfs_pct", "frames_above_-6dbfs_pct"]
    peak_matrix = np.array([[float(next(r[c] for r in peak_rows if r["track"] == track)) for c in peak_cols] for track in tracks])
    heatmap(OUTDIR / "forensic_peak_density_heatmap.png", tracks, peak_cols, peak_matrix, "Peak density frame percent")

    print(OUTDIR / "forensic_korean_report.md")
    print(OUTDIR / "forensic_decision_matrix.csv")
    print(OUTDIR / "forensic_band_stereo_phase.csv")
    print(OUTDIR / "forensic_peak_density.csv")
    print(OUTDIR / "forensic_low_frequency_peaks.csv")
    print(OUTDIR / "forensic_5s_segments.csv")
    print(OUTDIR / "forensic_side_mid_by_band.png")
    print(OUTDIR / "forensic_correlation_by_band.png")
    print(OUTDIR / "forensic_macro_eq_heatmap.png")
    print(OUTDIR / "forensic_peak_density_heatmap.png")


if __name__ == "__main__":
    main()
