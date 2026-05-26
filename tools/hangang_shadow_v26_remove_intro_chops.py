from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import convert_wav_24, read_wav, write_float_wav

SOURCE = ROOT / "audio_work" / "hangang_shadow_v23_new_female_gated_pan" / "processed_stems" / "female_double_new_gated_pan_24-48.wav"
WORK = ROOT / "audio_work" / "hangang_shadow_v26_v23_base_synth_natural"
PROCESSED = WORK / "processed_stems"
REPORTS = ROOT / "reports" / "hangang_shadow_v26_v23_base_synth_natural"
FLOAT_OUT = PROCESSED / "female_double_no_intro_chops_float.wav"
WAV_OUT = PROCESSED / "female_double_no_intro_chops_24-48.wav"
REPORT_JSON = REPORTS / "intro_chop_removal_report.json"
REPORT_MD = REPORTS / "intro_chop_removal_report.md"


def fade_region(audio: np.ndarray, start: int, end: int, sr: int) -> None:
    fade = max(1, int(sr * 0.080))
    end = min(end, len(audio))
    fade_start = max(start, end - fade)
    audio[start:fade_start] = 0.0
    if fade_start < end:
        ramp = np.linspace(0.0, 1.0, end - fade_start, endpoint=False, dtype=np.float64)
        audio[fade_start:end] *= ramp[:, None]


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    sr, audio, _ = read_wav(SOURCE)
    out = audio.astype(np.float64).copy()

    # The first added female-double fragments read as intro chops; leave the male lead untouched.
    cutoff_s = 9.20
    cutoff = int(sr * cutoff_s)
    before_energy = float(np.sqrt(np.mean(out[:cutoff] ** 2))) if cutoff > 0 else 0.0
    fade_region(out, 0, cutoff, sr)
    after_energy = float(np.sqrt(np.mean(out[:cutoff] ** 2))) if cutoff > 0 else 0.0

    write_float_wav(FLOAT_OUT, sr, out.astype(np.float32))
    convert_wav_24(FLOAT_OUT, WAV_OUT)

    metrics = {
        "source": str(SOURCE),
        "output": str(WAV_OUT),
        "policy": "Removed only the added female double layer before 9.20s. The male main vocal and original music stems are untouched.",
        "cutoff_s": cutoff_s,
        "intro_rms_before": round(before_energy, 8),
        "intro_rms_after": round(after_energy, 8),
        "duration_s": round(len(out) / sr, 3),
    }
    REPORT_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Intro Chop Removal Report",
                "",
                f"- Output: `{WAV_OUT.relative_to(ROOT)}`",
                f"- Removed added female-double layer before: {cutoff_s}s",
                "- Male main vocal and original beat stems were not cut.",
                f"- Intro RMS before: {metrics['intro_rms_before']}",
                f"- Intro RMS after: {metrics['intro_rms_after']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
