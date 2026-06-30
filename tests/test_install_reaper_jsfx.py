from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.install_reaper_jsfx import JSFX_FILES, build_plan


def make_jsfx_sources(root: Path) -> None:
    for item in JSFX_FILES:
        source = root / item["source"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"desc:{item['display_name'].replace('JS: ', '')}\n", encoding="utf-8")


def test_jsfx_install_plan_is_dry_run_by_default(tmp_path: Path) -> None:
    make_jsfx_sources(tmp_path)
    resource = tmp_path / "REAPER"

    plan = build_plan(tmp_path, resource, apply=False, overwrite=False)

    assert plan["passed"] is True
    assert plan["ready_for_reaper_rescan"] is False
    assert all(action["copied"] is False for action in plan["actions"])
    assert all(action["skip_reason"] == "dry_run" for action in plan["actions"])
    assert not any((resource / item["destination"]).exists() for item in JSFX_FILES)


def test_jsfx_install_plan_copies_when_apply_is_true(tmp_path: Path) -> None:
    make_jsfx_sources(tmp_path)
    resource = tmp_path / "REAPER"

    plan = build_plan(tmp_path, resource, apply=True, overwrite=False)

    assert plan["passed"] is True
    assert plan["ready_for_reaper_rescan"] is True
    assert all(action["copied"] is True for action in plan["actions"])
    assert all((resource / item["destination"]).is_file() for item in JSFX_FILES)


def test_jsfx_install_cli_writes_report(tmp_path: Path) -> None:
    make_jsfx_sources(tmp_path)
    out = tmp_path / "work/logs/jsfx_install_plan.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/install_reaper_jsfx.py"),
            "--root",
            str(tmp_path),
            "--reaper-resource-dir",
            str(tmp_path / "REAPER"),
            "--output",
            str(out),
            "--apply",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["ready_for_reaper_rescan"] is True
    assert out.exists()
