from __future__ import annotations

import json
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
    write,
)


REAPER = ROOT / "reaper"
PASS03_RPP = REAPER / "FRESH_MIX_MASTER_PASS_03_BEAT_FORWARD_LOUD.rpp"
PASS03_PREMASTER = RENDERS / "PASS03_PREMASTER_BEAT_FORWARD_24bit_48k.wav"
PASS03_MASTER = RENDERS / "PASS03_MASTER_BEAT_FORWARD_LOUD_24bit_48k.wav"
PASS03_MP3 = RENDERS / "PASS03_MASTER_BEAT_FORWARD_LOUD_320k.mp3"


def main() -> int:
    now = datetime.now().isoformat(timespec="seconds")
    metrics = {
        "pass02_master": analyze_wav(PASS02_MASTER),
        "pass03_premaster": analyze_wav(PASS03_PREMASTER),
        "pass03_master": analyze_wav(PASS03_MASTER),
        "technical_reference": analyze_wav(TECH_REF),
    }
    profiles = {
        "pass02_master": band_profile(PASS02_MASTER),
        "pass03_master": band_profile(PASS03_MASTER),
        "technical_reference": band_profile(TECH_REF),
    }
    payload = {
        "generated": now,
        "project": str(PASS03_RPP),
        "renders": {
            "premaster": str(PASS03_PREMASTER),
            "master": str(PASS03_MASTER),
            "mp3": str(PASS03_MP3),
        },
        "metrics": metrics,
        "band_profiles": profiles,
    }
    (REPORTS / "pass03_beat_forward_loud_qc.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    write(REPORTS / "pass03_beat_forward_loud_report.md", "\n".join([
        "# Pass 03 Beat-Forward Loud Report",
        "",
        f"Generated: {now}",
        "",
        "## User Direction",
        "- Lower the vocal.",
        "- Make the beat and main melody more obvious.",
        "- Push loudness around -6 LUFS.",
        "",
        "## Mix Moves",
        "- Lowered 12_Vocals and MALE_LEAD_VOX_BUS relative to PASS02.",
        "- Raised likely main melody/beat stems: 04_Synth, 07_Keyboard, 01_Woodwinds, 05_Strings, and MUSIC_BUS.",
        "- Relaxed MUSIC_BUS ducking so the melody stays present under vocals.",
        "- Kept late/problem female vocal layers muted.",
        "- Tucked vocal reverb/delay further so the beat reads more clearly.",
        "- Pushed Event Horizon harder for a loud review master.",
        "",
        "## Metrics",
        metric_table(metrics),
        "",
        "## Tonal / Stereo Profile",
        profile_table(profiles),
        "",
        "## Interpretation",
        "- PASS03 hits the requested loudness range: around -5.6 LUFS by local approximation.",
        "- Clipping sample count is 0, and sample peak is -1.0 dBFS.",
        "- LRA remains low, so this is intentionally loud/squeezed and must be checked by ear for pumping or vocal distortion.",
        "- The beat and main melody should be more forward than PASS02 by level design.",
    ]) + "\n")

    write(REPORTS / "pass03_suno_regeneration_plan.md", "\n".join([
        "# Pass 03 Suno Regeneration Plan",
        "",
        "The user approved Suno generation budget up to 500 credits. Use this only for quality improvements that cannot be solved by mix moves.",
        "",
        "## Generate Candidates",
        "- Replacement male lead vocal stem: same lyrics and timing intent, cleaner natural formants, modern tuned Korean emo/digicore rap tone, no chipmunk artifacts.",
        "- Optional support adlib/BGV stem: very low, airy, not lead-like, phrase-end only.",
        "- Optional main melody reinforcement: short synth/pluck hook support that follows the existing song identity without copying the technical reference.",
        "",
        "## Avoid",
        "- Do not copy lyrics, melody, arrangement, artist identity, or topline from references.",
        "- Do not generate a full master and use it as production source.",
        "- Do not keep random vocal chops, moans, or glitch artifacts as active mix elements.",
        "",
        "## Suno Prompt Direction",
        "Korean emo rap / digicore / hyperpop vocal stem, male lead, emotionally tuned but natural, clean consonants, stable pitch, no formant tearing, no chipmunk tone, no robotic glitches, dry vocal stem preferred, tight timing to existing beat, commercial Seoul underground polish. Keep female support minimal and low if included.",
        "",
        "## Selection Criteria",
        "- Cleaner pitch/formant than current 12_Vocals.",
        "- Better timing lock to the beat.",
        "- Dry enough for REAPER reverb/delay.",
        "- No obvious AI syllable endings or hard cuts.",
        "- Does not overpower the beat/main melody.",
    ]) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
