#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
AUDIO = ROOT / "renders" / "0530_sample_v16_vocal_clarity_final_reaper" / "0530_sample_v16_VOCAL_CLARITY_FINAL_320k.mp3"
VIDEO = Path("/Users/hantaeheuk/Downloads/EXC3_CM3 - kkmfd (1080p, h264) (1).mp4")
SLUG = "0530_front_1min_lyric_v01"
OUT_DIR = ROOT / "renders" / SLUG
REPORT_DIR = ROOT / "reports" / SLUG
FFMPEG = Path(imageio_ffmpeg.get_ffmpeg_exe())

FINAL_MP4 = OUT_DIR / "0530_front_1min_lyric_v01_1080p.mp4"
ASS_PATH = REPORT_DIR / "0530_front_1min_lyric_v01.ass"
TIMING_CSV = REPORT_DIR / "0530_front_1min_lyric_timing.csv"
CONTACT_SHEET = REPORT_DIR / "0530_front_1min_contact_sheet.jpg"
QC_JSON = REPORT_DIR / "0530_front_1min_qc.json"
QC_MD = REPORT_DIR / "0530_front_1min_qc_report.md"

AUDIO_START_S = 30.0
DURATION_S = 60.0

LYRICS = [
    (0.00, 3.00, "I can't smile, 난", "태어나자 울었으니까"),
    (3.00, 6.00, "세상은 너와 내게", "고통을 가르쳤지만"),
    (6.00, 9.00, "우린 공명 한채로", "웃음 소리"),
    (9.00, 12.00, "숨지 마 더이상", "내가 지켜주기"),
    (12.00, 15.00, "Erase your 나쁜기억에", "Hashtag 너의 그 웃음소리"),
    (15.00, 18.00, "보고싶어도 말하지 못해", "널 얻기엔 가진게 부족해"),
    (18.00, 21.00, "I'm not afraid더", "감기네 시계 태엽"),
    (21.00, 24.00, "끝까지 옆에 있기로", "택해 널 마주한 기로"),
    (24.00, 27.00, "I don't understand,", "Why are u love me?"),
    (27.00, 30.00, "대체 너는 왜", "다 주려는지"),
    (30.00, 33.00, "Can't pay for this,", "Just pray for u"),
    (33.00, 36.00, "남은 시한부의", "명을 줄게 전부"),
    (36.00, 39.00, "너의 손은 차가와서", "내심장에 속도 제한을둬"),
    (39.00, 42.00, "못멈춰 난 박을것 처럼", "막나가게 되는게 두려워"),
    (42.00, 45.00, "사랑은 감싸고 안야주며", "받은적이 없던 걸 남기는거"),
    (45.00, 48.00, "아물지 못한 상처를 닫고", "약속 흉을 옅게 만들기로"),
    (48.00, 51.00, "I don't understand,", "Why are u love me?"),
    (51.00, 54.00, "대체 너는 왜", "다 주려는지"),
    (54.00, 57.00, "Can't pay for this,", "Just pray for u"),
    (57.00, 60.00, "남은 수", "명을 줄게 전부"),
]


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def write_ass() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Apple SD Gothic Neo,68,&HEFE9DE&,&H000000FF&,&H64100810&,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,2.2,2,120,120,118,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for index, (start, end, line1, line2) in enumerate(LYRICS):
        top = ass_escape(line1)
        bottom = ass_escape(line2)
        color_tag = r"{\fad(120,180)\blur0.45}"
        if index in {8, 16}:
            color_tag = r"{\fad(90,170)\blur0.35\c&HEDE0FF&\3c&H6524142A&}"
        text = f"{color_tag}{top}\\N{bottom}"
        events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Main,,0,0,0,,{text}")
    ASS_PATH.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def write_timing_csv() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with TIMING_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["start_s", "end_s", "line_1", "line_2"])
        for row in LYRICS:
            writer.writerow(row)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def render_video() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ass_arg = str(ASS_PATH).replace("\\", "\\\\").replace(":", "\\:")
    filters = (
        "[0:v]"
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,"
        "eq=contrast=1.05:saturation=0.86:brightness=-0.035,"
        "unsharp=5:5:0.35:3:3:0.15,"
        "vignette=angle=PI/5,"
        f"ass='{ass_arg}'"
        "[v];"
        f"[1:a]atrim=start={AUDIO_START_S}:duration={DURATION_S},"
        "asetpts=PTS-STARTPTS,"
        "afade=t=in:st=0:d=0.04,"
        "afade=t=out:st=59.82:d=0.18,"
        "loudnorm=I=-12.5:TP=-1.0:LRA=7:linear=false"
        "[a]"
    )
    cmd = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "0",
        "-t",
        str(DURATION_S),
        "-i",
        str(VIDEO),
        "-i",
        str(AUDIO),
        "-filter_complex",
        filters,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-r",
        "30000/1001",
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-shortest",
        str(FINAL_MP4),
    ]
    run(cmd)


def render_contact_sheet() -> None:
    cmd = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(FINAL_MP4),
        "-vf",
        "select='not(mod(t,5))',scale=480:-1,tile=4x3",
        "-frames:v",
        "1",
        str(CONTACT_SHEET),
    ]
    run(cmd)


def ffmpeg_probe_text(path: Path) -> str:
    proc = subprocess.run([str(FFMPEG), "-hide_banner", "-i", str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return proc.stderr


def validate_decode() -> None:
    run([str(FFMPEG), "-v", "error", "-i", str(FINAL_MP4), "-f", "null", "-"])


def write_qc() -> None:
    info = ffmpeg_probe_text(FINAL_MP4)
    qc = {
        "output": str(FINAL_MP4),
        "audio_source": str(AUDIO),
        "audio_used_start_s": AUDIO_START_S,
        "audio_used_end_s": AUDIO_START_S + DURATION_S,
        "video_source": str(VIDEO),
        "duration_target_s": DURATION_S,
        "caption_events": len(LYRICS),
        "contact_sheet": str(CONTACT_SHEET),
        "ffmpeg_info": info,
    }
    QC_JSON.write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    QC_MD.write_text(
        "\n".join(
            [
                "# 0530 Front 1min Lyric Video QC",
                "",
                f"- Output: `{FINAL_MP4}`",
                f"- Audio: `{AUDIO}`",
                f"- Audio segment: `{AUDIO_START_S:.2f}s` to `{AUDIO_START_S + DURATION_S:.2f}s`",
                f"- Video base: `{VIDEO}`",
                f"- Target duration: `{DURATION_S:.2f}s`",
                f"- Caption events: `{len(LYRICS)}`",
                f"- ASS captions: `{ASS_PATH}`",
                f"- Timing CSV: `{TIMING_CSV}`",
                f"- Contact sheet: `{CONTACT_SHEET}`",
                "",
                "Decode validation: passed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not AUDIO.exists():
        raise FileNotFoundError(AUDIO)
    if not VIDEO.exists():
        raise FileNotFoundError(VIDEO)
    write_ass()
    write_timing_csv()
    render_video()
    render_contact_sheet()
    validate_decode()
    write_qc()
    print(json.dumps({"output": str(FINAL_MP4), "ass": str(ASS_PATH), "qc": str(QC_MD), "contact_sheet": str(CONTACT_SHEET)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
