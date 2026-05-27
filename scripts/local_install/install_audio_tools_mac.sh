#!/usr/bin/env bash
set -u

if [[ "${EXECUTE_INSTALL:-0}" != "1" ]]; then
  echo "[dry-run] Would install/verify FFmpeg, Python QC packages, Demucs, UVR, DeepFilterNet, and RNNoise candidates."
  echo "[dry-run] No models or packages are downloaded in dry-run mode."
  exit 0
fi

echo "[execute] Placeholder only. Add reviewed commands on the main computer."
exit 2

