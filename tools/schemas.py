from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import uuid
import wave
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
AUDIO_EXTENSIONS = {".wav", ".aiff", ".aif", ".flac", ".mp3", ".m4a"}
REFERENCE_TRACK = "SOURCE full mix reference muted - not in master"
MALE_MAIN_TRACK = "08 MALE_NONHOOK_CENTER"
REF_BUS = "REF BUS"
VOX_BUS = "VOX BUS"
DRUM_BUS = "DRUM BUS"
BASS_BUS = "808/BASS BUS"
MUSIC_BUS = "MUSIC BUS"
MIX_BUS = "MIX BUS"
PREMASTER = "PREMASTER"
PRINT_MASTER = "PRINT MASTER"
DELIVERY_ZIP = ROOT / "delivery" / "codex_mix_master_delivery.zip"
PLUGIN_TRACE_PATH = ROOT / "work" / "traces" / "plugin_trace.json"
QC_JSON_PATH = ROOT / "work" / "qc" / "qc_report.json"
QC_MD_PATH = ROOT / "reports" / "QC_REPORT.md"
ASSET_MANIFEST_PATH = ROOT / "work" / "assets" / "asset_manifest.json"
ASSET_REPORT_PATH = ROOT / "reports" / "ASSET_REPORT.md"
PLUGIN_SUMMARY_PATH = ROOT / "reports" / "PLUGIN_TRACE_SUMMARY.md"
FINAL_REPORT_PATH = ROOT / "reports" / "FINAL_DELIVERY_REPORT.md"
VALIDATION_REPORT_PATH = ROOT / "work" / "traces" / "validation_gates.json"
PROJECT_PATH = ROOT / "work" / "reaper_project" / "codex_mix_master_project.rpp"
AUTO_CORRECT_LOG = ROOT / "work" / "logs" / "auto_correct_passes.jsonl"


TRACK_DEFS = [
    {"index": 0, "name": REFERENCE_TRACK, "kind": "reference", "muted": True, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 1, "name": REF_BUS, "kind": "bus", "muted": True, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 2, "name": "01 FX", "kind": "instrument", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 3, "name": "02 SYNTH", "kind": "instrument", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 4, "name": "03 KEYBOARD", "kind": "instrument", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 5, "name": "04 GUITAR", "kind": "instrument", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 6, "name": "05 BASS", "kind": "instrument", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 7, "name": "06 DRUMS", "kind": "instrument", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 8, "name": MALE_MAIN_TRACK, "kind": "vocal", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 9, "name": "09 MALE_HOOK_RESIDUAL_CENTER", "kind": "vocal", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": -3.0},
    {"index": 10, "name": "10 MALE_HOOK_LOWMID_SUPPORT", "kind": "vocal", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": -6.0},
    {"index": 11, "name": "11 FEMALE_L_SIDE", "kind": "vocal", "muted": False, "master_send_enabled": False, "pan": -0.75, "volume_db": -8.0},
    {"index": 12, "name": "12 FEMALE_R_SIDE", "kind": "vocal", "muted": False, "master_send_enabled": False, "pan": 0.75, "volume_db": -8.0, "delay_intent_ms": 6.0},
    {"index": 13, "name": "13 VOCAL_THROW_TUCKED", "kind": "vocal_fx_return", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": -12.0},
    {"index": 14, "name": VOX_BUS, "kind": "bus", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 15, "name": DRUM_BUS, "kind": "bus", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 16, "name": BASS_BUS, "kind": "bus", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 17, "name": MUSIC_BUS, "kind": "bus", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 18, "name": MIX_BUS, "kind": "bus", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 19, "name": PREMASTER, "kind": "bus", "muted": False, "master_send_enabled": False, "pan": 0.0, "volume_db": 0.0},
    {"index": 20, "name": PRINT_MASTER, "kind": "print_master", "muted": False, "master_send_enabled": True, "pan": 0.0, "volume_db": 0.0},
]

ROUTES = [
    (REFERENCE_TRACK, REF_BUS),
    ("01 FX", MUSIC_BUS),
    ("02 SYNTH", MUSIC_BUS),
    ("03 KEYBOARD", MUSIC_BUS),
    ("04 GUITAR", MUSIC_BUS),
    ("05 BASS", BASS_BUS),
    ("06 DRUMS", DRUM_BUS),
    (MALE_MAIN_TRACK, VOX_BUS),
    ("09 MALE_HOOK_RESIDUAL_CENTER", VOX_BUS),
    ("10 MALE_HOOK_LOWMID_SUPPORT", VOX_BUS),
    ("11 FEMALE_L_SIDE", VOX_BUS),
    ("12 FEMALE_R_SIDE", VOX_BUS),
    ("13 VOCAL_THROW_TUCKED", VOX_BUS),
    (VOX_BUS, MIX_BUS),
    (DRUM_BUS, MIX_BUS),
    (BASS_BUS, MIX_BUS),
    (MUSIC_BUS, MIX_BUS),
    (MIX_BUS, PREMASTER),
    (PREMASTER, PRINT_MASTER),
]

OPTIONAL_SIDECHAIN_ROUTES = [
    ("06 DRUMS", BASS_BUS, "3/4"),
    (MALE_MAIN_TRACK, MUSIC_BUS, "3/4"),
]

VOCAL_CHAIN = [
    "JS: Codex Vocal AI Artifact Split Tamer",
    "JS: Vocal Clarity De-Mud Dynamic EQ",
    "VST: ReaEQ (Cockos)",
    "VST3: TDR Nova (Tokyo Dawn Labs)",
    "JS: De-esser",
    "JS: Vocal Clarity Air Guard",
    "VST3: UADx LA-2A Tube Compressor",
    "VST3: UADx 1176 FET Compressor",
    "JS: Vocal Clarity Output Guard",
]

CHAIN_BY_TRACK = {
    "01 FX": ["VST: ReaEQ (Cockos)"],
    "02 SYNTH": ["VST3: TDR Nova (Tokyo Dawn Labs)"],
    "03 KEYBOARD": ["VST: ReaEQ (Cockos)"],
    "04 GUITAR": ["VST: ReaEQ (Cockos)"],
    "05 BASS": ["VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)", "VST3: FreeClip"],
    "06 DRUMS": ["VST: ReaEQ (Cockos)", "VST3: UADx 1176 FET Compressor", "VST3: FreeClip"],
    MALE_MAIN_TRACK: VOCAL_CHAIN,
    "09 MALE_HOOK_RESIDUAL_CENTER": VOCAL_CHAIN,
    "10 MALE_HOOK_LOWMID_SUPPORT": VOCAL_CHAIN,
    "11 FEMALE_L_SIDE": VOCAL_CHAIN,
    "12 FEMALE_R_SIDE": VOCAL_CHAIN,
    "13 VOCAL_THROW_TUCKED": ["VST: ReaEQ (Cockos)", "JS: De-esser"],
    REF_BUS: ["VST3: mvMeter2", "VST3: ClearMaster Audit"],
    VOX_BUS: ["VST3: TDR Nova (Tokyo Dawn Labs)", "VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "JS: Vocal Clarity Output Guard"],
    DRUM_BUS: ["VST: ReaEQ (Cockos)", "VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST3: FreeClip"],
    BASS_BUS: ["VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)", "VST3: FreeClip"],
    MUSIC_BUS: ["VST3: TDR Nova (Tokyo Dawn Labs)", "VST3: Ozone Imager 2"],
    MIX_BUS: ["VST3: Ozone 12 Equalizer", "VST3: TDR Kotelnikov (Tokyo Dawn Labs)"],
    PREMASTER: [
        "VST3: Ozone 12 Equalizer",
        "VST3: TDR Kotelnikov (Tokyo Dawn Labs)",
        "JS: Codex V20 Master Glue",
        "VST3: FreeClip",
        "VST: ReaLimit (Cockos)",
    ],
    PRINT_MASTER: ["VST3: mvMeter2", "VST3: ClearMaster Audit", "JS: Vocal Clarity Output Guard"],
}

QC_TARGETS = {
    "integrated_lufs": {"min": -12.5, "max": -8.0},
    "loud_reference_master_integrated_lufs": {"min": -9.5, "max": -8.0},
    "safe_streaming_master_integrated_lufs": {"min": -14.5, "max": -12.5},
    "true_peak_db_tp": {"max": -1.0},
    "sample_peak_dbfs": {"max": -1.0},
    "lr_rms_delta_db": {"max": 0.5},
    "stereo_correlation": {"min": 0.25},
    "mono_peak_dbfs": {"max": -1.0},
    "mono_loudness_delta_db": {"min": -1.0, "max": 1.0},
    "female_vs_male_delta_db": {"max": -5.0},
    "male_active_rms_dbfs": {"min": -24.0},
    "harshness_band_share": {"max": 0.26},
    "sibilance_band_share": {"max": 0.18},
    "master_bus_sustained_gain_reduction_db": {"max": 2.0},
}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_harness_dirs(root: Path = ROOT) -> None:
    for rel in [
        "configs",
        "input/stems",
        "input/reference",
        "work/assets",
        "work/reaper_project",
        "work/traces",
        "work/renders",
        "work/qc",
        "work/logs",
        "delivery",
        "reaper/scripts",
        "reaper/jsfx",
        "reports",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def db_to_linear(db: float) -> float:
    return 10 ** (db / 20.0)


def linear_to_db(value: float) -> Optional[float]:
    if value <= 0:
        return None
    return 20.0 * math.log10(value)


def classify_stem(filename: str) -> str:
    text = Path(filename).stem.lower()
    tokens = text.replace("-", "_").replace(" ", "_").split("_")
    joined = "_".join(tokens)

    def has(*words: str) -> bool:
        return any(word in joined for word in words)

    if has("female", "woman", "girl"):
        if has("_l", "left", "l_side", "side_l"):
            return "FEMALE_L_SIDE"
        if has("_r", "right", "r_side", "side_r"):
            return "FEMALE_R_SIDE"
        return "UNKNOWN"
    if has("throw") and has("vocal", "vox", "voice"):
        return "VOCAL_THROW_TUCKED"
    if has("male", "man", "lead", "main_vocal", "mainvox"):
        if has("lowmid", "low_mid", "body", "chest"):
            return "MALE_HOOK_LOWMID_SUPPORT"
        if has("residual", "rescue", "hook"):
            return "MALE_HOOK_RESIDUAL_CENTER"
        if has("vocal", "vox", "voice", "lead", "main"):
            return "MALE_NONHOOK_CENTER"
    if has("drum", "drums", "kick", "snare", "perc", "hat"):
        return "DRUMS"
    if has("bass", "808", "sub"):
        return "BASS"
    if has("guitar", "gtr"):
        return "GUITAR"
    if has("keyboard", "keys", "piano", "organ", "rhodes"):
        return "KEYBOARD"
    if has("synth", "pad", "lead_synth", "arp"):
        return "SYNTH"
    if has("fx", "sfx", "riser", "impact", "transition"):
        return "FX"
    return "UNKNOWN"


def discover_assets(root: Path = ROOT) -> Dict[str, Any]:
    ensure_harness_dirs(root)
    stems_root = root / "input" / "stems"
    reference_root = root / "input" / "reference"
    stem_assets: List[Dict[str, Any]] = []
    reference_assets: List[Dict[str, Any]] = []

    for base, bucket, asset_type in [
        (stems_root, stem_assets, "stem"),
        (reference_root, reference_assets, "reference"),
    ]:
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            suffix = path.suffix.lower()
            if suffix not in AUDIO_EXTENSIONS:
                continue
            role = "FULL_MIX_REFERENCE" if asset_type == "reference" else classify_stem(path.name)
            bucket.append(
                {
                    "path": str(path.relative_to(root)),
                    "absolute_path": str(path),
                    "filename": path.name,
                    "extension": suffix.lstrip("."),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "asset_type": asset_type,
                    "classification": role,
                    "classification_confidence": "conservative" if role != "UNKNOWN" else "unknown",
                }
            )

    unknown = [asset for asset in stem_assets if asset["classification"] == "UNKNOWN"]
    payload = {
        "timestamp": now_iso(),
        "root": str(root),
        "accepted_extensions": sorted(ext.lstrip(".") for ext in AUDIO_EXTENSIONS),
        "stems_root": "input/stems",
        "reference_root": "input/reference",
        "stem_count": len(stem_assets),
        "reference_count": len(reference_assets),
        "unknown_stem_count": len(unknown),
        "stems": stem_assets,
        "references": reference_assets,
        "unknown_stems": unknown,
    }
    payload["source_manifest_hash"] = sha256_payload({k: v for k, v in payload.items() if k != "source_manifest_hash"})
    return payload


def write_asset_report(manifest: Dict[str, Any], root: Path = ROOT) -> None:
    lines = [
        "# Asset Report",
        "",
        f"- Generated: {manifest['timestamp']}",
        f"- Stem count: {manifest['stem_count']}",
        f"- Reference count: {manifest['reference_count']}",
        f"- Unknown stem count: {manifest['unknown_stem_count']}",
        f"- Source manifest hash: `{manifest['source_manifest_hash']}`",
        "",
        "## Stems",
        "",
    ]
    if manifest["stems"]:
        for asset in manifest["stems"]:
            lines.append(f"- `{asset['path']}` -> `{asset['classification']}` ({asset['classification_confidence']})")
    else:
        lines.append("- No audio stems found under `input/stems/`.")
    lines.extend(["", "## References", ""])
    if manifest["references"]:
        for asset in manifest["references"]:
            lines.append(f"- `{asset['path']}` -> `{asset['classification']}`")
    else:
        lines.append("- No full mix reference audio found under `input/reference/`.")
    lines.extend(["", "## Notes", ""])
    if manifest["unknown_stems"]:
        lines.append("- Unknown stems require manual mapping before lead/support balance can be verified.")
    else:
        lines.append("- No uncertain stem classifications were found.")
    ASSET_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def detect_environment(root: Path = ROOT) -> Dict[str, Any]:
    reaper_candidates = [
        Path("/Applications/REAPER.app/Contents/MacOS/REAPER"),
        Path("/Applications/REAPER64.app/Contents/MacOS/REAPER"),
    ]
    for name in ("REAPER", "reaper"):
        found = shutil.which(name)
        if found:
            reaper_candidates.append(Path(found))
    reaper_path = next((str(path) for path in reaper_candidates if path.exists()), None)
    encoders = {
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "lame": shutil.which("lame"),
        "afconvert": shutil.which("afconvert"),
    }
    payload = {
        "timestamp": now_iso(),
        "os": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "reaper_executable_path": reaper_path,
        "reaper_available": reaper_path is not None,
        "reaper_version": None,
        "reaper_version_unavailable_reason": "version query is not run to avoid launching a GUI session",
        "encoders": encoders,
        "mp3_encoder_available": bool(encoders["ffmpeg"] or encoders["lame"]),
        "m4a_encoder_available": bool(encoders["ffmpeg"] or encoders["afconvert"]),
        "input_stems_dir_exists": (root / "input" / "stems").exists(),
        "input_reference_dir_exists": (root / "input" / "reference").exists(),
    }
    return payload


def _empty_fx(plugin_name: str, slot_index: int, runtime_verified: bool) -> Dict[str, Any]:
    is_repo_jsfx = plugin_name.startswith("JS: Codex") or plugin_name.startswith("JS: Vocal Clarity")
    is_cockos = "Cockos" in plugin_name or plugin_name.startswith("VST: Rea")
    return {
        "slot_index": slot_index,
        "requested_plugin_name": plugin_name,
        "resolved_plugin_name": plugin_name,
        "loaded": bool(runtime_verified),
        "offline": False if runtime_verified else None,
        "bypassed": False if runtime_verified else None,
        "wet_dry": 1.0 if runtime_verified else None,
        "parameters_written": [],
        "load_status": "runtime_verified" if runtime_verified else "planned_not_runtime_verified",
        "parameter_write_policy": (
            "repo_jsfx_write_allowed_when_installed"
            if is_repo_jsfx
            else "verified_cockos_mapping_required"
            if is_cockos
            else "insert_only_external_or_unverified_no_parameter_write"
        ),
    }


def _trace_rows_from_tracks(tracks: list[dict[str, Any]], runtime_verified: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fx_status = "loaded" if runtime_verified else "planned"
    for track in tracks:
        for fx in track.get("fx_chain", []):
            rows.append(
                {
                    "track": track.get("name"),
                    "stage": "planned fx insertion",
                    "status": fx_status,
                    "plugin": fx.get("resolved_plugin_name") or fx.get("requested_plugin_name"),
                    "fx_index": fx.get("slot_index"),
                    "wet": fx.get("wet_dry"),
                    "parameter_write_policy": fx.get("parameter_write_policy"),
                    "reason": fx.get("intent", "chain role defined by tools/schemas.py"),
                }
            )
        for send_index, send in enumerate(track.get("sends", [])):
            rows.append(
                {
                    "track": "routing",
                    "stage": "send",
                    "status": "planned" if not runtime_verified else "created",
                    "plugin": f"{track.get('name')} -> {send.get('target')}",
                    "fx_index": send_index,
                    "wet": None,
                    "parameter_write_policy": "no_parameter_write",
                    "reason": f"audio channels {send.get('channels', '1/2')}; optional={bool(send.get('optional'))}",
                }
            )
    return rows


def build_plugin_trace(
    manifest: Dict[str, Any],
    environment: Dict[str, Any],
    root: Path = ROOT,
    runtime_verified: bool = False,
) -> Dict[str, Any]:
    receive_map: Dict[str, List[Dict[str, Any]]] = {track["name"]: [] for track in TRACK_DEFS}
    send_map: Dict[str, List[Dict[str, Any]]] = {track["name"]: [] for track in TRACK_DEFS}
    for source, target in ROUTES:
        send = {"target": target, "channels": "1/2", "optional": False}
        send_map[source].append(send)
        receive_map[target].append({"source": source, "channels": "1/2", "optional": False})

    tracks = []
    for track_def in TRACK_DEFS:
        name = track_def["name"]
        chain = CHAIN_BY_TRACK.get(name, [])
        fx_chain = [_empty_fx(plugin, slot, runtime_verified) for slot, plugin in enumerate(chain)]
        if name == "12 FEMALE_R_SIDE":
            fx_chain.append(
                {
                    "slot_index": len(fx_chain),
                    "requested_plugin_name": "delay_or_filter_difference",
                    "resolved_plugin_name": None,
                    "loaded": False,
                    "offline": None,
                    "bypassed": None,
                    "wet_dry": None,
                    "parameters_written": [],
                    "load_status": "documented_fallback_needed",
                    "intent": "approximately 6 ms delay or alternate filter difference so L/R are not identical",
                }
            )
        tracks.append(
            {
                "index": track_def["index"],
                "name": name,
                "kind": track_def["kind"],
                "muted": track_def["muted"],
                "master_send_enabled": track_def["master_send_enabled"],
                "pan": track_def["pan"],
                "volume": db_to_linear(track_def["volume_db"]),
                "volume_db": track_def["volume_db"],
                "delay_intent_ms": track_def.get("delay_intent_ms"),
                "sends": send_map[name],
                "receives": receive_map[name],
                "fx_chain": fx_chain,
            }
        )

    payload = {
        "schema": "codex-reaper-plugin-trace-v2",
        "slug": "digicore_suno_ai_reaper_pipeline",
        "timestamp": now_iso(),
        "OS": environment.get("os"),
        "REAPER executable path": environment.get("reaper_executable_path"),
        "REAPER version": environment.get("reaper_version"),
        "project path": str(PROJECT_PATH),
        "source manifest hash": manifest.get("source_manifest_hash"),
        "runtime_verified": runtime_verified,
        "runtime_verification_note": "FX load states are planned unless this trace is collected from an actual REAPER run.",
        "source_full_mix_policy": "muted, master-send disabled, routed only to muted REF BUS by default",
        "required_main_track": MALE_MAIN_TRACK,
        "tracks": tracks,
        "optional_sidechain_sends": [
            {"source": source, "target": target, "channels": channels, "verified_ducking": False}
            for source, target, channels in OPTIONAL_SIDECHAIN_ROUTES
        ],
    }
    payload["rows"] = _trace_rows_from_tracks(tracks, runtime_verified)
    payload["gate_checks"] = compute_gate_checks(payload, root)
    return payload


def track_by_name(trace: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    return next((track for track in trace.get("tracks", []) if track.get("name") == name), None)


def compute_gate_checks(trace: Dict[str, Any], root: Path = ROOT) -> Dict[str, Any]:
    ref = track_by_name(trace, REFERENCE_TRACK)
    male = track_by_name(trace, MALE_MAIN_TRACK)
    ref_bus = track_by_name(trace, REF_BUS)
    track_names = {track.get("name") for track in trace.get("tracks", [])}
    route_pairs = {
        (track.get("name"), send.get("target"))
        for track in trace.get("tracks", [])
        for send in track.get("sends", [])
        if not send.get("optional")
    }
    reference_sends = ref.get("sends", []) if ref else []
    first_fx = None
    if male and male.get("fx_chain"):
        first_fx = male["fx_chain"][0].get("resolved_plugin_name") or male["fx_chain"][0].get("requested_plugin_name")
    reference_sends_safe = not reference_sends or all(send.get("target") == REF_BUS for send in reference_sends)
    ref_bus_inactive = bool(ref_bus and ref_bus.get("muted") is True and ref_bus.get("master_send_enabled") is False and not ref_bus.get("sends"))
    checks = {
        "full_mix_reference_exists": ref is not None,
        "full_mix_reference_muted": bool(ref and ref.get("muted") is True),
        "full_mix_reference_master_send_disabled": bool(ref and ref.get("master_send_enabled") is False),
        "raw_full_mix_not_active": bool(
            ref
            and ref.get("muted") is True
            and ref.get("master_send_enabled") is False
            and reference_sends_safe
            and (not reference_sends or ref_bus_inactive)
        ),
        "male_main_track_exists": male is not None,
        "male_main_first_fx_is_artifact_split_tamer": first_fx == "JS: Codex Vocal AI Artifact Split Tamer",
        "required_buses_exist": all(bus in track_names for bus in [REF_BUS, VOX_BUS, DRUM_BUS, BASS_BUS, MUSIC_BUS, MIX_BUS, PREMASTER, PRINT_MASTER]),
        "required_routing_exists": all(route in route_pairs for route in ROUTES),
        "render_files_exist": (root / "work" / "renders" / "final_24bit_48k.wav").exists()
        and (root / "work" / "renders" / "final_16bit_44k1.wav").exists(),
        "qc_files_exist": QC_JSON_PATH.exists() and QC_MD_PATH.exists(),
        "delivery_zip_exists": DELIVERY_ZIP.exists(),
    }
    checks["overall_pass"] = all(checks.values())
    return checks


def write_plugin_trace_summary(trace: Dict[str, Any]) -> None:
    gates = trace.get("gate_checks", {})
    missing_plugins = []
    for track in trace.get("tracks", []):
        for fx in track.get("fx_chain", []):
            if fx.get("loaded") is False and fx.get("load_status") != "runtime_verified":
                missing_plugins.append((track["name"], fx.get("requested_plugin_name"), fx.get("load_status")))
    lines = [
        "# Plugin Trace Summary",
        "",
        f"- Generated: {trace.get('timestamp')}",
        f"- Runtime verified: {trace.get('runtime_verified')}",
        f"- Project path: `{trace.get('project path')}`",
        f"- Source manifest hash: `{trace.get('source manifest hash')}`",
        "",
        "## Gate Checks",
        "",
    ]
    for name, value in gates.items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Missing Or Unverified Plugin Loads", ""])
    if missing_plugins:
        for track_name, plugin_name, status in missing_plugins:
            lines.append(f"- `{track_name}`: `{plugin_name}` -> {status}")
    else:
        lines.append("- No missing or unverified plugin loads were recorded.")
    PLUGIN_SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation_report(trace: Dict[str, Any], root: Path = ROOT) -> Dict[str, Any]:
    gates = compute_gate_checks(trace, root)
    payload = {
        "timestamp": now_iso(),
        "status": "PASS" if gates["overall_pass"] else "FAIL",
        "gate_checks": gates,
    }
    write_json(VALIDATION_REPORT_PATH, payload)
    return payload


def write_reaper_project_skeleton(root: Path = ROOT) -> Path:
    ensure_harness_dirs(root)
    lines = [
        '<REAPER_PROJECT 0.1 "7.0/macOS" 0',
        "  RIPPLE 0",
        "  GROUPOVERRIDE 0 0 0",
        "  AUTOXFADE 1",
        "  ENVATTACH 1",
        "  POOLEDENVATTACH 0",
        "  MIXERUIFLAGS 11 48",
        "  PEAKGAIN 1",
        "  FEEDBACK 0",
        "  PANLAW 1",
    ]
    for track in TRACK_DEFS:
        guid = "{" + str(uuid.uuid4()).upper() + "}"
        lines.extend(
            [
                f"  <TRACK {guid}",
                f'    NAME "{track["name"]}"',
                f'    VOLPAN {db_to_linear(track["volume_db"]):.8f} {track["pan"]:.8f} -1 -1 1',
                f'    MUTESOLO {1 if track["muted"] else 0} 0 0',
                "    IPHASE 0",
                "    PLAYOFFS 0 1",
                "    ISBUS 0 0",
                "    BUSCOMP 0 0 0 0 0",
                "    SHOWINMIX 1 0.6667 0.5 1 0.5 -1 -1 -1",
                "    FREEMODE 0",
                "    SEL 0",
                "    REC 0 0 1 0 0 0 0 0",
                "    VU 2",
                "    TRACKHEIGHT 0 0 0 0 0 0",
                "    INQ 0 0 0 0.5 100 0 0 100",
                "    NCHAN 2",
                "    FX 1",
                f"    TRACKID {guid}",
                "    PERF 0",
                "    MIDIOUT -1",
                f'    MAINSEND {1 if track["master_send_enabled"] else 0} 0',
                "  >",
            ]
        )
    lines.append(">")
    PROJECT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return PROJECT_PATH


def _metric(value: Optional[float], unit: str = "", status: str = "unavailable", reason: Optional[str] = None) -> Dict[str, Any]:
    return {"value": value, "unit": unit, "status": "available" if value is not None else status, "reason": reason}


def blocked_qc_report(audio_path: Path, reason: str) -> Dict[str, Any]:
    metrics = {
        "integrated_lufs": _metric(None, "LUFS", reason=reason),
        "true_peak_db_tp": _metric(None, "dBTP", reason="true peak is unavailable without decoded audio and oversampling"),
        "sample_peak_dbfs": _metric(None, "dBFS", reason=reason),
        "lr_rms_delta_db": _metric(None, "dB", reason=reason),
        "stereo_correlation": _metric(None, "", reason=reason),
        "mono_peak_dbfs": _metric(None, "dBFS", reason=reason),
        "mono_loudness_delta_db": _metric(None, "dB", reason=reason),
        "female_vs_male_level_delta_db": _metric(None, "dB", reason="requires comparable isolated male/female assets"),
        "harshness_band_result": _metric(None, "share", reason=reason),
        "sibilance_band_result": _metric(None, "share", reason=reason),
    }
    return {
        "timestamp": now_iso(),
        "status": "BLOCKED",
        "audio_path": str(audio_path),
        "metrics": metrics,
        "targets": QC_TARGETS,
        "summary": reason,
    }


def write_qc_markdown(report: Dict[str, Any]) -> None:
    metrics = report.get("metrics", {})
    lines = [
        "# QC Report",
        "",
        f"- Generated: {report.get('timestamp')}",
        f"- Status: {report.get('status')}",
        f"- Audio path: `{report.get('audio_path')}`",
        f"- Summary: {report.get('summary')}",
        "",
        "## Metrics",
        "",
    ]
    for name, metric in metrics.items():
        lines.append(f"- {name}: {metric.get('value')} {metric.get('unit', '')} ({metric.get('status')}; {metric.get('reason')})")
    QC_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def package_delivery(root: Path = ROOT) -> Dict[str, Any]:
    required = [
        root / "work" / "renders" / "final_24bit_48k.wav",
        root / "work" / "renders" / "final_16bit_44k1.wav",
        PLUGIN_TRACE_PATH,
        QC_JSON_PATH,
        QC_MD_PATH,
        PLUGIN_SUMMARY_PATH,
        ASSET_REPORT_PATH,
        FINAL_REPORT_PATH,
        root / "configs" / "mix_profile.yaml",
        root / "configs" / "plugin_allowlist.yaml",
        root / "configs" / "qc_targets.yaml",
        root / "configs" / "render_targets.yaml",
    ]
    preview_candidates = [root / "work" / "renders" / "preview.mp3", root / "work" / "renders" / "preview.m4a"]
    missing = [str(path) for path in required if not path.exists()]
    preview = next((path for path in preview_candidates if path.exists()), None)
    if preview is None:
        missing.append("work/renders/preview.mp3 or work/renders/preview.m4a")

    manifest = {
        "timestamp": now_iso(),
        "status": "BLOCKED" if missing else "PASS",
        "zip_path": str(DELIVERY_ZIP),
        "missing": missing,
        "included": [],
    }
    if missing:
        write_json(root / "delivery" / "package_manifest.json", manifest)
        return manifest

    DELIVERY_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DELIVERY_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required + [preview]:
            archive.write(path, path.relative_to(root))
            manifest["included"].append(str(path.relative_to(root)))
    write_json(root / "delivery" / "package_manifest.json", manifest)
    return manifest


def write_final_delivery_report(
    environment: Dict[str, Any],
    manifest: Dict[str, Any],
    trace: Optional[Dict[str, Any]],
    qc_report: Optional[Dict[str, Any]],
    package_manifest: Optional[Dict[str, Any]],
    root: Path = ROOT,
) -> None:
    gates = compute_gate_checks(trace, root) if trace else {}
    status = "PASS" if gates.get("overall_pass") else "BLOCKED"
    missing = []
    if manifest.get("stem_count", 0) == 0:
        missing.append("No stems found under input/stems/")
    if manifest.get("reference_count", 0) == 0:
        missing.append("No full mix reference found under input/reference/")
    if not environment.get("reaper_available"):
        missing.append("REAPER executable not found")
    if package_manifest and package_manifest.get("missing"):
        missing.extend(package_manifest["missing"])

    lines = [
        "# Final Delivery Report",
        "",
        f"- Generated: {now_iso()}",
        f"- Status: {status}",
        f"- REAPER executable: `{environment.get('reaper_executable_path')}`",
        f"- Project path: `{PROJECT_PATH}`",
        f"- Delivery ZIP: `{DELIVERY_ZIP}`",
        "",
        "## Gate Summary",
        "",
    ]
    for name, value in gates.items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Missing Or Unverified", ""])
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- None recorded.")
    lines.extend(["", "## QC Summary", ""])
    if qc_report:
        for name, metric in qc_report.get("metrics", {}).items():
            lines.append(f"- {name}: {metric.get('value')} {metric.get('unit', '')} ({metric.get('status')})")
    else:
        lines.append("- QC report was not generated.")
    FINAL_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cli_root(parser: argparse.ArgumentParser) -> Path:
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    args = parser.parse_args()
    return Path(args.root).resolve()
