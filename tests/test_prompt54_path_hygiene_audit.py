from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.path_hygiene_audit import build_path_hygiene_audit


def test_path_hygiene_audit_blocks_source_code_hardcoded_local_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = workspace / "automix/demo.py"
    source.parent.mkdir(parents=True)
    source.write_text('BAD = "/Users/example/Music/raw.wav"\n', encoding="utf-8")
    out = workspace / "automix_output"
    audit = build_path_hygiene_audit(project_name="unit", output_dir=out, workspace_root=workspace)
    assert audit["passed"] is False
    assert audit["finding_counts"]["blocker"] == 1
    assert "source_code_contains_absolute_local_path:automix/demo.py" in audit["blockers"]


def test_path_hygiene_audit_treats_runtime_report_paths_as_info(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    report = workspace / "automix/eval_reports/source_report.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({"path": "/Users/example/Music/source.wav"}), encoding="utf-8")
    audit = build_path_hygiene_audit(project_name="unit", output_dir=workspace / "automix", workspace_root=workspace)
    assert audit["passed"] is True
    assert audit["finding_counts"]["info"] == 1
    assert audit["blockers"] == []


def test_path_hygiene_cli_returns_nonzero_for_source_blocker(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = workspace / "scripts/bad.py"
    source.parent.mkdir(parents=True)
    source.write_text('PATH = "/Volumes/Studio/raw.wav"\n', encoding="utf-8")
    out = workspace / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_path_hygiene_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--workspace-root",
            str(workspace),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_current_prompt41_fixtures_use_relative_paths_after_generation(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "tests/automix_validation/scripts/generate_synthetic_audio_fixtures.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tests/automix_validation/scripts/create_minimal_reaper_test_project.py")], check=True)
    audio_manifest = json.loads((ROOT / "tests/automix_validation/fixtures/audio_fixture_manifest.json").read_text(encoding="utf-8"))
    assert all(not Path(item["path"]).is_absolute() for item in audio_manifest["fixtures"])
    project = json.loads((ROOT / "tests/automix_validation/fixtures/mock_projects/prompt41_scan_only_test.json").read_text(encoding="utf-8"))
    media_paths = [media["path"] for track in project["tracks"] for media in track.get("media_items", [])]
    assert media_paths
    assert all(not Path(path).is_absolute() for path in media_paths)


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
    print("Prompt54 direct tests passed")
