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
    normalize_to_rms,
    pan_stereo,
    read_wav,
    reverb_send,
    rms,
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

SLUG = "0101_v11_vocal_front_reference_rerender"
BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
V10_RENDERS = ROOT / "renders" / "0101_female_candidate_v10_qc_support"
WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_V11_VOCAL_FRONT_PROJECT.rpp"
BPM = 135


def ensure_dirs() -> None:
    for directory in (WORK, PROCESSED, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return MO.pad_or_trim(y, length)


def safe_normalize(y: np.ndarray, target_db: float) -> np.ndarray:
    if rms(y) < 1e-10:
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
        sr, y, _ = read_wav(path)
        sample_rates.add(sr)
        audio[name] = y
    if sample_rates != {48000}:
        raise RuntimeError(f"Expected 48 kHz sources, got {sorted(sample_rates)}")
    length = max(len(y) for y in audio.values())
    return 48000, {name: pad_or_trim(y, length) for name, y in audio.items()}


def body_restore_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    body = bandpass(vocal, sr, 135, 520, 3)
    body = compressor(body, sr, threshold_db=-33.0, ratio=2.7, smooth_ms=95, makeup_db=1.3)
    body = saturate(body, drive_db=1.7, mix=0.10)
    body, mud = dynamic_band_tame(body, sr, 240, 420, 1.15, 73, 130)
    body = biquad_peaking(body, sr, 190, 0.60, 0.95)
    body = biquad_peaking(body, sr, 330, -0.35, 1.15)
    body = safe_normalize(body, -24.0)
    return body.astype(np.float32), {"stage": "male_body_restore_parallel", "return_gain_db": -7.2, "mud_control": mud}


def clear_presence_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    presence = bandpass(vocal, sr, 1250, 4300, 3)
    presence = compressor(presence, sr, threshold_db=-34.0, ratio=3.4, smooth_ms=34, makeup_db=1.0)
    presence = vocal_harmonic_density(presence, sr, drive_db=1.7, wet=0.10)
    presence, edge = dynamic_band_tame(presence, sr, 3300, 5600, 1.9, 69, 52)
    presence, fizz = dynamic_band_tame(presence, sr, 5600, 11200, 3.2, 62, 44)
    presence = biquad_peaking(presence, sr, 2600, 0.75, 0.90)
    presence = biquad_shelf(presence, sr, 9000, -0.75, True)
    presence = safe_normalize(presence, -26.0)
    return presence.astype(np.float32), {"stage": "male_clear_presence_parallel", "return_gain_db": -8.8, "edge_control": edge, "fizz_control": fizz}


def process_male_front(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = MO.edge_fade(raw, sr, 32.0)
    out = butter_filter(out, sr, "highpass", 82, 3)
    moves.append({"stage": "v11_highpass_lower_to_keep_body", "hz": 82})
    out, beep = MO.suppress_beep_artifacts(out, sr, "v11_male_front", strength=0.96)
    out, sip = MO.suppress_sip_breaths(out, sr, "v11_male_front_pre")
    moves.extend([beep, sip])
    out, denoise = MO.spectral_denoise_vocal(
        out,
        sr,
        "v11_male_front",
        reduction=0.47,
        high_reduction=0.76,
        floor=0.58,
        high_floor=0.36,
    )
    moves.append(denoise)
    for low, high, cut, pct, smooth, name in [
        (220, 390, 1.25, 69, 145, "mud_without_thinning"),
        (690, 980, 1.65, 64, 115, "nasal_plastic_ring"),
        (980, 1360, 1.45, 66, 110, "formant_honk"),
        (2800, 4300, 1.45, 65, 75, "hard_attack"),
        (5200, 8500, 3.9, 58, 50, "sibilance_hash"),
        (8500, 13200, 3.4, 60, 44, "ai_fizz_noise"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"v11_dynamic_eq_{name}", **stats})
    out = saturate(out, drive_db=1.25, mix=0.08)
    out = compressor(out, sr, threshold_db=-25.0, ratio=2.15, smooth_ms=72, makeup_db=0.3)
    body, body_stats = body_restore_layer(out, sr)
    presence, presence_stats = clear_presence_layer(out, sr)
    out = out * float(amp_db(0.25)) + body * float(amp_db(-7.2)) + presence * float(amp_db(-8.8))
    moves.extend([body_stats, presence_stats])
    out, post_edge = dynamic_band_tame(out, sr, 3000, 5900, 1.25, 72, 62)
    out, post_air = dynamic_band_tame(out, sr, 6200, 12400, 2.8, 64, 48)
    moves.extend([{"stage": "v11_post_parallel_edge_control", **post_edge}, {"stage": "v11_post_parallel_air_noise_control", **post_air}])
    out = biquad_peaking(out, sr, 185, 0.30, 0.85)
    out = biquad_peaking(out, sr, 2850, 0.40, 0.9)
    out = biquad_shelf(out, sr, 10800, -0.25, True)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-21.1, max_cut_db=-6.8, max_boost_db=1.15, label="v11_male_front")
    moves.append(ride)
    out = safe_normalize(out, -19.25)
    out = limiter(MO.edge_fade(out, sr, 20.0), -1.8)
    moves.append({"stage": "v11_final_male_gain", "target_rms_dbfs": -19.25, "intent": "front, thicker, clearer male lead"})
    return out.astype(np.float32), moves


def make_reverb_behind(male: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    verb = reverb_send(male, sr, decay_s=0.54, wet_db=-30.0, predelay_ms=38, hp_hz=520, lp_hz=6400, seed=411)
    delay = (
        pan_stereo(delay_samples(male, int(sr * 0.235)), -0.38)
        + pan_stereo(delay_samples(male, int(sr * 0.355)), 0.38)
    ) * float(amp_db(-31.0))
    send = verb + delay
    send = sidechain_duck_full(send, male, sr, amount_db=4.8, release_ms=210, threshold_percentile=58)
    send, tame = dynamic_band_tame(send.astype(np.float32), sr, 4800, 9800, 2.4, 64, 55)
    return send.astype(np.float32), {
        "stage": "vocal_space_behind_only",
        "reverb_wet_db": -30.0,
        "delay_gain_db": -31.0,
        "duck_db": 4.8,
        "tame": tame,
    }


def render(sr: int, audio: dict[str, np.ndarray], male: np.ndarray) -> tuple[dict[str, Path], list[dict[str, object]]]:
    length = len(male)
    inst = pad_or_trim(audio["instrumental"], length)
    melody = pad_or_trim(audio["melody"], length)
    female = pad_or_trim(audio["female_layer"], length)
    drums = pad_or_trim(audio["drums"], length)
    bass = pad_or_trim(audio["bass"], length)

    inst_pocket = sidechain_duck_full(inst, male, sr, amount_db=0.70, release_ms=145, threshold_percentile=60)
    melody_pocket = sidechain_duck_full(melody, male, sr, amount_db=0.22, release_ms=130, threshold_percentile=66)
    female_tucked = sidechain_duck_full(female, male, sr, amount_db=5.2, release_ms=135, threshold_percentile=56)
    female_tucked, female_tame = dynamic_band_tame(female_tucked.astype(np.float32), sr, 5200, 11500, 3.8, 58, 45)
    vocal_space, space_stats = make_reverb_behind(male, sr)

    direct_mix = MO.safe_sum(
        [
            (inst_pocket, -1.00),
            (melody_pocket, 1.35),
            (drums, -10.2),
            (bass, -10.0),
            (male, -2.15),
            (female_tucked, -8.2),
            (vocal_space, 0.0),
        ],
        length,
        -1.7,
    )
    direct_mix, mix_res = MO.full_mix_resonance_polish(MO.edge_fade(direct_mix, sr, 24.0), sr)
    direct_mix = biquad_peaking(direct_mix, sr, 2300, 0.15, 0.9)
    direct_mix = biquad_shelf(direct_mix, sr, 11200, -0.08, True)
    direct_mix = stable_master_tone(direct_mix, sr)
    direct_mix = compressor(direct_mix, sr, threshold_db=-12.2, ratio=1.06, smooth_ms=280, makeup_db=0.0)
    direct_mix = soft_clip(direct_mix, drive_db=0.24, ceiling=0.88)
    direct_mix = limiter(direct_mix, -2.2)

    premaster = RENDERS / "0101_mix_v11_vocal_front_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_v11_vocal_front.wav"
    final_mp3 = RENDERS / "0101_FINAL_v11_vocal_front_320.mp3"
    write_float_wav(premaster, sr, direct_mix)
    ffmpeg_loudnorm(premaster, final_wav, target_lufs=-11.4, target_tp=-1.25, target_lra=4.0)
    convert_mp3(final_wav, final_mp3)

    male_path = RENDERS / "processed_male_vocal_v11_front_stem.wav"
    female_path = RENDERS / "processed_female_qc_support_v11_tucked_stem.wav"
    inst_path = RENDERS / "processed_instrumental_v11_pocket_stem.wav"
    write_float_wav(male_path, sr, male)
    write_float_wav(female_path, sr, limiter(female_tucked, -4.0))
    write_float_wav(inst_path, sr, limiter(inst_pocket, -1.8))
    moves = [
        {"stage": "mix_gain_revision", "male_gain_db": -2.15, "v10_male_gain_db": -5.8, "female_gain_db": -8.2, "instrumental_gain_db": -1.0, "melody_gain_db": 1.35},
        {"stage": "instrumental_vocal_pocket", "duck_db": 0.70},
        {"stage": "melody_light_pocket", "duck_db": 0.22},
        {"stage": "female_layer_tucked", "duck_db": 5.2, "high_tame": female_tame},
        *mix_res,
        space_stats,
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
      FADEIN 1 0.012 0 1 0 0 0
      FADEOUT 1 0.012 0 1 0 0 0
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
        rpp_track("ORIGINAL_V10_MAIN muted", V10_RENDERS / "0101_FINAL_female_qc_support.wav", length, 1, True, False),
        rpp_track("MALE_RAW muted", BASE_STEMS / "0101_vocal_raw.wav", length, 2, True, False),
        rpp_track("MALE_VOCAL_V11_FRONT muted", paths["male_stem"], length, 3, True, False),
        rpp_track("FEMALE_SUPPORT_V11_TUCKED muted", paths["female_stem"], length, 4, True, False),
        rpp_track("INSTRUMENTAL_V11_POCKET muted", paths["instrumental_stem"], length, 5, True, False),
        rpp_track("MIX_BUS V11 VOCAL FRONT ACTIVE", paths["final_wav"], length, 6, False, True),
        rpp_track("MASTER_MP3_MONITOR muted", paths["final_mp3"], length, 7, True, False),
    ]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip([0, 14.2, 42.7, 72.0, 101.3, length], ["intro", "verse", "hook", "section2", "outro", "end"]), start=1)
    ]
    RPP.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 v11 vocal front revision. Male direct vocal is forward/thicker; vocal reverb and delay are tucked behind.
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
        audio_metrics(paths["final_wav"], "v11_final_wav"),
        audio_metrics(paths["final_mp3"], "v11_final_mp3"),
        audio_metrics(paths["male_stem"], "v11_processed_male_front"),
        audio_metrics(V10_RENDERS / "0101_FINAL_female_qc_support.wav", "v10_previous_main"),
    ]
    write_csv(REPORTS / "final_render_metrics.csv", metrics)
    decisions = {"male_vocal": male_moves, "mix": mix_moves, "target": {"integrated_lufs": -11.4, "true_peak_dbfs": -1.25}}
    (REPORTS / "processing_decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        {
            "version": row["label"],
            "integrated_lufs": row.get("integrated_lufs"),
            "true_peak_dbfs": row.get("true_peak_dbfs"),
            "rms_dbfs": row.get("rms_dbfs"),
            "presence_pct": row.get("presence_1500_5000_pct"),
            "sibilance_pct": row.get("sibilance_5000_10000_pct"),
        }
        for row in metrics
    ]
    (REPORTS / "final_qc_report.md").write_text(
        "\n".join(
            [
                "# Final QC Report",
                "",
                markdown_table(summary, ["version", "integrated_lufs", "true_peak_dbfs", "rms_dbfs", "presence_pct", "sibilance_pct"]),
                "",
                "## Revision Notes",
                "",
                "- User complaint addressed: vocal too small/buried, male vocal too thin, noise too strong, reverb too forward.",
                "- Male direct vocal is lifted about 3.6 dB versus v10 mix gain and rebuilt with body/presence parallel layers.",
                "- Reverb and delay are behind-only: darker, lower, predelayed, and sidechain-ducked from the male lead.",
                "- Female support remains tucked and ducked so it does not mask the male lead.",
                "- Instrumental gets extra vocal pocketing while the sad melody remains present.",
                "- Master target remains true-peak safe and not over-bright.",
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
                "- Started from the timing-approved v10 female QC support render, not from a new Suno generation.",
                "- Male vocal was reprocessed from raw `0101_vocal_raw.wav` for more body and front clarity.",
                "- Added low-mid body restore and controlled presence restore; high fizz and sibilance were dynamically reduced.",
                "- Vocal FX is treated as rear ambience only: low level, darker bandwidth, predelay, and sidechain duck.",
                "- Female support layer was retained but heavily tucked/ducked.",
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
    male, male_moves = process_male_front(audio["male_raw"], sr)
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
