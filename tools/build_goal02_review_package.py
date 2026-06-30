#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.analyze_goal02_runtime_loudness import measure_loudnorm


DEFAULT_OUTPUT_DIR = ROOT / "delivery" / "goal02_v04_user_ab_review"
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_v04_user_ab_review"
DEFAULT_ZIP_NAME = "goal02_v04_user_ab_review_USER_AB_PENDING.zip"


AUDIO_SOURCES = [
    {
        "label": "twenty_second_ab_wav",
        "role": "20-second loudness-matched A/B sequence",
        "source": ROOT
        / "renders/goal02_chorus_lufs_target_v04/goal02_lufs_target_v04_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav",
        "dest": "audio/wav/01_20s_AB_current_candidate_primary_refs.wav",
    },
    {
        "label": "twenty_second_loud_wav",
        "role": "20-second loud reference review candidate",
        "source": ROOT
        / "renders/goal02_chorus_lufs_target_v04/goal02_lufs_target_v04_REAPER_LOUD_REFERENCE_-9p5LUFS_20s.wav",
        "dest": "audio/wav/02_20s_loud_reference_candidate.wav",
    },
    {
        "label": "twenty_second_safe_wav",
        "role": "20-second safer streaming review candidate",
        "source": ROOT
        / "renders/goal02_chorus_lufs_target_v04/goal02_lufs_target_v04_REAPER_SAFE_STREAMING_-13p5LUFS_20s.wav",
        "dest": "audio/wav/03_20s_safe_streaming_candidate.wav",
    },
    {
        "label": "full_song_ab_wav",
        "role": "full-song draft loudness-matched A/B sequence",
        "source": ROOT
        / "renders/goal02_fullsong_lufs_target_v04_draft/goal02_fullsong_lufs_target_v04_draft_AB_CURRENT_CANDIDATE_PRIMARY_REFS_FULL_SONG.wav",
        "dest": "audio/wav/04_fullsong_AB_current_candidate_primary_refs.wav",
    },
    {
        "label": "full_song_loud_wav",
        "role": "full-song loud reference draft candidate",
        "source": ROOT
        / "renders/goal02_fullsong_lufs_target_v04_draft/goal02_fullsong_lufs_target_v04_draft_REAPER_LOUD_REFERENCE_-9p5LUFS_FULL_SONG.wav",
        "dest": "audio/wav/05_fullsong_loud_reference_candidate.wav",
    },
    {
        "label": "full_song_safe_wav",
        "role": "full-song safer streaming draft candidate",
        "source": ROOT
        / "renders/goal02_fullsong_lufs_target_v04_draft/goal02_fullsong_lufs_target_v04_draft_REAPER_SAFE_STREAMING_-13p5LUFS_FULL_SONG.wav",
        "dest": "audio/wav/06_fullsong_safe_streaming_candidate.wav",
    },
]


EVIDENCE_SOURCES = [
    ROOT / "reports/goal02_candidate_decision_v04/goal02_candidate_decision.md",
    ROOT / "reports/goal02_candidate_decision_v04/goal02_candidate_decision.json",
    ROOT / "reports/goal02_chorus_lufs_target_v04/goal02_lufs_target_package.md",
    ROOT / "reports/goal02_chorus_lufs_target_v04/goal02_lufs_target_package.json",
    ROOT / "reports/goal02_8_reference_match/GOAL02_REFERENCE_8_TRACK_MIX_FEATURES.md",
    ROOT / "reports/goal02_8_reference_match/goal02_reference_8_track_mix_features.json",
    ROOT / "reports/goal02_8_reference_match/GOAL02_PRIMARY_REFERENCE_TRANSLATION_PACK.md",
    ROOT / "reports/goal02_8_reference_match/goal02_primary_reference_translation_pack.json",
    ROOT / "reports/goal02_objective_coverage/goal02_objective_coverage_audit.md",
    ROOT / "reports/goal02_objective_coverage/goal02_objective_coverage_audit.json",
    ROOT / "reports/goal02_fullsong_lufs_target_v04_draft/goal02_lufs_target_package.md",
    ROOT / "reports/goal02_fullsong_lufs_target_v04_draft/goal02_lufs_target_package.json",
    ROOT / "reports/goal02_chorus_reaper_v04/actual_reaper_plugin_trace.json",
    ROOT / "reports/goal02_fullsong_reaper_v04_draft/actual_reaper_plugin_trace.json",
    ROOT / "docs/digicore_suno_ai_reaper_pipeline.md",
    ROOT / "reports/digicore_suno_ai_pipeline_update_report.md",
]


TARGETS = {
    "loud": {"lufs_min": -9.5, "lufs_max": -8.0, "tp_max": -1.0},
    "safe": {"lufs_min": -14.5, "lufs_max": -12.5, "tp_max": -1.0},
}

AB_SEQUENCE_ORDER = (
    "Current target -> v04 candidate -> ref_06 -> v04 candidate -> "
    "ref_07 -> v04 candidate -> ref_03 -> v04 candidate"
)

DECISION_COMMANDS = [
    (
        "Approve loud and safe full-song final prep",
        "python3 tools/record_goal02_ab_decision.py --decision approve_v04_20s_then_extend_final "
        '--note "User approved the v04 matched-loudness A/B direction."',
    ),
    (
        "Approve safe-streaming only",
        "python3 tools/record_goal02_ab_decision.py --decision approve_safe_only "
        '--note "User approved only the safer streaming profile."',
    ),
    (
        "Roll back to v03 low-end",
        "python3 tools/record_goal02_ab_decision.py --decision rollback_to_v03_low_end "
        '--note "User reports v04 low-end is too thick or masks the vocal."',
    ),
    (
        "Revise vocal forward",
        "python3 tools/record_goal02_ab_decision.py --decision revise_v04_vocal_forward "
        '--note "User reports the lead vocal is still behind."',
    ),
    (
        "Revise hats or sibilance",
        "python3 tools/record_goal02_ab_decision.py --decision revise_v04_hat_sibilance "
        '--note "User reports hats, sibilance, or 7-12 kHz energy still fizz."',
    ),
    (
        "Revise 808/kick",
        "python3 tools/record_goal02_ab_decision.py --decision revise_v04_808_kick "
        '--note "User reports the 808/kick relationship still fails."',
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def copy_file(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    shutil.copy2(source, dest)


def encode_mp3(ffmpeg: str, source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(dest),
        ],
        check=True,
    )


def target_kind(label: str) -> str | None:
    if "_loud_" in label:
        return "loud"
    if "_safe_" in label:
        return "safe"
    return None


def annotate_target(row: dict[str, Any]) -> dict[str, Any]:
    kind = target_kind(str(row.get("label", "")))
    if not kind:
        row["review_target_kind"] = None
        row["review_target_pass"] = None
        return row
    target = TARGETS[kind]
    lufs = row.get("integrated_lufs")
    tp = row.get("true_peak_dbtp")
    row["review_target_kind"] = kind
    row["review_target_lufs_min"] = target["lufs_min"]
    row["review_target_lufs_max"] = target["lufs_max"]
    row["review_target_true_peak_max"] = target["tp_max"]
    row["review_target_pass"] = (
        isinstance(lufs, (int, float))
        and isinstance(tp, (int, float))
        and target["lufs_min"] <= lufs <= target["lufs_max"]
        and tp <= target["tp_max"]
    )
    return row


def write_review_checklist(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 v04 User A/B Review Checklist",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        "- Claim policy: `review package only; not a final delivery; no listening claims by Codex`",
        "- Start with `audio/wav/01_20s_AB_current_candidate_primary_refs.wav` or its MP3 copy.",
        "",
        "## Review Order",
        "",
        "1. Play the 20-second A/B sequence first.",
        f"2. Sequence order: `{AB_SEQUENCE_ORDER}`.",
        "3. Check whether the v04 candidate is not pushed behind the primary references at matched loudness.",
        "4. If the 20-second candidate is acceptable, check the full-song loud and safe drafts.",
        "5. Use the full-song A/B only as a long-form review helper after the 20-second direction is acceptable.",
        "6. Use the MP3 copies only for phone, laptop, car, and quick device translation checks.",
        "",
        "## Pass Criteria For The 20-Second Chorus",
        "",
        "- Lead vocal does not feel behind the primary references.",
        "- 808 remains readable and does not blur or mask the vocal.",
        "- Kick/drum transients do not feel flat against the primary references.",
        "- Hats and sibilance do not read as AI fizz or metallic glare.",
        "- Stereo center does not feel hollow when checked in mono.",
        "- Master density does not feel like a small demo at the same loudness.",
        "",
        "## If It Fails",
        "",
        "- If 808 feels too thick or masks the vocal, roll back to v03 or reduce 808/BASS bus before touching master loudness.",
        "- If vocal is still behind, adjust lead vocal/VOX BUS before limiting harder.",
        "- If hats or S/T bursts fizz, reduce 6-12 kHz dynamically before adding air.",
        "- If master gain reduction would exceed 2 dB sustained, return to VOX, 808/BASS, DRUM, or MUSIC BUS.",
        "",
        "## Included Audio",
        "",
    ]
    for row in result["files"]:
        if row["type"] in {"wav", "mp3"}:
            lines.append(f"- `{row['package_path']}`: {row['role']}")
    lines.extend(
        [
            "",
            "## Required Human Decision",
            "",
            "Keep the record pending until review is actually done:",
            "",
            "```bash",
            "python3 tools/record_goal02_ab_decision.py --decision pending",
            "```",
            "",
            "After review, record exactly one of these decisions:",
            "",
        ]
    )
    for label, command in DECISION_COMMANDS:
        lines.extend(["", f"### {label}", "", "```bash", command, "```"])
    lines.extend(
        [
            "",
            "Only `approve_v04_20s_then_extend_final` or `approve_safe_only` can unlock final-export preparation.",
            "Revision decisions keep the final delivery gate blocked and route the work back to the relevant bus-level fix.",
            "This checklist does not replace the final WAV/MP3/ZIP delivery gate.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_review_player(path: Path, result: dict[str, Any]) -> None:
    audio_rows = {row["label"]: row for row in result["files"] if row.get("type") == "mp3"}

    def audio_card(label: str, title: str, note: str) -> str:
        row = audio_rows[label]
        src = row["package_path"]
        return f"""
        <section class="item">
          <div>
            <h2>{title}</h2>
            <p>{note}</p>
            <p class="meta">File: <code>{src}</code></p>
          </div>
          <audio controls preload="none" src="{src}"></audio>
        </section>
        """

    sequence_steps = "\n".join(f"        <li>{step}</li>" for step in AB_SEQUENCE_ORDER.split(" -> "))
    decision_cards = "\n".join(
        f"""
        <div class="decision">
          <b>{label}</b>
          <code>{command}</code>
        </div>
        """
        for label, command in DECISION_COMMANDS
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GOAL 02 v04 A/B Review Player</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #101114;
      --panel: #191b20;
      --text: #f3f1ea;
      --muted: #b7b1a6;
      --line: #39372f;
      --accent: #e1b84f;
      --ok: #80cfa9;
      --warn: #ffb86b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 28px 18px 56px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 6vw, 48px);
      line-height: 1;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    p {{ margin: 0 0 10px; color: var(--muted); }}
    code {{
      color: var(--text);
      overflow-wrap: anywhere;
    }}
    .status {{
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      margin: 22px 0;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--panel);
    }}
    .metric b {{
      display: block;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    .item {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 12px;
      border-top: 1px solid var(--line);
      padding: 18px 0;
    }}
    audio {{
      width: 100%;
      min-height: 44px;
    }}
    .meta {{
      font-size: 13px;
      color: var(--muted);
    }}
    .commands {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      background: var(--panel);
      margin-top: 24px;
    }}
    .commands ul {{
      margin: 8px 0 0;
      padding-left: 20px;
    }}
    .commands li {{ margin: 6px 0; }}
    .sequence {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      background: var(--panel);
      margin: 18px 0 6px;
    }}
    .sequence ol {{
      margin: 8px 0 0;
      padding-left: 22px;
    }}
    .sequence li {{ margin: 4px 0; }}
    .decision {{
      display: grid;
      gap: 8px;
      border-top: 1px solid var(--line);
      padding: 12px 0;
    }}
    .decision:first-of-type {{ border-top: 0; }}
    .decision code {{
      display: block;
      padding: 10px;
      border-radius: 6px;
      background: #0b0c0f;
    }}
    .pass {{ color: var(--ok); }}
    .pending {{ color: var(--warn); }}
  </style>
</head>
<body>
  <main>
    <h1>GOAL 02 v04 A/B Review</h1>
    <p>This local page is only a review aid. It does not approve audio, claim listening results, or create final delivery.</p>
    <div class="status">
      <div class="metric"><b>Status</b><span class="pending">{result["status"]}</span></div>
      <div class="metric"><b>Review Gate</b>user loudness-matched A/B required</div>
      <div class="metric"><b>Start Here</b>20-second A/B sequence</div>
    </div>

    <section class="sequence">
      <h2>20-second A/B sequence order</h2>
      <p><code>{AB_SEQUENCE_ORDER}</code></p>
      <ol>
{sequence_steps}
      </ol>
    </section>

    {audio_card("twenty_second_ab_mp3", "1. 20-second current/candidate/primary refs A/B", "Use this first. Decide whether v04 avoids demo-level weakness at matched loudness.")}
    {audio_card("twenty_second_loud_mp3", "2. 20-second loud reference candidate", "Focused loud review candidate. Compare against the A/B impression.")}
    {audio_card("twenty_second_safe_mp3", "3. 20-second safer streaming candidate", "Lower-loudness check for translation and less pressure.")}
    {audio_card("full_song_loud_mp3", "4. Full-song loud draft", "Only review after the 20-second chorus direction feels acceptable.")}
    {audio_card("full_song_safe_mp3", "5. Full-song safe draft", "Use for phone, laptop, car, and safer streaming translation checks.")}
    {audio_card("full_song_ab_mp3", "6. Full-song A/B sequence", "Long-form comparison helper. This is not a final-delivery file.")}

    <section class="commands">
      <h2>Record One Decision</h2>
      <p>After review, record exactly one decision through <code>tools/record_goal02_ab_decision.py</code>. Only approval decisions unlock final-export prep; revision decisions keep final delivery blocked.</p>
{decision_cards}
    </section>
  </main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 v04 Review Package Report",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        f"- ZIP: `{result['zip_path']}`",
        f"- ZIP size bytes: `{result['zip_size_bytes']}`",
        f"- ZIP SHA256: `{result['zip_sha256']}`",
        f"- ZIP test: `{result['zip_test_status']}`",
        "- Claim policy: `user A/B review package only; final delivery remains blocked until approval`",
        "",
        "## Loudness / Device Check",
        "",
        "| label | LUFS-I | true peak dBTP | LRA | review target | pass |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in result["loudness_rows"]:
        lines.append(
            f"| `{row['label']}` | `{row.get('integrated_lufs')}` | `{row.get('true_peak_dbtp')}` | "
            f"`{row.get('lra_lu')}` | `{row.get('review_target_kind')}` | `{row.get('review_target_pass')}` |"
        )
    lines.extend(
        [
            "",
            "## Package Files",
            "",
            "| type | package path | source | bytes | sha256 |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in result["files"]:
        lines.append(
            f"| `{row['type']}` | `{row['package_path']}` | `{row.get('source_path', '')}` | "
            f"`{row['size_bytes']}` | `{row['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Remaining Gate",
            "",
            "- User loudness-matched A/B approval is still required.",
            "- This ZIP is not the final delivery package.",
            "- Final WAV/MP3/package can be created only after the user approves or gives revision notes.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip(output_dir: Path, zip_path: Path) -> tuple[str, int, str | None]:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            archive.write(path, path.relative_to(output_dir))
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
    status = "passed" if bad is None else "failed"
    return status, zip_path.stat().st_size, bad


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    report_dir = args.report_dir.resolve()
    zip_path = output_dir / args.zip_name
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    missing = [entry["source"] for entry in AUDIO_SOURCES if not entry["source"].exists()]
    missing.extend(path for path in EVIDENCE_SOURCES if not path.exists())
    if missing:
        result = {
            "schema": "goal02-review-package-v1",
            "created_at": now_utc(),
            "status": "BLOCKED_MISSING_REVIEW_INPUTS",
            "missing": [str(path) for path in missing],
        }
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "goal02_v04_review_package.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    for stale in [
        output_dir / "audio",
        output_dir / "evidence",
        output_dir / "checksums.sha256",
        output_dir / "GOAL02_USER_AB_REVIEW_CHECKLIST.md",
        output_dir / "GOAL02_REVIEW_PLAYER.html",
        output_dir / "goal02_v04_review_package_manifest.json",
        output_dir / "goal02_v04_review_package_manifest.csv",
        output_dir / "goal02_v04_review_loudness_measurements.csv",
    ]:
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()

    file_rows: list[dict[str, Any]] = []
    loudness_rows: list[dict[str, Any]] = []

    for entry in AUDIO_SOURCES:
        source = entry["source"]
        wav_dest = output_dir / entry["dest"]
        copy_file(source, wav_dest)
        mp3_dest = output_dir / "audio" / "mp3" / (wav_dest.stem + "_320k.mp3")
        encode_mp3(ffmpeg, wav_dest, mp3_dest)
        for kind, path in [("wav", wav_dest), ("mp3", mp3_dest)]:
            label = str(entry["label"]).replace("_wav", f"_{kind}")
            file_rows.append(
                {
                    "label": label,
                    "role": entry["role"],
                    "type": kind,
                    "source_path": rel(source) if kind == "wav" else rel(wav_dest),
                    "package_path": str(path.relative_to(output_dir)),
                    "absolute_path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
            loudness_rows.append(annotate_target(measure_loudnorm(ffmpeg, label, path)))

    for source in EVIDENCE_SOURCES:
        dest = output_dir / "evidence" / source.name
        if dest.exists():
            stem = source.stem
            dest = output_dir / "evidence" / f"{stem}_{source.parent.name}{source.suffix}"
        copy_file(source, dest)
        file_rows.append(
            {
                "label": dest.stem,
                "role": "supporting evidence",
                "type": "evidence",
                "source_path": rel(source),
                "package_path": str(dest.relative_to(output_dir)),
                "absolute_path": str(dest),
                "size_bytes": dest.stat().st_size,
                "sha256": sha256(dest),
            }
        )

    result: dict[str, Any] = {
        "schema": "goal02-review-package-v1",
        "created_at": now_utc(),
        "status": "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL",
        "claim_policy": "review package only; no listening claims; final delivery remains blocked until user approval",
        "ffmpeg": ffmpeg,
        "output_dir": str(output_dir),
        "report_dir": str(report_dir),
        "zip_path": str(zip_path),
        "files": file_rows,
        "loudness_rows": loudness_rows,
        "remaining_gates": [
            "user loudness-matched A/B approval",
            "user full-song review",
            "final approved WAV/MP3 export",
            "final delivery ZIP/package evidence",
        ],
    }

    checklist_path = output_dir / "GOAL02_USER_AB_REVIEW_CHECKLIST.md"
    write_review_checklist(checklist_path, result)
    file_rows.append(
        {
            "label": "user_ab_review_checklist",
            "role": "human review checklist",
            "type": "checklist",
            "source_path": "",
            "package_path": str(checklist_path.relative_to(output_dir)),
            "absolute_path": str(checklist_path),
            "size_bytes": checklist_path.stat().st_size,
            "sha256": sha256(checklist_path),
        }
    )

    review_player_path = output_dir / "GOAL02_REVIEW_PLAYER.html"
    write_review_player(review_player_path, result)
    file_rows.append(
        {
            "label": "review_player_html",
            "role": "local audio review player",
            "type": "review_page",
            "source_path": "",
            "package_path": str(review_player_path.relative_to(output_dir)),
            "absolute_path": str(review_player_path),
            "size_bytes": review_player_path.stat().st_size,
            "sha256": sha256(review_player_path),
        }
    )

    manifest_path = output_dir / "goal02_v04_review_package_manifest.json"
    csv_path = output_dir / "goal02_v04_review_package_manifest.csv"
    loudness_csv_path = output_dir / "goal02_v04_review_loudness_measurements.csv"
    write_csv(loudness_csv_path, loudness_rows)
    file_rows.append(
        {
            "label": "loudness_csv",
            "role": "loudness/device measurements",
            "type": "manifest",
            "source_path": "",
            "package_path": str(loudness_csv_path.relative_to(output_dir)),
            "absolute_path": str(loudness_csv_path),
            "size_bytes": loudness_csv_path.stat().st_size,
            "sha256": sha256(loudness_csv_path),
        }
    )
    write_csv(csv_path, file_rows)
    for path, label, role in [
        (loudness_csv_path, "loudness_csv", "loudness/device measurements"),
        (csv_path, "manifest_csv", "package file table"),
    ]:
        if any(row["package_path"] == str(path.relative_to(output_dir)) for row in file_rows):
            continue
        file_rows.append(
            {
                "label": label,
                "role": role,
                "type": "manifest",
                "source_path": "",
                "package_path": str(path.relative_to(output_dir)),
                "absolute_path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    checksums_path = output_dir / "checksums.sha256"
    checksums_path.write_text(
        "".join(f"{row['sha256']}  {row['package_path']}\n" for row in file_rows),
        encoding="utf-8",
    )
    file_rows.append(
        {
            "label": "checksums",
            "role": "package checksum manifest",
            "type": "manifest",
            "source_path": "",
            "package_path": "checksums.sha256",
            "absolute_path": str(checksums_path),
            "size_bytes": checksums_path.stat().st_size,
            "sha256": sha256(checksums_path),
        }
    )

    result["files"] = file_rows
    result["manifest_json_path"] = str(manifest_path)
    result["manifest_json_note"] = "The JSON manifest is self-describing, so it is not listed in files with its own hash."
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_status, zip_size, bad_file = build_zip(output_dir, zip_path)
    result["zip_test_status"] = zip_status
    result["zip_bad_file"] = bad_file
    result["zip_size_bytes"] = zip_size
    result["zip_sha256"] = sha256(zip_path)

    report_json = report_dir / "goal02_v04_review_package.json"
    report_md = report_dir / "goal02_v04_review_package.md"
    report_csv = report_dir / "goal02_v04_review_package_manifest.csv"
    loudness_report_csv = report_dir / "goal02_v04_review_loudness_measurements.csv"
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(report_md, result)
    write_csv(report_csv, file_rows)
    write_csv(loudness_report_csv, loudness_rows)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Goal 02 v04 user A/B review package.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--zip-name", default=DEFAULT_ZIP_NAME)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({"status": result["status"], "zip_path": result.get("zip_path")}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
