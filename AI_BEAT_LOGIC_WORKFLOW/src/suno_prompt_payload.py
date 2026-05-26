from __future__ import annotations

import json
from pathlib import Path


SUNO_STYLE_PROMPT = (
    "180 BPM fast melodic digicore hyperpop commercial short-form track. Clean modern pop mix, "
    "immediate musical hook within 2 seconds, no long intro. Controlled genre blend: digicore, "
    "hyperpop, emo rap, trap, future bass, jersey club bounce, electropop, pop-punk energy. "
    "Instrumental sample-flip feel from resampled synth riffs, sliced plucks, tight drum edits, "
    "reversed synth tails, clean digital fills, sparkling arps, and tight 808 bounce. Male lead "
    "vocal is the main vocal: centered, upfront, low-mid register, clean, bright, emotionally "
    "autotuned, intelligible, catchy topline. Female vocals only as sparse backing adlibs, "
    "doubles, and harmony tails, low volume, wide stereo, never lead, never verse, never main "
    "hook. Polished human arrangement, smooth transitions, controlled dynamics, punchy drums, "
    "clean low-end, loud but not crushed, aggressive but not noisy, commercial not demo-like."
)

SUNO_EXCLUDE_PROMPT = (
    "female lead vocal, female verse, female hook, loud female vocal, girl main voice, random "
    "female adlib, random ahh, random ooh, random yeah, moaning vocal, vocal chop intro, "
    "chopped vocal hook, pitched-up vocal, chipmunk vocal, anime voice, baby voice, hard vocal "
    "splice, abrupt vocal cut, sudden AI cutoff, random glitch noise, harsh white noise, noisy "
    "wall of sound, excessive bitcrush, unmusical stutter, phasey stereo, anti-phase widening, "
    "muddy bass, buried male vocal, muffled vocal, over-compression, clipping, long ambient "
    "intro, slow buildup, weak hook, random chord drift, generic AI demo, amateur demo"
)

SUNO_RECOMMENDED_SETTINGS = {
    "custom_mode": True,
    "instrumental": False,
    "vocal_gender": "Male",
    "weirdness_percent": "10-14",
    "style_influence_percent": "82-86",
    "audio_influence_percent": "0-20 unless using a clean instrumental reference only",
    "vocal_reference_audio": "do not use if female/random vocal artifacts are the problem",
}


def suno_prompt_payload() -> dict[str, object]:
    return {
        "style_prompt": SUNO_STYLE_PROMPT,
        "exclude_prompt": SUNO_EXCLUDE_PROMPT,
        "recommended_settings": SUNO_RECOMMENDED_SETTINGS,
        "source_rule": "Use Suno Studio WAV stems and stem-derived MIDI for production. MP3/final/master files are reference_only.",
    }


def write_suno_prompt_payload_reports(report_dir: str | Path) -> dict[str, Path]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    payload = suno_prompt_payload()

    json_path = report_path / "suno_prompt_payload.json"
    style_path = report_path / "suno_style_prompt.txt"
    exclude_path = report_path / "suno_exclude_prompt.txt"
    settings_path = report_path / "suno_generation_settings.md"
    export_plan_path = report_path / "studio_export_plan.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    style_path.write_text(SUNO_STYLE_PROMPT + "\n", encoding="utf-8")
    exclude_path.write_text(SUNO_EXCLUDE_PROMPT + "\n", encoding="utf-8")
    settings_path.write_text(
        "\n".join(
            [
                "# Suno Generation Settings",
                "",
                "- Custom Mode: ON",
                "- Instrumental: OFF",
                "- Vocal Gender: Male",
                "- Weirdness: 10-14%",
                "- Style Influence: 82-86%",
                "- Audio Influence: 0-20% unless using a clean instrumental reference only",
                "- Do not use vocal reference audio if female/random vocal artifacts are the problem.",
                "- Reject generations where female vocals become lead, verse, or main hook.",
                "- Treat Suno as idea/stem/MIDI generation, not as a finished master.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    export_plan_path.write_text(
        "\n".join(
            [
                "# Suno Studio Export Plan",
                "",
                "Export these before rebuilding in REAPER:",
                "",
                "- Full mix reference WAV if available",
                "- 12-track WAV stems",
                "- Vocals stem",
                "- Instrumental stem",
                "- Drums stem",
                "- Bass/808 stem",
                "- Music/synth stem",
                "- FX stem",
                "- Female BGV/adlib stem if available",
                "- MIDI from each useful stem",
                "- Tempo-locked WAV if available",
                "",
                "Warnings:",
                "",
                "- Do not use MP3 master as production source.",
                "- Do not rely on vocal-chop-heavy generations.",
                "- If female vocals appear as lead or random hooks, reject that Suno generation.",
                "- Use lower Weirdness for commercial quality.",
                "- Export stems before REAPER rebuild.",
                "- Manual Suno Studio export is required; do not automate login, CAPTCHA, credit spending, or protected UI actions.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "payload": json_path,
        "style_prompt": style_path,
        "exclude_prompt": exclude_path,
        "settings": settings_path,
        "export_plan": export_plan_path,
    }
