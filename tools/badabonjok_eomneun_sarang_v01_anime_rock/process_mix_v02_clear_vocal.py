#!/usr/bin/env python3
import json
import math
import os
import wave
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SRC_SLUG = "badabonjok_eomneun_sarang_v01_anime_rock"
SLUG = "badabonjok_eomneun_sarang_v02_clear_vocal_eq"
SRC = ROOT / "audio_work" / SRC_SLUG / "source_stems"
WORK = ROOT / "audio_work" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER = ROOT / "reaper" / SLUG
FEMALE_CANDIDATE = ROOT / "audio_work" / SRC_SLUG / "suno_generated_candidates" / "suno_anime_rock_female_candidate_7016b495.wav"


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


def envelope_gate(data, floor_db=-43.0, open_db=-30.0, reduction_db=-13.0, frame=1024, hop=256):
    mono = data.mean(axis=1)
    env = np.zeros(len(mono), dtype=np.float32)
    weight = np.zeros(len(mono), dtype=np.float32)
    for start in range(0, max(len(mono) - frame, 1), hop):
        chunk = mono[start : start + frame]
        level = db(np.sqrt(np.mean(chunk * chunk) + 1e-12))
        t = np.clip((level - floor_db) / max(open_db - floor_db, 1e-6), 0.0, 1.0)
        gain_db = reduction_db * (1.0 - t)
        gain = amp(gain_db)
        end = min(start + frame, len(mono))
        env[start:end] += gain
        weight[start:end] += 1.0
    env = np.divide(env, np.maximum(weight, 1.0))
    kernel = np.hanning(2049).astype(np.float32)
    kernel /= np.sum(kernel)
    env = np.convolve(env, kernel, mode="same")
    return data * env[:, None]


def center_focus(data, width=0.35):
    mid = (data[:, 0] + data[:, 1]) * 0.5
    side = (data[:, 0] - data[:, 1]) * 0.5 * width
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def pad_to(data, length):
    if data.shape[0] >= length:
        return data[:length]
    pad = np.zeros((length - data.shape[0], data.shape[1]), dtype=np.float32)
    return np.vstack([data, pad])


def make_rpp(sr, duration, track_paths, master_path, female_mix_path):
    def item_block(path, name, muted=False):
        return f'''  <TRACK
    NAME "{name}"
    BEAT -1
    AUTOMODE 0
    VOLPAN 1 0 -1 -1 1
    MUTESOLO {'1' if muted else '0'} 0 0
    IPHASE 0
    ISBUS 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 -1 -1 -1
    NCHAN 2
    TRACKID {{{os.urandom(16).hex().upper()}}}
    MAINSEND 1 0
    <ITEM
      POSITION 0
      LENGTH {duration:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0 0 1 0 0 0
      FADEOUT 1 0 0 1 0 0 0
      MUTE 0 0
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
    tracks = "".join(item_block(path, name) for name, path in track_paths)
    tracks += item_block(master_path, "PRINT clear vocal master muted reference", True)
    tracks += item_block(female_mix_path, "PRINT female layer experiment muted reference", True)
    return f'''<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 0 0
  RIPPLE 0 0
  RENDER_FILE "{RENDERS / (SLUG + '_reaper_print.wav')}"
  RENDER_FMT 0 2 {sr}
  RENDER_RANGE 1 0 {duration:.12f} 0 1000
  SAMPLERATE {sr} 1 0
  TEMPO 84 4 4 0
  PLAYRATE 1 0 0.25 4
  MARKER 1 0 "v02: vocal denoise, clearer EQ, male lead remains main" 0 0 1 B {{00000000-0000-0000-0000-000000000101}} 0 2
  MARKER 2 0 "female layer is MP3-derived experiment, not isolated stem" 0 0 1 B {{00000000-0000-0000-0000-000000000102}} 0 2
{tracks}>
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

    lead_clean = envelope_gate(loaded["lead"], -44, -31, -12)
    lead_clean = spectral_tilt(lead_clean, sr, [(35, -28), (85, -8), (145, -1.5), (260, -1.8), (850, 0.5), (1700, 1.7), (3200, -1.1), (4800, 1.8), (7600, -1.2), (11500, -1.4)])
    lead_clean = soft_compress(lead_clean, -24, 3.1, 1.4)
    lead_clean = saturate(lead_clean, 1.08, 0.12)

    backing_clean = envelope_gate(loaded["backing"], -46, -33, -14)
    backing_clean = spectral_tilt(backing_clean, sr, [(35, -28), (120, -7), (260, -2.0), (900, -0.8), (2200, -2.8), (4800, 0.4), (8500, -1.8), (13000, -3.0)])
    backing_clean = ms_width(soft_compress(backing_clean, -25, 2.5, -3.5), 1.18)

    drums = saturate(spectral_tilt(loaded["drums"], sr, [(35, -3), (62, 1.1), (135, 0.2), (310, -2.4), (1400, -0.6), (3600, -1.4), (8000, -1.8), (14000, -3.0)]), 1.36, 0.28) * amp(-1.4)
    bass = saturate(spectral_tilt(loaded["bass"], sr, [(30, -3), (58, 1.8), (105, 1.0), (255, -2.3), (700, 0.4), (2500, -2.5), (9000, -10)]), 1.62, 0.36) * amp(-0.9)
    synth = ms_width(spectral_tilt(loaded["synth"], sr, [(60, -7), (190, -2.5), (650, -0.2), (1600, -2.5), (3200, -2.8), (6200, -2.0), (12000, -3.4)]), 1.08) * amp(-2.9)
    other = ms_width(spectral_tilt(loaded["other"], sr, [(60, -7), (210, -2.8), (800, -0.4), (1900, -2.5), (4200, -2.2), (8500, -1.8), (13000, -3.0)]), 1.04) * amp(-3.2)

    female_layer = np.zeros_like(lead_clean)
    if FEMALE_CANDIDATE.exists():
        f_sr, female = read_wav(FEMALE_CANDIDATE)
        if f_sr != sr:
            raise ValueError("female candidate must be converted to 48 kHz WAV first")
        female = pad_to(female, length)
        female = center_focus(female, 0.22)
        female = envelope_gate(female, -45, -32, -16)
        female = spectral_tilt(female, sr, [(45, -35), (140, -14), (260, -6), (650, -2.8), (1400, 0.4), (2800, 1.4), (5200, 0.2), (8500, -2.2), (13000, -6.0)])
        female_layer = soft_compress(female, -26, 2.8, -8.5) * amp(-12.0)

    proc = {
        "lead_clear": limiter(lead_clean, -1.5),
        "backing_clean": limiter(backing_clean, -1.5),
        "drums_v02": limiter(drums, -1.5),
        "bass_v02": limiter(bass, -1.5),
        "synth_v02": limiter(synth, -1.5),
        "other_v02": limiter(other, -1.5),
        "female_layer_mp3_derived": limiter(female_layer, -8.0),
    }

    track_paths = []
    for name, data in proc.items():
        out = WORK / f"processed_{name}.wav"
        write_wav(out, sr, data)
        track_paths.append((name, out))

    premaster = (
        lead_clean * amp(0.9)
        + backing_clean * amp(-6.0)
        + drums * amp(-1.2)
        + bass * amp(-1.0)
        + synth * amp(-2.5)
        + other * amp(-2.8)
    )
    premaster = limiter(soft_compress(premaster, -14.0, 1.55, 0.0), -5.8)
    premaster_path = RENDERS / f"{SLUG}_premaster_48k16.wav"
    write_wav(premaster_path, sr, premaster)

    master = spectral_tilt(premaster, sr, [(30, -1.2), (70, 0.5), (180, 0.0), (420, -0.5), (1200, 0.3), (2800, 0.8), (5200, 0.6), (8200, -0.9), (14500, -1.7)])
    master = saturate(soft_compress(master, -15.5, 1.62, 3.0), 1.12, 0.18)
    master = limiter(normalize_peak(master, -1.0), -1.0)
    master_path = RENDERS / f"{SLUG}_MASTER_clear_vocal_48k16.wav"
    write_wav(master_path, sr, master)

    female_mix = premaster + female_layer
    female_mix = spectral_tilt(female_mix, sr, [(30, -1.2), (70, 0.4), (180, -0.1), (430, -0.6), (1300, 0.2), (2800, 0.5), (5200, 0.4), (8500, -1.2), (14500, -1.9)])
    female_mix = saturate(soft_compress(female_mix, -15.8, 1.62, 2.8), 1.1, 0.16)
    female_mix = limiter(normalize_peak(female_mix, -1.0), -1.0)
    female_mix_path = RENDERS / f"{SLUG}_MASTER_female_layer_experiment_48k16.wav"
    write_wav(female_mix_path, sr, female_mix)

    vocal_ref = limiter(normalize_peak(lead_clean * amp(0.8) + backing_clean * amp(-7.0), -1.0), -1.0)
    vocal_ref_path = RENDERS / f"{SLUG}_vocal_clean_reference_48k16.wav"
    write_wav(vocal_ref_path, sr, vocal_ref)

    duration = length / sr
    analysis = {
        "slug": SLUG,
        "source_slug": SRC_SLUG,
        "sample_rate": sr,
        "duration_seconds": round(duration, 3),
        "clear_master_metrics": metrics(master),
        "female_layer_experiment_metrics": metrics(female_mix),
        "premaster_metrics": metrics(premaster),
        "female_candidate_used": str(FEMALE_CANDIDATE) if FEMALE_CANDIDATE.exists() else None,
        "female_candidate_note": "MP3-derived full mix, not isolated vocal stem; used only as a low tucked layer.",
    }
    (REPORTS / "audio_qc.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    rpp_path = REAPER / f"{SLUG}.rpp"
    rpp_path.write_text(make_rpp(sr, duration, track_paths, master_path, female_mix_path), encoding="utf-8")

    notes = f"""# {SLUG} Revision Notes

## Status
- Source: user-provided Suno stems from `{SRC_SLUG}`.
- Revision goal: reduce vocal noise, make the vocal clearer, and rebalance full master EQ.
- Male lead remains the main vocal.
- Suno female candidate was included only in the separate experiment render because it is an MP3 full mix, not an isolated stem.

## Outputs
- Clear vocal master: `{master_path}`
- Female layer experiment: `{female_mix_path}`
- Premaster: `{premaster_path}`
- Clean vocal reference: `{vocal_ref_path}`
- REAPER project: `{rpp_path}`

## Mix Moves
- Added envelope-based cleanup to lead/backing vocals to lower quiet hiss and tail noise.
- Re-EQed lead vocal with less mud, less harsh upper glare, and more 1.7 kHz / 4.8 kHz intelligibility.
- Tucked backing vocal and widened it slightly so it supports instead of clouding the lead.
- Reduced instrumental masking around the vocal presence band, especially synth/other bed and drum bite.
- Master EQ is brighter in the vocal presence range but rolled off above the harsh air band.
- Female layer experiment uses the Suno MP3 candidate as a very low, center-focused texture only.

## QC
```json
{json.dumps(analysis, indent=2, ensure_ascii=False)}
```
"""
    (REPORTS / "mix_master_report.md").write_text(notes, encoding="utf-8")

    zip_path = RENDERS / f"{SLUG}_deliverables.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [master_path, female_mix_path, premaster_path, vocal_ref_path, REPORTS / "mix_master_report.md", REPORTS / "audio_qc.json", rpp_path]:
            zf.write(path, path.relative_to(ROOT))

    print(json.dumps({"ok": True, "master": str(master_path), "female_layer_experiment": str(female_mix_path), "zip": str(zip_path), "analysis": analysis}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
