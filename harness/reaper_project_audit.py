from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, add_finding, findings_to_dicts, has_warn_plus, max_severity
except ImportError:  # pragma: no cover
    from severity import Finding, add_finding, findings_to_dicts, has_warn_plus, max_severity


REQUIRED_TRACKS = [
    "01_REF_ORIGINAL",
    "02_WORKING_FULLMIX",
    "04_DRUMS_AUDIO_SUPPORT",
    "05_BASS",
    "06_MUSIC",
    "07_VOCAL_REPAIR",
    "08_FX_NOISE_REDUCTION",
    "09_PARALLEL_COMP",
    "10_MID_SIDE_REPAIR",
    "11_MIX_BUS",
    "12_MASTER_BUS",
    "13_MASTER_PRINT",
]
STEM_ROLE_TOKENS = {
    "drums": ("drum", "kick", "snare", "hat", "perc", "loop"),
    "bass": ("bass", "808", "sub"),
    "music": ("music", "synth", "key", "piano", "guitar", "melody", "inst", "instrumental"),
    "vocal": ("vocal", "vox", "lead", "bgv", "adlib", "voice"),
    "fx": ("fx", "sfx", "riser", "impact", "texture"),
}
FULLMIX_TOKENS = ("fullmix", "full_mix", "full mix", "2track", "two_track", "master", "original", "reference")


def _read_rpp(path: Path, findings: list[Finding]) -> str:
    if not path.exists():
        add_finding(
            "FAIL",
            "RPP_MISSING",
            "REAPER project file is missing.",
            f"Path does not exist: {path}",
            "Create the REAPER project with scripts/create_reaper_mix_session.lua or correct the path.",
            findings,
            affected_file=str(path),
            failed_assumption="A project file exists for the claimed render.",
            command_to_rerun=f"python3 -m harness.reaper_project_audit --project {path}",
        )
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.lstrip().startswith("<REAPER_PROJECT"):
        add_finding(
            "FAIL",
            "RPP_HEADER_INVALID",
            "File does not look like a REAPER .RPP project.",
            "Missing <REAPER_PROJECT header.",
            "Open and resave the project in REAPER, then rerun the audit.",
            findings,
            affected_file=str(path),
            failed_assumption="Project opens or is syntactically valid.",
        )
    return text


def _split_track_blocks(text: str) -> list[str]:
    parts = re.split(r"(?m)^\s*<TRACK\b", text)
    return ["<TRACK" + part for part in parts[1:]]


def _line_name(block: str) -> str:
    match = re.search(r'(?m)^\s*NAME\s+"([^"]*)"', block)
    return match.group(1) if match else ""


def _source_files(block: str) -> list[str]:
    return re.findall(r'(?m)^\s*FILE\s+"([^"]+)"', block)


def _fx_names(block: str) -> list[str]:
    return [
        match.group(2)
        for match in re.finditer(r'(?m)^\s*<(VST|VST3|JS|AU|CLAP|LV2)[^"]*"([^"]+)"', block)
    ]


def _role_from_name(name: str) -> str:
    lowered = name.lower()
    for role, tokens in STEM_ROLE_TOKENS.items():
        if any(token in lowered for token in tokens):
            return role
    return "other"


def _looks_fullmix(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in FULLMIX_TOKENS)


def audit_project(
    path: str | Path,
    findings: list[Finding] | None = None,
    *,
    mode: str = "auto",
    enforce_contract: bool = False,
) -> dict[str, Any]:
    findings = findings if findings is not None else []
    project_path = Path(path)
    text = _read_rpp(project_path, findings)
    track_blocks = _split_track_blocks(text)
    tracks = []
    custom_jsfx = []
    fullmix_primary_tracks = []
    fullmix_reference_tracks = []
    stem_track_roles = set()
    midi_item_count = 0
    item_count = 0
    source_media = []
    fx_names = []

    for index, block in enumerate(track_blocks, start=1):
        name = _line_name(block) or f"TRACK_{index:02d}"
        role = _role_from_name(name)
        item_count_for_track = len(re.findall(r"(?m)^\s*<ITEM\b", block))
        midi_count_for_track = len(re.findall(r"(?m)^\s*<SOURCE\s+MIDI\b", block))
        files = _source_files(block)
        fxs = _fx_names(block)
        item_count += item_count_for_track
        midi_item_count += midi_count_for_track
        source_media.extend(files)
        fx_names.extend(fxs)
        custom_jsfx.extend([fx for fx in fxs if fx.lower().startswith("js:")])
        if role in {"drums", "bass", "music", "vocal", "fx"} and (files or midi_count_for_track):
            stem_track_roles.add(role)
        fullmix_here = _looks_fullmix(name) or any(_looks_fullmix(file) for file in files)
        is_reference = "ref" in name.lower() or "reference" in name.lower()
        if fullmix_here and is_reference:
            fullmix_reference_tracks.append(name)
        elif fullmix_here:
            fullmix_primary_tracks.append(name)
        tracks.append(
            {
                "index": index,
                "name": name,
                "role": role,
                "item_count": item_count_for_track,
                "midi_item_count": midi_count_for_track,
                "source_files": files,
                "fx_names": fxs,
            }
        )

    render_metadata = sorted(set(re.findall(r"(?m)^\s*(RENDER_[A-Z0-9_]+)\b", text)))
    missing_required_tracks = [
        required for required in REQUIRED_TRACKS if not any(track["name"].startswith(required) for track in tracks)
    ]
    if enforce_contract and missing_required_tracks:
        add_finding(
            "FAIL",
            "RPP_REQUIRED_TRACKS_MISSING",
            "Project is missing required contract tracks.",
            ", ".join(missing_required_tracks),
            "Rebuild/update the session with scripts/create_reaper_mix_session.lua, then rerun the audit.",
            findings,
            affected_file=str(project_path),
            failed_assumption="The selected REAPER project follows the pipeline contract.",
            command_to_rerun=f"python3 -m harness.reaper_project_audit --project {project_path} --enforce-contract",
        )

    if item_count == 0:
        add_finding(
            "FAIL",
            "RPP_NO_ITEMS",
            "Project contains no media or MIDI items.",
            f"track_count={len(tracks)} item_count=0",
            "Import real source audio or MIDI items before claiming a mix, rebuild, or render.",
            findings,
            affected_file=str(project_path),
            failed_assumption="Project has timeline evidence.",
            command_to_rerun=f"python3 -m harness.reaper_project_audit --project {project_path} --mode {mode}",
        )

    if mode == "true_rebeat":
        has_required_rebeat_roles = {"drums", "bass", "music"}.issubset(stem_track_roles)
        if midi_item_count == 0 or not has_required_rebeat_roles:
            add_finding(
                "FAIL",
                "TRUE_REBEAT_EVIDENCE_MISSING",
                "True rebeat claim is not allowed without MIDI items and drum/bass/music timeline evidence.",
                f"midi_item_count={midi_item_count}, stem_track_roles={sorted(stem_track_roles)}",
                "Place or import explicit drum, bass, and music MIDI/audio items, save the project, and rerun the audit.",
                findings,
                affected_file=str(project_path),
                failed_assumption="Beat was fully recreated on the REAPER timeline.",
                command_to_rerun=f"python3 -m harness.reaper_project_audit --project {project_path} --mode true_rebeat --enforce-contract",
                human_listening_required=True,
            )

    if fullmix_primary_tracks and mode in {"true_rebeat", "stem_rebuild"}:
        add_finding(
            "WARN",
            "FULLMIX_PRIMARY_SOURCE_RISK",
            "Original fullmix appears to be used as a primary track in a rebuild-style mode.",
            ", ".join(fullmix_primary_tracks),
            "Move the fullmix to 01_REF_ORIGINAL muted/reference-only or downgrade the claim to fullmix rescue.",
            findings,
            affected_file=str(project_path),
            failed_assumption="The rebuild is not relying on the stereo fullmix as the main source.",
            command_to_rerun=f"python3 -m harness.reaper_project_audit --project {project_path} --mode {mode}",
            human_listening_required=True,
        )

    if not fx_names:
        add_finding(
            "WARN",
            "RPP_NO_FX_CHAIN",
            "Project has no detectable FX chain entries.",
            "No VST/JS/AU/CLAP/LV2 entries found in the .RPP text.",
            "Run scripts/apply_fx_chains.lua and rerun the project audit.",
            findings,
            affected_file=str(project_path),
            failed_assumption="Processing path is documented inside the project.",
            command_to_rerun=f"python3 -m harness.reaper_project_audit --project {project_path}",
        )

    add_finding(
        "PASS",
        "RPP_AUDIT_COMPLETED",
        "REAPER project text audit completed.",
        f"tracks={len(tracks)}, items={item_count}, midi_items={midi_item_count}, fx={len(fx_names)}",
        "Keep this audit report attached to any render claim.",
        findings,
        affected_file=str(project_path),
    )
    return {
        "project": str(project_path),
        "tracks": tracks,
        "track_count": len(tracks),
        "item_count": item_count,
        "source_media_references": source_media,
        "fx_chain_presence": bool(fx_names),
        "fx_names": sorted(set(fx_names)),
        "custom_jsfx_names": sorted(set(custom_jsfx)),
        "render_metadata_keys": render_metadata,
        "midi_item_count": midi_item_count,
        "stem_track_roles": sorted(stem_track_roles),
        "fullmix_reference_tracks": fullmix_reference_tracks,
        "fullmix_primary_tracks": fullmix_primary_tracks,
        "missing_required_tracks": missing_required_tracks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a REAPER .RPP project for claim evidence.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--mode", default="auto")
    parser.add_argument("--enforce-contract", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    audit = audit_project(args.project, findings, mode=args.mode, enforce_contract=args.enforce_contract)
    payload = {"audit": audit, "max_severity": max_severity(findings), "findings": findings_to_dicts(findings)}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"max_severity={payload['max_severity']} tracks={audit['track_count']} items={audit['item_count']}")
    return 2 if has_warn_plus(findings) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
