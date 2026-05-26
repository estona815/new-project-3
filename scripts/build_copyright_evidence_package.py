#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SOURCE_PACKAGE = Path("/Users/hantaeheuk/Downloads/[YG PLUS] 20260314_Estona,Nib_4dium")
AUDIO_DIR = SOURCE_PACKAGE / "2_음원 (최종 마스터)" / "3_MP3_320kbps"
LYRICS_DIR = SOURCE_PACKAGE / "5_가사 (트랙별 별도 Word 파일 작성)"
SCREENSHOT_DIR = Path("/Users/hantaeheuk/Desktop/copyright_evidence_work_screenshots")
OUTPUT_PACKAGE_DIR = Path("/Users/hantaeheuk/Desktop/copyright_evidence_package")
OUTPUT_ZIP = Path("/Users/hantaeheuk/Desktop/copyright_evidence_package_excluding_lovee_dough.zip")

README_TEXT = (
    "본 ZIP은 저작권 등록/협회 제출용 증빙자료 정리본입니다. 디지털 싱글의 경우 음원과 공표 화면 캡쳐, "
    "가사가 있는 저작물의 경우 전체가사를 포함해야 하므로 제출 전 각 곡별 자료 누락 여부를 확인해야 합니다. "
    "lovee 및 dough는 요청에 따라 본 ZIP에서 제외되었습니다.\n\n"
    "제출 전 확인:\n"
    "1. 각 곡 폴더에 MP3 음원, Apple Music 곡 상세 페이지 캡쳐, 전체 가사 TXT, 곡정보 TXT가 모두 있는지 확인하세요.\n"
    "2. Apple Music 캡쳐는 앨범 페이지가 아니라 곡 상세 페이지 기준이며, 작품명/아티스트명/작사/작곡/편곡 크레딧이 보이는 화면입니다.\n"
    "3. 협회 신고서의 작품명, 아티스트명, 작사/작곡/편곡 정보가 각 곡정보 TXT 및 Apple Music 캡쳐와 일치하는지 확인하세요.\n"
    "4. lovee 및 dough 관련 음원/가사/캡쳐/곡정보 파일은 곡 폴더로 포함하지 않았습니다.\n"
)

NO_LYRICS_TEXT = "본 저작물은 가사가 없는 연주곡/비가사 곡입니다."


TRACKS = [
    {
        "title": "Imnk",
        "folder": "Imnk",
        "audio_hint": "IMnK",
        "lyrics_file": "Imnk.docx",
        "screenshot_file": "Imnk_AppleMusic_공표증빙.png",
        "artist": "Estona,Nib",
        "lyricist": "Estona, Nib",
        "composer": "Estona, Nib",
        "arranger": "Estona, Nib, Hayden.havoc",
        "apple_music_url": "https://music.apple.com/kr/song/imnk/1881803937",
    },
    {
        "title": "Why",
        "folder": "Why",
        "audio_hint": "Why",
        "lyrics_file": "Why.docx",
        "screenshot_file": "Why_AppleMusic_공표증빙.png",
        "artist": "Estona,Nib",
        "lyricist": "Estona",
        "composer": "Estona, Nib",
        "arranger": "Estona, Nib, may3ke",
        "apple_music_url": "https://music.apple.com/kr/song/why/1881804118",
    },
    {
        "title": "Stuck in Seoul",
        "folder": "Stuck_in_Seoul",
        "audio_hint": "Stuck in Seoul",
        "lyrics_file": "Stuck in Seoul.docx",
        "screenshot_file": "Stuck_in_Seoul_AppleMusic_공표증빙.png",
        "artist": "Estona,Nib",
        "lyricist": "Estona",
        "composer": "Estona, Nib",
        "arranger": "Estona, Nib, Hayden.havoc",
        "apple_music_url": "https://music.apple.com/kr/song/stuck-in-seoul/1881804119",
    },
    {
        "title": "Broken",
        "folder": "Broken",
        "audio_hint": "Broken",
        "lyrics_file": "Broken.docx",
        "screenshot_file": "Broken_AppleMusic_공표증빙.png",
        "artist": "Estona,Nib",
        "lyricist": "Estona",
        "composer": "Estona, Nib",
        "arranger": "Estona, Nib, Orin Inc",
        "apple_music_url": "https://music.apple.com/kr/song/broken/1881804120",
    },
    {
        "title": "Miss u",
        "folder": "Miss_u",
        "audio_hint": "Missu",
        "lyrics_file": "Miss u.docx",
        "screenshot_file": "Miss_u_AppleMusic_공표증빙.png",
        "artist": "Estona,Nib",
        "lyricist": "Estona",
        "composer": "Estona, Nib",
        "arranger": "Estona, Nib, Orin Inc",
        "apple_music_url": "https://music.apple.com/kr/song/miss-u/1881804121",
    },
    {
        "title": "Phobia",
        "folder": "Phobia",
        "audio_hint": "Phobia",
        "lyrics_file": "Phobia.docx",
        "screenshot_file": "Phobia_AppleMusic_공표증빙.png",
        "artist": "Estona,Nib",
        "lyricist": "Estona",
        "composer": "Estona, Nib",
        "arranger": "Estona, Nib, Orin Inc",
        "apple_music_url": "https://music.apple.com/kr/song/phobia/1881804122",
    },
]

SCAN_DIRS_FOR_EXCLUSIONS = [
    AUDIO_DIR,
    LYRICS_DIR,
    SOURCE_PACKAGE / "2_음원 (최종 마스터)" / "2_WAV(필수)_4824 or 9624",
    SOURCE_PACKAGE / "2_음원 (최종 마스터)" / "1_FLAC 등 고음질 음원",
    Path("/Users/hantaeheuk/Desktop/앨범Word"),
    Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48."),
    ROOT / "suno_reference_pack" / "4dium_master_mp3",
]


def normalized(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", value).casefold()


def is_excluded(value: str) -> bool:
    compact = normalized(value)
    return "lovee" in compact or "dough" in compact


def safe_name(value: str) -> str:
    safe = re.sub(r'[\\/:\*\?"<>\|]', "_", value).strip()
    safe = re.sub(r"\s+", "_", safe)
    return safe[:80] or "untitled"


def docx_text(path: Path) -> str:
    with ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"<w:br\s*/>", "\n", xml)
    xml = re.sub(r"</w:p[^>]*>", "\n", xml)
    xml = re.sub(r"</w:tr[^>]*>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    text = html.unescape(xml)
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def find_audio(track: dict[str, str]) -> Path | None:
    candidates = sorted(AUDIO_DIR.glob("*.mp3"))
    hint = normalized(track["audio_hint"])
    for candidate in candidates:
        if is_excluded(candidate.name):
            continue
        if hint in normalized(candidate.name):
            return candidate
    return None


def copy_as_png(source: Path, dest: Path, missing: list[str], track_title: str) -> bool:
    if not source.exists():
        missing.append(f"{track_title}: Apple Music 곡 상세 페이지 캡쳐 누락 - {source}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["/usr/bin/sips", "-s", "format", "png", str(source), "--out", str(dest)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        shutil.copy2(source, dest)
    return True


def collect_excluded_files() -> list[str]:
    excluded: list[str] = []
    for scan_dir in SCAN_DIRS_FOR_EXCLUSIONS:
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*"):
            if path.is_file() and is_excluded(path.name):
                excluded.append(str(path))
    return sorted(set(excluded))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if OUTPUT_PACKAGE_DIR.exists():
        shutil.rmtree(OUTPUT_PACKAGE_DIR)
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    OUTPUT_PACKAGE_DIR.mkdir(parents=True)

    missing: list[str] = []
    manifest_rows: list[dict[str, str]] = []
    included_tracks: list[str] = []

    write_text(OUTPUT_PACKAGE_DIR / "00_README_제출전확인.txt", README_TEXT)

    for track in TRACKS:
        title = track["title"]
        folder = OUTPUT_PACKAGE_DIR / "tracks" / track["folder"]
        audio_dir = folder / "audio"
        screenshot_dir = folder / "screenshot"
        lyrics_dir = folder / "lyrics"
        info_dir = folder / "info"

        audio_source = find_audio(track)
        audio_dest_name = f"{safe_name(title)}_음원파일.mp3"
        audio_dest = audio_dir / audio_dest_name
        if audio_source:
            audio_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(audio_source, audio_dest)
        else:
            missing.append(f"{title}: MP3 음원 파일 누락 - 검색 폴더 {AUDIO_DIR}")

        screenshot_source = SCREENSHOT_DIR / track["screenshot_file"]
        screenshot_dest_name = f"{safe_name(title)}_AppleMusic_공표증빙.png"
        screenshot_dest = screenshot_dir / screenshot_dest_name
        copied_screenshot = copy_as_png(screenshot_source, screenshot_dest, missing, title)

        lyrics_source = LYRICS_DIR / track["lyrics_file"]
        lyrics_dest_name = f"{safe_name(title)}_전체가사.txt"
        lyrics_dest = lyrics_dir / lyrics_dest_name
        if lyrics_source.exists():
            lyrics_text = docx_text(lyrics_source)
            if lyrics_text:
                write_text(lyrics_dest, lyrics_text + "\n")
            else:
                lyrics_dest_name = "lyrics_가사없음.txt"
                lyrics_dest = lyrics_dir / lyrics_dest_name
                write_text(lyrics_dest, NO_LYRICS_TEXT + "\n")
        else:
            missing.append(f"{title}: 전체 가사 파일 누락 - {lyrics_source}")

        info_dest_name = f"{safe_name(title)}_곡정보.txt"
        info_text = (
            f"곡 제목: {title}\n"
            f"아티스트명: {track['artist']}\n"
            f"작사: {track['lyricist']}\n"
            f"작곡: {track['composer']}\n"
            f"편곡: {track['arranger']}\n"
            "발매/공표 플랫폼: Apple Music\n"
            "발매/공표 확인 방식: Apple Music 웹 캡쳐(곡 상세 페이지 기준)\n"
            f"음원 파일명: {audio_dest_name if audio_source else '누락'}\n"
            f"가사 파일명: {lyrics_dest_name if lyrics_dest.exists() else '누락'}\n"
            f"비고: Apple Music 곡 상세 URL {track['apple_music_url']} / 발매일 2026-03-14\n"
        )
        write_text(info_dir / info_dest_name, info_text)

        included = bool(audio_source and copied_screenshot and lyrics_dest.exists())
        if included:
            included_tracks.append(title)
        manifest_rows.append(
            {
                "track_title": title,
                "artist": track["artist"],
                "audio_file": f"tracks/{track['folder']}/audio/{audio_dest_name}" if audio_source else "",
                "screenshot_file": f"tracks/{track['folder']}/screenshot/{screenshot_dest_name}" if copied_screenshot else "",
                "lyrics_file": f"tracks/{track['folder']}/lyrics/{lyrics_dest_name}" if lyrics_dest.exists() else "",
                "included_in_zip": "yes" if included else "partial",
                "notes": f"곡 상세 페이지 기준. 작사 {track['lyricist']}; 작곡 {track['composer']}; 편곡 {track['arranger']}",
            }
        )

    with (OUTPUT_PACKAGE_DIR / "01_TRACK_MANIFEST.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "track_title",
                "artist",
                "audio_file",
                "screenshot_file",
                "lyrics_file",
                "included_in_zip",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    excluded_files = collect_excluded_files()
    report_lines = [
        "# MISSING FILES REPORT",
        "",
        "## 누락된 증빙자료",
    ]
    if missing:
        report_lines.extend(f"- {item}" for item in missing)
    else:
        report_lines.append("- 없음. 포함 곡 6곡 모두 MP3 음원, Apple Music 곡 상세 페이지 캡쳐, 전체 가사 TXT, 곡정보 TXT가 생성되었습니다.")
    report_lines.extend(
        [
            "",
            "## lovee/dough 제외 파일",
            "요청에 따라 아래 lovee/dough 관련 원본 후보 파일은 ZIP의 곡별 자료에 포함하지 않았습니다.",
        ]
    )
    if excluded_files:
        report_lines.extend(f"- {item}" for item in excluded_files)
    else:
        report_lines.append("- 발견된 제외 대상 파일 없음")
    write_text(OUTPUT_PACKAGE_DIR / "02_MISSING_FILES_REPORT.md", "\n".join(report_lines) + "\n")

    track_paths_with_exclusions = [
        str(path)
        for path in (OUTPUT_PACKAGE_DIR / "tracks").rglob("*")
        if is_excluded(path.name)
    ]
    if track_paths_with_exclusions:
        for path in track_paths_with_exclusions:
            target = Path(path)
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

    with ZipFile(OUTPUT_ZIP, "w", ZIP_DEFLATED) as zf:
        for path in sorted(OUTPUT_PACKAGE_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, Path("copyright_evidence_package") / path.relative_to(OUTPUT_PACKAGE_DIR))

    with ZipFile(OUTPUT_ZIP) as zf:
        bad_file = zf.testzip()
    if bad_file:
        raise RuntimeError(f"ZIP integrity check failed at {bad_file}")

    zip_track_exclusions = []
    with ZipFile(OUTPUT_ZIP) as zf:
        for name in zf.namelist():
            parts = Path(name).parts
            if "tracks" in parts and is_excluded(name):
                zip_track_exclusions.append(name)
    if zip_track_exclusions:
        raise RuntimeError("Excluded lovee/dough track artifacts remain in ZIP: " + json.dumps(zip_track_exclusions, ensure_ascii=False))

    summary = {
        "zip_path": str(OUTPUT_ZIP),
        "package_dir": str(OUTPUT_PACKAGE_DIR),
        "included_tracks": included_tracks,
        "excluded_files": excluded_files,
        "missing": missing,
        "manifest": str(OUTPUT_PACKAGE_DIR / "01_TRACK_MANIFEST.csv"),
        "missing_report": str(OUTPUT_PACKAGE_DIR / "02_MISSING_FILES_REPORT.md"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
