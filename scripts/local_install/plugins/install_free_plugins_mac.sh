#!/usr/bin/env bash
set -u

EXECUTE=0
for arg in "$@"; do
  [[ "$arg" == "--execute" ]] && EXECUTE=1
done
[[ "${EXECUTE_INSTALL:-0}" == "1" ]] && EXECUTE=1

echo "Free plugin install harness for macOS"
echo "Official source URLs are listed in plugin_registry/plugin_source_urls.md"

if [[ "$EXECUTE" != "1" ]]; then
  echo "[dry-run] Would open/download official installers for core plugins only on the main computer."
  echo "[dry-run] Refusing to install. Pass --execute or EXECUTE_INSTALL=1 on the main computer."
  exit 0
fi

echo "[refuse] Execution placeholder. Add reviewed commands locally after manual URL verification."
exit 2

