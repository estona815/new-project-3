#!/usr/bin/env python3
"""Render and codec QC for WAV/MP3 outputs."""

from pathlib import Path
import subprocess

from audio_utils import analyze_audio_file, ffmpeg_path, find_audio_files, resolve_path, write_json


def risk_flags(features: dict) -> dict:
    return {
        "clipping_risk": features.get("peak_dbfs", -120) > -0.3,
        "mp3_overshoot_risk": features.get("true_peak_proxy", -120) > -1.0,
        "low_end_mono_safety": features.get("side_low_energy_below_120hz", -120) < -24,
        "high_glare_risk": features.get("harshness_energy_3k_6k", -120) > -18,
        "sibilance_risk": features.get("sibilance_energy_6k_9k", -120) > -22,
    }


def run_qc() -> dict:
    render_files = find_audio_files(resolve_path("06_OUTPUTS", "renders"))
    mp3_files = find_audio_files(resolve_path("06_OUTPUTS", "mp3_check"))
    encoded = encode_missing_mp3_checks(render_files, mp3_files)
    mp3_files = find_audio_files(resolve_path("06_OUTPUTS", "mp3_check"))
    results = {
        "status": "ok" if render_files or mp3_files else "no_renders",
        "true_peak_limitation": "true_peak_proxy is a risk proxy, not a formal oversampled BS.1770 true-peak implementation.",
        "mp3_encode": encoded,
        "wav": [],
        "mp3": [],
    }
    for path in render_files:
        try:
            f = analyze_audio_file(path)
            f["risk_flags"] = risk_flags(f)
            results["wav"].append(f)
        except Exception as exc:
            results["wav"].append({"file": str(path), "error": str(exc)})
    for path in mp3_files:
        try:
            f = analyze_audio_file(path)
            f["risk_flags"] = risk_flags(f)
            results["mp3"].append(f)
        except Exception as exc:
            results["mp3"].append({"file": str(path), "error": str(exc)})
    write_json(resolve_path("06_OUTPUTS", "logs", "qc_result.json"), results)
    write_report(results)
    return results


def encode_missing_mp3_checks(render_files: list, existing_mp3_files: list) -> dict:
    exe = ffmpeg_path()
    outdir = resolve_path("06_OUTPUTS", "mp3_check")
    outdir.mkdir(parents=True, exist_ok=True)
    result = {"attempted": False, "ffmpeg_path": exe, "created": [], "errors": []}
    if not render_files or existing_mp3_files:
        return result
    if not exe:
        result["errors"].append("ffmpeg not available from PATH or imageio_ffmpeg; MP3 after-encode check skipped.")
        return result
    result["attempted"] = True
    for src in render_files:
        if src.suffix.lower() not in {".wav", ".wave", ".aif", ".aiff", ".flac"}:
            continue
        dest = outdir / (src.stem + "_mp3check.mp3")
        cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-codec:a", "libmp3lame", "-b:a", "320k", str(dest)]
        try:
            subprocess.run(cmd, check=True)
            result["created"].append(str(dest))
        except Exception as exc:
            result["errors"].append(f"{src.name}: {exc}")
    return result


def write_report(results: dict) -> None:
    lines = [
        "# QC Report",
        "",
        "## A. 코드가 측정한 사실",
        f"- Status: {results.get('status')}",
    ]
    for group in ("wav", "mp3"):
        for item in results.get(group, []):
            lines += [
                f"- {group.upper()} `{Path(item.get('file', 'unknown')).name}`: LUFS {item.get('integrated_lufs')}, TP proxy {item.get('true_peak_proxy')}, peak {item.get('peak_dbfs')}, crest {item.get('crest_factor')}",
                f"  - Risks: {item.get('risk_flags', {})}",
            ]
    if results.get("status") == "no_renders":
        lines.append("- No render files found yet; QC will run once WAV/MP3 files exist.")
    lines += [
        "",
        "## Method Limits",
        f"- {results.get('true_peak_limitation')}",
        f"- MP3 encode check: {results.get('mp3_encode')}",
        "",
        "## B. 정책 엔진이 추천한 수정",
        "- See `03_POLICY_ENGINE/mix_policy.json` and `master_policy.json` after policy generation.",
        "",
        "## C. 사용자가 청감으로 확인해야 하는 항목",
        "- 보컬이 너무 앞으로 튀는지",
        "- 보컬이 너무 묻히는지",
        "- 여자 더블이 리드처럼 들리는지",
        "- 808이 폰에서도 들리는지",
        "- 고역이 피곤한지",
        "- AI/Suno 느낌이 줄었는지",
        "- 레퍼런스와 감정적 방향이 맞는지",
    ]
    resolve_path("07_REPORTS", "qc_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(f"qc status: {run_qc().get('status')}")
