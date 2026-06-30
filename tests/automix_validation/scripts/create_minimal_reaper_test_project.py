#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "tests" / "automix_validation" / "fixtures" / "mock_projects"
AUDIO = ROOT / "tests" / "automix_validation" / "fixtures" / "audio"


def media(name: str) -> list[dict]:
    return [{"path": str(Path("..") / "audio" / name), "start": 0.0, "length": 10.0}]


PROJECTS = {
    "prompt41_scan_only_test.json": [
        {"name": "Lead Vocal Raw", "role": "lead_vocal", "media_items": media("raw_vocal_like_mono.wav"), "fx": []},
        {"name": "Lead Vocal AI Tuned", "role": "lead_vocal", "media_items": media("already_tuned_ai_like_vocal.wav"), "fx": []},
        {"name": "Watery Separated Vocal", "role": "lead_vocal", "media_items": media("source_separated_watery_vocal.wav"), "fx": []},
        {"name": "Instrumental Bus", "role": "instrumental_bus", "media_items": media("clean_instrumental_bus.wav"), "fx": []},
        {"name": "Full Mix Reference", "role": "reference", "media_items": media("full_mix_dense_polyphonic.wav"), "fx": []},
        {"name": "Master", "role": "master", "media_items": [], "fx": []},
    ],
    "prompt41_safe_draft_test.json": [
        {"name": "Lead Vocal Raw", "role": "lead_vocal", "media_items": media("raw_vocal_like_mono.wav"), "fx": []},
        {"name": "Lead Vocal AI Tuned", "role": "lead_vocal", "media_items": media("already_tuned_ai_like_vocal.wav"), "fx": []},
        {"name": "Backing Vox", "role": "backing_vocal", "media_items": media("fragile_thin_ai_vocal.wav"), "fx": []},
        {"name": "Instrumental Bus", "role": "instrumental_bus", "media_items": media("clean_instrumental_bus.wav"), "fx": []},
        {"name": "Reverb Send", "role": "send", "media_items": [], "fx": []},
        {"name": "Master", "role": "master", "media_items": [], "fx": []},
    ],
    "prompt41_full_mix_block_test.json": [
        {"name": "Full Mix Only", "role": "full_mix", "media_items": media("full_mix_dense_polyphonic.wav"), "fx": []},
        {"name": "Master", "role": "master", "media_items": [], "fx": []},
    ],
    "prompt41_export_block_test.json": [
        {"name": "Accepted Premaster Draft mock", "role": "premaster_draft", "accepted": True, "media_items": media("full_mix_dense_polyphonic.wav"), "fx": []},
        {"name": "Rejected Premaster Draft mock", "role": "premaster_draft", "accepted": False, "rejected": True, "media_items": media("vocal_buried_mix.wav"), "fx": []},
        {"name": "Master", "role": "master", "media_items": [], "fx": []},
    ],
}


def generate() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, tracks in PROJECTS.items():
        data = {
            "schema": "prompt41-mock-reaper-project-v1",
            "project_name": filename.removesuffix(".json"),
            "reaper_version": "mock",
            "no_external_plugins_required": True,
            "no_user_audio_references": True,
            "tracks": [
                {"track_index": idx + 1, **track}
                for idx, track in enumerate(tracks)
            ],
            "warnings": ["mock_project_metadata_no_reaper_runtime"],
        }
        path = OUT / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(str(path))
    return {"schema": "prompt41-mock-project-manifest-v1", "projects": paths}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
