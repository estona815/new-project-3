from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.fixture_coverage_audit import REQUIRED_FIXTURE_CATEGORIES, build_fixture_coverage_audit
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_fixture_root(tmp_path: Path, *, omit_category: str | None = None) -> Path:
    fixture_root = tmp_path / "fixtures"
    audio_dir = fixture_root / "audio"
    analysis_dir = fixture_root / "analysis_json"
    audio_dir.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)
    audio_fixtures = []
    for item in REQUIRED_FIXTURE_CATEGORIES:
        category = item["category"]
        if category == omit_category:
            continue
        if item["source"] != "audio":
            continue
        path = audio_dir / f"{category}.wav"
        path.write_bytes(b"fixture")
        audio_fixtures.append(
            {
                "path": str(path),
                "sample_rate": 48000,
                "channels": 1,
                "duration_seconds": 1.0,
                "coverage_tags": [category],
                "expected": f"{category} coverage",
            }
        )
    write_json(
        fixture_root / "audio_fixture_manifest.json",
        {
            "schema": "prompt41-audio-fixture-manifest-v1",
            "fixtures": audio_fixtures,
        },
    )
    for item in REQUIRED_FIXTURE_CATEGORIES:
        category = item["category"]
        if category == omit_category:
            continue
        if item["source"] != "analysis":
            continue
        write_json(
            analysis_dir / f"{category}.json",
            {
                "schema": "prompt41-mock-analysis-fixture-v1",
                "name": f"{category} fixture",
                "coverage_tags": [category],
                "input": {"category": category},
                "expected_decision": "covered",
            },
        )
    return fixture_root


def test_fixture_coverage_audit_passes_when_all_required_categories_are_tagged(tmp_path: Path) -> None:
    fixture_root = make_fixture_root(tmp_path)
    out = tmp_path / "automix"
    audit = build_fixture_coverage_audit(project_name="unit", output_dir=out, fixture_root=fixture_root)
    assert audit["passed"] is True
    assert audit["missing_categories"] == []
    assert len(audit["covered_categories"]) == len(REQUIRED_FIXTURE_CATEGORIES)
    assert (out / "eval_reports/fixture_coverage_audit.json").exists()
    md = (out / "eval_reports/fixture_coverage_audit.md").read_text(encoding="utf-8")
    assert "Fixture Coverage Audit" in md
    assert "does not prove audio quality" in md


def test_fixture_coverage_audit_blocks_missing_required_category(tmp_path: Path) -> None:
    fixture_root = make_fixture_root(tmp_path, omit_category="phase_issue")
    out = tmp_path / "automix"
    audit = build_fixture_coverage_audit(project_name="unit", output_dir=out, fixture_root=fixture_root)
    assert audit["passed"] is False
    assert "phase_issue" in audit["missing_categories"]
    assert "required_fixture_category_missing:phase_issue" in audit["blockers"]


def test_fixture_coverage_cli_returns_nonzero_for_missing_category(tmp_path: Path) -> None:
    fixture_root = make_fixture_root(tmp_path, omit_category="feedback_mapping")
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_fixture_coverage_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--fixture-root",
            str(fixture_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert data["missing_categories"] == ["feedback_mapping"]
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_fixture_coverage_audit_blocks_missing_audio_file(tmp_path: Path) -> None:
    fixture_root = make_fixture_root(tmp_path)
    manifest_path = fixture_root / "audio_fixture_manifest.json"
    manifest = read_json(manifest_path)
    missing_path = fixture_root / "audio/missing_clean_vocal.wav"
    manifest["fixtures"][0]["path"] = str(missing_path)
    write_json(manifest_path, manifest)
    audit = build_fixture_coverage_audit(project_name="unit", output_dir=tmp_path / "automix", fixture_root=fixture_root)
    assert audit["passed"] is False
    assert str(missing_path) in audit["audio"]["missing_audio_files"]
    assert any(blocker.startswith("audio_fixture_file_missing:") for blocker in audit["blockers"])


def test_report_index_groups_fixture_coverage_audit(tmp_path: Path) -> None:
    fixture_root = make_fixture_root(tmp_path)
    out = tmp_path / "automix"
    build_fixture_coverage_audit(project_name="unit", output_dir=out, fixture_root=fixture_root)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "validation harness" and item["summary"] == "fixture_coverage_audit.json" for item in index["reports"])


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            with tempfile.TemporaryDirectory() as directory:
                fn(Path(directory))
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt50 direct tests passed")
