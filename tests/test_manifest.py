from pathlib import Path

from tools.schemas import AUDIO_EXTENSIONS, classify_stem, discover_assets


def test_audio_extensions_cover_requested_formats():
    assert {".wav", ".aiff", ".aif", ".flac", ".mp3", ".m4a"}.issubset(AUDIO_EXTENSIONS)


def test_discover_assets_writes_conservative_roles(tmp_path: Path):
    stems = tmp_path / "input" / "stems"
    refs = tmp_path / "input" / "reference"
    stems.mkdir(parents=True)
    refs.mkdir(parents=True)
    (stems / "male_lead_vocal.wav").write_bytes(b"stem")
    (stems / "mystery_texture.wav").write_bytes(b"stem")
    (refs / "full_mix_reference.mp3").write_bytes(b"ref")

    manifest = discover_assets(tmp_path)

    roles = {asset["filename"]: asset["classification"] for asset in manifest["stems"]}
    assert roles["male_lead_vocal.wav"] == "MALE_NONHOOK_CENTER"
    assert roles["mystery_texture.wav"] == "UNKNOWN"
    assert manifest["reference_count"] == 1
    assert manifest["unknown_stem_count"] == 1
    assert manifest["source_manifest_hash"]


def test_classifier_is_conservative_for_ambiguous_female_stem():
    assert classify_stem("female_hook.wav") == "UNKNOWN"
