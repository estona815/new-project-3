from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


PLUGIN_ROLES: dict[str, dict[str, object]] = {
    "pitch_correction": {
        "preferred": ["Auto-Tune Pro", "Auto-Tune", "Melodyne", "Waves Tune Real-Time", "MetaTune", "Graillon"],
        "fallback": "ReaTune",
    },
    "surgical_eq": {
        "preferred": ["FabFilter Pro-Q 3", "Kirchhoff-EQ", "DMG Equilibrium", "TDR Nova"],
        "fallback": "ReaEQ",
    },
    "dynamic_eq": {
        "preferred": ["FabFilter Pro-Q 3", "TDR Nova", "Ozone Dynamic EQ", "Waves F6"],
        "fallback": "ReaXcomp",
    },
    "deesser": {
        "preferred": ["FabFilter Pro-DS", "Soothe2", "Waves Sibilance", "TDR Nova"],
        "fallback": "ReaXcomp",
    },
    "compressor_clean": {
        "preferred": ["FabFilter Pro-C 2", "RComp", "SSL Channel", "Pro-C 2"],
        "fallback": "ReaComp",
    },
    "compressor_character": {
        "preferred": ["CLA-76", "LA-2A", "1176", "RComp", "SSL Channel"],
        "fallback": "ReaComp",
    },
    "saturation": {
        "preferred": ["FabFilter Saturn", "Saturn", "Decapitator", "Fresh Air", "Tape"],
        "fallback": "JS: Saturation",
    },
    "multiband_compressor": {
        "preferred": ["FabFilter Pro-MB", "Ozone Dynamics", "C4", "C6"],
        "fallback": "ReaXcomp",
    },
    "stereo_imager": {
        "preferred": ["Ozone Imager", "MSED", "bx_stereomaker", "bx_digital"],
        "fallback": "JS: Stereo Width",
    },
    "mid_side_eq": {
        "preferred": ["FabFilter Pro-Q 3", "bx_digital", "Kirchhoff-EQ", "TDR Nova"],
        "fallback": "ReaEQ",
    },
    "reverb_plate": {
        "preferred": ["ValhallaPlate", "Valhalla Plate", "FabFilter Pro-R", "RVerb"],
        "fallback": "ReaVerbate",
    },
    "reverb_room": {
        "preferred": ["ValhallaRoom", "Valhalla Room", "FabFilter Pro-R", "RVerb"],
        "fallback": "ReaVerbate",
    },
    "delay": {
        "preferred": ["EchoBoy", "H-Delay", "Timeless", "FabFilter Timeless"],
        "fallback": "ReaDelay",
    },
    "limiter": {
        "preferred": ["FabFilter Pro-L 2", "Ozone Maximizer", "L2", "Elephant"],
        "fallback": "ReaLimit",
    },
    "loudness_meter": {
        "preferred": ["Youlean Loudness Meter", "Insight", "dpMeter"],
        "fallback": "ffmpeg ebur128 / JS: Loudness Meter Peak/RMS/LUFS",
    },
    "noise_reduction": {
        "preferred": ["RX Voice De-noise", "Clarity Vx", "NS1", "ReaFIR"],
        "fallback": "ReaFIR",
    },
}


PLUGIN_SCAN_DIRS = [
    Path("/Library/Audio/Plug-Ins/Components"),
    Path("/Library/Audio/Plug-Ins/VST"),
    Path("/Library/Audio/Plug-Ins/VST3"),
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "Components",
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST",
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST3",
]


REAPER_PLUGIN_FILES = [
    Path.home() / "Library" / "Application Support" / "REAPER" / "reaper-vstplugins64.ini",
    Path.home() / "Library" / "Application Support" / "REAPER" / "reaper-auplugins64.ini",
]


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def scan_plugin_names() -> dict[str, object]:
    names: set[str] = set()
    sources: list[str] = []
    for folder in PLUGIN_SCAN_DIRS:
        try:
            if not folder.exists():
                continue
            for path in folder.iterdir():
                if path.suffix.lower() in {".component", ".vst", ".vst3"} or path.is_dir():
                    names.add(path.stem)
                    sources.append(str(path))
        except OSError:
            continue
    for plugin_file in REAPER_PLUGIN_FILES:
        try:
            if not plugin_file.exists():
                continue
            for line in plugin_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line.strip() or line.startswith("["):
                    continue
                names.add(line.split(",", 1)[0].split("=", 1)[0].strip())
            sources.append(str(plugin_file))
        except OSError:
            continue
    return {"names": sorted(names), "sources": sorted(set(sources))}


def resolve_role(role: str, available_names: Iterable[str]) -> dict[str, object]:
    spec = PLUGIN_ROLES[role]
    preferred = [str(item) for item in spec["preferred"]]
    fallback = str(spec["fallback"])
    normalized_available = {_normalize(name): name for name in available_names}
    detected = []
    for candidate in preferred:
        candidate_norm = _normalize(candidate)
        match = next((actual for key, actual in normalized_available.items() if candidate_norm and candidate_norm in key), None)
        if match:
            detected.append({"requested": candidate, "detected_name": match})
    selected = detected[0]["detected_name"] if detected else fallback
    return {
        "role": role,
        "preferred": preferred,
        "fallback": fallback,
        "detected": detected,
        "selected_plugin": selected,
        "uses_fallback": not bool(detected),
        "insertion_policy": "REAPER Lua attempts insertion by name; if unavailable it records missing_fx metadata and manual notes.",
    }


def plugin_map_yaml() -> str:
    lines = [
        "# Suno/Reaper harness v0.5 plugin role map.",
        "# Edit preferred lists if your installed REAPER plugin names differ.",
        "roles:",
    ]
    for role, spec in PLUGIN_ROLES.items():
        lines.append(f"  {role}:")
        lines.append("    preferred:")
        for candidate in spec["preferred"]:
            lines.append(f"      - {candidate}")
        lines.append(f"    fallback: {spec['fallback']}")
    return "\n".join(lines) + "\n"


def write_plugin_inventory(project_dir: str | Path) -> dict[str, object]:
    root = Path(project_dir)
    config_dir = root / "config"
    report_dir = root / "reports"
    config_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    plugin_map_path = config_dir / "plugin_map.yaml"
    if not plugin_map_path.exists():
        plugin_map_path.write_text(plugin_map_yaml(), encoding="utf-8")

    scanned = scan_plugin_names()
    roles = {role: resolve_role(role, scanned["names"]) for role in PLUGIN_ROLES}
    payload = {
        "schema_version": "reaper_plugin_inventory.v0.5",
        "plugin_map": str(plugin_map_path),
        "scan_sources": scanned["sources"],
        "available_plugin_name_count": len(scanned["names"]),
        "available_plugin_names": scanned["names"],
        "roles": roles,
        "claim_rule": "Detected plugins are availability hints. Do not claim plugin processing was applied until REAPER insertion and render are verified.",
    }
    (report_dir / "plugin_inventory.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Plugin Inventory",
        "",
        "- Harness version: v0.5",
        f"- Plugin map: `{plugin_map_path}`",
        f"- Safe scan sources inspected: {len(scanned['sources'])}",
        f"- Available plugin name hints: {len(scanned['names'])}",
        "- Claim rule: detected plugins are hints only; rendered/plugin-applied claims require REAPER verification.",
        "",
        "| role | selected | fallback? | detected preferred | fallback |",
        "| --- | --- | --- | --- | --- |",
    ]
    for role, item in roles.items():
        detected = ", ".join(match["detected_name"] for match in item["detected"]) or "none"
        lines.append(
            f"| {role} | {item['selected_plugin']} | {str(item['uses_fallback']).lower()} | {detected} | {item['fallback']} |"
        )
    (report_dir / "plugin_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manual_lines = [
        "# Manual Plugin Notes",
        "",
        "REAPER Lua will attempt safe plugin insertion by name. If a premium plugin is not present or REAPER uses a different exact name, the project still opens with stock fallbacks/placeholders.",
        "",
        "| role | manual instruction |",
        "| --- | --- |",
    ]
    for role, item in roles.items():
        action = (
            f"Use `{item['selected_plugin']}` if it appears on the track. "
            f"If missing, insert `{item['fallback']}` and follow the role-specific settings in the mix reports."
        )
        manual_lines.append(f"| {role} | {action} |")
    (report_dir / "manual_plugin_notes.md").write_text("\n".join(manual_lines) + "\n", encoding="utf-8")
    return payload

