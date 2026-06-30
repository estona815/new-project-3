# Signal Path Map

There is no C++ `processBlock`. In this repository, JSFX `@sample` is the real-time processing equivalent. No C++ `AudioProcessor`, no APVTS, no `prepareToPlay`, and no `releaseResources` implementation were found.

## Entry Point

- File: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
- Function: JSFX `@sample`
- Lines: `220-807`
- Description: REAPER input L/R samples enter as `spl0` and `spl1`, are copied to dry sample variables, passed through a JSFX parameter snapshot and early dry-return gates, then processed through bad-input/silence checks, a bounded time-domain filterbank, detector/gain logic, optional M/S dynamic multiband attenuation, smoothed dry/wet blend, optional residual monitor output, and final NaN/Inf fallback.

## processBlock Path

NOT FOUND: `processBlock()`.

Searched: `rg "processBlock|prepareToPlay|releaseResources|AudioProcessor|AudioProcessorValueTreeState|APVTS|createParameterLayout"`. Implementation matches were NOT FOUND; docs/tests mention these terms only. Actual path below maps JSFX `@sample`.

1. Input buffer received
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:220-236`
   - details: Reads current REAPER samples from `spl0`/`spl1` into `in_l`/`in_r`, creates the JSFX snapshot, then checks bad input and silence.
   - risk: JSFX is per-sample, not block-based; no block-size snapshot exists.

2. Parameter read
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:77-110`, snapshot at `:223-239`
   - parameters read: Amount, Dry/Wet, Output Trim, Bypass, Max Reduction, Attack/Release, Processing Enabled, Mask Strength, Soft Knee, Vocal/Clarity/Air/Transient Preserve, Multiband Enabled, M/S Enabled, Multiband Mode, Mid/Side Amount, Side Artifact Reduction, Surgical Artifact Reduction, Residual Monitor, Mid Preserve.
   - risk: Reads happen in JSFX `@slider`, then are copied into `snap_*` variables at `@sample` start. This is the JSFX equivalent of a processBlock snapshot, not a C++ block snapshot.

3. Bypass handling
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:89`, `:265-271`
   - behavior: `bypass = slider8 >= 0.5`; snapshot `snap_bypass` returns dry before filterbank/denoise processing, resets wet smoothing to `0`, sets `status = 1`.
   - risk: Host bypass is separate from this plugin bypass and still needs DAW validation.

4. Dry copy
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:221-222`, `:265-285`, `:757-797`
   - behavior: `in_l`/`in_r` preserve the dry sample and are used for bypass, DryWet=0, disabled, bad processed fallback, suspicious-drop/full-band fallback, dry/wet, and final bad-output fallback.
   - risk: Dry copy is per-sample, not block-buffer copy. Bad input cannot safely pass through NaN/Inf, so it uses the previous stable output (`last_safe_l`/`last_safe_r`).

5. Denoise preparation
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:202-218`, `:287-337`
   - behavior: Sample-rate-safe one-pole filter coefficients are prepared in `@slider`; `@sample` splits audio into low/body/rest/attack/sandy/fizz/air bands and computes envelope, tail, transient, and high-band detector features.
   - risk: Broad filterbank detectors can misclassify source tone as artifact.

6. STFT / FFT analysis if present
   - file/line: NOT FOUND in active plugin path.
   - FFT size: NOT FOUND.
   - hop size: NOT FOUND.
   - window: NOT FOUND.
   - overlap-add: NOT FOUND.
   - risk: The active plugin is a time-domain IIR/filterbank JSFX, not STFT. Offline Python tools contain STFT helpers, but they are not the plugin path.

7. Model inference if present
   - file/line: NOT FOUND in active plugin path.
   - input tensor: NOT FOUND.
   - output tensor: NOT FOUND.
   - output type: NOT FOUND in runtime; `model_output_contract.py:9-16` defines future output types only.
   - risk: Any claim of AI model inference for the current JSFX would be false. Future model path must use the contract before trusting output.

8. Mask / gain calculation
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:356-381`, `:425-435`, `:523-585`, `:675-691`
   - current formula if readable: Soft artifact probabilities are logistic functions of detector dB and thresholds (`:356-371`); attenuation dB equals band max dB times probability, snapshotted mapped Amount, snapshotted Mask Strength, and band amount (`:373-376`); gain is `exp(-attenuation_db * db2lin)` clamped to per-band minimum (`:378-381`). M/S multiband targets use similar attenuation calculations and lower bounds (`:571-585`).
   - hard mask or soft mask: Soft probability/gain, not hard 0/1 mask.
   - suppression limit: Global `Max Reduction` creates `min_gain` (`:90-91`) and per-band maximums (`:172-183`, `:192-195`, `:544-558`, `:680-691`). Prompt 13/14 made collapse/floor and presence/air cap constants explicit at `:44-56`.
   - risk: Full-band or broad high-band attenuation can still reduce clarity before dry fallback triggers.

9. Magnitude / waveform reconstruction
   - file/line: `vocal_ai_artifact_split_tamer.jsfx:703-736`
   - behavior: Reconstructs processed L/R by summing attenuated filterbank bands. If M/S is active, it reconstructs mid/side then decodes to L/R (`:697-714`); otherwise sums L/R bands directly (`:715-730`).
   - risk: IIR band split is not perfect STFT reconstruction; no overlap-add normalization exists because there is no STFT path.

10. Dry/wet mix
    - file/line: `vocal_ai_artifact_split_tamer.jsfx:765-776`
    - formula: `out_l = in_l + (proc_l - in_l) * wet_state`; same for right. Equivalent to `dry * (1 - wet) + processed * wet`.
    - risk: Wet is smoothed (`:762-766`) after processing succeeds. DryWet=0 now returns dry before filterbank processing (`:259-265`).

11. Output sanitization
    - file/line: `vocal_ai_artifact_split_tamer.jsfx:741-763`, `:785-798`
    - NaN/Inf handling: Checks processed and final output via `x != x` and absolute limit; falls back to dry for bad processed/final output. Bad input uses the last stable safe output (`:231-235`).
    - risk: If the first ever input sample is invalid, `last_safe_l/r` are initialized to zero.

12. Final output
    - file/line: `vocal_ai_artifact_split_tamer.jsfx:795-798`
    - behavior: Writes final processed/mixed output to `spl0`/`spl1`.

## Diagram

Actual active path:

```text
REAPER input L/R (`spl0`, `spl1`)
-> dry sample variables (`in_l`, `in_r`)
-> JSFX parameter snapshot (`snap_*`)
-> bad-input and silence checks
-> early dry return for bypass / DryWet=0 / processing disabled
-> time-domain filterbank split
-> envelope / tail / transient / artifact detectors
-> soft probability and bounded gain calculation
-> optional M/S dynamic multiband attenuation
-> processed L/R reconstruction
-> processed-output numerical check
-> bad processed / suspicious-drop / full-band dry fallback
-> smoothed dry/wet blend
-> optional residual monitor output
-> final numerical check
-> REAPER output L/R (`spl0`, `spl1`)
```

Non-paths:

- No STFT/FFT in the active plugin path.
- No model inference call.
- No APVTS.
- No C++ processBlock allocation path.
- No file IO in JSFX `@sample`.

## A-Z Code Questions

| ID | Answer | Evidence | Risk | Recommended Next Action |
| --- | --- | --- | --- | --- |
| A. Where is the input buffer first modified? | YES | Bad/silence/early dry branches write `spl0`/`spl1` at `vocal_ai_artifact_split_tamer.jsfx:231-272`; normal path writes final output at `:788-789`. | First invalid sample can use zero-initialized last-safe state. | Add host test for invalid input transition. |
| B. Is a dry copy made before processing? | YES | `in_l = spl0`, `in_r = spl1` at `:208-209`. | Per-sample dry copy only. | Keep this invariant in future ports. |
| C. Where is bypass handled? | YES | Parameter read at `:76`; snapshot at `:214`; early dry branch at `:252-258`. | Host bypass remains separate. | Add host render test for bypass. |
| D. Is bypass true dry passthrough? | YES | `spl0 = in_l`, `spl1 = in_r` at `:253-254`. | Near bit-identical for normal finite input; bad-input branch happens earlier. | Add host render test for bypass. |
| E. Where is dry/wet applied? | YES | `out_l = in_l + (proc_l - in_l) * wet_state` at `:768-769`. | Wet smoothing can mask automation timing after processing succeeds. | Test automation transitions. |
| F. Is dry/wet applied before or after denoising? | YES, after | Reconstruction at `:697-730`, trim at `:732-733`, wet at `:759-769`. DryWet=0 exits early at `:259-265`. | None for DryWet=0; processed path still runs for nonzero wet. | Add host test for wet=0. |
| G. Are parameters read once per block or repeatedly in loops? | NO block exists | JSFX reads/clamps in `@slider` at `:64-97`; `snap_*` copies are made at `:210-226`; no C++ block loop. | Future C++ port still needs immutable snapshot. | Keep issue for future processor only. |
| H. Are parameters clamped? | YES | Clamps at `:66-96`; preset clamp in `preset_policy.py:54-70`. | Internal thresholds are constants, not user parameters. | Continue testing JSFX/JSON drift. |
| I. Where is Amount used? | YES | `amount` and nonlinear `mapped_amount` at `:66-67`; used at `:317-320` and `:515-529`. | Amount touches broad attenuation. | Default remains preservation-first. |
| J. Is Amount linear or nonlinear? | YES, nonlinear | `mapped_amount = pow(amount, 1.6)` at `:67`; JSON mapping at `factory_presets_safe_defaults.json:32`. | User-facing scale is not linear. | Document UI label if future custom UI exists. |
| K. Where is threshold used? | YES, internal | Threshold constants at `:183-186`; soft-knee probability at `:307-315`; low/body/rest thresholds embedded at `:444-449`. | No exposed Threshold parameter. | Do not add threshold until safety patch sequence. |
| L. Is there a hard mask? | NO | Soft logistic probabilities/gains at `:300-325`; no 0/1 mask in active path. | Soft mask can still over-attenuate if detector is wrong. | Evaluate residual and clean-input preservation. |
| M. Can any mask/gain become 0.0? | NO for normal finite params | Minimum gains from Max Reduction at `:76-77`, `:178-181`, `:531-545`, `:630-635`. | If invalid math occurred, fallback catches bad processed/output. | Keep min-gain tests. |
| N. Is there a MaxSuppressionDb or equivalent? | YES | Slider10 default/range at `:14`; clamp/min gain at `:76-77`; caps at `:158-169`. | Strong preset uses higher value intentionally. | Strong mode must remain non-default. |
| O. Does any code zero spectral bins? | NO | No STFT bins; time-domain gains are bounded above zero. | Offline scripts may contain STFT denoise, but not active plugin. | Keep offline tools out of runtime claims. |
| P. Does any code subtract noise magnitude directly? | NO in active plugin | Reconstruction sums attenuated bands (`:654-687`), no magnitude subtraction. | Model contract supports residual estimate but not runtime. | Do not add subtraction path without guard. |
| Q. Is there time smoothing? | YES | Detector coefficients at `:195-204`; gain smoothing at `:341-362` and `:547-617`; wet smoothing at `:725-729`. | Attack/release semantics are inverted in comments vs user expectation should be listening-tested. | Add automation/block-size render tests. |
| R. Is there frequency smoothing? | YES | Adjacent high-band smoothing at `:327-332`; M/S grouped bands at `:416-545`. | Broad smoothing may still dull source. | Residual/clean vocal A/B required. |
| S. Is there STFT overlap-add normalization? | NO | No STFT/FFT path found; file comments say no STFT model at `:98-100` and `:300-301`. | None for active path. | Only needed if future STFT path is added. |
| T. Can log(0), divide-by-zero, sqrt negative, NaN, or Inf occur? | LOW but not impossible | `eps` at `:42`; `max(..., eps)` around logs/divisions; bad processed/final checks at `:735-757`, `:779-792`. | Bad input uses last stable output; first invalid input can still resolve to initialized zero. | Keep numerical fuzz tests and host invalid-input checks. |
| U. Is model output shape checked? | NO in active plugin; YES in contract | Runtime model path NOT FOUND. Contract checks shape at `model_output_contract.py:266-276`. | Contract is not audio path. | Do not trust future model until wired through contract. |
| V. Is model output finite-checked? | NO in active plugin; YES in contract | Runtime model path NOT FOUND. Contract checks finite output at `model_output_contract.py:301-310`. | Contract only. | Same as U. |
| W. What happens if model is missing? | Current runtime has no model | Metadata says model version none and missing model behavior is DSP-only safe path (`release/rc_metadata.json:19-26`). | Product naming may imply AI model. | UI/release copy must not imply active inference. |
| X. What happens if model output is invalid? | NOT APPLICABLE runtime | Contract returns invalid fallback results at `model_output_contract.py:203-223`, `:255-310`. | Not connected to JSFX. | Future integration must define dry fallback. |
| Y. Does model output directly replace waveform? | NO active runtime | No model output runtime. Contract waveform path blends, not direct replace (`model_output_contract.py:368-391`). | Future code could bypass this if not enforced. | Keep contract tests mandatory. |
| Z. Can processBlock allocate memory? | UNKNOWN / NOT APPLICABLE | `processBlock` NOT FOUND. JSFX `@sample` has no file IO/allocation calls found in inspected path. | Future C++ processor could introduce allocations. | Re-audit when C++ code appears. |
