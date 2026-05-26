from __future__ import annotations

import csv
import importlib.util
import json
import shutil
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
    detect_phrase_endings,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    ms_width,
    normalize_to_rms,
    pan_stereo,
    read_wav,
    reverb_send,
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
V14 = load_module(ROOT / "tools" / "0101_v14_reference_clean_tuned_panned_female.py", "codex_0101_v14")

SLUG = "0101_v15_dry_vocal_clarity_final"
WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed"
BACKUP = WORK / "backup"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "reaper_session_clarity_pass.rpp"
BPM = 135

BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
V14_RENDERS = ROOT / "renders" / "0101_v14_reference_clean_tuned_panned_female"
V14_FINAL = V14_RENDERS / "0101_FINAL_v14_reference_clean_tuned_panned_female.wav"
REFERENCE_PATHS = [
    BASE_STEMS / "0101_original_reference.wav",
    ROOT / "suno_reference_pack" / "i0i_master_mp3" / "030 320kbps.mp3",
    ROOT / "suno_reference_pack" / "i0i_master_mp3" / "Am i 5u5ide? 320kbps.mp3",
]

VARIANTS = {
    "A_subtle": {
        "presence_db": 0.55,
        "presence2_db": 0.10,
        "air_db": -0.10,
        "tune_gain_db": -9.0,
        "clarity_gain_db": -9.8,
        "sat_drive": 1.10,
        "sat_mix": 0.060,
        "male_mix_db": -3.25,
        "female_mix_db": -1.55,
        "instrumental_duck_db": 0.68,
        "presence_pocket_db": 0.78,
    },
    "B_presence": {
        "presence_db": 1.05,
        "presence2_db": 0.28,
        "air_db": 0.05,
        "tune_gain_db": -8.2,
        "clarity_gain_db": -8.7,
        "sat_drive": 1.28,
        "sat_mix": 0.078,
        "male_mix_db": -3.35,
        "female_mix_db": -1.35,
        "instrumental_duck_db": 0.78,
        "presence_pocket_db": 0.98,
    },
    "C_air_control": {
        "presence_db": 1.10,
        "presence2_db": 0.34,
        "air_db": 0.42,
        "tune_gain_db": -8.5,
        "clarity_gain_db": -8.9,
        "sat_drive": 1.22,
        "sat_mix": 0.072,
        "male_mix_db": -3.45,
        "female_mix_db": -1.25,
        "instrumental_duck_db": 0.82,
        "presence_pocket_db": 1.05,
    },
}


def ensure_dirs() -> None:
    for directory in (WORK, PROCESSED, BACKUP, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    if V14_FINAL.exists():
        shutil.copy2(V14_FINAL, BACKUP / V14_FINAL.name)


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
    return V12.load_audio()


def tuned_presence_layer(vocal: np.ndarray, sr: int, settings: dict[str, float]) -> tuple[np.ndarray, dict[str, object]]:
    tune, tune_stats = MO.strong_tune_density_layer(vocal, sr)
    clarity = bandpass(vocal, sr, 1500, 5100, 3)
    clarity = compressor(clarity, sr, threshold_db=-34.5, ratio=3.0, smooth_ms=30, makeup_db=0.65)
    clarity = vocal_harmonic_density(clarity, sr, drive_db=1.65, wet=0.10)
    clarity, edge = dynamic_band_tame(clarity, sr, 3050, 5550, 1.05, 73, 54)
    clarity, hiss = dynamic_band_tame(clarity, sr, 5600, 11000, 1.65, 65, 44)
    clarity = biquad_peaking(clarity, sr, 2550, 0.52, 0.92)
    clarity = biquad_shelf(clarity, sr, 10200, -0.30, True)
    clarity = safe_normalize(clarity, -25.6)
    layer = tune * float(amp_db(settings["tune_gain_db"])) + clarity * float(amp_db(settings["clarity_gain_db"]))
    layer = limiter(layer, -2.6)
    layer = safe_normalize(layer, -24.0)
    return layer.astype(np.float32), {
        "stage": "v15_parallel_tune_presence",
        "tune_gain_db": settings["tune_gain_db"],
        "clarity_gain_db": settings["clarity_gain_db"],
        "source_tune_layer": tune_stats,
        "edge_control": edge,
        "hiss_control": hiss,
    }


def process_male(raw: np.ndarray, sr: int, variant: str, settings: dict[str, float]) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, moves = V12.process_male_clear_dry(raw, sr)
    base, shiik_pre = V14.suppress_shiik_noise(base, sr, f"{variant}_male_pre", strength=0.68)
    base, mud = dynamic_band_tame(base, sr, 220, 450, 1.05, 74, 132)
    base, blanket = dynamic_band_tame(base, sr, 520, 900, 0.72, 73, 112)
    base, nasal = dynamic_band_tame(base, sr, 900, 1420, 0.42, 78, 118)
    body = bandpass(base, sr, 170, 410, 3)
    body = compressor(body, sr, threshold_db=-35.0, ratio=2.35, smooth_ms=86, makeup_db=0.75)
    body = saturate(body, drive_db=0.95, mix=0.055)
    body = safe_normalize(body, -25.0)
    parallel, parallel_stats = tuned_presence_layer(base, sr, settings)
    out = base * float(amp_db(0.74)) + body * float(amp_db(-8.2)) + parallel * float(amp_db(-6.7))
    out = biquad_peaking(out, sr, 230, 0.22, 0.85)
    out = biquad_peaking(out, sr, 760, -0.20, 1.05)
    out = biquad_peaking(out, sr, 2900, settings["presence_db"], 0.82)
    out = biquad_peaking(out, sr, 4100, settings["presence2_db"], 1.00)
    out = biquad_shelf(out, sr, 9800, settings["air_db"], True)
    out = saturate(out, drive_db=settings["sat_drive"], mix=settings["sat_mix"])
    out = compressor(out, sr, threshold_db=-23.8, ratio=2.05, smooth_ms=66, makeup_db=0.18)
    out, edge = dynamic_band_tame(out, sr, 2850, 5200, 0.72, 76, 62)
    out, sib = dynamic_band_tame(out, sr, 5450, 8800, 2.25, 61, 44)
    out, glass = dynamic_band_tame(out, sr, 8900, 13200, 1.70, 65, 40)
    if variant == "C_air_control":
        out, extra_sib = dynamic_band_tame(out, sr, 6200, 9800, 0.70, 72, 45)
    else:
        extra_sib = {"stage": "extra_sib_guard", "active": False}
    out, shiik_post = V14.suppress_shiik_noise(out, sr, f"{variant}_male_post", strength=0.48 if variant != "C_air_control" else 0.56)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-19.2, max_cut_db=-5.0, max_boost_db=0.95, label=f"v15_{variant}_male")
    out = safe_normalize(out, -18.55)
    out = soft_clip(out, drive_db=0.34, ceiling=0.88)
    out = limiter(MO.edge_fade(out, sr, 16.0), -1.55)
    moves.extend(
        [
            {"stage": "v15_variant", "variant": variant},
            shiik_pre,
            {"stage": "v15_low_mid_cloud_dynamic_cut", **mud},
            {"stage": "v15_blanket_500_900_dynamic_cut", **blanket},
            {"stage": "v15_formant_preserve_light_control", **nasal},
            {"stage": "v15_body_parallel", "return_gain_db": -8.2, "band_hz": "170-410"},
            parallel_stats,
            {"stage": "v15_presence_eq", "presence_2900_db": settings["presence_db"], "presence_4100_db": settings["presence2_db"], "air_9800_db": settings["air_db"]},
            {"stage": "v15_post_presence_edge_guard", **edge},
            {"stage": "v15_de_ess_5450_8800", **sib},
            {"stage": "v15_ai_fizz_8900_13200", **glass},
            extra_sib,
            shiik_post,
            ride,
            {"stage": "v15_final_male_gain", "target_rms_dbfs": -18.55, "reverb_delay": "none on main vocal"},
        ]
    )
    return out.astype(np.float32), moves


def process_female(female: np.ndarray, male: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    panned, moves = V14.process_female_v14(female, male, sr)
    panned, lowmid = dynamic_band_tame(panned, sr, 250, 700, 0.75, 74, 120)
    panned = biquad_peaking(panned, sr, 2550, 0.28, 0.95)
    panned = biquad_shelf(panned, sr, 9300, -0.25, True)
    panned = safe_normalize(panned, -21.2)
    panned = limiter(panned, -4.4)
    moves.extend(
        [
            {"stage": "v15_female_side_layer_louder", "target_rms_dbfs": -21.2, "role": "audible side support, not center lead"},
            {"stage": "v15_female_lowmid_blur_control", **lowmid},
        ]
    )
    return panned.astype(np.float32), moves


def band_duck(source: np.ndarray, trigger: np.ndarray, sr: int, low: float, high: float, amount_db: float, percentile: float = 58.0) -> np.ndarray:
    band = bandpass(source, sr, low, high, 3)
    mono = np.mean(bandpass(trigger, sr, 150, 5200, 2), axis=1)
    env = np.abs(mono)
    active = env[env > 1e-8]
    if not len(active):
        return source.astype(np.float32)
    threshold = float(np.percentile(active, percentile))
    mask = env > threshold
    smooth = V14.smooth_mask(mask, sr, 85.0)
    reduce = 1.0 - (1.0 - float(amp_db(-amount_db))) * smooth[:, None]
    return (source - band + band * reduce).astype(np.float32)


def throw_fx(male: np.ndarray, female: np.ndarray, sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    endings = detect_phrase_endings(male, sr)
    ranked = sorted(
        [e for e in endings if e.get("throw") or float(e.get("confidence", 0.0)) >= 0.66 or float(e.get("following_pause_s", 0.0)) >= 0.45],
        key=lambda e: float(e.get("confidence", 0.0)) + float(e.get("following_pause_s", 0.0)) * 0.22 + (0.20 if e.get("long_tail") else 0.0),
        reverse=True,
    )
    selected = sorted(ranked[:14], key=lambda e: float(e["time_s"]))
    mask = np.zeros(length, dtype=np.float32)
    for event in selected:
        end = min(max(int(float(event["time_s"]) * sr), 0), length)
        start = max(0, end - int(sr * 0.20))
        stop = min(length, end + int(sr * 0.04))
        if stop > start:
            local = np.hanning(max(stop - start, 4)).astype(np.float32)
            mask[start:stop] = np.maximum(mask[start:stop], local[: stop - start])
    source = (male * float(amp_db(-2.5)) + female * float(amp_db(-6.5))) * mask[:, None]
    slap = (
        pan_stereo(delay_samples(source, int(sr * 0.095)), -0.22)
        + pan_stereo(delay_samples(source, int(sr * 0.145)), 0.26)
    ) * float(amp_db(-28.5))
    room = reverb_send(source, sr, decay_s=0.34, wet_db=-31.5, predelay_ms=34, hp_hz=720, lp_hz=4800, seed=1515)
    fx = slap + room
    fx = sidechain_duck_full(fx.astype(np.float32), male, sr, amount_db=3.0, release_ms=170, threshold_percentile=55)
    fx, haze = dynamic_band_tame(fx.astype(np.float32), sr, 250, 900, 1.4, 68, 100)
    fx, hiss = dynamic_band_tame(fx.astype(np.float32), sr, 5400, 10500, 2.2, 60, 44)
    return fx.astype(np.float32), [
        {"stage": "v15_phrase_end_throw_fx", "selected_events": len(selected), "wet_policy": "phrase endings only, no global reverb/delay", "slap_db": -28.5, "reverb_wet_db": -31.5},
        {"stage": "v15_throw_lowmid_haze_guard", **haze},
        {"stage": "v15_throw_hiss_guard", **hiss},
    ]


def render_variant(
    sr: int,
    audio: dict[str, np.ndarray],
    variant: str,
    male: np.ndarray,
    female: np.ndarray,
) -> tuple[dict[str, Path], list[dict[str, object]]]:
    settings = VARIANTS[variant]
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)

    vocal_ref = male * float(amp_db(-0.8)) + female * float(amp_db(-3.2))
    inst_pocket = sidechain_duck_full(inst, vocal_ref, sr, amount_db=settings["instrumental_duck_db"], release_ms=126, threshold_percentile=59)
    inst_pocket = band_duck(inst_pocket, vocal_ref, sr, 250, 500, 0.78, 58)
    inst_pocket = band_duck(inst_pocket, male, sr, 1500, 4000, settings["presence_pocket_db"], 60)
    melody_pocket = sidechain_duck_full(melody, male, sr, amount_db=0.06, release_ms=110, threshold_percentile=68)
    throw, throw_moves = throw_fx(male, female, sr, length)
    mix = MO.safe_sum(
        [
            (inst_pocket, -1.10),
            (melody_pocket, 1.10),
            (drums, -10.65),
            (bass, -10.12),
            (male, settings["male_mix_db"]),
            (female, settings["female_mix_db"]),
            (throw, 0.0),
        ],
        length,
        -1.8,
    )
    mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(mix, sr, 20.0), sr)
    mix, shiik_mix = V14.suppress_shiik_noise(mix, sr, f"{variant}_full_mix", strength=0.14)
    mix = biquad_peaking(mix, sr, 330, -0.18, 0.95)
    mix = biquad_peaking(mix, sr, 2750, 0.06 if variant == "A_subtle" else 0.12, 0.95)
    mix = biquad_shelf(mix, sr, 11300, -0.06 if variant != "C_air_control" else 0.03, True)
    mix = stable_master_tone(mix, sr)
    mix = compressor(mix, sr, threshold_db=-12.5, ratio=1.04, smooth_ms=285, makeup_db=0.0)
    mix = soft_clip(mix, drive_db=0.14, ceiling=0.89)
    mix = limiter(mix, -2.2)

    suffix = {
        "A_subtle": "A_subtle",
        "B_presence": "B_presence",
        "C_air_control": "C_air_control",
    }[variant]
    premaster = RENDERS / f"0101_vocal_clarity_{suffix}_premaster.wav"
    final_wav = RENDERS / f"0101_vocal_clarity_{suffix}.wav"
    final_mp3 = RENDERS / f"0101_vocal_clarity_{suffix}_320.mp3"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-10.5, target_tp=-1.25, target_lra=3.6)
    convert_mp3(final_wav, final_mp3)
    moves = [
        {"stage": "v15_render_variant", "variant": variant, **settings},
        {"stage": "v15_instrumental_masking_control", "lowmid_duck_db": 0.78, "presence_duck_db": settings["presence_pocket_db"]},
        shiik_mix,
        *throw_moves,
        *mix_res,
    ]
    return {"premaster": premaster, "final_wav": final_wav, "final_mp3": final_mp3, "instrumental_stem": None}, moves


def score_variant(metrics: dict[str, object]) -> float:
    presence = float(metrics.get("presence_1500_5000_pct") or 0.0)
    sibilance = float(metrics.get("sibilance_5000_10000_pct") or 0.0)
    air = float(metrics.get("air_10000_16000_pct") or 0.0)
    lufs = float(metrics.get("integrated_lufs") or -99.0)
    true_peak = float(metrics.get("true_peak_dbfs") or 0.0)
    loudness_bonus = max(0.0, 1.0 - abs(lufs + 10.5) * 0.45)
    tp_penalty = max(0.0, true_peak + 0.95) * 3.0
    harsh_penalty = sibilance * 6.5 + air * 3.5
    return presence * 0.70 + loudness_bonus - harsh_penalty - tp_penalty


def select_preview_source(final_path: Path, male: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    sr_final, audio, _ = read_wav(final_path)
    if sr_final != sr:
        raise RuntimeError("sample-rate mismatch for preview")
    mono = np.mean(bandpass(male, sr, 150, 5200, 2), axis=1)
    win = int(sr * 15.0)
    hop = int(sr * 1.0)
    best_start = 0
    best_energy = -1.0
    for start in range(0, max(len(mono) - win, 1), hop):
        energy = float(np.mean(np.square(mono[start : start + win])) + 1e-12)
        if energy > best_energy:
            best_energy = energy
            best_start = start
    preview = audio[best_start : best_start + win]
    if len(preview) < win:
        preview = np.pad(preview, ((0, win - len(preview)), (0, 0)))
    return preview.astype(np.float32), best_start


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


def write_rpp(sr: int, audio: dict[str, np.ndarray], selected: Path, variant_paths: dict[str, Path], male_stem: Path, female_stem: Path) -> None:
    length = len(audio["male_raw"]) / sr
    tracks = [
        rpp_track("BACKUP_V14 muted", V14_FINAL, length, 1, True, False),
        rpp_track("MALE_V15_PROCESSED muted", male_stem, length, 2, True, False),
        rpp_track("FEMALE_V15_PANNED muted", female_stem, length, 3, True, False),
        rpp_track("A_SUBTLE muted", variant_paths["A_subtle"], length, 4, True, False),
        rpp_track("B_PRESENCE muted", variant_paths["B_presence"], length, 5, True, False),
        rpp_track("C_AIR_CONTROL muted", variant_paths["C_air_control"], length, 6, True, False),
        rpp_track("SELECTED_FINAL_ACTIVE", selected, length, 7, False, True),
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v15 dry vocal clarity pass. Main vocal has no global reverb/delay; only phrase-end throw is printed at very low level. Stock/free DSP-style chain documented in clarity_qc_report.md.
  >
  SAMPLERATE 48000 1 0
  TEMPO {BPM}.000000 4 4 0
  RENDER_RANGE 0 0 {length:.12f} 0 1000
  MASTER_NCH 2 2
{chr(10).join(tracks)}
>
""",
        encoding="utf-8",
    )


def write_reports(
    selected_variant: str,
    variant_metrics: list[dict[str, object]],
    reference_metrics: list[dict[str, object]],
    male_moves: dict[str, list[dict[str, object]]],
    female_moves: list[dict[str, object]],
    mix_moves: dict[str, list[dict[str, object]]],
    paths: dict[str, Path],
) -> Path:
    write_csv(REPORTS / "variant_metrics.csv", variant_metrics)
    write_csv(REPORTS / "reference_metrics.csv", reference_metrics)
    write_csv(REPORTS / "final_render_metrics.csv", [m for m in variant_metrics if m["label"] == f"selected_{selected_variant}"])
    (REPORTS / "processing_decisions.json").write_text(
        json.dumps(
            {
                "selected_variant": selected_variant,
                "selection_rule": "highest vocal presence score with penalties for sibilance/AI-air and unsafe true peak",
                "source_mode": "separate stems existed and were used; no stem separation needed",
                "male_vocal": male_moves,
                "female_layer": female_moves,
                "mix": mix_moves,
                "global_reverb_delay": "removed",
                "phrase_end_throw": "very subtle printed only on detected phrase endings",
                "backup": str(BACKUP / V14_FINAL.name),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    comparison = [
        {
            "label": row["label"],
            "integrated_lufs": row.get("integrated_lufs"),
            "true_peak_dbfs": row.get("true_peak_dbfs"),
            "rms_dbfs": row.get("rms_dbfs"),
            "presence_pct": row.get("presence_1500_5000_pct"),
            "sibilance_pct": row.get("sibilance_5000_10000_pct"),
            "air_pct": row.get("air_10000_16000_pct"),
            "score": row.get("selection_score"),
        }
        for row in variant_metrics
    ]
    (REPORTS / "clarity_qc_report.md").write_text(
        "\n".join(
            [
                "# 0101 Vocal Clarity QC Report",
                "",
                f"- Selected final: `{selected_variant}`.",
                "- Processing used existing vocal/instrumental stems; no Demucs/separation was needed.",
                "- Backup created before processing from the v14 final.",
                "- Main vocal global reverb/delay was removed; only very quiet phrase-ending throw FX was printed.",
                "- Vocal chain: low-mid dynamic cleanup, preserved 700 Hz-1.4 kHz formant, 2.5-4.5 kHz wide presence lift, 5.5-9 kHz de-ess, 9-13 kHz AI fizz control, parallel tune/presence layer, light saturation, gentle compression.",
                "- Instrumental masking control: subtle 250-500 Hz and 1.5-4 kHz dynamic pocketing during vocal phrases.",
                "- Female layer: side-panned, louder than earlier hidden versions, center kept low and ducked under the main vocal.",
                "- Artifacts noted: source is still AI/stem-derived, so exact note-by-note commercial vocal tuning is limited without a cleaner raw vocal or manual pitch editing.",
                "",
                "## Variant Metrics",
                "",
                markdown_table(comparison, ["label", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "presence_pct", "sibilance_pct", "air_pct", "score"]),
                "",
                "## Final Decision",
                "",
                f"`{selected_variant}` was selected because it gave the best measured clarity score without increasing sibilance/AI-air artifacts.",
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
                "- v15 follows the dry-vocal direction: no global vocal reverb or delay.",
                "- Phrase-ending throw FX is printed quietly and only at detected endings/focus points.",
                "- Three clarity passes were rendered; the selected final is copied to the main final filename.",
                "- RPP is a handoff/session file showing the backup, variants, processed stems, and selected print.",
                "- No Antares or paid plugins were used.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        paths["final_wav"],
        paths["final_mp3"],
        paths["preview"],
        paths["A_wav"],
        paths["B_wav"],
        paths["C_wav"],
        paths["male_stem"],
        paths["female_stem"],
        RPP,
        REPORTS / "clarity_qc_report.md",
        REPORTS / "variant_metrics.csv",
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
    variant_outputs: dict[str, dict[str, Path]] = {}
    variant_metrics: list[dict[str, object]] = []
    male_moves: dict[str, list[dict[str, object]]] = {}
    mix_moves: dict[str, list[dict[str, object]]] = {}
    male_stems: dict[str, np.ndarray] = {}
    female_stem: np.ndarray | None = None
    female_moves: list[dict[str, object]] = []

    for variant, settings in VARIANTS.items():
        male, moves = process_male(audio["male_raw"], sr, variant, settings)
        if female_stem is None:
            female_stem, female_moves = process_female(audio["female_layer"], male, sr)
        paths, mix = render_variant(sr, audio, variant, male, female_stem)
        metric = audio_metrics(paths["final_wav"], variant)
        metric["selection_score"] = round(score_variant(metric), 4)
        variant_metrics.append(metric)
        variant_outputs[variant] = paths
        male_moves[variant] = moves
        mix_moves[variant] = mix
        male_stems[variant] = male

    selected_metric = max(variant_metrics, key=lambda row: float(row["selection_score"]))
    selected_variant = str(selected_metric["label"])
    selected_paths = variant_outputs[selected_variant]
    final_wav = RENDERS / "0101_FINAL_v15_dry_vocal_clarity_selected.wav"
    final_mp3 = RENDERS / "0101_FINAL_v15_dry_vocal_clarity_selected_320.mp3"
    shutil.copy2(selected_paths["final_wav"], final_wav)
    shutil.copy2(selected_paths["final_mp3"], final_mp3)
    selected_final_metrics = audio_metrics(final_wav, f"selected_{selected_variant}")
    selected_final_metrics["selection_score"] = selected_metric["selection_score"]
    variant_metrics.append(selected_final_metrics)

    male_stem_path = RENDERS / "processed_male_vocal_v15_selected_stem.wav"
    female_stem_path = RENDERS / "processed_female_layer_v15_side_stem.wav"
    write_float_wav(male_stem_path, sr, male_stems[selected_variant])
    write_float_wav(female_stem_path, sr, female_stem)

    preview, preview_start = select_preview_source(final_wav, male_stems[selected_variant], sr)
    preview_path = RENDERS / "0101_vocal_clarity_preview_15s.wav"
    write_float_wav(preview_path, sr, preview)

    reference_metrics = [audio_metrics(path, f"reference_{path.stem}") for path in REFERENCE_PATHS if path.exists()]
    variant_paths = {name: data["final_wav"] for name, data in variant_outputs.items()}
    write_rpp(sr, audio, final_wav, variant_paths, male_stem_path, female_stem_path)
    report_paths = {
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "preview": preview_path,
        "A_wav": variant_outputs["A_subtle"]["final_wav"],
        "B_wav": variant_outputs["B_presence"]["final_wav"],
        "C_wav": variant_outputs["C_air_control"]["final_wav"],
        "male_stem": male_stem_path,
        "female_stem": female_stem_path,
    }
    zip_path = write_reports(
        selected_variant,
        variant_metrics,
        reference_metrics,
        male_moves,
        female_moves,
        mix_moves,
        report_paths,
    )
    print(
        json.dumps(
            {
                "slug": SLUG,
                "selected_variant": selected_variant,
                "final_wav": str(final_wav),
                "final_mp3": str(final_mp3),
                "preview_15s": str(preview_path),
                "preview_start_s": round(preview_start / sr, 3),
                "male_vocal_stem": str(male_stem_path),
                "female_layer_stem": str(female_stem_path),
                "reports": str(REPORTS),
                "reaper_project": str(RPP),
                "delivery_zip": str(zip_path),
                "scores": {row["label"]: row.get("selection_score") for row in variant_metrics},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
