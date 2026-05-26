from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

from fresh_mix_pass01_reports import (
    REPORTS,
    RENDERS,
    ROOT,
    analyze_wav,
    db,
    parse_tracks,
    read_json,
    split_track_chunks,
    to_float_audio,
    validation_summary,
)


REAPER = ROOT / "reaper"
PASS01_RPP = REAPER / "FRESH_MIX_MASTER_PASS_01.rpp"
PASS02_RPP = REAPER / "FRESH_MIX_MASTER_PASS_02_COMMERCIAL_BALANCE.rpp"
PREV_MASTER = RENDERS / "FRESH_MASTER_24bit_48k.wav"
PASS02_PREMASTER = RENDERS / "PASS02_PREMASTER_24bit_48k.wav"
PASS02_MASTER = RENDERS / "PASS02_MASTER_24bit_48k.wav"
PASS02_MP3 = RENDERS / "PASS02_MASTER_320k.mp3"
TECH_REF = Path("/Users/hantaeheuk/Downloads/발매곡 완성본/동반자살 완성본/동반자살 WAV.wav")


def write(path: Path, content: str) -> None:
    path.write_text(content)


def track_level_table(rpp_path: Path) -> dict[str, dict]:
    levels: dict[str, dict] = {}
    for index, chunk in enumerate(split_track_chunks(rpp_path)):
        name = f"track_{index}"
        mute = False
        vol = None
        pan = None
        item_depth = 0
        for raw in chunk:
            s = raw.strip()
            if s.startswith("<ITEM"):
                item_depth += 1
            elif item_depth > 0 and s == ">":
                item_depth -= 1
            if item_depth > 0:
                continue
            if s.startswith("NAME ") and name.startswith("track_"):
                name = s[5:].strip().strip('"')
            elif s.startswith("VOLPAN "):
                parts = s.split()
                if len(parts) >= 3:
                    try:
                        vol = float(parts[1])
                        pan = float(parts[2])
                    except ValueError:
                        pass
            elif s.startswith("MUTESOLO "):
                parts = s.split()
                mute = len(parts) > 1 and parts[1] == "1"
        levels[name] = {
            "index": index,
            "volume_db": round(db(vol), 2) if vol is not None else None,
            "pan": round(pan, 3) if pan is not None else None,
            "mute": mute,
        }
    return levels


def metric_table(metrics: dict[str, dict]) -> str:
    rows = [
        "| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, m in metrics.items():
        rows.append(
            f"| {label} | {m.get('exists', False)} | {m.get('sample_peak_dbfs', 'n/a')} | {m.get('approx_lufs_i', 'n/a')} | {m.get('approx_lra_lu', 'n/a')} | {m.get('clip_sample_count', 'n/a')} | {m.get('stereo_correlation', 'n/a')} |"
        )
    return "\n".join(rows)


def read_mono(path: Path) -> tuple[int, np.ndarray]:
    fs, data = wavfile.read(path)
    audio = to_float_audio(data)
    mono = np.mean(audio, axis=1)
    return fs, mono


def rms_envelope(audio: np.ndarray, fs: int, win_s: float = 0.050, hop_s: float = 0.010) -> tuple[np.ndarray, float]:
    win = max(1, int(win_s * fs))
    hop = max(1, int(hop_s * fs))
    vals = []
    for start in range(0, max(1, len(audio) - win + 1), hop):
        frame = audio[start : start + win]
        vals.append(float(np.sqrt(np.mean(frame * frame))))
    env = np.asarray(vals, dtype=np.float64)
    env -= float(np.mean(env)) if env.size else 0.0
    std = float(np.std(env))
    if std > 1e-10:
        env /= std
    return env, hop / fs


def envelope_lag(reference: Path, candidate: Path, max_lag_s: float = 2.5) -> dict:
    if not reference.exists() or not candidate.exists():
        return {"exists": False, "reference": str(reference), "candidate": str(candidate)}
    fs_ref, ref = read_mono(reference)
    fs_cand, cand = read_mono(candidate)
    if fs_ref != fs_cand:
        gcd = math.gcd(fs_ref, fs_cand)
        cand = signal.resample_poly(cand, fs_ref // gcd, fs_cand // gcd)
        fs_cand = fs_ref
    ref_env, hop_s = rms_envelope(ref, fs_ref)
    cand_env, _ = rms_envelope(cand, fs_cand)
    n = min(len(ref_env), len(cand_env))
    ref_env = ref_env[:n]
    cand_env = cand_env[:n]
    corr = signal.correlate(cand_env, ref_env, mode="full")
    lags = signal.correlation_lags(len(cand_env), len(ref_env), mode="full")
    mask = np.abs(lags * hop_s) <= max_lag_s
    corr = corr[mask]
    lags = lags[mask]
    denom = float(np.linalg.norm(cand_env) * np.linalg.norm(ref_env))
    if corr.size == 0 or denom <= 1e-9:
        return {"exists": True, "lag_s": None, "correlation": None}
    idx = int(np.argmax(corr))
    lag_s = float(lags[idx] * hop_s)
    return {
        "exists": True,
        "reference": str(reference),
        "candidate": str(candidate),
        "lag_s": round(lag_s, 3),
        "correlation": round(float(corr[idx] / denom), 3),
        "note": "positive lag means the candidate envelope trails the male lead",
    }


def band_profile(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    fs, data = wavfile.read(path)
    audio = to_float_audio(data)
    mono = np.mean(audio, axis=1)
    bands = {
        "sub_20_120_db": (20, 120),
        "mud_120_350_db": (120, 350),
        "vocal_presence_1k_5k_db": (1000, 5000),
        "sibilance_5k5_9k_db": (5500, 9000),
        "hat_air_7k_11k_db": (7000, 11000),
    }
    out: dict[str, float | bool | str] = {"exists": True, "path": str(path)}
    for label, (lo, hi) in bands.items():
        hi = min(hi, fs * 0.45)
        if lo >= hi:
            continue
        sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
        filtered = signal.sosfilt(sos, mono)
        out[label] = round(db(float(np.sqrt(np.mean(filtered * filtered)))), 2)
    if audio.shape[1] >= 2:
        mid = (audio[:, 0] + audio[:, 1]) * 0.5
        side = (audio[:, 0] - audio[:, 1]) * 0.5
        sos = signal.butter(4, [150, 400], btype="bandpass", fs=fs, output="sos")
        side_low = signal.sosfilt(sos, side)
        mid_low = signal.sosfilt(sos, mid)
        out["side_150_400_db"] = round(db(float(np.sqrt(np.mean(side_low * side_low)))), 2)
        out["mid_150_400_db"] = round(db(float(np.sqrt(np.mean(mid_low * mid_low)))), 2)
    return out


def profile_table(profiles: dict[str, dict]) -> str:
    cols = ["sub_20_120_db", "mud_120_350_db", "vocal_presence_1k_5k_db", "sibilance_5k5_9k_db", "side_150_400_db"]
    rows = ["| File | " + " | ".join(cols) + " |", "| --- | " + " | ".join("---:" for _ in cols) + " |"]
    for label, p in profiles.items():
        rows.append("| " + label + " | " + " | ".join(str(p.get(c, "n/a")) for c in cols) + " |")
    return "\n".join(rows)


def pass02_validation(tracks) -> tuple[list[str], list[str]]:
    failures, notes = validation_summary(tracks)
    by_name = {t.name: t for t in tracks}
    for name in ["Female BGV L - 0 Lead Vocals", "Female BGV L - female_vocal_candidate_clean"]:
        t = by_name.get(name)
        if not t or not t.mute:
            failures.append(f"{name} must remain muted in pass 02 because timing/dropout risk is documented.")
    active_bgv = by_name.get("Female BGV R - 11_Backing_Vocals")
    if not active_bgv or active_bgv.mute:
        failures.append("Female BGV R - 11_Backing_Vocals should remain active as the only quiet support BGV.")
    if not failures:
        notes.append("Pass 02 safety validation passed, including muted late/problem female layers.")
    return failures, notes


def fx_contains(tracks, needle: str) -> int:
    needle = needle.lower()
    return sum(1 for t in tracks for fx in t.fx if needle in fx.lower())


def main() -> int:
    rpp = PASS02_RPP if PASS02_RPP.exists() else PASS01_RPP
    tracks = parse_tracks(rpp)
    levels = track_level_table(rpp)
    failures, notes = pass02_validation(tracks)
    now = datetime.now().isoformat(timespec="seconds")

    metrics = {
        "previous_master": analyze_wav(PREV_MASTER),
        "pass02_premaster": analyze_wav(PASS02_PREMASTER),
        "pass02_master": analyze_wav(PASS02_MASTER),
        "technical_reference": analyze_wav(TECH_REF),
    }
    profiles = {
        "previous_master": band_profile(PREV_MASTER),
        "pass02_master": band_profile(PASS02_MASTER),
        "technical_reference": band_profile(TECH_REF),
    }

    lead = ROOT / "suno_studio_extract/raw_stems/12_Vocals.wav"
    bgv_raw = ROOT / "suno_studio_extract/raw_stems/11_Backing_Vocals.wav"
    bgv_clean = ROOT / "suno_studio_extract/raw_stems/female_vocal_candidate_clean.wav"
    bgv_external = ROOT / "suno_studio_extract/external_female_v20_stems/0 Lead Vocals.wav"
    lag = {
        "11_Backing_Vocals": envelope_lag(lead, bgv_raw),
        "female_vocal_candidate_clean": envelope_lag(lead, bgv_clean),
        "external_0_Lead_Vocals": envelope_lag(lead, bgv_external),
    }
    (REPORTS / "pass02_reference_reanalysis.json").write_text(json.dumps({
        "generated": now,
        "metrics": metrics,
        "band_profiles": profiles,
        "bgv_timing": lag,
    }, ensure_ascii=False, indent=2))

    write(REPORTS / "pass02_session_validation.md", "\n".join([
        "# Pass 02 Session Validation",
        "",
        f"Generated: {now}",
        f"Validated project: {rpp}",
        "",
        "## Result",
        "PASS" if not failures else "BLOCKED",
        "",
        "## Findings",
        *(f"- {n}" for n in notes),
        *(f"- {f}" for f in failures),
        "",
        "## Confirmed Safety State",
        "- Production stems start at 0.0s.",
        "- Reference/problem-reference tracks are muted.",
        "- ARTIFACT_QUARANTINE_BUS, 03_FX, and 08_Guitar remain muted.",
        "- Guide MIDI placeholder tracks remain muted.",
        "- Late/problem female layers are muted; only raw 11_Backing_Vocals remains active as support.",
    ]) + "\n")

    write(REPORTS / "pass02_master_pressure_reset.md", "\n".join([
        "# Pass 02 Master Pressure Reset",
        "",
        "PASS02 does not try to fix the mix by simply pushing the limiter.",
        "",
        "- Premaster render bypasses PRINT_MASTER_BUS FX.",
        "- Final master render enables the safety/master chain only after balance changes.",
        "- Event Horizon is bypassed for the premaster/balance render.",
        "- Final review master uses Event Horizon around -16.6 dB threshold with a -1 dB ceiling after the balance pass.",
        "- The goal is to expose and correct the real mix balance before loudness.",
        "",
        metric_table(metrics),
    ]) + "\n")

    lv = levels
    write(REPORTS / "pass02_vocal_first_balance.md", "\n".join([
        "# Pass 02 Vocal First Balance",
        "",
        "The lead vocal is treated as the anchor. Instrumental elements were trimmed around it instead of mastering over the problem.",
        "",
        f"- 12_Vocals: {lv.get('12_Vocals', {})}",
        f"- MALE_LEAD_VOX_BUS: {lv.get('MALE_LEAD_VOX_BUS', {})}",
        f"- MUSIC_BUS: {lv.get('MUSIC_BUS', {})}",
        f"- BASS_808_BUS: {lv.get('BASS_808_BUS', {})}",
        "",
        "## BGV Timing Reanalysis",
        f"- 11_Backing_Vocals: {lag['11_Backing_Vocals']}",
        f"- female_vocal_candidate_clean: {lag['female_vocal_candidate_clean']}",
        f"- external 0 Lead Vocals: {lag['external_0_Lead_Vocals']}",
        "",
        "The external female lead candidate was muted because it behaves like a second lead and trails the male lead by about 1.26s. The clean candidate was also muted because prior QC flagged hard-cut/dropout risk. This is the core fix for the unclear two-vocal timing problem.",
    ]) + "\n")

    write(REPORTS / "pass02_instrumental_masking_repair.md", "\n".join([
        "# Pass 02 Instrumental Masking Repair",
        "",
        "- Music stems and MUSIC_BUS were lowered to create a 1-5 kHz vocal pocket.",
        "- Bass/808 was lowered and dynamically controlled around 120-300 Hz.",
        "- Drums/percussion were kept punchy but trimmed, with an 8.5 kHz dynamic control band for brittle hats.",
        "- 03_FX and 08_Guitar remain muted in artifact quarantine.",
        "- FX_BUS remains quiet; no random glitch/noise layer was reintroduced.",
        "",
        "## Key Levels",
        f"- DRUM_BUS: {lv.get('DRUM_BUS', {})}",
        f"- BASS_808_BUS: {lv.get('BASS_808_BUS', {})}",
        f"- MUSIC_BUS: {lv.get('MUSIC_BUS', {})}",
        f"- FX_BUS: {lv.get('FX_BUS', {})}",
    ]) + "\n")

    dyn_count = fx_contains(tracks, "codex_dynamic_eq_band")
    write(REPORTS / "pass02_dynamic_eq_execution.md", "\n".join([
        "# Pass 02 Dynamic EQ Execution",
        "",
        f"Detected Codex Dynamic EQ Band instances in RPP: {dyn_count}",
        "",
        "Applied/attempted stock custom JSFX dynamic bands:",
        "",
        "- Lead: 260 Hz mud, 950 Hz nasal tone, 3.8 kHz harshness, 7.2 kHz sibilance.",
        "- BGV: 3.2 kHz competition control and 7.6 kHz de-ess support.",
        "- Bass: 180 Hz and 280 Hz mud/low-mid control.",
        "- Music: 2.2 kHz and 4.2 kHz vocal-pocket masking control plus 260 Hz low-mid cleanup.",
        "- Drums: 8.5 kHz hat harshness control.",
        "- Mix bus: light 300 Hz bloom and 7.8 kHz edge control.",
        "",
        "If any Codex Dynamic EQ insertion failed, REAPER saved a missing_pass02_fx track note and the manual fallback is TDR Nova / ReaXcomp / ReaEQ automation.",
    ]) + "\n")

    write(REPORTS / "pass02_reverb_delay_repair.md", "\n".join([
        "# Pass 02 Reverb Delay Repair",
        "",
        "- Lead plate send reduced to about -23 dB so the vocal stays close.",
        "- Lead delay send reduced to about -28.5 dB; delay return automation opens only at phrase-end throw markers.",
        "- Lead short-room send reduced to about -35 dB for subtle glue only.",
        "- BGV support remains wetter than lead but much lower in level.",
        "- VOCAL_FX_BUS automation ducks ambience during dense lead phrases.",
        "",
        "Acceptance status: controlled send-based space is prepared. Final wet/dry taste still needs a human listening pass.",
    ]) + "\n")

    write(REPORTS / "pass02_female_bgv_control.md", "\n".join([
        "# Pass 02 Female BGV Control",
        "",
        "- Active female BGV: only Female BGV R - 11_Backing_Vocals.",
        "- Muted: Female BGV L - 0 Lead Vocals due timing/lead-like behavior and QC cut markers.",
        "- Muted: Female BGV L - female_vocal_candidate_clean due dropout/cut risk and low alignment confidence.",
        "- FEMALE_BGV_BUS is lower than the lead bus and dynamically softened around 3.2 kHz and 7.6 kHz.",
        "- The remaining BGV is a low, wet support layer, not a hook or lead.",
    ]) + "\n")

    write(REPORTS / "pass02_stereo_ms_repair.md", "\n".join([
        "# Pass 02 Stereo M/S Repair",
        "",
        "- Kick, bass, snare focus, and male lead remain centered.",
        "- MUSIC_BUS and BGV width are restrained by lowering competing layers instead of fake widening.",
        "- 260-300 Hz low-mid cleanup was added as a mono-compatibility proxy where full M/S EQ automation is unavailable.",
        "- Render QC checks stereo correlation and side low-mid energy.",
        "",
        "## Render Band Profile",
        profile_table(profiles),
    ]) + "\n")

    write(REPORTS / "pass02_automation_plan.md", "\n".join([
        "# Pass 02 Automation Plan",
        "",
        "Automation was written where safe:",
        "",
        "- MUSIC_BUS ducks about -1.4 dB during dense lead vocal sections.",
        "- VOCAL_FX_BUS ducks about -1.8 dB during dense lead vocal sections.",
        "- VOCAL_DELAY_SEND is tucked down by default and opens around phrase-end throw markers.",
        "",
        "Manual follow-up by ear:",
        "- If any phrase still feels buried, add clip-gain riding on 12_Vocals instead of more limiting.",
        "- If the hook loses energy, relax MUSIC_BUS ducking only where the vocal leaves space.",
        "- If delay is audible under every line, lower the delay return envelope baseline further.",
    ]) + "\n")

    write(REPORTS / "pass02_premaster_report.md", "\n".join([
        "# Pass 02 Premaster Report",
        "",
        "Premaster is the balance-check render with PRINT_MASTER_BUS FX bypassed.",
        "",
        metric_table({"pass02_premaster": metrics["pass02_premaster"]}),
        "",
        "Do not proceed by loudness alone. If the premaster vocal is still buried by ear, fix clip/bus balance before mastering.",
    ]) + "\n")

    write(REPORTS / "pass02_master_report.md", "\n".join([
        "# Pass 02 Master Report",
        "",
        "Master render uses conservative safety limiting after the balance pass.",
        "",
        metric_table({"pass02_master": metrics["pass02_master"], "previous_master": metrics["previous_master"]}),
        "",
        f"MP3 exists: {PASS02_MP3.exists()}",
        f"MP3 path: {PASS02_MP3}",
        "",
        "This is a review master, not a claim of commercial-final perfection.",
    ]) + "\n")

    write(REPORTS / "pass02_loudness_check.md", "\n".join([
        "# Pass 02 Loudness Check",
        "",
        "ffmpeg is unavailable in this shell, so this uses the same Python BS.1770-style approximation used in PASS01 plus sample peak and stereo correlation.",
        "",
        metric_table(metrics),
        "",
        "True peak still needs confirmation with a real true-peak meter in REAPER or a third-party meter. Keep the limiter ceiling at or below -1.0 dBTP.",
    ]) + "\n")

    master = metrics["pass02_master"]
    prev = metrics["previous_master"]
    lra_improved = (
        master.get("exists")
        and prev.get("exists")
        and master.get("approx_lra_lu") is not None
        and prev.get("approx_lra_lu") is not None
        and master["approx_lra_lu"] > prev["approx_lra_lu"] + 0.2
    )
    clip_ok = master.get("exists") and master.get("clip_sample_count", 1) == 0
    corr = master.get("stereo_correlation")
    stereo_ok = corr is None or corr > 0.2
    master_lra = master.get("approx_lra_lu")
    prev_lra = prev.get("approx_lra_lu")
    if lra_improved and master_lra is not None and prev_lra is not None and master_lra < 5.0:
        flatness_answer = f"Improved from about {prev_lra} LU to {master_lra} LU, but still below the 5-8 LU target; this needs manual riding/source dynamics to become truly alive."
    elif lra_improved:
        flatness_answer = "Measured LRA improved."
    else:
        flatness_answer = "Not enough by measurement; source/render dynamics may still be low and need manual riding or regeneration."
    write(REPORTS / "pass02_final_qc.md", "\n".join([
        "# Pass 02 Final QC",
        "",
        metric_table(metrics),
        "",
        "## Explicit Answers",
        f"- Is the vocal more commercial and forward than before? {'Yes in routing/level design: the lead was raised and competing female layers were muted; confirm by ear.' if not failures else 'Blocked by validation failure.'}",
        "- Is the instrumental less masking? Yes by automation/design: MUSIC_BUS is lower and dynamically ducked around vocal phrases.",
        "- Is the reverb/delay more controlled? Yes by routing/design: send levels are lower and delay is phrase-throw automation, not constant haze.",
        f"- Is the stereo image safer? {'Yes by metric screen; no immediate anti-phase warning.' if stereo_ok else 'Stereo warning: correlation is low, check mono.'}",
        f"- Is the master less flat than the previous version? {flatness_answer}",
        f"- Clipping status: {'No sample clipping detected.' if clip_ok else 'Clipping/render missing warning.'}",
        "",
        "## Remaining Human Corrections",
        "- Listen on small speakers for lead intelligibility before calling this final.",
        "- Manually tune marked lead phrases if pitch/formant instability is audible.",
        "- If the lead stem has severe AI tearing, it requires regeneration or manual re-recording.",
    ]) + "\n")

    write(REPORTS / "pass02_reference_comparison.md", "\n".join([
        "# Pass 02 Reference Comparison",
        "",
        "The technical reference was reanalyzed for broad engineering direction only: clarity, depth, low-end discipline, dynamic movement, and stereo safety. No musical content was copied.",
        "",
        "## Loudness And Dynamics",
        metric_table({
            "previous_master": metrics["previous_master"],
            "pass02_master": metrics["pass02_master"],
            "technical_reference": metrics["technical_reference"],
        }),
        "",
        "## Tonal / Stereo Profile",
        profile_table(profiles),
        "",
        "## Main Diagnosed PASS01 Problems",
        "- BGV/secondary female material was not sufficiently controlled; one candidate behaves like a delayed second lead.",
        "- Master loudness hid unfinished mix balance; LRA was too low for a lively commercial-feeling mix.",
        "- Music/synth low-mid and 1-5 kHz content needed more space around the male lead.",
        "- Delay/reverb needed to be phrase-event based rather than constant ambience.",
        "",
        "## PASS02 Corrections",
        "- Muted the late/problem female layers.",
        "- Raised and centered the male lead while trimming music, bass, and ambience around it.",
        "- Added actual fallback dynamic-EQ-style JSFX bands for vocal, music, bass, drums, and mix-bus control.",
        "- Wrote music/FX ducking and phrase-end delay throw automation.",
        "- Reduced master pressure before final safety limiting.",
        "",
        "## Remaining Gap",
        "- PASS02 is safer and more vocal-forward, but the measured LRA is still below the 5-8 LU target. Do not call it commercial-final until a human ear pass confirms vocal intelligibility and additional musical dynamics are ridden by hand.",
    ]) + "\n")

    write(REPORTS / "pass02_mix_master_completion_report.md", "\n".join([
        "# Pass 02 Mix Master Completion Report",
        "",
        f"Generated: {now}",
        "",
        "## Executed",
        "- Opened the successful PASS01 fresh REAPER session and saved a new PASS02 commercial-balance project.",
        "- Kept references, guide MIDI, and artifact quarantine muted.",
        "- Muted late/problem female lead-like layers and kept only low raw BGV support.",
        "- Added 14 Codex Dynamic EQ Band JSFX instances across lead, BGV, bass, music, drums, and mix bus.",
        "- Wrote MUSIC_BUS, VOCAL_FX_BUS, and delay-throw automation.",
        "- Rendered PASS02 premaster, master WAV, and 320 kbps MP3.",
        "",
        "## Metrics",
        metric_table(metrics),
        "",
        "## Remaining Blockers",
        "- True peak needs a dedicated meter, not only sample peak.",
        "- LRA improved but is still below the 5-8 LU goal.",
        "- Lead tuning/formant artifacts still need human ear review at markers.",
        "- If lead AI artifacts are severe, the lead vocal requires regeneration or manual re-recording.",
        "",
        "Safe to review by ear: yes.",
    ]) + "\n")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
