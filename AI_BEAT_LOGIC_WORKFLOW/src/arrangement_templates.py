from __future__ import annotations

from typing import Any


LENGTH_MODES = {"reels_15sec", "short_30sec", "under_2min", "full_song"}
GENRE_MODES = {
    "hip_hop",
    "hyperpop",
    "digicore",
    "internet_underground",
    "system_seoul_adjacent",
    "commercial_digicore_hyperpop",
}


def normalize_length_mode(value: str | None) -> str:
    aliases = {
        "15sec_reels": "reels_15sec",
        "reels": "reels_15sec",
        "30sec_short_form": "short_30sec",
        "short": "short_30sec",
        "keep_original": "full_song",
        "under 2 minutes": "under_2min",
    }
    key = (value or "under_2min").strip().lower().replace("-", "_").replace(" ", "_")
    return aliases.get(key, key if key in LENGTH_MODES else "under_2min")


def normalize_genre_mode(value: str | None) -> str:
    key = (value or "digicore").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "hiphop": "hip_hop",
        "system_seoul": "system_seoul_adjacent",
        "system_seoul_adjacent": "system_seoul_adjacent",
        "commercial_digicore": "commercial_digicore_hyperpop",
    }
    return aliases.get(key, key if key in GENRE_MODES else "digicore")


def arrangement_template(length_mode: str, genre_mode: str) -> dict[str, Any]:
    length = normalize_length_mode(length_mode)
    genre = normalize_genre_mode(genre_mode)
    templates: dict[str, list[dict[str, Any]]] = {
        "reels_15sec": [
            {"name": "hook", "start": 0.0, "end": 8.0, "purpose": "immediate motif/rhythm identity"},
            {"name": "variation", "start": 8.0, "end": 13.5, "purpose": "micro switch-up or fill"},
            {"name": "cut_or_loop", "start": 13.5, "end": 15.0, "purpose": "clean ending or loop point"},
        ],
        "short_30sec": [
            {"name": "motif_seed", "start": 0.0, "end": 4.0, "purpose": "recognizable motif within four seconds"},
            {"name": "hook_drop", "start": 4.0, "end": 12.0, "purpose": "hook/drop arrival"},
            {"name": "development", "start": 12.0, "end": 22.0, "purpose": "controlled development"},
            {"name": "final_variation", "start": 22.0, "end": 30.0, "purpose": "variation and clean ending"},
        ],
        "under_2min": [
            {"name": "intro", "start": 0.0, "end": 8.0, "purpose": "short identity setup"},
            {"name": "hook_drop", "start": 8.0, "end": 32.0, "purpose": "early hook/drop"},
            {"name": "verse", "start": 32.0, "end": 56.0, "purpose": "space for vocal or main idea"},
            {"name": "contrast", "start": 56.0, "end": 72.0, "purpose": "breakdown, mute, or texture contrast"},
            {"name": "final_hook", "start": 72.0, "end": 104.0, "purpose": "return with variation"},
            {"name": "outro", "start": 104.0, "end": 116.0, "purpose": "clean outro or hard stop"},
        ],
        "full_song": [
            {"name": "intro", "start": 0.0, "end": 12.0, "purpose": "signature texture"},
            {"name": "hook", "start": 12.0, "end": 36.0, "purpose": "early hook statement"},
            {"name": "verse", "start": 36.0, "end": 68.0, "purpose": "main vocal/arrangement body"},
            {"name": "pre", "start": 68.0, "end": 84.0, "purpose": "lift into hook"},
            {"name": "hook", "start": 84.0, "end": 116.0, "purpose": "main hook"},
            {"name": "bridge", "start": 116.0, "end": 140.0, "purpose": "contrast"},
            {"name": "final_hook", "start": 140.0, "end": 176.0, "purpose": "final hook variation"},
            {"name": "outro", "start": 176.0, "end": 188.0, "purpose": "controlled finish"},
        ],
    }
    return {
        "length_mode": length,
        "genre_mode": genre,
        "sections": templates[length],
        "global_rules": _global_rules(length, genre),
    }


def _global_rules(length_mode: str, genre_mode: str) -> list[str]:
    rules = [
        "Avoid exact protected song, melody, drum pattern, bassline, lyric, or sound recording copying.",
        "Avoid random AI glitch; every fill/mute/variation needs an arrangement purpose.",
        "Keep sub/808 mono and use width only above the low end.",
    ]
    if length_mode == "reels_15sec":
        rules.extend(["Hook or motif must arrive immediately.", "No weak intro.", "End on a clean cut or loop point."])
    elif length_mode == "short_30sec":
        rules.extend(["Motif within four seconds.", "Hook/drop by eight to twelve seconds.", "Final variation by twenty to twenty-eight seconds."])
    elif length_mode == "under_2min":
        rules.extend(["Intro must be zero to eight seconds unless user asks otherwise.", "Use four to eight bar variation.", "Include one breakdown or contrast section."])
    else:
        rules.extend(["Use intro/hook/verse/pre/hook/bridge/final hook/outro shape.", "Longer form must still avoid AI loop repetition."])
    if genre_mode in {"hyperpop", "digicore", "commercial_digicore_hyperpop"}:
        rules.append("Prioritize bright digital hook identity with controlled low-end and disciplined clipping.")
    if genre_mode == "hip_hop":
        rules.append("Pocket and vocal space are more important than constant density.")
    return rules
