#!/usr/bin/env python3
"""Create analysis-only proxy stems from mastered mixes/references.

This is not a substitute for real multitracks or Demucs/Open-Unmix stems. It is
an automation aid when only masters are available. Outputs are deliberately
labeled "proxy" and must not be treated as release-quality separated stems.
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import soundfile as sf
from scipy import ndimage, signal


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
INPUT_DIRS = [
    PROJECT_ROOT / "00_AUDIO_INPUT",
    Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48."),
]
OUTPUT_ROOT = PROJECT_ROOT / "audio_work" / "proxy_stems"
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a"}
EPS = 1e-12


def slugify(name: str) -> str:
    text = Path(name).stem.lower()
    text = text.replace(",", "_").replace(" ", "_")
    text = re.sub(r"[^a-z0-9가-힣_+-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "audio"


def find_audio_files() -> List[Path]:
    files = []
    for folder in INPUT_DIRS:
        if folder.exists():
            files.extend(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    unique = {}
    for path in files:
        unique[str(path.resolve())] = path
    return sorted(unique.values())


def ensure_stereo(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return np.column_stack([audio, audio])
    if audio.shape[1] == 1:
        return np.repeat(audio, 2, axis=1)
    return audio[:, :2]


def db_amp(value: float) -> float:
    return 20 * math.log10(max(abs(float(value)), EPS))


def db_power(value: float) -> float:
    return 10 * math.log10(max(float(value), EPS))


def sos_filter(audio: np.ndarray, sr: int, kind: str, cutoff) -> np.ndarray:
    nyq = sr / 2.0
    if kind == "lowpass":
        wn = min(float(cutoff) / nyq, 0.95)
        sos = signal.butter(4, wn, btype="lowpass", output="sos")
    elif kind == "highpass":
        wn = max(float(cutoff) / nyq, 0.0001)
        sos = signal.butter(4, wn, btype="highpass", output="sos")
    elif kind == "bandpass":
        low, high = cutoff
        wn = [max(float(low) / nyq, 0.0001), min(float(high) / nyq, 0.95)]
        if wn[1] <= wn[0]:
            return audio.copy()
        sos = signal.butter(4, wn, btype="bandpass", output="sos")
    else:
        raise ValueError(kind)
    try:
        return signal.sosfiltfilt(sos, audio, axis=0)
    except Exception:
        return signal.sosfilt(sos, audio, axis=0)


def stft_hpss(mono: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    nperseg = 4096
    noverlap = 3072
    freqs, times, zxx = signal.stft(mono, fs=sr, nperseg=nperseg, noverlap=noverlap, boundary="zeros")
    mag = np.abs(zxx)
    harmonic = ndimage.median_filter(mag, size=(1, 31))
    percussive = ndimage.median_filter(mag, size=(31, 1))
    hmask = harmonic / (harmonic + percussive + EPS)
    pmask = percussive / (harmonic + percussive + EPS)
    _, h = signal.istft(zxx * hmask, fs=sr, nperseg=nperseg, noverlap=noverlap, input_onesided=True)
    _, p = signal.istft(zxx * pmask, fs=sr, nperseg=nperseg, noverlap=noverlap, input_onesided=True)
    n = len(mono)
    return h[:n], p[:n]


def normalize_proxy(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    max_abs = float(np.max(np.abs(x)) + EPS)
    if max_abs > peak:
        x = x * (peak / max_abs)
    return np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)


def stereo_from_mono(x: np.ndarray) -> np.ndarray:
    return np.column_stack([x, x])


def feature_summary(audio: np.ndarray, sr: int) -> dict:
    if audio.ndim == 2:
        mono = audio.mean(axis=1)
        stereo_rms = float(np.sqrt(np.mean(audio * audio) + EPS))
        mono_rms = float(np.sqrt(np.mean(mono * mono) + EPS))
        if mono_rms < stereo_rms * 0.05:
            mono = audio[:, 0]
    else:
        mono = audio
    peak = float(np.max(np.abs(audio)) + EPS)
    rms = float(np.sqrt(np.mean(mono * mono) + EPS))
    freqs, pxx = signal.welch(mono, fs=sr, nperseg=min(8192, max(1024, int(sr * 0.17))))
    total = float(np.sum(pxx) + EPS)

    def band(low, high):
        mask = (freqs >= low) & (freqs < high)
        return db_power(float(np.sum(pxx[mask]) + EPS) / total)

    return {
        "peak_dbfs": db_amp(peak),
        "rms_dbfs": db_amp(rms),
        "crest_factor_db": db_amp(peak / max(rms, EPS)),
        "band_20_120_db": band(20, 120),
        "band_120_350_db": band(120, 350),
        "band_350_1000_db": band(350, 1000),
        "band_1k_4k_db": band(1000, 4000),
        "band_4k_8k_db": band(4000, 8000),
        "band_8k_20k_db": band(8000, min(20000, sr / 2 * 0.95)),
    }


def tail_proxy(audio: np.ndarray, sr: int) -> np.ndarray:
    # Emphasize sustained low-transient material and stereo tail energy.
    mono = audio.mean(axis=1)
    analytic_env = np.abs(signal.hilbert(mono))
    smooth = sos_filter(analytic_env.reshape(-1, 1), sr, "lowpass", 12.0)[:, 0]
    transient = np.abs(np.diff(smooth, prepend=smooth[0]))
    sustain_mask = 1.0 - np.clip(transient / (np.percentile(transient, 95) + EPS), 0, 1)
    sustain_mask = sos_filter(sustain_mask.reshape(-1, 1), sr, "lowpass", 8.0)[:, 0]
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    tail = (mid * 0.35 + side * 0.75) * sustain_mask
    tail = sos_filter(tail.reshape(-1, 1), sr, "bandpass", (350, min(12000, sr * 0.45)))[:, 0]
    return stereo_from_mono(tail)


def create_proxy_stems(path: Path) -> dict:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float64")
    audio = ensure_stereo(audio)
    slug = slugify(path.name)
    outdir = OUTPUT_ROOT / slug
    outdir.mkdir(parents=True, exist_ok=True)
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    harmonic, percussive = stft_hpss(mid, sr)

    proxies = {
        "sub_bass_proxy": stereo_from_mono(sos_filter(mid.reshape(-1, 1), sr, "lowpass", 120.0)[:, 0]),
        "center_vocal_proxy": stereo_from_mono(sos_filter(mid.reshape(-1, 1), sr, "bandpass", (150.0, 6500.0))[:, 0] * 0.75),
        "percussive_drum_proxy": stereo_from_mono(sos_filter(percussive.reshape(-1, 1), sr, "bandpass", (45.0, 12000.0))[:, 0]),
        "harmonic_music_proxy": stereo_from_mono(sos_filter(harmonic.reshape(-1, 1), sr, "bandpass", (120.0, 12000.0))[:, 0]),
        "side_space_proxy": np.column_stack([side, -side]),
        "air_hash_proxy": stereo_from_mono(sos_filter(mid.reshape(-1, 1), sr, "bandpass", (6500.0, min(18000.0, sr * 0.45)))[:, 0]),
        "reverb_tail_proxy": tail_proxy(audio, sr),
    }

    outputs = []
    for name, data in proxies.items():
        data = normalize_proxy(data)
        out = outdir / f"{slug}_{name}.flac"
        sf.write(str(out), data, sr, format="FLAC", subtype="PCM_16")
        outputs.append({
            "proxy_type": name,
            "path": str(out),
            "warning": proxy_warning(name),
            "features": feature_summary(data, sr),
        })
    return {
        "source_file": str(path),
        "slug": slug,
        "sample_rate": sr,
        "duration_sec": float(len(audio) / sr),
        "output_dir": str(outdir),
        "outputs": outputs,
    }


def proxy_warning(name: str) -> str:
    warnings = {
        "center_vocal_proxy": "Center mid-band proxy only; not an isolated vocal stem.",
        "percussive_drum_proxy": "HPSS percussive proxy; transients from vocal/instruments may leak.",
        "harmonic_music_proxy": "HPSS harmonic proxy; vocal and sustained synth/guitar may overlap.",
        "sub_bass_proxy": "Low-frequency proxy for mono/bass analysis, not separate 808/kick.",
        "side_space_proxy": "Side channel proxy for width/reverb analysis, not musical stem.",
        "air_hash_proxy": "High-band proxy for fizz/hash/de-ess analysis.",
        "reverb_tail_proxy": "Sustain/side-tail proxy; not an actual reverb return.",
    }
    return warnings.get(name, "Analysis-only proxy stem.")


def aggregate_matrix(results: List[dict]) -> List[dict]:
    rows = []
    for result in results:
        for out in result["outputs"]:
            row = {
                "source": Path(result["source_file"]).name,
                "proxy_type": out["proxy_type"],
                "path": out["path"],
                **out["features"],
            }
            rows.append(row)
    return rows


def write_reports(results: List[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "status": "proxy_stems_created",
        "policy": {
            "analysis_only": True,
            "not_release_quality_stems": True,
            "do_not_use_to_copy_reference_creative_elements": True,
            "demucs_not_used": True,
        },
        "results": results,
    }
    (REPORTS_DIR / "proxy_stem_separation_report.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    matrix = aggregate_matrix(results)
    with (REPORTS_DIR / "proxy_stem_feature_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix[0].keys()) if matrix else ["source"])
        writer.writeheader()
        writer.writerows(matrix)

    lines = [
        "# Proxy Stem Separation Report",
        "",
        "This created analysis-only proxy stems. These are not release-quality separated stems and should not be used as copied musical material.",
        "",
        f"- Sources processed: {len(results)}",
        f"- Proxy stem folders: `{OUTPUT_ROOT}`",
        "",
        "## Proxy Types",
        "- `center_vocal_proxy`: center mid-band clue, not isolated vocal.",
        "- `percussive_drum_proxy`: HPSS transient/percussive clue.",
        "- `harmonic_music_proxy`: sustained/harmonic clue.",
        "- `sub_bass_proxy`: low-frequency mono/bass clue.",
        "- `side_space_proxy`: side/reverb/width clue.",
        "- `air_hash_proxy`: high fizz/hash clue.",
        "- `reverb_tail_proxy`: sustain/side-tail clue.",
        "",
        "## Files",
    ]
    for result in results:
        lines.append(f"### {Path(result['source_file']).name}")
        for out in result["outputs"]:
            features = out["features"]
            lines.append(
                f"- `{out['proxy_type']}`: RMS {features['rms_dbfs']:.2f} dBFS, 20-120 {features['band_20_120_db']:.2f}, 1k-4k {features['band_1k_4k_db']:.2f}, 8k-20k {features['band_8k_20k_db']:.2f}. {out['warning']}"
            )
    (REPORTS_DIR / "proxy_stem_separation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reaper_import_script(results: List[dict]) -> None:
    script = PROJECT_ROOT / "reaper" / "import_proxy_stems_for_analysis.lua"
    script.parent.mkdir(parents=True, exist_ok=True)
    paths = [out["path"] for result in results for out in result["outputs"]]
    quoted = ",\n".join(f'  "{p}"' for p in paths)
    script.write_text(
        f"""-- Import analysis-only proxy stems into REAPER.
-- These are not release stems. Use them for measurement/routing/QC only.

local files = {{
{quoted}
}}

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
for _, path in ipairs(files) do
  reaper.InsertMedia(path, 1)
end
reaper.AddProjectMarker2(0, false, 0, 0, "ESTONA proxy stems imported for analysis only", -1, 0)
reaper.PreventUIRefresh(-1)
reaper.UpdateArrange()
reaper.Undo_EndBlock("Import ESTONA proxy stems for analysis", -1)
""",
        encoding="utf-8",
    )


def main() -> None:
    files = find_audio_files()
    if not files:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / "proxy_stem_separation_report.md").write_text("No audio files found for proxy stem separation.\n", encoding="utf-8")
        print(json.dumps({"status": "no_audio_files"}, indent=2))
        return
    results = [create_proxy_stems(path) for path in files]
    write_reports(results)
    write_reaper_import_script(results)
    print(json.dumps({"status": "proxy_stems_created", "sources": len(results), "proxy_files": sum(len(r["outputs"]) for r in results), "output_root": str(OUTPUT_ROOT)}, indent=2))


if __name__ == "__main__":
    main()
