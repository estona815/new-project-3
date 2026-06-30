"""End-to-end fail-closed AutoMix orchestration layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator

__all__ = ["AutoMixOrchestrator"]


def __getattr__(name: str):
    if name == "AutoMixOrchestrator":
        from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator

        return AutoMixOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
