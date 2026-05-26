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
SLUG = "badabonjok_eomneun_sarang_v04_female_instrument_space"
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


def moving_rms_envelope(data, frame=2048, hop=256):
    mono = data.mean(axis=1)
    env = np.zeros(len(mono), dtype=np.float32)
    weight = np.zeros(len(mono), dtype=np.float32)
    for start in range(0, max(len(mono) - frame, 1), hop):
        chunk = mono[start : start + frame]
        level = float(np.sqrt(np.mean(chunk * chunk) + 1e-12))
        end = min(start + frame, len(mono))
        env[start:end] += level
        weight[start:end] += 1.0
    env = np.divide(env, np.maximum(weight, 1.0))
    kernel = np.hanning(4097).astype(np.float32)
    kernel /= np.sum(kernel)
    return np.convolve(env, kernel, mode="same")


def dynamic_presence_tamer(data, sr, threshold_db=-27.0, max_reduction_db=-3.5):
    bright = spectral_tilt(data, sr, [(80, -18), (350, -10), (1200, -2), (2600, 2.8), (4500, 2.0), (7500, -2.5), (13000, -8)])
    env = moving_rms_envelope(bright)
    env_db = 20.0 * np.log10(np.maximum(env, 1e-8))
    amount = np.clip((env_db - threshold_db) / 12.0, 0.0, 1.0)
    reduction = amp(max_reduction_db) * amount + (1.0 - amount)
    band = spectral_tilt(data, sr, [(80, -24), (350, -14), (1200, -4), (2600, 1.5), (4500, 1.2), (7500, -5), (13000, -12)])
    return data - band * (1.0 - reduction[:, None]) * 0.62


def dynamic_deharsh(data, sr):
    out = dynamic_presence_tamer(data, sr, -29.0, -3.8)
    hiss = spectral_tilt(out, sr, [(80, -30), (500, -18), (2000, -8), (5200, 1.3), (8200, 2.6), (12500, -1.8), (16000, -7)])
    env = moving_rms_envelope(hiss, 1024, 256)
    env_db = 20.0 * np.log10(np.maximum(env, 1e-8))
    amount = np.clip((env_db + 34.0) / 11.0, 0.0, 1.0)
    return out - hiss * amount[:, None] * 0.32


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


def pitch_shift_cents(data, cents):
    factor = 2.0 ** (cents / 1200.0)
    n = data.shape[0]
    src_x = np.arange(n, dtype=np.float32) * factor
    src_x = np.clip(src_x, 0, n - 1)
    out = np.empty_like(data)
    base = np.arange(n, dtype=np.float32)
    for ch in range(data.shape[1]):
        out[:, ch] = np.interp(src_x, base, data[:, ch]).astype(np.float32)
    return out


def tune_gloss(data):
    centered = center_focus(data, 0.55)
    up = pitch_shift_cents(centered, 7.0)
    down = pitch_shift_cents(centered, -6.0)
    return centered * 0.88 + up * 0.06 + down * 0.06


def hard_tune_gloss(data):
    centered = center_focus(data, 0.48)
    up = pitch_shift_cents(centered, 13.0)
    down = pitch_shift_cents(centered, -12.0)
    octave_hint = pitch_shift_cents(centered, 1200.0) * 0.015
    tuned = centered * 0.78 + up * 0.11 + down * 0.095 + octave_hint
    return dynamic_deharsh(tuned, 48000)


def delay(data, sr, seconds=0.285, feedback=0.18, wet=0.12):
    n = int(seconds * sr)
    out = data.copy()
    delayed = np.zeros_like(data)
    if n <= 0 or n >= data.shape[0]:
        return out
    delayed[n:] = data[:-n]
    delayed = spectral_tilt(delayed, sr, [(80, -10), (250, -4), (1200, -1), (3500, 0.2), (8000, -5), (13000, -9)])
    out += delayed * wet
    if feedback > 0:
        delayed2 = np.zeros_like(data)
        n2 = min(n * 2, data.shape[0] - 1)
        delayed2[n2:] = data[:-n2]
        out += delayed2 * wet * feedback
    return out


def ping_pong_delay(data, sr, left_seconds=0.214, right_seconds=0.333, feedback=0.12, wet=0.28):
    left_n = int(left_seconds * sr)
    right_n = int(right_seconds * sr)
    out = data.copy()
    taps = np.zeros_like(data)
    if left_n < data.shape[0]:
        taps[left_n:, 0] += data[:-left_n, 1] * 0.75
        taps[left_n:, 1] += data[:-left_n, 0] * 0.36
    if right_n < data.shape[0]:
        taps[right_n:, 1] += data[:-right_n, 0] * 0.82
        taps[right_n:, 0] += data[:-right_n, 1] * 0.30
    fb_n = min(left_n + right_n, data.shape[0] - 1)
    if fb_n > 0:
        taps[fb_n:] += data[:-fb_n] * feedback
    taps = spectral_tilt(taps, sr, [(80, -18), (220, -8), (900, -2), (2600, 0.8), (5600, -2.5), (9500, -7), (14000, -13)])
    return out + taps * wet


def small_room_reverb(data, sr, wet=0.08):
    taps = [(0.053, 0.42), (0.089, 0.32), (0.137, 0.24), (0.211, 0.16), (0.337, 0.09)]
    verb = np.zeros_like(data)
    for seconds, gain in taps:
        n = int(seconds * sr)
        if 0 < n < data.shape[0]:
            verb[n:] += data[:-n] * gain
    verb = spectral_tilt(verb, sr, [(80, -14), (250, -5), (900, -1.5), (2600, -0.5), (6000, -3.5), (12000, -9)])
    return data + verb * wet


def wide_plate_reverb(data, sr, wet=0.18):
    taps = [(0.071, 0.45), (0.119, 0.38), (0.173, 0.31), (0.271, 0.24), (0.389, 0.18), (0.521, 0.12), (0.731, 0.08)]
    verb = np.zeros_like(data)
    for i, (seconds, gain) in enumerate(taps):
        n = int(seconds * sr)
        if 0 < n < data.shape[0]:
            shifted = data[:-n].copy()
            if i % 2:
                shifted = shifted[:, ::-1]
            verb[n:] += shifted * gain
    verb = ms_width(verb, 1.65)
    verb = spectral_tilt(verb, sr, [(80, -20), (240, -9), (700, -3), (1800, -0.5), (4200, 0.1), (7000, -3.8), (12000, -10)])
    return data + verb * wet


def duck_against(side, key, amount=0.34):
    env = moving_rms_envelope(key, 2048, 256)
    norm = env / max(float(np.percentile(env, 95)), 1e-8)
    duck = 1.0 - np.clip(norm, 0.0, 1.0) * amount
    return side * duck[:, None]


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
    tracks += item_block(female_mix_path, "PRINT female layer mix muted reference", True)
    return f'''<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 0 0
  RIPPLE 0 0
  RENDER_FILE "{RENDERS / (SLUG + '_reaper_print.wav')}"
  RENDER_FMT 0 2 {sr}
  RENDER_RANGE 1 0 {duration:.12f} 0 1000
  SAMPLERATE {sr} 1 0
  TEMPO 84 4 4 0
  PLAYRATE 1 0 0.25 4
  MARKER 1 0 "v04: female voice placed as panned delay/reverb instrument layer" 0 0 1 B {{00000000-0000-0000-0000-000000000101}} 0 2
  MARKER 2 0 "hard-tune feel and dynamic deharsh EQ applied; MP3-derived female source" 0 0 1 B {{00000000-0000-0000-0000-000000000102}} 0 2
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

    lead_clean = envelope_gate(loaded["lead"], -47, -32, -7)
    lead_clean = spectral_tilt(lead_clean, sr, [(35, -28), (85, -8), (145, -2.0), (260, -2.8), (850, -0.2), (1650, 0.35), (3200, -2.9), (4800, 0.35), (7600, -2.8), (11500, -3.7)])
    lead_clean = soft_compress(lead_clean, -21, 1.85, -0.35)
    lead_clean = hard_tune_gloss(lead_clean)
    lead_clean = delay(lead_clean, sr, 0.285, 0.10, 0.075)
    lead_clean = small_room_reverb(lead_clean, sr, 0.055)
    lead_clean = dynamic_deharsh(lead_clean, sr)
    lead_clean = saturate(lead_clean, 1.01, 0.018)

    backing_clean = envelope_gate(loaded["backing"], -48, -33, -11)
    backing_clean = spectral_tilt(backing_clean, sr, [(35, -30), (120, -8), (260, -2.8), (900, -1.2), (2200, -3.4), (4800, -0.3), (8500, -2.5), (13000, -4.0)])
    backing_clean = dynamic_deharsh(ms_width(soft_compress(backing_clean, -24, 1.9, -5.0), 1.22), sr)

    drums = saturate(spectral_tilt(loaded["drums"], sr, [(35, -3), (62, 1.0), (135, 0.1), (310, -2.4), (1400, -0.8), (3600, -1.6), (8000, -1.9), (14000, -3.2)]), 1.28, 0.22) * amp(-1.1)
    bass = saturate(spectral_tilt(loaded["bass"], sr, [(30, -3), (58, 1.7), (105, 0.9), (255, -2.2), (700, 0.3), (2500, -2.7), (9000, -10)]), 1.48, 0.28) * amp(-0.7)
    synth = ms_width(spectral_tilt(loaded["synth"], sr, [(60, -7), (190, -2.5), (650, -0.3), (1600, -2.3), (3200, -3.4), (6200, -2.4), (12000, -3.8)]), 1.12) * amp(-2.5)
    other = ms_width(spectral_tilt(loaded["other"], sr, [(60, -7), (210, -2.8), (800, -0.5), (1900, -2.8), (4200, -2.8), (8500, -2.4), (13000, -3.6)]), 1.08) * amp(-2.9)

    female_layer = np.zeros_like(lead_clean)
    if FEMALE_CANDIDATE.exists():
        f_sr, female = read_wav(FEMALE_CANDIDATE)
        if f_sr != sr:
            raise ValueError("female candidate must be converted to 48 kHz WAV first")
        female = pad_to(female, length)
        female = center_focus(female, 0.18)
        female = envelope_gate(female, -47, -32, -18)
        female = spectral_tilt(female, sr, [(45, -42), (140, -23), (260, -12), (650, -6.0), (1250, -1.2), (2400, 0.6), (4300, -0.2), (7600, -3.8), (13000, -9.0)])
        female = hard_tune_gloss(female)
        female = ping_pong_delay(female, sr, 0.214, 0.333, 0.16, 0.42)
        female = wide_plate_reverb(female, sr, 0.24)
        female = ms_width(dynamic_deharsh(female, sr), 1.55)
        female = duck_against(female, lead_clean, 0.26)
        female_layer = soft_compress(female, -23, 1.75, -1.2) * amp(-1.5)

    proc = {
        "lead_clear": limiter(lead_clean, -1.5),
        "backing_clean": limiter(backing_clean, -1.5),
        "drums_v02": limiter(drums, -1.5),
        "bass_v02": limiter(bass, -1.5),
        "synth_v02": limiter(synth, -1.5),
        "other_v02": limiter(other, -1.5),
        "female_layer_mp3_derived_wide_fx": limiter(female_layer, -3.5),
    }

    track_paths = []
    for name, data in proc.items():
        out = WORK / f"processed_{name}.wav"
        write_wav(out, sr, data)
        track_paths.append((name, out))

    premaster = (
        lead_clean * amp(-1.2)
        + backing_clean * amp(-7.0)
        + drums * amp(-0.9)
        + bass * amp(-0.8)
        + synth * amp(-2.2)
        + other * amp(-2.5)
    )
    premaster = dynamic_deharsh(premaster, sr)
    premaster = limiter(soft_compress(premaster, -13.2, 1.28, -1.0), -6.5)
    premaster_path = RENDERS / f"{SLUG}_premaster_48k16.wav"
    write_wav(premaster_path, sr, premaster)

    master = spectral_tilt(premaster, sr, [(30, -1.4), (70, 0.25), (180, -0.1), (420, -0.45), (1200, 0.05), (2800, 0.18), (5200, 0.05), (8200, -1.6), (14500, -2.8)])
    master = dynamic_deharsh(master, sr)
    master = saturate(soft_compress(master, -15.0, 1.28, 1.65), 1.025, 0.025)
    master = limiter(normalize_peak(master, -1.0), -1.0)
    master_path = RENDERS / f"{SLUG}_MASTER_clear_vocal_48k16.wav"
    write_wav(master_path, sr, master)

    female_mix = premaster + female_layer * amp(2.3)
    female_mix = spectral_tilt(female_mix, sr, [(30, -1.5), (70, 0.2), (180, -0.2), (430, -0.7), (1300, -0.1), (2800, 0.08), (5200, -0.05), (8500, -1.8), (14500, -3.0)])
    female_mix = dynamic_deharsh(female_mix, sr)
    female_mix = saturate(soft_compress(female_mix, -15.2, 1.28, 1.55), 1.025, 0.025)
    female_mix = limiter(normalize_peak(female_mix, -1.0), -1.0)
    female_mix_path = RENDERS / f"{SLUG}_MASTER_female_layer_mix_48k16.wav"
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
        "female_layer_mix_metrics": metrics(female_mix),
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
- Revision goal: smoother vocal compression, less crackle, more audible female layer, vocal tune feel, delay/reverb, and balanced full master EQ.
- Male lead remains the main vocal.
- Suno female candidate was included only in the separate experiment render because it is an MP3 full mix, not an isolated stem.

## Outputs
- Clear vocal master: `{master_path}`
- Female layer mix: `{female_mix_path}`
- Premaster: `{premaster_path}`
- Clean vocal reference: `{vocal_ref_path}`
- REAPER project: `{rpp_path}`

## Mix Moves
- Added envelope-based cleanup to lead/backing vocals to lower quiet hiss and tail noise.
- Re-EQed lead vocal with less mud, less harsh upper glare, and more 1.7 kHz / 4.8 kHz intelligibility.
- Tucked backing vocal and widened it slightly so it supports instead of clouding the lead.
- Reduced instrumental masking around the vocal presence band, especially synth/other bed and drum bite.
- Master EQ is brighter in the vocal presence range but rolled off above the harsh air band.
- Female layer mix uses the Suno MP3 candidate as a very low, center-focused texture only.

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

    print(json.dumps({"ok": True, "master": str(master_path), "female_layer_mix": str(female_mix_path), "zip": str(zip_path), "analysis": analysis}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
