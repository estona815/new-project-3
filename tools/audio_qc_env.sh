#!/usr/bin/env bash
set -euo pipefail

export CODEX_AUDIO_QC_VENV="${CODEX_AUDIO_QC_VENV:-$HOME/.cache/codex-audio-qc/new-project-3-venv}"

if [[ ! -x "$CODEX_AUDIO_QC_VENV/bin/python" ]]; then
  echo "Missing QC venv: $CODEX_AUDIO_QC_VENV" >&2
  return 1 2>/dev/null || exit 1
fi

# shellcheck disable=SC1091
source "$CODEX_AUDIO_QC_VENV/bin/activate"

FFMPEG_PATH="$(python - <<'PY'
import imageio_ffmpeg
print(imageio_ffmpeg.get_ffmpeg_exe())
PY
)"

STATIC_FFMPEG_INFO="$(python - <<'PY'
import contextlib
import sys

try:
    import static_ffmpeg
    with contextlib.redirect_stdout(sys.stderr):
        ffmpeg_path, ffprobe_path = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    print(ffmpeg_path)
    print(ffprobe_path)
except Exception:
    print("")
    print("")
PY
)"

STATIC_FFMPEG_PATH="$(printf '%s\n' "$STATIC_FFMPEG_INFO" | sed -n '1p')"
FFPROBE_PATH="$(printf '%s\n' "$STATIC_FFMPEG_INFO" | sed -n '2p')"
FFMPEG_DIR="$(dirname "$FFMPEG_PATH")"
STATIC_FFMPEG_DIR=""
if [[ -n "$STATIC_FFMPEG_PATH" ]]; then
  STATIC_FFMPEG_DIR="$(dirname "$STATIC_FFMPEG_PATH")"
fi

ln -sf "$FFMPEG_PATH" "$CODEX_AUDIO_QC_VENV/bin/ffmpeg"
if [[ -n "$FFPROBE_PATH" && -x "$FFPROBE_PATH" ]]; then
  ln -sf "$FFPROBE_PATH" "$CODEX_AUDIO_QC_VENV/bin/ffprobe"
fi

export FFMPEG_PATH
export FFPROBE_PATH
export PATH="$CODEX_AUDIO_QC_VENV/bin:$FFMPEG_DIR${STATIC_FFMPEG_DIR:+:$STATIC_FFMPEG_DIR}:$PATH"

if [[ "${1:-}" == "--check" ]]; then
  echo "audio_qc_env=ok"
  echo "python_path=$(command -v python)"
  echo "python_version=$(python --version 2>&1)"
  echo "pip_version=$(python -m pip --version)"
  echo "ffmpeg_path=$(command -v ffmpeg)"
  echo "ffmpeg_version_first_line=$(ffmpeg -version 2>&1 | sed -n '1p')"
  if command -v ffprobe >/dev/null 2>&1; then
    echo "ffprobe_available=true"
    echo "ffprobe_path=$(command -v ffprobe)"
    echo "ffprobe_version_first_line=$(ffprobe -version 2>&1 | sed -n '1p')"
  else
    echo "ffprobe_available=false"
  fi
  echo "ffmpeg_normalize_version=$(ffmpeg-normalize --version 2>&1)"
  python - <<'PY'
def check(name):
    try:
        module = __import__(name)
        version = getattr(module, "__version__", "ok")
        print(f"{name}_import=ok {version}")
    except Exception as exc:
        print(f"{name}_import=FAIL {type(exc).__name__}: {exc}")

for module_name in ["pyloudnorm", "soundfile", "numpy", "scipy"]:
    check(module_name)
PY
fi
