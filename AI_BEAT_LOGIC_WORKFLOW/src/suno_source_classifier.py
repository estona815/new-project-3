from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REFERENCE_ONLY = "reference_only"
TECHNICAL_MIX_REFERENCE = "technical_mix_reference"
PROBLEM_REFERENCE = "problem_reference"
DRUMS = "drums"
BASS_OR_808 = "bass_or_808"
MALE_LEAD_VOCAL = "male_lead_vocal"
FEMALE_BGV = "female_bgv"
MUSIC_OR_SYNTH = "music_or_synth"
FX = "fx"
VOCAL_ARTIFACT_QUARANTINE = "vocal_artifact_quarantine"
GUIDE_MIDI = "guide_midi"
UNCERTAIN = "uncertain"

PRODUCTION_AUDIO_CATEGORIES = {
    DRUMS,
    BASS_OR_808,
    MALE_LEAD_VOCAL,
    FEMALE_BGV,
    MUSIC_OR_SYNTH,
    FX,
}

REFERENCE_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg"}
MIDI_EXTENSIONS = {".mid", ".midi"}
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a"}
ARCHIVE_EXTENSIONS = {".zip"}


@dataclass(frozen=True)
class ClassifiedSource:
    path: str
    name: str
    extension: str
    category: str
    reason: str
    reference_only: bool
    production_eligible: bool
    guide_only: bool
    quarantine: bool


def normalized_name(path_or_name: str | Path) -> str:
    path = Path(path_or_name)
    text = unicodedata.normalize("NFC", f"{path.parent.name} {path.stem} {path.suffix}".lower())
    text = re.sub(r"[_./\\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_word(text: str, *words: str) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text) for word in words)


def classify_source_file(path: str | Path) -> ClassifiedSource:
    source = Path(path)
    text = normalized_name(source)
    extension = source.suffix.lower()

    category = MUSIC_OR_SYNTH
    reason = "default wav/aiff/flac production music source"

    if extension in MIDI_EXTENSIONS:
        category = GUIDE_MIDI
        reason = "Suno MIDI is treated as guide-only and never final truth"
    elif _has(
        text,
        "estona",
        "nib",
        "lovee",
        "technical reference",
        "technical mix reference",
        "reference wav",
        "dongbanjasal",
        "동반자살",
        "발매곡",
        "완성본",
    ):
        category = TECHNICAL_MIX_REFERENCE
        reason = "commercial mix reference for technical analysis only"
    elif extension in REFERENCE_EXTENSIONS or _has(
        text,
        "hangang shadow",
        "current master",
        "problem master",
        "problem reference",
        "master 320k",
        "320k mp3",
    ):
        category = PROBLEM_REFERENCE
        reason = "current/problem master or mp3-like source is analysis-only"
    elif extension in REFERENCE_EXTENSIONS or _has(
        text,
        "master",
        "full mix",
        "fullmix",
        "mixdown",
        "320k",
        "final",
        "reference",
        "ref ",
        " ref",
    ):
        category = REFERENCE_ONLY
        reason = "master/fullmix/final/mp3-like source is reference-only"
    elif extension in ARCHIVE_EXTENSIONS:
        category = UNCERTAIN
        reason = "archive must be safely unpacked and classified by contained files"
    elif _has(
        text,
        "vocal chop",
        "vox chop",
        "voxchop",
        "chopped vocal",
        "chop vocal",
        "ahh",
        "aah",
        "ooh",
        "yeah",
        "yea",
        "moan",
        "moaning",
        "weird vocal",
        "random vocal",
        "random vox",
        "random adlib",
        "random female",
        "hard vocal splice",
        "abrupt vocal",
        "chipmunk",
        "anime voice",
        "baby voice",
        "female lead",
        "female verse",
        "female hook",
        "girl main",
        "loud female",
    ):
        category = VOCAL_ARTIFACT_QUARANTINE
        reason = "filename suggests random vocal chop/adlib/splice artifact"
    elif _has(text, "external female", "external female v20 stems") and _has(text, "instrumental"):
        category = REFERENCE_ONLY
        reason = "external separation companion instrumental is reference-only to avoid duplicating raw Suno stems"
    elif _has(text, "instrumental"):
        category = MUSIC_OR_SYNTH
        reason = "instrumental/music source"
    elif _has(text, "female", "bgv", "backing", "harmony", "double", "adlib"):
        category = FEMALE_BGV
        reason = "female/backing/adlib/double material is backing support only"
    elif _has(text, "male", "lead vocal", "main vocal", "vox lead") or (
        _has_word(text, "vocals", "vocal", "vox") and not _has(text, "backing")
    ):
        category = MALE_LEAD_VOCAL
        reason = "lead/main vocal source"
    elif _has(text, "kick", "snare", "hat", "hats", "drum", "drums", "percussion"):
        category = DRUMS
        reason = "drum/percussion source"
    elif _has(text, "bass", "808", "sub"):
        category = BASS_OR_808
        reason = "bass/808/sub source"
    elif _has(text, "riser", "impact", "sweep", "noise", "transition", "fx"):
        category = FX
        reason = "transition/fx/noise source"
    elif _has(text, "synth", "music", "keys", "keyboard", "pluck", "arp", "chord", "lead", "guitar", "strings", "brass", "woodwinds"):
        category = MUSIC_OR_SYNTH
        reason = "music/synth/harmonic source"

    reference_only = category in {REFERENCE_ONLY, TECHNICAL_MIX_REFERENCE, PROBLEM_REFERENCE}
    guide_only = category == GUIDE_MIDI
    quarantine = category == VOCAL_ARTIFACT_QUARANTINE
    production_eligible = category in PRODUCTION_AUDIO_CATEGORIES and extension in AUDIO_EXTENSIONS
    return ClassifiedSource(
        path=str(source),
        name=source.name,
        extension=extension,
        category=category,
        reason=reason,
        reference_only=reference_only,
        production_eligible=production_eligible,
        guide_only=guide_only,
        quarantine=quarantine,
    )


def classify_sources(paths: Iterable[str | Path]) -> list[ClassifiedSource]:
    return [classify_source_file(path) for path in sorted(paths, key=lambda item: str(item).lower())]


def production_rebuild_status(classified: Iterable[ClassifiedSource]) -> dict[str, object]:
    items = list(classified)
    production_count = sum(1 for item in items if item.production_eligible)
    reference_count = sum(1 for item in items if item.reference_only)
    technical_reference_count = sum(1 for item in items if item.category == TECHNICAL_MIX_REFERENCE)
    problem_reference_count = sum(1 for item in items if item.category == PROBLEM_REFERENCE)
    guide_midi_count = sum(1 for item in items if item.guide_only)
    quarantine_count = sum(1 for item in items if item.quarantine)
    blocked = production_count == 0
    reason = ""
    if blocked:
        reason = "Only reference/master files found. Export Suno Studio WAV stems and stem-derived MIDI before rebuilding."
    return {
        "allowed": not blocked,
        "reason": reason,
        "production_audio_count": production_count,
        "reference_only_count": reference_count,
        "technical_mix_reference_count": technical_reference_count,
        "problem_reference_count": problem_reference_count,
        "guide_midi_count": guide_midi_count,
        "quarantine_count": quarantine_count,
    }


def write_source_classification_report(classified: Iterable[ClassifiedSource], report_dir: str | Path) -> dict[str, Path]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    items = list(classified)
    status = production_rebuild_status(items)
    payload = {
        "status": status,
        "sources": [asdict(item) for item in items],
    }
    json_path = report_path / "source_classification.json"
    md_path = report_path / "source_classification.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Source Classification",
        "",
        f"- Production rebuild allowed: {str(status['allowed']).lower()}",
        f"- Production audio files: {status['production_audio_count']}",
        f"- Reference-only files: {status['reference_only_count']}",
        f"- Technical mix references: {status['technical_mix_reference_count']}",
        f"- Problem references: {status['problem_reference_count']}",
        f"- Guide MIDI files: {status['guide_midi_count']}",
        f"- Quarantined files: {status['quarantine_count']}",
    ]
    if status["reason"]:
        lines.append(f"- Block reason: {status['reason']}")
    lines.extend(
        [
            "",
            "| file | category | production | muted/quarantine reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in items:
        lines.append(
            f"| {item.name} | {item.category} | {str(item.production_eligible).lower()} | {item.reason} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}
