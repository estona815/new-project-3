from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.io import wavfile

from audio_metrics import audio_quality_metrics, bandpass, mono, rms, rms_db, spectral_band_rms, to_stereo
from audio_qc import analyze_audio_array
from suno_source_classifier import classify_source_file


AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}


def _safe_extract_audio(zip_path: Path, target_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            name = member.filename
            if member.is_dir():
                continue
            candidate = Path(name)
            if candidate.is_absolute() or ".." in candidate.parts:
                continue
            if candidate.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            destination = target_dir / candidate.name
            with archive.open(member) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(destination)
    return extracted


def _locate_existing(path_text: str | Path, project_dir: Path) -> Path | None:
    path = Path(path_text)
    if path.exists():
        return path
    basename = path.name
    matches = sorted(project_dir.rglob(basename))
    if matches:
        return matches[0]
    return None


def _audio_from_source(source: str | Path, project_dir: Path, temp_dir: Path) -> tuple[Path | None, str]:
    resolved = _locate_existing(source, project_dir)
    if not resolved:
        return None, f"missing: {source}"
    if resolved.suffix.lower() == ".zip":
        extracted = _safe_extract_audio(resolved, temp_dir / resolved.stem)
        if not extracted:
            return None, f"zip contained no supported audio: {resolved}"
        return sorted(extracted, key=lambda item: item.stat().st_size, reverse=True)[0], f"extracted from {resolved}"
    if resolved.suffix.lower() in AUDIO_EXTENSIONS:
        return resolved, "direct audio"
    return None, f"unsupported source: {resolved}"


def _read_audio(path: Path, temp_dir: Path) -> tuple[int, np.ndarray, dict[str, object]]:
    codec = path.suffix.lower().lstrip(".") or "unknown"
    if path.suffix.lower() == ".wav":
        sr, data = wavfile.read(path)
        bit_depth = str(data.dtype)
        samples = data.astype(np.float32, copy=False)
        if np.issubdtype(data.dtype, np.integer):
            info = np.iinfo(data.dtype)
            samples = samples / max(abs(info.min), info.max)
        return int(sr), to_stereo(np.nan_to_num(samples)), {"codec": codec, "bit_depth": bit_depth}

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg  # type: ignore

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    if not ffmpeg:
        raise RuntimeError(f"ffmpeg unavailable for decoding {path.suffix}")
    decoded = temp_dir / f"{path.stem}_decoded.wav"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le", str(decoded)],
        check=True,
    )
    sr, data = wavfile.read(decoded)
    return int(sr), to_stereo(np.nan_to_num(data.astype(np.float32))), {"codec": codec, "bit_depth": "decoded_float32"}


def _window_movement(audio: np.ndarray, sample_rate: int) -> dict[str, object]:
    samples = mono(audio)
    window = max(1, int(sample_rate * 0.4))
    hop = max(1, int(sample_rate * 0.1))
    values = []
    for start in range(0, max(1, samples.size - window), hop):
        values.append(rms_db(samples[start : start + window]))
    if not values:
        values = [rms_db(samples)]
    arr = np.asarray(values, dtype=np.float32)
    return {
        "rms_window_p10_dbfs": round(float(np.percentile(arr, 10)), 2),
        "rms_window_median_dbfs": round(float(np.percentile(arr, 50)), 2),
        "rms_window_p90_dbfs": round(float(np.percentile(arr, 90)), 2),
        "rms_window_movement_db": round(float(np.percentile(arr, 90) - np.percentile(arr, 10)), 2),
    }


def _spectral_centroid(audio: np.ndarray, sample_rate: int) -> float:
    samples = mono(audio)
    if samples.size < 32:
        return 0.0
    if samples.size > sample_rate * 30:
        samples = samples[: sample_rate * 30]
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(samples.size)))
    freqs = np.fft.rfftfreq(samples.size, 1.0 / sample_rate)
    return round(float(np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-12)), 2)


def _band_ratio(audio: np.ndarray, sample_rate: int, low: float, high: float) -> float:
    full = rms(mono(audio)[:, None]) + 1e-12
    band = rms(bandpass(mono(audio)[:, None], low, high, sample_rate)) + 1e-12
    return round(float(20.0 * np.log10(band / full)), 2)


def analyze_profile(source: str | Path, project_dir: str | Path, *, label: str) -> dict[str, object]:
    root = Path(project_dir)
    with tempfile.TemporaryDirectory(prefix="suno_ref_compare_") as tmp:
        temp_dir = Path(tmp)
        audio_path, note = _audio_from_source(source, root, temp_dir)
        if not audio_path:
            return {
                "label": label,
                "source": str(source),
                "available": False,
                "note": note,
                "classification": classify_source_file(source).category,
            }
        try:
            sample_rate, audio, format_info = _read_audio(audio_path, temp_dir)
        except Exception as exc:
            return {
                "label": label,
                "source": str(source),
                "available": False,
                "note": f"{note}; analysis failed: {exc}",
                "classification": classify_source_file(audio_path).category,
            }
        quality = audio_quality_metrics(audio, sample_rate)
        qc = analyze_audio_array(audio, sample_rate, source_name=str(audio_path), category=classify_source_file(audio_path).category)
        return {
            "label": label,
            "source": str(source),
            "resolved_audio": str(audio_path),
            "available": True,
            "note": note,
            "classification": classify_source_file(audio_path).category,
            "format": {
                "sample_rate": sample_rate,
                "duration_s": round(float(audio.shape[0] / sample_rate), 3),
                **format_info,
            },
            "metrics": {
                **quality,
                **_window_movement(audio, sample_rate),
                "spectral_centroid_hz": _spectral_centroid(audio, sample_rate),
                "low_end_concentration_db": _band_ratio(audio, sample_rate, 20.0, 140.0),
                "high_frequency_harshness_db": _band_ratio(audio, sample_rate, 5_000.0, 9_000.0),
                "air_band_db": _band_ratio(audio, sample_rate, 9_000.0, 16_000.0),
                "spectral_band_rms_dbfs": spectral_band_rms(audio, sample_rate),
            },
            "qc_issue_count": len(qc["issues"]),
            "qc_issues": qc["issues"],
        }


def _metric(profile: dict[str, object], key: str, default: float = 0.0) -> float:
    metrics = profile.get("metrics", {})
    if not isinstance(metrics, dict):
        return default
    value = metrics.get(key, default)
    return float(value) if isinstance(value, (int, float)) else default


def comparison_actions(current: dict[str, object], reference: dict[str, object]) -> list[str]:
    actions = [
        "Use the reference as a technical compass only. Do not copy melody, lyric, arrangement, chord movement, topline, artist identity, or musical content.",
        "Keep MP3/full-master files as problem_reference/reference_only. Production rebuild stays blocked unless WAV stems are present.",
    ]
    if not current.get("available"):
        actions.append("Current/problem reference was not available, so compare again after placing it in the project.")
        return actions
    if not reference.get("available"):
        actions.append("Technical commercial reference was not available; use current QC plus manual listening until a WAV reference is supplied.")
        return actions

    if _metric(current, "low_end_concentration_db") > _metric(reference, "low_end_concentration_db") + 2.0:
        actions.append("EQ: current low end is more concentrated. Tighten sub/80-200 Hz before vocal processing and keep bass mono below 120 Hz.")
    if _metric(current, "rms_window_movement_db") < _metric(reference, "rms_window_movement_db") - 1.0:
        actions.append("Dynamics: current movement is flatter. Avoid crushed master limiting; aim for premaster headroom and 1-2 dB glue compression max.")
    if _metric(current, "side_mid_db") > _metric(reference, "side_mid_db") + 2.0:
        actions.append("M/S space: side energy is too strong or phasey. Reduce side low-mids and check mono compatibility.")
    else:
        actions.append("M/S space: keep lead vocal/bass centered and widen only synth/BGV above the low-mid range.")
    if _metric(current, "harshness_score_db") > _metric(reference, "harshness_score_db") + 2.0:
        actions.append("Lead vocal/dynamic EQ: tame 5-9 kHz harshness dynamically; do not use dull static cuts that bury consonants.")
    else:
        actions.append("Lead vocal: build clarity around 3-5 kHz, de-ess only harsh syllables, and keep pitch correction before dynamic EQ.")
    actions.append("Reverb: use filtered plate/room sends with 20-35 ms predelay and ducking under the lead vocal.")
    actions.append("Delay: use tempo-synced throw automation at phrase ends, not constant messy delay under every line.")
    actions.append("Master bus: true peak ceiling -1.0 dBTP, do not chase reference loudness blindly, and avoid over-limiting if vocal stability suffers.")
    return actions


def write_reference_comparison(project_dir: str | Path, current: str | Path, reference: str | Path) -> dict[str, object]:
    root = Path(project_dir)
    report_dir = root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    current_profile = analyze_profile(current, root, label="current_problem")
    reference_profile = analyze_profile(reference, root, label="technical_reference")
    actions = comparison_actions(current_profile, reference_profile)
    payload = {
        "schema_version": "reference_comparison.v0.5",
        "current": current_profile,
        "reference": reference_profile,
        "actions": actions,
    }
    (report_dir / "current_problem_profile.json").write_text(json.dumps(current_profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / "reference_profile.json").write_text(json.dumps(reference_profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Reference Comparison",
        "",
        "- Reference use policy: technical direction only, no musical cloning.",
        f"- Current/problem source available: {str(bool(current_profile.get('available'))).lower()}",
        f"- Technical reference available: {str(bool(reference_profile.get('available'))).lower()}",
        "",
    ]
    for profile in (current_profile, reference_profile):
        lines.extend(
            [
                f"## {profile['label']}",
                "",
                f"- Source: `{profile['source']}`",
                f"- Classification: `{profile.get('classification', 'unknown')}`",
                f"- Note: {profile.get('note', '')}",
            ]
        )
        if profile.get("available"):
            metrics = profile["metrics"]
            fmt = profile["format"]
            lines.extend(
                [
                    f"- Format: {fmt['sample_rate']} Hz, {fmt['bit_depth']}, codec `{fmt['codec']}`, {fmt['duration_s']} s",
                    f"- LUFS-like proxy: {metrics['lufs_like_proxy_db']} dB",
                    f"- RMS movement: {metrics['rms_window_movement_db']} dB",
                    f"- Peak/oversampled proxy: {metrics['peak_dbfs']} / {metrics['oversampled_peak_proxy_dbfs']} dBFS",
                    f"- Stereo corr / side-mid: {metrics['mono_compatibility']['left_right_correlation']} / {metrics['side_mid_db']} dB",
                    f"- Low-end concentration: {metrics['low_end_concentration_db']} dB",
                    f"- Harshness risk: {metrics['high_frequency_harshness_db']} dB",
                    f"- QC issue count: {profile['qc_issue_count']}",
                ]
            )
        lines.append("")
    lines.extend(["## Action Translation", ""])
    for action in actions:
        lines.append(f"- {action}")
    (report_dir / "reference_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload
