from __future__ import annotations

import json
import platform
import re
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


PROJECT_CONTEXT_SCHEMA = "automix-project-context-v1"


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_rpp_project(path: Path) -> dict[str, Any]:
    if not path or not path.exists() or not path.is_file():
        return {"tracks": [], "media_items_count": 0, "existing_fx_chains": [], "warnings": ["project_file_missing_or_not_provided"]}
    if path.suffix.lower() == ".json":
        data = _safe_json(path) or {}
        tracks = data.get("tracks", []) if isinstance(data.get("tracks"), list) else []
        normalized_tracks = []
        for idx, track in enumerate(tracks):
            fx = track.get("fx", track.get("fx_chain", [])) if isinstance(track, dict) else []
            media_items = track.get("media_items", track.get("items", [])) if isinstance(track, dict) else []
            media_paths: list[str] = []
            if isinstance(media_items, list):
                for item in media_items:
                    if isinstance(item, dict) and item.get("path"):
                        media_paths.append(str(item.get("path")))
                    elif isinstance(item, str):
                        media_paths.append(item)
            normalized_tracks.append(
                {
                    "track_index": int(track.get("track_index", idx + 1)) if isinstance(track, dict) else idx + 1,
                    "name": str(track.get("name", f"Track {idx + 1}")) if isinstance(track, dict) else f"Track {idx + 1}",
                    "track_guid": str(track.get("track_guid", track.get("guid", ""))) if isinstance(track, dict) else "",
                    "folder_depth": int(track.get("folder_depth", 0)) if isinstance(track, dict) else 0,
                    "media_items": len(media_items) if isinstance(media_items, list) else int(media_items or 0),
                    "media_paths": media_paths,
                    "fx_count": len(fx) if isinstance(fx, list) else int(fx or 0),
                    "fx": fx if isinstance(fx, list) else [],
                    "role": track.get("role", "unknown") if isinstance(track, dict) else "unknown",
                    "channel_count": int(track.get("channel_count", track.get("nchan", 2))) if isinstance(track, dict) else 2,
                    "volume": float(track.get("volume", 1.0)) if isinstance(track, dict) else 1.0,
                    "pan": float(track.get("pan", 0.0)) if isinstance(track, dict) else 0.0,
                    "send_count": int(track.get("send_count", len(track.get("sends", [])) if isinstance(track.get("sends"), list) else 0)) if isinstance(track, dict) else 0,
                    "receive_count": int(track.get("receive_count", len(track.get("receives", [])) if isinstance(track.get("receives"), list) else 0)) if isinstance(track, dict) else 0,
                    "take_pitch_playrate_states": track.get("take_pitch_playrate_states", []) if isinstance(track, dict) else [],
                }
            )
        return {
            "tracks": normalized_tracks,
            "media_items_count": sum(int(track.get("media_items", 0)) for track in normalized_tracks),
            "existing_fx_chains": [track for track in normalized_tracks if track.get("fx")],
            "warnings": list(data.get("warnings", [])),
        }
    text = path.read_text(encoding="utf-8", errors="ignore")
    tracks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    before_first_track = True
    master_fx_count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<TRACK"):
            before_first_track = False
            current = {
                "name": "",
                "track_guid": "",
                "folder_depth": 0,
                "fx": [],
                "media_items": 0,
                "media_paths": [],
                "channel_count": 2,
                "volume": 1.0,
                "pan": 0.0,
                "send_count": 0,
                "receive_count": 0,
                "take_pitch_playrate_states": [],
            }
            tracks.append(current)
        elif before_first_track and re.match(r"^<(?:VST|JS|AU|CLAP|LV2|DX)\b", stripped, re.IGNORECASE):
            master_fx_count += 1
        elif current is not None and stripped.startswith("NAME ") and not current.get("name"):
            current["name"] = stripped[5:].strip().strip('"')
        elif current is not None and stripped.startswith("TRACKID "):
            current["track_guid"] = stripped[8:].strip()
        elif current is not None and stripped.startswith("FOLDERDEPTH "):
            try:
                current["folder_depth"] = int(stripped.split()[1])
            except (IndexError, ValueError):
                current["folder_depth"] = 0
        elif current is not None and stripped.startswith("NCHAN "):
            try:
                current["channel_count"] = int(stripped.split()[1])
            except (IndexError, ValueError):
                current["channel_count"] = 2
        elif current is not None and stripped.startswith("VOLPAN "):
            parts = stripped.split()
            try:
                current["volume"] = float(parts[1])
                current["pan"] = float(parts[2])
            except (IndexError, ValueError):
                pass
        elif current is not None and stripped.startswith("<ITEM"):
            current["media_items"] += 1
        elif current is not None and stripped.startswith("FILE "):
            match = re.search(r'FILE\s+"([^"]+)"', stripped)
            if match:
                current["media_paths"].append(match.group(1))
        elif current is not None and (stripped.startswith("PLAYRATE ") or stripped.startswith("PITCH ")):
            current["take_pitch_playrate_states"].append(stripped)
        elif current is not None and re.match(r"^<(?:VST|JS|AU|CLAP|LV2|DX)\b", stripped, re.IGNORECASE):
            current["fx"].append(stripped[:120])
        elif current is not None and stripped.startswith("AUXSEND "):
            current["send_count"] += 1
        elif current is not None and stripped.startswith("AUXRECV "):
            current["receive_count"] += 1
    media_items_count = len(re.findall(r"(?m)^\s*<ITEM\b", text))
    return {
        "tracks": [
            {
                "track_index": idx + 1,
                "name": track.get("name") or f"Track {idx + 1}",
                "track_guid": track.get("track_guid", ""),
                "folder_depth": track.get("folder_depth", 0),
                "media_items": track.get("media_items", 0),
                "media_paths": track.get("media_paths", []),
                "fx_count": len(track.get("fx", [])),
                "fx": track.get("fx", []),
                "channel_count": track.get("channel_count", 2),
                "volume": track.get("volume", 1.0),
                "pan": track.get("pan", 0.0),
                "send_count": track.get("send_count", 0),
                "receive_count": track.get("receive_count", 0),
                "take_pitch_playrate_states": track.get("take_pitch_playrate_states", []),
            }
            for idx, track in enumerate(tracks)
        ],
        "media_items_count": media_items_count,
        "existing_fx_chains": [track for track in tracks if track.get("fx")],
        "master_fx_count": master_fx_count,
        "warnings": [],
    }


def _available_files(directory: Path, patterns: list[str]) -> list[str]:
    out: list[str] = []
    for pattern in patterns:
        out.extend(str(path) for path in sorted(directory.glob(pattern)) if path.is_file())
    return sorted(set(out))


def resolve_project_context(
    *,
    project_path: str | Path | None,
    output_dir: Path,
    target_profile: str,
    references: list[str] | None = None,
) -> dict[str, Any]:
    path = Path(project_path).expanduser() if project_path else Path("")
    parsed = _parse_rpp_project(path)
    reports = _available_files(output_dir, ["analysis_reports/*.json", "eval_reports/*.json", "eval_reports/*.md", "chain_plans/*.json"])
    rollback_files = _available_files(output_dir, ["rollback/*.json"])
    reference_files = [str(Path(ref)) for ref in references or []]
    inventory = _safe_json(output_dir / "analysis_reports" / "plugin_inventory_audit.json")
    manifest = _safe_json(output_dir / "orchestrator" / "automix_orchestration_manifest.json")
    warnings = list(parsed.get("warnings", []))
    if not project_path:
        warnings.append("project_path_empty_report_only_context")

    context = {
        "schema": PROJECT_CONTEXT_SCHEMA,
        "project_name": path.stem if project_path and path.stem else "project",
        "project_path": str(path) if project_path else "",
        "reaper_version": (inventory or {}).get("reaper_version", "unknown"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "created_at": now_utc(),
        "tracks_count": len(parsed.get("tracks", [])),
        "media_items_count": parsed.get("media_items_count", 0),
        "track_list": parsed.get("tracks", []),
        "existing_fx_chains": parsed.get("existing_fx_chains", []),
        "routing_summary": {
            "source": "offline_rpp_parse_or_empty",
            "master_fx_count": parsed.get("master_fx_count", 0),
            "track_send_count": sum(int(track.get("send_count", 0)) for track in parsed.get("tracks", [])),
            "track_receive_count": sum(int(track.get("receive_count", 0)) for track in parsed.get("tracks", [])),
            "warnings": [],
        },
        "known_automix_folders": [str(path) for path in sorted(output_dir.glob("*")) if path.is_dir()],
        "previous_automix_state_found": bool(manifest),
        "available_reports": reports,
        "available_rollback_files": rollback_files,
        "available_references": reference_files,
        "target_profile": target_profile,
        "plugin_inventory_status": (inventory or {}).get("summary", {}),
        "accepted_rejected_stage_statuses": {},
        "warnings": sorted(set(warnings)),
    }
    write_json(output_dir / "orchestrator" / "project_context.json", context)
    return context
