#!/usr/bin/env python3
"""Create 15 second A/B preview WAV snippets from available render/reference files."""

import shutil
import subprocess
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_ANALYSIS"))

from audio_utils import ffmpeg_path, find_audio_files, resolve_path, write_json


def create_previews() -> dict:
    outdir = resolve_path("06_OUTPUTS", "ab_previews")
    outdir.mkdir(parents=True, exist_ok=True)
    candidates = []
    for folder in [
        resolve_path("00_REFERENCES", "approved_tracks"),
        resolve_path("06_OUTPUTS", "renders"),
        resolve_path("01_CURRENT_SONG", "premaster"),
    ]:
        candidates.extend(find_audio_files(folder))
    result = {"status": "ok" if candidates else "no_audio", "created": [], "message": ""}
    exe = ffmpeg_path()
    if not candidates:
        result["message"] = "No audio files found for A/B previews."
    elif not exe:
        result["status"] = "ffmpeg_unavailable"
        result["message"] = "ffmpeg not available; cannot cut previews. Install ffmpeg or imageio-ffmpeg."
    else:
        labels = ["reference", "current_render", "premaster", "hook_section", "loudest_section", "vocal_exposed"]
        for idx, src in enumerate(candidates[:6]):
            label = labels[idx] if idx < len(labels) else f"preview_{idx+1}"
            dest = outdir / f"{label}_15s.wav"
            cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", "-ss", "0", "-t", "15", "-i", str(src), str(dest)]
            subprocess.run(cmd, check=True)
            result["created"].append(str(dest))
    write_json(resolve_path("06_OUTPUTS", "logs", "ab_preview_result.json"), result)
    return result


if __name__ == "__main__":
    print(f"ab preview status: {create_previews().get('status')}")
