# Parameter Audit

Scope: active REAPER JSFX path plus current JSON preset/default policy. No parameter values were changed.

## Parameter System

- APVTS: NOT FOUND. Searched `AudioProcessorValueTreeState`, `APVTS`, and `createParameterLayout`.
- UI binding: JSFX host sliders only, defined directly in `vocal_ai_artifact_split_tamer.jsfx:5-32`.
- DSP read location: JSFX `@slider`, `vocal_ai_artifact_split_tamer.jsfx:77-110`.
- Prompt 15 snapshot note: `VocalPreserve`, `ClarityPreserve`, `AirPreserve`, `TransientPreserve`, internal `HarmonicPreserve`, and `MidPreserve` are copied into `snap_*` variables at the top of JSFX `@sample` before processing decisions.
- Preset/default source: JSFX slider defaults (`:5-32`) plus factory JSON (`factory_presets_safe_defaults.json:23-52`, Preserve preset at `:107-112`).
- Preset/state behavior: legacy slider order is preserved and missing new parameters use safe defaults (`factory_presets_safe_defaults.json:16-22`); Python sanitizer clamps invalid/missing values (`preset_policy.py:60-70`).

## Parameter Table

| ID | Display Name | Defined | Range | Default | Smoothing | UI Binding | DSP Read | Preset/State | Risk |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| AttackHarshTame | Attack Harsh Tame | JSFX `:5`, JSON `:24` | 0..100 | 32 | Gain smoothing `:341-347` | JSFX slider1 | `:68` | Preserve `:108` | Can affect consonants/transients. |
| SandySibilanceTame | Sandy Sibilance Tame | JSFX `:6`, JSON `:25` | 0..100 | 38 | Gain smoothing `:348-352` | JSFX slider2 | `:69` | Preserve `:108` | Can dull sibilance/clarity. |
| DigitalFizzTame | Digital Fizz Tame | JSFX `:7`, JSON `:26` | 0..100 | 44 | Gain smoothing `:353-357` | JSFX slider3 | `:70` | Preserve `:108` | Can remove air/texture. |
| TailWarbleHide | Tail Warble Hide | JSFX `:8`, JSON `:27` | 0..100 | 28 | Tail env `:197-198`, gains `:353-362` | JSFX slider4 | `:71` | Preserve `:108` | Tail cleanup may remove ambience. |
| BodyPreserve | Body Preserve | JSFX `:9`, JSON `:28` | 0..100 | 20 | None direct | JSFX slider5 | `:72`, used `:414` | Preserve `:108` | Tiny body lift; still sound-affecting. |
| DryWet | Dry/Wet | JSFX `:10`, JSON `:29` | 0..100 | 70 | Wet smoothing `:725-729` | JSFX slider6 | `:73` | Preserve `:108` | Main destructive-audio exposure control. |
| OutputTrimDb | Output Trim (dB) | JSFX `:11`, JSON `:30` | -18..18 | 0 | None | JSFX slider7 | `:74`, used `:689-690` | Preserve `:108` | Can clip if boosted externally. |
| Bypass | Bypass | JSFX `:12`, JSON `:31` | 0..1 | 0 | Early dry branch, resets wet `:252-258` | JSFX slider8 | `:76`, snapshot `:214` | Preserve `:108` | Must remain true dry passthrough. |
| Amount | Amount | JSFX `:13`, JSON `:32` | 0..100 | 30 | Indirect gain smoothing | JSFX slider9 | `:66-67` | Preserve `:109` | Nonlinear global strength. |
| MaxSuppressionDb | Max Reduction (dB) | JSFX `:14`, JSON `:33` | 0..24 | 8 | None direct | JSFX slider10 | `:76-77` | Preserve `:109` | Critical destructive suppression limiter. |
| AttackMs | Detector Attack (ms) | JSFX `:15`, JSON `:34` | 1..200 | 50 | Coefficients `:195`, `:201` | JSFX slider11 | `:78` | Preserve `:109` | Fast settings could grab transients. |
| ReleaseMs | Detector Release (ms) | JSFX `:16`, JSON `:35` | 1..500 | 12 | Coefficients `:196-202` | JSFX slider12 | `:79` | Preserve `:109` | Release affects smear/recovery. |
| ProcessingEnabled | Processing Enabled | JSFX `:17`, JSON `:36` | 0..1 | 1 | Hard branch `:706-710` | JSFX slider13 | `:80` | Preserve `:109` | Equivalent to model-disabled/dsp-disabled dry fallback. |
| MaskStrength | Mask Strength | JSFX `:18`, JSON `:37` | 0..1 | 0.35 | Indirect gain smoothing | JSFX slider14 | `:81` | Preserve `:109` | Multiplies attenuation. |
| SoftKneeDb | Soft Knee (dB) | JSFX `:19`, JSON `:38` | 1..24 | 9 | None | JSFX slider15 | `:82` | Preserve `:109` | Detection curve shape. |
| VocalPreserve | Vocal Preserve | JSFX `:20`, JSON `:39` | 0..1 | 0.85 | Guards `:171-176`, `:483-497` | JSFX slider16 | `:83` | Preserve `:110` | Lower values permit vocal removal. |
| ClarityPreserve | Clarity Preserve | JSFX `:21`, JSON `:40` | 0..1 | 0.85 | Guards `:171-176`, `:382-395` | JSFX slider17 | `:84` | Preserve `:110` | Protects consonants/presence. |
| AirPreserve | Air Preserve | JSFX `:22`, JSON `:41` | 0..1 | 0.80 | Air guard `:397-407` | JSFX slider18 | `:85` | Preserve `:110` | Protects high air/ambience. |
| TransientPreserve | Transient Preserve | JSFX `:23`, JSON `:42` | 0..1 | 0.80 | Transient guard `:290-298`, smoothing `:203` | JSFX slider19 | `:86` | Preserve `:110` | Protects attacks. |
| MultibandEnabled | Multiband Enabled | JSFX `:24`, JSON `:43` | 0..1 | 1 | M/S gain smoothing `:547-617` | JSFX slider20 | `:88` | Preserve `:110` | Extra attenuation path. |
| MSEnabled | M/S Enabled | JSFX `:25`, JSON `:44` | 0..1 | 1 | M/S gain smoothing `:547-617` | JSFX slider21 | `:89` | Preserve `:110` | Stereo width/source risk. |
| MultibandMode | Multiband Mode | JSFX `:26`, JSON `:45` | 0..3 enum | 0 | Mode caps `:101-153` | JSFX slider22 | `:90` | Preserve `:110` | Strong mode is not release default. |
| MidAmount | Mid Amount | JSFX `:27`, JSON `:46` | 0..1 | 0.25 | M/S gains `:547-617` | JSFX slider23 | `:91` | Preserve `:111` | Center vocal exposure. |
| SideAmount | Side Amount | JSFX `:28`, JSON `:47` | 0..1 | 0.40 | M/S gains `:547-617` | JSFX slider24 | `:92` | Preserve `:111` | Side ambience/width exposure. |
| SideArtifactReduction | Side Artifact Reduction | JSFX `:29`, JSON `:48` | 0..1 | 0.45 | M/S gains `:547-617` | JSFX slider25 | `:93` | Preserve `:111` | Can narrow stereo texture. |
| SurgicalArtifactReduction | Surgical Artifact Reduction | JSFX `:30`, JSON `:49` | 0..1 | 0.25 | M/S gains `:547-617` | JSFX slider26 | `:94` | Preserve `:111` | Chirp-focused gate can hit source harmonics. |
| ResidualMonitor | Residual Monitor | JSFX `:31`, JSON `:50` | 0..2 enum | 0 | None | JSFX slider27 | `:95`, output `:733-740` | Preserve `:111` | Debug output can confuse users if left on. |
| MidPreserve | Mid Preserve | JSFX `:32`, JSON `:51` | 0..1 | 0.85 | Protect factors `:483-489` | JSFX slider28 | `:96` | Preserve `:111` | Protects center material. |
| HarmonicPreserve | internal hidden constant | JSFX `:87`, JSON `:52` | 0..1 | 0.75 | Guards `:290-294`, `:483-497` | NOT FOUND UI | internal only | JSON internal default | Internal constant overrides parameter; no slider. |

## Required Parameter Findings

- Amount: FOUND, `slider9`, JSFX `:13`, read `:66-67`, nonlinear `pow(amount, 1.6)`.
- Mix / DryWet: FOUND, `slider6`, JSFX `:10`, read `:73`, applied `:731-732`.
- Threshold: NOT FOUND as user parameter. Internal constants only at `:183-186` and low/body/rest embedded offsets at `:444-449`.
- MaskStrength: FOUND, `slider14`, JSFX `:18`, read `:81`, used `:317-320` and `:515-529`.
- Suppression / MaxSuppressionDb: FOUND as `Max Reduction (dB)`, `slider10`, JSFX `:14`, read `:76-77`.
- Attack / Release: FOUND, `slider11`/`slider12`, JSFX `:15-16`, read `:78-79`.
- FFT size: NOT FOUND in active plugin.
- Hop size: NOT FOUND in active plugin.
- Bypass: FOUND, `slider8`, JSFX `:12`, read `:76`, snapshot `:214`, branch `:252-258`.
- InferenceEnabled: NOT FOUND as AI parameter. Closest equivalent is `ProcessingEnabled` (`slider13`, JSFX `:17`, `:80`, `:706-710`).
- ModelMode: NOT FOUND in active plugin. Factory preset metadata has `"model_mode": "DSP Only"` for presets, e.g. `factory_presets_safe_defaults.json:105`.
- QualityMode: NOT FOUND. `MultibandMode` exists but is not a quality/render mode.
- Preset: JSON policy only; not a JSFX runtime parameter.

## Mismatches / Risks

- APVTS default differs from UI default: NOT APPLICABLE; APVTS NOT FOUND.
- UI default differs from DSP fallback: no custom UI found. JSFX defaults and Preserve JSON are intended to match (`factory_presets_safe_defaults.json:107-112`).
- Preset default differs from fresh instance: no mismatch found; Preserve policy says fresh default (`factory_presets_safe_defaults.json:6-15`).
- Internal constant overrides parameter: `harmonic_preserve = 0.75` is internal only (`vocal_ai_artifact_split_tamer.jsfx:101`).
- Missing clamp: No missing clamp found for host-visible sliders in `@slider`; clamps are at `vocal_ai_artifact_split_tamer.jsfx:80-110`.
- Dangerous default: Strong mode exists but is not default (`factory_presets_safe_defaults.json:82-90`, `:178-194`).
