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
    ms_width,
    normalize_to_rms,
    pan_stereo,
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
V12 = load_module(ROOT / "tools" / "0101_v12_clear_dry_vocal_rerender.py", "codex_0101_v12")

SLUG = "0101_v13_clear_tuned_female_layer_rerender"
WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V13_CLEAR_TUNED_FEMALE_LAYER.rpp"
BPM = 135

BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
V12_RENDERS = ROOT / "renders" / "0101_v12_clear_dry_vocal_rerender"


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


def smooth_mask(mask: np.ndarray, sr: int, ms: float) -> np.ndarray:
    samples = max(int(sr * ms / 1000.0), 3)
    if samples % 2 == 0:
        samples += 1
    kernel = np.hanning(samples).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    return np.clip(np.convolve(mask.astype(np.float32), kernel, mode="same"), 0.0, 1.0)


def active_overlap_mask(male: np.ndarray, female: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    male_env = np.abs(np.mean(bandpass(male, sr, 160, 5200, 2), axis=1))
    female_env = np.abs(np.mean(bandpass(female, sr, 220, 6400, 2), axis=1))
    male_active = male_env > max(float(np.percentile(male_env, 58)), 1e-5)
    female_active = female_env > max(float(np.percentile(female_env[female_env > 1e-8], 45)) if np.any(female_env > 1e-8) else 1e-5, 1e-5)
    mask = male_active & female_active
    expand = max(int(sr * 0.090), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(expand, dtype=np.float32), mode="same") > 0
    mask_f = smooth_mask(mask, sr, 95.0)
    coverage = float(np.mean(mask_f > 0.08))
    return mask_f.astype(np.float32), {"stage": "female_layer_overlap_gate", "coverage_pct": round(coverage * 100, 2)}


def clarity_pop_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    pop = bandpass(vocal, sr, 1550, 6100, 3)
    pop = compressor(pop, sr, threshold_db=-35.0, ratio=4.2, smooth_ms=26, makeup_db=1.05)
    pop = vocal_harmonic_density(pop, sr, drive_db=2.8, wet=0.18)
    pop, edge = dynamic_band_tame(pop, sr, 3200, 6200, 1.45, 71, 48)
    pop, fizz = dynamic_band_tame(pop, sr, 6600, 11800, 1.85, 64, 42)
    pop = biquad_peaking(pop, sr, 2300, 0.75, 0.90)
    pop = biquad_peaking(pop, sr, 4100, 0.38, 1.0)
    pop = biquad_shelf(pop, sr, 10400, -0.10, True)
    pop = safe_normalize(pop, -24.4)
    return pop.astype(np.float32), {
        "stage": "v13_clarity_pop_parallel",
        "return_gain_db": -5.8,
        "saturation_drive_db": 2.8,
        "edge_control": edge,
        "fizz_control": fizz,
    }


def process_male_v13(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, moves = V12.process_male_clear_dry(raw, sr)
    base, mud = dynamic_band_tame(base, sr, 290, 520, 0.75, 76, 130)
    base, veil = dynamic_band_tame(base, sr, 620, 1450, 0.95, 72, 112)
    tune_layer, tune_stats = MO.strong_tune_density_layer(base, sr)
    pop_layer, pop_stats = clarity_pop_layer(base, sr)
    out = base * float(amp_db(0.95)) + tune_layer * float(amp_db(-5.2)) + pop_layer * float(amp_db(-7.0))
    out = biquad_peaking(out, sr, 730, -0.42, 1.0)
    out = biquad_peaking(out, sr, 2450, 0.86, 0.82)
    out = biquad_peaking(out, sr, 3850, 0.42, 0.95)
    out = biquad_shelf(out, sr, 10600, 0.16, True)
    out = saturate(out, drive_db=1.75, mix=0.12)
    out = compressor(out, sr, threshold_db=-24.0, ratio=2.12, smooth_ms=54, makeup_db=0.32)
    out = soft_clip(out, drive_db=1.05, ceiling=0.82)
    out, sib = dynamic_band_tame(out, sr, 5350, 9050, 1.75, 64, 45)
    out, air = dynamic_band_tame(out, sr, 9400, 13800, 1.15, 67, 42)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-19.7, max_cut_db=-5.2, max_boost_db=1.35, label="v13_clear_tuned_male")
    out = safe_normalize(out, -18.65)
    out = soft_clip(out, drive_db=0.65, ceiling=0.84)
    out = limiter(MO.edge_fade(out, sr, 16.0), -1.55)
    moves.extend(
        [
            {"stage": "v13_extra_deveil_low_mid", **mud},
            {"stage": "v13_extra_deveil_formant", **veil},
            {**tune_stats, "mix_gain_db": -5.2},
            pop_stats,
            {"stage": "v13_post_tune_sibilance_guard", **sib},
            {"stage": "v13_post_tune_air_guard", **air},
            ride,
            {"stage": "v13_final_male_gain", "target_rms_dbfs": -18.65, "vocal_fx": "none", "intent": "clearer, denser, tuned, saturated without losing the v12 core"},
        ]
    )
    return out.astype(np.float32), moves


def process_female_layer(female: np.ndarray, male: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = pad_or_trim(female, len(male))
    mask, mask_stats = active_overlap_mask(male, out, sr)
    out = out * mask[:, None]
    moves.append(mask_stats)
    out = butter_filter(out, sr, "highpass", 135, 3)
    out, nasal = dynamic_band_tame(out, sr, 720, 1550, 1.55, 65, 92)
    out, bite = dynamic_band_tame(out, sr, 2600, 5200, 1.25, 69, 58)
    out, fizz = dynamic_band_tame(out, sr, 5600, 11800, 2.55, 60, 43)
    out = compressor(out, sr, threshold_db=-31.5, ratio=2.4, smooth_ms=62, makeup_db=0.35)
    out = saturate(out, drive_db=0.80, mix=0.055)
    out = biquad_peaking(out, sr, 2500, 0.25, 1.0)
    out = biquad_shelf(out, sr, 9800, -0.55, True)
    out = ms_width(out, 1.8)
    out = sidechain_duck_full(out, male, sr, amount_db=3.2, release_ms=118, threshold_percentile=57)
    out = limiter(out, -3.0)
    moves.extend(
        [
            {"stage": "female_dynamic_nasal_guard", **nasal},
            {"stage": "female_dynamic_bite_guard", **bite},
            {"stage": "female_dynamic_fizz_guard", **fizz},
            {"stage": "female_layer_sidechain_duck", "duck_db": 3.2, "width_db": 1.8, "role": "quiet audible support layer"},
        ]
    )
    return out.astype(np.float32), moves


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray, female_layer: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)
    female = pad_or_trim(female_layer, length)

    inst_pocket = sidechain_duck_full(inst, male, sr, amount_db=0.86, release_ms=118, threshold_percentile=60)
    melody_pocket = sidechain_duck_full(melody, male, sr, amount_db=0.10, release_ms=105, threshold_percentile=68)
    mix = MO.safe_sum(
        [
            (inst_pocket, -1.28),
            (melody_pocket, 1.18),
            (drums, -10.8),
            (bass, -10.35),
            (male, -5.8),
            (female, -4.8),
        ],
        length,
        -1.75,
    )
    mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(mix, sr, 20.0), sr)
    mix = biquad_peaking(mix, sr, 720, -0.18, 1.0)
    mix = biquad_peaking(mix, sr, 2450, 0.22, 0.9)
    mix = biquad_shelf(mix, sr, 11300, 0.05, True)
    mix = stable_master_tone(mix, sr)
    mix = compressor(mix, sr, threshold_db=-12.0, ratio=1.05, smooth_ms=248, makeup_db=0.0)
    mix = soft_clip(mix, drive_db=0.20, ceiling=0.89)
    mix = limiter(mix, -2.2)

    premaster = RENDERS / "0101_mix_v13_clear_tuned_female_layer_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v13_clear_tuned_female_layer.wav"
    final_mp3 = RENDERS / "0101_FINAL_v13_clear_tuned_female_layer_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v13_clear_tuned_stem.wav"
    female_path = RENDERS / "processed_female_layer_v13_overlap_support_stem.wav"
    inst_path = RENDERS / "processed_instrumental_v13_vocal_pocket_stem.wav"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-11.2, target_tp=-1.25, target_lra=3.7)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, female)
    write_float_wav(inst_path, sr, limiter(inst_pocket, -1.8))
    moves = [
        {
            "stage": "v13_mix_gain_revision",
            "male_gain_db": -5.8,
            "female_gain_db": -4.8,
            "vocal_reverb_delay": "removed",
            "instrumental_gain_db": -1.28,
            "melody_gain_db": 1.18,
        },
        {"stage": "instrumental_stronger_vocal_pocket", "duck_db": 0.86},
        {"stage": "melody_kept_forward", "duck_db": 0.10},
        *mix_res,
    ]
    return {
        "premaster": premaster,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "male_stem": male_path,
        "female_stem": female_path,
        "instrumental_stem": inst_path,
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
        rpp_track("V12_PREVIOUS_DRY muted", V12_RENDERS / "0101_FINAL_v12_clear_dry_vocal.wav", length, 1, True, False),
        rpp_track("MALE_RAW muted", BASE_STEMS / "0101_vocal_raw.wav", length, 2, True, False),
        rpp_track("MALE_VOCAL_V13_CLEAR_TUNED muted", paths["male_stem"], length, 3, True, False),
        rpp_track("FEMALE_LAYER_V13_OVERLAP_SUPPORT muted", paths["female_stem"], length, 4, True, False),
        rpp_track("INSTRUMENTAL_V13_POCKET muted", paths["instrumental_stem"], length, 5, True, False),
        rpp_track("MIX_BUS V13 CLEAR TUNED FEMALE ACTIVE", paths["final_wav"], length, 6, False, True),
        rpp_track("MASTER_MP3_MONITOR muted", paths["final_mp3"], length, 7, True, False),
    ]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip([0, 14.2, 42.7, 72.0, 101.3, length], ["intro", "verse", "hook", "section2", "outro", "end"]), start=1)
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v13. Dry no-reverb vocal, stronger tune/saturation clarity, female support layer reintroduced only on overlap.
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


def write_reports(paths: dict[str, Path], male_moves: list[dict[str, object]], female_moves: list[dict[str, object]], mix_moves: list[dict[str, object]]) -> Path:
    metrics = [
        audio_metrics(paths["final_wav"], "v13_final_wav_clear_tuned_female"),
        audio_metrics(paths["final_mp3"], "v13_final_mp3_clear_tuned_female"),
        audio_metrics(paths["male_stem"], "v13_processed_male_clear_tuned"),
        audio_metrics(paths["female_stem"], "v13_processed_female_overlap_support"),
        audio_metrics(V12_RENDERS / "0101_FINAL_v12_clear_dry_vocal.wav", "v12_previous_dry"),
    ]
    write_csv(REPORTS / "final_render_metrics.csv", metrics)
    (REPORTS / "processing_decisions.json").write_text(
        json.dumps(
            {
                "male_vocal": male_moves,
                "female_layer": female_moves,
                "mix": mix_moves,
                "target": {"integrated_lufs": -11.2, "true_peak_dbfs": -1.25},
                "explicit_user_request": "female layer back in, clearer vocal, stronger tune/saturation, no hazy reverb",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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
                "- Female layer is back in, but overlap-gated and sidechain-ducked so it supports the male lead instead of smearing it.",
                "- Vocal reverb and delay remain removed from the active mix.",
                "- Male vocal clarity was increased with a stronger DSP tune-density layer, extra harmonic saturation, and presence parallel.",
                "- Low-mid veil and formant haze were dynamically reduced before the vocal was lifted in the mix.",
                "- Instrumental gets a stronger vocal pocket while the melody remains forward.",
                "- No Antares or paid plugins used.",
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
                "- Started from v12 dry vocal direction because the user rejected reverb blur.",
                "- Reintroduced the female layer only where male/female activity overlaps, then widened and ducked it.",
                "- Added stronger tune-feel density and saturation to the male lead; this is DSP processing, not Antares/manual note tuning.",
                "- Vocal reverb/delay were not added.",
                "- Master was rendered and measured after MP3 conversion.",
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
        paths["female_stem"],
        paths["instrumental_stem"],
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
    sr, audio = V12.load_audio()
    male, male_moves = process_male_v13(audio["male_raw"], sr)
    female, female_moves = process_female_layer(audio["female_layer"], male, sr)
    paths, mix_moves = render(sr, audio, male, female)
    write_rpp(sr, audio, paths)
    zip_path = write_reports(paths, male_moves, female_moves, mix_moves)
    print(
        json.dumps(
            {
                "slug": SLUG,
                "final_wav": str(paths["final_wav"]),
                "final_mp3": str(paths["final_mp3"]),
                "premaster": str(paths["premaster"]),
                "male_vocal_stem": str(paths["male_stem"]),
                "female_layer_stem": str(paths["female_stem"]),
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
