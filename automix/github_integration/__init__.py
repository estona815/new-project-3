"""GitHub-researched REAPER integration helpers.

This package is intentionally isolated from live REAPER automation. It provides
portable diagnostics, source-attribution metadata, and dry-run adapter checks for
future MCP/reapy work without granting write safety.
"""

from .audio_diagnostics import build_audio_diagnostic_report, write_audio_diagnostic_report
from .integration_manifest import build_github_integration_manifest
from .reaper_dry_run_adapter import ReaperDryRunAdapter
from .smoke import build_github_integration_smoke, write_github_integration_smoke

__all__ = [
    "ReaperDryRunAdapter",
    "build_audio_diagnostic_report",
    "build_github_integration_manifest",
    "build_github_integration_smoke",
    "write_audio_diagnostic_report",
    "write_github_integration_smoke",
]
