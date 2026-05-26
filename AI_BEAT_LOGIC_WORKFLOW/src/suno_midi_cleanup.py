from __future__ import annotations

import json
import shutil
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from suno_source_classifier import (
    BASS_OR_808,
    DRUMS,
    FEMALE_BGV,
    FX,
    MALE_LEAD_VOCAL,
    MUSIC_OR_SYNTH,
    classify_source_file,
)


TICKS_PER_BEAT = 480
DEFAULT_TEMPO_BPM = 180


@dataclass(frozen=True)
class MidiNote:
    start: int
    end: int
    note: int
    velocity: int
    channel: int


def _read_vlq(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[index]
        index += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, index


def _write_vlq(value: int) -> bytes:
    value = max(0, int(value))
    buffer = value & 0x7F
    value >>= 7
    out = [buffer]
    while value:
        buffer = (value & 0x7F) | 0x80
        out.insert(0, buffer)
        value >>= 7
    return bytes(out)


def _parse_track(track: bytes) -> tuple[str | None, list[MidiNote], int | None]:
    index = 0
    tick = 0
    running_status: int | None = None
    open_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}
    notes: list[MidiNote] = []
    track_name: str | None = None
    tempo: int | None = None

    while index < len(track):
        delta, index = _read_vlq(track, index)
        tick += delta
        status = track[index]
        if status & 0x80:
            index += 1
            running_status = status
        elif running_status is not None:
            status = running_status
        else:
            break

        if status == 0xFF:
            meta_type = track[index]
            index += 1
            length, index = _read_vlq(track, index)
            payload = track[index : index + length]
            index += length
            if meta_type == 0x03:
                track_name = payload.decode("utf-8", errors="ignore")
            elif meta_type == 0x51 and length == 3:
                tempo = int.from_bytes(payload, "big")
            elif meta_type == 0x2F:
                break
            continue
        if status in {0xF0, 0xF7}:
            length, index = _read_vlq(track, index)
            index += length
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        if event_type in {0xC0, 0xD0}:
            index += 1
            continue
        if index + 2 > len(track):
            break
        first = track[index]
        second = track[index + 1]
        index += 2
        if event_type == 0x90 and second > 0:
            open_notes.setdefault((channel, first), []).append((tick, second))
        elif event_type in {0x80, 0x90}:
            starts = open_notes.get((channel, first), [])
            if starts:
                start, velocity = starts.pop(0)
                if tick > start:
                    notes.append(MidiNote(start, tick, first, velocity, channel))
    return track_name, notes, tempo


def parse_midi_notes(path: str | Path) -> tuple[list[MidiNote], int]:
    data = Path(path).read_bytes()
    if not data.startswith(b"MThd"):
        raise ValueError("not a standard MIDI file")
    header_length = struct.unpack(">I", data[4:8])[0]
    division = struct.unpack(">H", data[12:14])[0]
    index = 8 + header_length
    notes: list[MidiNote] = []
    tempo = int(round(60_000_000 / DEFAULT_TEMPO_BPM))
    while index + 8 <= len(data):
        kind = data[index : index + 4]
        length = struct.unpack(">I", data[index + 4 : index + 8])[0]
        index += 8
        chunk = data[index : index + length]
        index += length
        if kind != b"MTrk":
            continue
        _, track_notes, track_tempo = _parse_track(chunk)
        notes.extend(track_notes)
        if track_tempo:
            tempo = track_tempo
    if division <= 0:
        division = TICKS_PER_BEAT
    if division != TICKS_PER_BEAT:
        scale = TICKS_PER_BEAT / division
        notes = [
            MidiNote(
                start=int(round(note.start * scale)),
                end=int(round(note.end * scale)),
                note=note.note,
                velocity=note.velocity,
                channel=note.channel,
            )
            for note in notes
        ]
    return notes, tempo


def _role_for_midi(path: str | Path) -> str:
    text = Path(path).stem.lower()
    if "drum" in text or "percussion" in text:
        return DRUMS
    if "bass" in text or "808" in text:
        return BASS_OR_808
    if "vocal" in text or "vox" in text:
        if "backing" in text or "female" in text or "bgv" in text:
            return FEMALE_BGV
        return MALE_LEAD_VOCAL
    if "fx" in text:
        return FX
    return MUSIC_OR_SYNTH


def _quantize(value: int, grid: int) -> int:
    return int(round(value / grid) * grid)


def clean_midi_notes(notes: Iterable[MidiNote], *, role: str) -> list[MidiNote]:
    grid = 60 if role in {DRUMS, FX} else 120
    min_length = 24 if role in {DRUMS, FX} else 60
    cleaned: list[MidiNote] = []
    seen: dict[tuple[int, int, int], MidiNote] = {}
    for note in sorted(notes, key=lambda item: (item.start, item.note, item.channel, item.end)):
        if note.end - note.start < min_length:
            continue
        start = max(0, _quantize(note.start, grid))
        end = max(start + min_length, _quantize(note.end, grid))
        velocity = int(max(48, min(108, round(68 + (note.velocity - 64) * 0.55))))
        candidate = MidiNote(start, end, int(max(0, min(127, note.note))), velocity, int(max(0, min(15, note.channel))))
        key = (candidate.channel, candidate.note, candidate.start)
        previous = seen.get(key)
        if previous and previous.end >= candidate.start:
            if candidate.end - candidate.start > previous.end - previous.start or candidate.velocity > previous.velocity:
                seen[key] = candidate
            continue
        seen[key] = candidate
    cleaned = sorted(seen.values(), key=lambda item: (item.start, item.channel, item.note, item.end))

    deoverlapped: list[MidiNote] = []
    last_by_pitch: dict[tuple[int, int], MidiNote] = {}
    for note in cleaned:
        key = (note.channel, note.note)
        previous = last_by_pitch.get(key)
        if previous and previous.end > note.start:
            shortened = MidiNote(previous.start, max(previous.start + min_length, note.start), previous.note, previous.velocity, previous.channel)
            deoverlapped[-1] = shortened
        deoverlapped.append(note)
        last_by_pitch[key] = note
    return deoverlapped


def _meta(delta: int, kind: int, payload: bytes) -> bytes:
    return _write_vlq(delta) + bytes([0xFF, kind]) + _write_vlq(len(payload)) + payload


def write_midi(path: str | Path, notes: Iterable[MidiNote], *, tempo_us_per_quarter: int, track_name: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    events: list[tuple[int, int, bytes]] = []
    for note in notes:
        events.append((note.start, 1, bytes([0x90 + note.channel, note.note, note.velocity])))
        events.append((note.end, 0, bytes([0x80 + note.channel, note.note, 0])))
    events.sort(key=lambda item: (item[0], item[1]))

    tempo_track = bytearray()
    tempo_track += _meta(0, 0x03, b"Tempo")
    tempo_track += _meta(0, 0x51, int(tempo_us_per_quarter).to_bytes(3, "big"))
    tempo_track += _meta(0, 0x58, bytes([4, 2, 24, 8]))
    tempo_track += _meta(0, 0x2F, b"")

    note_track = bytearray()
    note_track += _meta(0, 0x03, track_name.encode("utf-8"))
    last_tick = 0
    for tick, _, event in events:
        note_track += _write_vlq(max(0, tick - last_tick)) + event
        last_tick = tick
    note_track += _meta(0, 0x2F, b"")

    with path.open("wb") as handle:
        handle.write(b"MThd")
        handle.write(struct.pack(">IHHH", 6, 1, 2, TICKS_PER_BEAT))
        for chunk in (bytes(tempo_track), bytes(note_track)):
            handle.write(b"MTrk")
            handle.write(struct.pack(">I", len(chunk)))
            handle.write(chunk)


def cleanup_midi_directory(source_dir: str | Path, output_dir: str | Path, report_dir: str | Path) -> dict[str, object]:
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    report_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for midi_path in sorted(list(source_path.glob("*.mid")) + list(source_path.glob("*.midi"))):
        role = _role_for_midi(midi_path)
        classification = classify_source_file(midi_path)
        output_name = f"{midi_path.stem}_cleaned_guide.mid"
        output_file = output_path / output_name
        try:
            original, tempo = parse_midi_notes(midi_path)
            cleaned = clean_midi_notes(original, role=role)
            write_midi(output_file, cleaned, tempo_us_per_quarter=tempo, track_name=f"{role}_cleaned_guide")
            status = "cleaned"
            warning = "guide_midi_only_not_final_truth"
        except Exception as exc:  # pragma: no cover - fallback path depends on third-party MIDI quirks
            shutil.copy2(midi_path, output_file)
            original = []
            cleaned = []
            status = "copied_uncertain"
            warning = f"uncertain_guide_midi_parse_fallback: {exc}"
        rows.append(
            {
                "source": str(midi_path),
                "output": str(output_file),
                "classification": classification.category,
                "role_guess": role,
                "status": status,
                "warning": warning,
                "original_note_count": len(original),
                "cleaned_note_count": len(cleaned),
            }
        )

    payload = {
        "schema_version": "suno_midi_cleanup.v1",
        "guide_only": True,
        "output_dir": str(output_path),
        "files": rows,
    }
    (report_path / "midi_analysis.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    analysis_lines = [
        "# MIDI Analysis",
        "",
        "- All Suno MIDI is guide MIDI only, never final truth.",
        f"- MIDI files inspected: {len(rows)}",
        "",
        "| file | role guess | original notes | status |",
        "| --- | --- | ---: | --- |",
    ]
    cleanup_lines = [
        "# MIDI Cleanup",
        "",
        "- Ultra-short glitch notes are removed except tighter drum/fx guide hits.",
        "- Notes are quantized to 1/16, with 1/32 allowed for drum/fx fills.",
        "- Duplicate overlaps are de-overlapped and velocities normalized.",
        "- Uncertain files are labelled as guide-only material for manual review.",
        "",
        "| output | cleaned notes | warning |",
        "| --- | ---: | --- |",
    ]
    for row in rows:
        analysis_lines.append(f"| {Path(str(row['source'])).name} | {row['role_guess']} | {row['original_note_count']} | {row['status']} |")
        cleanup_lines.append(f"| {Path(str(row['output'])).name} | {row['cleaned_note_count']} | {row['warning']} |")
    (report_path / "midi_analysis.md").write_text("\n".join(analysis_lines) + "\n", encoding="utf-8")
    (report_path / "midi_cleanup.md").write_text("\n".join(cleanup_lines) + "\n", encoding="utf-8")
    return payload
