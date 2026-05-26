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
V15 = load_module(ROOT / "tools" / "0101_v15_dry_vocal_clarity_final.py", "codex_0101_v15")

SLUG = "0101_v16_raw_core_sat_clarity"
WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V16_RAW_CORE_SAT_CLARITY.rpp"
BPM = 135

BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
V15_RENDERS = ROOT / "renders" / "0101_v15_dry_vocal_clarity_final"
RAW_VOCAL = BASE_STEMS / "0101_vocal_raw.wav"


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


def process_raw_vocal(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = MO.edge_fade(raw, sr, 14.0)
    out = butter_filter(out, sr, "highpass", 74, 3)
    moves.append({"stage": "raw_start_no_prior_chain", "source": str(RAW_VOCAL), "hpf_hz": 74})

    out, beep = MO.suppress_beep_artifacts(out, sr, "v16_raw", strength=0.58)
    moves.append({**beep, "note": "lighter than v12/v15 to avoid dulling raw consonants"})
    out, shiik = V14.suppress_shiik_noise(out, sr, "v16_raw_main", strength=0.34)
    moves.append(shiik)

    for low, high, cut, pct, smooth, name in [
        (230, 430, 0.55, 78, 135, "low_mud_light"),
        (520, 840, 0.42, 78, 122, "blanket_light"),
        (930, 1420, 0.18, 86, 126, "formant_preserve"),
        (5650, 8800, 1.05, 66, 48, "sibilance_control_not_kill"),
        (9000, 13200, 0.78, 68, 44, "ai_fizz_light"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"v16_dynamic_{name}", **stats})

    body = bandpass(out, sr, 175, 430, 3)
    body = compressor(body, sr, threshold_db=-35.5, ratio=2.0, smooth_ms=90, makeup_db=0.55)
    body = saturate(body, drive_db=0.75, mix=0.055)
    body = safe_normalize(body, -27.2)

    clarity = bandpass(out, sr, 1650, 4650, 3)
    clarity = compressor(clarity, sr, threshold_db=-35.0, ratio=2.4, smooth_ms=34, makeup_db=0.40)
    clarity = vocal_harmonic_density(clarity, sr, drive_db=1.20, wet=0.075)
    clarity, clarity_edge = dynamic_band_tame(clarity, sr, 3150, 5600, 0.75, 74, 54)
    clarity = safe_normalize(clarity, -28.0)

    out = out * float(amp_db(0.88)) + body * float(amp_db(-10.2)) + clarity * float(amp_db(-10.8))
    out = biquad_peaking(out, sr, 210, 0.22, 0.90)
    out = biquad_peaking(out, sr, 720, -0.16, 1.05)
    out = biquad_peaking(out, sr, 2600, 0.48, 0.88)
    out = biquad_peaking(out, sr, 3850, 0.18, 1.10)
    out = biquad_shelf(out, sr, 10400, 0.05, True)
    out = saturate(out, drive_db=1.65, mix=0.115)
    out = soft_clip(out, drive_db=0.42, ceiling=0.90)
    out = compressor(out, sr, threshold_db=-23.8, ratio=1.85, smooth_ms=70, makeup_db=0.14)
    out, post_sib = dynamic_band_tame(out, sr, 5500, 9000, 0.85, 70, 46)
    out, post_fizz = dynamic_band_tame(out, sr, 9200, 13200, 0.62, 72, 42)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-20.1, max_cut_db=-4.6, max_boost_db=0.75, label="v16_raw_core")
    out = safe_normalize(out, -18.65)
    out = limiter(MO.edge_fade(out, sr, 12.0), -1.8)
    moves.extend(
        [
            {"stage": "v16_body_parallel_return", "gain_db": -10.2, "band_hz": "175-430"},
            {"stage": "v16_clarity_parallel_return", "gain_db": -10.8, "band_hz": "1650-4650", "edge_control": clarity_edge},
            {"stage": "v16_static_presence_sat", "presence_2600_db": 0.48, "presence_3850_db": 0.18, "sat_drive_db": 1.65, "sat_mix": 0.115},
            {"stage": "v16_post_sibilance_guard", **post_sib},
            {"stage": "v16_post_fizz_guard", **post_fizz},
            ride,
            {"stage": "v16_final_raw_core_gain", "target_rms_dbfs": -18.65, "intent": "raw core preserved; saturation and clarity only"},
        ]
    )
    return out.astype(np.float32), moves


def process_female_side(female: np.ndarray, male: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    side, moves = V14.process_female_v14(female, male, sr)
    side = sidechain_duck_full(side, male, sr, amount_db=2.0, release_ms=125, threshold_percentile=58)
    side = safe_normalize(side, -22.2)
    side = limiter(side, -5.0)
    moves.append({"stage": "v16_female_side_support", "target_rms_dbfs": -22.2, "note": "kept side-only so it does not blur raw main"})
    return side.astype(np.float32), moves


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray, female: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)

    vocal_ref = male * float(amp_db(-0.5)) + female * float(amp_db(-5.8))
    inst_pocket = sidechain_duck_full(inst, vocal_ref, sr, amount_db=0.56, release_ms=126, threshold_percentile=60)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 1500, 4000, 0.58, 60)
    melody_pocket = sidechain_duck_full(melody, male, sr, amount_db=0.05, release_ms=110, threshold_percentile=68)
    mix = MO.safe_sum(
        [
            (inst_pocket, -1.05),
            (melody_pocket, 1.12),
            (drums, -10.65),
            (bass, -10.10),
            (male, -3.05),
            (female, -2.75),
        ],
        length,
        -1.8,
    )
    mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(mix, sr, 18.0), sr)
    mix = biquad_peaking(mix, sr, 330, -0.10, 0.95)
    mix = biquad_peaking(mix, sr, 2600, 0.04, 0.90)
    mix = biquad_shelf(mix, sr, 11600, -0.06, True)
    mix = stable_master_tone(mix, sr)
    mix = compressor(mix, sr, threshold_db=-12.6, ratio=1.035, smooth_ms=290, makeup_db=0.0)
    mix = soft_clip(mix, drive_db=0.12, ceiling=0.89)
    mix = limiter(mix, -2.2)

    premaster = RENDERS / "0101_mix_v16_raw_core_sat_clarity_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v16_raw_core_sat_clarity.wav"
    final_mp3 = RENDERS / "0101_FINAL_v16_raw_core_sat_clarity_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v16_raw_core_sat_stem.wav"
    female_path = RENDERS / "processed_female_layer_v16_side_support_stem.wav"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-10.7, target_tp=-1.2, target_lra=3.8)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, female)
    return {
        "premaster": premaster,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "male_stem": male_path,
        "female_stem": female_path,
    }, [
        {"stage": "v16_mix_route", "male_gain_db": -3.05, "female_side_gain_db": -2.75, "global_reverb_delay": "none", "throw_fx": "none"},
        {"stage": "v16_instrumental_vocal_pocket", "full_duck_db": 0.56, "presence_band_duck_db": 0.58},
        *mix_res,
    ]


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
        rpp_track("RAW_VOCAL_REFERENCE muted", RAW_VOCAL, length, 1, True, False),
        rpp_track("V15_FINAL_REFERENCE muted", V15_RENDERS / "0101_FINAL_v15_dry_vocal_clarity_selected.wav", length, 2, True, False),
        rpp_track("MALE_V16_RAW_CORE muted", paths["male_stem"], length, 3, True, False),
        rpp_track("FEMALE_V16_SIDE muted", paths["female_stem"], length, 4, True, False),
        rpp_track("V16_FINAL_ACTIVE", paths["final_wav"], length, 5, False, True),
        rpp_track("V16_MP3_MONITOR muted", paths["final_mp3"], length, 6, True, False),
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v16 raw-core vocal pass. Starts from raw vocal stem, not from previous processed vocal. Saturation/clarity only, no global reverb or delay.
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


def write_reports(paths: dict[str, Path], male_moves: list[dict[str, object]], female_moves: list[dict[str, object]], mix_moves: list[dict[str, object]]) -> Path:
    metrics = [
        audio_metrics(RAW_VOCAL, "raw_vocal_reference"),
        audio_metrics(V15_RENDERS / "processed_male_vocal_v15_selected_stem.wav", "v15_processed_male_reference"),
        audio_metrics(paths["male_stem"], "v16_processed_male_raw_core"),
        audio_metrics(V15_RENDERS / "0101_FINAL_v15_dry_vocal_clarity_selected.wav", "v15_final_reference"),
        audio_metrics(paths["final_wav"], "v16_final_wav"),
        audio_metrics(paths["final_mp3"], "v16_final_mp3"),
    ]
    write_csv(REPORTS / "raw_vs_v16_metrics.csv", metrics)
    comparison = [
        {
            "label": row["label"],
            "integrated_lufs": row.get("integrated_lufs"),
            "true_peak_dbfs": row.get("true_peak_dbfs"),
            "rms_dbfs": row.get("rms_dbfs"),
            "formant_pct": row.get("formant_500_1500_pct"),
            "presence_pct": row.get("presence_1500_5000_pct"),
            "sibilance_pct": row.get("sibilance_5000_10000_pct"),
            "air_pct": row.get("air_10000_16000_pct"),
        }
        for row in metrics
    ]
    (REPORTS / "v16_raw_core_qc_report.md").write_text(
        "\n".join(
            [
                "# v16 Raw Core QC Report",
                "",
                "- Cause found: v15 processed male reduced the raw 700 Hz-1.5 kHz formant core too much and pushed 1.5-5 kHz presence too hard.",
                "- v16 starts directly from `0101_vocal_raw.wav`, with only light cleanup, saturation, preserved body/formant, and a small clarity parallel.",
                "- No global reverb/delay and no phrase throw FX in this pass.",
                "- Female layer remains side support only, lower than the raw main vocal so it does not blur the center.",
                "",
                markdown_table(comparison, ["label", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "formant_pct", "presence_pct", "sibilance_pct", "air_pct"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPORTS / "processing_decisions.json").write_text(
        json.dumps({"male_moves": male_moves, "female_moves": female_moves, "mix_moves": mix_moves}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        paths["final_wav"],
        paths["final_mp3"],
        paths["premaster"],
        paths["male_stem"],
        paths["female_stem"],
        RPP,
        REPORTS / "v16_raw_core_qc_report.md",
        REPORTS / "raw_vs_v16_metrics.csv",
        REPORTS / "processing_decisions.json",
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
    male, male_moves = process_raw_vocal(audio["male_raw"], sr)
    female, female_moves = process_female_side(audio["female_layer"], male, sr)
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
