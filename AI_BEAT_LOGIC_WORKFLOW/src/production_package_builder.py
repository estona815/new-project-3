from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arrangement_to_logic_package import build_mix_prep_checklist, convert_arrangement_to_logic_package, render_mix_prep_checklist
from production_todo_generator import build_production_todo, render_production_todo


def build_production_package(
    arrangement_plan: dict[str, Any],
    *,
    midi_region_guide: dict[str, Any],
    automation_guide: dict[str, Any],
    creative_brief: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    master_target: str = "streaming_safe",
) -> dict[str, Any]:
    package = convert_arrangement_to_logic_package(
        arrangement_plan,
        midi_region_guide=midi_region_guide,
        automation_guide=automation_guide,
        creative_brief=creative_brief,
        vocal_to_code=vocal_to_code,
        master_target=master_target,
    )
    checklist = build_mix_prep_checklist(package)
    package = {
        **package,
        "schema_version": "production_package_manifest.v1",
        "mix_prep_checklist": checklist,
    }
    package["production_todo"] = build_production_todo(package)
    return package


def write_production_package(project_root: str | Path, package: dict[str, Any]) -> dict[str, Path]:
    root = Path(project_root)
    edit_dir = root / "02_EDIT_PLAN"
    edit_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": edit_dir / "production_package_manifest.json",
        "todo": edit_dir / "production_todo.md",
        "mix_prep_checklist": edit_dir / "mix_prep_checklist.md",
    }
    paths["manifest"].write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["todo"].write_text(render_production_todo(package), encoding="utf-8")
    paths["mix_prep_checklist"].write_text(render_mix_prep_checklist(package), encoding="utf-8")
    return paths


def build_and_write_production_package(
    project_root: str | Path,
    arrangement_plan: dict[str, Any],
    *,
    midi_region_guide: dict[str, Any],
    automation_guide: dict[str, Any],
    creative_brief: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    master_target: str = "streaming_safe",
) -> dict[str, Any]:
    package = build_production_package(
        arrangement_plan,
        midi_region_guide=midi_region_guide,
        automation_guide=automation_guide,
        creative_brief=creative_brief,
        vocal_to_code=vocal_to_code,
        master_target=master_target,
    )
    paths = write_production_package(project_root, package)
    return {"package": package, "paths": paths}
