# C WAV Helper Tools

These tools are helper utilities for fast WAV checks and simple fallback processing. They do not replace Logic Pro, arrangement decisions, musical judgment, or final mastering.

## Supported Minimum WAV Format

- Little-endian RIFF/WAVE
- Mono or stereo
- PCM 16-bit, PCM 24-bit, PCM 32-bit
- IEEE float 32-bit

Unsupported or malformed files exit non-zero and print a clear error to stderr.

## Build

```bash
make -C AI_BEAT_LOGIC_WORKFLOW/tools
```

Clean build artifacts:

```bash
make -C AI_BEAT_LOGIC_WORKFLOW/tools clean
```

Run the local smoke test:

```bash
make -C AI_BEAT_LOGIC_WORKFLOW/tools test
```

The test generates a dummy WAV, parses JSON output, runs gain/trim helpers, and confirms an invalid file does not crash.

## Tools

### `wav_analyzer`

```bash
AI_BEAT_LOGIC_WORKFLOW/tools/wav_analyzer input.wav
```

Prints JSON to stdout with sample rate, channels, bit depth, duration, peak, RMS, possible clipping, clipped sample count, and simple silence regions below -60 dBFS for longer than 0.5 seconds.

### `wav_gain_stage`

```bash
AI_BEAT_LOGIC_WORKFLOW/tools/wav_gain_stage input.wav output.wav --target-peak-db -3.0
```

Applies gain so the detected peak reaches the requested target peak. The tool refuses silent files and target peaks above 0 dBFS. Output is written as 32-bit float WAV while preserving sample rate and channel count.

### `wav_trim_fade`

```bash
AI_BEAT_LOGIC_WORKFLOW/tools/wav_trim_fade input.wav output.wav --start 5.0 --end 125.0 --fade-in 0.02 --fade-out 1.5
```

Trims a section and applies linear fades. Output is written as 32-bit float WAV while preserving sample rate and channel count.

### `wav_integrity_check`

```bash
AI_BEAT_LOGIC_WORKFLOW/tools/wav_integrity_check input.wav
```

Validates the WAV header, supported format, frame alignment, and basic data-size consistency. Prints pass/fail JSON.

