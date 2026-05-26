from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from pass02_commercial_balance_reports import (
    PASS02_MASTER,
    REPORTS,
    RENDERS,
    ROOT,
    TECH_REF,
    analyze_wav,
    band_profile,
    metric_table,
    profile_table,
    track_level_table,
    write,
)
from fresh_mix_pass01_reports import parse_tracks, validation_summary


REAPER = ROOT / "reaper"
PASS03_RPP = REAPER / "FRESH_MIX_MASTER_PASS_03_BEAT_FORWARD_LOUD.rpp"
PASS04_RPP = REAPER / "FRESH_MIX_MASTER_PASS_04_SUNO_000000_ALL_INFO.rpp"
PASS03_MASTER = RENDERS / "PASS03_MASTER_BEAT_FORWARD_LOUD_24bit_48k.wav"
PASS04_PREMASTER = RENDERS / "PASS04_PREMASTER_ALL_INFO_24bit_48k.wav"
PASS04_MASTER = RENDERS / "PASS04_MASTER_ALL_INFO_LOUD_24bit_48k.wav"
PASS04_MP3 = RENDERS / "PASS04_MASTER_ALL_INFO_LOUD_320k.mp3"
SUNO_DIR = ROOT / "downloads" / "suno_pass04"
SUNO_ZIP = SUNO_DIR / "pass04_000000_voice_male_lead_A_all_detected_stems.zip"
SUNO_STEMS = SUNO_DIR / "stems"
SUNO_LINKS = [
    "https://suno.com/song/6da5749b-9e26-49d3-a4cc-0eb738891537",
    "https://suno.com/song/0ed0460d-42dc-42e9-b29d-33ee30a366d8",
]


def stem_paths() -> list[Path]:
    return [
        SUNO_STEMS / "0 Lead Vocals.wav",
        SUNO_STEMS / "1 Drums.wav",
        SUNO_STEMS / "2 Bass.wav",
        SUNO_STEMS / "3 Synth.wav",
        SUNO_STEMS / "4 Other.wav",
    ]


def pass04_validation() -> tuple[list[str], list[str]]:
    tracks = parse_tracks(PASS04_RPP)
    failures, notes = validation_summary(tracks)
    by_name = {t.name: t for t in tracks}
    for name in [
        "SUNO_000000_CANDIDATE_BUS",
        "SUNO000000 CANDIDATE - Lead Vocals",
        "SUNO000000 CANDIDATE - Drums",
        "SUNO000000 CANDIDATE - Bass",
        "SUNO000000 CANDIDATE - Synth",
        "SUNO000000 CANDIDATE - Other",
    ]:
        t = by_name.get(name)
        if not t:
            failures.append(f"{name} was not imported")
        elif not t.mute:
            failures.append(f"{name} must remain muted for PASS04 render")
    if not failures:
        notes.append("PASS04 validation passed: references, quarantine, guide MIDI, and Suno 000000 candidate tracks are muted.")
    return failures, notes


def make_mp3_note() -> str:
    if PASS04_MP3.exists():
        return f"MP3 exists: {PASS04_MP3}"
    if shutil.which("ffmpeg") or shutil.which("lame"):
        return "MP3 encoder appears available, but PASS04 script did not create MP3 automatically."
    return "MP3 preview skipped: ffmpeg/lame unavailable in this shell; WAV master is the verified render."


def main() -> int:
    now = datetime.now().isoformat(timespec="seconds")
    stem_metrics = {p.name: analyze_wav(p) for p in stem_paths()}
    metrics = {
        "pass02_master": analyze_wav(PASS02_MASTER),
        "pass03_master": analyze_wav(PASS03_MASTER),
        "pass04_premaster": analyze_wav(PASS04_PREMASTER),
        "pass04_master": analyze_wav(PASS04_MASTER),
        "technical_reference": analyze_wav(TECH_REF),
    }
    profiles = {
        "pass03_master": band_profile(PASS03_MASTER),
        "pass04_master": band_profile(PASS04_MASTER),
        "technical_reference": band_profile(TECH_REF),
    }
    failures, notes = pass04_validation()
    levels = track_level_table(PASS04_RPP) if PASS04_RPP.exists() else {}
    payload = {
        "generated": now,
        "project": str(PASS04_RPP),
        "suno": {
            "voice_required": "000000",
            "voice_confirmed_in_ui": True,
            "credits": {
                "generation": 10,
                "all_detected_stems": 50,
                "total_this_000000_pass": 60,
                "observed_balance_after_extract": 9200,
            },
            "links": SUNO_LINKS,
            "zip": str(SUNO_ZIP),
            "stems_dir": str(SUNO_STEMS),
            "stem_metrics": stem_metrics,
            "active_use": "imported muted as candidate/reference; not active in render",
            "reason_muted": "Candidate is 39.92s and the Chrome input path stripped Korean lyrics, so it is not a full aligned production replacement.",
        },
        "metrics": metrics,
        "band_profiles": profiles,
        "validation": {"failures": failures, "notes": notes},
        "track_levels": {
            k: levels.get(k)
            for k in [
                "12_Vocals",
                "MALE_LEAD_VOX_BUS",
                "MUSIC_BUS",
                "DRUM_BUS",
                "BASS_808_BUS",
                "VOCAL_FX_BUS",
                "SUNO_000000_CANDIDATE_BUS",
            ]
        },
        "mp3_note": make_mp3_note(),
    }
    (REPORTS / "pass04_suno_000000_qc.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    write(REPORTS / "pass04_suno_000000_stem_download_report.md", "\n".join([
        "# Pass 04 Suno 000000 Stem Download Report",
        "",
        f"Generated: {now}",
        "",
        "## Result",
        "- Selected Suno voice: `000000`.",
        "- Generated 2 candidates; extracted all detected stems from the longer 0:39 candidate.",
        "- Credits used for this 000000 pass: 10 generation + 50 all detected stems = 60.",
        "- Observed credit balance after extraction: 9200.",
        f"- Downloaded ZIP: `{SUNO_ZIP}`.",
        f"- Extracted stems directory: `{SUNO_STEMS}`.",
        "",
        "## Download Error Analysis",
        "- Chrome blocked the Suno render download domain with `ERR_BLOCKED_BY_CLIENT`.",
        "- The UI-generated download URL itself was valid; downloading the same URL through `curl` succeeded.",
        "- This points to a Chrome client/extension block, not a failed Suno stem extraction.",
        "",
        "## Important Limitation",
        "- The candidate is only about 39.92s long.",
        "- The Chrome text input path stripped Korean characters in the lyrics field, so the generated lyric content is incomplete.",
        "- Therefore these stems are imported into REAPER muted as a `000000` candidate/reference, not used as active production replacement.",
        "",
        "## Suno Candidate Links",
        *(f"- {link}" for link in SUNO_LINKS),
    ]) + "\n")

    write(REPORTS / "pass04_suno_000000_source_classification.md", "\n".join([
        "# Pass 04 Suno 000000 Source Classification",
        "",
        f"Generated: {now}",
        "",
        "| File | Class | Active Production | Reason |",
        "| --- | --- | --- | --- |",
        *(
            f"| `{p.name}` | suno_000000_candidate_stem | false | 39.92s generated candidate; imported muted pending human audition/timing validation |"
            for p in stem_paths()
        ),
        "",
        "The stems are valid downloaded WAV stems from the selected `000000` voice, but they are not full-length aligned replacement stems. They should only become active after manual audition and timing repair.",
    ]) + "\n")

    write(REPORTS / "pass04_all_info_mix_report.md", "\n".join([
        "# Pass 04 All-Info Mix Report",
        "",
        f"Generated: {now}",
        "",
        "## Executed",
        "- Imported downloaded Suno `000000` all-detected stems into the REAPER session as muted candidate tracks.",
        "- Kept references, quarantine, guide MIDI, and candidate Suno stems muted for render safety.",
        "- Lowered the main vocal further than PASS03 and brought music/beat melody up.",
        "- Tightened vocal FX returns and delay throws so the beat reads more clearly.",
        "- Kept dynamic EQ strategy active on lead, music, bass, drums, and mix bus through the existing stock/fallback chain.",
        "- Saved progressed project as `reaper/FRESH_MIX_MASTER_PASS_04_SUNO_000000_ALL_INFO.rpp`.",
        "",
        "## Session Validation",
        "PASS" if not failures else "BLOCKED",
        *(f"- {n}" for n in notes),
        *(f"- {f}" for f in failures),
        "",
        "## Key Track Levels",
        "| Track | Volume dB | Pan | Muted |",
        "| --- | ---: | ---: | --- |",
        *(
            f"| {name} | {info.get('volume_db') if info else 'n/a'} | {info.get('pan') if info else 'n/a'} | {info.get('mute') if info else 'n/a'} |"
            for name, info in payload["track_levels"].items()
        ),
        "",
        "## Why Suno Stems Are Muted",
        "- The selected voice requirement was satisfied: `000000` appears on the Suno candidate.",
        "- But the downloaded candidate is short and not a full aligned vocal take.",
        "- It also contains incomplete lyric input caused by Chrome text-entry stripping Korean characters.",
        "- Using it as an active production layer would risk fake/unmatched phrasing. It is preserved for manual audition only.",
    ]) + "\n")

    write(REPORTS / "pass04_loudness_check.md", "\n".join([
        "# Pass 04 Loudness Check",
        "",
        f"Generated: {now}",
        "",
        "ffmpeg ebur128 is unavailable in this shell. This report uses the local Python BS.1770-style approximation plus sample peak and stereo correlation.",
        "",
        metric_table(metrics),
        "",
        make_mp3_note(),
    ]) + "\n")

    write(REPORTS / "pass04_final_qc.md", "\n".join([
        "# Pass 04 Final QC",
        "",
        f"Generated: {now}",
        "",
        "## Metrics",
        metric_table(metrics),
        "",
        "## Tonal / Stereo Profile",
        profile_table(profiles),
        "",
        "## Answers",
        "- Is the beat/main melody more forward than before? PASS04 level design raises MUSIC_BUS and main melody stems relative to the lowered vocal.",
        "- Are the new Suno `000000` stems used safely? Yes, they are downloaded, imported, documented, and muted because they are not a full aligned replacement.",
        "- Is the master only louder? No. PASS04 changes the mix balance before the limiter: vocal down, music up, FX tucked.",
        "- Remaining human check: listen for limiter pumping at the loud target and confirm whether the original lead vocal artifacts are still acceptable.",
        "- If the original lead still has pitch/formant tearing by ear, the answer remains: lead vocal requires regeneration or manual re-recording using voice `000000` with correct lyric input.",
    ]) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
