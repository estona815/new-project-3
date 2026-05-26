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
    compressor,
    convert_mp3,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    ms_width,
    normalize_to_rms,
    read_wav,
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
V18 = load_module(ROOT / "tools" / "0101_v18_endpoint_throw_female_up.py", "codex_0101_v18")

SLUG = "0101_v19_final_vocal_redesign"
WORK = ROOT / "audio_work" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V19_FINAL_VOCAL_REDESIGN.rpp"
BPM = 135

BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
RAW_VOCAL = BASE_STEMS / "0101_vocal_raw.wav"
V18_RENDERS = ROOT / "renders" / "0101_v18_endpoint_throw_female_up"
V17_RENDERS = ROOT / "renders" / "0101_v17_vocal_pocket_synth_tame"


def ensure_dirs() -> None:
    for directory in (WORK, RENDERS, REPORTS, REAPER_DIR):
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


def harmonic_voice_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    layer = bandpass(vocal, sr, 155, 1500, 3)
    layer = compressor(layer, sr, threshold_db=-35.0, ratio=2.15, smooth_ms=82, makeup_db=0.7)
    layer = saturate(layer, drive_db=1.15, mix=0.085)
    layer, mud = dynamic_band_tame(layer, sr, 230, 470, 0.72, 76, 130)
    layer, nasal = dynamic_band_tame(layer, sr, 760, 1420, 0.32, 84, 120)
    layer = biquad_peaking(layer, sr, 220, 0.20, 0.85)
    layer = safe_normalize(layer, -26.3)
    return layer.astype(np.float32), {
        "stage": "v19_harmonic_voice_layer",
        "purpose": "body/formant density without EQ haze",
        "return_gain_db": -8.2,
        "mud_control": mud,
        "nasal_control": nasal,
    }


def consonant_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    layer = bandpass(vocal, sr, 2100, 5200, 3)
    layer = compressor(layer, sr, threshold_db=-36.0, ratio=3.8, smooth_ms=22, makeup_db=0.9)
    layer = vocal_harmonic_density(layer, sr, drive_db=1.95, wet=0.13)
    layer, edge = dynamic_band_tame(layer, sr, 3300, 5900, 1.05, 72, 48)
    layer, hiss = dynamic_band_tame(layer, sr, 5600, 9800, 1.65, 66, 42)
    layer = biquad_peaking(layer, sr, 2850, 0.46, 0.85)
    layer = biquad_shelf(layer, sr, 9500, -0.42, True)
    layer = safe_normalize(layer, -27.6)
    return layer.astype(np.float32), {
        "stage": "v19_consonant_layer",
        "purpose": "articulation without raising whole vocal",
        "return_gain_db": -7.4,
        "edge_control": edge,
        "hiss_control": hiss,
    }


def required_tune_noise_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    cleaned, shiik = V14.suppress_shiik_noise(vocal, sr, "v19_required_tune_pre", strength=0.36)
    cleaned, sib = dynamic_band_tame(cleaned, sr, 5500, 9000, 0.95, 68, 45)
    cleaned, fizz = dynamic_band_tame(cleaned, sr, 9000, 13200, 0.78, 70, 42)
    tune, tune_stats = MO.strong_tune_density_layer(cleaned, sr)
    tune, tune_sib = dynamic_band_tame(tune, sr, 5400, 9800, 1.45, 66, 44)
    tune = saturate(tune, drive_db=0.85, mix=0.055)
    tune = safe_normalize(tune, -24.4)
    return tune.astype(np.float32), {
        "stage": "v19_required_tune_noise_layer",
        "return_gain_db": -8.5,
        "policy": "required tune/noise chain, controlled parallel",
        "shiik": shiik,
        "sibilance": sib,
        "fizz": fizz,
        "tune": tune_stats,
        "tune_deess": tune_sib,
    }


def process_male_redesign(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    core = MO.edge_fade(raw, sr, 14.0)
    core = V12.butter_filter(core, sr, "highpass", 72, 3)
    core, beep = MO.suppress_beep_artifacts(core, sr, "v19_raw_core", strength=0.62)
    core, shiik_pre = V14.suppress_shiik_noise(core, sr, "v19_raw_core_pre", strength=0.38)
    moves.extend([{"stage": "v19_start_from_raw", "source": str(RAW_VOCAL)}, beep, shiik_pre])
    for low, high, cut, pct, smooth, name in [
        (230, 430, 0.55, 78, 135, "mud_light"),
        (520, 900, 0.36, 80, 122, "blanket_light"),
        (930, 1420, 0.12, 88, 126, "formant_preserve"),
        (5450, 9000, 1.15, 66, 46, "sibilance_separate"),
        (9000, 13200, 0.88, 70, 42, "ai_fizz_separate"),
    ]:
        core, stats = dynamic_band_tame(core, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"v19_core_{name}", **stats})
    harmonic, harmonic_stats = harmonic_voice_layer(core, sr)
    consonant, consonant_stats = consonant_layer(core, sr)
    tune, tune_stats = required_tune_noise_layer(core, sr)
    out = (
        core * float(amp_db(0.90))
        + harmonic * float(amp_db(-8.2))
        + consonant * float(amp_db(-7.4))
        + tune * float(amp_db(-8.5))
    )
    out = biquad_peaking(out, sr, 215, 0.18, 0.90)
    out = biquad_peaking(out, sr, 720, -0.10, 1.05)
    out = biquad_peaking(out, sr, 2700, 0.38, 0.90)
    out = biquad_peaking(out, sr, 3950, 0.14, 1.08)
    out = biquad_shelf(out, sr, 10400, -0.04, True)
    out = saturate(out, drive_db=1.55, mix=0.11)
    out = soft_clip(out, drive_db=0.30, ceiling=0.90)
    out = compressor(out, sr, threshold_db=-23.6, ratio=1.9, smooth_ms=68, makeup_db=0.12)
    out, sib = dynamic_band_tame(out, sr, 5450, 9000, 0.95, 70, 46)
    out, fizz = dynamic_band_tame(out, sr, 9200, 13200, 0.75, 72, 42)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-19.5, max_cut_db=-4.8, max_boost_db=0.75, label="v19_vocal_redesign")
    out = safe_normalize(out, -18.35)
    out = limiter(MO.edge_fade(out, sr, 12.0), -1.75)
    moves.extend(
        [
            harmonic_stats,
            consonant_stats,
            tune_stats,
            {"stage": "v19_final_presence_sat", "presence_2700_db": 0.38, "presence_3950_db": 0.14, "sat_drive_db": 1.55, "sat_mix": 0.11},
            {"stage": "v19_final_sibilance_guard", **sib},
            {"stage": "v19_final_fizz_guard", **fizz},
            ride,
            {"stage": "v19_final_male_gain", "target_rms_dbfs": -18.35, "intent": "source redesign 2+3+6"},
        ]
    )
    return out.astype(np.float32), moves


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray, female_v18: np.ndarray, melody_tamed: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)
    melody = pad_or_trim(melody_tamed, length)
    female = limiter(pad_or_trim(female_v18, length) * float(amp_db(1.0)), -3.0)
    throw, throw_moves = V18.endpoint_throw(male, sr, length)

    vocal_ref = male * float(amp_db(0.0)) + female * float(amp_db(-4.7))
    inst_pocket = sidechain_duck_full(inst, vocal_ref, sr, amount_db=0.76, release_ms=128, threshold_percentile=60)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 250, 520, 0.76, 58)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 1500, 4100, 1.10, 60)
    inst_pocket, inst_edge = dynamic_band_tame(inst_pocket, sr, 2600, 5200, 0.45, 76, 75)
    inst_pocket, inst_fizz = dynamic_band_tame(inst_pocket, sr, 8200, 12800, 0.65, 70, 60)
    inst_pocket = ms_width(inst_pocket, 0.12)

    mix = MO.safe_sum(
        [
            (inst_pocket, -1.12),
            (melody, 0.68),
            (drums, -10.65),
            (bass, -10.10),
            (male, -2.28),
            (female, -2.95),
            (throw, 0.0),
        ],
        length,
        -1.8,
    )
    mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(mix, sr, 18.0), sr)
    mix = biquad_peaking(mix, sr, 330, -0.08, 0.95)
    mix = biquad_peaking(mix, sr, 2600, 0.04, 0.90)
    mix = biquad_shelf(mix, sr, 11600, -0.06, True)
    mix = stable_master_tone(mix, sr)
    mix = compressor(mix, sr, threshold_db=-12.7, ratio=1.035, smooth_ms=290, makeup_db=0.0)
    mix = soft_clip(mix, drive_db=0.10, ceiling=0.89)
    mix = limiter(mix, -2.2)

    premaster = RENDERS / "0101_mix_v19_final_vocal_redesign_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v19_final_vocal_redesign.wav"
    final_mp3 = RENDERS / "0101_FINAL_v19_final_vocal_redesign_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v19_redesigned_stem.wav"
    female_path = RENDERS / "processed_female_layer_v19_side_plus1db_more_stem.wav"
    throw_path = RENDERS / "endpoint_throw_fx_v19_stem.wav"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-10.3, target_tp=-1.2, target_lra=3.8)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, female)
    write_float_wav(throw_path, sr, throw)
    return {
        "premaster": premaster,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "male_stem": male_path,
        "female_stem": female_path,
        "throw_stem": throw_path,
    }, [
        {"stage": "v19_mix", "base": "v18 approved feel", "female_gain_change_db_vs_v18": 1.0, "male_mix_gain_db": -2.28, "global_reverb_delay": "none", "endpoint_throw": "kept"},
        {"stage": "v19_instrumental_pocket", "full_duck_db": 0.76, "lowmid_duck_db": 0.76, "presence_duck_db": 1.10},
        {"stage": "v19_instrumental_edge_tame", **inst_edge},
        {"stage": "v19_instrumental_fizz_tame", **inst_fizz},
        *throw_moves,
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
        rpp_track("V18_REFERENCE muted", V18_RENDERS / "0101_FINAL_v18_endpoint_throw_female_up.wav", length, 1, True, False),
        rpp_track("RAW_VOCAL_REFERENCE muted", RAW_VOCAL, length, 2, True, False),
        rpp_track("MALE_V19_REDESIGNED muted", paths["male_stem"], length, 3, True, False),
        rpp_track("FEMALE_V19_SIDE_PLUS1_MORE muted", paths["female_stem"], length, 4, True, False),
        rpp_track("ENDPOINT_THROW_V19 muted", paths["throw_stem"], length, 5, True, False),
        rpp_track("V19_FINAL_ACTIVE", paths["final_wav"], length, 6, False, True),
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v19 final vocal redesign. Applies source redesign 2/3/6: harmonic density, consonant layer, noise/clarity separation. Female side layer +1 dB over v18.
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


def write_reports(paths: dict[str, Path], male_moves: list[dict[str, object]], mix_moves: list[dict[str, object]]) -> Path:
    metrics = [
        audio_metrics(RAW_VOCAL, "raw_vocal_reference"),
        audio_metrics(V18_RENDERS / "0101_FINAL_v18_endpoint_throw_female_up.wav", "v18_reference"),
        audio_metrics(paths["male_stem"], "v19_male_redesigned_stem"),
        audio_metrics(paths["female_stem"], "v19_female_plus1_more_stem"),
        audio_metrics(paths["throw_stem"], "v19_endpoint_throw_fx_stem"),
        audio_metrics(paths["final_wav"], "v19_final_wav"),
        audio_metrics(paths["final_mp3"], "v19_final_mp3"),
    ]
    write_csv(REPORTS / "v19_metrics.csv", metrics)
    summary = [
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
    (REPORTS / "v19_final_qc_report.md").write_text(
        "\n".join(
            [
                "# v19 Final QC Report",
                "",
                "- Applied requested methods 2, 3, and 6.",
                "- Method 2: raw vocal redesign with harmonic/body/formant layer under the original core.",
                "- Method 3: consonant layer for perceived lyric articulation.",
                "- Method 6: sibilance/AI fizz separated and controlled before presence is added.",
                "- Required tune/noise chain remains included as controlled parallel, not replacing the main core.",
                "- Female side layer is +1 dB louder than v18.",
                "- Endpoint throw delay/reverb is kept; no global vocal reverb/delay.",
                "",
                markdown_table(summary, ["label", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "formant_pct", "presence_pct", "sibilance_pct", "air_pct"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPORTS / "processing_decisions.json").write_text(
        json.dumps({"male_moves": male_moves, "mix_moves": mix_moves}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        paths["final_wav"],
        paths["final_mp3"],
        paths["premaster"],
        paths["male_stem"],
        paths["female_stem"],
        paths["throw_stem"],
        RPP,
        REPORTS / "v19_final_qc_report.md",
        REPORTS / "v19_metrics.csv",
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
    mel_sr, melody_tamed, _ = read_wav(V17_RENDERS / "processed_melody_synth_v17_tamed_stem.wav")
    female_sr, female_v18, _ = read_wav(V18_RENDERS / "processed_female_layer_v18_side_plus1db_stem.wav")
    if mel_sr != sr or female_sr != sr:
        raise RuntimeError("sample-rate mismatch")
    length = max(len(audio["male_raw"]), len(melody_tamed), len(female_v18))
    audio = {name: pad_or_trim(y, length) for name, y in audio.items()}
    male, male_moves = process_male_redesign(audio["male_raw"], sr)
    male = pad_or_trim(male, length)
    melody_tamed = pad_or_trim(melody_tamed, length)
    female_v18 = pad_or_trim(female_v18, length)
    paths, mix_moves = render(sr, audio, male, female_v18, melody_tamed)
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
                "female_layer_stem": str(paths["female_stem"]),
                "throw_fx_stem": str(paths["throw_stem"]),
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
