# Realtime Safety Audit

Inspected path: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`, especially JSFX `@slider` (`:77-218`) and `@sample` (`:220-807`). C++ `processBlock` and functions called by it are NOT FOUND.

## Summary

NO OBVIOUS REAL-TIME UNSAFE OPERATION FOUND IN INSPECTED PATH for file IO, logging, locks, model loading, network calls, dynamic allocation, or unbounded loops inside the active JSFX `@sample` path.

This statement is limited to the active JSFX path. It does not validate missing C++/JUCE sources, REAPER host internals, offline Python render scripts, or CI workflows that reference missing `plugin/` sources.

## Checklist

| Check | Finding | Evidence | Severity | Recommended Fix |
| --- | --- | --- | --- | --- |
| Dynamic allocation | NOT FOUND in JSFX `@sample` | `@sample` is arithmetic/state only, `vocal_ai_artifact_split_tamer.jsfx:220-807` | P0 if added later | Re-audit future C++/JSFX edits. |
| `std::vector resize` | NOT APPLICABLE / NOT FOUND | No C++ processBlock found. | P0 for future C++ | Require allocation tests in future port. |
| `new` / `delete` | NOT FOUND in active path | No C++ active path. | P0 if future code allocates | Keep forbidden-pattern RC check. |
| File IO | NOT FOUND in JSFX `@sample` | No `fopen`/logging in `@sample`; RC check scans sample body. | P0 if added | File IO only outside audio thread. |
| Console/disk logging | NOT FOUND in JSFX `@sample` | `status` is numeric state only (`vocal_ai_artifact_split_tamer.jsfx:60`, `:701-723`, `:742-747`). | P0 if added | Use UI-readable atomic/status equivalent only. |
| Locks/mutex | NOT FOUND | No `mutex`/`lock` in JSFX. | P0 if added | No blocking locks in audio path. |
| Blocking wait | NOT FOUND | No wait/sleep calls. | P0 if added | Background init only. |
| Network call | NOT FOUND | No network API in JSFX. | P0 if added | Never in audio thread. |
| Model loading | NOT FOUND | No runtime model path; metadata says no model file required (`release/rc_metadata.json:19-26`). | P0 if added in audio path | Prepare/background load only. |
| Preset loading | NOT FOUND in `@sample` | Preset JSON handling is Python (`preset_policy.py:14-23`, `:60-70`), not JSFX sample path. | P0 if added | Host/preset load outside audio callback. |
| Expensive string construction | NOT FOUND | JSFX `@sample` contains no strings. | P2 | None. |
| Exception-driven control flow | NOT APPLICABLE | JSFX has no exceptions. | P2 | Future Python/C++ tests only. |
| Unbounded loops | NOT FOUND | `@sample` is straight-line arithmetic/branches. | P0 if added | Any future loops must be bounded by channels/block size. |
| UI calls | NOT FOUND | JSFX sliders update globals in `@slider`; no custom UI call. | P2 | Keep custom UI out of audio thread. |
| Parameter tree mutation | NOT APPLICABLE | APVTS NOT FOUND. | P0 for future C++ | Immutable snapshot if APVTS appears. |
| Non-atomic shared state | JSFX state is audio-thread local/global | State variables initialized at `:39-74`, updated in `@sample`. | P2 | For C++ port use atomics or lock-free messaging for status. |
| Sample-rate/block-size reallocation | NOT FOUND | Coefficients use `srate` in `@slider` `:202-218`; no memory reallocation. | P2 | Host sample-rate behavior needs REAPER validation. |

## Numerical Safety

| Area | Evidence | Finding | Risk |
| --- | --- | --- | --- |
| Epsilon and floors | `vocal_ai_artifact_split_tamer.jsfx:42-56` | `eps = 0.00000001`; Prompt 13 made floor/collapse constants explicit; Prompt 14 made presence/air caps explicit. | Helps avoid log/divide zero and makes destructive-collapse guard thresholds reviewable. |
| Input finite check | `:228-235` | NaN/Inf/huge input detected; output uses `last_safe_l/r`. | Avoids invalid output; first invalid sample may use zero-initialized last-safe state. |
| Log protection | `:278-279`, `:302-305`, `:382-399`, `:444-449`, `:641` | Uses `max(..., eps)` before logs/divides. | Low numerical risk. |
| Gain bounds | `:372-375`, `:414-428`, `:673-685` | Gains clamped to min/max; near-floor/full-band collapse constants are explicit. | Protects from zero masks and broad floor collapse. |
| Processed finite check | `:735-750` | Bad processed falls back to dry. | Good. |
| Final output finite check | `:779-792` | Bad final output falls back to dry. | Good. |

## Findings

| File | Function | Line | Issue | Severity | Recommended Fix |
| --- | --- | --- | --- | --- | --- |
| `vocal_ai_artifact_split_tamer.jsfx` | `@sample` | `235-242` | Reduced: bad input now uses last stable safe output instead of hard zero. First invalid sample can still resolve to initialized zero. | P1 | Host-test one-sample invalid spikes. |
| `vocal_ai_artifact_split_tamer.jsfx` | `@sample` | `754-770` | Reduced: suspicious drop/full-band collapse now dry-fallbacks instead of 25% wet processing; Prompt 14 blends high-band floor collapse earlier. | P1 | Validate with real REAPER renders and residual listening. |
| `vocal_ai_artifact_split_tamer.jsfx` | `@slider` / `@sample` | `77-110`, `223-239` | JSFX has no C++ block, but `snap_*` copies now provide deterministic per-sample parameter/fallback decisions. | P2 | Future C++ processor must add true block snapshot before inner loops. |
| `evaluation_harness.py` | `render_item` | `77-93` | Harness cannot execute JSFX directly; it compares passthrough or external processed WAVs. | P2 | Add REAPER render automation or documented manual render capture. |
| `.github/workflows/*.yml` | CI | macOS `45-65`, Windows `45-67`, Linux `89-112` | CI references missing `plugin/` CMake project. | P3/P0 release | Align CI with actual JSFX package or add missing plugin project. |

## Inspected Non-Paths

- C++ `AudioProcessor`: NOT FOUND.
- C++ `processBlock`: NOT FOUND.
- APVTS parameter tree: NOT FOUND.
- Model loading/inference: NOT FOUND.
- STFT/FFT frame processor: NOT FOUND in active plugin.
