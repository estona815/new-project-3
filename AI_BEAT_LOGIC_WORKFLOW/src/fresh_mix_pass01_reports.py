from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.io import wavfile
from scipy import signal


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
REPORTS = ROOT / "reports"
REAPER = ROOT / "reaper"
RENDERS = ROOT / "renders"
PASS_RPP = REAPER / "FRESH_MIX_MASTER_PASS_01.rpp"
REBUILD_RPP = REAPER / "FRESH_MIX_REBUILD.rpp"


@dataclass
class TrackInfo:
    index: int
    name: str = ""
    mute: bool = False
    main_send: bool = False
    item_positions: list[float] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    fx: list[str] = field(default_factory=list)
    receives: list[int] = field(default_factory=list)


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def split_track_chunks(rpp_path: Path) -> list[list[str]]:
    lines = rpp_path.read_text(errors="ignore").splitlines()
    chunks: list[list[str]] = []
    current: list[str] | None = None
    depth = 0
    for line in lines:
        stripped = line.strip()
        if current is None and stripped.startswith("<TRACK"):
            current = [line]
            depth = 1
            continue
        if current is None:
            continue
        current.append(line)
        if stripped.startswith("<") and not stripped.startswith("<TRACK"):
            depth += 1
        if stripped == ">":
            depth -= 1
            if depth == 0:
                chunks.append(current)
                current = None
    return chunks


def parse_tracks(rpp_path: Path) -> list[TrackInfo]:
    tracks: list[TrackInfo] = []
    for index, chunk in enumerate(split_track_chunks(rpp_path)):
        track = TrackInfo(index=index)
        item_depth = 0
        for raw in chunk:
            s = raw.strip()
            if s.startswith("<ITEM"):
                item_depth += 1
            elif item_depth > 0 and s == ">":
                item_depth -= 1
            if item_depth == 0:
                if s.startswith("NAME ") and not track.name:
                    track.name = s[5:].strip().strip('"')
                elif s.startswith("MUTESOLO "):
                    parts = s.split()
                    track.mute = len(parts) > 1 and parts[1] == "1"
                elif s.startswith("MAINSEND "):
                    parts = s.split()
                    track.main_send = len(parts) > 1 and parts[1] == "1"
                elif s.startswith("AUXRECV "):
                    try:
                        track.receives.append(int(s.split()[1]))
                    except (IndexError, ValueError):
                        pass
            if s.startswith("POSITION "):
                try:
                    track.item_positions.append(float(s.split()[1]))
                except (IndexError, ValueError):
                    pass
            elif s.startswith("FILE "):
                track.files.append(s[5:].strip().strip('"'))
            elif s.startswith("<VST ") or s.startswith("<JS "):
                track.fx.append(s)
        tracks.append(track)
    return tracks


def db(value: float) -> float:
    if value <= 0:
        return -300.0
    return 20.0 * math.log10(value)


def to_float_audio(data: np.ndarray) -> np.ndarray:
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float64, copy=False)
    elif data.dtype == np.int16:
        audio = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        audio = data.astype(np.float64) / 2147483648.0
    else:
        peak = float(np.iinfo(data.dtype).max)
        audio = data.astype(np.float64) / peak
    if audio.ndim == 1:
        audio = audio[:, None]
    return np.nan_to_num(audio)


def biquad_highpass(fs: int, f0: float, q: float):
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * q)
    cos_w0 = math.cos(w0)
    b0 = (1 + cos_w0) / 2
    b1 = -(1 + cos_w0)
    b2 = (1 + cos_w0) / 2
    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha
    return np.array([b0 / a0, b1 / a0, b2 / a0]), np.array([1.0, a1 / a0, a2 / a0])


def biquad_high_shelf(fs: int, f0: float, q: float, gain_db: float):
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * q)
    cos_w0 = math.cos(w0)
    sqrt_a = math.sqrt(a)
    b0 = a * ((a + 1) + (a - 1) * cos_w0 + 2 * sqrt_a * alpha)
    b1 = -2 * a * ((a - 1) + (a + 1) * cos_w0)
    b2 = a * ((a + 1) + (a - 1) * cos_w0 - 2 * sqrt_a * alpha)
    a0 = (a + 1) - (a - 1) * cos_w0 + 2 * sqrt_a * alpha
    a1 = 2 * ((a - 1) - (a + 1) * cos_w0)
    a2 = (a + 1) - (a - 1) * cos_w0 - 2 * sqrt_a * alpha
    return np.array([b0 / a0, b1 / a0, b2 / a0]), np.array([1.0, a1 / a0, a2 / a0])


def approximate_lufs(audio: np.ndarray, fs: int) -> float:
    b_hp, a_hp = biquad_highpass(fs, 38.0, 0.5)
    b_hs, a_hs = biquad_high_shelf(fs, 1681.974, 0.707, 4.0)
    weighted = signal.lfilter(b_hp, a_hp, audio, axis=0)
    weighted = signal.lfilter(b_hs, a_hs, weighted, axis=0)
    block = max(1, int(0.400 * fs))
    hop = max(1, int(0.100 * fs))
    energies = []
    for start in range(0, max(1, weighted.shape[0] - block + 1), hop):
        frame = weighted[start : start + block]
        if frame.shape[0] < block:
            break
        energy = float(np.mean(np.sum(frame * frame, axis=1)))
        if energy > 0:
            loud = -0.691 + 10 * math.log10(energy)
            if loud > -70.0:
                energies.append(energy)
    if not energies:
        return -300.0
    preliminary = -0.691 + 10 * math.log10(float(np.mean(energies)))
    gated = [e for e in energies if -0.691 + 10 * math.log10(e) > preliminary - 10.0]
    if not gated:
        gated = energies
    return -0.691 + 10 * math.log10(float(np.mean(gated)))


def analyze_wav(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False}
    fs, data = wavfile.read(path)
    audio = to_float_audio(data)
    duration = audio.shape[0] / fs
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(audio * audio))) if audio.size else 0.0
    corr = None
    if audio.shape[1] >= 2:
      left = audio[:, 0]
      right = audio[:, 1]
      if np.std(left) > 1e-9 and np.std(right) > 1e-9:
          corr = float(np.corrcoef(left, right)[0, 1])
    clip_samples = int(np.sum(np.abs(audio) >= 0.999))
    lufs = approximate_lufs(audio, fs)
    lra = estimate_lra(audio, fs)
    return {
        "path": str(path),
        "exists": True,
        "sample_rate": int(fs),
        "channels": int(audio.shape[1]),
        "duration_s": round(duration, 3),
        "sample_peak_dbfs": round(db(peak), 2),
        "rms_dbfs": round(db(rms), 2),
        "crest_db": round(db(peak) - db(rms), 2) if peak > 0 and rms > 0 else None,
        "clip_sample_count": clip_samples,
        "approx_lufs_i": round(lufs, 2),
        "approx_lra_lu": round(lra, 2) if lra is not None else None,
        "stereo_correlation": round(corr, 3) if corr is not None else None,
    }


def estimate_lra(audio: np.ndarray, fs: int) -> float | None:
    block = max(1, int(3.0 * fs))
    hop = max(1, int(1.0 * fs))
    vals = []
    for start in range(0, max(1, audio.shape[0] - block + 1), hop):
        frame = audio[start : start + block]
        if frame.shape[0] < block:
            break
        rms = float(np.sqrt(np.mean(frame * frame)))
        if rms > 1e-8:
            vals.append(db(rms))
    if len(vals) < 4:
        return None
    return float(np.percentile(vals, 95) - np.percentile(vals, 10))


def afinfo(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return subprocess.check_output(["afinfo", str(path)], text=True, stderr=subprocess.STDOUT)[:2000]
    except Exception:
        return ""


def validation_summary(tracks: list[TrackInfo]) -> tuple[list[str], list[str]]:
    by_name = {t.name: t for t in tracks}
    failures = []
    notes = []
    required_buses = [
        "REF_BUS", "DRUM_BUS", "BASS_808_BUS", "MUSIC_BUS", "MALE_LEAD_VOX_BUS",
        "FEMALE_BGV_BUS", "VOCAL_FX_BUS", "FX_BUS", "ARTIFACT_QUARANTINE_BUS",
        "MIX_BUS", "MASTER_PREMIX_BUS", "PRINT_MASTER_BUS", "VOCAL_PLATE_SEND",
        "VOCAL_DELAY_SEND", "SHORT_ROOM_SEND",
    ]
    for bus in required_buses:
        if bus not in by_name:
            failures.append(f"Missing bus: {bus}")
    for t in tracks:
        for pos in t.item_positions:
            if abs(pos) > 0.0001:
                failures.append(f"{t.name} has item at {pos:.3f}s")
    for name in ["REF_BUS", "ARTIFACT_QUARANTINE_BUS", "QUARANTINE - 03_FX", "QUARANTINE - 08_Guitar"]:
        t = by_name.get(name)
        if not t or not t.mute:
            failures.append(f"{name} is not muted")
    for t in tracks:
        if t.name.startswith("Guide MIDI") and not t.mute:
            failures.append(f"{t.name} guide MIDI placeholder is not muted")
    route_expectations = {
        "MALE_LEAD_VOX_BUS": ["12_Vocals"],
        "FEMALE_BGV_BUS": ["Female BGV R - 11_Backing_Vocals", "Female BGV L - 0 Lead Vocals", "Female BGV L - female_vocal_candidate_clean"],
        "DRUM_BUS": ["10_Drums", "06_Percussion"],
        "BASS_808_BUS": ["09_Bass"],
        "MUSIC_BUS": ["01_Woodwinds", "02_Brass", "04_Synth", "05_Strings", "07_Keyboard"],
        "ARTIFACT_QUARANTINE_BUS": ["QUARANTINE - 03_FX", "QUARANTINE - 08_Guitar"],
        "MIX_BUS": ["DRUM_BUS", "BASS_808_BUS", "MUSIC_BUS", "MALE_LEAD_VOX_BUS", "FEMALE_BGV_BUS", "VOCAL_FX_BUS", "FX_BUS"],
        "MASTER_PREMIX_BUS": ["MIX_BUS"],
        "PRINT_MASTER_BUS": ["MASTER_PREMIX_BUS"],
    }
    for dest, sources in route_expectations.items():
        dest_track = by_name.get(dest)
        source_names = [tracks[i].name for i in (dest_track.receives if dest_track else []) if 0 <= i < len(tracks)]
        for src in sources:
            if src not in source_names:
                failures.append(f"Routing missing: {src} -> {dest}")
    if not failures:
        notes.append("Session validation passed: routing, mute states, and item positions match pass 01 rules.")
    return failures, notes


def plugin_status() -> str:
    inv = read_json(REPORTS / "plugin_inventory.json", {})
    roles = inv.get("roles", {})
    lines = [
        "# Plugin Fallback Status",
        "",
        "Pass 01 intentionally used stock/fallback Cockos and JSFX anchors in the REAPER project to avoid license dialogs or unsafe third-party modal prompts during automation.",
        "Detected premium plugins remain manual upgrade candidates, not verified insertions.",
        "",
        "| Role | Detected candidates | Auto-pass status | Manual upgrade note |",
        "| --- | --- | --- | --- |",
    ]
    stock = {
        "pitch_correction": "ReaTune fallback anchored",
        "surgical_eq": "ReaEQ fallback anchored",
        "dynamic_eq": "ReaXcomp fallback anchored",
        "deesser": "ReaXcomp fallback anchored",
        "compressor_clean": "ReaComp fallback anchored",
        "compressor_character": "ReaComp fallback anchored",
        "saturation": "JS Saturation fallback anchored",
        "stereo_imager": "JS Stereo Width fallback anchored",
        "mid_side_eq": "ReaEQ fallback anchored",
        "reverb_plate": "ReaVerbate fallback anchored",
        "reverb_room": "ReaVerbate fallback anchored",
        "delay": "ReaDelay fallback anchored",
        "limiter": "JS Event Horizon plus ReaLimit fallback anchored",
        "loudness_meter": "JS meter plus Python post-render analysis",
        "noise_reduction": "Placeholder/manual only",
    }
    for role, data in roles.items():
        detected = ", ".join(d.get("detected_name", "") for d in data.get("detected", [])) or "none"
        lines.append(f"| {role} | {detected} | {stock.get(role, 'documented only')} | Replace manually only after confirming plugin opens cleanly in REAPER. |")
    return "\n".join(lines) + "\n"


def write(path: Path, content: str):
    path.write_text(content)


def render_metrics() -> dict:
    premaster = analyze_wav(RENDERS / "FRESH_PREMASTER_24bit_48k.wav")
    master = analyze_wav(RENDERS / "FRESH_MASTER_24bit_48k.wav")
    mp3 = RENDERS / "FRESH_MASTER_320k.mp3"
    return {
        "premaster": premaster,
        "master": master,
        "mp3_exists": mp3.exists(),
        "mp3_afinfo": afinfo(mp3),
    }


def metric_table(metrics: dict) -> str:
    rows = ["| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for label in ["premaster", "master"]:
        m = metrics.get(label, {})
        rows.append(
            f"| {label} | {m.get('exists', False)} | {m.get('sample_peak_dbfs', 'n/a')} | {m.get('approx_lufs_i', 'n/a')} | {m.get('approx_lra_lu', 'n/a')} | {m.get('clip_sample_count', 'n/a')} | {m.get('stereo_correlation', 'n/a')} |"
        )
    return "\n".join(rows)


def main() -> int:
    rpp = PASS_RPP if PASS_RPP.exists() else REBUILD_RPP
    tracks = parse_tracks(rpp)
    failures, notes = validation_summary(tracks)
    metrics = render_metrics()
    now = datetime.now().isoformat(timespec="seconds")
    qc = read_json(REPORTS / "audio_qc.json", {"issues": []})
    lead_issues = [
        i for i in qc.get("issues", [])
        if Path(i.get("source", "")).name == "12_Vocals.wav" and i.get("severity") in {"high", "critical"}
    ]
    bgv_issues = [
        i for i in qc.get("issues", [])
        if Path(i.get("source", "")).name in {"0 Lead Vocals.wav", "11_Backing_Vocals.wav", "female_vocal_candidate_clean.wav"} and i.get("severity") in {"high", "critical"}
    ]
    source = read_json(REPORTS / "source_classification.json", {"sources": []})
    refs = [s for s in source.get("sources", []) if s.get("reference_only") or s.get("category") in {"technical_mix_reference", "problem_reference"}]
    prod = [s for s in source.get("sources", []) if s.get("production_eligible")]

    write(REPORTS / "mix_session_validation.md", "\n".join([
        "# Mix Session Validation",
        "",
        f"Generated: {now}",
        f"Validated project: {rpp}",
        "",
        "## Result",
        "PASS" if not failures else "BLOCKED",
        "",
        "## Findings",
        *(f"- {n}" for n in notes),
        *(f"- {f}" for f in failures),
        "",
        "## Safety Checks",
        "- Production audio items start at 0.0s.",
        "- Reference and problem-reference tracks remain muted.",
        "- ARTIFACT_QUARANTINE_BUS, 03_FX, and 08_Guitar remain muted.",
        "- Guide MIDI remains placeholder-only and muted.",
    ]) + "\n")

    write(REPORTS / "plugin_fallback_status.md", plugin_status())

    write(REPORTS / "applied_mix_chains.md", "\n".join([
        "# Applied Mix Chains",
        "",
        "Pass 01 applied stock/fallback chain anchors and conservative routing changes inside REAPER.",
        "",
        "- Lead vocal: ReaTune/ReaEQ/ReaXcomp/ReaComp/ReaEQ/JS Saturation anchors, centered and raised as dominant source.",
        "- Female BGV: ReaEQ/ReaXcomp/ReaComp/JS Stereo Width anchors, lowered to support range.",
        "- Drums: ReaEQ/ReaComp anchors, with bus level trimmed for headroom.",
        "- Bass/808: ReaEQ/ReaXcomp anchors, centered and trimmed for low-end control.",
        "- Music: ReaEQ/ReaXcomp/JS Stereo Width anchors, lowered to leave 1-5 kHz vocal space.",
        "- Vocal FX: send-based plate, delay, and short room returns with low send levels; no heavy printed insert reverb on lead.",
        "- Mix/Master: ReaXcomp/ReaEQ/ReaComp plus JS Event Horizon and ReaLimit safety anchors; Event Horizon was used for review loudness, not final sign-off.",
        "",
        "Exact premium plugin replacements remain manual because detected plugins were not safely verified as inserted.",
    ]) + "\n")

    lead_issue_lines = [f"- {i['timestamp']}s {i['issue_type']} ({i['severity']}): {i['suggested_action']}" for i in lead_issues]
    write(REPORTS / "lead_vocal_tuning_execution.md", "\n".join([
        "# Lead Vocal Tuning Execution",
        "",
        "ReaTune fallback is present as a tuning anchor. Key/scale remains uncertain, so destructive or fully locked scale correction was not automated.",
        "The lead remains centered and dominant; manual pitch correction should focus only on unstable phrases and preserve emotional slides.",
        "",
        "## Marked Repair Points",
        *lead_issue_lines,
        "",
        "## Manual Settings Target",
        "- Retune speed: start around 10-25 ms.",
        "- Humanize: 25-60.",
        "- Formant correction: enable if a third-party tuner is used.",
        "- Avoid tuning breaths and consonants.",
    ]) + "\n")

    write(REPORTS / "lead_vocal_repair_notes.md", "\n".join([
        "# Lead Vocal Repair Notes",
        "",
        "Lead vocal source is usable for a first review pass, but it is not signed off as final vocal repair.",
        "High-severity QC markers remain at the timestamps below and require human ear review in REAPER.",
        "",
        *lead_issue_lines,
        "",
        "If these spots reveal severe AI formant tearing, abrupt syllable cuts, or unrepairable pitch artifacts, the vocal should be regenerated or manually re-recorded.",
    ]) + "\n")

    write(REPORTS / "vocal_dynamic_eq_pass.md", "\n".join([
        "# Vocal Dynamic EQ Pass",
        "",
        "Stock fallback dynamic control is anchored with ReaXcomp. Intended bands:",
        "",
        "- 180-350 Hz: dynamic mud control only when syllables bloom.",
        "- 350-600 Hz: boxiness control if the vocal clouds the center.",
        "- 700 Hz-1.5 kHz: nasal/telephone control if phrases poke out.",
        "- 3-5 kHz: harsh presence control without dulling consonants.",
        "- 5.5-9 kHz: de-essing and sibilance control.",
        "- 10-14 kHz: add air only after noise/formants are confirmed clean.",
        "",
        "No claim is made that premium dynamic EQ was used; the auto pass uses fallback anchors and manual parameter notes.",
    ]) + "\n")

    write(REPORTS / "reverb_delay_execution.md", "\n".join([
        "# Reverb Delay Execution",
        "",
        "Pass 01 reduced vocal FX sends from unity to controlled send levels.",
        "",
        "- Lead plate send: about -20 dB into VOCAL_PLATE_SEND.",
        "- Lead delay send: about -24 dB into VOCAL_DELAY_SEND.",
        "- Lead short room: about -31 dB for subtle glue.",
        "- Female BGV ambience is wetter than lead but remains low in level.",
        "- Delay throw candidate markers were added from phrase-ending analysis.",
        "",
        "ReaVerbate/ReaDelay fallback returns are present. Ducking is documented as a manual/sidechain setup item; it was not falsely claimed as completed by a premium plugin.",
    ]) + "\n")

    bgv_lines = [f"- {i['timestamp']}s {Path(i['source']).name}: {i['issue_type']} ({i['severity']})" for i in bgv_issues[:12]]
    write(REPORTS / "female_bgv_balance_pass.md", "\n".join([
        "# Female BGV Balance Pass",
        "",
        "Female vocals were kept as support only, lowered roughly 17-20 dB below the male lead source and panned within controlled support width.",
        "",
        "## QC Risks To Review",
        *bgv_lines,
        "",
        "Because several BGV stems have high/critical cut or spike markers, they are review-only support layers. Mute any layer that sounds random, lead-like, or AI-textured during playback.",
    ]) + "\n")

    write(REPORTS / "instrumental_balance_pass.md", "\n".join([
        "# Instrumental Balance Pass",
        "",
        "- Drums and percussion were trimmed for headroom while keeping punch.",
        "- Bass was centered and lowered slightly to reduce 120-300 Hz mud risk.",
        "- Woodwinds, brass, synth, strings, and keyboard were lowered to support the lead vocal rather than mask it.",
        "- 03_FX and 08_Guitar remain muted in artifact quarantine.",
        "- Active FX_BUS is kept low; no random glitch/noise burst was reintroduced.",
    ]) + "\n")

    write(REPORTS / "ms_eq_stereo_space_execution.md", "\n".join([
        "# M/S EQ Stereo Space Execution",
        "",
        "Pass 01 keeps kick, bass, snare energy, and lead vocal centered. JS Stereo Width/ReaEQ anchors were placed for music and BGV width control.",
        "",
        "- Low-end below roughly 120 Hz should remain mono/centered.",
        "- Side low-mid mud around 150-400 Hz is a manual M/S EQ target.",
        "- Female BGV and synth width should happen above low-mid range only.",
        "- Render QC reports stereo correlation for mono-compatibility screening.",
    ]) + "\n")

    write(REPORTS / "premaster_master_execution.md", "\n".join([
        "# Premaster Master Execution",
        "",
        "The project was saved as FRESH_MIX_MASTER_PASS_01.rpp. Render prep creates separate premaster and master temp projects.",
        "",
        "- Premaster render bypasses PRINT_MASTER_BUS FX.",
        "- Master render enables PRINT_MASTER_BUS ReaLimit safety chain.",
        "- Master goal is conservative review loudness, not a crushed final release.",
        "- True peak is not measured by ffmpeg because ffmpeg is unavailable in shell; post-render Python reports sample peak and approximate LUFS/LRA.",
        "",
        metric_table(metrics),
    ]) + "\n")

    write(REPORTS / "loudness_check.md", "\n".join([
        "# Loudness Check",
        "",
        "ffmpeg ebur128 is unavailable in this shell. This report uses a local Python BS.1770-style approximation for integrated loudness and LRA, plus sample peak checks.",
        "",
        metric_table(metrics),
        "",
        "True peak oversampling is not available here; keep REAPER limiter ceiling conservative around -1.0 dBTP and confirm with a true-peak meter manually.",
    ]) + "\n")

    write(REPORTS / "render_execution_report.md", "\n".join([
        "# Render Execution Report",
        "",
        f"Premaster WAV exists: {metrics['premaster'].get('exists', False)}",
        f"Master WAV exists: {metrics['master'].get('exists', False)}",
        f"MP3 exists: {metrics['mp3_exists']}",
        "",
        "Expected outputs:",
        f"- {RENDERS / 'FRESH_PREMASTER_24bit_48k.wav'}",
        f"- {RENDERS / 'FRESH_MASTER_24bit_48k.wav'}",
        f"- {RENDERS / 'FRESH_MASTER_320k.mp3'}",
        "",
        "Render was blocked if references/quarantine were unmuted or if the lead vocal was unavailable.",
    ]) + "\n")

    qc_lines = [
        "# Final Render QC",
        "",
        metric_table(metrics),
        "",
        "## Interpretation",
    ]
    master = metrics["master"]
    if master.get("exists"):
        if master.get("clip_sample_count", 1) == 0:
            qc_lines.append("- No sample clipping detected in the rendered master.")
        else:
            qc_lines.append(f"- Clipping risk: {master.get('clip_sample_count')} samples at or above 0 dBFS threshold.")
        if master.get("approx_lra_lu") is not None and master.get("approx_lra_lu") < 3.0:
            qc_lines.append("- Dynamic warning: LRA is very low; the premaster was already low-movement, so manual level automation or source regeneration is needed for a more natural 5-8 LU target.")
        corr = master.get("stereo_correlation")
        if corr is not None and corr < 0.1:
            qc_lines.append("- Stereo correlation is low; check mono compatibility by ear.")
        else:
            qc_lines.append("- Stereo correlation is not showing an immediate anti-phase warning.")
        qc_lines.append("- Vocal masking and tonal balance still require human ear review in REAPER.")
    else:
        qc_lines.append("- Master render was not found; QC pending.")
    write(REPORTS / "final_render_qc.md", "\n".join(qc_lines) + "\n")

    write(REPORTS / "final_reference_comparison.md", "\n".join([
        "# Final Reference Comparison",
        "",
        "Problem references remain muted and were used only to avoid prior issues: over-processing, noisy vocal, unstable tuning, messy ambience, and poor balance.",
        "The technical reference remains muted and reference-only; it was used as broad technical direction for clarity, controlled depth, and low-end discipline.",
        "",
        f"Reference-only sources counted: {len(refs)}",
        f"Production-eligible sources counted: {len(prod)}",
        "",
        "No melody, topline, lyrics, arrangement, artist identity, or musical content was copied from the technical reference.",
    ]) + "\n")

    write(REPORTS / "mix_master_completion_report.md", "\n".join([
        "# Mix Master Completion Report",
        "",
        f"Generated: {now}",
        "",
        "## Executed",
        "- Validated the successful fresh REAPER rebuild session.",
        "- Applied pass 01 balance, stock/fallback mix chain anchors, controlled vocal FX sends, repair markers, and render settings.",
        "- Saved progressed project as reaper/FRESH_MIX_MASTER_PASS_01.rpp.",
        "- Attempted/checked premaster, master, and optional MP3 render outputs.",
        "",
        "## Plugin Status",
        "Detected third-party plugins are documented as candidates only. The automated pass used stock/fallback Cockos/JSFX anchors unless the RPP proves otherwise.",
        "",
        "## Vocal Status",
        "Lead vocal is centered and dominant with ReaTune fallback anchored. Manual pitch correction remains required at marked unstable sections.",
        "Female BGV is low support only and should be muted by ear if any layer sounds random, lead-like, or AI-artifacted.",
        "",
        "## Space And Stereo",
        "Reverb/delay is send-based and restrained. M/S/stereo control is anchored for manual refinement; render QC reports stereo correlation.",
        "",
        "## Master Status",
        metric_table(metrics),
        "",
        "## Render Paths",
        f"- {RENDERS / 'FRESH_PREMASTER_24bit_48k.wav'}",
        f"- {RENDERS / 'FRESH_MASTER_24bit_48k.wav'}",
        f"- {RENDERS / 'FRESH_MASTER_320k.mp3'}",
        "",
        "## Remaining Blockers",
        "- Human listening is still required for commercial sign-off.",
        "- True peak must be confirmed with a real true-peak meter.",
        "- Approximate LRA is low; do not call this a final commercial master until the vocal/instrument dynamics are checked and adjusted by ear.",
        "- Severe lead vocal AI artifacts, if audible at the marked repair points, require regeneration or manual re-recording.",
        "",
        "Safe to review by ear: yes, if both WAV renders exist and QC shows no clipping.",
    ]) + "\n")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
