from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.midi_reconstruction_audit import audit_reaper_midi_reconstruction


def write_rpp(path: Path, tracks: list[tuple[str, str]]) -> None:
    body = ["<REAPER_PROJECT 0.1 \"7.0\" 0"]
    for name, content in tracks:
        body.extend(
            [
                "  <TRACK",
                f"    NAME \"{name}\"",
                content,
                "  >",
            ]
        )
    body.append(">")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


class MidiReconstructionAuditTests(unittest.TestCase):
    def test_audits_drum_bass_music_midi_and_bus_renders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rpp = root / "song.rpp"
            render_dir = root / "renders"
            render_dir.mkdir()
            for role in ("drums", "bass", "music", "mix", "master"):
                (render_dir / f"song_v01_{role}_bus.wav").write_bytes(b"placeholder")
            write_rpp(
                rpp,
                [
                    ("04_KICK_REBUILD_MIDI", "<ITEM\n<SOURCE MIDI\nnote=36\n>\n>"),
                    ("05_SNARE_CLAP_REBUILD_MIDI", "<ITEM\n<SOURCE MIDI\nnote=38\n>\n>"),
                    ("08_BASS_REBUILD_MIDI", "<ITEM\n<SOURCE MIDI\nnote=48\n>\n>"),
                    ("10_MUSIC_REBUILD_MIDI", "<ITEM\n<SOURCE MIDI\nnote=60\n>\n>"),
                ],
            )

            payload = audit_reaper_midi_reconstruction(rpp, bus_render_dir=render_dir)

            self.assertTrue(payload["has_drum_midi"])
            self.assertTrue(payload["has_bass_midi"])
            self.assertTrue(payload["has_music_midi"])
            self.assertTrue(payload["has_separate_bus_renders"])
            self.assertTrue(payload["true_rebeat_allowed"])

    def test_missing_rpp_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = audit_reaper_midi_reconstruction(Path(tmp) / "missing.rpp")

            self.assertEqual(payload["max_severity"], "FAIL")
            self.assertFalse(payload["true_rebeat_allowed"])

    def test_fullmix_active_with_drum_midi_is_reinforcement_not_true_rebeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rpp = root / "song.rpp"
            audio = root / "fullmix.wav"
            audio.write_bytes(b"placeholder")
            write_rpp(
                rpp,
                [
                    ("02_WORKING_FULLMIX", f"<ITEM\n<SOURCE WAVE\nFILE \"{audio}\"\n>\n>"),
                    ("04_KICK_REBUILD_MIDI", "<ITEM\n<SOURCE MIDI\nnote=36\n>\n>"),
                ],
            )

            payload = audit_reaper_midi_reconstruction(rpp)

            self.assertTrue(payload["original_fullmix_active"])
            self.assertEqual(payload["classification_recommendation"], "drum_reinforcement")
            self.assertFalse(payload["true_rebeat_allowed"])


if __name__ == "__main__":
    unittest.main()
