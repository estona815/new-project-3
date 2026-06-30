from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.github_integration import (
    ReaperDryRunAdapter,
    build_audio_diagnostic_report,
    build_github_integration_manifest,
    write_audio_diagnostic_report,
)


def write_tone(path: Path, *, seconds: float = 0.25, sample_rate: int = 16000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            sample = int(0.20 * 32767 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
            handle.writeframes(struct.pack("<h", sample))


def test_manifest_keeps_github_repos_as_references_only() -> None:
    manifest = build_github_integration_manifest()
    assert manifest["status"] == "research_reference_and_dry_run_only"
    assert "no_third_party_source_copied" in manifest["claim_limits"]
    assert manifest["safe_command_contract"]["default_dry_run"] is True
    assert manifest["safe_command_contract"]["project_overwrite_allowed"] is False
    assert {item["name"] for item in manifest["reference_repositories"]} >= {
        "shiehn/total-reaper-mcp",
        "wegitor/reaper-reapy-mcp",
        "RomeoDespres/reapy",
    }
    add_fx = next(item for item in manifest["safe_command_candidates"] if item["id"] == "add_fx")
    assert add_fx["write_allowed"] is False
    assert "project_snapshot" in add_fx["evidence_required"]


def test_dry_run_adapter_blocks_real_writes_without_evidence() -> None:
    adapter = ReaperDryRunAdapter()
    dry = adapter.add_fx(track_index=0, fx_name="JS: ReaEQ")
    assert dry["ok"] is True
    assert dry["dry_run"] is True
    blocked = adapter.add_fx(track_index=0, fx_name="JS: ReaEQ", dry_run=False)
    assert blocked["ok"] is False
    assert blocked.get("write_safety") in {"blocked", None}


def test_audio_diagnostics_are_report_only_and_not_lufs(tmp_path: Path) -> None:
    audio = tmp_path / "tone.wav"
    write_tone(audio)
    report = build_audio_diagnostic_report(audio)
    assert report["status"] == "report_only"
    assert "not_lufs" in report["claim_limits"]
    assert report["features"]["readable"] is True
    assert report["loudness"]["kind"] == "proxy_not_lufs"
    paths = write_audio_diagnostic_report(report, tmp_path / "reports")
    assert Path(paths["json"]).exists()
    assert Path(paths["markdown"]).exists()


def test_cli_writes_isolated_smoke_reports(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_github_integration_smoke.py"),
            "--output-dir",
            str(tmp_path / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert (tmp_path / "automix/eval_reports/github_integration_smoke.json").exists()
    assert (tmp_path / "automix/eval_reports/github_integration_smoke.md").exists()
    report = json.loads((tmp_path / "automix/eval_reports/github_integration_smoke.json").read_text(encoding="utf-8"))
    assert report["audio_diagnostics"]["supplied"] is False
    assert report["qc_passed"] is True
    assert report["dry_run_adapter"]["render_project"]["dry_run"] is True


def test_docs_entrypoint_exists() -> None:
    assert (ROOT / "docs/github_integration_pipeline.md").exists()


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(key for key in current if key.startswith("test_")):
        fn = current[name]
        try:
            if "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as directory:
                    fn(Path(directory))
            else:
                fn()
        except Exception as exc:  # pragma: no cover - direct runner diagnostics
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("GitHub integration direct tests passed")
