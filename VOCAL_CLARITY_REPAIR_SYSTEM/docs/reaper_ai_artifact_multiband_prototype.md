# Reaper AI Artifact Multiband Prototype

This is a DAW prototype workflow for testing whether conservative dynamic multiband processing can reduce AI noise/artifacts without damaging source quality. It is not final plugin DSP.

Run the template script from REAPER:

```sh
VOCAL_CLARITY_REPAIR_SYSTEM/scripts/create_reaper_ai_artifact_multiband_prototype.lua
```

The script creates `reaper/ai_noise_multiband_prototype/AI_NOISE_MULTIBAND_PROTOTYPE.rpp` and a trace at `reports/ai_noise_multiband_prototype/reaper_multiband_prototype_trace.json`.

## Objective

Compare:
- Original dry signal
- Processed full chain
- Loudness-matched processed signal
- Residual: original minus processed
- Mid-only processing
- Side-only processing
- Broad multiband-only processing
- Surgical dynamic EQ-only processing
- ReaFIR micro suppression experiment
- Gate/expander-only cleanup
- 24/48/64-band dynamic suppressor candidate decisions

The question is not "how clean can it get?" The question is whether the chain preserves vocal presence, consonants, sibilance detail, transient attack, air, ambience, tone, and musical harmonics.

## Test Audio

Use at least:
- Clean vocal
- Vocal with broadband hiss
- Vocal with room tone or reverb tail
- Vocal with breath and consonants
- AI or source-separated vocal with metallic/watery/codec artifacts
- Acoustic guitar picking
- Drum loop with snare and hi-hat transients
- Full mix with centered vocal
- Stereo ambience-heavy material
- Optional room tone, hiss-only, artifact-tail, or silence/gap sections

Do not tune the chain on one file only. A chain that wins on one vocal but damages a clean vocal fails.

## Track Layout

| Track | Name | Role |
| ---: | --- | --- |
| 1 | Original Dry | Unprocessed source reference |
| 2 | Processed Full | Full prototype chain |
| 3 | Processed Matched | Level-matched processed comparison |
| 4 | Residual Monitor | Original minus Processed |
| 5 | Mid Process Bus | Conservative center-vocal path |
| 6 | Side Process Bus | Slightly stronger stereo artifact path |
| 7 | Broad Multiband Bus | ReaXcomp/TDR Nova broad-band test |
| 8 | Surgical Dynamic EQ Bus | Multi-instance TDR Nova-style notches |
| 9 | ReaFIR Micro Suppression Bus | Micro-band experiment |
| 10 | Gate/Expander Bus | Gaps-only cleanup |
| 11 | Print/Render A/B | Render/record versions |
| 12 | Notes/Markers | Settings, failures, decisions |
| 13 | 24-64 Band Suppressor Candidate | Design log and spectrum check only |

Solo these tracks for fast comparison. Keep residual muted until checking removed material.

## Routing

- Original feeds residual and experiment buses.
- Processed feeds residual with polarity inversion on the send where REAPER supports it.
- Processed Matched is for level trim only.
- Mid and Side buses use JS Mid/Side Encoder as a prototype helper; verify actual routing by ear before scoring.
- Print/Render A/B receives the matched processed path.
- The 24-64 Band Suppressor Candidate receives original audio for visual/spectral inspection only. It is not an active final suppressor in this patch.

Residual pass criteria: hiss, hum, rumble, non-musical chirps, metallic artifacts. Residual fail criteria: ghost vocal, S/T/CH consonants, vocal body, harmonics, guitar picking, snare attack, cymbal musical detail, or source reverb tail.

## Chain Templates

### Static Cleanup

Use ReaEQ only for fixed technical issues:
- High-pass 20-35 Hz, 12 or 18 dB/oct if needed
- 50/60 Hz hum notches, Q 20-50, -3 to -12 dB only when present
- Stable non-musical whistle notch, Q 10-30, -1 to -4 dB

Reject broad presence cuts, static de-airing, large mid scoops, or anything that makes clean vocal worse.

### Broad Dynamic Stabilization

Use ReaXcomp or TDR Nova-style broad dynamic bands:

| Band | Range | Target | Max GR |
| --- | --- | --- | --- |
| 1 | 20-120 Hz | Rumble/proximity | -1 to -4 dB |
| 2 | 120-350 Hz | Low-mid cloud | -1 to -3 dB |
| 3 | 350 Hz-1 kHz | Box/smear | -0.5 to -2 dB |
| 4 | 1-2.5 kHz | Nasal/AI mid | -0.5 to -1.5 dB |
| 5 | 2.5-5 kHz | Presence danger zone | -0.3 to -1 dB |
| 6 | 5-8 kHz | Consonant danger zone | -0.5 to -1.5 dB |
| 7 | 8-16 kHz | Hiss/air danger zone | -0.3 to -1.5 dB |

Ratio 1.1:1 to 1.5:1, attack 20-80 ms, release 100-300 ms, soft knee, makeup/auto gain off.

### TDR Nova Multi-Instance Layout

- Nova A: 80 Hz-1.2 kHz low/low-mid cleanup
- Nova B: 1.2-4 kHz mid/nasal/plastic cleanup
- Nova C: 3-8 kHz presence/consonant protection zone
- Nova D: 8-16 kHz air/hiss/fizz control
- Nova E: surgical artifact notches only

Do not make every band active all the time. If a band has no target, remove it.

### 24-64 Band Dynamic Suppressor Candidate

This is the next DSP candidate, not an active sound-changing feature in this prototype. It should be validated in REAPER before being ported.

| Mode | Band Count | Use | Default Status |
| --- | ---: | --- | --- |
| Preserve | 24 | Broad artifact-aware dynamic control | Default candidate |
| Balanced | 48 | More frequency resolution for confirmed artifacts | Test only |
| Surgical | 64 | Narrow birdies/metallic artifacts | Stress/special-case only |

Rules:
- Bands are log-spaced from roughly 80 Hz to 16 kHz, with optional technical bands below 80 Hz only for rumble/hum.
- Mid and Side are processed independently. Mid gets stricter vocal, consonant, transient, and harmonic guards; Side may allow slightly more reduction for stereo fizz or room artifacts.
- Each band has its own artifact score, gain smoother, maximum reduction cap, and keep/reduce/remove decision.
- 24 bands is the only acceptable preservation-first default. 48 or 64 bands are not defaults until residual monitoring proves they do not remove source.
- No post-EQ clarity compensation, exciter, high-shelf repair, or artificial air restoration is allowed.

### Artifact Score Detector

The suppressor should not react to level alone. A band only reduces when a clamped artifact score crosses threshold:

```text
artifact_score =
  narrow_tonal_peak
  + spectral_flatness_or_noise_excess
  + temporal_instability
  + high_frequency_fizz
  - vocal_presence_guard
  - transient_guard
  - harmonic_guard
  - residual_source_leak_penalty
```

Clamp the score to 0.0-1.0. Smooth it per band with attack/release. If the score is ambiguous, preserve the source.

### Guard Coupling

The existing vocal, transient, and harmonic guards should reduce suppression depth before the gain mask is applied:

| Guard | Protects | Suppressor effect |
| --- | --- | --- |
| Vocal guard | formants, vowels, centered voice | lowers mid-band max reduction |
| Transient guard | consonants, plucks, snare/hat attacks | slows or reduces gain reduction during attacks |
| Harmonic guard | musical partials and stable tone | rejects narrow cuts that follow musical pitch |
| Air guard | room tone, breath, natural high end | limits 8 kHz+ reduction unless residual is clean |

This must be a pre-mask safety limit, not a fake clarity post-process.

### Residual Monitor for Suppressor Validation

For every suppressor preset, monitor `Original - Processed`. If residual contains vocal syllables, S/T/CH consonants, stable harmonics, room tail, picking, snare attack, or musical air, the responsible band is reduced or removed. A cleaner but duller output fails.

### ReaFIR Micro Suppression

Use as an experiment only:
- FFT 1024 or 2048
- Ratio 1.05:1 to 1.3:1 if using compressor-style behavior
- Conservative threshold
- Avoid aggressive subtract mode unless a clean noise-only profile exists

Reject if it creates watery, phasey, dull, or transient-smearing texture.

### Gate/Expander

Use ReaGate only for gaps and tails:
- Attack 5-20 ms
- Hold 50-150 ms
- Release 150-400 ms
- Limited range/wet-dry if available

Never use the gate to solve noise under active singing.

## Prototype Presets

| Preset | Intent | Candidate Bands | Active Stages | Default Wet | Pass Condition |
| --- | --- | ---: | --- | ---: | --- |
| Vocal Preserve | Minimum damage, mild cleanup | 24 | Static + light broad + guarded suppressor candidate | 50-70% | Vocal stays close to original |
| Balanced Artifact Reduction | Practical compromise | 24-48 | Broad + limited surgical + light side | 65-85% | Residual mostly artifact/noise |
| AI Metallic Surgical | Chirps, whistles, metallic tones | 48-64 sparse | Narrow dynamic bands only on confirmed artifacts | 60-80% | Bands inactive most of the time |
| Strong Stress Test | Find damage boundary | 64 | Stronger experimental settings | 80-100% | Document failure point, not default |

## Band Decision Table

| Stage | Plugin | Band | Count | Freq | Q | Score/Threshold | Ratio | Attack | Release | Max GR | M/S | Guard Link | Target | Residual Result | Source Risk | Decision |
| --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Static | ReaEQ | HPF | n/a | 20-35 Hz | 0.7 | n/a | n/a | n/a | n/a | n/a | Both | n/a | Rumble | pending | Low | keep/reduce/remove |
| Broad | ReaXcomp/Nova | B5 | 7 | 2.5-5 kHz | broad | source-set | 1.1-1.5 | 20-80 ms | 100-300 ms | -0.3 to -1 dB | Mid | vocal/transient | Presence harshness | pending | High | keep only if residual is non-musical |
| Suppressor | Future DSP | Log band | 24/48/64 | source-specific | band-derived | artifact_score >= threshold | gain mask | 20-80 ms | 60-250 ms | mid -0.5 to -2 dB, side -1 to -3 dB | M/S independent | vocal/transient/harmonic/air | AI fizz/chirp/noise | pending | High | keep only after residual pass |
| Surgical | Nova E | Artifact | sparse | source-specific | 8-30 | high score only | 1.5-3 | 5-30 ms | 80-250 ms | -1 to -4 dB | M/S | harmonic/transient | Chirp/whistle | pending | High | remove if musical |

Every active band must get a decision. More bands are not automatically better.

## Evaluation Scores

For every source and preset score 1-5:

| Source | Preset | Noise Reduction | Vocal Preservation | Clarity | Air | Transients | Residual Cleanliness | Stereo/Space | Overall | Pass/Fail | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| clean vocal | Vocal Preserve | pending | pending | pending | pending | pending | pending | pending | pending | pending | Must not damage clean vocal |

A preset with noise reduction 5 and vocal preservation 2 fails. A preset with noise reduction 3 and vocal preservation 5 may be the better default.

## Porting Rules

Port only if it works across sources, residual does not leak source, 2-8 kHz and 8 kHz+ survive, transients stay sharp, stereo does not collapse, CPU is bounded, and it does not need per-phrase manual tuning.

Do not port huge static notch banks, harsh gating, strong ReaFIR subtract behavior, broad de-airing, or anything that sounds better only because it is louder.

## Final Conclusion Format

1. Best-performing chain:
2. Safest default chain:
3. Most dangerous stage:
4. Bands that consistently damaged vocal:
5. Bands that consistently reduced artifact safely:
6. Whether many dynamic bands is validated:
7. What should be implemented in Prompt 5:
8. What should be rejected:

## Current Evaluation Status

No manual A/B was performed in this patch because no source set was selected in this request. The workflow, session builder, band log, presets, and scoring template are ready for source-file testing.
