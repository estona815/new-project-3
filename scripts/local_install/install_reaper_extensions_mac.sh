#!/usr/bin/env bash
set -u

if [[ "${EXECUTE_INSTALL:-0}" != "1" ]]; then
  echo "[dry-run] Would install/verify SWS, ReaPack, ReaTeam repos, js_ReaScriptAPI, and ReaImGui."
  echo "[dry-run] Re-run on main computer with EXECUTE_INSTALL=1 after reviewing official sources."
  exit 0
fi

echo "[execute] Placeholder only. Fill official download commands after local review."
exit 2

