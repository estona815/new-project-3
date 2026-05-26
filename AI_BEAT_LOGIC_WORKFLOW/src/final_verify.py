from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from loudness_estimation import rms_db


def expected_sample_rate(export_format: str) -> int:
    return 44100 if export_format == "wav24_44k" else 48000


def expected_final_name(export_format: str) -> str:
    return "final_suno_logic_processed_24bit_44k.wav" if export_format == "wav24_44k" else "final_suno_logic_processed_24bit_48k.wav"


def expected_bit_depth(export_format: str) -> int:
    return 24 if export_format in {"wav24_44k", "wav24_48k"} else 24


def clipping_count(path: Path) -> int:
    _metadata, channels = read_wav_float(path)
    return sum(1 for channel in channels for sample in channel if abs(sample) >= 0.999969)


def rms_for_wav(path: Path) -> float:
    _metadata, channels = read_wav_float(path)
    samples = [sample for channel in channels for sample in channel]
    return rms_db(samples)


def _base_result(path: Path, requested_format: str) -> dict[str, Any]:
    return {
        "ok": False,
        "path": str(path),
        "exists": path.exists(),
        "file_size": path.stat().st_size if path.exists() else 0,
        "duration_seconds": None,
        "sample_rate": None,
        "expected_sample_rate": expected_sample_rate(requested_format),
        "channels": None,
        "codec_name": None,
        "bit_depth_verified": False,
        "bit_depth": None,
        "format_verified": False,
        "peak_dbfs": None,
        "rms_dbfs": None,
        "clipping_count": None,
        "errors": [],
    }


def _run_probe(command: list[str]) -> tuple[bool, str, str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stdout, result.stderr
    return True, result.stdout, result.stderr


def _apply_ffprobe(result: dict[str, Any], path: Path) -> None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return
    ok, stdout, stderr = _run_probe(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,bits_per_sample,duration",
            "-of",
            "json",
            str(path),
        ]
    )
    if not ok:
        result["errors"].append(f"ffprobe failed: {stderr.strip() or stdout.strip() or 'no diagnostic output'}")
        return
    try:
        payload = json.loads(stdout)
        stream = (payload.get("streams") or [{}])[0]
    except (json.JSONDecodeError, IndexError, TypeError) as error:
        result["errors"].append(f"ffprobe output could not be parsed: {error}")
        return
    result["codec_name"] = stream.get("codec_name") or result["codec_name"]
    if stream.get("sample_rate"):
        result["sample_rate"] = int(stream["sample_rate"])
    if stream.get("channels") is not None:
        result["channels"] = int(stream["channels"])
    if stream.get("duration") not in {None, "N/A"}:
        result["duration_seconds"] = float(stream["duration"])
    bits = stream.get("bits_per_sample")
    if bits not in {None, "N/A", 0, "0"}:
        result["bit_depth"] = int(bits)
        result["bit_depth_verified"] = int(bits) == expected_bit_depth("wav24_48k")


def _apply_afinfo(result: dict[str, Any], path: Path) -> None:
    if result["bit_depth_verified"] and result["codec_name"]:
        return
    afinfo = shutil.which("afinfo")
    if not afinfo:
        return
    ok, stdout, stderr = _run_probe([afinfo, str(path)])
    if not ok:
        result["errors"].append(f"afinfo failed: {stderr.strip() or stdout.strip() or 'no diagnostic output'}")
        return
    lower = stdout.lower()
    if "linear pcm" in lower:
        result["codec_name"] = result["codec_name"] or "linear_pcm"
    if "24-bit" in lower or "24 bit" in lower:
        result["bit_depth"] = 24
        result["bit_depth_verified"] = True
    elif "16-bit" in lower or "16 bit" in lower:
        result["bit_depth"] = 16
        result["bit_depth_verified"] = False


def _apply_python_metrics(result: dict[str, Any], path: Path) -> None:
    try:
        metadata, channels = read_wav_float(path)
    except Exception as error:  # noqa: BLE001 - verifier reports clean errors.
        result["errors"].append(f"Python WAV analysis failed: {error}")
        return
    samples = [sample for channel in channels for sample in channel]
    peak = max((abs(sample) for sample in samples), default=0.0)
    result["duration_seconds"] = result["duration_seconds"] if result["duration_seconds"] is not None else metadata["duration_seconds"]
    result["sample_rate"] = result["sample_rate"] if result["sample_rate"] is not None else metadata["sample_rate"]
    result["channels"] = result["channels"] if result["channels"] is not None else metadata["channels"]
    result["bit_depth"] = result["bit_depth"] if result["bit_depth"] is not None else metadata["bit_depth"]
    result["codec_name"] = result["codec_name"] or ("pcm_s24le" if metadata["audio_format"] == "pcm" and metadata["bit_depth"] == 24 else metadata["audio_format"])
    result["bit_depth_verified"] = bool(result["bit_depth_verified"] or (metadata["audio_format"] == "pcm" and metadata["bit_depth"] == 24))
    result["peak_dbfs"] = 20.0 * math.log10(peak) if peak > 0 else float("-inf")
    result["rms_dbfs"] = rms_db(samples)
    result["clipping_count"] = sum(1 for sample in samples if abs(sample) >= 0.999969)


def verify_final_wav(final_wav_path: str | Path, requested_format: str) -> dict[str, Any]:
    path = Path(final_wav_path).expanduser()
    result = _base_result(path, requested_format)
    if not path.exists():
        result["errors"].append(f"final WAV missing: {path}")
        return result
    if path.stat().st_size <= 0:
        result["errors"].append(f"final WAV is empty: {path}")
        return result

    _apply_ffprobe(result, path)
    _apply_afinfo(result, path)
    _apply_python_metrics(result, path)

    if result["duration_seconds"] is None or float(result["duration_seconds"]) <= 0.0:
        result["errors"].append("duration could not be read")
    if result["sample_rate"] != result["expected_sample_rate"]:
        result["errors"].append(f"sample rate mismatch: expected {result['expected_sample_rate']}, got {result['sample_rate']}")
    if not result["bit_depth_verified"] or result["bit_depth"] != expected_bit_depth(requested_format):
        result["errors"].append(f"24-bit PCM format could not be verified; got bit_depth={result['bit_depth']}, codec={result['codec_name']}")
    if result["peak_dbfs"] is None or result["rms_dbfs"] is None or result["clipping_count"] is None:
        result["errors"].append("peak/RMS/clipping metrics could not be read")
    if result["clipping_count"] and int(result["clipping_count"]) > 0:
        result["errors"].append("clipped samples detected")

    pcm_codec = result["codec_name"] in {"pcm_s24le", "linear_pcm"} or str(result["codec_name"]).startswith("pcm")
    result["format_verified"] = bool(
        result["sample_rate"] == result["expected_sample_rate"]
        and result["bit_depth_verified"]
        and result["bit_depth"] == expected_bit_depth(requested_format)
        and pcm_codec
    )
    result["errors"] = list(dict.fromkeys(result["errors"]))
    result["ok"] = bool(result["format_verified"] and result["peak_dbfs"] is not None and result["rms_dbfs"] is not None and result["clipping_count"] == 0 and not result["errors"])
    return result


def verify_final_export(path: Path, export_format: str, length_mode: str = "under_2min") -> dict[str, Any]:
    info = verify_final_wav(path, export_format)
    expected_sr = expected_sample_rate(export_format)
    warnings: list[str] = list(info.get("errors", []))

    if info.get("sample_rate") is not None and int(info["sample_rate"]) != expected_sr:
        warnings.append(f"sample rate mismatch: expected {expected_sr}, got {info['sample_rate']}")
    if info.get("bit_depth") != expected_bit_depth(export_format):
        warnings.append(f"unexpected bit depth: {info.get('bit_depth')}")
    if info.get("peak_dbfs") is not None and float(info["peak_dbfs"]) > -1.0:
        warnings.append("final peak is above the approximate -1.0 dBFS safety target")
    if info.get("clipping_count") is not None and int(info["clipping_count"]) > 0:
        warnings.append("clipped samples detected")
    if info.get("duration_seconds") is not None:
        duration = float(info["duration_seconds"])
        if length_mode == "under_2min" and duration > 120.5:
            warnings.append("duration exceeds under-2-minute mode")
        if length_mode == "15sec_reels" and abs(duration - 15.0) > 0.75:
            warnings.append("duration does not match 15-second reels mode")

    result = {
        **info,
        "expected_sample_rate": expected_sr,
        "length_mode": length_mode,
        "warnings": list(dict.fromkeys(warnings)),
        "passed": info["ok"] and not warnings,
    }
    return result


def write_verification_json(verification: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")


def verify_release_package_audio_readiness(
    *,
    final_wav_path: str | Path | None,
    requested_format: str,
    qc_report_path: str | Path | None = None,
    release_checklist_path: str | Path | None = None,
) -> dict[str, Any]:
    blocking: list[str] = []
    if not final_wav_path:
        verification = {"ok": False, "exists": False, "errors": ["final master WAV missing"]}
        blocking.append("final master WAV missing")
    else:
        verification = verify_final_wav(final_wav_path, requested_format)
        if not bool(verification.get("ok")):
            blocking.append("final master WAV failed final_verify")
        if not verification.get("format_verified"):
            blocking.append("final master WAV has wrong or unverified format")
    if qc_report_path and not Path(qc_report_path).exists():
        blocking.append(f"QC report missing: {qc_report_path}")
    elif not qc_report_path:
        blocking.append("QC report missing")
    if release_checklist_path and not Path(release_checklist_path).exists():
        blocking.append(f"release checklist missing: {release_checklist_path}")
    elif not release_checklist_path:
        blocking.append("release checklist missing")
    blocking.extend(str(item) for item in verification.get("errors", []))
    return {
        "release_package_audio_ready": not list(dict.fromkeys(blocking)),
        "verification": verification,
        "blocking_reasons": list(dict.fromkeys(blocking)),
        "rule": "Release package cannot be ready if final master WAV is missing or wrong format.",
    }
