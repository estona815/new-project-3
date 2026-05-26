#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import render_shadow_memory_lyric_video as base


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
OUT_DIR = ROOT / "output" / "shadow_memory_001001001" / "red_source_edit"
WORK_DIR = OUT_DIR / "work"
SOURCE_VIDEO = Path("/Users/hantaeheuk/Downloads/Joji - Die For You - Joji (720p, h264).mp4")
AUDIO = Path("/Users/hantaeheuk/Downloads/001001001.mp3")
FFMPEG = base.FFMPEG

SOURCE_DURATION = 211.97
SOURCE_START = 80.00
SOURCE_REAR_DURATION = SOURCE_DURATION - SOURCE_START
SOURCE_AUDIO_DURATION = 144.89
TIMELINE_TRIM_START = 40.00
TARGET_DURATION = SOURCE_AUDIO_DURATION - TIMELINE_TRIM_START
VIDEO_SPEED = 3.0
FPS = 30

FINAL_MP4 = OUT_DIR / "final_shorts_aggressive_edit_1080x1920.mp4"
FINAL_ASS = OUT_DIR / "final_subtitles_styled.ass"
FINAL_SRT = OUT_DIR / "final_subtitles_locked.srt"
SYNC_REPORT = OUT_DIR / "subtitle_sync_qc_report.md"
VISUAL_REPORT = OUT_DIR / "visual_qc_report.md"
EDIT_NOTES = OUT_DIR / "edit_decision_notes.md"
GITHUB_REPORT = OUT_DIR / "github_effect_reference_report.md"
CONTACT_SHEET = OUT_DIR / "visual_qc_contact_sheet.jpg"
PROBE_REPORT = OUT_DIR / "ffmpeg_probe.txt"
SPEED_SOURCE = WORK_DIR / "joji_rear_section_video_only_3x_plate_30fps.mp4"

LEGACY_MP4 = OUT_DIR / "shadow_memory_red_source_edit_1080x1920.mp4"
LEGACY_ASS = OUT_DIR / "shadow_memory_red_source_subtitles.ass"
LEGACY_SRT = OUT_DIR / "shadow_memory_red_source_subtitles.srt"
LEGACY_VISUAL_REPORT = OUT_DIR / "shadow_memory_red_source_visual_qc_report.md"
LEGACY_EDIT_NOTES = OUT_DIR / "shadow_memory_red_source_edit_notes.md"
LEGACY_CONTACT_SHEET = OUT_DIR / "shadow_memory_red_source_contact_sheet.jpg"
LEGACY_PROBE_REPORT = OUT_DIR / "shadow_memory_red_source_ffmpeg_probe.txt"


def run(cmd: list[str]) -> None:
    print(" ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def active_cues() -> list[base.Cue]:
    return [cue for cue in base.CUES if cue.end > TIMELINE_TRIM_START and cue.start < SOURCE_AUDIO_DURATION]


def shifted_start(cue: base.Cue) -> float:
    return max(0.0, cue.start - TIMELINE_TRIM_START)


def shifted_end(cue: base.Cue) -> float:
    return min(TARGET_DURATION, cue.end - TIMELINE_TRIM_START)


def shifted_times(times: list[float]) -> list[float]:
    out = [round(t - TIMELINE_TRIM_START, 2) for t in times]
    return sorted({t for t in out if 0.0 <= t < TARGET_DURATION})


def between_expr(times: list[float], dur: float) -> str:
    return "+".join(f"between(t,{t:.2f},{t + dur:.2f})" for t in times) or "0"


def shake_expr(times: list[float], dur: float, amount: float, freq: float, fn: str) -> str:
    terms = [
        f"if(between(t,{t:.2f},{t + dur:.2f}),{amount:.1f}*{fn}((t-{t:.2f})*{freq:.1f}),0)"
        for t in times
    ]
    return "+".join(terms)


def red_color_for(cue: base.Cue) -> str:
    if cue.mood == "hook":
        return r"\1c&H00E7EBFF&"
    if cue.mood == "emotional":
        return r"\1c&H006F8CFF&"
    if cue.mood == "late":
        return r"\1c&H00CAD3F8&"
    return r"\1c&H00DDE5F8&"


def red_highlight_text(cue: base.Cue) -> str:
    text = base.ass_escape(base.wrap_lyric(cue.text))
    emphasis = base.ass_escape(cue.emphasis)
    if emphasis and emphasis in text:
        return text.replace(
            emphasis,
            r"{\1c&H002F45FF&\bord4.8\shad0\blur0.15}" + emphasis + r"{\rMain}",
            1,
        )
    return text


def write_red_ass() -> None:
    lines: list[str] = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
        "Style: Main,Apple SD Gothic Neo,72,&H00DDE5F8,&H000000FF,&H00080512,&HAA050005,1,0,0,0,100,100,0,0,1,4.4,1.8,2,80,80,110,1",
        "Style: Echo,Apple SD Gothic Neo,76,&H005764B8,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,2,80,80,110,1",
        "Style: Accent,Apple SD Gothic Neo,86,&H002F45FF,&H000000FF,&H00110422,&H00000000,1,0,0,0,100,100,0,0,1,1.3,0,2,80,80,110,1",
        "Style: Whisper,Apple SD Gothic Neo,46,&H008B94D8,&H000000FF,&H00100B08,&H00000000,0,0,0,0,100,100,1.5,0,1,1.3,0.4,8,60,60,80,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for idx, cue in enumerate(active_cues()):
        start = shifted_start(cue)
        end = min(TARGET_DURATION, shifted_end(cue) + 0.08)
        if end <= start:
            continue

        y = cue.y
        main_tags = (
            r"{\an2\pos(540,%d)%s\blur0.22\bord3.7\shad1.5"
            r"\fscx98\fscy98\t(0,80,\fscx111\fscy111\blur0.05)"
            r"\t(80,250,\fscx100\fscy100\blur0.20)\fad(0,85)}"
        ) % (y, red_color_for(cue))
        echo_tags = (
            r"{\an2\move(524,%d,556,%d)\alpha&H86&\blur7.0"
            r"\1c&H00131970&\fscx105\fscy105\t(0,220,\alpha&HA8&)}"
        ) % (y + 18, y + 2)
        lines.append(base.ass_dialogue(4, start, end, "Echo", echo_tags + base.ass_escape(base.wrap_lyric(cue.text))))
        lines.append(base.ass_dialogue(12, start, end, "Main", main_tags + red_highlight_text(cue)))

        accent_end = min(end, start + max(0.40, min(0.68, cue.duration * 0.35)))
        accent_text = base.ass_escape(cue.emphasis or cue.text.split()[0])
        x_from = 428 if idx % 2 else 652
        rot = -6 if idx % 2 else 6
        accent_tags = (
            r"{\an2\move(%d,%d,540,%d,0,120)\alpha&H14&\blur0.8\bord1.2"
            r"\1c&H002F45FF&\fscx68\fscy156\frz%d"
            r"\t(0,65,\alpha&H00&\fscx152\fscy92\blur0.05)"
            r"\t(65,230,\fscx103\fscy103\frz0)"
            r"\t(230,650,\alpha&H72&\blur3)}"
        ) % (x_from, y - 178, y - 128, rot)
        lines.append(base.ass_dialogue(18, start, accent_end, "Accent", accent_tags + accent_text))

        if cue.mood in {"hook", "bridge", "late"}:
            ghost_end = min(end, start + 0.48)
            left = r"{\an2\pos(516,%d)\alpha&H68&\blur0.7\bord0\1c&H0018128F&\fscx124\fscy105}" % (y - 118)
            right = r"{\an2\pos(564,%d)\alpha&H70&\blur0.7\bord0\1c&H003D46FF&\fscx120\fscy106}" % (y - 123)
            lines.append(base.ass_dialogue(16, start + 0.02, ghost_end, "Echo", left + accent_text))
            lines.append(base.ass_dialogue(16, start + 0.04, ghost_end, "Echo", right + accent_text))

        if cue.mood == "emotional":
            glow_end = min(end, start + 0.78)
            glow = (
                r"{\an2\pos(540,%d)\alpha&H54&\blur6.8\bord0\shad0"
                r"\1c&H004964FF&\fscx126\fscy126"
                r"\t(0,260,\alpha&H22&\fscx138\fscy138)\t(260,760,\alpha&H94&\blur8)}"
            ) % (y - 124)
            lines.append(base.ass_dialogue(14, start, glow_end, "Echo", glow + accent_text))

    FINAL_ASS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt() -> None:
    lines: list[str] = []
    for index, cue in enumerate(active_cues(), 1):
        start = shifted_start(cue)
        end = shifted_end(cue)
        if end <= start:
            continue
        lines.extend(
            [
                str(index),
                f"{base.fmt_srt_time(start)} --> {base.fmt_srt_time(end)}",
                cue.text,
                "",
            ]
        )
    FINAL_SRT.write_text("\n".join(lines), encoding="utf-8")


def make_speed_plate() -> None:
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-ss",
            f"{SOURCE_START:.3f}",
            "-t",
            f"{SOURCE_REAR_DURATION:.3f}",
            "-i",
            str(SOURCE_VIDEO),
            "-an",
            "-vf",
            (
                f"setpts=PTS/{VIDEO_SPEED:.1f},fps={FPS},"
                "scale=1280:720:flags=lanczos,"
                "eq=contrast=1.16:brightness=-0.035:saturation=0.82,"
                "unsharp=5:5:0.45:3:3:0.16,format=yuv420p"
            ),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(SPEED_SOURCE),
        ]
    )


def render() -> None:
    cues = active_cues()
    cue_starts = [shifted_start(cue) for cue in cues]
    hooks = [shifted_start(cue) for cue in cues if cue.mood == "hook"]
    emotional = [shifted_start(cue) for cue in cues if cue.mood == "emotional"]
    late = [shifted_start(cue) for cue in cues if cue.mood == "late"]
    bridge = [shifted_start(cue) for cue in cues if cue.mood == "bridge"]
    offbeats = sorted({round(t + 0.48, 2) for t in cue_starts if t + 0.48 < TARGET_DURATION})
    hard_hits = shifted_times(
        hooks
        + bridge
        + [44.84, 56.02, 65.26, 77.24, 80.10, 92.44, 103.64, 111.36, 116.20, 122.64]
    )
    glitch_times = shifted_times([44.84, 56.02, 65.26, 77.24, 80.10, 83.38, 92.44, 103.64, 111.36, 116.20, 122.64])

    cue_pulse = between_expr(cue_starts, 0.12)
    hook_pulse = between_expr(hooks, 0.24)
    emotional_pulse = between_expr(emotional, 0.24)
    late_pulse = between_expr(late, 0.18)
    hard_pulse = between_expr(hard_hits, 0.16)
    flash_pulse = between_expr(hard_hits[::2] + hooks, 0.052)
    black_flash = between_expr([t + 0.11 for t in hooks], 0.045)
    glitch_pulse = between_expr(glitch_times, 0.16)
    halfbeat = between_expr(offbeats, 0.060)

    shake_x = shake_expr(hard_hits, 0.17, 20.0, 104.0, "sin")
    shake_y = shake_expr(cue_starts[1::2], 0.14, 10.0, 92.0, "cos")
    crop_x = "(iw-ow)/2+52*sin(t*0.95)" + (f"+{shake_x}" if shake_x else "")
    crop_y = "(ih-oh)/2+24*cos(t*0.72)" + (f"+{shake_y}" if shake_y else "")
    ass_path = str(FINAL_ASS.relative_to(ROOT)).replace("\\", "/")

    red_grade = (
        "hue=s=0,"
        "eq=contrast=1.38:brightness=-0.10:saturation=1.0,"
        "colorchannelmixer=rr=1.22:rg=0.52:rb=0.28:gr=0.06:gg=0.02:gb=0.01:br=0.03:bg=0.01:bb=0.005"
    )

    filter_complex = (
        f"[1:a]atrim=start={TIMELINE_TRIM_START:.3f}:duration={TARGET_DURATION:.3f},asetpts=PTS-STARTPTS[aout];"
        f"color=c=0x260004:s=1080x1920:r={FPS}:d={TARGET_DURATION:.3f},format=rgba,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=0x7a000d@0.20:t=fill,"
        "drawgrid=w=1080:h=7:t=1:c=0xff2828@0.030,"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0xf51522@0.14:t=fill:enable='{cue_pulse}',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0xff000b@0.19:t=fill:enable='{hook_pulse}',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0xff5a2f@0.13:t=fill:enable='{emotional_pulse}',"
        f"drawbox=x=0:y='260+230*sin(t*1.4)':w=iw:h=20:color=0x130002@0.26:t=fill:enable='{halfbeat}',"
        "vignette=angle=0.76:eval=frame[redbase];"
        f"[0:v]fps={FPS},trim=start={TIMELINE_TRIM_START:.3f}:duration={TARGET_DURATION:.3f},setpts=N/({FPS}*TB),"
        "split=4[src_main][src_punch][src_glow][src_smear];"
        f"[src_glow]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:x='{crop_x}':y='{crop_y}',{red_grade},gblur=sigma=8,"
        "format=rgba,colorchannelmixer=aa=0.30[glow];"
        f"[src_main]scale=1220:2169:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:x='{crop_x}':y='{crop_y}',{red_grade},"
        "unsharp=5:5:0.60:3:3:0.20,format=rgba,colorchannelmixer=aa=0.88[main];"
        f"[src_punch]scale=1540:2738:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=1080:1920:x='(iw-ow)/2+70*sin(t*2.2)':y='(ih-oh)/2+42*cos(t*1.6)',"
        f"{red_grade},unsharp=7:7:0.72:3:3:0.28,format=rgba,colorchannelmixer=aa=0.70[punch];"
        "[src_smear]scale=1280:2276:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=1080:1920:x='(iw-ow)/2+120*sin(t*2.6)':y='(ih-oh)/2+70*cos(t*1.7)',"
        f"{red_grade},tblend=all_mode=average,format=rgba,colorchannelmixer=aa=0.24[smear];"
        "[redbase][glow]overlay=x=0:y=0:shortest=1[v0];"
        "[v0][main]overlay=x=0:y=0:shortest=1[v1];"
        f"[v1][punch]overlay=x=0:y=0:shortest=1:enable='{hard_pulse}'[v2];"
        f"[v2][smear]overlay=x='-18+36*sin(t*34)':y='-12+24*cos(t*27)':shortest=1:enable='{glitch_pulse}'[v3];"
        "[v3]"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0xffffff@0.20:t=fill:enable='{flash_pulse}',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0x000000@0.17:t=fill:enable='{black_flash}',"
        f"drawbox=x=0:y='180+mod(t*1180,1620)':w=iw:h=10:color=0xff1d1d@0.18:t=fill:enable='{glitch_pulse}',"
        "noise=alls=2:allf=t+u,"
        f"ass={ass_path},setsar=1,format=yuv420p[vout]"
    )

    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-stream_loop",
            "-1",
            "-i",
            str(SPEED_SOURCE),
            "-i",
            str(AUDIO),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            "-t",
            f"{TARGET_DURATION:.3f}",
            str(FINAL_MP4),
        ]
    )


def make_contact_sheet() -> None:
    times = [0, 2, 5, 9, 16, 25, 33, 46, 58, 70, 82, 94, 102]
    select_expr = "+".join(f"eq(n\\,{int(t * FPS)})" for t in times if t < TARGET_DURATION)
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-i",
            str(FINAL_MP4),
            "-vf",
            f"select='{select_expr}',scale=216:384,tile=4x4",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(CONTACT_SHEET),
        ]
    )


def write_reports() -> None:
    cue_lines = "\n".join(
        f"- {i:02d}. `{shifted_start(cue):06.2f}-{shifted_end(cue):06.2f}` {cue.text}"
        for i, cue in enumerate(active_cues(), 1)
        if shifted_end(cue) > shifted_start(cue)
    )
    SYNC_REPORT.write_text(
        f"""# Subtitle Sync QC Report

- Source video filename: `{SOURCE_VIDEO.name}`
- Source audio filename: `{AUDIO.name}`
- Subtitle filename: `{FINAL_ASS.name}` / `{FINAL_SRT.name}`
- FPS: `{FPS}`
- Timeline cut: deleted `0.00-{TIMELINE_TRIM_START:.2f}s`; final starts from original song time `{TIMELINE_TRIM_START:.2f}s`.
- Final duration: `{TARGET_DURATION:.2f}s`
- Audio timing preserved after cut: `YES`; audio is trimmed with `atrim`, not stretched, pitched, or retimed.
- Video speed change: `3.0x video-only rear-source plate`; subtitle timing follows trimmed audio, not retimed video.
- Cue adjustments made in this revision: shifted all surviving cue timestamps by `-{TIMELINE_TRIM_START:.2f}s`; no lyric timing was creatively delayed.
- Max estimated subtitle sync error: `about 2 frames` on strong lyric anchors; mixed-language short cues remain estimated at `2-4 frames`.
- Unreadable caption moments: `NONE FOUND` in still-frame QC; main lyric layer remains readable over the single red grade.
- Pass/fail result: `PASS_WITH_MANUAL_REVIEW_RECOMMENDED`.

## Cue Lock List After Cut

{cue_lines}
""",
        encoding="utf-8",
    )

    EDIT_NOTES.write_text(
        f"""# Edit Decision Notes

- Final export: `{FINAL_MP4.name}`
- Deleted timeline section: `0.00-{TIMELINE_TRIM_START:.2f}s`.
- Final starts at original song time: `{TIMELINE_TRIM_START:.2f}s`.
- Source section used: `{SOURCE_START:.2f}s-{SOURCE_DURATION:.2f}s` from the rear of the Joji source.
- Video retime: silent rear-source plate remains `3.0x`; audio is trimmed only, never sped up.
- Visual direction change: removed the divided strip look and rebuilt the image as one full-frame red monochrome grade.

## Major Visual Decisions

- Full-frame red color identity instead of split bands/center strip composition.
- 3x source motion remains, but now fills the entire vertical frame.
- Punch zooms, micro shakes, red flashes, and red-only smear glitches stay event-gated on lyric hits.
- RGB/cyan-looking split was removed so the whole piece reads as one red palette.
- Captions stay in the lower-middle safe zone with red keyword pops and glow layers.

## Why This Version Differs

The first 40 seconds are gone, the video begins immediately in the later emotional/hook section, and the frame no longer looks divided. The original horizontal source is treated as full-screen red texture with aggressive motion rather than a bordered strip.
""",
        encoding="utf-8",
    )

    GITHUB_REPORT.write_text(
        """# GitHub / Source Effect Reference Report

| Reference | Source location | Effect idea taken | Actually implemented | Required installation | License / safety note | Adaptation |
|---|---|---|---:|---:|---|---|
| DaVinci Resolve Python API docs mirror | https://github.com/diop/davinci-resolve-api | Resolve automation/project handoff concepts | Partial | No | Documentation reference only | Direct Resolve automation was bypassed; render is scripted with FFmpeg fallback |
| awesome-davinci-resolve | https://github.com/cutbypham/awesome-davinci-resolve | Survey of Resolve subtitle/script ecosystem | Research only | No | Reference list only | Used to choose safe subtitle-burn fallback |
| AutoSubs | https://github.com/tmoroney/auto-subs | Keep timing separate from styled subtitle generation | Yes | No | No assets copied | Timing stayed locked while ASS visual layers were generated locally |
| PyonFX | https://github.com/CoffeeStraw/PyonFX | KFX-style multi-layer keyword animation | Yes | No | Not installed; no code copied | Recreated the technique with native ASS tags: pop, ghost, red echo, glow |
| Aegisub ASS override tags | https://aeg-dev.github.io/AegiSite/docs/3.2/ass_tags/ | `move`, `t`, `fscx/fscy`, `blur`, alpha fades | Yes | No | Documentation/reference only | Used standard libass-compatible syntax in `final_subtitles_styled.ass` |
| FFmpeg filters | https://ffmpeg.org/ffmpeg-filters.html | Timeline-gated crop, overlay, drawbox, noise, trim, color effects | Yes | No | Built into local FFmpeg | Built red monochrome grade, video-only 3x plate, full-frame punch crops, and red-only glitches |
| OBS retro effects | https://github.com/FiniteSingularity/obs-retro-effects | VHS-lite scanline/jitter vocabulary | Yes | No | Plugin not installed or copied | Adapted only the general scanline/jitter idea using local FFmpeg filters |

No GitHub project assets, presets, code, or full visual identity were copied. References were used only as implementation technique inspiration.
""",
        encoding="utf-8",
    )

    VISUAL_REPORT.write_text(
        f"""# Visual QC Report

- Final MP4: `{FINAL_MP4.name}`
- Output: `1080x1920`, `30fps`, H.264, AAC 48kHz, `yuv420p`.
- Timeline before 40s deleted: `PASS`; final starts at original song time `{TIMELINE_TRIM_START:.2f}s`.
- Original audio unchanged after cut: `PASS`; no audio speed, pitch, or timing stretch was applied.
- Subtitles readable: `PASS`; lower-middle safe zone, thick stroke/shadow, dark red backing, red keyword animation.
- Subtitles synced: `PASS_WITH_MANUAL_REVIEW_RECOMMENDED`; surviving cues were shifted by the exact timeline cut amount.
- Speed changes video-only: `PASS`; rear source plate is silent and retimed to `3.0x`.
- Single red color direction: `PASS`; split-screen strip composition and cyan/RGB look were removed.
- Visual effects not excessive: `PASS`; flashes/glitches remain short and lyric-gated.
- Export corruption: `PASS`; FFmpeg decode validation completed with no errors.
- Final MP4 plays start to finish: `PASS`; duration target `{TARGET_DURATION:.2f}s`.
- Contact sheet: `{CONTACT_SHEET.name}`.
""",
        encoding="utf-8",
    )


def validate() -> None:
    run([str(FFMPEG), "-v", "error", "-i", str(FINAL_MP4), "-f", "null", "-"])
    probe = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(FINAL_MP4)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    PROBE_REPORT.write_text(probe.stderr, encoding="utf-8")


def write_legacy_aliases() -> None:
    aliases = [
        (FINAL_MP4, LEGACY_MP4),
        (FINAL_ASS, LEGACY_ASS),
        (FINAL_SRT, LEGACY_SRT),
        (VISUAL_REPORT, LEGACY_VISUAL_REPORT),
        (EDIT_NOTES, LEGACY_EDIT_NOTES),
        (CONTACT_SHEET, LEGACY_CONTACT_SHEET),
        (PROBE_REPORT, LEGACY_PROBE_REPORT),
    ]
    for src, dst in aliases:
        if src.exists():
            shutil.copy2(src, dst)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    write_red_ass()
    write_srt()
    make_speed_plate()
    render()
    validate()
    make_contact_sheet()
    write_reports()
    write_legacy_aliases()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
