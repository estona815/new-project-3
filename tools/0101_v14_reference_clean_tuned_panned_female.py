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
    delay_samples,
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
V13 = load_module(ROOT / "tools" / "0101_v13_clear_tuned_female_layer_rerender.py", "codex_0101_v13")

SLUG = "0101_v14_reference_clean_tuned_panned_female"
WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V14_REFERENCE_CLEAN_TUNED_PANNED_FEMALE.rpp"
BPM = 135

BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
V13_RENDERS = ROOT / "renders" / "0101_v13_clear_tuned_female_layer_rerender"
REFERENCE_PATHS = [
    BASE_STEMS / "0101_original_reference.wav",
    ROOT / "suno_reference_pack" / "i0i_master_mp3" / "030 320kbps.mp3",
    ROOT / "suno_reference_pack" / "i0i_master_mp3" / "Am i 5u5ide? 320kbps.mp3",
]


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


def suppress_shiik_noise(y: np.ndarray, sr: int, label: str, strength: float = 0.66) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 5200, 13200, 4)
    mid = bandpass(y, sr, 240, 4600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    mid_env = np.abs(np.mean(mid, axis=1))
    active = high_env[high_env > 1e-8]
    if not len(active):
        return y.astype(np.float32), {"stage": "shiik_noise_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active, 88.5)), float(np.max(active) * 0.18))
    ratio = high_env / (mid_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 0.52)
    mask = np.convolve(mask.astype(np.float32), np.ones(max(int(sr * 0.075), 1), dtype=np.float32), mode="same") > 0
    mask_f = smooth_mask(mask, sr, 95.0)
    out = y - high * (mask_f[:, None] * strength)
    out, hiss = dynamic_band_tame(out.astype(np.float32), sr, 5600, 10400, 2.05, 60, 48)
    out, glass = dynamic_band_tame(out.astype(np.float32), sr, 9800, 14200, 1.70, 64, 44)
    return out.astype(np.float32), {
        "stage": "shiik_noise_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "strength": strength,
        "hiss_guard": hiss,
        "glass_guard": glass,
    }


def female_audible_overlap_mask(male: np.ndarray, female: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    male_env = np.abs(np.mean(bandpass(male, sr, 150, 5200, 2), axis=1))
    female_env = np.abs(np.mean(bandpass(female, sr, 220, 6500, 2), axis=1))
    male_active = male_env > max(float(np.percentile(male_env, 52)), 1e-5)
    active_female = female_env[female_env > 1e-8]
    female_threshold = float(np.percentile(active_female, 35)) if np.any(active_female) else 1e-5
    female_active = female_env > max(female_threshold, 1e-5)
    mask = male_active & female_active
    mask = np.convolve(mask.astype(np.float32), np.ones(max(int(sr * 0.140), 1), dtype=np.float32), mode="same") > 0
    mask_f = smooth_mask(mask, sr, 120.0)
    coverage = float(np.mean(mask_f > 0.08))
    return mask_f.astype(np.float32), {
        "stage": "female_audible_overlap_gate",
        "coverage_pct": round(coverage * 100, 2),
        "note": "more generous than v13 because user said female layer is hard to hear",
    }


def reference_body_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    body = bandpass(vocal, sr, 145, 430, 3)
    body = compressor(body, sr, threshold_db=-34.5, ratio=2.45, smooth_ms=86, makeup_db=0.9)
    body = saturate(body, drive_db=1.1, mix=0.08)
    body, mud = dynamic_band_tame(body, sr, 245, 430, 0.95, 75, 126)
    body = safe_normalize(body, -24.6)
    return body.astype(np.float32), {"stage": "v14_reference_body_parallel", "return_gain_db": -7.8, "mud_control": mud}


def tuned_clarity_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    tune, stats = MO.strong_tune_density_layer(vocal, sr)
    clean = bandpass(vocal, sr, 1400, 5200, 3)
    clean = compressor(clean, sr, threshold_db=-35.0, ratio=3.2, smooth_ms=30, makeup_db=0.8)
    clean = vocal_harmonic_density(clean, sr, drive_db=2.0, wet=0.12)
    clean, edge = dynamic_band_tame(clean, sr, 3000, 5600, 1.2, 72, 56)
    clean, hiss = dynamic_band_tame(clean, sr, 5600, 10800, 1.8, 64, 46)
    clean = biquad_peaking(clean, sr, 2450, 0.55, 0.9)
    clean = biquad_shelf(clean, sr, 10200, -0.30, True)
    clean = safe_normalize(clean, -25.0)
    layer = limiter(tune * float(amp_db(-3.6)) + clean * float(amp_db(-5.0)), -2.4)
    layer = safe_normalize(layer, -22.8)
    return layer.astype(np.float32), {
        "stage": "v14_tuned_clarity_parallel",
        "return_gain_db": -7.0,
        "source_tune_layer": stats,
        "edge_control": edge,
        "hiss_control": hiss,
    }


def process_male_v14(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, moves = V12.process_male_clear_dry(raw, sr)
    base, shiik_pre = suppress_shiik_noise(base, sr, "male_pre_tune", strength=0.74)
    base, low_veil = dynamic_band_tame(base, sr, 255, 520, 0.82, 77, 132)
    base, nasal = dynamic_band_tame(base, sr, 690, 1420, 1.08, 70, 106)
    body, body_stats = reference_body_layer(base, sr)
    tune, tune_stats = tuned_clarity_layer(base, sr)
    out = base * float(amp_db(0.80)) + body * float(amp_db(-7.8)) + tune * float(amp_db(-7.0))
    out = biquad_peaking(out, sr, 220, 0.35, 0.8)
    out = biquad_peaking(out, sr, 880, -0.48, 1.05)
    out = biquad_peaking(out, sr, 2620, 0.55, 0.92)
    out = biquad_peaking(out, sr, 3820, 0.22, 1.00)
    out = biquad_shelf(out, sr, 10400, -0.22, True)
    out = saturate(out, drive_db=1.45, mix=0.095)
    out = compressor(out, sr, threshold_db=-24.0, ratio=2.05, smooth_ms=62, makeup_db=0.24)
    out, edge = dynamic_band_tame(out, sr, 2750, 5100, 0.90, 74, 62)
    out, sib = dynamic_band_tame(out, sr, 5200, 9000, 2.20, 61, 46)
    out, air = dynamic_band_tame(out, sr, 9200, 13600, 1.75, 65, 42)
    out, shiik_post = suppress_shiik_noise(out, sr, "male_post_tune", strength=0.52)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-19.4, max_cut_db=-5.4, max_boost_db=1.10, label="v14_reference_clean_male")
    out = safe_normalize(out, -18.15)
    out = soft_clip(out, drive_db=0.52, ceiling=0.86)
    out = limiter(MO.edge_fade(out, sr, 16.0), -1.55)
    moves.extend(
        [
            shiik_pre,
            {"stage": "v14_low_veil_control", **low_veil},
            {"stage": "v14_nasal_formant_control", **nasal},
            body_stats,
            tune_stats,
            {"stage": "v14_presence_edge_guard", **edge},
            {"stage": "v14_sibilance_guard", **sib},
            {"stage": "v14_air_glass_guard", **air},
            shiik_post,
            ride,
            {"stage": "v14_final_male_gain", "target_rms_dbfs": -18.15, "note": "clean tuned vocal with reference-like body, no reverb"},
        ]
    )
    return out.astype(np.float32), moves


def process_female_v14(female: np.ndarray, male: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = pad_or_trim(female, len(male))
    mask, mask_stats = female_audible_overlap_mask(male, out, sr)
    out = out * mask[:, None]
    out = butter_filter(out, sr, "highpass", 150, 3)
    out, shiik = suppress_shiik_noise(out, sr, "female_layer", strength=0.72)
    out, nasal = dynamic_band_tame(out, sr, 660, 1500, 1.55, 66, 88)
    out, bite = dynamic_band_tame(out, sr, 2550, 5200, 1.10, 70, 55)
    out, fizz = dynamic_band_tame(out, sr, 5450, 11200, 2.25, 62, 42)
    out = compressor(out, sr, threshold_db=-31.0, ratio=2.25, smooth_ms=58, makeup_db=0.30)
    out = saturate(out, drive_db=0.95, mix=0.065)
    out = biquad_peaking(out, sr, 2150, 0.32, 1.0)
    out = biquad_shelf(out, sr, 9800, -0.68, True)
    left = pan_stereo(out, -0.60) * float(amp_db(0.6))
    right = pan_stereo(delay_samples(out, int(sr * 0.014)), 0.52) * float(amp_db(-0.2))
    center_hint = out * float(amp_db(-13.5))
    panned = ms_width(left + right + center_hint, 1.9)
    panned = sidechain_duck_full(panned, male, sr, amount_db=1.35, release_ms=122, threshold_percentile=58)
    panned = safe_normalize(panned, -21.6)
    panned = limiter(panned, -4.6)
    moves.extend(
        [
            mask_stats,
            shiik,
            {"stage": "female_dynamic_nasal_guard", **nasal},
            {"stage": "female_dynamic_bite_guard", **bite},
            {"stage": "female_dynamic_fizz_guard", **fizz},
            {"stage": "female_panned_separation", "left_pan": -0.60, "right_pan": 0.52, "right_delay_ms": 14, "center_hint_db": -13.5, "sidechain_duck_db": 1.35, "target_rms_dbfs": -21.6},
        ]
    )
    return panned.astype(np.float32), moves


def load_audio() -> tuple[int, dict[str, np.ndarray]]:
    return V12.load_audio()


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray, female: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)
    female = pad_or_trim(female, length)

    vocal_ref = male * float(amp_db(-1.0)) + female * float(amp_db(-3.2))
    inst_pocket = sidechain_duck_full(inst, vocal_ref, sr, amount_db=0.62, release_ms=130, threshold_percentile=60)
    melody_pocket = sidechain_duck_full(melody, male, sr, amount_db=0.07, release_ms=110, threshold_percentile=68)
    inst_pocket = ms_width(inst_pocket, 0.55)
    mix = MO.safe_sum(
        [
            (inst_pocket, -1.14),
            (melody_pocket, 1.12),
            (drums, -10.65),
            (bass, -10.15),
            (male, -3.65),
            (female, -1.35),
        ],
        length,
        -1.8,
    )
    mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(mix, sr, 20.0), sr)
    mix, shiik_mix = suppress_shiik_noise(mix, sr, "full_mix", strength=0.20)
    mix = biquad_peaking(mix, sr, 720, -0.12, 1.0)
    mix = biquad_peaking(mix, sr, 2550, 0.10, 0.9)
    mix = biquad_shelf(mix, sr, 11600, -0.08, True)
    mix = stable_master_tone(mix, sr)
    mix = compressor(mix, sr, threshold_db=-12.4, ratio=1.045, smooth_ms=278, makeup_db=0.0)
    mix = soft_clip(mix, drive_db=0.17, ceiling=0.89)
    mix = limiter(mix, -2.2)

    premaster = RENDERS / "0101_mix_v14_reference_clean_tuned_panned_female_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v14_reference_clean_tuned_panned_female.wav"
    final_mp3 = RENDERS / "0101_FINAL_v14_reference_clean_tuned_panned_female_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v14_reference_clean_tuned_stem.wav"
    female_path = RENDERS / "processed_female_layer_v14_panned_support_stem.wav"
    inst_path = RENDERS / "processed_instrumental_v14_reference_pocket_stem.wav"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-11.4, target_tp=-1.25, target_lra=3.8)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, female)
    write_float_wav(inst_path, sr, limiter(inst_pocket, -1.8))
    moves = [
        {"stage": "v14_mix_gain", "male_gain_db": -3.65, "female_gain_db": -1.35, "female_pan": "wide L/R support raised because user said it was too hard to hear", "vocal_reverb_delay": "none"},
        {"stage": "v14_vocal_pocket", "instrumental_duck_db": 0.62, "melody_duck_db": 0.07},
        {"stage": "v14_music_width", "instrumental_side_gain_db": 0.55},
        shiik_mix,
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
        rpp_track("0101_ORIGINAL_REFERENCE muted", BASE_STEMS / "0101_original_reference.wav", length, 1, True, False),
        rpp_track("V13_PREVIOUS muted", V13_RENDERS / "0101_FINAL_v13_clear_tuned_female_layer.wav", length, 2, True, False),
        rpp_track("MALE_VOCAL_V14_CLEAN_TUNED muted", paths["male_stem"], length, 3, True, False),
        rpp_track("FEMALE_LAYER_V14_PANNED muted", paths["female_stem"], length, 4, True, False),
        rpp_track("INSTRUMENTAL_V14_POCKET muted", paths["instrumental_stem"], length, 5, True, False),
        rpp_track("MIX_BUS V14 ACTIVE", paths["final_wav"], length, 6, False, True),
        rpp_track("MASTER_MP3_MONITOR muted", paths["final_mp3"], length, 7, True, False),
    ]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip([0, 14.2, 42.7, 72.0, 101.3, length], ["intro", "verse", "hook", "section2", "outro", "end"]), start=1)
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v14 reference-informed clean tuned vocal pass. Existing beat stems are processed, not re-recorded. Female layer is panned and separated.
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
        audio_metrics(paths["final_wav"], "v14_final_wav"),
        audio_metrics(paths["final_mp3"], "v14_final_mp3"),
        audio_metrics(paths["male_stem"], "v14_processed_male_clean_tuned"),
        audio_metrics(paths["female_stem"], "v14_processed_female_panned"),
        audio_metrics(V13_RENDERS / "0101_FINAL_v13_clear_tuned_female_layer.wav", "v13_previous"),
    ]
    reference_metrics = [audio_metrics(path, f"reference_{path.stem}") for path in REFERENCE_PATHS if path.exists()]
    write_csv(REPORTS / "final_render_metrics.csv", metrics)
    write_csv(REPORTS / "reference_metrics.csv", reference_metrics)
    (REPORTS / "processing_decisions.json").write_text(
        json.dumps(
            {
                "reference_files": [str(path) for path in REFERENCE_PATHS if path.exists()],
                "male_vocal": male_moves,
                "female_layer": female_moves,
                "mix": mix_moves,
                "target": {"integrated_lufs": -11.4, "true_peak_dbfs": -1.25},
                "note": "Beat was not rebuilt or re-recorded; existing stems were processed and printed.",
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
            "stereo_corr": row.get("stereo_corr"),
            "side_mid_db": row.get("side_mid_db"),
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
                markdown_table(summary, ["version", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "stereo_corr", "side_mid_db", "presence_pct", "sibilance_pct", "air_pct"]),
                "",
                "## Revision Notes",
                "",
                "- Reference-informed pass used the local 0101 original reference plus local i0i reference masters for measured comparison.",
                "- Male vocal was rebuilt cleaner than v13: more body/formant core, less over-thin presence, stronger tune-density layer, and extra shiik/sibilance suppression.",
                "- Female layer is audible and separated with L/R panning, short right offset, low center hint, and sidechain ducking from the male lead.",
                "- Vocal reverb and delay remain removed.",
                "- Existing beat stems were processed and mastered; the beat was not replayed or re-recorded in REAPER.",
                "- MP3 and WAV true peak were checked after rendering.",
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
                "- Answer to user question: prior revisions generated REAPER projects, but the audible renders were offline DSP prints from existing stems, not a fresh REAPER beat re-recording.",
                "- v14 keeps the same stem/mix-set route and prints a new REAPER session for handoff.",
                "- Reference translation: keep vocal clean and tune-forward, reduce glassy/shiik top noise, keep female layer audible via panning rather than center stacking.",
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
        paths["female_stem"],
        paths["instrumental_stem"],
        RPP,
        REPORTS / "final_qc_report.md",
        REPORTS / "final_render_metrics.csv",
        REPORTS / "reference_metrics.csv",
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
    male, male_moves = process_male_v14(audio["male_raw"], sr)
    female, female_moves = process_female_v14(audio["female_layer"], male, sr)
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
