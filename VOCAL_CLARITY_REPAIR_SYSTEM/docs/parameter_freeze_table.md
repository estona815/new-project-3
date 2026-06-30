# Parameter Freeze Table

Prompt 9 freezes the current JSFX slider order and meaning for preset/session compatibility. Existing slider IDs must not be renamed or reused for different meanings. New parameters must be appended with safe defaults and migration behavior.

| ID | Display name | Range | Default | Automation-safe | Preset-safe | Internal mapping | Risk |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| AttackHarshTame | Attack Harsh Tame | 0..100 | 32 | developer only | yes | clamped percent | Legacy raw control; keep ID/order. |
| SandySibilanceTame | Sandy Sibilance Tame | 0..100 | 38 | developer only | yes | clamped percent | Legacy raw control; keep ID/order. |
| DigitalFizzTame | Digital Fizz Tame | 0..100 | 44 | developer only | yes | clamped percent | Legacy raw control; keep ID/order. |
| TailWarbleHide | Tail Warble Hide | 0..100 | 28 | developer only | yes | clamped percent | Legacy raw control; keep ID/order. |
| BodyPreserve | Body Preserve | 0..100 | 20 | bounded | yes | clamped percent | Can change body gain slightly; keep conservative. |
| DryWet | Dry/Wet | 0..100 | 70 | yes, smoothed | yes | percent to 0..1 | DryWet 0 must remain dry. |
| OutputTrimDb | Output Trim (dB) | -18..18 | 0 | bounded | yes | dB to gain | Can clip if abused; output finite checks remain active. |
| Bypass | Bypass | 0..1 | 0 | yes | yes | boolean | Must return dry and ignore residual mode. |
| Amount | Amount | 0..100 | 30 | yes, smoothed by gain path | yes | `pow(userAmount, 1.6)` | Main cleanup strength; never remap without migration. |
| MaxSuppressionDb | Max Reduction (dB) | 0..24 | 8 | yes, bounded | yes | dB gain floor | Strong values allowed only by user/preset, not default. |
| AttackMs | Detector Attack (ms) | 1..200 | 50 | bounded | yes | coefficient from sample rate | Fast automation can alter detector feel. |
| ReleaseMs | Detector Release (ms) | 1..500 | 12 | bounded | yes | coefficient from sample rate | Fast automation can alter detector feel. |
| ProcessingEnabled | Processing Enabled | 0..1 | 1 | developer only | yes | boolean | Disabled must be dry passthrough. |
| MaskStrength | Mask Strength | 0..1 | 0.35 | advanced/developer | yes | clamped multiplier | Raw denoise strength; keep hidden from simple UI. |
| SoftKneeDb | Soft Knee (dB) | 1..24 | 9 | advanced/developer | yes | logistic probability width | Too narrow can sound grabby. |
| VocalPreserve | Vocal Preserve | 0..1 | 0.85 | yes | yes | attenuation-limit reducer | Source guard only; never boost. |
| ClarityPreserve | Clarity Preserve | 0..1 | 0.85 | yes | yes | attenuation-limit reducer | Protects consonants/presence. |
| AirPreserve | Air Preserve | 0..1 | 0.80 | yes | yes | attenuation-limit reducer | Protects air/ambience. |
| TransientPreserve | Transient Preserve | 0..1 | 0.80 | yes | yes | attenuation-limit reducer | Protects attacks. |
| MultibandEnabled | Multiband Enabled | 0..1 | 1 | mode-safe | yes | boolean | Must not allocate or reset unsafely. |
| MSEnabled | M/S Enabled | 0..1 | 1 | mode-safe | yes | boolean | Mono/stereo paths must stay safe. |
| MultibandMode | Multiband Mode | 0..3 | 0 | mode-safe | yes | enum Preserve/Balanced/Surgical/Strong | Strong must never be default or auto-migrated. |
| MidAmount | Mid Amount | 0..1 | 0.25 | yes | yes | clamped multiplier | Mid vocal must remain protected. |
| SideAmount | Side Amount | 0..1 | 0.40 | yes | yes | clamped multiplier | Side cleanup must not collapse width. |
| SideArtifactReduction | Side Artifact Reduction | 0..1 | 0.45 | yes | yes | clamped multiplier | Side-biased reduction; stereo guard active. |
| SurgicalArtifactReduction | Surgical Artifact Reduction | 0..1 | 0.25 | yes | yes | clamped multiplier | Surgical mode only; no clean-source damage. |
| ResidualMonitor | Residual Monitor | 0..2 | 0 | mode-safe | yes | enum Off/Processed/Residual | Debug/listening output; must not affect bypass. |
| MidPreserve | Mid Preserve | 0..1 | 0.85 | yes | yes | attenuation-limit reducer | Protects center vocal. |
| HarmonicPreserve | Harmonic Preserve | 0..1 | 0.75 | internal | yes | internal constant | Internal source guard only. |

Mandatory freeze rules:

- Do not rename existing IDs.
- Do not reorder existing sliders.
- Do not change parameter meaning without migration.
- Do not change normalized mapping without migration.
- Missing new parameters use safe defaults.
- Invalid values are finite-clamped.
- Strong mode is never selected by default or migration.
