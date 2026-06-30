from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from VOCAL_CLARITY_REPAIR_SYSTEM.eval.audio_metrics import (
    AudioBuffer,
    band_energies,
    compute_residual,
    evaluate_pair,
    loudness_match,
    read_wav,
    transient_features,
    write_wav,
)
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness import run_evaluation, write_single_input_manifest
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.synthetic_assets import generate_synthetic_suite, harmonic_stack


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
DOCS = SYSTEM / "docs"
JSFX = SYSTEM / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
PLUGIN_EVAL = SYSTEM / "scripts" / "plugin_eval.py"


def sine(sr: int, freq: float, duration: float = 0.25, amp: float = 0.25) -> np.ndarray:
    t = np.arange(int(sr * duration), dtype=np.float64) / sr
    return (amp * np.sin(2.0 * np.pi * freq * t))[:, None].astype(np.float32)


def test_prompt16_docs_and_existing_architecture_are_explicit() -> None:
    eval_doc = (DOCS / "evaluation_harness.md").read_text(encoding="utf-8")
    residual_doc = (DOCS / "residual_monitor.md").read_text(encoding="utf-8")
    manual_doc = (DOCS / "manual_test_plan_prompt16.md").read_text(encoding="utf-8")

    assert "AudioProcessor file: NOT FOUND" in eval_doc
    assert "processBlock file/function: NOT FOUND" in eval_doc
    assert "JSFX `@sample`" in eval_doc
    assert "processed.wav" in eval_doc
    assert "processed_matched.wav" in eval_doc
    assert "residual.wav" in eval_doc
    assert "inputAligned - processedAligned" in residual_doc
    assert "ghost vocal" in residual_doc.lower()
    assert "clean but low-quality" in manual_doc


def test_residual_monitor_is_documented_and_plugin_mode_exists() -> None:
    text = JSFX.read_text(encoding="utf-8")

    assert "slider27:0<0,2,1{Off,Processed,Residual}>Residual Monitor" in text
    assert "Residual monitor convention: dry input minus processed-before-drywet." in text
    assert "out_l = in_l - proc_l;" in text
    assert "out_r = in_r - proc_r;" in text


def test_residual_calculation_handles_identical_silence_and_stereo() -> None:
    mono = np.array([[0.1], [-0.2], [0.3]], dtype=np.float32)
    stereo = np.column_stack([mono[:, 0], -mono[:, 0]]).astype(np.float32)

    assert np.max(np.abs(compute_residual(mono, mono))) == 0.0
    assert np.allclose(compute_residual(mono, np.zeros_like(mono)), mono)
    assert np.allclose(compute_residual(stereo, np.zeros_like(stereo)), stereo)


def test_level_matching_is_report_only_and_handles_silence() -> None:
    sr = 48000
    x = harmonic_stack(sr, 0.25)[:, None].astype(np.float32)
    matched, gain_db = loudness_match(x, x * 0.25)
    silent, silent_gain = loudness_match(np.zeros_like(x), np.zeros_like(x))

    assert 11.9 < gain_db < 12.1
    assert abs(float(np.sqrt(np.mean(matched * matched))) - float(np.sqrt(np.mean(x * x)))) < 1.0e-4
    assert silent_gain == 0.0
    assert np.max(np.abs(silent)) == 0.0


def test_band_energy_places_sines_in_presence_clarity_and_air() -> None:
    sr = 48000
    presence = band_energies(sine(sr, 3000.0), sr)
    clarity = band_energies(sine(sr, 6000.0), sr)
    air = band_energies(sine(sr, 12000.0), sr)

    assert presence["presence"] > presence["body"]
    assert presence["presence"] > presence["air"]
    assert clarity["clarity"] > clarity["body"]
    assert air["air"] > air["presence"]


def test_spectral_tilt_and_transient_metrics_are_reported() -> None:
    sr = 48000
    source = sine(sr, 3000.0) + sine(sr, 6000.0) + sine(sr, 500.0)
    darker = sine(sr, 500.0) + sine(sr, 3000.0, amp=0.05) + sine(sr, 6000.0, amp=0.05)
    identical = evaluate_pair(AudioBuffer(sr, source), AudioBuffer(sr, source.copy()), preset="Preserve")
    dark = evaluate_pair(AudioBuffer(sr, source), AudioBuffer(sr, darker), preset="Preserve")

    assert identical["metrics"]["spectral_tilt_loss_db"] < 0.01
    assert dark["preservation"]["spectral_tilt_loss_db"] > 2.0

    impulse = np.zeros((sr // 4, 1), dtype=np.float32)
    impulse[2000, 0] = 0.8
    softened = impulse * 0.2
    transient = evaluate_pair(AudioBuffer(sr, impulse), AudioBuffer(sr, softened), preset="Preserve")
    assert "transient_preservation_ratio" in transient["metrics"]
    assert transient_features(impulse, sr)["flux"] >= transient_features(softened, sr)["flux"]


def test_synthetic_generator_outputs_finite_non_clipping_assets(tmp_path: Path) -> None:
    manifest = generate_synthetic_suite(tmp_path)

    required_ids = {
        "synthetic_silence",
        "synthetic_sine_3000hz",
        "synthetic_sine_6000hz",
        "synthetic_sine_12000hz",
        "synthetic_harmonic_stack",
        "synthetic_impulse_train",
        "synthetic_hiss_plus_harmonic",
        "synthetic_stereo_side_noise",
    }
    ids = {item["id"] for item in manifest["items"]}
    assert required_ids <= ids

    for item in manifest["items"]:
        audio = read_wav(tmp_path / item["path"])
        assert np.all(np.isfinite(audio.samples))
        assert float(np.max(np.abs(audio.samples))) < 0.999


def test_offline_eval_writes_prompt16_outputs_and_metrics(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    generate_synthetic_suite(assets)
    single_manifest = json.loads((assets / "manifest.synthetic.json").read_text(encoding="utf-8"))
    single_manifest["items"] = [item for item in single_manifest["items"] if item["id"] == "synthetic_sine_3000hz"]
    manifest_path = assets / "single.json"
    manifest_path.write_text(json.dumps(single_manifest, indent=2), encoding="utf-8")

    report = run_evaluation(
        manifest_path,
        preset="Preserve",
        output_dir=tmp_path / "eval",
        renderer="passthrough",
        block_size=512,
    )

    item_dir = tmp_path / "eval" / "Preserve" / "synthetic_sine_3000hz"
    metrics = json.loads((item_dir / "metrics.json").read_text(encoding="utf-8"))
    assert report["summary"]["fail_count"] == 0
    for name in ("processed.wav", "processed_matched.wav", "residual.wav", "metrics.json", "report.md"):
        assert (item_dir / name).exists()
    assert metrics["residual_definition"] == "inputAligned - processedAligned"
    assert metrics["level"]["match_gain_db"] == 0.0
    assert "presence_loss_db" in metrics["preservation"]
    assert "residual_presence_ratio_db" in metrics["residual"]
    assert "nan_count" in metrics["safety"]


def test_single_input_manifest_and_plugin_eval_entrypoint_exist(tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    write_wav(input_path, AudioBuffer(48000, sine(48000, 1000.0)))
    manifest_path = write_single_input_manifest(input_path, tmp_path / "eval")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert PLUGIN_EVAL.exists()
    assert manifest["items"][0]["path"] == str(input_path.resolve())


def test_metrics_detect_nan_inf_without_writing_non_finite_values() -> None:
    sr = 48000
    source = sine(sr, 1000.0, duration=0.05)
    processed = source.copy()
    processed[3, 0] = np.nan
    processed[4, 0] = np.inf
    metrics = evaluate_pair(AudioBuffer(sr, source), AudioBuffer(sr, processed), preset="Preserve")

    assert metrics["status"] == "fail"
    assert "nan_inf" in metrics["failures"]
    assert metrics["safety"]["processed_nan_count"] == 1
    assert metrics["safety"]["processed_inf_count"] == 1
    assert math.isfinite(metrics["level"]["processed_rms"])
