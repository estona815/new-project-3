from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


NOTE_TOKEN_RE = re.compile(r"\b(?:note|NOTE)\s*[:=]\s*(\d{1,3})\b")
REAPER_EVENT_RE = re.compile(r"^\s*E\s+\d+\s+[0-9A-Fa-f]{2}\s+([0-9A-Fa-f]{2})\s+([0-9A-Fa-f]{2})")
FILE_RE = re.compile(r'\bFILE\s+"([^"]+)"')


def _track_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    lines = text.splitlines()
    current: list[str] = []
    depth = 0
    in_track = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<TRACK"):
            in_track = True
            current = [line]
            depth = 1
            continue
        if in_track:
            current.append(line)
            if stripped.startswith("<") and not stripped.startswith("<TRACK"):
                depth += 1
            if stripped == ">":
                depth -= 1
                if depth <= 0:
                    blocks.append("\n".join(current))
                    current = []
                    in_track = False
    return blocks


def _track_name(block: str, index: int) -> str:
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("NAME "):
            return stripped[5:].strip().strip('"')
    return f"TRACK_{index:02d}"


def _muted(block: str) -> bool:
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("MUTESOLO "):
            parts = stripped.split()
            if len(parts) > 1:
                return parts[1] == "1"
    return False


def _media_files(block: str) -> list[str]:
    return FILE_RE.findall(block)


def _note_numbers(block: str) -> list[int]:
    notes: list[int] = []
    for match in NOTE_TOKEN_RE.finditer(block):
        note = int(match.group(1))
        if 0 <= note <= 127:
            notes.append(note)
    for line in block.splitlines():
        match = REAPER_EVENT_RE.match(line)
        if not match:
            continue
        status = int(match.group(1), 16)
        note = int(match.group(2), 16)
        if 0x90 <= status <= 0x9F and 0 <= note <= 127:
            notes.append(note)
    return notes


def _role_from_name(name: str) -> set[str]:
    lowered = name.lower()
    roles: set[str] = set()
    if any(term in lowered for term in ("kick", "snare", "clap", "hat", "perc", "drum")):
        roles.add("drums")
    if "bass" in lowered or "808" in lowered:
        roles.add("bass")
    if any(term in lowered for term in ("music", "chord", "lead", "synth", "keys", "guitar", "piano")):
        roles.add("music")
    if "vocal" in lowered:
        roles.add("vocal")
    return roles


def _stem_track(name: str) -> bool:
    lowered = name.lower()
    return "stem" in lowered and "missing" not in lowered and "unavailable" not in lowered


def _bus_render_map(bus_render_dir: str | Path | None, explicit: list[str] | None = None) -> dict[str, list[str]]:
    result = {"drums": [], "bass": [], "music": [], "mix": [], "master": []}
    paths = [Path(value) for value in (explicit or [])]
    if bus_render_dir:
        root = Path(bus_render_dir)
        if root.exists():
            paths.extend(path for path in root.glob("*.wav") if path.is_file())
    for path in paths:
        lowered = path.name.lower()
        for role in result:
            if role in lowered:
                result[role].append(str(path))
    return result


def audit_reaper_midi_reconstruction(
    rpp_path: str | Path,
    *,
    bus_render_dir: str | Path | None = None,
    bus_renders: list[str] | None = None,
) -> dict[str, Any]:
    findings: list[Finding] = []
    path = Path(rpp_path)
    if not path.exists():
        add_finding(
            "FAIL",
            "RPP_MISSING",
            "REAPER project file is missing.",
            str(path),
            "Create the REAPER session and rerun MIDI reconstruction audit.",
            findings,
            affected_file=str(path),
            failed_assumption="RPP exists for audit.",
        )
        return {
            "schema_version": 1,
            "rpp": str(path),
            "tracks": [],
            "true_rebeat_allowed": False,
            "classification_recommendation": "blocked",
            "max_severity": max_severity(findings),
            "findings": findings_to_dicts(findings),
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = _track_blocks(text)
    if not blocks:
        add_finding(
            "FAIL",
            "RPP_TRACK_PARSE_FAILED",
            "No REAPER track blocks could be parsed.",
            f"size_bytes={path.stat().st_size}",
            "Inspect the RPP syntax or regenerate the session.",
            findings,
            affected_file=str(path),
            failed_assumption="RPP contains parseable tracks.",
        )

    tracks: list[dict[str, Any]] = []
    kick = snare = hat = bass = music = 0
    has_drum_audio_support = False
    has_stem_tracks = False
    original_fullmix_active = False
    source_media: list[str] = []

    for index, block in enumerate(blocks, start=1):
        name = _track_name(block, index)
        roles = _role_from_name(name)
        media = _media_files(block)
        source_media.extend(media)
        notes = _note_numbers(block)
        has_midi = "<SOURCE MIDI" in block or bool(notes)
        has_audio = bool(media) and any(Path(item).suffix.lower() in {".wav", ".flac", ".mp3", ".aif", ".aiff"} for item in media)
        muted = _muted(block)
        lowered = name.lower()

        if "fullmix" in lowered or "working_fullmix" in lowered:
            if not muted and has_audio:
                original_fullmix_active = True
        if _stem_track(name):
            has_stem_tracks = True
        if "drums_audio_support" in lowered and has_audio:
            has_drum_audio_support = True

        if has_midi:
            if "kick" in lowered:
                kick += len(notes) or 1
            elif "snare" in lowered or "clap" in lowered:
                snare += len(notes) or 1
            elif "hat" in lowered or "perc" in lowered:
                hat += len(notes) or 1
            elif "drum" in lowered:
                for note in notes:
                    if note == 36:
                        kick += 1
                    elif note in {38, 40}:
                        snare += 1
                    elif note in {42, 46, 39, 51}:
                        hat += 1
                if not notes:
                    kick += 1
            elif "bass" in lowered:
                bass += len(notes) or 1
            elif any(term in lowered for term in ("music", "chord", "lead", "synth", "keys", "guitar", "piano")):
                music += len(notes) or 1

        tracks.append(
            {
                "index": index,
                "name": name,
                "roles": sorted(roles),
                "muted": muted,
                "has_midi": has_midi,
                "midi_note_count": len(notes),
                "note_numbers": notes[:500],
                "has_audio": has_audio,
                "media_files": media,
            }
        )

    bus_render_map = _bus_render_map(bus_render_dir, bus_renders)
    has_separate_bus_renders = all(bus_render_map[role] for role in ("drums", "bass", "music", "mix", "master"))

    has_drum_midi = kick + snare + hat > 0
    has_bass_midi = bass > 0
    has_music_midi = music > 0
    rebuild_roles = []
    if has_drum_midi or has_drum_audio_support:
        rebuild_roles.append("drums")
    if has_bass_midi or bus_render_map["bass"]:
        rebuild_roles.append("bass")
    if has_music_midi or bus_render_map["music"]:
        rebuild_roles.append("music")

    true_rebeat_allowed = bool(has_drum_midi and has_bass_midi and has_music_midi and has_separate_bus_renders and not original_fullmix_active)
    if not has_drum_midi and has_drum_audio_support:
        add_finding(
            "WARN",
            "DRUM_AUDIO_SUPPORT_WITHOUT_MIDI",
            "Drum support audio exists but no drum MIDI reconstruction was found.",
            "has_drum_audio_support=true, has_drum_midi=false",
            "Use drum_reinforcement language unless MIDI reconstruction is added and audited.",
            findings,
            affected_file=str(path),
            failed_assumption="Drum support equals MIDI reconstruction.",
            human_listening_required=True,
        )
    if not has_separate_bus_renders:
        add_finding(
            "WARN",
            "REBEAT_BUS_RENDERS_MISSING",
            "Separate bus renders required for true_rebeat are missing.",
            json.dumps(bus_render_map, sort_keys=True),
            "Render drums, bass, music/support, mix, and master buses, then rerun audit.",
            findings,
            affected_file=str(bus_render_dir or path),
            failed_assumption="Role bus render evidence exists.",
        )
    if original_fullmix_active and (has_drum_midi or has_bass_midi or has_music_midi):
        add_finding(
            "WARN",
            "FULLMIX_ACTIVE_WITH_REBUILD_ITEMS",
            "The fullmix is active while reconstruction items exist.",
            "original_fullmix_active=true",
            "Classify as drum reinforcement or partial rebeat unless the independent arrangement can play without fullmix reliance.",
            findings,
            affected_file=str(path),
            failed_assumption="Rebuild items are the primary sound source.",
            human_listening_required=True,
        )

    if true_rebeat_allowed:
        classification = "true_rebeat"
    elif has_drum_midi and not (has_bass_midi or has_music_midi):
        classification = "drum_reinforcement" if original_fullmix_active else "partial_rebeat"
    elif has_drum_midi or has_bass_midi or has_music_midi:
        classification = "partial_rebeat"
    elif has_stem_tracks:
        classification = "stem_assisted_rebuild"
    elif original_fullmix_active:
        classification = "fullmix_rescue"
    else:
        classification = "master_only"

    dependency = "high" if original_fullmix_active and not (has_bass_midi and has_music_midi) else "medium" if original_fullmix_active else "low"
    payload = {
        "schema_version": 1,
        "rpp": str(path),
        "track_count": len(tracks),
        "tracks": tracks,
        "source_media_references": sorted(set(source_media)),
        "has_drum_midi": has_drum_midi,
        "kick_note_count": kick,
        "snare_note_count": snare,
        "hat_note_count": hat,
        "has_bass_midi": has_bass_midi,
        "bass_note_count": bass,
        "has_music_midi": has_music_midi,
        "music_note_count": music,
        "has_drum_audio_support": has_drum_audio_support,
        "has_stem_tracks": has_stem_tracks,
        "has_separate_bus_renders": has_separate_bus_renders,
        "bus_renders": bus_render_map,
        "original_fullmix_active": original_fullmix_active,
        "fullmix_dependency_level": dependency,
        "rebuild_roles": rebuild_roles,
        "true_rebeat_allowed": true_rebeat_allowed,
        "classification_recommendation": classification,
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    track_rows = [
        "| {index} | {name} | {roles} | {midi} | {notes} | {audio} | {muted} |".format(
            index=track.get("index"),
            name=track.get("name"),
            roles=",".join(track.get("roles", [])) or "-",
            midi=track.get("has_midi"),
            notes=track.get("midi_note_count"),
            audio=track.get("has_audio"),
            muted=track.get("muted"),
        )
        for track in payload.get("tracks", [])
    ]
    if not track_rows:
        track_rows.append("| - | - | - | - | - | - | - |")
    return "\n".join(
        [
            "# MIDI Reconstruction Audit",
            "",
            f"- RPP: `{payload.get('rpp')}`",
            f"- Classification recommendation: `{payload.get('classification_recommendation')}`",
            f"- True rebeat allowed: `{payload.get('true_rebeat_allowed')}`",
            f"- Fullmix dependency: `{payload.get('fullmix_dependency_level')}`",
            f"- Bus renders complete: `{payload.get('has_separate_bus_renders')}`",
            "",
            "## Counts",
            "",
            f"- Kick notes: `{payload.get('kick_note_count')}`",
            f"- Snare notes: `{payload.get('snare_note_count')}`",
            f"- Hat/percussion notes: `{payload.get('hat_note_count')}`",
            f"- Bass notes: `{payload.get('bass_note_count')}`",
            f"- Music notes: `{payload.get('music_note_count')}`",
            "",
            "## Tracks",
            "",
            "| # | Name | Roles | MIDI | Notes | Audio | Muted |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *track_rows,
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit REAPER RPP MIDI/audio evidence for rebeat claims.")
    parser.add_argument("--rpp", required=True)
    parser.add_argument("--bus-render-dir")
    parser.add_argument("--bus-render", action="append", default=[])
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = audit_reaper_midi_reconstruction(args.rpp, bus_render_dir=args.bus_render_dir, bus_renders=args.bus_render)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
