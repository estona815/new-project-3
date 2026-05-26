#!/usr/bin/env python3
import json
import math
import os
import wave
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SLUG = "badabonjok_eomneun_sarang_v01_anime_rock"
SRC = ROOT / "audio_work" / SLUG / "source_stems"
WORK = ROOT / "audio_work" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER = ROOT / "reaper" / SLUG


def read_wav(path):
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sr = wf.getframerate()
        frames = wf.getnframes()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(frames)
    if sampwidth != 2:
        raise ValueError(f"{path} is not 16-bit PCM")
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return sr, data.reshape(-1, channels)


def write_wav(path, sr, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(data, -0.999969, 0.999969)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(data.shape[1])
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def db(x):
    return 20.0 * math.log10(max(float(x), 1e-12))


def amp(db_value):
    return 10.0 ** (db_value / 20.0)


def metrics(data):
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(data * data) + 1e-12))
    mono = data.mean(axis=1)
    lufs_rough = -0.691 + 10.0 * math.log10(float(np.mean(mono * mono)) + 1e-12)
    corr = float(np.corrcoef(data[:, 0], data[:, 1])[0, 1]) if data.shape[1] == 2 else 1.0
    return {
        "peak_dbfs": round(db(peak), 2),
        "rms_dbfs": round(db(rms), 2),
        "rough_integrated_lufs": round(lufs_rough, 2),
        "stereo_correlation": round(corr, 3),
    }


def spectral_tilt(data, sr, points):
    freqs = np.fft.rfftfreq(data.shape[0], 1.0 / sr)
    logf = np.log10(np.maximum(freqs, 20.0))
    p_freq = np.array([p[0] for p in points], dtype=np.float32)
    p_gain = np.array([p[1] for p in points], dtype=np.float32)
    gains = np.interp(logf, np.log10(p_freq), p_gain)
    curve = amp(gains).astype(np.float32)
    out = np.empty_like(data)
    for ch in range(data.shape[1]):
        spec = np.fft.rfft(data[:, ch])
        out[:, ch] = np.fft.irfft(spec * curve, n=data.shape[0]).astype(np.float32)
    return out


def soft_compress(data, threshold_db=-18.0, ratio=2.2, makeup_db=0.0):
    mag = np.abs(data)
    level_db = 20.0 * np.log10(np.maximum(mag, 1e-8))
    over = np.maximum(level_db - threshold_db, 0.0)
    gain_db = -over * (1.0 - 1.0 / ratio) + makeup_db
    return data * np.power(10.0, gain_db / 20.0)


def saturate(data, drive=1.0, mix=1.0):
    wet = np.tanh(data * drive) / np.tanh(drive)
    return data * (1.0 - mix) + wet * mix


def ms_width(data, width):
    if data.shape[1] != 2:
        return data
    mid = (data[:, 0] + data[:, 1]) * 0.5
    side = (data[:, 0] - data[:, 1]) * 0.5 * width
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def limiter(data, ceiling_db=-1.0):
    ceiling = amp(ceiling_db)
    peak = float(np.max(np.abs(data)))
    if peak > ceiling:
        data = data * (ceiling / peak)
    return data


def normalize_peak(data, target_db=-1.0):
    peak = float(np.max(np.abs(data)))
    if peak <= 1e-9:
        return data
    return data * (amp(target_db) / peak)


def onset_bpm_guess(data, sr):
    mono = data.mean(axis=1)
    hop = 1024
    frames = mono[: (len(mono) // hop) * hop].reshape(-1, hop)
    energy = np.sqrt(np.mean(frames * frames, axis=1))
    novelty = np.maximum(np.diff(energy, prepend=energy[0]), 0.0)
    novelty -= np.mean(novelty)
    if np.max(np.abs(novelty)) <= 1e-8:
        return None
    ac = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
    bpms = np.arange(70, 191)
    lags = np.round((60.0 / bpms) * sr / hop).astype(int)
    valid = (lags > 1) & (lags < len(ac))
    scores = ac[lags[valid]]
    bpm = int(bpms[valid][int(np.argmax(scores))])
    return bpm


def simple_key_guess(data, sr):
    mono = data.mean(axis=1)
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
    mask = (freqs >= 55.0) & (freqs <= 1760.0)
    chroma = np.zeros(12, dtype=np.float64)
    for f, s in zip(freqs[mask], spec[mask]):
        midi = int(round(69 + 12 * math.log2(f / 440.0))) % 12
        chroma[midi] += float(s)
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return names[int(np.argmax(chroma))]


def make_rpp(sr, duration, processed_paths, master_path, bpm):
    def item_block(path, name, color):
        return f'''  <TRACK
    NAME "{name}"
    PEAKCOL {color}
    BEAT -1
    AUTOMODE 0
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 -1 -1 -1
    FREEMODE 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 2
    TRACKHEIGHT 0 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {{{os.urandom(16).hex().upper()}}}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH {duration:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0 0 1 0 0 0
      FADEOUT 1 0 0 1 0 0 0
      MUTE 0 0
      SEL 0
      IGUID {{{os.urandom(16).hex().upper()}}}
      IID 1
      NAME "{Path(path).name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{os.urandom(16).hex().upper()}}}
      <SOURCE WAVE
        FILE "{path}"
      >
    >
  >
'''
    tracks = []
    colors = [16744576, 16761024, 3368703, 5635925, 11184810, 8421631]
    for i, (name, path) in enumerate(processed_paths):
        tracks.append(item_block(str(path), name, colors[i % len(colors)]))
    tracks.append(item_block(str(master_path), "PRINT reference master muted on import", 4210752).replace("MUTESOLO 0 0 0", "MUTESOLO 1 0 0"))
    body = "".join(tracks)
    return f'''<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 0 0
  RIPPLE 0 0
  AUTOXFADE 129
  RENDER_FILE "{RENDERS / (SLUG + '_reaper_print.wav')}"
  RENDER_FMT 0 2 {sr}
  RENDER_RANGE 1 0 {duration:.12f} 0 1000
  SAMPLERATE {sr} 1 0
  TEMPO {bpm or 150} 4 4 0
  PLAYRATE 1 0 0.25 4
  MARKER 1 0 "source stems preserved; processed mix stems active" 0 0 1 B {{00000000-0000-0000-0000-000000000001}} 0 2
  MARKER 2 0 "Suno female anime rock vocal guide prepared; no generated Suno audio imported yet" 0 0 1 B {{00000000-0000-0000-0000-000000000002}} 0 2
{body}>
'''


def main():
    for p in (WORK, RENDERS, REPORTS, REAPER):
        p.mkdir(parents=True, exist_ok=True)
    stems = {
        "lead": SRC / "0 Lead Vocals.wav",
        "backing": SRC / "1 Backing Vocals.wav",
        "drums": SRC / "2 Drums.wav",
        "bass": SRC / "3 Bass.wav",
        "synth": SRC / "4 Synth.wav",
        "other": SRC / "5 Other.wav",
    }
    loaded = {}
    sr = None
    length = None
    for name, path in stems.items():
        this_sr, data = read_wav(path)
        if sr is None:
            sr = this_sr
            length = data.shape[0]
        loaded[name] = data[:length]

    full_source = sum(loaded.values())
    bpm = onset_bpm_guess(loaded["drums"] + loaded["bass"] * 0.5, sr)
    key = simple_key_guess(loaded["bass"] + loaded["synth"] * 0.6 + loaded["lead"] * 0.4, sr)

    proc = {}
    proc["lead"] = soft_compress(spectral_tilt(loaded["lead"], sr, [(35, -18), (90, -4), (160, 0.5), (900, 1.0), (2500, -1.8), (5500, 1.5), (12000, -1.0)]), -22, 2.8, 1.2)
    proc["backing"] = ms_width(soft_compress(spectral_tilt(loaded["backing"], sr, [(35, -20), (140, -4), (700, -0.5), (2500, -2.2), (6500, 0.6), (12000, -1.5)]), -24, 2.4, -3.0), 1.22)
    proc["drums"] = saturate(spectral_tilt(loaded["drums"], sr, [(35, -2), (65, 1.4), (150, 0.6), (350, -1.7), (2500, 0.4), (7500, -0.8), (14000, -2.0)]), 1.45, 0.35) * amp(-0.7)
    proc["bass"] = saturate(spectral_tilt(loaded["bass"], sr, [(30, -2), (58, 2.2), (110, 1.2), (280, -1.8), (900, 0.8), (4500, -3), (12000, -12)]), 1.8, 0.45) * amp(-0.2)
    proc["synth"] = ms_width(spectral_tilt(loaded["synth"], sr, [(60, -5), (180, -1.5), (700, 0.5), (1800, -2.2), (4200, -1.2), (9000, -2.0), (14000, -3.0)]), 1.12) * amp(-2.2)
    proc["other"] = ms_width(spectral_tilt(loaded["other"], sr, [(60, -5), (200, -2), (850, 0), (2300, -1.8), (6000, -0.6), (13000, -2.3)]), 1.08) * amp(-2.8)

    processed_paths = []
    for name, data in proc.items():
        safe = limiter(data, -1.5)
        out = WORK / f"processed_{name}.wav"
        write_wav(out, sr, safe)
        processed_paths.append((f"processed {name}", out))

    premaster = (
        proc["lead"] * amp(0.4)
        + proc["backing"] * amp(-5.0)
        + proc["drums"] * amp(-1.0)
        + proc["bass"] * amp(-1.2)
        + proc["synth"] * amp(-2.0)
        + proc["other"] * amp(-2.4)
    )
    premaster = limiter(soft_compress(premaster, -13.0, 1.65, 0.0), -5.5)
    premaster_path = RENDERS / f"{SLUG}_premaster_48k16.wav"
    write_wav(premaster_path, sr, premaster)

    master = spectral_tilt(premaster, sr, [(30, -0.8), (70, 0.7), (180, 0.2), (500, -0.2), (1700, -0.4), (4200, 0.5), (9000, -0.4), (14500, -1.1)])
    master = saturate(soft_compress(master, -15.0, 1.7, 3.2), 1.18, 0.22)
    master = limiter(normalize_peak(master, -1.0), -1.0)
    master_path = RENDERS / f"{SLUG}_MASTER_48k16.wav"
    write_wav(master_path, sr, master)

    instr = proc["drums"] * amp(-1.0) + proc["bass"] * amp(-1.2) + proc["synth"] * amp(-2.0) + proc["other"] * amp(-2.4)
    instr = limiter(normalize_peak(soft_compress(instr, -14.0, 1.5, 2.0), -1.0), -1.0)
    instr_path = RENDERS / f"{SLUG}_instrumental_mix_48k16.wav"
    write_wav(instr_path, sr, instr)

    vocal_ref = limiter(normalize_peak(proc["lead"] * amp(0.5) + proc["backing"] * amp(-5.0), -1.0), -1.0)
    vocal_ref_path = RENDERS / f"{SLUG}_vocal_reference_48k16.wav"
    write_wav(vocal_ref_path, sr, vocal_ref)

    duration = length / sr
    analysis = {
        "slug": SLUG,
        "sample_rate": sr,
        "duration_seconds": round(duration, 3),
        "estimated_bpm": bpm,
        "rough_key_center": key,
        "source_mix_metrics": metrics(full_source),
        "premaster_metrics": metrics(premaster),
        "master_metrics": metrics(master),
        "rendered_files": [str(master_path), str(premaster_path), str(instr_path), str(vocal_ref_path)],
    }
    (REPORTS / "audio_qc.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    notes = f"""# {SLUG} Mix/Master Notes

## Status
- Source: user-provided Suno stems zip.
- Workflow status: genre_based_draft with measured local audio QC.
- Duration: {duration:.3f}s, sample rate: {sr} Hz.
- Estimated tempo: {bpm or 'uncertain'} BPM.
- Rough tonal center: {key}.

## Render Outputs
- Master WAV: `{master_path}`
- Premaster WAV: `{premaster_path}`
- Instrumental mix: `{instr_path}`
- Vocal reference: `{vocal_ref_path}`

## Mix Direction
- Anime-rock / digicore vocal-forward balance.
- Lead vocal cleaned with high-pass, mild de-harsh, compression, and top-end control.
- Backing vocal tucked/widened to leave room for a future female Suno vocal layer.
- Kick/bass given controlled saturation and low-end density without broad level pushing.
- Synth/other beds tucked and de-harshened so a generated female vocal can sit on top.

## Limitation
- I did not import a newly generated Suno female vocal into the render yet. This package prepares the timing/key/context and REAPER session for it. Once the generated vocal WAV is available, place it in `audio_work/{SLUG}/suno_female_vocal.wav` and align/mix it against the vocal reference.

## QC
```json
{json.dumps(analysis, indent=2, ensure_ascii=False)}
```
"""
    (REPORTS / "mix_master_report.md").write_text(notes, encoding="utf-8")

    prompt = f"""# Suno Female Vocal Generation Guide

Use under 200 credits. Generate one or two candidate takes only.

Style prompt:
Anime opening rock vocal, Korean female rock singer, bright emotional high-energy vocal, clean pitch, tight timing, energetic chorus lift, digicore hyperpop edge, glossy but not harsh, powerful belted hooks, intimate verse, no crowd noise, no spoken intro, no long instrumental intro.

Arrangement instruction:
Match the uploaded instrumental and vocal reference timing. Keep the female voice rhythmically locked to the existing lead melody. Avoid changing chord progression, BPM, or song structure. Keep consonants crisp and avoid excessive reverb tails.

Detected context:
- Estimated BPM: {bpm or 'uncertain, keep source timing'}
- Rough key center: {key}
- Source length: {duration:.2f}s

Best upload references:
1. `{instr_path}`
2. `{vocal_ref_path}`

After download:
Save the exported female vocal stem as:
`audio_work/{SLUG}/suno_female_vocal.wav`
"""
    (REPORTS / "suno_female_anime_rock_prompt.md").write_text(prompt, encoding="utf-8")

    rpp_path = REAPER / f"{SLUG}.rpp"
    rpp_path.write_text(make_rpp(sr, duration, processed_paths, master_path, bpm), encoding="utf-8")

    zip_path = RENDERS / f"{SLUG}_deliverables.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [master_path, premaster_path, instr_path, vocal_ref_path, REPORTS / "mix_master_report.md", REPORTS / "suno_female_anime_rock_prompt.md", REPORTS / "audio_qc.json", rpp_path]:
            zf.write(path, path.relative_to(ROOT))

    print(json.dumps({"ok": True, "master": str(master_path), "zip": str(zip_path), "rpp": str(rpp_path), "analysis": analysis}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
