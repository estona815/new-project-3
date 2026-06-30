#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
from pathlib import Path
from typing import Any


JSFX_FILES = [
    {
        "source": Path("VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx"),
        "destination": Path("Effects/Codex Vocal/vocal_ai_artifact_split_tamer.jsfx"),
        "display_name": "JS: Codex Vocal AI Artifact Split Tamer",
        "required": True,
    },
    {
        "source": Path("VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_demud_dynamic_eq.jsfx"),
        "destination": Path("Effects/Codex Vocal/vocal_demud_dynamic_eq.jsfx"),
        "display_name": "JS: Vocal Clarity De-Mud Dynamic EQ",
        "required": False,
    },
    {
        "source": Path("VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_presence_enhancer.jsfx"),
        "destination": Path("Effects/Codex Vocal/vocal_presence_enhancer.jsfx"),
        "display_name": "JS: Vocal Clarity Presence Enhancer",
        "required": False,
    },
    {
        "source": Path("VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_air_guard.jsfx"),
        "destination": Path("Effects/Codex Vocal/vocal_air_guard.jsfx"),
        "display_name": "JS: Vocal Clarity Air Guard",
        "required": False,
    },
    {
        "source": Path("VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_output_guard.jsfx"),
        "destination": Path("Effects/Codex Vocal/vocal_output_guard.jsfx"),
        "display_name": "JS: Vocal Clarity Output Guard",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Noise Floor Tamer"),
        "destination": Path("Effects/Codex Vocal/noise_floor_tamer.jsfx"),
        "display_name": "JS: Codex Noise Floor Tamer",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Vocal Gate Expander"),
        "destination": Path("Effects/Codex Vocal/vocal_gate_expander.jsfx"),
        "display_name": "JS: Codex Vocal Gate Expander",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Dynamic EQ Band"),
        "destination": Path("Effects/Codex Vocal/codex_dynamic_eq_band.jsfx"),
        "display_name": "JS: Codex Dynamic EQ Band",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Pro Dynamic MS EQ"),
        "destination": Path("Effects/Codex Vocal/codex_pro_dynamic_ms_eq.jsfx"),
        "display_name": "JS: Codex Pro Dynamic MS EQ",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex MS Melody Tuck"),
        "destination": Path("Effects/Codex Vocal/codex_ms_melody_tuck.jsfx"),
        "display_name": "JS: Codex MS Melody Tuck",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Presence Tilt"),
        "destination": Path("Effects/Codex Vocal/codex_presence_tilt.jsfx"),
        "display_name": "JS: Codex Presence Tilt",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex V20 Channel Polish"),
        "destination": Path("Effects/Codex Vocal/codex_v20_channel_polish.jsfx"),
        "display_name": "JS: Codex V20 Channel Polish",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex V20 Master Glue"),
        "destination": Path("Effects/Codex Vocal/codex_v20_master_glue.jsfx"),
        "display_name": "JS: Codex V20 Master Glue",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Vocal Pitch Monitor"),
        "destination": Path("Effects/Codex Vocal/codex_vocal_pitch_monitor.jsfx"),
        "display_name": "JS: Codex Vocal Pitch Monitor",
        "required": False,
    },
    {
        "source": Path("reaper/jsfx/Codex Glitch Diffuse Spread"),
        "destination": Path("Effects/Codex Vocal/codex_glitch_diffuse_spread.jsfx"),
        "display_name": "JS: Codex Glitch Diffuse Spread",
        "required": False,
    },
]


def default_reaper_resource_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "REAPER"
    if system == "Windows":
        return Path.home() / "AppData" / "Roaming" / "REAPER"
    return Path.home() / ".config" / "REAPER"


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_plan(root: Path, reaper_resource_dir: Path, *, apply: bool, overwrite: bool) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    for item in JSFX_FILES:
        source = root / item["source"]
        destination = reaper_resource_dir / item["destination"]
        exists = destination.exists()
        action = {
            "source": str(source),
            "destination": str(destination),
            "display_name": item["display_name"],
            "required": item["required"],
            "source_exists": source.is_file(),
            "destination_exists_before": exists,
            "copied": False,
            "skipped": False,
            "skip_reason": "",
        }
        if not source.is_file():
            code = f"source_jsfx_missing:{item['source']}"
            if item["required"]:
                blockers.append(code)
            else:
                warnings.append(code)
            action["skipped"] = True
            action["skip_reason"] = code
        elif exists and not overwrite:
            action["skipped"] = True
            action["skip_reason"] = "destination_exists_use_overwrite_to_replace"
        elif apply:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            action["copied"] = True
            action["destination_exists_after"] = destination.exists()
        else:
            action["skipped"] = True
            action["skip_reason"] = "dry_run"
        if "destination_exists_after" not in action:
            action["destination_exists_after"] = destination.exists()
        actions.append(action)

    return {
        "schema": "codex-reaper-jsfx-install-plan-v1",
        "root": str(root),
        "reaper_resource_dir": str(reaper_resource_dir),
        "apply": apply,
        "overwrite": overwrite,
        "actions": actions,
        "blockers": blockers,
        "warnings": warnings,
        "passed": not blockers,
        "ready_for_reaper_rescan": apply and not blockers,
        "next_steps": [
            "Restart REAPER or run an FX rescan after copying JSFX files.",
            "Run the selected REAPER routing/FX insertion script on a saved project copy, then verify work/traces/plugin_trace.json.",
            "Do not render or deliver if the first FX on 08 MALE_NONHOOK_CENTER is not JS: Codex Vocal AI Artifact Split Tamer.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install bundled Codex JSFX into the local REAPER resource Effects folder.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reaper-resource-dir", type=Path, default=default_reaper_resource_dir())
    parser.add_argument("--output", type=Path, default=Path("work/logs/jsfx_install_plan.json"))
    parser.add_argument("--apply", action="store_true", help="Copy files. Without this flag the command is dry-run only.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing destination JSFX files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    plan = build_plan(root, args.reaper_resource_dir.expanduser(), apply=args.apply, overwrite=args.overwrite)
    write_json(output, plan)
    print(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if plan["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
