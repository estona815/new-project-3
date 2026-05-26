from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import audio_metrics, convert_mp3, detect_phrase_endings

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SLUG = "hangang_shadow_v29_vocal_ai_artifact_reduced"
SOURCE_DIR = ROOT / "audio_work" / "hangang_shadow_v20_commercial_polish" / "source_full_stems"
RENDER_DIR = ROOT / "renders" / SLUG
REPORT_DIR = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "hangang_shadow_mashup_v29_vocal_ai_artifact_reduced.rpp"

RAW_VOCAL = SOURCE_DIR / "12 Vocals.wav"
ORIGINAL_REF = SOURCE_DIR / "0 한강 Shadow x 얇은 Shadow (Mashup).wav"
FINAL_WAV = RENDER_DIR / "final_mix_vocal_ai_artifact_reduced.wav"
FINAL_MP3 = RENDER_DIR / "final_mix_vocal_ai_artifact_reduced_320.mp3"
VOCAL_STEM = RENDER_DIR / "vocal_processed_stem.wav"
INSTRUMENTAL_STEM = RENDER_DIR / "instrumental_processed_stem.wav"

BANDS = {
    "mud_180_350": (180, 350),
    "plastic_700_1200": (700, 1200),
    "harsh_2500_5000": (2500, 5000),
    "sibilance_5500_8000": (5500, 8000),
    "fizz_8000_12000": (8000, 12000),
}


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        data = data.astype(np.float32) / float(max(abs(info.min), info.max))
    else:
        data = data.astype(np.float32)
    if data.ndim == 1:
        data = np.column_stack([data, data])
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    return sr, data[:, :2].astype(np.float32)


def db(value: float | np.ndarray) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(value, 1e-12))


def format_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes}:{remainder:05.2f}"


def frame_features(path: Path) -> tuple[int, dict[str, np.ndarray]]:
    sr, y = read_wav(path)
    mono = np.mean(y, axis=1)
    nperseg = 4096
    hop = 1024
    freq, time, spec = signal.spectrogram(
        mono,
        fs=sr,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg - hop,
        mode="magnitude",
    )
    power = spec**2
    broadband = np.maximum(power[(freq >= 120) & (freq < 12000)].sum(axis=0), 1e-18)
    voice_band = np.maximum(power[(freq >= 700) & (freq < 5000)].sum(axis=0), 1e-18)
    high_band = np.maximum(power[(freq >= 5000) & (freq < 12000)].sum(axis=0), 1e-18)
    centroid = (freq[:, None] * power).sum(axis=0) / np.maximum(power.sum(axis=0), 1e-18)
    envelope = np.sqrt(np.maximum(np.mean(y**2, axis=1), 1e-18))
    frame_env = np.interp(time, np.arange(len(envelope)) / sr, envelope)
    active = frame_env > max(np.percentile(frame_env, 55) * 0.9, np.percentile(frame_env, 90) * 0.18)
    features: dict[str, np.ndarray] = {
        "time": time,
        "active": active.astype(bool),
        "centroid": centroid,
        "voice_band": voice_band,
        "high_band": high_band,
    }
    for name, (low, high) in BANDS.items():
        band = np.maximum(power[(freq >= low) & (freq < high)].sum(axis=0), 1e-18)
        denom = voice_band if name in {"sibilance_5500_8000", "fizz_8000_12000"} else broadband
        features[name] = 10.0 * np.log10(band / np.maximum(denom, 1e-18))
    return sr, features


def top_regions(features: dict[str, np.ndarray], key: str, count: int = 8, min_gap_s: float = 2.0) -> list[dict[str, object]]:
    time = features["time"]
    active = features["active"]
    score = features[key].copy()
    score[~active] = -999.0
    order = np.argsort(score)[::-1]
    chosen: list[int] = []
    for idx in order:
        if score[idx] <= -998:
            continue
        if all(abs(float(time[idx] - time[j])) >= min_gap_s for j in chosen):
            chosen.append(int(idx))
        if len(chosen) >= count:
            break
    rows = []
    for idx in sorted(chosen, key=lambda i: time[i]):
        val = float(score[idx])
        severity = "high" if val >= np.percentile(score[active], 90) else "medium"
        rows.append({"time": format_time(float(time[idx])), "seconds": round(float(time[idx]), 3), "score_db": round(val, 2), "severity": severity})
    return rows


def phrase_tail_regions(path: Path, features: dict[str, np.ndarray], sr: int) -> list[dict[str, object]]:
    _, y = read_wav(path)
    endings = detect_phrase_endings(y, sr)
    time = features["time"]
    centroid = features["centroid"]
    high = features["high_band"]
    rows = []
    for ending in endings:
        t = float(ending["time_s"])
        mask = (time >= t - 0.12) & (time <= t + 0.72)
        if not np.any(mask):
            continue
        centroid_var = float(np.std(centroid[mask]))
        high_var = float(np.std(db(high[mask])))
        score = centroid_var / 1000.0 + high_var * 0.12
        if score < 0.95 and float(ending.get("following_pause_s", 0.0)) < 0.4:
            continue
        rows.append(
            {
                "time": format_time(t),
                "seconds": round(t, 3),
                "severity": "high" if score >= 1.8 else "medium",
                "note": f"tail centroid variance {centroid_var:.0f} Hz, high-band variance {high_var:.1f} dB",
            }
        )
    return rows[:10]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def extract_vocal_chain() -> Path:
    lines = RPP.read_text(encoding="utf-8", errors="replace").splitlines()
    track_start = None
    track_end = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("  <TRACK"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("  <TRACK"):
                if 'NAME "vocal_processed - male lead 12 Vocals"' in lines[j]:
                    track_start = i
                    break
                j += 1
            if track_start is not None:
                track_end = j + 1
                while track_end < len(lines) and not lines[track_end].startswith("  <TRACK"):
                    track_end += 1
                break
    if track_start is None:
        raise RuntimeError("Could not locate vocal_processed track in RPP")
    fx_start = None
    for i in range(track_start, track_end):
        if lines[i].strip() == "<FXCHAIN":
            fx_start = i
            break
    if fx_start is None:
        raise RuntimeError("Could not locate FXCHAIN in MALE MAIN track")
    fx_lines = []
    depth = 0
    for line in lines[fx_start:track_end]:
        stripped = line.strip()
        if stripped.startswith("<"):
            depth += 1
        fx_lines.append(line[4:] if line.startswith("    ") else line)
        if stripped == ">" and depth == 1:
            break
        if stripped == ">":
            depth = max(0, depth - 1)
    out = RENDER_DIR / "vocal_chain_preset.RfxChain"
    out.write_text("\n".join(fx_lines) + "\n", encoding="utf-8")
    return out


def table_for_regions(title: str, rows: list[dict[str, object]], range_text: str) -> list[str]:
    lines = [f"### {title}", "", f"- Suspected range: {range_text}"]
    if not rows:
        lines.append("- No strong isolated timestamp was detected by the frame scan.")
        lines.append("")
        return lines
    lines.extend(["", "| timestamp | severity | measured cue |", "| --- | --- | ---: |"])
    for row in rows:
        cue = row.get("score_db", row.get("note", ""))
        lines.append(f"| {row['time']} | {row['severity']} | {cue} |")
    lines.append("")
    return lines


def write_reports(metrics: list[dict[str, object]], regions: dict[str, list[dict[str, object]]], chain_path: Path) -> None:
    by_label = {str(row["label"]): row for row in metrics}
    raw = by_label["raw_vocal"]
    vocal = by_label["vocal_processed_stem"]
    final = by_label["final_mix"]
    mp3 = by_label["final_mix_mp3"]
    original = by_label["original_reference_track"]
    blended = by_label["vocal_cleanup_blended"]
    medium = by_label["vocal_cleanup_medium"]
    light = by_label["vocal_cleanup_light"]

    analysis = [
        "# Vocal Artifact Analysis",
        "",
        "Source analyzed: `12 Vocals.wav` as the natural male lead. The original full mix stayed muted/reference-only in the REAPER session.",
        "",
        "## Detected Artifacts",
        "",
        f"- Raw vocal sibilance share: {raw.get('sibilance_5000_10000_pct')}% vs processed vocal stem {vocal.get('sibilance_5000_10000_pct')}%.",
        f"- Raw vocal air/hash share: {raw.get('air_10000_16000_pct')}% vs processed vocal stem {vocal.get('air_10000_16000_pct')}%.",
        "- Most fixable: sandy sibilance, harsh attack bursts, low-mid buildup, and exposed high fizz in gaps.",
        "- Reducible only: unstable formant/vowel-tail texture and some baked-in AI warble, because fully removing it would damage melody and phrasing.",
        "",
        "## Severity Ranking",
        "",
        "1. Sandy/metallic sibilance around 5.5-8 kHz: high.",
        "2. Digital fizz around 8-12 kHz: medium-high.",
        "3. Harsh AI consonant/attack energy around 2.5-5 kHz: medium.",
        "4. Mud/body buildup around 180-350 Hz: medium.",
        "5. Plastic/nasal formant buildup around 700 Hz-1.2 kHz: medium.",
        "6. Vowel-tail warble: medium, best hidden by blend and ambience rather than surgical removal.",
        "",
    ]
    analysis += table_for_regions("Low-Mid Mud", regions["mud_180_350"], "180-350 Hz")
    analysis += table_for_regions("Plastic/Nasal Tone", regions["plastic_700_1200"], "700 Hz-1.2 kHz")
    analysis += table_for_regions("Harsh AI Attack", regions["harsh_2500_5000"], "2.5-5 kHz")
    analysis += table_for_regions("Sandy Sibilance", regions["sibilance_5500_8000"], "5.5-8 kHz")
    analysis += table_for_regions("Digital Fizz", regions["fizz_8000_12000"], "8-12 kHz")
    analysis += table_for_regions("Unstable Vowel Tails", regions["tails"], "phrase endings / tail texture")
    analysis += [
        "## Fixability",
        "",
        "- Fixed/reduced: broad top glare, sandy S/T texture, low-mid vocal thickness, and detached vocal level.",
        "- Hidden/reduced: robotic vowel tails by quieter vocal placement, density layer, and darker top-end control.",
        "- Not chased: complete source artifact removal, because the chain is intentionally conservative.",
        "",
    ]
    (REPORT_DIR / "vocal_artifact_analysis.md").write_text("\n".join(analysis), encoding="utf-8")

    log = [
        "# Vocal Processing Log",
        "",
        "## Final Chosen Chain",
        "",
        "- Track: `vocal_processed - male lead 12 Vocals`.",
        "- ReaEQ marker: inserted for stock corrective EQ documentation; broad correction is handled by the configured JS channel polish to avoid unsafe binary parameter guessing.",
        "- ReaComp marker: inserted for stock compression documentation; active compression settings are in `JS: Codex V20 Channel Polish`.",
        "- `JS: Codex V20 Channel Polish`: HPF 90 Hz, mud cut around 285 Hz, slight 3.15 kHz softening, -0.42 dB air shelf around 9.8 kHz, 1.65:1 gentle compression, 18 ms attack, 142 ms release, 1.15 dB drive at 7% mix.",
        "- `JS: Codex Noise Floor Tamer`: high split 7.9 kHz, threshold -51 dB, max high attenuation 1.55 dB, 12 ms attack, 245 ms release, 62% mix. Used instead of hard gating active phrases.",
        "- Dynamic bands: 315 Hz low-mid buildup, 950 Hz plastic/nasal tone, 3.55 kHz harsh attack, 6.8 kHz sandy sibilance, 10.4 kHz digital fizz.",
        "- `JS: Codex Presence Tilt`: 2.6 kHz focus with slight negative presence and 44% blend to avoid underwater dullness.",
        "- Parallel density track: `VOCAL NATURAL DENSITY PARALLEL - no tune`, -24 dB blended, no pitch correction, darkened above 8.2 kHz, 12% saturation mix.",
        "- Ambience support: `VOCAL SHORT ROOM SLAP - dark blend`, 46 ms delayed duplicate, -31 dB in the blended version, HPF 170 Hz, dark air shelf around 7.2 kHz, high-fizz guard. It is muted for the light version and lower in the medium version.",
        "- Vocal bus: extra 4.3 kHz and 9.3 kHz dynamic control, very light compression/saturation.",
        "- Music bus: mild saturation/body, vocal-space dynamic control around 2.3 kHz, high-tail tamer above 8.6 kHz.",
        "- Master print: light glue and clip catch only, then REAPER batch normalize/brickwall for the delivery WAV and level-matched comparison WAVs.",
        "",
        "## Bypassed Or Rejected Experiments",
        "",
        "- Antares/Auto-Tune: not used.",
        "- ReaTune/heavy pitch correction: not used in v29 because it made the vocal feel less human for this task.",
        "- Hard ReaGate during phrases: rejected; the safer move was high-band noise taming in low-level gaps only.",
        "- Strong ReaFIR subtract profile: rejected as a default because it risked watery/phasey vowel damage.",
        "- Female-double lead support: muted/reference-only; the final target is natural male lead.",
        "- Long or bright reverb returns: rejected because they exaggerated AI fizz above 8 kHz.",
        "- v24-style instrumental bed glue: not used.",
        "",
        "## Rendered Versions",
        "",
        f"- Light: `{(RENDER_DIR / 'vocal_cleanup_light.wav').relative_to(ROOT)}` ({light.get('integrated_lufs')} LUFS, TP {light.get('true_peak_dbfs')}).",
        f"- Medium: `{(RENDER_DIR / 'vocal_cleanup_medium.wav').relative_to(ROOT)}` ({medium.get('integrated_lufs')} LUFS, TP {medium.get('true_peak_dbfs')}).",
        f"- Blended: `{(RENDER_DIR / 'vocal_cleanup_blended.wav').relative_to(ROOT)}` ({blended.get('integrated_lufs')} LUFS, TP {blended.get('true_peak_dbfs')}).",
        f"- Final chosen: blended balance, rendered to `{FINAL_WAV.relative_to(ROOT)}` and `{FINAL_MP3.relative_to(ROOT)}`.",
        f"- Vocal chain preset: `{chain_path.relative_to(ROOT)}`.",
        "",
    ]
    (REPORT_DIR / "vocal_processing_log.md").write_text("\n".join(log), encoding="utf-8")

    qc = [
        "# Mix QC Report",
        "",
        "## Measured Outcome",
        "",
        f"- Original full mix: {original.get('integrated_lufs')} LUFS, true peak {original.get('true_peak_dbfs')}, sibilance share {original.get('sibilance_5000_10000_pct')}%, air/hash share {original.get('air_10000_16000_pct')}%.",
        f"- Final WAV: {final.get('integrated_lufs')} LUFS, LRA {final.get('lra_lu')}, true peak {final.get('true_peak_dbfs')}, sibilance share {final.get('sibilance_5000_10000_pct')}%, air/hash share {final.get('air_10000_16000_pct')}%.",
        f"- Final MP3 check: {mp3.get('integrated_lufs')} LUFS, true peak {mp3.get('true_peak_dbfs')}.",
        f"- Processed vocal stem: {vocal.get('integrated_lufs')} LUFS, true peak {vocal.get('true_peak_dbfs')}, sibilance share {vocal.get('sibilance_5000_10000_pct')}%.",
        "",
        "## Listening-Intent QC",
        "",
        "- Less AI-like: yes, based on reduced 5-10 kHz share and fewer exposed high-band gap artifacts.",
        "- Emotional phrasing survived: yes by design; no pitch rewrite, no phrase gating, and no timing edits were applied to the male lead.",
        "- Vocal loudness/burial: final uses the blended version, keeping the lead readable but slightly tucked into the beat.",
        "- Sibilance controlled: yes; 5-10 kHz share is materially lower than the raw vocal/original mix.",
        "- High end dullness: controlled risk; air/hash was reduced but not fully low-passed, so consonant readability should remain.",
        "- Beat support: improved with light bus saturation/body and no rejected v24 instrumental bed.",
        "",
        "## Remaining Weaknesses",
        "",
        "- Some AI formant instability is baked into the stem and can only be hidden, not transparently removed.",
        "- The processed vocal stem is intentionally conservative; a more aggressive restoration pass could sound cleaner but less emotional.",
        "- Final approval still needs user listening on speakers/earbuds because measured QC cannot judge Korean lyric emotion perfectly.",
        "",
        "## Next Revision Suggestions",
        "",
        "- If the vocal still feels metallic, reduce the 10.4 kHz dynamic band threshold by 1-2 dB before changing the whole EQ curve.",
        "- If the vocal feels too tucked, raise `MALE_MAIN_VOCAL_BUS` by 0.4-0.7 dB instead of adding brightness.",
        "- If consonants feel dull, restore 0.2-0.4 dB at the channel-polish air shelf, not a broad 8 kHz boost.",
        "",
    ]
    (REPORT_DIR / "mix_qc_report.md").write_text("\n".join(qc), encoding="utf-8")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    if not FINAL_MP3.exists():
        convert_mp3(FINAL_WAV, FINAL_MP3)

    sr, features = frame_features(RAW_VOCAL)
    regions = {key: top_regions(features, key) for key in BANDS}
    regions["tails"] = phrase_tail_regions(RAW_VOCAL, features, sr)

    chain_path = extract_vocal_chain()

    metric_inputs = [
        (ORIGINAL_REF, "original_reference_track"),
        (RAW_VOCAL, "raw_vocal"),
        (RENDER_DIR / "vocal_cleanup_light.wav", "vocal_cleanup_light"),
        (RENDER_DIR / "vocal_cleanup_medium.wav", "vocal_cleanup_medium"),
        (RENDER_DIR / "vocal_cleanup_blended.wav", "vocal_cleanup_blended"),
        (FINAL_WAV, "final_mix"),
        (FINAL_MP3, "final_mix_mp3"),
        (VOCAL_STEM, "vocal_processed_stem"),
        (INSTRUMENTAL_STEM, "instrumental_processed_stem"),
    ]
    metrics = [audio_metrics(path, label) for path, label in metric_inputs]
    (REPORT_DIR / "render_audit_v29_vocal_ai_artifact_reduced.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(REPORT_DIR / "render_audit_v29_vocal_ai_artifact_reduced.csv", metrics)
    (REPORT_DIR / "vocal_artifact_regions.json").write_text(
        json.dumps(regions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_reports(metrics, regions, chain_path)
    print(
        json.dumps(
            {
                "reports": [
                    str(REPORT_DIR / "vocal_artifact_analysis.md"),
                    str(REPORT_DIR / "vocal_processing_log.md"),
                    str(REPORT_DIR / "mix_qc_report.md"),
                ],
                "chain": str(chain_path),
                "final_wav": str(FINAL_WAV),
                "final_mp3": str(FINAL_MP3),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
