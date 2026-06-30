from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from VOCAL_CLARITY_REPAIR_SYSTEM.eval.audio_metrics import AudioBuffer, evaluate_pair, loudness_match, read_wav, write_wav
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness import run_evaluation
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.synthetic_assets import generate_synthetic_suite, harmonic_stack


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/manifest.json"
REPORT = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/docs/prompt7_ab_quality_harness_report.md"


def test_manifest_and_report_document_required_categories() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")

    assert manifest["schema"] == "codex-vocal-ab-eval-manifest-v1"
    categories = {item["category"] for item in manifest["items"]}
    assert "clean_vocal" in categories
    assert "ai_metallic_vocal" in categories
    assert "stereo_ambience" in categories
    assert "residual source leakage" in report.lower()
    assert "processed_matched.wav" in report


def test_synthetic_generation_creates_manifest_and_audio(tmp_path: Path) -> None:
    manifest = generate_synthetic_suite(tmp_path)

    assert manifest["schema"] == "codex-vocal-ab-eval-manifest-v1"
    assert len(manifest["items"]) >= 10
    for item in manifest["items"]:
        assert (tmp_path / item["path"]).exists()


def test_passthrough_evaluation_writes_processed_residual_and_reports(tmp_path: Path) -> None:
    generate_synthetic_suite(tmp_path / "assets")
    report = run_evaluation(
        tmp_path / "assets/manifest.synthetic.json",
        preset="Preserve",
        output_dir=tmp_path / "eval",
        renderer="passthrough",
        block_size=256,
    )

    assert report["summary"]["fail_count"] == 0
    run_metrics = tmp_path / "eval/Preserve/run_metrics.json"
    index = tmp_path / "eval/Preserve/index.md"
    assert run_metrics.exists()
    assert index.exists()
    first = report["files"][0]
    item_dir = tmp_path / "eval/Preserve" / first["id"]
    assert (item_dir / "processed.wav").exists()
    assert (item_dir / "processed_matched.wav").exists()
    assert (item_dir / "residual.wav").exists()
    assert (item_dir / "metrics.json").exists()
    residual = read_wav(item_dir / "residual.wav").samples
    assert np.max(np.abs(residual)) <= 1.0 / 32767.0


def test_loudness_matching_reports_gain_without_hiding_raw_output() -> None:
    sr = 48000
    x = harmonic_stack(sr, 0.25)[:, None].astype(np.float32)
    quiet = x * 0.5
    matched, gain_db = loudness_match(x, quiet)

    assert 5.9 < gain_db < 6.1
    assert abs(float(np.sqrt(np.mean(matched * matched))) - float(np.sqrt(np.mean(x * x)))) < 1.0e-4


def test_metrics_fail_clean_input_damage_when_presence_is_removed() -> None:
    sr = 48000
    t = np.arange(int(sr * 0.5)) / sr
    source = (
        0.12 * np.sin(2 * np.pi * 220 * t)
        + 0.10 * np.sin(2 * np.pi * 3000 * t)
        + 0.08 * np.sin(2 * np.pi * 6000 * t)
    )[:, None].astype(np.float32)
    damaged = (0.12 * np.sin(2 * np.pi * 220 * t))[:, None].astype(np.float32)

    metrics = evaluate_pair(
        AudioBuffer(sr, source),
        AudioBuffer(sr, damaged),
        preset="Preserve",
        expected_behavior="do_no_harm",
    )

    assert metrics["status"] == "fail"
    assert "vocal_presence_loss" in metrics["failures"] or "consonant_loss" in metrics["failures"]
    assert metrics["scores"]["source_preservation"] < 50.0


def test_residual_source_leakage_detects_processed_silence() -> None:
    sr = 48000
    source = harmonic_stack(sr, 0.5)[:, None].astype(np.float32)
    processed = np.zeros_like(source)
    metrics = evaluate_pair(
        AudioBuffer(sr, source),
        AudioBuffer(sr, processed),
        preset="Preserve",
        expected_behavior="do_no_harm",
    )

    assert metrics["status"] == "fail"
    assert "residual_ghost_vocal" in metrics["failures"]
    assert metrics["metrics"]["residual_source_leakage_score"] > 40.0


def test_external_renderer_uses_processed_files(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    manifest = generate_synthetic_suite(assets)
    processed_root = tmp_path / "processed"
    item = manifest["items"][1]
    original = read_wav(assets / item["path"])
    processed_item_dir = processed_root / "Preserve" / item["id"]
    processed_item_dir.mkdir(parents=True)
    write_wav(processed_item_dir / "processed.wav", AudioBuffer(original.sample_rate, original.samples * 0.8))

    single_manifest = {"schema": manifest["schema"], "items": [item]}
    (assets / "single.json").write_text(json.dumps(single_manifest, indent=2), encoding="utf-8")
    report = run_evaluation(
        assets / "single.json",
        preset="Preserve",
        output_dir=tmp_path / "eval",
        renderer="external",
        processed_dir=processed_root,
    )

    assert len(report["files"]) == 1
    assert report["files"][0]["level"]["rms_delta_db"] < -1.0
