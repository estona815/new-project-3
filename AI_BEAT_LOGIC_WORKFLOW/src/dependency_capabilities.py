from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import shutil
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from paths import PROJECT_ROOT


SCHEMA_VERSION = "dependency_capabilities.v1"
DEFAULT_LOGIC_APP_PATH = Path("/Applications/Logic Pro.app")
AU_PLUGIN_DIRS = (
    Path("/Library/Audio/Plug-Ins/Components"),
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "Components",
)


def _platform_name(system: str | None = None) -> str:
    value = system or platform.system()
    if value == "Darwin":
        return "macOS"
    if value == "Linux":
        return "linux"
    if value == "Windows":
        return "windows"
    return "unknown"


def _run_version(command: list[str], timeout: float = 2.0) -> str | None:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else None


def _tool_status(
    name: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    version_command: list[str] | None = None,
) -> dict[str, Any]:
    path = which(name)
    status: dict[str, Any] = {"available": bool(path)}
    if path:
        status["path"] = path
        if version_command:
            status["version"] = _run_version([path, *version_command])
    elif version_command:
        status["version"] = None
    return status


def _stdlib_wav_status() -> dict[str, Any]:
    return {
        "available": hasattr(wave, "open"),
        "module": "wave",
        "version": None,
    }


def _python_package_status(module_name: str, distribution_name: str | None = None) -> dict[str, Any]:
    available = importlib.util.find_spec(module_name) is not None
    version = None
    if available:
        try:
            version = importlib.metadata.version(distribution_name or module_name)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return {"available": available, "version": version}


def _logic_status(platform_name: str, logic_app_path: Path = DEFAULT_LOGIC_APP_PATH) -> dict[str, Any]:
    available = platform_name == "macOS" and logic_app_path.exists()
    return {"available": available, "path": str(logic_app_path) if available else None}


def _scan_au_components(name_terms: tuple[str, ...], plugin_dirs: tuple[Path, ...] = AU_PLUGIN_DIRS) -> list[str]:
    matches: list[str] = []
    lowered_terms = tuple(term.lower() for term in name_terms)
    for directory in plugin_dirs:
        try:
            if not directory.exists():
                continue
            for path in directory.glob("*.component"):
                lowered_name = path.name.lower()
                if any(term in lowered_name for term in lowered_terms):
                    matches.append(str(path))
        except OSError:
            continue
    return sorted(matches)


def _plugin_status(platform_name: str) -> dict[str, Any]:
    decapitator_paths = _scan_au_components(("decapitator", "soundtoys"))
    return {
        "autotune_like": {
            "available": False,
            "status": "manual_required",
            "detected": False,
            "note": "AutoTune-like plugin detection is intentionally generic; do not claim pitch plugin application without verified processing.",
        },
        "soundtoys_decapitator": {
            "available": bool(decapitator_paths),
            "status": "detected_manual_required" if decapitator_paths else "not_detected",
            "detected": bool(decapitator_paths),
            "paths": decapitator_paths,
            "check_method": "safe_audio_unit_component_scan" if platform_name == "macOS" else "not_applicable",
            "note": (
                "Soundtoys Decapitator appears installed; insertion still requires manual or verified Logic automation."
                if decapitator_paths
                else "Soundtoys Decapitator was not detected; use manual instruction or generic saturation fallback language."
            ),
        },
    }


def _first_available(tools: dict[str, dict[str, Any]], names: tuple[str, ...], fallback: str = "unavailable") -> str:
    for name in names:
        if tools.get(name, {}).get("available"):
            return name
    return fallback


def _capabilities(tools: dict[str, dict[str, Any]], platform_name: str) -> tuple[dict[str, Any], list[str]]:
    limitations: list[str] = []
    metadata_probe = _first_available(tools, ("ffprobe", "afinfo"), "stdlib")
    wav_export = _first_available(tools, ("ffmpeg", "afconvert"), "unavailable")
    if wav_export == "unavailable":
        limitations.append("No ffmpeg or afconvert was found; final WAV export must be blocked until an export backend is available.")
    bpm = "essentia" if tools["essentia"]["available"] else "librosa" if tools["librosa"]["available"] else "stdlib_heuristic"
    key = "essentia" if tools["essentia"]["available"] else "librosa" if tools["librosa"]["available"] else "low_confidence_heuristic"
    vocal_pitch = "pyin" if tools["librosa"]["available"] else "heuristic" if tools["python_stdlib_wav"]["available"] else "unavailable"
    logic_project_creation = (
        "available"
        if platform_name == "macOS" and tools["logic_pro"]["available"] and tools["osascript"]["available"]
        else "manual_required"
        if platform_name == "macOS" and tools["logic_pro"]["available"]
        else "unavailable"
    )
    plugin_automation = "manual_required" if tools["logic_pro"]["available"] else "unavailable"
    if plugin_automation == "manual_required":
        limitations.append("Plugin availability checks do not prove plugin insertion; plugin-applied claims require verified processing.")
    if logic_project_creation != "available":
        limitations.append("Logic automation is unavailable or manual-only; Logic success must require a verified project/export artifact.")

    return (
        {
            "metadata_probe": metadata_probe,
            "wav_export": wav_export,
            "peak_rms_analysis": tools["python_stdlib_wav"]["available"],
            "rough_onset_analysis": tools["python_stdlib_wav"]["available"],
            "bpm_estimation": bpm,
            "key_estimation": key,
            "vocal_pitch_tracking": vocal_pitch,
            "logic_project_creation": logic_project_creation,
            "plugin_automation": plugin_automation,
        },
        limitations,
    )


def collect_dependency_capabilities(
    *,
    checked_at: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    logic_app_path: Path = DEFAULT_LOGIC_APP_PATH,
) -> dict[str, Any]:
    platform_name = _platform_name()
    tools: dict[str, dict[str, Any]] = {
        "python_stdlib_wav": _stdlib_wav_status(),
        "ffmpeg": _tool_status("ffmpeg", which=which, version_command=["-version"]),
        "ffprobe": _tool_status("ffprobe", which=which, version_command=["-version"]),
        "afinfo": _tool_status("afinfo", which=which),
        "afconvert": _tool_status("afconvert", which=which),
        "sox": _tool_status("sox", which=which, version_command=["--version"]),
        "librosa": _python_package_status("librosa"),
        "essentia": _python_package_status("essentia"),
        "numpy": _python_package_status("numpy"),
        "scipy": _python_package_status("scipy"),
        "soundfile": _python_package_status("soundfile", "soundfile"),
        "logic_pro": _logic_status(platform_name, logic_app_path),
        "osascript": _tool_status("osascript", which=which),
    }
    plugins = _plugin_status(platform_name)
    capabilities, limitations = _capabilities(tools, platform_name)
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "platform": platform_name,
            "checked_at": checked_at or datetime.now(timezone.utc).isoformat(),
        },
        "tools": tools,
        "plugins": plugins,
        "capabilities": capabilities,
        "limitations": limitations,
    }


def write_dependency_capabilities(
    project_root: Path = PROJECT_ROOT,
    *,
    capabilities: dict[str, Any] | None = None,
) -> Path:
    payload = capabilities or collect_dependency_capabilities()
    output_path = project_root / "01_ANALYSIS" / "dependency_capabilities.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
