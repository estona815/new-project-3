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
    delay_samples,
    detect_phrase_endings,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    ms_width,
    pan_stereo,
    read_wav,
    reverb_send,
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
V15 = load_module(ROOT / "tools" / "0101_v15_dry_vocal_clarity_final.py", "codex_0101_v15")
V17 = load_module(ROOT / "tools" / "0101_v17_vocal_pocket_synth_tame.py", "codex_0101_v17")

SLUG = "0101_v18_endpoint_throw_female_up"
WORK = ROOT / "audio_work" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V18_ENDPOINT_THROW_FEMALE_UP.rpp"
BPM = 135

V17_RENDERS = ROOT / "renders" / "0101_v17_vocal_pocket_synth_tame"


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


def endpoint_throw(male: np.ndarray, sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    endings = detect_phrase_endings(male, sr)
    ranked = sorted(
        [
            e
            for e in endings
            if e.get("throw") or float(e.get("following_pause_s", 0.0)) >= 0.38 or float(e.get("confidence", 0.0)) >= 0.64
        ],
        key=lambda e: float(e.get("confidence", 0.0)) + float(e.get("following_pause_s", 0.0)) * 0.28 + (0.22 if e.get("long_tail") else 0.0),
        reverse=True,
    )
    selected = sorted(ranked[:16], key=lambda e: float(e["time_s"]))
    mask = np.zeros(length, dtype=np.float32)
    for event in selected:
        end = min(max(int(float(event["time_s"]) * sr), 0), length)
        start = max(0, end - int(sr * 0.18))
        stop = min(length, end + int(sr * 0.045))
        if stop <= start:
            continue
        local = np.hanning(max(stop - start, 4)).astype(np.float32)
        mask[start:stop] = np.maximum(mask[start:stop], local[: stop - start])
    src = male * mask[:, None]
    slap = (
        pan_stereo(delay_samples(src, int(sr * 0.105)), -0.28)
        + pan_stereo(delay_samples(src, int(sr * 0.155)), 0.32)
    ) * float(amp_db(-26.5))
    room = reverb_send(src, sr, decay_s=0.42, wet_db=-30.5, predelay_ms=36, hp_hz=760, lp_hz=5200, seed=1818)
    fx = slap + room
    fx = sidechain_duck_full(fx.astype(np.float32), male, sr, amount_db=2.4, release_ms=180, threshold_percentile=54)
    fx, lowmid = dynamic_band_tame(fx.astype(np.float32), sr, 250, 900, 1.35, 68, 96)
    fx, hiss = dynamic_band_tame(fx.astype(np.float32), sr, 5400, 10400, 2.0, 62, 44)
    fx = limiter(fx, -9.0)
    return fx.astype(np.float32), [
        {"stage": "v18_endpoint_throw", "events": len(selected), "slap_db": -26.5, "reverb_wet_db": -30.5, "policy": "endpoints/focus only"},
        {"stage": "v18_throw_lowmid_guard", **lowmid},
        {"stage": "v18_throw_hiss_guard", **hiss},
    ]


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray, female: np.ndarray, melody_tamed: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)
    melody = pad_or_trim(melody_tamed, length)
    female_up = limiter(female * float(amp_db(1.0)), -4.0)
    throw, throw_moves = endpoint_throw(male, sr, length)

    vocal_ref = male * float(amp_db(0.0)) + female_up * float(amp_db(-5.0))
    inst_pocket = sidechain_duck_full(inst, vocal_ref, sr, amount_db=0.74, release_ms=128, threshold_percentile=60)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 250, 520, 0.72, 58)
    inst_pocket = V15.band_duck(inst_pocket, male, sr, 1500, 4100, 1.05, 60)
    inst_pocket, inst_edge = dynamic_band_tame(inst_pocket, sr, 2600, 5200, 0.42, 76, 75)
    inst_pocket, inst_fizz = dynamic_band_tame(inst_pocket, sr, 8200, 12800, 0.65, 70, 60)
    inst_pocket = ms_width(inst_pocket, 0.15)

    mix = MO.safe_sum(
        [
            (inst_pocket, -1.12),
            (melody, 0.70),
            (drums, -10.65),
            (bass, -10.10),
            (male, -2.05),
            (female_up, -2.95),
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
    mix = soft_clip(mix, drive_db=0.11, ceiling=0.89)
    mix = limiter(mix, -2.2)

    premaster = RENDERS / "0101_mix_v18_endpoint_throw_female_up_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v18_endpoint_throw_female_up.wav"
    final_mp3 = RENDERS / "0101_FINAL_v18_endpoint_throw_female_up_320.mp3"
    male_path = RENDERS / "processed_male_vocal_v18_with_endpoint_throw_source_stem.wav"
    female_path = RENDERS / "processed_female_layer_v18_side_plus1db_stem.wav"
    throw_path = RENDERS / "endpoint_throw_fx_v18_stem.wav"
    write_float_wav(premaster, sr, mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-10.4, target_tp=-1.2, target_lra=3.8)
    convert_mp3(final_wav, final_mp3)
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, female_up)
    write_float_wav(throw_path, sr, throw)
    return {
        "premaster": premaster,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "male_stem": male_path,
        "female_stem": female_path,
        "throw_stem": throw_path,
    }, [
        {"stage": "v18_mix_revision", "base": "v17 approved", "female_gain_change_db": 1.0, "master_target_lufs": -10.4, "not_pushed_to_minus_6": True},
        {"stage": "v18_instrumental_pocket_kept_from_v17", "full_duck_db": 0.74, "lowmid_duck_db": 0.72, "presence_duck_db": 1.05},
        {"stage": "v18_instrumental_edge_tame", **inst_edge},
        {"stage": "v18_instrumental_fizz_tame", **inst_fizz},
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
        rpp_track("V17_REFERENCE muted", V17_RENDERS / "0101_FINAL_v17_vocal_pocket_synth_tame.wav", length, 1, True, False),
        rpp_track("MALE_V18_SOURCE muted", paths["male_stem"], length, 2, True, False),
        rpp_track("FEMALE_V18_SIDE_PLUS1DB muted", paths["female_stem"], length, 3, True, False),
        rpp_track("ENDPOINT_THROW_FX muted", paths["throw_stem"], length, 4, True, False),
        rpp_track("V18_FINAL_ACTIVE", paths["final_wav"], length, 5, False, True),
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v18. Based on approved v17. Female side layer +1 dB. Main vocal endpoint-only delay/reverb throw; no global vocal space.
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
        audio_metrics(V17_RENDERS / "0101_FINAL_v17_vocal_pocket_synth_tame.wav", "v17_reference"),
        audio_metrics(paths["final_wav"], "v18_final_wav"),
        audio_metrics(paths["final_mp3"], "v18_final_mp3"),
        audio_metrics(paths["female_stem"], "v18_female_plus1db_stem"),
        audio_metrics(paths["throw_stem"], "v18_endpoint_throw_fx_stem"),
    ]
    write_csv(REPORTS / "v18_metrics.csv", metrics)
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
    (REPORTS / "v18_mix_qc_report.md").write_text(
        "\n".join(
            [
                "# v18 Mix QC Report",
                "",
                "- Started from approved v17.",
                "- Female side layer raised by +1 dB.",
                "- Main vocal endpoint/focus-point delay and reverb throw added only on phrase endings.",
                "- No global vocal reverb/delay was added.",
                "- Master was not pushed toward -6 LUFS; it stays near the v17 loudness range.",
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
        paths["throw_stem"],
        RPP,
        REPORTS / "v18_mix_qc_report.md",
        REPORTS / "v18_metrics.csv",
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
    male_sr, male, _ = read_wav(V17_RENDERS / "processed_male_vocal_v17_raw_core_plus1db_stem.wav")
    female_sr, female, _ = read_wav(V17_RENDERS / "processed_female_layer_v17_side_support_stem.wav")
    mel_sr, melody_tamed, _ = read_wav(V17_RENDERS / "processed_melody_synth_v17_tamed_stem.wav")
    if len({sr, male_sr, female_sr, mel_sr}) != 1:
        raise RuntimeError("sample-rate mismatch")
    length = max(len(audio["male_raw"]), len(male), len(female), len(melody_tamed))
    audio = {name: pad_or_trim(y, length) for name, y in audio.items()}
    male = pad_or_trim(male, length)
    female = pad_or_trim(female, length)
    melody_tamed = pad_or_trim(melody_tamed, length)
    paths, moves = render(sr, audio, male, female, melody_tamed)
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
