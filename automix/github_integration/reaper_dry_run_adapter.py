"""Dry-run REAPER adapter boundary for future reapy/MCP execution.

The adapter imports without REAPER and refuses real write operations until the
existing AutoMix evidence gates can prove snapshot, rollback, A/B preview, and
semantic parameter safety.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ReaperDryRunAdapter:
    """Small JSON-safe adapter with dry-run defaults and fail-closed writes."""

    def __init__(self) -> None:
        self._reapy = self._load_reapy()

    @staticmethod
    def _load_reapy() -> Any | None:
        try:
            import reapy  # type: ignore

            return reapy
        except Exception:
            return None

    def _error(self, action: str) -> dict[str, Any]:
        return {
            "ok": False,
            "action": action,
            "dry_run": None,
            "error": "reapy is unavailable or REAPER is not configured on this machine",
        }

    @staticmethod
    def _dry(action: str, **payload: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "action": action,
            "dry_run": True,
            "would_execute": payload,
        }

    @staticmethod
    def _blocked(action: str, reason: str) -> dict[str, Any]:
        return {
            "ok": False,
            "action": action,
            "dry_run": False,
            "error": reason,
            "write_safety": "blocked",
        }

    def test_connection(self, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return self._dry("test_connection")
        if self._reapy is None:
            return self._error("test_connection")
        try:
            project = self._reapy.Project()
            return {"ok": True, "action": "test_connection", "dry_run": False, "project": str(project)}
        except Exception as exc:
            return {"ok": False, "action": "test_connection", "dry_run": False, "error": str(exc)}

    def list_tracks(self, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return self._dry("list_tracks")
        if self._reapy is None:
            return self._error("list_tracks")
        try:
            project = self._reapy.Project()
            tracks = [{"index": index, "name": track.name} for index, track in enumerate(project.tracks)]
            return {"ok": True, "action": "list_tracks", "dry_run": False, "tracks": tracks}
        except Exception as exc:
            return {"ok": False, "action": "list_tracks", "dry_run": False, "error": str(exc)}

    def list_fx(self, track_index: int, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return self._dry("list_fx", track_index=track_index)
        if self._reapy is None:
            return self._error("list_fx")
        return self._blocked("list_fx", "real FX listing waits for the project runtime inventory collector")

    def list_available_fx(self, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return self._dry("list_available_fx")
        if self._reapy is None:
            return self._error("list_available_fx")
        return self._blocked("list_available_fx", "plugin inventory scanning must use the existing semantic validation gates")

    def add_fx(self, track_index: int, fx_name: str, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return self._dry("add_fx", track_index=track_index, fx_name=fx_name)
        if self._reapy is None:
            return self._error("add_fx")
        return self._blocked("add_fx", "write operation blocked until snapshot and rollback evidence are implemented")

    def set_fx_param(
        self,
        track_index: int,
        fx_index: int,
        param_name: str,
        value: float,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if dry_run:
            return self._dry(
                "set_fx_param",
                track_index=track_index,
                fx_index=fx_index,
                param_name=param_name,
                value=value,
            )
        if self._reapy is None:
            return self._error("set_fx_param")
        return self._blocked("set_fx_param", "write operation blocked until semantic parameter safety is proven")

    def render_project(self, output_path: str | Path, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return self._dry("render_project", output_path=str(output_path))
        if self._reapy is None:
            return self._error("render_project")
        return self._blocked("render_project", "render execution blocked until A/B preview and rollback gates are wired")
