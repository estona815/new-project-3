from __future__ import annotations

import csv
import importlib.util
import json
import sys
import uuid
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (  # noqa: E402
    amp_db,
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    normalize_to_rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    vocal_harmonic_density,
    write_float_wav,
)
from tools.mgmg_v11_female_70_mseq_layers import stable_master_tone  # noqa: E402


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MO = load_module(ROOT / "tools" / "0101_male_only_strong_tune_mix.py", "codex_0101_male_only")
V11 = load_module(ROOT / "tools" / "0101_v11_vocal_front_reference_rerender.py", "codex_0101_v11")

SLUG = "0101_v12_clear_dry_vocal_rerender"
BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
V10_RENDERS = ROOT / "renders" / "0101_female_candidate_v10_qc_support"
V11_RENDERS = ROOT / "renders" / "0101_v11_vocal_front_reference_rerender"
WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V12_CLEAR_DRY_PROJECT.rpp"
BPM = 135


def ensure_dirs() -> None:
    for directory in (WORK, PROCESSED, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return MO.pad_or_trim(y, length)


def safe_normalize(y: np.ndarray, target_db: float) -> np.ndarray:
    if float(np.sqrt(np.mean(np.square(y.astype(np.float64))) + 1e-12)) < 1e-10:
        return y.astype(np.float32)
    return normalize_to_rms(y, target_db).astype(np.float32)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(out)


def load_audio() -> tuple[int, dict[str, np.ndarray]]:
    paths = {
        "male_raw": BASE_STEMS / "0101_vocal_raw.wav",
        "instrumental": V10_RENDERS / "processed_instrumental_stem.wav",
        "female_layer": V10_RENDERS / "processed_female_qc_support_stem.wav",
        "melody": V10_RENDERS / "melody_stem.wav",
        "drums": V10_RENDERS / "drums_stem.wav",
        "bass": V10_RENDERS / "bass808_stem.wav",
    }
    audio: dict[str, np.ndarray] = {}
    sample_rates = set()
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(path)
        sr, y, _ = V11.read_wav(path)
        sample_rates.add(sr)
        audio[name] = y
    if sample_rates != {48000}:
        raise RuntimeError(f"Expected 48 kHz sources, got {sorted(sample_rates)}")
    length = max(len(y) for y in audio.values())
    return 48000, {name: pad_or_trim(y, length) for name, y in audio.items()}


def clear_parallel(raw: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    clear = bandpass(raw, sr, 1500, 5200, 3)
    clear = compressor(clear, sr, threshold_db=-35.0, ratio=2.3, smooth_ms=38, makeup_db=0.6)
    clear = vocal_harmonic_density(clear, sr, drive_db=1.1, wet=0.08)
    clear, attack = dynamic_band_tame(clear, sr, 3100, 5200, 1.05, 70, 52)
    clear, hiss = dynamic_band_tame(clear, sr, 6200, 11200, 1.55, 61, 46)
    clear = safe_normalize(clear, -27.0)
    return clear.astype(np.float32), {
        "stage": "v12_clear_parallel_no_reverb",
        "return_gain_db": -10.2,
        "attack_control": attack,
        "hiss_control": hiss,
    }


def body_parallel(raw: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    body = bandpass(raw, sr, 150, 620, 3)
    body = compressor(body, sr, threshold_db=-34.0, ratio=2.1, smooth_ms=82, makeup_db=0.8)
    body, mud = dynamic_band_tame(body, sr, 240, 430, 0.85, 72, 125)
    body = safe_normalize(body, -25.2)
    return body.astype(np.float32), {
        "stage": "v12_body_parallel_preserve_male_weight",
        "return_gain_db": -9.8,
        "mud_control": mud,
    }


def process_male_clear_dry(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = MO.edge_fade(raw, sr, 28.0)
    out = butter_filter(out, sr, "highpass", 74, 3)
    moves.append({"stage": "v12_low_highpass_preserve_original_clarity", "hz": 74})
    out, beep = MO.suppress_beep_artifacts(out, sr, "v12_clear_dry", strength=0.92)
    out, sip = MO.suppress_sip_breaths(out, sr, "v12_clear_dry")
    moves.extend([beep, sip])
    out, denoise = MO.spectral_denoise_vocal(
        out,
        sr,
        "v12_clear_dry",
        reduction=0.31,
        high_reduction=0.50,
        floor=0.72,
        high_floor=0.52,
    )
    moves.append({**denoise, "intent": "lighter than v11 to keep original vocal clarity"})
    for low, high, cut, pct, smooth, name in [
        (230, 400, 0.85, 70, 135, "mud"),
        (690, 1180, 1.05, 66, 105, "plastic_nasal"),
        (2750, 4500, 0.78, 72, 62, "sharp_edge_without_dulling"),
        (5400, 8500, 2.15, 60, 48, "sibilance_noise"),
        (9000, 13600, 1.35, 62, 44, "top_fizz"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"v12_dynamic_eq_{name}", **stats})
    body, body_stats = body_parallel(out, sr)
    clear, clear_stats = clear_parallel(out, sr)
    out = out * float(amp_db(0.10)) + body * float(amp_db(-9.8)) + clear * float(amp_db(-10.2))
    moves.extend([body_stats, clear_stats])
    out = biquad_peaking(out, sr, 2100, 0.55, 0.90)
    out = biquad_peaking(out, sr, 3600, 0.32, 1.05)
    out = biquad_shelf(out, sr, 10200, 0.18, True)
    out = saturate(out, drive_db=0.85, mix=0.055)
    out = compressor(out, sr, threshold_db=-24.5, ratio=1.85, smooth_ms=66, makeup_db=0.15)
    out, post_sib = dynamic_band_tame(out, sr, 5200, 9200, 1.65, 63, 47)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-20.35, max_cut_db=-5.6, max_boost_db=1.05, label="v12_clear_dry")
    moves.extend([{"stage": "v12_post_sibilance_guard", **post_sib}, ride])
    out = safe_normalize(out, -18.95)
    out = limiter(MO.edge_fade(out, sr, 18.0), -1.7)
    moves.append({"stage": "v12_final_male_gain", "target_rms_dbfs": -18.95, "vocal_fx": "none"})
    return out.astype(np.float32), moves


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    female = pad_or_trim(audio["female_layer"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)

    inst_pocket = sidechain_duck_full(inst, male, sr, amount_db=0.55, release_ms=128, threshold_percentile=61)
    melody_pocket = sidechain_duck_full(melody, male, sr, amount_db=0.12, release_ms=120, threshold_percentile=67)
    female_muted = female * 0.0
    dry_mix = MO.safe_sum(
        [
            (inst_pocket, -1.05),
            (melody_pocket, 1.22),
            (drums, -10.6),
            (bass, -10.2),
            (male, -1.75),
            (female_muted, -120.0),
        ],
        length,
        -1.75,
    )
    dry_mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(dry_mix, sr, 22.0), sr)
    dry_mix = biquad_peaking(dry_mix, sr, 2300, 0.20, 0.9)
    dry_mix = biquad_shelf(dry_mix, sr, 11200, 0.03, True)
    dry_mix = stable_master_tone(dry_mix, sr)
    dry_mix = compressor(dry_mix, sr, threshold_db=-12.0, ratio=1.045, smooth_ms=260, makeup_db=0.0)
    dry_mix = soft_clip(dry_mix, drive_db=0.18, ceiling=0.89)
    dry_mix = limiter(dry_mix, -2.2)

    premaster = RENDERS / "0101_mix_v12_clear_dry_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v12_clear_dry_vocal.wav"
    final_mp3 = RENDERS / "0101_FINAL_v12_clear_dry_vocal_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v12_clear_dry_stem.wav"
    inst_path = RENDERS / "processed_instrumental_v12_dry_pocket_stem.wav"
    melody_path = RENDERS / "melody_v12_forward_stem.wav"
    write_float_wav(premaster, sr, dry_mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-11.4, target_tp=-1.25, target_lra=4.0)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(inst_path, sr, limiter(inst_pocket, -1.8))
    write_float_wav(melody_path, sr, limiter(melody_pocket, -2.0))
    moves = [
        {
            "stage": "v12_dry_clear_mix_gain_revision",
            "male_gain_db": -1.75,
            "female_gain_db": "muted",
            "vocal_reverb_delay": "removed",
            "instrumental_gain_db": -1.05,
            "melody_gain_db": 1.22,
        },
        {"stage": "instrumental_vocal_pocket", "duck_db": 0.55},
        {"stage": "melody_light_pocket", "duck_db": 0.12},
        *mix_res,
    ]
    return {
        "premaster": premaster,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "male_stem": male_path,
        "instrumental_stem": inst_path,
        "melody_stem": melody_path,
    }, moves


def rpp_item(path: Path, length: float, iid: int, muted: bool = False) -> str:
    return f"""    <ITEM
      POSITION 0
      LENGTH {length:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0.010 0 1 0 0 0
      FADEOUT 1 0.010 0 1 0 0 0
      MUTE {1 if muted else 0} 0
      SEL 0
      IGUID {{{uuid.uuid4()}}}
      IID {iid}
      NAME {path.name}
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{uuid.uuid4()}}}
      <SOURCE WAVE
        FILE "{path}"
      >
    >"""


def rpp_track(name: str, path: Path | None, length: float, iid: int, muted: bool = False, mainsend: bool = True) -> str:
    item = rpp_item(path, length, iid, muted) if path else ""
    vol = "0.70794578438414" if muted else "1"
    return f"""  <TRACK {{{uuid.uuid4()}}}
    NAME "{name}"
    VOLPAN {vol} 0 -1 -1 1
    MUTESOLO {1 if muted else 0} 0 0
    NCHAN 2
    FX 1
    TRACKID {{{uuid.uuid4()}}}
    MAINSEND {1 if mainsend else 0} 0
{item}
  >"""


def write_rpp(sr: int, audio: dict[str, np.ndarray], paths: dict[str, Path]) -> None:
    length = len(audio["male_raw"]) / sr
    tracks = [
        rpp_track("V11_PREVIOUS muted", V11_RENDERS / "0101_FINAL_v11_vocal_front.wav", length, 1, True, False),
        rpp_track("MALE_RAW muted", BASE_STEMS / "0101_vocal_raw.wav", length, 2, True, False),
        rpp_track("MALE_VOCAL_V12_CLEAR_DRY muted", paths["male_stem"], length, 3, True, False),
        rpp_track("INSTRUMENTAL_V12_DRY_POCKET muted", paths["instrumental_stem"], length, 4, True, False),
        rpp_track("MELODY_V12_FORWARD muted", paths["melody_stem"], length, 5, True, False),
        rpp_track("MIX_BUS V12 CLEAR DRY ACTIVE", paths["final_wav"], length, 6, False, True),
        rpp_track("MASTER_MP3_MONITOR muted", paths["final_mp3"], length, 7, True, False),
    ]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip([0, 14.2, 42.7, 72.0, 101.3, length], ["intro", "verse", "hook", "section2", "outro", "end"]), start=1)
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v12 clear dry revision. Vocal reverb and delay removed. Female layer muted. Male lead is dry, forward, and clarity-preserving.
  >
  SAMPLERATE 48000 1 0
  TEMPO {BPM}.000000 4 4 0
  RENDER_RANGE 0 0 {length:.12f} 0 1000
  MASTER_NCH 2 2
{chr(10).join(markers)}
{chr(10).join(tracks)}
>
""",
        encoding="utf-8",
    )


def write_reports(paths: dict[str, Path], male_moves: list[dict[str, object]], mix_moves: list[dict[str, object]]) -> Path:
    metrics = [
        audio_metrics(paths["final_wav"], "v12_final_wav_clear_dry"),
        audio_metrics(paths["final_mp3"], "v12_final_mp3_clear_dry"),
        audio_metrics(paths["male_stem"], "v12_processed_male_clear_dry"),
        audio_metrics(BASE_STEMS / "0101_vocal_raw.wav", "raw_male_reference"),
        audio_metrics(V11_RENDERS / "0101_FINAL_v11_vocal_front.wav", "v11_previous_with_reverb"),
    ]
    write_csv(REPORTS / "final_render_metrics.csv", metrics)
    decisions = {
        "male_vocal": male_moves,
        "mix": mix_moves,
        "target": {"integrated_lufs": -11.4, "true_peak_dbfs": -1.25},
        "explicit_user_request": "remove reverb and make vocal clear",
    }
    (REPORTS / "processing_decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        {
            "version": row["label"],
            "integrated_lufs": row.get("integrated_lufs"),
            "true_peak_dbfs": row.get("true_peak_dbfs"),
            "rms_dbfs": row.get("rms_dbfs"),
            "presence_pct": row.get("presence_1500_5000_pct"),
            "sibilance_pct": row.get("sibilance_5000_10000_pct"),
            "air_pct": row.get("air_10000_16000_pct"),
        }
        for row in metrics
    ]
    (REPORTS / "final_qc_report.md").write_text(
        "\n".join(
            [
                "# Final QC Report",
                "",
                markdown_table(summary, ["version", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "presence_pct", "sibilance_pct", "air_pct"]),
                "",
                "## Revision Notes",
                "",
                "- Vocal reverb and delay were removed completely from the active mix.",
                "- Female support layer was muted to avoid lyric/pitch smear and keep the male lead clear.",
                "- Male vocal processing was rebuilt lighter than v11 to preserve the originally clear tone.",
                "- Beep/sip/noise and harsh resonance controls remain active, but high-end reduction is less aggressive than v11.",
                "- Melody was kept forward with only light vocal pocketing.",
                "- Master remains true-peak safe and measured after MP3 encoding.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPORTS / "reaper_mix_decision_log.md").write_text(
        "\n".join(
            [
                "# REAPER Mix Decision Log",
                "",
                f"- Slug: `{SLUG}`.",
                "- User requested: original vocal was clear, remove reverb, make vocal clearer, rerender.",
                "- Removed all active vocal reverb and delay returns.",
                "- Muted female layer in the final mix to prevent timing/lyric/pitch smear.",
                "- Used a lighter male vocal denoise pass than v11 and restored controlled clarity around 2-5 kHz.",
                "- Kept dynamic EQ on mud, nasal tone, sibilance, and top fizz.",
                "- No Antares or paid plugins used.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        paths["final_wav"],
        paths["final_mp3"],
        paths["premaster"],
        paths["male_stem"],
        paths["instrumental_stem"],
        paths["melody_stem"],
        RPP,
        REPORTS / "final_qc_report.md",
        REPORTS / "final_render_metrics.csv",
        REPORTS / "reaper_mix_decision_log.md",
    ]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        seen: set[Path] = set()
        for path in include:
            if path.exists() and path not in seen:
                zf.write(path, arcname=path.name)
                seen.add(path)
    return zip_path


def main() -> None:
    ensure_dirs()
    sr, audio = load_audio()
    male, male_moves = process_male_clear_dry(audio["male_raw"], sr)
    paths, mix_moves = render(sr, audio, male)
    write_rpp(sr, audio, paths)
    zip_path = write_reports(paths, male_moves, mix_moves)
    print(
        json.dumps(
            {
                "slug": SLUG,
                "final_wav": str(paths["final_wav"]),
                "final_mp3": str(paths["final_mp3"]),
                "premaster": str(paths["premaster"]),
                "male_vocal_stem": str(paths["male_stem"]),
                "reports": str(REPORTS),
                "reaper_project": str(RPP),
                "delivery_zip": str(zip_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
