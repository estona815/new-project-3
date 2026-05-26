#!/usr/bin/env python3
"""Scan local REAPER/plugin capability for automation planning.

This is an inventory and routing report, not permission to use paid plugins.
Default automation remains REAPER stock/JSFX/free tools unless the user
explicitly allows an installed paid plugin.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
REPORTS_DIR = PROJECT_ROOT / "reports"
REAPER_RESOURCE = Path.home() / "Library/Application Support/REAPER"
PLUGIN_DIRS = [
    Path.home() / "Library/Audio/Plug-Ins",
    Path("/Library/Audio/Plug-Ins"),
]


CATEGORY_RULES = {
    "eq_dynamic_eq": ["reaeq", "nova", "equalizer", "eq"],
    "compressor_limiter": ["reacomp", "reaxcomp", "realimit", "kotelnikov", "1176", "la-2a", "clip", "limiter"],
    "reverb_space": ["reaverb", "reaverbate", "valhalla", "raum", "supermassive", "vintageverb", "verb"],
    "delay": ["readelay", "delay", "echo"],
    "saturation_distortion": ["saturation", "decapitator", "ivgi", "krush", "byod", "distort", "drive"],
    "stereo_ms": ["wider", "imager", "doubler", "stereo", "width", "m/s", "ms"],
    "meter_analyzer": ["meter", "mvMeter", "loudness", "analyzer", "scope"],
    "pitch_tune_optional": ["graillon", "autopitch", "pitch"],
}


PAID_OR_REQUIRES_PERMISSION = [
    "soundtoys",
    "decapitator",
    "valhalla",
    "ozone",
    "izotope",
    "uad",
    "uaudio",
    "slate",
    "fresh air",
]


def classify(name: str) -> List[str]:
    low = name.lower()
    cats = []
    for cat, keys in CATEGORY_RULES.items():
        if any(k.lower() in low for k in keys):
            cats.append(cat)
    return cats or ["uncategorized"]


def permission_class(path: Path) -> str:
    low = str(path).lower()
    if path.name.lower().startswith(("rea", "js:")):
        return "stock_or_jsfx_preferred"
    if "tdr nova" in low or "tdr kotelnikov" in low or "freeclip" in low or "ivgi" in low or "krush" in low or "wider" in low or "mvMeter".lower() in low:
        return "free_or_likely_free_optional"
    if any(key in low for key in PAID_OR_REQUIRES_PERMISSION):
        return "installed_but_requires_explicit_user_allowance"
    if "antares" in low:
        return "forbidden"
    return "installed_optional_unknown_license"


def scan_plugin_dirs() -> List[dict]:
    rows = []
    for root in PLUGIN_DIRS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() in {".vst3", ".component", ".vst"}:
                rows.append({
                    "name": path.stem,
                    "path": str(path),
                    "format": path.suffix.lower().lstrip("."),
                    "categories": classify(path.name),
                    "permission_class": permission_class(path),
                })
    return rows


def scan_reaper_fxchains() -> List[dict]:
    fxchains = []
    folder = REAPER_RESOURCE / "FXChains"
    if not folder.exists():
        return fxchains
    for path in sorted(folder.glob("*.RfxChain")):
        fxchains.append({
            "name": path.stem,
            "path": str(path),
            "categories": classify(path.name),
            "permission_class": permission_class(path),
        })
    return fxchains


def scan_reaper_ini_plugins() -> dict:
    data = {}
    for ini_name in ["reaper-vstplugins_arm64.ini", "reaper-auplugins_arm64.ini", "reaper-clap-macos-aarch64.ini"]:
        path = REAPER_RESOURCE / ini_name
        if path.exists():
            lines = [line.strip() for line in path.read_text(errors="ignore").splitlines() if line.strip() and not line.startswith("[")]
            data[ini_name] = lines[:300]
    return data


def stock_tool_map() -> List[dict]:
    return [
        {"name": "ReaEQ", "categories": ["eq_dynamic_eq"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "static EQ points, broad tonal shaping, resonance notches"},
        {"name": "ReaComp", "categories": ["compressor_limiter"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "vocal/instrument/mix bus leveling"},
        {"name": "ReaXcomp", "categories": ["eq_dynamic_eq", "compressor_limiter"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "dynamic EQ by band, de-harsh, de-mud, de-ess proxy"},
        {"name": "ReaLimit", "categories": ["compressor_limiter"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "master limiter with safe ceiling"},
        {"name": "ReaDelay", "categories": ["delay"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "tempo delay throws and subtle width"},
        {"name": "ReaVerbate/ReaVerb", "categories": ["reverb_space"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "short room/glue or IR reverb if available"},
        {"name": "JSFX estona_DigiClip", "categories": ["saturation_distortion"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "soft clipping/density"},
        {"name": "JSFX estona_MonoSub_Guard", "categories": ["stereo_ms"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "low-end mono compatibility"},
        {"name": "JSFX estona_Vocal_AntiAI_Harsh", "categories": ["eq_dynamic_eq"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "harshness/sibilance reduction"},
        {"name": "JSFX estona_Vocal_Beat_Glue", "categories": ["compressor_limiter", "saturation_distortion"], "permission_class": "stock_or_jsfx_preferred", "automation_use": "gentle bus glue"},
    ]


def build_capability_matrix(rows: List[dict]) -> dict:
    matrix: Dict[str, List[dict]] = {cat: [] for cat in CATEGORY_RULES}
    matrix["uncategorized"] = []
    for row in rows:
        for cat in row["categories"]:
            matrix.setdefault(cat, []).append({
                "name": row["name"],
                "permission_class": row["permission_class"],
                "format": row.get("format", "stock/jsfx/fxchain"),
            })
    return matrix


def write_reports(data: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "reaper_plugin_capability_scan.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# REAPER Plugin Capability Scan",
        "",
        "This is an inventory. Installed paid plugins are not used automatically.",
        "",
        f"- Plugin files found: {len(data['installed_plugins'])}",
        f"- FXChains found: {len(data['fxchains'])}",
        "",
        "## Preferred Automation Tools",
    ]
    for row in data["stock_tools"]:
        lines.append(f"- {row['name']}: {row['automation_use']}")
    lines += ["", "## Capability Matrix"]
    for cat, rows in data["capability_matrix"].items():
        if not rows:
            continue
        lines.append(f"### {cat}")
        for row in rows[:30]:
            lines.append(f"- {row['name']} ({row['format']}): {row['permission_class']}")
    lines += [
        "",
        "## Policy",
        "- Use REAPER stock/JSFX first.",
        "- TDR Nova/Kotelnikov, FreeClip, IVGI2, Krush, Wider, mvMeter may be optional if confirmed working.",
        "- Valhalla, Soundtoys, Ozone, UAD, Slate-style tools require explicit user allowance before automation.",
        "- Antares tools are forbidden by request.",
    ]
    (REPORTS_DIR / "reaper_plugin_capability_scan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    installed = scan_plugin_dirs()
    fxchains = scan_reaper_fxchains()
    stock = stock_tool_map()
    all_rows = installed + fxchains + stock
    data = {
        "reaper_resource_path": str(REAPER_RESOURCE),
        "installed_plugins": installed,
        "fxchains": fxchains,
        "stock_tools": stock,
        "reaper_ini_plugin_cache": scan_reaper_ini_plugins(),
        "capability_matrix": build_capability_matrix(all_rows),
        "policy": {
            "stock_jsfx_first": True,
            "paid_plugins_require_explicit_allowance": True,
            "antares_forbidden": True,
        },
    }
    write_reports(data)
    print(json.dumps({"installed_plugins": len(installed), "fxchains": len(fxchains), "reports": ["reaper_plugin_capability_scan.md"]}, indent=2))


if __name__ == "__main__":
    main()
