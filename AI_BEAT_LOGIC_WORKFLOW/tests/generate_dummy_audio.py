from __future__ import annotations

import math
import wave
from pathlib import Path


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "dummy_suno_like.wav"


def envelope(index: int, start: int, end: int) -> float:
    if index < start or index >= end:
        return 0.0
    length = max(1, end - start)
    pos = (index - start) / length
    return min(1.0, max(0.0, math.sin(math.pi * pos)))


def generate_dummy_audio(path: Path = FIXTURE_PATH, sample_rate: int = 48000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    duration_seconds = 12.0
    frames = int(duration_seconds * sample_rate)

    intro_end = int(1.0 * sample_rate)
    melody_start = int(1.0 * sample_rate)
    bass_start = int(3.0 * sample_rate)
    drums_start = int(5.0 * sample_rate)
    vocal_start = int(7.0 * sample_rate)
    outro_start = int(10.5 * sample_rate)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for index in range(frames):
            t = index / sample_rate
            sample = 0.0

            if index >= melody_start and index < outro_start:
                melody_freq = 440.0 if int(t * 2) % 2 == 0 else 554.37
                sample += math.sin(2.0 * math.pi * melody_freq * t) * 0.20

            if index >= bass_start and index < outro_start:
                sample += math.sin(2.0 * math.pi * 55.0 * t) * 0.24

            if index >= drums_start and index < outro_start:
                beat_phase = (index - drums_start) % int(0.5 * sample_rate)
                if beat_phase < 360:
                    sample += envelope(beat_phase, 0, 360) * 0.42

            if index >= vocal_start and index < int(9.0 * sample_rate):
                chop_phase = (index - vocal_start) % int(0.18 * sample_rate)
                gate = 1.0 if chop_phase < int(0.08 * sample_rate) else 0.0
                sample += gate * math.sin(2.0 * math.pi * 950.0 * t) * 0.12
                sample += gate * math.sin(2.0 * math.pi * 1450.0 * t) * 0.08

            if index < intro_end or index >= outro_start:
                sample *= 0.05

            sample = max(-0.95, min(0.95, sample))
            integer = int(round(sample * 32767))
            data = integer.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(data + data)

    return path


if __name__ == "__main__":
    generated = generate_dummy_audio()
    print(generated)

