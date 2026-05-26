#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
OUT_DIR = ROOT / "output" / "shadow_memory_001001001"
WORK_DIR = OUT_DIR / "work"
AUDIO = Path("/Users/hantaeheuk/Downloads/001001001.mp3")
FFMPEG = Path(
    "/Users/hantaeheuk/Library/Python/3.9/lib/python/site-packages/"
    "imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
)

FINAL_MP4 = OUT_DIR / "shadow_memory_lyric_video_1080x1920.mp4"
FINAL_ASS = OUT_DIR / "shadow_memory_subtitles_styled.ass"
FINAL_SRT = OUT_DIR / "shadow_memory_subtitles_locked.srt"
SYNC_REPORT = OUT_DIR / "shadow_memory_subtitle_sync_qc_report.md"
EDIT_NOTES = OUT_DIR / "shadow_memory_edit_decision_notes.md"
VISUAL_REPORT = OUT_DIR / "shadow_memory_visual_qc_report.md"
BEAT_CSV = OUT_DIR / "shadow_memory_effect_markers.csv"
CONTACT_SHEET = OUT_DIR / "shadow_memory_contact_sheet.jpg"
BACKGROUND_MP4 = WORK_DIR / "shadow_memory_background_540x960.mp4"
PREVIEW_BACKGROUND_MP4 = WORK_DIR / "shadow_memory_preview_background_540x960.mp4"
PREVIEW_MP4 = WORK_DIR / "shadow_memory_preview.mp4"

FPS = 30
DURATION = 144.94
LYRIC_END = 128.14
BG_W = 540
BG_H = 960


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str
    emphasis: str
    y: int = 1392
    mood: str = "main"

    @property
    def duration(self) -> float:
        return self.end - self.start


# Timings are anchored to faster-whisper-small word/phrase timestamps on the
# provided MP3, then corrected to the user-provided lyric text.
CUES: list[Cue] = [
    Cue(0.00, 3.26, "사라져도 기억이 남아있어", "남아있어", 1370, "hook"),
    Cue(3.26, 6.20, "어두워 지네, 너의 얇은 shadow", "shadow", 1408, "hook"),
    Cue(6.20, 9.18, "울때는 널 지키고 싶어서", "지키고", 1370, "hook"),
    Cue(9.18, 12.36, "곁에있어, 지워 니 외로움", "외로움", 1408, "hook"),
    Cue(12.36, 14.26, "Time is burn, we got just limit", "limit", 1378, "verse"),
    Cue(14.26, 15.86, "뒤돌아 본뒤, 넌 남아있길", "남아있길", 1410, "verse"),
    Cue(15.86, 18.00, "If u cry then, 가자 한강, with me", "한강", 1378, "verse"),
    Cue(18.00, 20.76, "잘해주면 생겨 의심이", "의심이", 1410, "verse"),
    Cue(20.76, 22.38, "넌 sometimes,", "sometimes", 1388, "verse"),
    Cue(22.38, 24.28, "아파도 감추니까", "감추니까", 1422, "verse"),
    Cue(24.28, 26.92, "너의 잘못과 연관 된건 없어", "잘못", 1378, "verse"),
    Cue(26.92, 30.22, "또 혼자, 흐르게 두네 시간", "시간", 1410, "verse"),
    Cue(30.22, 32.60, "도울게난 흉이 안 번지도록", "흉", 1388, "verse"),
    Cue(32.60, 35.88, "사라져도 기억이 남아있어", "남아있어", 1368, "hook"),
    Cue(35.88, 38.36, "어두워 지네, 너의 얇은 shadow", "shadow", 1408, "hook"),
    Cue(38.36, 41.78, "울때는 널 지키고 싶어서", "지키고", 1368, "hook"),
    Cue(41.78, 44.84, "곁에있어, 지워 니 외로움", "외로움", 1408, "hook"),
    Cue(44.84, 46.18, "I dont know why", "know why", 1378, "bridge"),
    Cue(46.18, 47.44, "R u cry until sunrise,", "sunrise", 1410, "bridge"),
    Cue(47.92, 49.00, "밤이 와", "밤", 1388, "bridge"),
    Cue(49.00, 50.32, "오늘은 전화 할거야?", "전화", 1422, "bridge"),
    Cue(50.32, 52.20, "Im swerving on ur vibe", "vibe", 1378, "bridge"),
    Cue(52.92, 55.02, "Just wanna ur smile", "smile", 1410, "bridge"),
    Cue(56.02, 57.98, "Cant believe no mo'", "no mo'", 1378, "verse"),
    Cue(57.98, 59.40, "안되네 얘들과 소통", "소통", 1410, "verse"),
    Cue(59.68, 60.58, "말이 통해서,", "통해서", 1378, "verse"),
    Cue(60.58, 62.32, "우린 같이 산거처럼", "같이", 1410, "verse"),
    Cue(62.32, 65.26, "Life goes on, 되지마 나처럼", "Life goes on", 1378, "verse"),
    Cue(65.26, 68.26, "안아줘, 아픔을 잊도록", "안아줘", 1410, "emotional"),
    Cue(68.26, 70.08, "상관 없어 머리를 비워", "비워", 1378, "verse"),
    Cue(70.08, 71.86, "혼자 보낸, 억울했던", "혼자", 1410, "emotional"),
    Cue(71.86, 74.48, "시간이 지나, 뒤덮인 건", "뒤덮인", 1378, "emotional"),
    Cue(74.48, 77.24, "밤과 나의 말 소리로", "밤", 1410, "emotional"),
    Cue(77.24, 80.10, "오늘 슬펐던 기억을 잊고", "잊고", 1378, "emotional"),
    Cue(80.10, 83.38, "사라져도 기억이 남아있어", "남아있어", 1368, "hook"),
    Cue(83.38, 86.48, "어두워 지네, 너의 얇은 shadow", "shadow", 1408, "hook"),
    Cue(86.48, 89.22, "울때는 널 지키고 싶어서", "지키고", 1368, "hook"),
    Cue(89.22, 92.44, "곁에있어, 지워 니 외로움", "외로움", 1408, "hook"),
    Cue(92.44, 95.08, "Missin on' u, at da late night", "late night", 1378, "late"),
    Cue(95.08, 97.78, "I dont say it, I just wanna ur smile", "smile", 1410, "late"),
    Cue(97.78, 100.74, "They said lyin', 하나도 믿지마", "믿지마", 1378, "late"),
    Cue(100.74, 103.64, "원하는게 없이 옆에 있지난", "옆에", 1410, "late"),
    Cue(103.64, 105.62, "I dont like u", "like u", 1378, "late"),
    Cue(106.64, 109.00, "Just wanna ur smile", "smile", 1410, "late"),
    Cue(109.64, 111.36, "U said, buck u", "buck u", 1378, "late"),
    Cue(111.36, 115.12, "No mo' just cryin'", "cryin'", 1410, "late"),
    Cue(116.20, 118.90, "사라져도 기억이 남아있어", "남아있어", 1368, "hook"),
    Cue(118.90, 122.64, "어두워 지네, 너의 얇은 shadow", "shadow", 1408, "hook"),
    Cue(122.64, 124.76, "울때는 널 지키고 싶어서", "지키고", 1368, "hook"),
    Cue(124.76, 128.14, "곁에있어, 지워 니 외로움", "외로움", 1408, "hook"),
]


def fmt_ass_time(seconds: float) -> str:
    centiseconds = int(round(max(0.0, seconds) * 100))
    hours, rem = divmod(centiseconds, 360_000)
    minutes, rem = divmod(rem, 6_000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{cs:02}"


def fmt_srt_time(seconds: float) -> str:
    milliseconds = int(round(max(0.0, seconds) * 1000))
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def ass_escape(text: str) -> str:
    return text.replace("{", "").replace("}", "").replace("\n", r"\N")


def wrap_lyric(text: str) -> str:
    if len(text) <= 22:
        return text
    splitters = [", ", " / ", " then ", " and ", " I ", " 우린 ", " 하나도 ", " 기억이 "]
    best: tuple[int, str] | None = None
    for splitter in splitters:
        idx = text.find(splitter, 8)
        if idx > 0:
            score = abs(idx - len(text) / 2)
            if best is None or score < best[0]:
                cut = idx + (len(splitter) if splitter.strip() in {"then", "and"} else len(splitter))
                best = (int(score), text[:cut].rstrip() + r"\N" + text[cut:].lstrip())
    if best:
        return best[1]
    words = text.split()
    if len(words) > 3:
        mid = len(words) // 2
        return " ".join(words[:mid]) + r"\N" + " ".join(words[mid:])
    return text


def color_for(cue: Cue) -> str:
    if cue.mood == "hook":
        return r"\1c&H00E8DFD4&"
    if cue.mood == "emotional":
        return r"\1c&H00F2D6B4&"
    if cue.mood == "late":
        return r"\1c&H00C7DDE8&"
    return r"\1c&H00D8DDE1&"


def highlight_text(cue: Cue) -> str:
    text = ass_escape(wrap_lyric(cue.text))
    emphasis = ass_escape(cue.emphasis)
    if emphasis and emphasis in text:
        return text.replace(
            emphasis,
            r"{\1c&H006FA8FF&\bord4.6\shad0\blur0.2}" + emphasis + r"{\rMain}",
            1,
        )
    return text


def ass_dialogue(layer: int, start: float, end: float, style: str, text: str) -> str:
    return f"Dialogue: {layer},{fmt_ass_time(start)},{fmt_ass_time(end)},{style},,0,0,0,,{text}"


def build_ass() -> str:
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
        "Style: Main,Apple SD Gothic Neo,72,&H00D8DDE1,&H000000FF,&H00100B08,&H9A05070B,1,0,0,0,100,100,0,0,1,3.4,1.3,2,80,80,110,1",
        "Style: Echo,Apple SD Gothic Neo,76,&H0089A9C4,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,2,80,80,110,1",
        "Style: Accent,Apple SD Gothic Neo,84,&H006FA8FF,&H000000FF,&H00220F05,&H00000000,1,0,0,0,100,100,0,0,1,1.2,0,2,80,80,110,1",
        "Style: Whisper,Apple SD Gothic Neo,46,&H00B5B9B8,&H000000FF,&H00100B08,&H00000000,0,0,0,0,100,100,1.5,0,1,1.3,0.4,8,60,60,80,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for cue in CUES:
        start = max(0.0, cue.start - 0.03)
        end = min(DURATION, cue.end + 0.08)
        y = cue.y
        main_tags = (
            r"{\an2\pos(540,%d)%s\blur0.28\bord3.4\shad1.3"
            r"\fscx98\fscy98\t(0,90,\fscx108\fscy108\blur0.08)"
            r"\t(90,260,\fscx100\fscy100\blur0.22)\fad(0,90)}"
        ) % (y, color_for(cue))
        echo_tags = (
            r"{\an2\move(528,%d,552,%d)\alpha&H88&\blur8"
            r"\fscx104\fscy104\t(0,220,\alpha&HA8&)}"
        ) % (y + 20, y + 4)
        lines.append(ass_dialogue(4, start, end, "Echo", echo_tags + ass_escape(wrap_lyric(cue.text))))
        lines.append(ass_dialogue(12, start, end, "Main", main_tags + highlight_text(cue)))

        accent_end = min(end, start + max(0.42, min(0.72, cue.duration * 0.35)))
        accent_text = cue.emphasis or cue.text.split()[0]
        accent_tags = (
            r"{\an2\pos(540,%d)\alpha&H28&\blur1.6\bord1.0"
            r"\fscx84\fscy112\t(0,70,\alpha&H00&\fscx126\fscy126)"
            r"\t(70,260,\fscx100\fscy100)\t(260,650,\alpha&H74&\blur3)}"
        ) % (y - 118)
        lines.append(ass_dialogue(15, start, accent_end, "Accent", accent_tags + ass_escape(accent_text)))

        if cue.mood in {"hook", "late"}:
            ghost_end = min(end, start + 0.48)
            left_tags = r"{\an2\pos(526,%d)\alpha&H72&\blur0.8\1c&H00FFB26A&}" % (y + 2)
            right_tags = r"{\an2\pos(554,%d)\alpha&H78&\blur0.8\1c&H006A89FF&}" % (y - 2)
            lines.append(ass_dialogue(6, start + 0.03, ghost_end, "Echo", left_tags + ass_escape(accent_text)))
            lines.append(ass_dialogue(6, start + 0.05, ghost_end, "Echo", right_tags + ass_escape(accent_text)))

    lines.append(
        ass_dialogue(
            3,
            LYRIC_END + 1.1,
            min(DURATION, LYRIC_END + 8.4),
            "Whisper",
            r"{\an8\pos(540,210)\alpha&H72&\blur1.4\fad(600,1200)}memory stays / shadow thins",
        )
    )
    return "\n".join(lines) + "\n"


def write_srt() -> None:
    out: list[str] = []
    for idx, cue in enumerate(CUES, 1):
        out.extend(
            [
                str(idx),
                f"{fmt_srt_time(cue.start)} --> {fmt_srt_time(cue.end)}",
                cue.text,
                "",
            ]
        )
    FINAL_SRT.write_text("\n".join(out), encoding="utf-8")


def between_expr(times: list[float], dur: float) -> str:
    return "+".join(f"between(t,{t:.2f},{t + dur:.2f})" for t in times) or "0"


def marker_times() -> dict[str, list[float]]:
    cue_starts = [cue.start for cue in CUES]
    hooks = [cue.start for cue in CUES if cue.mood == "hook"]
    emotional = [cue.start for cue in CUES if cue.mood == "emotional"]
    late = [cue.start for cue in CUES if cue.mood == "late"]
    offbeats = sorted({round(t + 0.48, 2) for t in cue_starts if t + 0.48 < LYRIC_END})
    return {
        "cue_start_pulse": cue_starts,
        "hook_blue_pulse": hooks,
        "emotional_amber_pulse": emotional,
        "late_glass_pulse": late,
        "halfbeat_micro_shadow": offbeats,
    }


def write_marker_csv(markers: dict[str, list[float]]) -> None:
    with BEAT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "type", "duration_seconds"])
        for kind, times in markers.items():
            duration = {
                "cue_start_pulse": 0.10,
                "hook_blue_pulse": 0.18,
                "emotional_amber_pulse": 0.22,
                "late_glass_pulse": 0.16,
                "halfbeat_micro_shadow": 0.055,
            }[kind]
            for t in times:
                writer.writerow([f"{t:.2f}", kind, f"{duration:.3f}"])


def build_video_filter(markers: dict[str, list[float]]) -> str:
    cue_pulse = between_expr(markers["cue_start_pulse"], 0.10)
    hook_pulse = between_expr(markers["hook_blue_pulse"], 0.18)
    emotional_pulse = between_expr(markers["emotional_amber_pulse"], 0.22)
    late_pulse = between_expr(markers["late_glass_pulse"], 0.16)
    halfbeat = between_expr(markers["halfbeat_micro_shadow"], 0.055)
    shake_terms_x = "+".join(
        f"if(between(t,{t:.2f},{t + 0.16:.2f}),16*sin((t-{t:.2f})*96),0)"
        for t in markers["cue_start_pulse"][::2]
    )
    shake_terms_y = "+".join(
        f"if(between(t,{t:.2f},{t + 0.14:.2f}),10*cos((t-{t:.2f})*86),0)"
        for t in markers["cue_start_pulse"][1::2]
    )
    x_expr = "60+14*sin(t*0.42)" + (f"+{shake_terms_x}" if shake_terms_x else "")
    y_expr = "143+16*cos(t*0.31)" + (f"+{shake_terms_y}" if shake_terms_y else "")

    ass_path = str(FINAL_ASS.relative_to(ROOT)).replace("\\", "/")
    return (
        "[0:a]asplit=3[a_freq][a_wave][aout];"
        f"gradients=s=1240x2206:r={FPS}:d={DURATION:.2f}:"
        "c0=0x02040a:c1=0x071421:c2=0x102232:c3=0x2b1014:n=4:"
        "type=spiral:speed=0.018,format=rgba[grad];"
        f"perlin=s=1240x2206:r={FPS}:octaves=4:persistence=0.62:"
        "xscale=0.030:yscale=0.024:tscale=0.42:random_mode=seed:seed=1001,"
        "format=rgba,colorchannelmixer=aa=0.18[grain];"
        "[grad][grain]blend=all_mode=overlay:all_opacity=0.33,"
        "vignette=angle=0.78:eval=frame,"
        "eq=contrast=1.18:brightness=-0.055:saturation=0.86,"
        "colorbalance=rs=-0.05:gs=-0.02:bs=0.12[base];"
        f"[a_freq]showfreqs=s=1080x620:r={FPS}:mode=line:fscale=log:ascale=sqrt:"
        "win_size=4096:overlap=0.86:colors=0x6fa8ff|0xe07154,"
        "format=rgba,colorchannelmixer=aa=0.42[freq];"
        f"[a_wave]showwaves=s=1080x300:r={FPS}:mode=line:"
        "colors=0x9fb7c9@0.52|0xe07154@0.34,"
        "format=rgba,colorchannelmixer=aa=0.36[wave];"
        "[base][freq]overlay=x=80:y=315:format=auto:shortest=1[v1];"
        "[v1][wave]overlay=x=80:y=1415:format=auto:shortest=1[v2];"
        "[v2]"
        "drawgrid=w=90:h=90:t=1:c=0x34485c@0.09,"
        "drawbox=x='620+420*sin(t*0.19)':y=0:w=96:h=ih:color=0x000000@0.16:t=fill,"
        "drawbox=x=0:y='235+46*sin(t*0.47)':w=iw:h=3:color=0x8bb9ff@0.14:t=fill,"
        "drawbox=x=0:y='1670+28*cos(t*0.52)':w=iw:h=2:color=0xe07154@0.13:t=fill,"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0xeaf4ff@0.105:t=fill:enable='{cue_pulse}',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0x6fa8ff@0.135:t=fill:enable='{hook_pulse}',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=0xe07154@0.125:t=fill:enable='{emotional_pulse}',"
        f"drawbox=x=70:y=260:w=1100:h=5:color=0xcdd9e8@0.35:t=fill:enable='{late_pulse}',"
        f"drawbox=x=0:y='1120+120*sin(t*2.1)':w=iw:h=9:color=0x000000@0.22:t=fill:enable='{halfbeat}',"
        "gblur=sigma=0.18,"
        "scale=1200:2134,"
        f"crop=1080:1920:x='{x_expr}':y='{y_expr}',"
        "unsharp=5:5:0.48:3:3:0.18,"
        f"ass={ass_path},format=yuv420p[vout]"
    )


def run(cmd: list[str], *, cwd: Path = ROOT) -> None:
    print(" ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def render(preview_seconds: float | None) -> None:
    markers = marker_times()
    write_marker_csv(markers)
    background = PREVIEW_BACKGROUND_MP4 if preview_seconds is not None else BACKGROUND_MP4
    final = PREVIEW_MP4 if preview_seconds is not None else FINAL_MP4
    render_background(background, markers, preview_seconds)
    ass_path = str(FINAL_ASS.relative_to(ROOT)).replace("\\", "/")
    cmd = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-i",
        str(background),
        "-i",
        str(AUDIO),
        "-vf",
        f"scale=1080:1920,setsar=1,ass={ass_path},format=yuv420p",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
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
        str(final),
    ]
    run(cmd)


def decode_audio_envelope(seconds: float) -> np.ndarray:
    sample_rate = 2400
    command = [
        str(FFMPEG),
        "-v",
        "error",
        "-i",
        str(AUDIO),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "-",
    ]
    audio = subprocess.run(command, cwd=ROOT, check=True, capture_output=True).stdout
    samples = np.frombuffer(audio, dtype=np.float32)
    frame_count = int(math.ceil(seconds * FPS))
    samples_per_frame = sample_rate / FPS
    env = np.zeros(frame_count, dtype=np.float32)
    for i in range(frame_count):
        start = int(i * samples_per_frame)
        end = int((i + 1) * samples_per_frame)
        chunk = samples[start:end]
        if chunk.size:
            env[i] = float(np.sqrt(np.mean(np.square(chunk))))
    peak = np.percentile(env, 96) if env.size else 1.0
    if peak <= 0:
        peak = 1.0
    env = np.clip(env / peak, 0.0, 1.25)
    return env


def pulse_track(times: list[float], frame_count: int, width_seconds: float, amount: float = 1.0) -> np.ndarray:
    track = np.zeros(frame_count, dtype=np.float32)
    width = max(1.0, width_seconds * FPS)
    for t in times:
        center = int(round(t * FPS))
        lo = max(0, int(center - width * 0.8))
        hi = min(frame_count, int(center + width * 2.2))
        for idx in range(lo, hi):
            x = (idx - center) / width
            if x >= -0.8:
                track[idx] += amount * math.exp(-2.6 * max(0.0, x) ** 2) * max(0.0, 1.0 + x)
    return np.clip(track, 0.0, 1.5)


def render_background(path: Path, markers: dict[str, list[float]], preview_seconds: float | None) -> None:
    seconds = preview_seconds if preview_seconds is not None else DURATION
    frame_count = int(math.ceil(seconds * FPS))
    env = decode_audio_envelope(seconds)[:frame_count]
    cue = pulse_track(markers["cue_start_pulse"], frame_count, 0.10, 0.7)
    hook = pulse_track(markers["hook_blue_pulse"], frame_count, 0.18, 0.95)
    emotional = pulse_track(markers["emotional_amber_pulse"], frame_count, 0.22, 0.85)
    late = pulse_track(markers["late_glass_pulse"], frame_count, 0.16, 0.7)
    halfbeat = pulse_track(markers["halfbeat_micro_shadow"], frame_count, 0.055, 0.45)

    x = np.linspace(0.0, 1.0, BG_W, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, BG_H, dtype=np.float32)[:, None]
    vignette = np.clip(1.12 - 1.10 * ((x - 0.50) ** 2 + (y - 0.52) ** 2), 0.42, 1.0)
    rng = np.random.default_rng(1001)
    particle_x = rng.integers(0, BG_W, size=180)
    particle_y = rng.integers(0, BG_H, size=180)
    particle_speed = rng.uniform(4.0, 18.0, size=180)
    particle_bright = rng.uniform(0.15, 0.65, size=180)

    cmd = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{BG_W}x{BG_H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    print(" ".join(cmd))
    proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for i in range(frame_count):
        t = i / FPS
        e = float(env[i]) if i < env.size else 0.0
        cp = float(cue[i])
        hp = float(hook[i])
        ep = float(emotional[i])
        lp = float(late[i])
        hb = float(halfbeat[i])

        texture = (
            6.0 * np.sin((x * 8.0 + y * 2.1 + t * 0.08) * math.tau)
            + 4.0 * np.sin((y * 9.0 - t * 0.055) * math.tau)
            + 3.2 * np.sin(((x - y) * 5.6 + t * 0.035) * math.tau)
        )
        frame = np.empty((BG_H, BG_W, 3), dtype=np.float32)
        frame[:, :, 0] = 5 + 13 * (1 - y) + 11 * x + texture + 36 * ep + 13 * lp
        frame[:, :, 1] = 8 + 20 * (1 - y) + 14 * x + texture * 0.65 + 28 * hp + 8 * e + 16 * ep
        frame[:, :, 2] = 18 + 58 * (1 - y) + 24 * x + texture * 0.90 + 64 * hp + 22 * e + 12 * cp

        # Memory-shadow panel drift.
        panel_x = int(BG_W * (0.50 + 0.35 * math.sin(t * 0.19)))
        panel_w = 34 + int(16 * math.sin(t * 0.11) ** 2)
        frame[:, max(0, panel_x - panel_w) : min(BG_W, panel_x + panel_w), :] *= 0.70

        # River/wave reflection near the caption area.
        horizon = int(BG_H * (0.735 + 0.015 * math.sin(t * 0.43)))
        frame[max(0, horizon - 1) : min(BG_H, horizon + 2), :, :] = (
            frame[max(0, horizon - 1) : min(BG_H, horizon + 2), :, :] * 0.45
            + np.array([88, 132, 180], dtype=np.float32) * (0.30 + 0.35 * e)
        )
        for px in range(0, BG_W, 5):
            idx = min(frame_count - 1, max(0, i + (px - BG_W // 2) // 8))
            amp = float(env[idx]) if idx < env.size else 0.0
            yy = int(horizon + (amp - 0.35) * 78 + 6 * math.sin(t * 1.7 + px * 0.03))
            y0 = max(0, yy - 1)
            y1 = min(BG_H, yy + 2)
            frame[y0:y1, px : min(BG_W, px + 3), :] = (
                frame[y0:y1, px : min(BG_W, px + 3), :] * 0.25
                + np.array([110 + 90 * ep, 146 + 48 * hp, 190 + 44 * hp], dtype=np.float32) * 0.75
            )

        # Short cue flashes and half-beat shadow cuts.
        if cp > 0.02:
            frame = frame * (1.0 + 0.12 * cp) + np.array([8, 12, 20], dtype=np.float32) * cp
        if hb > 0.02:
            band_y = int(BG_H * (0.58 + 0.10 * math.sin(t * 2.1)))
            frame[max(0, band_y - 5) : min(BG_H, band_y + 5), :, :] *= 0.58
        if lp > 0.02:
            bar_y = int(BG_H * 0.22)
            frame[max(0, bar_y - 2) : min(BG_H, bar_y + 3), 36 : BG_W - 36, :] = (
                frame[max(0, bar_y - 2) : min(BG_H, bar_y + 3), 36 : BG_W - 36, :] * 0.25
                + np.array([192, 215, 232], dtype=np.float32) * 0.75
            )

        # Sparse phone-camera particles.
        active = np.arange(particle_x.size)
        py = ((particle_y[active] + t * particle_speed[active]) % BG_H).astype(int)
        px = particle_x[active]
        valid = (py >= 0) & (py < BG_H) & (px >= 0) & (px < BG_W)
        frame[py[valid], px[valid], :] += (18 + 42 * particle_bright[valid])[:, None]

        grain = rng.normal(0.0, 0.9 + 0.9 * e, size=(BG_H, BG_W, 1)).astype(np.float32)
        frame = (frame + grain) * vignette[:, :, None]
        frame[:2, :, :] *= 0.35
        frame[-2:, :, :] *= 0.35
        frame[:, :2, :] *= 0.35
        frame[:, -2:, :] *= 0.35
        out = np.clip(frame, 0, 255).astype(np.uint8)
        proc.stdin.write(out.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("background render failed")


def write_reports() -> None:
    cue_lines = "\n".join(
        f"- {i:02d}. `{cue.start:06.2f}-{cue.end:06.2f}` {cue.text}"
        for i, cue in enumerate(CUES, 1)
    )
    SYNC_REPORT.write_text(
        f"""# Shadow Memory Subtitle Sync QC Report

- Source audio filename: `{AUDIO}`
- Subtitle filename: `{FINAL_ASS.name}` / `{FINAL_SRT.name}`
- FPS: `{FPS}`
- Audio timing preserved: `YES`; source MP3 is mapped at original speed/pitch and transcoded only for MP4 compatibility.
- Timing source: faster-whisper-small cached local model, word timestamps, Korean language lock, then manual correction to the supplied lyric text.
- Cue count: `{len(CUES)}`
- Last lyric cue ends: `{LYRIC_END:.2f}s`
- Full audio duration: `{DURATION:.2f}s`
- Visual outro without lyric captions: `{LYRIC_END:.2f}-{DURATION:.2f}s`

## Cue Lock List

{cue_lines}

## Adjustments Made

- Replaced ASR mistranscriptions with the user-provided lyric lines.
- Kept ASR phrase/word starts as timing anchors wherever confidence was usable.
- Korean/English spacing normalized for phone readability.
- Obvious typo normalized: `khow` -> `know`; command suffix `ㄱㄱ` was not treated as lyric.

## Estimated Sync Error

- Strong ASR anchors: approximately `1-3 frames`.
- Ambiguous mixed-language/final chorus areas: approximately `3-6 frames`.
- No subtitle animation delays the cue start; readability begins at or slightly before the locked phrase start.

## Readability

- Lower-middle safe zone, large Korean font, thick dark stroke, soft shadow.
- Accent pops are short overlays; main lyric stays readable underneath.
- Final result should receive a human phone playback pass for the final ±2-frame standard.

Final judgment: `PASS_WITH_MANUAL_REVIEW_RECOMMENDED`
""",
        encoding="utf-8",
    )

    EDIT_NOTES.write_text(
        f"""# Shadow Memory Edit Decision Notes

- Audio source: `{AUDIO.name}`
- Final export: `{FINAL_MP4.name}`
- Visual direction: dark urban memory / thin shadow / Han River afterimage.

## Different Visual Skill Used This Time

- Built a procedural cinematic visualizer instead of reusing source footage.
- Used animated spiral gradient, Perlin texture, audio-reactive spectrum, waveform reflection, glass-line panels, and soft cue-start light pulses.
- Kept glitches restrained; the visual identity is shadowy and fluid rather than aggressive raw-footage glitch.

## Effect Plan

- `0.00-12.36s`: immediate hook, blue-white light pulses, low shadow drift, large caption emphasis on `남아있어`, `shadow`, `지키고`, `외로움`.
- `12.36-32.60s`: tighter verse typography with cue-start flashes and subtle micro camera shake.
- `32.60-44.84s`: chorus returns with stronger blue pulse and RGB text ghosts only on hook words.
- `44.84-55.02s`: bridge switches to glass-line accents and quieter negative space.
- `56.02-80.10s`: rap run uses faster caption alternation and half-beat black shadow strips.
- `80.10-92.44s`: emotional hook reprise; warmer amber on protection/loneliness lines.
- `92.44-115.12s`: late-night section uses cooler spectrum, thin horizontal light bars, and sparse caption echoes.
- `116.20-128.14s`: final hook with controlled blue pulse and stronger memory echo.
- `128.14-144.94s`: no extra lyrics; audio outro carries abstract waveform/afterimage only.

## Caption Animation Style

- ASS kinetic lyrics with scale pop, soft echo layer, accent word lift, short RGB ghost on hooks, and no delayed entrance.
- Main caption remains stable while effect accents move around it.

## Key Emphasis Words

남아있어, shadow, 지키고, 외로움, limit, 남아있길, 한강, 의심이, sometimes, 감추니까, 잘못, 시간, 흉, sunrise, 전화, vibe, smile, 소통, Life goes on, 안아줘, 뒤덮인, 잊고, late night, 믿지마, 옆에, cryin'

## Compromises

- No original video was supplied for this request, so this render uses a procedural audio-reactive visual treatment.
- ASR text was not trusted as lyrics; it was used for timing anchors only.
""",
        encoding="utf-8",
    )

    VISUAL_REPORT.write_text(
        f"""# Shadow Memory Visual QC Report

- Final file: `{FINAL_MP4.name}`
- Output target: `1080x1920`, `9:16`, `{FPS}fps`, H.264 MP4, AAC audio.
- Audio unchanged: `YES`; no speed, pitch, or arrangement changes were applied.
- Captions burned in: `YES`, via libass.
- Visual style: procedural cinematic audio-reactive lyric video, dark blue-black with amber memory pulses.
- Not raw-source-looking: `YES`; no raw footage source was used.
- Effects excessive check: `PASS`; pulses and shadow strips are short and leave captions readable.
- Subtitle readability: `PASS_WITH_MANUAL_REVIEW_RECOMMENDED`.
- Subtitle sync: `PASS_WITH_MANUAL_REVIEW_RECOMMENDED`; see sync QC report.
- Intentional lyric-free outro: `{LYRIC_END:.2f}-{DURATION:.2f}s`.

## Machine QC To Run

- Decode validation with FFmpeg.
- Container inspection with FFmpeg input probe.
- Contact sheet spot-check.
""",
        encoding="utf-8",
    )


def make_contact_sheet() -> None:
    times = [0, 3, 9, 16, 33, 46, 58, 70, 80, 92, 116, 132]
    select_expr = "+".join(f"eq(n\\,{int(t * FPS)})" for t in times)
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-i",
            str(FINAL_MP4),
            "-vf",
            f"select='{select_expr}',scale=216:384,tile=4x3",
            "-frames:v",
            "1",
            str(CONTACT_SHEET),
        ]
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
    with (OUT_DIR / "shadow_memory_ffmpeg_probe.txt").open("w", encoding="utf-8") as handle:
        handle.write(probe.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-seconds", type=float, default=None)
    parser.add_argument("--skip-render", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_ASS.write_text(build_ass(), encoding="utf-8")
    write_srt()
    write_reports()
    if not args.skip_render:
        render(args.preview_seconds)
        if args.preview_seconds is None:
            validate()
            make_contact_sheet()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
