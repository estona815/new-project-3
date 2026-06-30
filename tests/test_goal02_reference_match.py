from __future__ import annotations

import json
import math
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.analyze_goal02_reference_match import analyze_goal02, default_manifest
from tools.render_goal02_chorus_candidate import (
    db_to_linear,
    limit_true_peak_estimate,
    stem_role,
    true_peak_estimate,
)


def write_tone(path: Path, freqs: list[float], seconds: float = 1.0, sample_rate: int = 16000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for index in range(int(seconds * sample_rate)):
        t = index / sample_rate
        left = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs)) * 0.25
        right = left * 0.9
        for value in (left, right):
            sample = int(max(-1.0, min(1.0, value)) * 32767)
            frames.extend(sample.to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))
    return path


def write_float_tone(path: Path, freqs: list[float], seconds: float = 1.0, sample_rate: int = 16000) -> Path:
    import numpy as np
    from scipy.io import wavfile

    path.parent.mkdir(parents=True, exist_ok=True)
    samples = []
    for index in range(int(seconds * sample_rate)):
        t = index / sample_rate
        left = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs)) * 0.25
        samples.append([left, left * 0.85])
    wavfile.write(str(path), sample_rate, np.asarray(samples, dtype=np.float32))
    return path


def write_manifest(root: Path, *, with_audio: bool) -> Path:
    manifest = default_manifest(root)
    manifest["analysis_window"]["duration_seconds"] = 0.5
    if with_audio:
        target = write_tone(root / "input" / "target" / "target_chorus.wav", [90.0, 1200.0, 5200.0])
        manifest["target"]["path"] = str(target.relative_to(root))
        for index, item in enumerate(manifest["references"], start=1):
            ref = write_tone(root / "input" / "reference" / f"ref_{index:02d}.wav", [80.0 + index, 1000.0, 4500.0])
            item["path"] = str(ref.relative_to(root))
    path = root / "configs" / "goal02_8_reference_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_goal02_blocks_missing_inputs_and_writes_reports(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, with_audio=False)
    output = tmp_path / "reports" / "goal02"
    result = analyze_goal02(tmp_path, manifest, output)

    assert result["summary"]["status"] == "blocked_missing_inputs"
    assert result["summary"]["references_measured"] == 0
    assert "target_chorus_missing_or_unmeasured" in result["summary"]["blocked_reasons"]
    assert (output / "goal02_reference_features.csv").exists()
    assert (output / "goal02_reference_match.json").exists()
    assert (output / "GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md").exists()


def test_goal02_measures_target_and_eight_references(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, with_audio=True)
    output = tmp_path / "reports" / "goal02"
    result = analyze_goal02(tmp_path, manifest, output)

    assert result["summary"]["status"] == "measured_8_reference_profile_ready_for_reaper_plan"
    assert result["summary"]["references_measured"] == 8
    assert result["target"]["status"] == "measured"
    assert len(result["closest_references"]) > 0
    assert result["reference_average"]["spectral_centroid_hz"] is not None


def test_goal02_measures_float_wav_fallback(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, with_audio=False)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    target = write_float_tone(tmp_path / "input" / "target" / "target_chorus.wav", [95.0, 1250.0, 6000.0])
    data["target"]["path"] = str(target.relative_to(tmp_path))
    for index, item in enumerate(data["references"], start=1):
        ref = write_float_tone(tmp_path / "input" / "reference" / f"ref_{index:02d}.wav", [80.0 + index, 1100.0, 4800.0])
        item["path"] = str(ref.relative_to(tmp_path))
    manifest.write_text(json.dumps(data), encoding="utf-8")

    result = analyze_goal02(tmp_path, manifest, tmp_path / "reports" / "goal02")

    assert result["summary"]["status"] == "measured_8_reference_profile_ready_for_reaper_plan"
    assert result["target"]["sample_rate"] == 16000
    assert result["target"]["channels"] == 2
    assert result["target"]["status"] == "measured"


def test_goal02_render_preview_true_peak_estimate_guard() -> None:
    import numpy as np

    impulse = np.zeros((512, 2), dtype=np.float64)
    impulse[128, :] = 1.0

    limited = limit_true_peak_estimate(impulse, -1.0)

    assert true_peak_estimate(limited) <= db_to_linear(-1.0) + 1.0e-9


def test_goal02_render_preview_excludes_raw_full_mix_stem() -> None:
    assert stem_role(Path("0 SOURCE full mix reference muted - not in master.wav")) == "full_mix_reference_excluded"
    assert stem_role(Path("01_Bass_808.wav")) == "bass"
