from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

try:
    from .audio_qc import compare_before_after
    from .plugin_audit import audit_plugins
    from .reaper_project_audit import audit_project
    from .severity import (
        Finding,
        add_finding,
        findings_to_dicts,
        findings_to_markdown,
        has_warn_plus,
        max_severity,
        status_from_findings,
        warn_plus_findings,
    )
except ImportError:  # pragma: no cover - direct script execution.
    from audio_qc import compare_before_after
    from plugin_audit import audit_plugins
    from reaper_project_audit import audit_project
    from severity import (
        Finding,
        add_finding,
        findings_to_dicts,
        findings_to_markdown,
        has_warn_plus,
        max_severity,
        status_from_findings,
        warn_plus_findings,
    )


AUDIO_EXTS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".ogg"}
MIDI_EXTS = {".mid", ".midi"}
REPORT_EXTS = {".md", ".json", ".csv", ".txt"}
IGNORE_DIRS = {".git", "__pycache__", ".venv", ".venv_handoff", "build", "external_models"}
MODES = ("auto", "fullmix_rescue", "stem_rebuild", "true_rebeat", "master_only", "vocal_repair")
CANDIDATES = ("A_safe", "B_more_deai", "C_punch_preserve", "D_reference_match")

ROLE_TOKENS = {
    "drums": ("drum", "kick", "snare", "hat", "perc", "beat"),
    "bass": ("bass", "808", "sub"),
    "music": ("music", "synth", "key", "piano", "guitar", "melody", "instrumental", "inst"),
    "vocal": ("vocal", "vox", "lead", "voice", "adlib", "bgv"),
    "fx": ("fx", "sfx", "riser", "impact", "noise", "texture"),
    "fullmix": ("fullmix", "full_mix", "full mix", "2track", "two_track", "master", "original", "reference"),
}


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS or part.startswith(".venv") for part in path.parts)


def _iter_project_files(root: Path, suffixes: set[str]) -> list[Path]:
    results: list[Path] = []
    for path in root.rglob("*"):
        if _is_ignored(path):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            results.append(path)
    return sorted(results)


def _resolve_optional_path(value: str | None, root: Path) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def _classify_audio_role(path: Path) -> str:
    lowered = " ".join([path.stem.lower(), path.parent.name.lower()])
    for role, tokens in ROLE_TOKENS.items():
        if any(token in lowered for token in tokens):
            return role
    return "other_audio"


def _scan_project(root: Path, source: Path | None, findings: list[Finding]) -> dict[str, Any]:
    if not root.exists():
        add_finding(
            "BLOCKER",
            "PROJECT_ROOT_MISSING",
            "Project root does not exist.",
            str(root),
            "Correct --project-root and rerun the pipeline harness.",
            findings,
            affected_file=str(root),
            failed_assumption="Project folder can be located.",
            command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {root} --mode auto --strict",
        )
        return {"project_root": str(root), "audio_files": [], "rpp_files": [], "midi_files": []}

    source_midi: list[Path] = []
    if source and source.exists():
        if source.is_file():
            source_audio = [source] if source.suffix.lower() in AUDIO_EXTS else []
            source_midi = [source] if source.suffix.lower() in MIDI_EXTS else []
        else:
            source_audio = _iter_project_files(source, AUDIO_EXTS)
            source_midi = _iter_project_files(source, MIDI_EXTS)
    elif source:
        source_audio = []
        add_finding(
            "BLOCKER",
            "SOURCE_PATH_MISSING",
            "Requested source path does not exist.",
            str(source),
            "Correct --source or place the source audio/stems in the project.",
            findings,
            affected_file=str(source),
            failed_assumption="Source audio path can be resolved.",
            command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {root} --source {source} --mode auto --strict",
        )
    else:
        likely_roots = [root / "SUNO_STUDIO_EXPORTS", root / "audio", root / "audio_work", root / "input_stems"]
        existing_roots = [path for path in likely_roots if path.exists()]
        source_audio = []
        for scan_root in existing_roots:
            source_audio.extend(_iter_project_files(scan_root, AUDIO_EXTS))
        if not source_audio:
            source_audio = _iter_project_files(root, AUDIO_EXTS)

    rpp_files = _iter_project_files(root, {".rpp"})
    midi_files = _iter_project_files(root, MIDI_EXTS)
    report_files = _iter_project_files(root, REPORT_EXTS)
    preset_files = _iter_project_files(root / "presets", {".json"}) if (root / "presets").exists() else []
    jsfx_files = _iter_project_files(root, {".jsfx"})
    fxchain_files = _iter_project_files(root, {".rfxchain"})
    roles: dict[str, list[str]] = {role: [] for role in [*ROLE_TOKENS, "other_audio"]}
    for audio in source_audio:
        roles.setdefault(_classify_audio_role(audio), []).append(str(audio))

    if not source_audio:
        add_finding(
            "BLOCKER",
            "NO_SOURCE_AUDIO_DISCOVERED",
            "No source audio was discovered.",
            f"source={source or 'auto scan'}",
            "Place user-owned source audio/stems under --source or input_stems/<song>, then rerun.",
            findings,
            affected_file=str(source or root),
            failed_assumption="The pipeline has lawful source audio to inspect.",
            command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {root} --source SOURCE --mode auto --strict",
        )
    else:
        add_finding(
            "PASS",
            "SOURCE_AUDIO_DISCOVERED",
            "Source audio files were discovered.",
            f"audio_file_count={len(source_audio)}",
            "Keep the source manifest attached to the session report.",
            findings,
            affected_file=str(source or root),
        )

    return {
        "project_root": str(root),
        "source": str(source) if source else None,
        "source_explicit": bool(source),
        "audio_files": [str(path) for path in source_audio],
        "audio_roles": roles,
        "source_midi_files": [str(path) for path in source_midi],
        "midi_files": [str(path) for path in midi_files],
        "rpp_files": [str(path) for path in rpp_files],
        "report_files": [str(path) for path in report_files],
        "preset_files": [str(path) for path in preset_files],
        "jsfx_files": [str(path) for path in jsfx_files],
        "fxchain_files": [str(path) for path in fxchain_files],
    }


def _classify_capability(scan: dict[str, Any], requested_mode: str, project_audits: list[dict[str, Any]], findings: list[Finding]) -> dict[str, Any]:
    roles = scan.get("audio_roles", {})
    role_counts = {role: len(paths) for role, paths in roles.items()}
    stem_roles = {role for role in ("drums", "bass", "music", "vocal", "fx") if role_counts.get(role, 0) > 0}
    project_midi_count = sum(int(audit.get("midi_item_count", 0)) for audit in project_audits)
    project_stem_roles = set()
    for audit in project_audits:
        project_stem_roles.update(audit.get("stem_track_roles", []))
    source_explicit = bool(scan.get("source_explicit"))
    source_midi_files = scan.get("source_midi_files", [])
    has_midi = project_midi_count > 0 or (source_explicit and bool(source_midi_files))
    has_fullmix = role_counts.get("fullmix", 0) > 0
    has_vocal = role_counts.get("vocal", 0) > 0
    has_rebuild_stems = len(stem_roles.intersection({"drums", "bass", "music", "vocal"})) >= 2
    source_rebeat_evidence = source_explicit and bool(source_midi_files) and {"drums", "bass", "music"}.issubset(stem_roles)
    project_rebeat_evidence = project_midi_count > 0 and {"drums", "bass", "music"}.issubset(project_stem_roles)
    true_rebeat_possible = has_midi and (source_rebeat_evidence or project_rebeat_evidence)

    if requested_mode != "auto":
        classification = requested_mode
    elif true_rebeat_possible:
        classification = "true_rebeat"
    elif has_rebuild_stems:
        classification = "stem_rebuild"
    elif has_vocal and not has_fullmix:
        classification = "vocal_repair"
    elif has_fullmix:
        classification = "fullmix_rescue"
    else:
        classification = "master_only"

    possible = {
        "fullmix_rescue": has_fullmix or bool(scan.get("audio_files")),
        "stem_rebuild": has_rebuild_stems,
        "true_rebeat": true_rebeat_possible,
        "vocal_repair": has_vocal,
        "master_only": bool(scan.get("audio_files")),
    }

    if classification == "true_rebeat" and not true_rebeat_possible:
        add_finding(
            "FAIL",
            "TRUE_REBEAT_NOT_ALLOWED",
            "The requested/selected classification is true_rebeat, but MIDI and reconstructed role evidence are missing.",
            f"midi={has_midi}, stem_roles={sorted(stem_roles)}, project_stem_roles={sorted(project_stem_roles)}",
            "Downgrade to fullmix_rescue/stem_rebuild or add actual drum/bass/music MIDI/audio items and rerun.",
            findings,
            affected_file=scan.get("project_root", ""),
            failed_assumption="Beat was recreated rather than rescued from existing audio.",
            command_to_rerun="python3 harness/run_music_pipeline.py --project-root PROJECT --source SOURCE --mode true_rebeat --strict",
            human_listening_required=True,
        )
    if classification == "stem_rebuild" and not has_rebuild_stems:
        add_finding(
            "WARN",
            "STEM_REBUILD_EVIDENCE_WEAK",
            "Stem rebuild was requested but not enough active stem roles were discovered.",
            f"stem_roles={sorted(stem_roles)}",
            "Downgrade the claim or place real stems under --source before building the REAPER session.",
            findings,
            affected_file=scan.get("source") or scan.get("project_root", ""),
            failed_assumption="Stems are available and active in the rebuild.",
            command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {scan.get('project_root', 'PROJECT')} --source {scan.get('source') or 'SOURCE'} --mode stem_rebuild --strict",
        )
    if classification in {"stem_rebuild", "true_rebeat"} and has_fullmix:
        add_finding(
            "WARN",
            "FULLMIX_PRESENT_IN_REBUILD_MODE",
            "A fullmix/reference file is present while the selected mode is rebuild-style.",
            f"fullmix_count={role_counts.get('fullmix', 0)}",
            "Keep fullmix muted/reference-only and verify project routing before using rebuild language.",
            findings,
            affected_file=scan.get("source") or scan.get("project_root", ""),
            failed_assumption="Rebuild result is not primarily the stereo fullmix.",
            command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {scan.get('project_root', 'PROJECT')} --source {scan.get('source') or 'SOURCE'} --mode {classification} --strict",
            human_listening_required=True,
        )

    return {
        "requested_mode": requested_mode,
        "selected_classification": classification,
        "role_counts": role_counts,
        "possible": possible,
        "true_rebeat_possible": true_rebeat_possible,
        "has_midi_evidence": has_midi,
        "stem_roles": sorted(stem_roles),
        "project_stem_roles": sorted(project_stem_roles),
    }


def _candidate_plan(root: Path, classification: str) -> dict[str, Any]:
    render_root = root / "renders" / "music_pipeline_candidates"
    report_root = root / "reports" / "music_pipeline_candidates"
    candidates = []
    for name in CANDIDATES:
        candidates.append(
            {
                "candidate_id": name,
                "render_wav": str(render_root / f"{name}.wav"),
                "report_json": str(report_root / f"{name}.json"),
                "classification": classification,
                "must_not_overwrite": True,
            }
        )
    return {
        "render_root": str(render_root),
        "report_root": str(report_root),
        "candidates": candidates,
    }


def _check_reaper(root: Path, reaper_path: str | None, strict: bool, findings: list[Finding]) -> dict[str, Any]:
    if reaper_path:
        resolved = Path(reaper_path).expanduser()
        exists = resolved.exists()
        if not exists:
            add_finding(
                "BLOCKER",
                "REAPER_EXECUTABLE_MISSING",
                "Provided REAPER executable path does not exist.",
                str(resolved),
                "Correct --reaper-path or install REAPER before project creation/render.",
                findings,
                affected_file=str(resolved),
                failed_assumption="REAPER executable is available.",
            )
        else:
            add_finding(
                "PASS",
                "REAPER_EXECUTABLE_FOUND",
                "REAPER executable path exists.",
                str(resolved),
                "Use this path for renderproject commands.",
                findings,
                affected_file=str(resolved),
            )
        return {"requested_path": str(resolved), "exists": exists}

    discovered = shutil.which("REAPER") or shutil.which("reaper")
    if discovered:
        add_finding(
            "PASS",
            "REAPER_EXECUTABLE_FOUND",
            "REAPER executable was found on PATH.",
            discovered,
            "Use this executable for renderproject commands.",
            findings,
            affected_file=discovered,
        )
        return {"requested_path": None, "path": discovered, "exists": True}

    add_finding(
        "BLOCKER" if strict else "WARN",
        "REAPER_EXECUTABLE_NOT_VERIFIED",
        "REAPER executable was not provided or found on PATH.",
        "--reaper-path was not set and PATH lookup failed.",
        "Provide --reaper-path before claiming project creation, rendering, or mastering completion.",
        findings,
        affected_file=str(root),
        failed_assumption="REAPER can run the Lua scripts and render candidates.",
        command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {root} --source SOURCE --reaper-path /path/to/REAPER --strict",
    )
    return {"requested_path": None, "path": None, "exists": False}


def _write_reports(root: Path, payload: dict[str, Any], findings: list[Finding]) -> tuple[Path, Path]:
    report_dir = root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "music_pipeline_report.json"
    md_path = report_dir / "music_pipeline_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown_report(payload, findings), encoding="utf-8")
    if has_warn_plus(findings):
        warn_prompt = report_dir / "WARN_PLUS_PROMPT.md"
        warn_prompt.write_text(_render_warn_plus_prompt(payload, findings), encoding="utf-8")
    return json_path, md_path


def _render_markdown_report(payload: dict[str, Any], findings: list[Finding]) -> str:
    classification = payload["classification"]["selected_classification"]
    status = payload["status"]
    lines = [
        "# Music Pipeline Harness Report",
        "",
        f"- Status: **{status}**",
        f"- Selected classification: **{classification}**",
        f"- Max severity: **{payload['max_severity']}**",
        f"- Claim status: **{payload['claim_status']}**",
        "",
        "## What Was Actually Done",
        "",
        "- Scanned project/source folders for audio, MIDI, reports, presets, JSFX, FXChains, and REAPER projects.",
        "- Audited available REAPER project text where present.",
        "- Audited plugin map, JSFX files, and custom DeAI references.",
        "- Wrote a candidate render plan. No candidate is called final by this harness.",
    ]
    if payload.get("audio_qc"):
        lines.append("- Ran before/after audio QC.")
    else:
        lines.append("- Did not run before/after audio QC because --before and --after were not both provided.")
    lines.extend(
        [
            "",
            "## WARN+ Findings",
            "",
            findings_to_markdown(warn_plus_findings(findings)),
            "",
            "## Commands",
            "",
            "```sh",
            *payload["commands"],
            "```",
            "",
            "## Candidate Plan",
            "",
            "```json",
            json.dumps(payload["candidate_plan"], indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_warn_plus_prompt(payload: dict[str, Any], findings: list[Finding]) -> str:
    rows = findings_to_markdown(warn_plus_findings(findings))
    return "\n".join(
        [
            "# WARN+ Prompt For Next Patch",
            "",
            "The music pipeline has WARN, FAIL, or BLOCKER findings. Do not claim final success, rebeat, stem rebuild, vocal tuning, mastered, or noise removed until these are cleared.",
            "",
            rows,
            "",
            "Required next behavior:",
            "",
            "1. Fix the highest severity finding first.",
            "2. Rerun the exact command listed for that finding.",
            "3. Keep human listening required when the finding says so.",
            "4. Only upgrade the claim after JSON and Markdown reports show no WARN+ findings.",
            "",
            "Current claim status:",
            "",
            f"- {payload['claim_status']}",
            "",
        ]
    )


def _build_commands(root: Path, source: Path | None, before: Path | None, after: Path | None, reaper_path: str | None) -> list[str]:
    source_arg = f" --source {source}" if source else ""
    commands = [
        "python3 -m unittest tests.test_harness_smoke",
        f"python3 harness/run_music_pipeline.py --project-root {root}{source_arg} --mode auto --strict",
    ]
    if before and after:
        commands.append(f"python3 -m harness.audio_qc --before {before} --after {after} --json")
    else:
        commands.append("python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json")
    reaper = reaper_path or "/path/to/REAPER"
    commands.extend(
        [
            f'"{reaper}" -newinst -nosplash -renderproject {root / "reaper" / "music_pipeline_candidates" / "A_safe_RENDER.rpp"}',
            f"python3 -m harness.reaper_project_audit --project {root / 'reaper' / 'music_pipeline_candidates' / 'A_safe_RENDER.rpp'} --enforce-contract --json",
            f"python3 harness/run_music_pipeline.py --project-root {root}{source_arg} --before BEFORE.wav --after AFTER.wav --mode auto --reaper-path {reaper} --strict",
        ]
    )
    return commands


def run_pipeline(args: argparse.Namespace) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    root = Path(args.project_root).expanduser().resolve()
    source = _resolve_optional_path(args.source, root)
    before = _resolve_optional_path(args.before, root)
    after = _resolve_optional_path(args.after, root)
    reference = _resolve_optional_path(args.reference, root)

    scan = _scan_project(root, source, findings)
    project_audits = []
    project_files = [Path(path) for path in scan.get("rpp_files", [])]
    audit_limit = 5
    for project_path in project_files[:audit_limit]:
        try:
            audit = audit_project(
                project_path,
                findings,
                mode=args.mode if args.mode != "auto" else "auto",
                enforce_contract=bool(args.strict and len(project_files) == 1),
            )
            project_audits.append(audit)
        except Exception as exc:
            add_finding(
                "FAIL",
                "RPP_AUDIT_EXCEPTION",
                "REAPER project audit failed.",
                f"{project_path}: {exc}",
                "Open/resave the project or remove it from the selected source path, then rerun.",
                findings,
                affected_file=str(project_path),
                failed_assumption="Project file can be inspected as text.",
            )
    if len(project_files) > audit_limit:
        add_finding(
            "INFO",
            "RPP_AUDIT_LIMITED",
            "Only the first REAPER projects were deeply audited to keep the harness bounded.",
            f"audited={audit_limit}, total={len(project_files)}",
            "Pass a narrower --source/project folder for the specific session before final claims.",
            findings,
            affected_file=str(root),
        )

    classification = _classify_capability(scan, args.mode, project_audits, findings)
    plugin_audit = audit_plugins(root, findings, mode=classification["selected_classification"], project_files=project_files[:audit_limit])
    reaper = _check_reaper(root, args.reaper_path, args.strict, findings)
    candidate_plan = _candidate_plan(root, classification["selected_classification"])

    audio_qc = None
    if before and after:
        audio_qc = compare_before_after(before, after, findings)
    elif before or after:
        add_finding(
            "FAIL",
            "BEFORE_AFTER_PAIR_INCOMPLETE",
            "Only one side of the before/after QC pair was provided.",
            f"before={before}, after={after}",
            "Provide both --before and --after, then rerun QC.",
            findings,
            affected_file=str(before or after),
            failed_assumption="Before/after files can be distinguished.",
        )
    else:
        add_finding(
            "WARN",
            "BEFORE_AFTER_QC_NOT_RUN",
            "Before/after QC was not run.",
            "--before and --after were not both provided.",
            "Run before/after QC before claiming mastered, noise removed, tuned, or final.",
            findings,
            affected_file=str(root),
            failed_assumption="Objective before/after evidence exists.",
            command_to_rerun=f"python3 harness/run_music_pipeline.py --project-root {root} --source {source or 'SOURCE'} --before BEFORE.wav --after AFTER.wav --mode {args.mode} --strict",
            human_listening_required=True,
        )

    if reference and not reference.exists():
        add_finding(
            "WARN",
            "REFERENCE_PATH_MISSING",
            "Reference path was provided but does not exist.",
            str(reference),
            "Correct --reference or remove reference-matching language.",
            findings,
            affected_file=str(reference),
            failed_assumption="Reference matching uses actual reference audio.",
        )
    elif not reference:
        add_finding(
            "INFO",
            "NO_REFERENCE_PROVIDED",
            "No reference audio was provided.",
            "Reference matching remains advisory/unavailable.",
            "Do not claim reference matched.",
            findings,
            affected_file=str(root),
        )

    max_found = max_severity(findings)
    payload = {
        "status": status_from_findings(findings),
        "max_severity": max_found,
        "claim_status": "not_final_warn_plus" if has_warn_plus(findings) else "eligible_no_warn_plus",
        "project_root": str(root),
        "scan": scan,
        "classification": classification,
        "project_audits": project_audits,
        "plugin_audit": plugin_audit,
        "reaper": reaper,
        "reference": str(reference) if reference else None,
        "audio_qc": audio_qc,
        "candidate_plan": candidate_plan,
        "findings": findings_to_dicts(findings),
        "commands": _build_commands(root, source, before, after, args.reaper_path),
    }
    json_path, md_path = _write_reports(root, payload, findings)
    payload["report_json"] = str(json_path)
    payload["report_markdown"] = str(md_path)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Claim-gated REAPER music pipeline harness.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--source")
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--reference")
    parser.add_argument("--mode", choices=MODES, default="auto")
    parser.add_argument("--reaper-path")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload, findings = run_pipeline(args)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload['status']} max_severity={payload['max_severity']} report={payload['report_markdown']}")
    return 2 if args.strict and has_warn_plus(findings) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
