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
    biquad_peaking,
    biquad_shelf,
    compressor,
    convert_mp3,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    ms_width,
    read_wav,
    saturate,
    sidechain_duck_full,
    soft_clip,
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
V16 = load_module(ROOT / "tools" / "0101_v16_raw_core_sat_clarity.py", "codex_0101_v16")

SLUG = "0101_v17_vocal_pocket_synth_tame"
WORK = ROOT / "audio_work" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V17_VOCAL_POCKET_SYNTH_TAME.rpp"
BPM = 135

V16_RENDERS = ROOT / "renders" / "0101_v16_raw_core_sat_clarity"
RAW_VOCAL = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems" / "0101_vocal_raw.wav"


def ensure_dirs() -> None:
    for directory in (WORK, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return MO.pad_or_trim(y, length)


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


def tame_synth_melody(melody: np.ndarray, male: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = sidechain_duck_full(melody, male, sr, amount_db=0.20, release_ms=118, threshold_percentile=67)
    out = V15.band_duck(out, male, sr, 1800, 4200, 0.72, 60)
    out, edge = dynamic_band_tame(out, sr, 2600, 5000, 0.82, 72, 72)
    out, fizz = dynamic_band_tame(out, sr, 7800, 12200, 1.10, 66, 58)
    out = biquad_peaking(out, sr, 3400, -0.18, 1.05)
    out = biquad_shelf(out, sr, 10800, -0.22, True)
    return out.astype(np.float32), [
        {"stage": "v17_melody_synth_vocal_duck", "full_duck_db": 0.20, "presence_band_duck_db": 0.72},
        {"stage": "v17_synth_edge_tame", **edge},
        {"stage": "v17_synth_fizz_tame", **fizz},
    ]


def apply_required_tune_noise_chain(male: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    clean, shiik = V14.suppress_shiik_noise(male, sr, "v17_required_tune_noise_pre", strength=0.30)
    clean, sib = dynamic_band_tame(clean, sr, 5450, 9000, 0.80, 70, 46)
    clean, fizz = dynamic_band_tame(clean, sr, 9000, 13200, 0.55, 72, 42)
    tune_layer, tune_stats = MO.strong_tune_density_layer(clean, sr)
    tune_layer, tune_sib = dynamic_band_tame(tune_layer, sr, 5400, 9800, 1.35, 66, 45)
    tune_layer = saturate(tune_layer, drive_db=0.95, mix=0.060)
    out = clean * float(amp_db(0.82)) + tune_layer * float(amp_db(-7.8))
    out = biquad_peaking(out, sr, 2550, 0.16, 0.92)
    out = biquad_shelf(out, sr, 10400, -0.06, True)
    out = soft_clip(out, drive_db=0.16, ceiling=0.90)
    out = limiter(MO.edge_fade(out, sr, 10.0), -1.8)
    return out.astype(np.float32), [
        {"stage": "v17_required_tune_noise_chain", "policy": "required by user, parallel/controlled so raw core remains main"},
        shiik,
        {"stage": "v17_required_chain_sibilance_guard", **sib},
        {"stage": "v17_required_chain_fizz_guard", **fizz},
        {**tune_stats, "mix_gain_db": -7.8},
        {"stage": "v17_required_tune_layer_deess", **tune_sib},
    ]


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray, female: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)

    melody_tamed, melody_moves = tame_synth_melody(melody, male, sr)
    vocal_ref = male * float(amp_db(0.0)) + female * float(amp_db(-6.0))
    inst_pocket = sidechain_duck_full(inst, vocal_ref, sr, amount_db=0.74, release_ms=128, threshold_percentile=60)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 250, 520, 0.72, 58)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 1500, 4100, 1.05, 60)
    inst_pocket, inst_edge = dynamic_band_tame(inst_pocket, sr, 2600, 5200, 0.42, 76, 75)
    inst_pocket, inst_fizz = dynamic_band_tame(inst_pocket, sr, 8200, 12800, 0.65, 70, 60)
    inst_pocket = ms_width(inst_pocket, 0.15)

    mix = MO.safe_sum(
        [
            (inst_pocket, -1.12),
            (melody_tamed, 0.70),
            (drums, -10.65),
            (bass, -10.10),
            (male, -2.05),
            (female, -2.95),
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
    mix = soft_clip(mix, drive_db=0.11, ceiling=0.89)
    mix = limiter(mix, -2.2)

    premaster = RENDERS / "0101_mix_v17_vocal_pocket_synth_tame_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v17_vocal_pocket_synth_tame.wav"
    final_mp3 = RENDERS / "0101_FINAL_v17_vocal_pocket_synth_tame_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v17_raw_core_plus1db_stem.wav"
    female_path = RENDERS / "processed_female_layer_v17_side_support_stem.wav"
    inst_path = RENDERS / "processed_instrumental_v17_pocket_stem.wav"
    melody_path = RENDERS / "processed_melody_synth_v17_tamed_stem.wav"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-10.6, target_tp=-1.2, target_lra=3.8)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, female)
    write_float_wav(inst_path, sr, limiter(inst_pocket, -1.8))
    write_float_wav(melody_path, sr, limiter(melody_tamed, -2.0))
    return {
        "premaster": premaster,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "male_stem": male_path,
        "female_stem": female_path,
        "instrumental_stem": inst_path,
        "melody_stem": melody_path,
    }, [
        {"stage": "v17_mix_revision", "male_gain_db": -2.05, "v16_male_gain_db": -3.05, "female_side_gain_db": -2.95, "melody_gain_db": 0.70, "v16_melody_gain_db": 1.12},
        {"stage": "v17_instrumental_pocket", "full_duck_db": 0.74, "lowmid_duck_db": 0.72, "presence_duck_db": 1.05},
        {"stage": "v17_instrumental_edge_tame", **inst_edge},
        {"stage": "v17_instrumental_fizz_tame", **inst_fizz},
        *melody_moves,
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
        rpp_track("V16_REFERENCE muted", V16_RENDERS / "0101_FINAL_v16_raw_core_sat_clarity.wav", length, 1, True, False),
        rpp_track("RAW_VOCAL_REFERENCE muted", RAW_VOCAL, length, 2, True, False),
        rpp_track("MALE_V17_PLUS1DB muted", paths["male_stem"], length, 3, True, False),
        rpp_track("FEMALE_V17_SIDE muted", paths["female_stem"], length, 4, True, False),
        rpp_track("INSTRUMENTAL_V17_POCKET muted", paths["instrumental_stem"], length, 5, True, False),
        rpp_track("MELODY_SYNTH_V17_TAMED muted", paths["melody_stem"], length, 6, True, False),
        rpp_track("V17_FINAL_ACTIVE", paths["final_wav"], length, 7, False, True),
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v17 vocal pocket and synth tame. Built from v16 raw-core vocal, +1 dB vocal gain, stronger dynamic instrumental pocket, melody/synth edge tamed.
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


def write_reports(paths: dict[str, Path], mix_moves: list[dict[str, object]]) -> Path:
    metrics = [
        audio_metrics(V16_RENDERS / "0101_FINAL_v16_raw_core_sat_clarity.wav", "v16_reference"),
        audio_metrics(paths["final_wav"], "v17_final_wav"),
        audio_metrics(paths["final_mp3"], "v17_final_mp3"),
        audio_metrics(paths["male_stem"], "v17_male_plus1db_tune_noise_stem"),
        audio_metrics(paths["melody_stem"], "v17_melody_synth_tamed_stem"),
    ]
    write_csv(REPORTS / "v17_metrics.csv", metrics)
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
    (REPORTS / "v17_mix_qc_report.md").write_text(
        "\n".join(
            [
                "# v17 Mix QC Report",
                "",
                "- Started from v16 raw-core vocal direction.",
                "- Main vocal is raised by about 1 dB in the mix.",
                "- Required tune/noise chain is included as a controlled parallel layer, not as the main vocal core.",
                "- Instrumental gets stronger dynamic pocketing at 250-520 Hz and 1.5-4.1 kHz while vocal is active.",
                "- Melody/synth overlay is reduced from v16 and dynamically tamed around 2.6-5 kHz and 7.8-12.2 kHz to reduce awkward synth edge.",
                "- No global reverb/delay added.",
                "",
                markdown_table(summary, ["label", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "formant_pct", "presence_pct", "sibilance_pct", "air_pct"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPORTS / "processing_decisions.json").write_text(json.dumps({"mix_moves": mix_moves}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        paths["final_wav"],
        paths["final_mp3"],
        paths["premaster"],
        paths["male_stem"],
        paths["female_stem"],
        paths["instrumental_stem"],
        paths["melody_stem"],
        RPP,
        REPORTS / "v17_mix_qc_report.md",
        REPORTS / "v17_metrics.csv",
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
    male_sr, male, _ = read_wav(V16_RENDERS / "processed_male_vocal_v16_raw_core_sat_stem.wav")
    female_sr, female, _ = read_wav(V16_RENDERS / "processed_female_layer_v16_side_support_stem.wav")
    if male_sr != sr or female_sr != sr:
        raise RuntimeError("sample-rate mismatch")
    length = max(len(audio["male_raw"]), len(male), len(female))
    audio = {name: pad_or_trim(y, length) for name, y in audio.items()}
    male = pad_or_trim(male, length)
    female = pad_or_trim(female, length)
    male, tune_noise_moves = apply_required_tune_noise_chain(male, sr)
    paths, moves = render(sr, audio, male, female)
    moves = tune_noise_moves + moves
    write_rpp(sr, audio, paths)
    zip_path = write_reports(paths, moves)
    print(
        json.dumps(
            {
                "slug": SLUG,
                "final_wav": str(paths["final_wav"]),
                "final_mp3": str(paths["final_mp3"]),
                "premaster": str(paths["premaster"]),
                "male_vocal_stem": str(paths["male_stem"]),
                "female_layer_stem": str(paths["female_stem"]),
                "melody_synth_stem": str(paths["melody_stem"]),
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
