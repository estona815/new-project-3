from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import load_defaults
from paths import PROJECT_ROOT


ANALYSIS_PATH = PROJECT_ROOT / "01_ANALYSIS" / "analysis.json"
EDIT_PLAN_PATH = PROJECT_ROOT / "02_EDIT_PLAN" / "edit_plan.md"
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "edit_plan_template.md"


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
    return "\n".join(
        [
            f"- final length: {options.get('length_mode', 'under_2min')}",
            f"- vocal suppression setting: {options.get('vocal_mode', 'suppress')}",
            f"- melody focus: {options.get('melody_focus', 'front')}",
            f"- drum/808 strength: {options.get('drum_808', 'strong_controlled')}",
            f"- export format: {options.get('export_format', 'wav24_48k')}",
            f"- Logic project save preference: {str(options.get('save_logic_project', True)).lower()}",
        ]
    )


def structure_text() -> str:
    return "\n".join(f"- {time}: {label}" for time, label in DEFAULT_STRUCTURE)


def suggested_total_duration(analysis: dict[str, Any], options: dict[str, Any]) -> str:
    duration = analysis.get("metadata", {}).get("duration_seconds", 0.0)
    length_mode = options.get("length_mode", "under_2min")
    if length_mode == "15sec_reels":
        return "15 seconds, centered on the strongest hook/motif candidate"
    if length_mode == "keep_original":
        return f"keep original length if arrangement holds attention ({duration:.2f}s analyzed)"
    if length_mode == "specific_section_only":
        return "specific section only; choose the strongest hook/motif window from the analysis"
    return "under 2 minutes, with the strongest melodic identity arriving early"


def build_edit_plan(analysis: dict[str, Any], options: dict[str, Any]) -> str:
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
) -> Path:
    analysis = load_analysis(analysis_path)
    resolved_options = options or load_defaults()
    body = build_edit_plan(analysis, resolved_options)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_template(body), encoding="utf-8")
    return output_path


def main() -> int:
    output = write_edit_plan()
    print(f"Wrote edit plan: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

