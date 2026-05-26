from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import load_defaults
from humanization_rubric import reference_plain_language, render_style_match_qc
from paths import PROJECT_ROOT
from vocal_fx_intent import build_vocal_fx_intent


ANALYSIS_PATH = PROJECT_ROOT / "01_ANALYSIS" / "analysis.json"
EDIT_PLAN_PATH = PROJECT_ROOT / "02_EDIT_PLAN" / "edit_plan.md"
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "edit_plan_template.md"
REFERENCE_PROFILE_PATH = PROJECT_ROOT / "08_REFERENCE_MATCH" / "reference_target_profile.json"
PRODUCTION_PACKAGE_PATH = PROJECT_ROOT / "02_EDIT_PLAN" / "production_package_manifest.json"


DEFAULT_STRUCTURE = [
    ("0:00", "immediate motif / filtered motif"),
    ("0:08", "drums enter or partial drop"),
    ("0:16", "main groove"),
    ("0:32", "hook / strongest melody"),
    ("0:48", "variation"),
    ("1:04", "second hook"),
    ("1:20", "breakdown or filtered melody"),
    ("1:36", "final hook"),
    ("1:52", "fade or clean outro"),
]


def load_analysis(path: Path = ANALYSIS_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Analysis JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference_profile(path: Path = REFERENCE_PROFILE_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_production_package(path: Path = PRODUCTION_PACKAGE_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def seconds_to_time(value: float | int | None) -> str:
    if value is None:
        return "not detected"
    seconds = max(0.0, float(value))
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes}:{remaining:05.2f}"


def region_label(region: dict[str, Any] | None) -> str:
    if not region:
        return "not detected"
    return f"{seconds_to_time(region.get('start'))}-{seconds_to_time(region.get('end'))}"


def list_regions(items: list[dict[str, Any]], fallback: str) -> str:
    if not items:
        return f"- {fallback}\n"
    lines = []
    for item in items[:8]:
        confidence = item.get("confidence")
        confidence_text = f" ({confidence} confidence)" if confidence else ""
        lines.append(f"- {region_label(item)}{confidence_text}: {item.get('reason', 'review manually')}")
    return "\n".join(lines) + "\n"


def user_settings_text(options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    length = brief.get("length", {})
    avoid = brief.get("avoid", [])
    lines = [
        f"- project mode: {brief.get('mode') or options.get('mode', 'instrumental_beat')}",
        f"- final length: {length.get('mode') or options.get('length_mode', 'under_2min')}",
        f"- specific section: {length.get('start') or 'not provided'} to {length.get('end') or 'not provided'}",
        f"- creative target: {brief.get('creative_target') or options.get('creative_target') or 'not provided'}",
        f"- priority: {brief.get('priority') or options.get('priority') or 'not provided'}",
        f"- avoid list: {', '.join(avoid) if avoid else options.get('avoid_list') or 'not provided'}",
        f"- vocal direction: {brief.get('vocal_direction') or options.get('vocal_direction') or options.get('vocal_style', 'polished')}",
        f"- drum/808 direction: {brief.get('drum_808_direction') or options.get('drum_808_direction') or options.get('drum_808', 'strong_controlled')}",
        f"- master direction: {brief.get('master_direction') or options.get('master_direction') or options.get('master_loudness', 'master_ready_headroom')}",
        f"- vocal suppression setting: {options.get('vocal_mode', 'suppress')}",
        f"- melody focus: {options.get('melody_focus', 'front')}",
        f"- export format: {options.get('export_format', 'wav24_48k')}",
        f"- Logic project save preference: {str(options.get('save_logic_project', True)).lower()}",
    ]
    return "\n".join(lines)


def creative_brief_summary_section(options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    avoid = brief.get("avoid") or options.get("avoid_list") or []
    if isinstance(avoid, str):
        avoid_text = avoid or "not provided"
    else:
        avoid_text = ", ".join(str(item) for item in avoid) if avoid else "not provided"
    return "\n".join(
        [
            "## Creative Brief Summary",
            "",
            f"- mode: {brief.get('mode') or options.get('project_mode') or options.get('mode', 'instrumental_beat')}",
            f"- target feeling: {brief.get('creative_target') or options.get('creative_target') or 'not provided'}",
            f"- priority element: {brief.get('priority') or options.get('priority') or 'not provided'}",
            f"- avoid list: {avoid_text}",
            f"- vocal direction: {brief.get('vocal_direction') or options.get('vocal_direction') or options.get('vocal_style', 'polished')}",
            f"- drum/808 direction: {brief.get('drum_808_direction') or options.get('drum_808_direction') or options.get('drum_808', 'strong_controlled')}",
            f"- master direction: {brief.get('master_direction') or options.get('master_direction') or options.get('master_loudness', 'master_ready_headroom')}",
        ]
    )


def structure_text() -> str:
    return "\n".join(f"- {time}: {label}" for time, label in DEFAULT_STRUCTURE)


def _reference_requests(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return profile.get("parsed_intent", {}).get("reference_requests", [])


def _target_elements(profile: dict[str, Any]) -> list[str]:
    parsed = profile.get("parsed_intent", {})
    traits = profile.get("reference_traits", {})
    targets = set(str(item) for item in (parsed.get("target_elements") or []) if item)
    targets.update(str(item) for item in (traits.get("target_elements") or []) if item)
    targets.update(str(item.get("target_element")) for item in _reference_requests(profile) if item.get("target_element"))
    if len(targets) > 1 and "whole_song" in targets:
        targets.remove("whole_song")
    return sorted(targets) or ["whole_song"]


def _has_target(profile: dict[str, Any], names: set[str]) -> bool:
    return any(item in names for item in _target_elements(profile))


def _mode_from_options(options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    return str(brief.get("mode") or options.get("project_mode") or options.get("mode") or "instrumental_beat")


def _only_one_stereo_file(options: dict[str, Any]) -> bool:
    brief = options.get("creative_brief") or {}
    files = brief.get("input_files", {})
    if not files:
        return bool(options.get("input") or options.get("input_file")) and not any(
            options.get(key)
            for key in ("beat_file", "lead_vocal_file", "adlibs_file", "backing_vocal_file", "stems_folder")
        )
    provided = [
        files.get("main_input"),
        files.get("beat_file"),
        files.get("lead_vocal_file"),
        files.get("adlibs_file"),
        files.get("backing_vocal_file"),
        files.get("stems_folder"),
    ]
    return len([item for item in provided if item]) == 1


def _reference_audio_provided(profile: dict[str, Any]) -> bool:
    source = profile.get("source", {})
    audio_path = source.get("reference_audio_path")
    return bool(audio_path)


def _what_will_be_matched(profile: dict[str, Any]) -> str:
    targets = set(_target_elements(profile))
    traits = profile.get("reference_traits", {})
    pieces = []
    if targets & {"bass", "808", "bass_808"}:
        bass = profile.get("bass_808_targets", {})
        pieces.append(
            f"bass/808 direction: {bass.get('tone', 'unknown')} tone, sub weight {bass.get('sub_weight', 'unknown')}/5, glide {bass.get('glide', 'unknown')}/5, movement {bass.get('movement', 'unknown')}"
        )
    if "synth_width" in targets:
        width = traits.get("synth_width", {})
        pieces.append(
            f"synth width: {width.get('pan_motion', 'none')} pan motion, width {width.get('stereo_width', 2)}/5, mono-safe low end"
        )
    if "drums" in targets:
        drums = profile.get("drum_targets", {})
        pieces.append(
            f"drum feel: {drums.get('kick', 'unknown')} kick, {drums.get('snare_or_clap', 'unknown')} snare/clap, {drums.get('hats', 'unknown')} hats, {drums.get('fills', 'unknown')} fills"
        )
    if "vocal" in targets:
        vocal = profile.get("vocal_targets", {})
        pieces.append(
            f"vocal balance: {vocal.get('lead_position', 'unknown')} lead, {vocal.get('texture', 'unknown')} texture"
        )
    if not pieces:
        style = profile.get("style_targets", {})
        pieces.append(
            f"broad energy {style.get('energy', 'unknown')}/5, brightness {style.get('brightness', 'unknown')}/5, low-end weight {style.get('low_end_weight', 'unknown')}/5"
        )
    return "; ".join(pieces)


def reference_target_section(profile: dict[str, Any], options: dict[str, Any]) -> str:
    parsed = profile.get("parsed_intent", {})
    source = profile.get("source", {})
    style = profile.get("style_targets", {})
    drums = profile.get("drum_targets", {})
    bass = profile.get("bass_808_targets", {})
    vocals = profile.get("vocal_targets", {})
    arrangement = profile.get("arrangement_targets", {})
    traits = profile.get("reference_traits", {})
    web = profile.get("web_reference_research", {})
    avoid = profile.get("avoid", [])
    requests = _reference_requests(profile)
    raw_text = parsed.get("raw_text") or source.get("reference_text") or (options.get("creative_brief") or {}).get("creative_target") or "not provided"
    reference_audio = "yes" if _reference_audio_provided(profile) else "no"
    request_lines = []
    for request in requests:
        request_lines.extend(
            [
                f"- raw user phrase: {raw_text}",
                f"- parsed reference title: {request.get('reference_title') or 'not provided'}",
                f"- target element: {request.get('target_element') or 'whole_song'}",
                f"- action intent: {request.get('action') or 'not provided'}",
                f"- confidence level: {request.get('confidence') or source.get('confidence', 'low')}",
                f"- reference audio provided: {reference_audio}",
            ]
        )
    if not request_lines:
        request_lines = [
            f"- raw user phrase: {raw_text}",
            "- parsed reference title: not provided",
            f"- target element: {', '.join(parsed.get('target_elements', [])) or 'whole_song'}",
            f"- confidence level: {source.get('confidence', 'low')}",
            f"- reference audio provided: {reference_audio}",
        ]
    return "\n".join(
        [
            "## Reference-Inspired Production Target",
            "",
            *request_lines,
            f"- what will be matched: {_what_will_be_matched(profile)}.",
            "- what will not be copied: exact melody, sample, drum pattern, lyrics, sound recording, mix print, or protected song identity.",
            "",
            f"- Parsed target elements: {', '.join(parsed.get('target_elements', [])) or 'not provided'}.",
            f"- Reference titles: {', '.join(parsed.get('reference_titles', [])) or 'not provided'}.",
            f"- Confidence: {profile.get('source', {}).get('confidence', 'low')}.",
            f"- Evidence used: {'; '.join(traits.get('evidence_summary', [])) or 'text-only prompt interpretation'}.",
            f"- Web research unavailable: {str(bool(web.get('web_reference_research_unavailable'))).lower()}.",
            f"- Priority: {parsed.get('priority', 'not provided')}.",
            f"- Plain-language interpretation: {reference_plain_language(profile)}",
            f"- Drum feel target: kick {drums.get('kick')}, snare/clap {drums.get('snare_or_clap')}, hats {drums.get('hats')}, swing {drums.get('swing')}, fills {drums.get('fills')}.",
            f"- 808/bass target: tone {bass.get('tone')}, sub weight {bass.get('sub_weight')}/5, distortion {bass.get('distortion')}/5, glide {bass.get('glide')}/5, movement {bass.get('movement')}, priority {bass.get('priority')}.",
            f"- Synth width target: pan {traits.get('synth_width', {}).get('pan_motion', 'none')}, width {traits.get('synth_width', {}).get('stereo_width', 2)}/5, low end mono below {traits.get('synth_width', {}).get('low_frequency_mono_cutoff_hz', 120)} Hz.",
            f"- Melody treatment target: preserve the melodic identity while matching brightness {style.get('brightness')}/5 and emotional energy {style.get('energy')}/5.",
            f"- Vocal treatment target: lead {vocals.get('lead_position')}, texture {vocals.get('texture')}, adlib width {vocals.get('adlib_width')} if vocals/stems are present.",
            f"- Arrangement target: hook around {arrangement.get('hook_entrance_seconds')}s, {arrangement.get('drop_style')} drop, variation every {arrangement.get('variation_frequency_bars')} bars.",
            "- Mix/master target: controlled loudness, clear transient lift, strong low-end support without uncontrolled clipping.",
            "- Legal/accuracy notes:",
            *(f"  - {item}" for item in profile.get("legal_and_accuracy_notes", [])),
            "- Explicit avoid list:",
            *(f"  - {item}" for item in avoid),
            "",
            render_style_match_qc(profile, stereo_only=True, vocal_mode=options.get("vocal_mode", "suppress")).rstrip(),
        ]
    )


def bass_808_reference_plan(profile: dict[str, Any], options: dict[str, Any]) -> str:
    if not _has_target(profile, {"bass", "808", "bass_808"}):
        return ""
    bass = profile.get("bass_808_targets", {})
    source = profile.get("source", {})
    audio = profile.get("audio_analysis", {})
    raw_text = profile.get("parsed_intent", {}).get("raw_text") or source.get("reference_text", "")
    reference_audio = _reference_audio_provided(profile)
    text_only_note = ""
    if raw_text and not reference_audio:
        text_only_note = "Text-only reference. Exact bass tone cannot be verified. The plan uses a reference-inspired bass direction: controlled sub, clear 808/bass presence, melody-supportive low-end, no muddy masking."
    analysis_note = ""
    if reference_audio and audio.get("available"):
        analysis_note = (
            f"- Reference audio analysis: low-end weight {audio.get('low_end_weight_heuristic')}, "
            f"onset density {audio.get('onset_density')}, brightness {audio.get('spectral_brightness_heuristic')}, "
            f"dynamic range {audio.get('dynamic_range_heuristic')}."
        )
    stereo_warning = ""
    if _mode_from_options(options) == "full_song_stereo" or _only_one_stereo_file(options):
        stereo_warning = "- Stereo-only warning: broad EQ, gain, fade, saturation, and mastering moves are possible, but actual bassline replacement needs stems, MIDI, or manual Logic layering."
    return "\n".join(
        [
            "## Bass / 808 Reference Plan",
            "",
            f"- desired sub weight: {bass.get('sub_weight', 'unknown')}/5.",
            f"- desired tone: {bass.get('tone', 'unknown')}.",
            f"- glide amount: {bass.get('glide', 'unknown')}/5.",
            f"- distortion amount: {bass.get('distortion', 'unknown')}/5.",
            f"- movement density: {bass.get('movement', 'unknown')} movement, rhythmic density {bass.get('rhythmic_density', 'unknown')}/5.",
            f"- relationship to melody: {bass.get('priority', 'balanced')}. Keep low-end supportive unless the creative brief explicitly prioritizes 808/bass.",
            "- mono sub rule: keep sub bass and the fundamental low-end centered/mono; only widen upper harmonics or high-passed layers.",
            *([f"- {text_only_note}"] if text_only_note else []),
            *([analysis_note] if analysis_note else []),
            *([stereo_warning] if stereo_warning else []),
            "- Logic manual steps:",
            "  - If stems or MIDI exist, edit bass notes directly, tune slides to the key, and automate sub level under melody hooks.",
            "  - If only stereo exists, layer a new Logic 808/bass part manually and high-pass/duck the printed low-end only enough to avoid masking.",
            "  - If width is requested, duplicate or layer the synth/bass texture, high-pass the widened copy around 120-180 Hz, and leave the sub centered.",
            "  - Check small speakers, sub-capable speakers, and headphones before final export.",
            *(f"  - {item}" for item in bass.get("manual_logic_notes", [])),
        ]
    )


def synth_width_reference_plan(profile: dict[str, Any], options: dict[str, Any]) -> str:
    if not _has_target(profile, {"synth_width"}):
        return ""
    traits = profile.get("reference_traits", {})
    width = traits.get("synth_width", {})
    stereo_warning = ""
    if _mode_from_options(options) == "full_song_stereo" or _only_one_stereo_file(options):
        stereo_warning = "- Stereo-only warning: broad mid/side EQ or widening can be suggested, but stem-level panning requires stems or manual Logic layers."
    return "\n".join(
        [
            "## Synth Width / Panning Plan",
            "",
            f"- pan motion: {width.get('pan_motion', 'none')}.",
            f"- stereo width: {width.get('stereo_width', 2)}/5.",
            f"- mid/side approach: {width.get('mid_side_approach', 'unknown')}.",
            f"- low-frequency mono cutoff: {width.get('low_frequency_mono_cutoff_hz', 120)} Hz.",
            "- sub and fundamental low-end must stay mono/centered.",
            "- widening applies to synth layers, upper harmonics, pads, doubles, or high-passed bass layers.",
            "- avoid phase problems and mono incompatibility.",
            *([stereo_warning] if stereo_warning else []),
            "- Logic manual steps:",
            "  - Duplicate the synth layer or create a supporting high-passed double.",
            "  - High-pass the widened layer around 120-180 Hz.",
            "  - Keep the sub/fundamental centered and mono.",
            "  - Automate pan or use stereo spread carefully.",
            "  - Check mono compatibility before final export.",
        ]
    )


def drum_reference_plan(profile: dict[str, Any]) -> str:
    if not _has_target(profile, {"drums", "kick", "snare", "hats"}):
        return ""
    drums = profile.get("drum_targets", {})
    style = profile.get("style_targets", {})
    avoid = profile.get("avoid", [])
    raw_text = (profile.get("parsed_intent", {}).get("raw_text") or "").lower()
    love_blur_lines = []
    if "love blur" in raw_text:
        love_blur_lines = [
            "- Love Blur drum translation: energetic digital/underground drum feel.",
            "- Love Blur drum translation: punchy kick.",
            "- Love Blur drum translation: snare/clap cuts without harshness.",
            "- Love Blur drum translation: active but controlled hats.",
            "- Love Blur drum translation: intentional fills.",
            "- Love Blur drum translation: strong but controlled 808 support.",
            "- Love Blur drum translation: no uncontrolled rage clipping.",
        ]
    return "\n".join(
        [
            "## Drum Reference Plan",
            "",
            f"- kick target: {drums.get('kick', 'unknown')}.",
            f"- snare/clap target: {drums.get('snare_or_clap', 'unknown')}.",
            f"- hats target: {drums.get('hats', 'unknown')}.",
            f"- fill amount: {drums.get('fills', 'controlled')}.",
            f"- swing feel: {drums.get('swing', 'unknown')}.",
            f"- transient sharpness: {style.get('energy', 'unknown')}/5 energy translated into punch without harsh clipping.",
            "- avoid random AI glitch: true.",
            f"- avoid cheap generic trap loop unless requested: {'generic trap loop' in avoid or 'predictable generic trap cadence' in avoid}.",
            *love_blur_lines,
            "- Logic manual steps:",
            "  - Use kick/snare/hat targets as replacement or layering guidance only when stems, MIDI, or manual programming are available.",
            "  - For stereo-only files, use transient shaping, EQ, automation, and optional manual drum layers; do not claim the printed pattern was replaced.",
            *(f"  - {item}" for item in drums.get("manual_logic_notes", [])),
        ]
    )


def commercial_digicore_autopilot_section(profile: dict[str, Any], options: dict[str, Any]) -> str:
    autopilot = profile.get("commercial_digicore_autopilot") or profile.get("reference_traits", {}).get("commercial_digicore_autopilot", {})
    if not autopilot or not autopilot.get("active"):
        return ""
    arrangement = autopilot.get("arrangement_defaults", {})
    mix = autopilot.get("mix_targets", {})
    style = autopilot.get("style_cluster", {})
    qc = autopilot.get("qc_requirements", {})
    stereo_only = _mode_from_options(options) == "full_song_stereo" or _only_one_stereo_file(options)
    return "\n".join(
        [
            "## Commercial Digicore Autopilot",
            "",
            "- Purpose: translate rough Korean creative direction into safe commercial-quality production targets.",
            "- Commercial quality means technical readiness, mix clarity, arrangement intentionality, and QC discipline; it does not promise chart-level success.",
            f"- Style cluster active: {str(bool(style.get('active'))).lower()} ({', '.join(style.get('labels', [])) or 'not provided'}).",
            f"- Hook target: {'early' if arrangement.get('hook_early') else 'natural'}, target seconds {arrangement.get('target_hook_seconds') or 'not fixed'}, intro max {arrangement.get('intro_max_seconds')}s.",
            f"- Variation cadence: every {arrangement.get('variation_frequency_bars')} bars; drop energy {arrangement.get('drop_energy')}.",
            f"- Humanize Suno/AI feel: {str(bool(autopilot.get('humanize_suno_requested'))).lower()} by adding intentional section changes and reducing loop repetition.",
            f"- Mix target: {mix.get('target')}; low end {mix.get('low_end')}; drums {mix.get('drums')}; vocal {mix.get('vocal')}.",
            f"- Master target: {mix.get('master')}; promise limit: {mix.get('promise_limit')}.",
            f"- Stereo-only limitation active: {str(stereo_only).lower()}.",
            "- Automatic fallback scope: broad stereo EQ, gain staging, trim/fade, conservative width, saturation, and mastering polish only.",
            "- Manual Logic scope: kick/bass replacement, drum rewrite, vocal tuning, plugin insertion, arrangement edits, and stem-level moves require stems, MIDI, or manual layers.",
            f"- QC must check: {', '.join(qc.get('score_dimensions', [])) or 'commercial readiness'}.",
            "- Avoid:",
            *(f"  - {item}" for item in autopilot.get("avoid", [])),
        ]
    )


def korean_request_translation_section(profile: dict[str, Any], options: dict[str, Any]) -> str:
    parsed = profile.get("parsed_intent", {})
    traits = profile.get("reference_traits", {})
    copying_policy = profile.get("copying_policy", {})
    source = profile.get("source", {})
    brief = options.get("creative_brief") or {}
    raw_request = (
        brief.get("raw_full_korean_request")
        or parsed.get("raw_text")
        or source.get("reference_text")
        or options.get("reference_text")
        or options.get("creative_target")
        or "not provided"
    )
    targets = _target_elements(profile)
    stereo_only = _mode_from_options(options) == "full_song_stereo" or _only_one_stereo_file(options)
    safety = traits.get("safety", {})
    vocal = traits.get("vocal", {})
    bass = traits.get("bass_808", {})
    drums = traits.get("drums", {})
    synth = traits.get("synth_width", {})
    arrangement = traits.get("arrangement", {})
    style_cluster_active = bool({"whole_style", "vocal", "synth_width", "arrangement"} & set(targets)) and any(
        token in raw_request.lower()
        for token in ("2hollis", "ycs", "system seoul", "투홀리스", "시스템서울", "시스템 서울", "와이씨에스")
    )
    return "\n".join(
        [
            "## Korean Natural-Language Request Translation",
            "",
            f"- Raw user request: {raw_request}",
            f"- Parsed targets: {', '.join(targets) or 'not provided'}",
            f"- Reference confidence: {source.get('confidence') or safety.get('confidence', 'low')}",
            f"- Copying policy: {copying_policy.get('report_note', 'No exact copying is performed or claimed.')}",
            "- What can be done automatically: parse the request, build high-level production targets, create fallback-safe broad processing, write QC checks, and prepare manual Logic instructions.",
            "- What requires stems/manual Logic: kick or bass replacement, exact MIDI/rhythm editing, vocal tuning choices, plugin insertion, detailed panning automation, and any stem-level remix.",
            "- What will not be copied: exact songs, exact kick samples, exact basslines, melodies, lyrics, drum patterns, sound recordings, artist voices, producer identity, or mix/master prints.",
            "",
            "## Kick/Bass `따와라` Request",
            f"- copying requested: {str(bool(copying_policy.get('copying_requested'))).lower()}.",
            f"- exact copy allowed: {str(bool(copying_policy.get('exact_copy_allowed'))).lower()}.",
            "- Do not extract or copy a kick/bass sample unless the user provides an owned/cleared local sample or stem.",
            "- If stems, MIDI, or an owned/cleared sample are provided:",
            "  - layer or replace kick/bass carefully.",
            "  - preserve phase alignment against the existing low end.",
            "  - tune 808 to the song key.",
            "  - check mono compatibility.",
            "- If no owned source is provided:",
            "  - design from scratch based on high-level traits.",
            f"  - match punch {drums.get('kick_transient', drums.get('transient_sharpness', 'unknown'))}/5, sub weight {bass.get('sub_weight', 'unknown')}/5, transient, saturation {bass.get('distortion', 'unknown')}/5, envelope, and groove density.",
            "  - avoid exact pattern or bassline copying.",
            "",
            "## Decapitator / AutoTune Vocal Request",
            f"- Pitch correction plan: {vocal.get('pitch_correction') or vocal.get('tuning', 'none')}.",
            f"- Saturation plan: {'Decapitator if installed, generic saturation otherwise' if vocal.get('requested_plugin') == 'Soundtoys Decapitator' or 'decapitator' in raw_request.lower() or '디카페이터' in raw_request else vocal.get('saturation', 'none')}.",
            "- Insert order recommendation:",
            "  1. cleanup EQ",
            "  2. pitch correction",
            "  3. compression",
            "  4. saturation / Decapitator",
            "  5. de-esser after saturation if needed",
            "  6. tone EQ",
            "  7. reverb/delay sends",
            "- If Logic automation cannot insert plugins: manual_required.",
            "- Do not claim plugin was applied unless verified by the rendered session/log/output.",
            "",
            "## 2hollis / ycs / SYSTEM SEOUL Style Cluster",
            f"- applies to this request: {str(style_cluster_active).lower()}.",
            "- Translate to bright digital hooks.",
            "- Translate to internet/digicore/hyperpop energy.",
            "- Use strong controlled 808.",
            "- Use sharp but controlled drums.",
            "- Keep vocal-forward if applicable.",
            f"- Add synth width and movement: width {synth.get('stereo_width', 2)}/5, pan motion {synth.get('pan_motion', 'none')}.",
            f"- Keep hook-forward arrangement: hook early {str(bool(arrangement.get('hook_early'))).lower()}.",
            "- Reduce random AI glitch.",
            "- Avoid cheap rage clipping.",
            "- No exact artist/song copying.",
            "",
            "## Synth Width / Panning",
            "- Keep sub/kick/808 fundamental mono and centered.",
            "- Widen upper synth layers only.",
            "- High-pass widened duplicate around 120-180Hz.",
            "- Pan/auto-pan only high-passed layers.",
            "- Check mono compatibility.",
            "- If only stereo source exists, use conservative mid/side treatment and warn about limits.",
            "",
            "## Stereo-Only Source Limitation",
            f"- stereo-only source active: {str(stereo_only).lower()}.",
            "- If current input is a single stereo WAV, no true kick/bass replacement is possible unless stems/manual layering are added.",
            "- No real stem-level drum rewrite is claimed.",
            "- No guaranteed vocal removal is claimed.",
            "- Broad EQ, saturation, width, trim, fade, gain staging, and mastering polish only.",
            "- QC must mark manual Logic edit needed if requested target requires stem-level changes.",
        ]
    )


def reference_application_logic_section(profile: dict[str, Any], options: dict[str, Any]) -> str:
    targets = set(_target_elements(profile))
    traits = profile.get("reference_traits", {})
    copying_policy = profile.get("copying_policy", {})
    master_direction = (
        (options.get("creative_brief") or {}).get("master_direction")
        or options.get("master_direction")
        or options.get("master_loudness")
        or "master_ready_headroom"
    )
    stereo_only = _mode_from_options(options) == "full_song_stereo" or _only_one_stereo_file(options)
    drums_active = bool(targets & {"drums", "kick", "snare", "hats"})
    bass_active = bool(targets & {"bass", "808", "bass_808"})
    synth_width_active = "synth_width" in targets
    vocal_active = "vocal" in targets
    return "\n".join(
        [
            "## Reference Application in Logic Pro",
            "",
            "Apply references as high-level production targets only. This section does not authorize copying exact songs, drum patterns, basslines, samples, lyrics, melodies, sound recordings, or a living artist's vocal identity.",
            f"- detected reference targets: {', '.join(sorted(targets)) or 'broad whole-song direction'}.",
            f"- stereo-only source limitation active: {str(stereo_only).lower()}.",
            "- If the user says `따와라`, use a licensed/owned user-provided sample or stem only; otherwise translate it to punch, transient sharpness, bass tone, saturation, width, and arrangement energy.",
            f"- copying policy: {copying_policy.get('report_note', 'No exact copying is performed or claimed.')}",
            f"- exact copy allowed: {str(bool(copying_policy.get('exact_copy_allowed'))).lower()}.",
            "",
            "### A. Drums Like Reference",
            f"- applies to this request: {str(drums_active).lower()}.",
            "- If stems, MIDI, or a drum track exists:",
            "  - adjust kick sample character.",
            "  - adjust snare/clap layer.",
            "  - adjust hat density.",
            "  - adjust swing.",
            "  - add controlled fills.",
            "  - avoid copying the exact reference drum pattern.",
            "  - avoid copying an exact protected kick sample unless the user supplied a licensed/owned source.",
            "- If only a stereo beat exists:",
            "  - use broad transient shaping, EQ, and arrangement cuts only.",
            "  - recommend manual drum layering if needed.",
            "  - mark stem-level drum rewrite as unavailable.",
            "",
            "### B. Bass / 808 Like Reference",
            f"- applies to this request: {str(bass_active).lower()}.",
            "- Keep sub below roughly 120Hz mono/centered.",
            "- Use saturation for audibility instead of excessive sub gain.",
            "- Use sidechain or automation so melody/vocal remains audible.",
            "- If glide or melodic movement is requested, exact bassline rewriting requires MIDI, stems, or manual Logic programming.",
            "- Do not copy an exact protected bassline or bass recording unless it is a licensed/owned user-provided source.",
            "- If only a stereo source exists, broad low-end EQ and saturation are possible, not true bassline replacement.",
            "",
            "### C. Synth Panning / Spatial Width",
            f"- applies to this request: {str(synth_width_active).lower()}.",
            "- Trigger phrases include `베이스처럼 신디를 패닝`, `신디를 좌우로 벌려`, and `공간감 줘`.",
            "- Do not widen sub frequencies.",
            "- Widen only synth layers, pads, upper harmonics, or high-passed duplicate layers.",
            "- Suggested Logic workflow:",
            "  1. duplicate synth layer if stems exist.",
            "  2. high-pass duplicate layer around 120-180Hz.",
            "  3. pan or use Direction Mixer/Stereo Spread carefully.",
            "  4. automate pan movement subtly.",
            "  5. keep main melody or vocal center.",
            "  6. check mono compatibility.",
            "- If only a stereo file exists:",
            "  - use conservative mid/side EQ or stereo width.",
            "  - warn about phase/mono risk.",
            "",
            "### D. Vocal Like Artist",
            f"- applies to this request: {str(vocal_active).lower()}.",
            "- If the user says `내 목소리를 [artist]처럼`, do not clone the artist's voice.",
            "- Translate to vocal production traits only:",
            f"  - forwardness: {traits.get('vocal', {}).get('lead_position', 'front')}.",
            f"  - brightness: {traits.get('vocal', {}).get('brightness', 'unknown')}.",
            f"  - compression: {traits.get('vocal', {}).get('compression', 'medium')}.",
            f"  - tuning amount: {traits.get('vocal', {}).get('tuning', 'unknown')}.",
            f"  - saturation/distortion: {traits.get('vocal', {}).get('saturation', 'subtle')}.",
            f"  - reverb/delay: {traits.get('vocal', {}).get('reverb_space', 'small_room')} / {traits.get('vocal', {}).get('delay_style', 'throw_only')}.",
            f"  - plugin-style reference: {traits.get('vocal', {}).get('plugin_style_reference') or 'not provided'}.",
            "  - adlib width: wider than the lead only when adlibs/backings exist.",
            "- Keep the user's own vocal identity.",
            "- If reference audio is provided, use it for broad tonal and spatial targets, not exact imitation.",
            "",
            "### E. Master / Final Loudness",
            "- Do not over-limit just to match reference loudness.",
            f"- Maintain requested master mode: {master_direction}.",
            "- QC must block PASS if clipping or wrong export format occurs.",
        ]
    )


def stereo_only_limitation_section(options: dict[str, Any]) -> str:
    if _mode_from_options(options) != "full_song_stereo" and not _only_one_stereo_file(options):
        return ""
    return "\n".join(
        [
            "## Stereo-Only Limitation",
            "",
            "- With a full stereo song or one stereo beat file, broad EQ, gain, fade, transient, saturation, and mastering treatment is possible.",
            "- Actual bassline replacement, drum pattern replacement, vocal removal, or stem-level remixing requires stems, MIDI, source sessions, or manual Logic layering.",
            "- This plan must be read as heuristic/stereo-only guidance unless separated sources are provided.",
        ]
    )


def drum_programming_section(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""
    drums = profile.get("drum_targets", {})
    bass = profile.get("bass_808_targets", {})
    avoid = profile.get("avoid", [])
    return "\n".join(
        [
            "## Drum Programming / Drum Treatment Plan",
            "",
            "If stems, MIDI, or drum replacement are available:",
            f"- Kick type: {drums.get('kick', 'short_punchy')}.",
            f"- Snare/clap type: {drums.get('snare_or_clap', 'tight')}.",
            f"- Hat density: {drums.get('hats', 'medium')}; keep active hats controlled rather than smeared.",
            f"- Swing: {drums.get('swing', 'straight')}.",
            f"- Fills: {drums.get('fills', 'controlled')}; fills should feel intentional, not random AI glitches.",
            "- Drum mutes: use pre-hook and second-hook mutes to lift the hook quickly.",
            f"- 808 variation: {bass.get('movement', 'simple')} movement, strong but supporting the melody.",
            "- Drop energy: make the hook lift quickly without cheap clipping.",
            "",
            "If only a stereo Suno file is available:",
            "- Use broad low-end, transient, and EQ treatment only.",
            "- Use manual Logic steps for drum replacement, layering, or MIDI reconstruction.",
            "- Do not claim actual drum pattern replacement from a stereo file.",
            "- Punchy kick should not become muddy; snare/clap should cut without harshness.",
            "- Hats can be active but controlled.",
            "- 808 should be strong but support the melody.",
            "- Avoid:",
            *(f"  - {item}" for item in avoid),
        ]
    )


def vocal_mode_active(options: dict[str, Any]) -> bool:
    project_mode = options.get("project_mode") or options.get("mode")
    vocal_mode = options.get("vocal_mode")
    return bool(project_mode in {"vocal_plus_beat", "full_song_stereo", "stems"} or vocal_mode in {"front", "lead", "polished", "rap_forward"})


def logic_vocal_mix_checklist(reference_profile: dict[str, Any] | None, options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    reference_note = (
        "- Reference direction is active: translate it into drum density, transient shape, 808 tone, and arrangement energy."
        if reference_profile
        else "- No reference direction was provided; use the vocal and beat balance goals from the creative brief/listening pass."
    )
    request_text = " ".join(
        str(item)
        for item in (
            options.get("vocal_fx_request"),
            options.get("reference_text"),
            options.get("creative_target"),
            options.get("vocal_direction"),
            brief.get("creative_target"),
            brief.get("vocal_direction"),
        )
        if item
    )
    vocal_fx = options.get("vocal_fx_intent") if isinstance(options.get("vocal_fx_intent"), dict) else build_vocal_fx_intent(request_text)
    saturation = vocal_fx.get("saturation", {})
    plugin = vocal_fx.get("plugin_application", {})
    pitch = vocal_fx.get("pitch_correction", {})
    return "\n".join(
        [
            "## Logic Pro Vocal Mix Checklist",
            "",
            "This is a manual Logic Pro checklist. AppleScript automation may help create or import a session, but it cannot fully mix vocals, tune performance, choose plugin settings, or make listening judgments automatically.",
            "",
            "### A. Session Setup",
            "- Import beat and vocal files.",
            "- Set project sample rate to export target.",
            "- Keep raw vocal muted as backup.",
            "- Route lead vocal, adlibs, and backing vocals to separate buses.",
            "- Route all vocals to a vocal bus.",
            "- Route instrumental to an instrumental bus.",
            "- Route all audio to a pre-master bus.",
            "",
            "### B. Vocal Gain Staging",
            "- Clip gain phrases before compression.",
            "- Reduce loud spikes manually.",
            "- Raise quiet phrases only enough for consistent delivery.",
            "- Avoid normalizing destructively.",
            "",
            "### C. Lead Vocal Chain",
            "Suggested chain:",
            "1. Channel EQ high-pass",
            "2. Subtractive EQ for mud/boxiness",
            "3. Resonance control",
            "4. Pitch correction/tuning if requested",
            "5. Compressor for leveling",
            "6. De-esser",
            "7. Saturation if requested",
            "8. Second compressor if needed for tone",
            "9. Presence/air EQ if needed",
            "10. De-ess again if saturation or brightness raises sibilance",
            "11. Send to reverb",
            "12. Send to delay throws",
            "",
            "### C2. Plugin-Aware Vocal FX Requests",
            f"- pitch correction requested: {str(bool(pitch.get('requested'))).lower()}, intensity {pitch.get('intensity', 'none')}.",
            f"- saturation requested: {str(bool(saturation.get('requested'))).lower()}, intensity {saturation.get('intensity', 'none')}, parallel mix {saturation.get('parallel_mix', 'none')}, tone {saturation.get('tone', 'neutral')}.",
            f"- requested saturation plugin: {saturation.get('requested_plugin') or 'not provided'}.",
            f"- plugin status: {plugin.get('status', 'not_requested')}.",
            f"- claim rule: {plugin.get('claim_language', 'do not claim plugin application without verification')}.",
            *([f"- manual instruction: {plugin.get('manual_logic_instruction')}"] if plugin.get("manual_logic_instruction") else []),
            *([f"- fallback: {plugin.get('fallback')} only; do not call it Decapitator."] if plugin.get("fallback") else []),
            "- Keep user voice identity; do not clone 2hollis, Nate Sib, ycs, or any artist voice.",
            "",
            "### D. Rap-Forward Vocal",
            "- Keep vocal dry and upfront.",
            "- Use less reverb.",
            "- Use delay throws at phrase endings.",
            "- Compress enough for consistency but avoid lifeless flattening.",
            "",
            "### E. Hyperpop / Digicore Vocal",
            "- Use brighter presence carefully.",
            "- Use tuning/formant effects only if requested.",
            "- Make adlibs wider than lead.",
            "- Keep lead intelligible.",
            "- Avoid harsh sibilance.",
            "",
            "### F. Adlibs / Backings",
            "- Lower than lead.",
            "- Wider than lead.",
            "- More reverb/delay than lead.",
            "- High-pass more aggressively if muddy.",
            "- Do not mask the hook.",
            "",
            "### G. Beat vs Vocal Balance",
            "- Lower beat slightly where vocal enters if needed.",
            "- Use automation around hooks.",
            "- Prevent 808 from masking low vocal body.",
            "- Prevent synth leads from fighting vocal presence.",
            "",
            "### H. Reference-Inspired Drum Direction",
            reference_note,
            "- Do not copy exact drum patterns from the reference.",
            "- If only stereo beat exists, use broad treatment or manual layering.",
            "- If stems/MIDI exist, adjust kick/snare/hat/808 programming more directly.",
            "",
            "### I. Pre-Master",
            "- Check vocal intelligibility at low volume.",
            "- Check sibilance on headphones.",
            "- Check 808 on small speakers and sub-capable speakers.",
            "- Leave headroom.",
            "- Export with normalize off.",
        ]
    )


def suggested_total_duration(analysis: dict[str, Any], options: dict[str, Any]) -> str:
    duration = analysis.get("metadata", {}).get("duration_seconds", 0.0)
    brief_length = (options.get("creative_brief") or {}).get("length", {})
    length_mode = brief_length.get("mode") or options.get("length_mode", "under_2min")
    if length_mode == "15sec_reels":
        return "15 seconds, centered on the strongest hook/motif candidate"
    if length_mode == "keep_original":
        return f"keep original length if arrangement holds attention ({duration:.2f}s analyzed)"
    if length_mode in {"specific_section", "specific_section_only"}:
        start = brief_length.get("start")
        end = brief_length.get("end")
        if start or end:
            return f"specific section only: {start or 'start not provided'} to {end or 'end not provided'}"
        return "specific section only; choose the strongest hook/motif window from the analysis"
    if length_mode == "30sec_short_form":
        return "30 seconds, built around the strongest hook/motif and a clean ending"
    return "under 2 minutes, with the strongest melodic identity arriving early"


def build_edit_plan(analysis: dict[str, Any], options: dict[str, Any], reference_profile: dict[str, Any] | None = None) -> str:
    arrangement = analysis.get("arrangement_candidates", {})
    silence = analysis.get("silence_detection", {})
    hook = arrangement.get("first_hook_or_main_motif_entrance")
    intro = silence.get("intro_silence") or arrangement.get("intro")
    glitch_candidates = arrangement.get("ai_random_transition_or_glitch_candidates", [])
    repeated_blocks = arrangement.get("repeated_loop_blocks", [])
    vocal_candidates = analysis.get("vocal_like_texture_candidates", [])
    melody_buried = analysis.get("melody_buried_candidates", [])
    low_end = analysis.get("low_end_excess_candidates", [])
    strongest = arrangement.get("main_melody_strongest_region") or hook

    sections = [
        "## 1. Project Objective",
        "",
        "Preserve the Suno-generated main melody and emotional atmosphere while reducing AI-generated artifacts, random transitions, fake vocal textures, and generic loop behavior. The target is a cleaner instrumental beat that feels arranged, mixed, and edited by a human producer. Writing this plan does not mean the beat has already been humanized; it is a guide until actual editing, processing, export, and verification happen.",
        "",
        "## 2. User Settings",
        "",
        user_settings_text(options),
        "",
        creative_brief_summary_section(options),
        "",
        "## 3. Arrangement Plan",
        "",
        f"- Recommended intro cut: {region_label(intro)}. If the intro feels empty or AI-smudged, tighten it so the motif arrives immediately.",
        f"- Recommended hook entrance time: {region_label(hook)}.",
        f"- Recommended total duration: {suggested_total_duration(analysis, options)}.",
        "- Suggested 4-bar / 8-bar structure:",
        structure_text(),
        "- Add variation at 0:48 and 1:04 with drum mutes, small melody filter movement, altered 808 rhythm, or a counter texture.",
        "- Crossfade abrupt transitions at these heuristic candidates:",
        list_regions(glitch_candidates, "No strong abrupt transition candidates; still audition all section changes."),
        "- Remove or reduce random FX / risers / glitch fills at these candidates:",
        list_regions(glitch_candidates, "No random FX/glitch timestamp candidates detected."),
        "- Review repeated loop blocks and add human-feeling edits instead of letting the same printed loop repeat unchanged:",
        list_regions(repeated_blocks, "No repeated loop candidates detected; use the default structure if section detection is weak."),
        "- If no section detection feels musically convincing, use the default arrangement: keep the strongest melodic section early, target under 2 minutes, and follow the 0:00 to 1:52 structure above.",
        "",
        reference_target_section(reference_profile, options) if reference_profile else "",
        "",
        korean_request_translation_section(reference_profile, options) if reference_profile else "",
        "",
        commercial_digicore_autopilot_section(reference_profile, options) if reference_profile else "",
        "",
        reference_application_logic_section(reference_profile, options) if reference_profile else "",
        "",
        bass_808_reference_plan(reference_profile, options) if reference_profile else "",
        "",
        synth_width_reference_plan(reference_profile, options) if reference_profile else "",
        "",
        drum_reference_plan(reference_profile) if reference_profile else "",
        "",
        stereo_only_limitation_section(options),
        "",
        drum_programming_section(reference_profile) if reference_profile else "",
        "",
        "## 4. Melody-Forward Mix Plan",
        "",
        f"- Protect the main melody first. Strongest heuristic melody region: {region_label(strongest)}.",
        "- Keep piano / sample / synth / pluck elements in front and automate them up 0.5-1.5 dB where the hook needs emotional focus.",
        "- Reduce mud around 200-500 Hz if the melody feels cloudy or the printed Suno mix has low-mid smear.",
        "- Control harsh 2 kHz-6 kHz edges with narrow EQ or dynamic EQ, but do not bury the lead.",
        "- Do not let vocal chops or fake voice-like textures become the lead unless the user explicitly wants that.",
        "- Use volume automation where melody-buried candidates appear:",
        list_regions(melody_buried, "No melody-buried timestamps detected; still check low-volume playback manually."),
        "",
        "## 5. Vocal Chop / AI Texture Suppression Plan",
        "",
        "- These are heuristic candidates, not confirmed vocals. Audition before cutting.",
        "- Lower vocal-like texture level where detected, especially if it sounds like fake human chops or voice-styled lead texture.",
        "- EQ high-mid vocal bands around 300 Hz-3 kHz only as much as needed; avoid destroying the original atmosphere.",
        "- De-emphasize fake voice textures with clip gain, automation, narrow EQ, or short mutes into crossfades.",
        "- Candidate timestamps:",
        list_regions(vocal_candidates, "No vocal-like texture candidates detected by heuristic analysis."),
        "",
        "## 6. Drum / 808 Plan",
        "",
        "- Kick and 808 should be strong but controlled. They must support the melody, not flatten it.",
        "- Reduce excessive sub buildup in these heuristic sections:",
        list_regions(low_end, "No strong low-end excess timestamps detected."),
        "- Avoid cheap trap loop feel: add small 808 rhythm changes, one-bar breath moments, and subtle kick variation every 8 or 16 bars.",
        "- Avoid rage-style clipping unless intentionally selected later. This workflow should leave headroom.",
        "- Use gentle sidechain or volume automation when kick/808 masks the melody.",
        "- Add 808 variation into second hook or final hook: slide into the downbeat, omit one sub note before a drop, or simplify under exposed melody.",
        "",
        "## 7. AI-Feel Reduction Plan",
        "",
        "- Reduce random glitch fills and risers that do not introduce or resolve a section.",
        "- Smooth strange transitions with short crossfades, pre-drop mutes, reverse tails, or filtered delays.",
        "- Add subtle human-like arrangement variation: hat mute, drum fill restraint, melody filter movement, reverb send movement, and 808 note changes.",
        "- Remove meaningless repeated blocks or turn them into call-and-response changes.",
        "- Abrupt/random transition candidates:",
        list_regions(glitch_candidates, "No abrupt transition candidates detected; still listen through all section boundaries."),
        "",
        "## 8. Sound Polish Plan",
        "",
        "- EQ: clean low-mid mud, high-pass non-bass textures, and carve space for the main melody.",
        "- Light compression: use leveling, not flattening. Keep transients alive.",
        "- Gentle saturation: add warmth or phone translation, not harsh low-end distortion.",
        "- Limiter only at the final stage. Do not use limiting to fix arrangement or mix balance.",
        "- Leave headroom. Avoid loudness-war mastering.",
        "- Target peak around -1.0 dBTP or safer in the final verified export stage.",
        "",
        "## 9. Logic Pro Manual Checklist",
        "",
        "1. Create a new Logic Pro project.",
        "2. Import `04_PROCESSED_AUDIO/working_input.wav`.",
        "3. Set the project sample rate to match the selected export format.",
        "4. Cut or tighten the intro using the recommended intro cut.",
        "5. Arrange sections around immediate motif, partial drop, main groove, hook, variation, second hook, breakdown, final hook, and clean outro.",
        "6. Add crossfades at abrupt transition candidates.",
        "7. Apply EQ to reduce mud and protect the lead melody.",
        "8. Apply light compression for control, not loudness-war density.",
        "9. Balance drum/808 against the melody; check low-volume playback.",
        "10. Suppress vocal-like parts at the candidate timestamps if they distract from the instrumental lead.",
        "11. Add automation: melody lift, drum mutes, reverb send moves, filter movement, and 808 changes.",
        "12. Export WAV only after the edit feels musically intentional.",
        "13. Verify the exported file exists, has the expected metadata, and does not clip.",
        "",
        logic_vocal_mix_checklist(reference_profile, options) if vocal_mode_active(options) else "",
        "",
        "## 10. Fallback Processing Notes",
        "",
        "- The non-Logic pipeline can trim, fade, gain-stage, apply basic EQ where available, and verify output metadata.",
        "- It can help prepare a cleaner stereo guide and make simple reel-friendly edits.",
        "- It cannot truly remix stems from a single stereo file unless stem separation is added.",
        "- It cannot make musical arrangement judgments by itself; use the plan as a guide and audition every suggested timestamp.",
    ]
    return "\n".join(sections) + "\n"


def render_template(body: str, template_path: Path = TEMPLATE_PATH) -> str:
    if not template_path.exists():
        return body
    template = template_path.read_text(encoding="utf-8")
    return template.replace("{{ body }}", body)


def write_edit_plan(
    analysis_path: Path = ANALYSIS_PATH,
    output_path: Path = EDIT_PLAN_PATH,
    options: dict[str, Any] | None = None,
    reference_profile_path: Path = REFERENCE_PROFILE_PATH,
) -> Path:
    analysis = load_analysis(analysis_path)
    resolved_options = options or load_defaults()
    body = build_edit_plan(analysis, resolved_options, load_reference_profile(reference_profile_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_template(body), encoding="utf-8")
    return output_path


def main() -> int:
    output = write_edit_plan()
    print(f"Wrote edit plan: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
