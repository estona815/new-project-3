from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from creative_brief import (
    build_creative_brief as build_creative_brief_payload,
    normalize_drum_808_direction,
    normalize_export_format,
    normalize_length_mode,
    normalize_master_direction,
    normalize_mode,
    normalize_vocal_direction,
    write_creative_brief_files as persist_creative_brief_files,
)
from paths import PROJECT_ROOT
from release_intent_resolver import build_release_intent


SUPPORTED_INPUT_EXTENSIONS = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a"}
SUPPORTED_MODES = {"instrumental_beat", "vocal_plus_beat", "full_song_stereo", "stems"}
SUPPORTED_VOCAL_STYLES = {"natural", "polished", "hyperpop", "digicore", "rap_forward", "airy_pop", "intimate", "aggressive"}
SUPPORTED_MIX_INTENSITIES = {"conservative", "standard", "bold"}
SUPPORTED_MASTER_LOUDNESS = {"streaming_safe", "loud_demo", "master_ready_headroom", "release_master"}
SUPPORTED_AUTOTUNE = {"none", "subtle", "medium", "hard_effect"}
SUPPORTED_DEESS = {"light", "medium", "strong"}
SUPPORTED_REVERB_SPACES = {"dry", "small_room", "plate", "wide_hall", "washed"}
SUPPORTED_DELAY_STYLES = {"none", "slap", "quarter", "eighth", "pingpong", "throw_only"}
SUPPORTED_WORKFLOWS = {
    "bad_ai_song_rescue",
    "song_to_mix_master",
    "song_to_release",
    "sample_to_arrangement",
    "sample_to_release",
    "vocal_to_code",
    "vocal_to_release",
    "stems_to_production",
    "stems_to_release",
    "plan_only",
}
SUPPORTED_RESCUE_MODES = {"plan", "demo", "final"}
SUPPORTED_TARGET_LENGTHS = {"reels_15sec", "short_30sec", "under_2min", "full_song"}
SUPPORTED_RESCUE_STYLE_CLUSTERS = {"commercial_digicore_hyperpop", "system_seoul_adjacent", "custom"}
SUPPORTED_TARGET_DELIVERABLES = {"demo", "final_master", "release_package"}
SUPPORTED_RELEASE_PROFILES = {"commercial_digicore", "hip_hop", "hyperpop", "internet_underground", "system_seoul_adjacent", "custom"}


@dataclass(frozen=True)
class UserOptions:
    input_path: str | None
    length_mode: str
    vocal_mode: str
    melody_focus: str
    drum_808: str
    export_format: str
    save_logic_project: bool
    mode: str
    vocal_file: str | None = None
    beat_file: str | None = None
    lead_vocal_file: str | None = None
    adlib_file: str | None = None
    backing_vocal_file: str | None = None
    stems_folder: str | None = None
    reference_audio: str | None = None
    sample_folder: str | None = None
    reference_text: str | None = None
    vocal_style: str = "polished"
    mix_intensity: str = "standard"
    master_loudness: str = "master_ready_headroom"
    autotune: str = "subtle"
    deess: str = "medium"
    reverb_space: str = "plate"
    delay_style: str = "throw_only"
    creative_target: str = ""
    creative_target_text: str = ""
    raw_full_korean_request: str = ""
    vocal_fx_text: str = ""
    drum_bass_request_text: str = ""
    style_cluster_text: str = ""
    owned_reference_sample: bool = False
    owned_reference_stems: bool = False
    owned_samples: bool = False
    owned_stems: bool = False
    owned_vocals: bool = False
    release_metadata: dict[str, Any] = field(default_factory=dict)
    release_rights: dict[str, Any] = field(default_factory=dict)
    priority: str = ""
    avoid_list: str = ""
    vocal_direction: str = ""
    drum_808_direction: str = ""
    master_direction: str = ""
    length_start: str | None = None
    length_end: str | None = None
    arrangement_autopilot: bool = False
    arrangement_sample_file: str | None = None
    arrangement_vocal_file: str | None = None
    arrangement_genre: str = "digicore"
    workflow: str | None = None
    rough_request: str = ""
    rescue_mode: str = "plan"
    generate_lead: bool = True
    demote_vocal_texture: bool = True
    target_length: str = "under_2min"
    style_cluster: str = "custom"
    release_ready: bool = False
    zero_clarification: bool = False
    target_deliverable: str = "demo"
    release_profile: str = "custom"
    release_intent: dict[str, Any] | None = None
    creative_brief: dict[str, Any] | None = None
    input_exists: bool = False
    validation_warnings: tuple[str, ...] = field(default_factory=tuple)


def parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "save"}:
        return True
    if normalized in {"0", "false", "no", "n", "skip"}:
        return False
    raise ValueError(f"Expected a boolean value, got: {value}")


def ask_text(prompt: str, default: Any) -> str:
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or str(default)


def ask_bool(prompt: str, default: bool) -> bool:
    default_text = "true" if default else "false"
    answer = input(f"{prompt} [{default_text}]: ").strip()
    return parse_bool(answer or default_text, default)


def ask_optional(prompt: str, default: str = "") -> str:
    default_suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{default_suffix}: ").strip()
    return answer or default


def validate_input_path(input_path: str | None) -> tuple[bool, tuple[str, ...]]:
    if not input_path:
        return False, ("No input file path provided. Audio ingest will be handled in a later branch.",)

    path = Path(input_path).expanduser()
    warnings: list[str] = []
    if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        warnings.append("Input path should point to an MP3, WAV, AIFF, FLAC, or M4A file.")
    if not path.exists():
        warnings.append("Input path does not exist; conversion will fail until a real file is provided.")

    return path.exists(), tuple(warnings)


def value_or_default(value: str | None, default: str) -> str:
    return value or default


def validate_choice(name: str, value: str, supported: set[str], warnings: list[str]) -> str:
    if value in supported:
        return value
    warnings.append(f"{name} '{value}' is unsupported; using a conservative default.")
    return sorted(supported)[0]


def normalize_rescue_style_cluster(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "commercial_digicore": "commercial_digicore_hyperpop",
        "digicore_hyperpop": "commercial_digicore_hyperpop",
        "system_seoul": "system_seoul_adjacent",
    }
    selected = aliases.get(normalized, normalized)
    return selected if selected in SUPPORTED_RESCUE_STYLE_CLUSTERS else "custom"


def normalize_rescue_target_length(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "15sec_reels": "reels_15sec",
        "15_sec_reels": "reels_15sec",
        "reels": "reels_15sec",
        "30sec_short_form": "short_30sec",
        "30_sec_short_form": "short_30sec",
        "short": "short_30sec",
        "keep_original": "full_song",
        "under_2_minutes": "under_2min",
    }
    selected = aliases.get(normalized, normalized)
    return selected if selected in SUPPORTED_TARGET_LENGTHS else "under_2min"


def any_release_metadata_provided(metadata: dict[str, Any]) -> bool:
    for value in metadata.values():
        if isinstance(value, list):
            if value:
                return True
        elif value not in {None, ""}:
            return True
    return False


def inferred_mode(args: Any, defaults: dict[str, Any]) -> str:
    workflow = getattr(args, "workflow", None)
    if workflow in {"song_to_mix_master", "song_to_release"}:
        return "full_song_stereo"
    if workflow == "bad_ai_song_rescue":
        return "full_song_stereo"
    if workflow in {"vocal_to_code", "vocal_to_release"}:
        return "vocal_plus_beat"
    if workflow in {"stems_to_production", "stems_to_release"}:
        return "stems"
    if getattr(args, "mode", None):
        return args.mode
    if getattr(args, "vocal_file", None) or getattr(args, "lead_vocal_file", None):
        return "vocal_plus_beat"
    return defaults.get("mode", "instrumental_beat")


def primary_input_for_mode(args: Any, mode: str) -> str | None:
    if getattr(args, "input", None):
        return args.input
    if getattr(args, "workflow", None) in {"vocal_to_code", "vocal_to_release"} and getattr(args, "vocal_file", None):
        return args.vocal_file
    if mode in {"vocal_plus_beat", "stems"} and getattr(args, "beat_file", None):
        return args.beat_file
    if mode == "full_song_stereo" and getattr(args, "reference_audio", None):
        return args.reference_audio
    return None


def options_from_args(args: Any, defaults: dict[str, Any]) -> UserOptions:
    save_logic_project = parse_bool(getattr(args, "save_logic_project", None), bool(defaults["save_logic_project"]))
    mode = inferred_mode(args, defaults)
    primary_input = primary_input_for_mode(args, mode)
    input_exists, warnings_tuple = validate_input_path(primary_input)
    warnings = list(warnings_tuple)
    mode = validate_choice("mode", mode, SUPPORTED_MODES, warnings)
    vocal_style = validate_choice("vocal_style", value_or_default(getattr(args, "vocal_style", None), defaults["vocal_style"]), SUPPORTED_VOCAL_STYLES, warnings)
    mix_intensity = validate_choice("mix_intensity", value_or_default(getattr(args, "mix_intensity", None), defaults["mix_intensity"]), SUPPORTED_MIX_INTENSITIES, warnings)
    master_loudness = validate_choice("master_loudness", value_or_default(getattr(args, "master_loudness", None), defaults["master_loudness"]), SUPPORTED_MASTER_LOUDNESS, warnings)
    autotune = validate_choice("autotune", value_or_default(getattr(args, "autotune", None), defaults["autotune"]), SUPPORTED_AUTOTUNE, warnings)
    deess = validate_choice("deess", value_or_default(getattr(args, "deess", None), defaults["deess"]), SUPPORTED_DEESS, warnings)
    reverb_space = validate_choice("reverb_space", value_or_default(getattr(args, "reverb_space", None), defaults["reverb_space"]), SUPPORTED_REVERB_SPACES, warnings)
    delay_style = validate_choice("delay_style", value_or_default(getattr(args, "delay_style", None), defaults["delay_style"]), SUPPORTED_DELAY_STYLES, warnings)
    creative_target = getattr(args, "creative_target", None) or ""
    creative_target_text = getattr(args, "creative_target_text", None) or ""
    rough_request = getattr(args, "rough_request", None) or ""
    vocal_fx_text = getattr(args, "vocal_fx_text", None) or ""
    drum_bass_request_text = getattr(args, "drum_bass_request_text", None) or ""
    style_cluster_text = getattr(args, "style_cluster_text", None) or ""
    reference_text = getattr(args, "reference_text", None) or ""
    raw_full_korean_request = " ".join(
        item
        for item in (
            rough_request,
            creative_target_text,
            creative_target,
            reference_text,
            vocal_fx_text,
            drum_bass_request_text,
            style_cluster_text,
        )
        if item
    )
    creative_target_for_brief = rough_request or creative_target_text or creative_target or reference_text or raw_full_korean_request
    owned_samples = parse_bool(getattr(args, "owned_samples", None), False)
    owned_stems = parse_bool(getattr(args, "owned_stems", None), False)
    owned_vocals = parse_bool(getattr(args, "owned_vocals", None), False)
    owned_reference_sample = parse_bool(getattr(args, "owned_reference_sample", None), owned_samples)
    owned_reference_stems = parse_bool(getattr(args, "owned_reference_stems", None), owned_stems)
    metadata_explicit = (
        None
        if getattr(args, "metadata_explicit", None) is None
        else parse_bool(getattr(args, "metadata_explicit", None), False)
    )
    release_metadata = {
        "title": getattr(args, "metadata_title", None) or "",
        "artist": getattr(args, "metadata_artist", None) or "",
        "version": getattr(args, "metadata_version", None) or "",
        "genre": getattr(args, "metadata_genre", None) or "",
        "language": getattr(args, "metadata_language", None) or "",
        "explicit": metadata_explicit,
        "isrc": getattr(args, "metadata_isrc", None) or "",
        "upc": getattr(args, "metadata_upc", None) or "",
        "copyright_year": getattr(args, "metadata_copyright_year", None) or "",
        "copyright_owner": getattr(args, "metadata_copyright_owner", None) or "",
        "producer": getattr(args, "metadata_producer", None) or "",
        "composer": getattr(args, "metadata_composer", None) or "",
        "lyricist": getattr(args, "metadata_lyricist", None) or "",
        "featured_artists": [],
    }
    release_rights = {
        "contains_samples": bool(getattr(args, "workflow", None) in {"sample_to_arrangement", "sample_to_release"} or getattr(args, "arrangement_sample_file", None)),
        "all_samples_owned_or_cleared": True if owned_samples or owned_reference_sample else None,
        "source_ownership_confirmed": True if (owned_samples or owned_stems or owned_vocals or owned_reference_sample or owned_reference_stems) else None,
        "vocal_performer_consent": True if owned_vocals else None,
        "featured_artist_metadata_complete": None,
        "explicit_content_flag_set": metadata_explicit in {True, False},
    }
    release_ready = parse_bool(getattr(args, "release_ready", None), False)
    zero_clarification_default = None if getattr(args, "zero_clarification", None) is None else parse_bool(getattr(args, "zero_clarification", None), False)
    target_deliverable = validate_choice(
        "target_deliverable",
        value_or_default(getattr(args, "target_deliverable", None), "release_package" if release_ready else "demo"),
        SUPPORTED_TARGET_DELIVERABLES,
        warnings,
    )
    release_profile = validate_choice(
        "release_profile",
        value_or_default(getattr(args, "release_profile", None), "custom"),
        SUPPORTED_RELEASE_PROFILES,
        warnings,
    )
    release_intent = build_release_intent(
        rough_request=raw_full_korean_request,
        workflow=getattr(args, "workflow", None),
        mode=mode,
        release_ready=release_ready,
        zero_clarification=zero_clarification_default,
        target_deliverable=target_deliverable,
        release_profile=release_profile,
        reference_audio_available=bool(getattr(args, "reference_audio", None)),
    )
    resolved_workflow = release_intent["workflow"] if getattr(args, "workflow", None) in {"bad_ai_song_rescue", "song_to_release", "sample_to_release", "vocal_to_release", "stems_to_release", "plan_only"} else getattr(args, "workflow", None)
    release_mode_requested = bool(
        release_ready
        or target_deliverable != "demo"
        or getattr(args, "workflow", None) in {"song_to_release", "sample_to_release", "vocal_to_release", "stems_to_release"}
    )
    release_ready = bool(release_intent["release_ready"])
    zero_clarification = bool(release_intent["zero_clarification"])
    target_deliverable = release_intent["target_deliverable"]
    release_profile = release_intent["style_cluster"]
    if release_mode_requested and not getattr(args, "master_loudness", None) and release_intent["mix_master_target"] in SUPPORTED_MASTER_LOUDNESS:
        master_loudness = release_intent["mix_master_target"]
    priority = getattr(args, "priority", None) or (release_intent["priority"] if release_mode_requested or raw_full_korean_request else "")
    avoid_list = getattr(args, "avoid_list", None) or ""
    has_brief_input = any(
        (
            creative_target,
            priority,
            avoid_list,
            getattr(args, "vocal_direction", None),
            getattr(args, "drum_808_direction", None),
            getattr(args, "master_direction", None),
            reference_text,
            getattr(args, "reference_audio", None),
            creative_target_text,
            vocal_fx_text,
            drum_bass_request_text,
            style_cluster_text,
            rough_request,
            release_ready,
            zero_clarification,
            target_deliverable != "demo",
            owned_reference_sample,
            owned_reference_stems,
            owned_samples,
            owned_stems,
            owned_vocals,
            any_release_metadata_provided(release_metadata),
            getattr(args, "length_start", None),
            getattr(args, "length_end", None),
        )
    )
    vocal_direction = normalize_vocal_direction(getattr(args, "vocal_direction", None) or "")
    drum_808_direction = normalize_drum_808_direction(getattr(args, "drum_808_direction", None) or getattr(args, "drum_808", None) or defaults["drum_808"])
    master_direction = normalize_master_direction(getattr(args, "master_direction", None) or getattr(args, "master_loudness", None) or master_loudness)
    rescue_mode = validate_choice(
        "rescue_mode",
        value_or_default(getattr(args, "rescue_mode", None), "plan"),
        SUPPORTED_RESCUE_MODES,
        warnings,
    )
    target_length = normalize_rescue_target_length(
        getattr(args, "target_length", None) or getattr(args, "length_mode", None) or release_intent["final_length"] or defaults["length_mode"]
    )
    rescue_style_cluster = normalize_rescue_style_cluster(
        getattr(args, "style_cluster", None)
        or (release_intent["style_cluster"] if release_intent.get("style_cluster") in SUPPORTED_RESCUE_STYLE_CLUSTERS else None)
    )
    generate_lead = parse_bool(getattr(args, "generate_lead", None), True)
    demote_vocal_texture = parse_bool(getattr(args, "demote_vocal_texture", None), True)
    length_mode = normalize_length_mode(getattr(args, "length_mode", None) or target_length or release_intent["final_length"] or defaults["length_mode"])
    export_format = normalize_export_format(getattr(args, "export_format", None) or defaults["export_format"])
    creative_brief = build_creative_brief_payload(
        mode=mode,
        main_input=primary_input,
        beat_file=getattr(args, "beat_file", None),
        lead_vocal_file=getattr(args, "lead_vocal_file", None) or getattr(args, "vocal_file", None),
        adlibs_file=getattr(args, "adlib_file", None),
        backing_vocal_file=getattr(args, "backing_vocal_file", None),
        stems_folder=getattr(args, "stems_folder", None),
        reference_audio=getattr(args, "reference_audio", None),
        length_mode=length_mode,
        length_start=getattr(args, "length_start", None),
        length_end=getattr(args, "length_end", None),
        creative_target=creative_target_for_brief,
        priority=priority,
        avoid=avoid_list,
        vocal_direction=vocal_direction,
        drum_808_direction=drum_808_direction,
        master_direction=master_direction,
        export_format=export_format,
        save_logic_project=save_logic_project,
        raw_full_korean_request=raw_full_korean_request,
        creative_target_text=creative_target_text or creative_target_for_brief,
        vocal_fx_text=vocal_fx_text,
        drum_bass_request_text=drum_bass_request_text,
        style_cluster_text=style_cluster_text,
        owned_reference_sample=owned_reference_sample,
        owned_reference_stems=owned_reference_stems,
        owned_samples=owned_samples,
        owned_stems=owned_stems,
        owned_vocals=owned_vocals,
        release_metadata=release_metadata,
        release_rights=release_rights,
        rough_request=rough_request,
        release_ready=release_ready,
        target_deliverable=target_deliverable,
        zero_clarification=zero_clarification,
        assumptions=release_intent["assumptions"],
        style_cluster=release_intent["style_cluster"],
        workflow=release_intent["workflow"],
        safety_blocks=release_intent["safety_blocks"],
        manual_logic_required=release_intent["manual_logic_required"],
        deliverables_requested=release_intent["deliverables_requested"],
    )
    if not has_brief_input:
        creative_brief = None
    return UserOptions(
        input_path=primary_input,
        length_mode=length_mode,
        vocal_mode=getattr(args, "vocal_mode", None) or defaults["vocal_mode"],
        melody_focus=getattr(args, "melody_focus", None) or defaults["melody_focus"],
        drum_808=drum_808_direction,
        export_format=export_format,
        save_logic_project=save_logic_project,
        mode=mode,
        vocal_file=getattr(args, "vocal_file", None),
        beat_file=getattr(args, "beat_file", None),
        lead_vocal_file=getattr(args, "lead_vocal_file", None),
        adlib_file=getattr(args, "adlib_file", None),
        backing_vocal_file=getattr(args, "backing_vocal_file", None),
        stems_folder=getattr(args, "stems_folder", None),
        reference_audio=getattr(args, "reference_audio", None),
        sample_folder=getattr(args, "sample_folder", None),
        reference_text=raw_full_korean_request or reference_text or creative_target,
        vocal_style=vocal_style,
        mix_intensity=mix_intensity,
        master_loudness=master_loudness,
        autotune=autotune,
        deess=deess,
        reverb_space=reverb_space,
        delay_style=delay_style,
        creative_target=creative_target_for_brief,
        creative_target_text=creative_target_text or creative_target_for_brief,
        raw_full_korean_request=raw_full_korean_request,
        vocal_fx_text=vocal_fx_text,
        drum_bass_request_text=drum_bass_request_text,
        style_cluster_text=style_cluster_text,
        owned_reference_sample=owned_reference_sample,
        owned_reference_stems=owned_reference_stems,
        owned_samples=owned_samples,
        owned_stems=owned_stems,
        owned_vocals=owned_vocals,
        release_metadata=release_metadata,
        release_rights=release_rights,
        priority=priority,
        avoid_list=avoid_list,
        vocal_direction=vocal_direction,
        drum_808_direction=drum_808_direction,
        master_direction=master_direction,
        length_start=getattr(args, "length_start", None),
        length_end=getattr(args, "length_end", None),
        arrangement_autopilot=bool(getattr(args, "arrangement_autopilot", False) or resolved_workflow in {"song_to_mix_master", "song_to_release", "sample_to_arrangement", "sample_to_release", "stems_to_production", "stems_to_release"}),
        arrangement_sample_file=getattr(args, "arrangement_sample_file", None),
        arrangement_vocal_file=getattr(args, "arrangement_vocal_file", None),
        arrangement_genre=getattr(args, "arrangement_genre", None) or "digicore",
        workflow=resolved_workflow,
        rough_request=rough_request,
        rescue_mode=rescue_mode,
        generate_lead=generate_lead,
        demote_vocal_texture=demote_vocal_texture,
        target_length=target_length,
        style_cluster=rescue_style_cluster,
        release_ready=release_ready,
        zero_clarification=zero_clarification,
        target_deliverable=target_deliverable,
        release_profile=release_profile,
        release_intent=release_intent,
        creative_brief=creative_brief,
        input_exists=input_exists,
        validation_warnings=tuple(warnings),
    )


def options_from_questionnaire(defaults: dict[str, Any], project_root: Path = PROJECT_ROOT) -> UserOptions:
    mode = normalize_mode(ask_text("Project mode (instrumental beat only / vocal + beat / full stereo song / stems)", "instrumental beat only"))
    input_path = ask_optional("Main input file") or None
    beat_file = ask_optional("Beat file if applicable") or None
    lead_vocal_file = ask_optional("Lead vocal file if applicable") or None
    adlib_file = ask_optional("Adlibs file if applicable") or None
    backing_vocal_file = ask_optional("Backing vocal file if applicable") or None
    stems_folder = ask_optional("Stems folder if applicable") or None
    raw_full_korean_request = ask_optional(
        '전체 수정 요청을 한국말로 한 번에 입력 (예: "웨스트우드 Just Touched Down 베이스랑 킥 느낌, 보컬 오토튠 더, 디카페이터 살짝, 2hollis/ycs/SYSTEM SEOUL처럼, 신디 넓게.")'
    )
    reference_audio = ask_optional("Reference audio file path, optional") or None
    owned_reference_sample = ask_bool("Are you providing an owned/licensed sample for exact sample/layer use?", False)
    owned_reference_stems = ask_bool("Are you providing owned/licensed stems for exact sample/layer use?", False)
    length_mode = normalize_length_mode(ask_text("Desired final length (keep original / under 2 minutes / 15 sec reels / 30 sec short-form / specific section)", "under 2 minutes"))
    length_start = None
    length_end = None
    if length_mode == "specific_section":
        length_start = ask_optional("Specific section start time") or None
        length_end = ask_optional("Specific section end time") or None
    creative_target = ask_optional(
        'Creative target text if separate from the raw request (optional)'
    ) or raw_full_korean_request
    priority = ask_text("Which part matters most (kick / bass / drums / vocal / synth width / melody / reels hook / master)", "vocal" if mode in {"vocal_plus_beat", "stems", "full_song_stereo"} else "melody")
    avoid_list = ask_optional("What must be avoided (exact copy, generic trap, cheap clipping, random AI glitch, muddy 808, harsh vocal, overcompression)")
    vocal_fx_text = ask_optional("Vocal FX direction (natural / medium autotune / hard tune / Decapitator subtle / Decapitator strong / custom)", "natural")
    drum_808_direction = normalize_drum_808_direction(ask_optional("Drum / bass request text (weak / medium / strong controlled / reference-inspired energetic digital drums / custom text)", "strong controlled"))
    style_cluster_text = ask_optional("Style cluster text (2hollis / ycs / SYSTEM SEOUL / domestic digicore / custom)", "")
    vocal_direction = normalize_vocal_direction(vocal_fx_text)
    master_direction = normalize_master_direction(ask_text("Master direction (master-ready headroom / streaming-safe / loud demo)", "master-ready headroom"))
    export_format = normalize_export_format(ask_text("Export format (WAV 24-bit 44.1kHz / WAV 24-bit 48kHz)", "WAV 24-bit 48kHz"))
    save_logic_project = ask_bool("Save Logic project?", bool(defaults["save_logic_project"]))
    vocal_mode = defaults["vocal_mode"]
    melody_focus = "front"
    drum_808 = drum_808_direction
    input_exists, warnings = validate_input_path(input_path)
    brief = build_creative_brief_payload(
        mode=mode,
        main_input=input_path,
        beat_file=beat_file,
        lead_vocal_file=lead_vocal_file,
        adlibs_file=adlib_file,
        backing_vocal_file=backing_vocal_file,
        stems_folder=stems_folder,
        reference_audio=reference_audio,
        length_mode=length_mode,
        length_start=length_start,
        length_end=length_end,
        creative_target=creative_target,
        priority=priority,
        avoid=avoid_list,
        vocal_direction=vocal_direction,
        drum_808_direction=drum_808_direction,
        master_direction=master_direction,
        export_format=export_format,
        save_logic_project=save_logic_project,
        raw_full_korean_request=raw_full_korean_request,
        creative_target_text=creative_target,
        vocal_fx_text=vocal_fx_text,
        drum_bass_request_text=drum_808_direction,
        style_cluster_text=style_cluster_text,
        owned_reference_sample=owned_reference_sample,
        owned_reference_stems=owned_reference_stems,
    )
    persist_creative_brief_files(brief, project_root)

    return UserOptions(
        input_path=input_path,
        length_mode=length_mode,
        vocal_mode=vocal_mode,
        melody_focus=melody_focus,
        drum_808=drum_808,
        export_format=export_format,
        save_logic_project=save_logic_project,
        mode=mode,
        vocal_file=lead_vocal_file,
        beat_file=beat_file,
        lead_vocal_file=lead_vocal_file,
        adlib_file=adlib_file,
        backing_vocal_file=backing_vocal_file,
        stems_folder=stems_folder,
        reference_audio=reference_audio,
        sample_folder=None,
        reference_text=" ".join(item for item in (raw_full_korean_request, creative_target, vocal_fx_text, drum_808_direction, style_cluster_text) if item),
        vocal_style=defaults["vocal_style"],
        mix_intensity=defaults["mix_intensity"],
        master_loudness=master_direction,
        autotune=defaults["autotune"],
        deess=defaults["deess"],
        reverb_space=defaults["reverb_space"],
        delay_style=defaults["delay_style"],
        creative_target=creative_target,
        creative_target_text=creative_target,
        raw_full_korean_request=raw_full_korean_request,
        vocal_fx_text=vocal_fx_text,
        drum_bass_request_text=drum_808_direction,
        style_cluster_text=style_cluster_text,
        owned_reference_sample=owned_reference_sample,
        owned_reference_stems=owned_reference_stems,
        priority=priority,
        avoid_list=avoid_list,
        vocal_direction=vocal_direction,
        drum_808_direction=drum_808_direction,
        master_direction=master_direction,
        length_start=length_start,
        length_end=length_end,
        arrangement_autopilot=False,
        arrangement_sample_file=None,
        arrangement_vocal_file=None,
        arrangement_genre="digicore",
        workflow=None,
        rough_request="",
        creative_brief=brief,
        input_exists=input_exists,
        validation_warnings=warnings,
    )
