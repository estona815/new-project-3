#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="${CODEX_VOCAL_RC_QA_DIR:-/tmp/codex_vocal_rc_qa}"

cd "$ROOT_DIR"

python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.rc_qa --output-dir "$OUTPUT_DIR" "$@"

printf 'RC QA command completed. If --output-dir was provided, use that directory; otherwise reports are in %s\n' "$OUTPUT_DIR"
