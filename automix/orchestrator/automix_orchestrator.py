from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from automix.export.final_export_state_resolver import resolve_final_export_state
from automix.intent.intent_classifier import build_intent_classification
from automix.orchestrator.global_qc_aggregator import build_global_qc_summary
from automix.orchestrator.global_rollback_registry import build_global_rollback_registry
from automix.orchestrator.current_state_report import build_current_state_summary, write_current_state_summary
from automix.orchestrator.global_safety_controller import (
    evaluate_workflow_continuation,
    global_status_from_results,
    next_actions_from_results,
)
from automix.orchestrator.project_context_resolver import resolve_project_context
from automix.orchestrator.professional_readiness_audit import build_professional_readiness_audit
from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.stage_dependency_graph import APPLIED_STAGES, STAGE_ORDER, can_run_stage
from automix.orchestrator.stage_result_schema import finish_stage, skipped_stage, start_stage
from automix.orchestrator.stage_status import StageStatus
from automix.orchestrator.state_resume import build_resume_state
from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_inventory_audit import audit_plugin_inventory, load_inventory, write_plugin_capability_report
from automix.github_integration import build_github_integration_smoke, write_github_integration_smoke


ORCHESTRATOR_VERSION = "automix-orchestrator-v1"
DEFAULT_CONFIG_PATH = Path("automix/config/automix_orchestrator_config.json")

WORKFLOW_MODES = {
    "scan_only",
    "real_project_scan_only",
    "recovery_only_pilot",
    "recovery_review",
    "recovery_review_form_only",
    "final_vocal_space_finish",
    "final_placement_adapter_validation",
    "finalize_review_only",
    "placement_validation_only",
    "full_safe_automix",
    "safe_draft",
    "review_package",
    "final_delivery",
    "diagnostic_continue",
}

RECOVERY_REVIEW_GATE_MODES = {
    "recovery_review",
    "recovery_review_form_only",
    "final_vocal_space_finish",
    "final_placement_adapter_validation",
    "finalize_review_only",
    "full_safe_automix",
}

FINAL_VOCAL_SPACE_MODES = {
    "final_vocal_space_finish",
    "final_placement_adapter_validation",
    "finalize_review_only",
    "full_safe_automix",
}

FINAL_PLACEMENT_ADAPTER_VALIDATION_MODES = {
    "final_placement_adapter_validation",
    "placement_validation_only",
    "full_safe_automix",
}

SAFE_FINALIZATION_MODES = FINAL_VOCAL_SPACE_MODES | FINAL_PLACEMENT_ADAPTER_VALIDATION_MODES

GLOBAL_STATUSES = {
    "scan_complete",
    "drafts_created_review_required",
    "blocked_plugin_mapping_required",
    "blocked_stem_required",
    "blocked_manual_review_required",
    "blocked_safety_failure",
    "final_delivery_ready",
    "final_delivery_created",
    "final_delivery_failed",
    "failed",
}


def load_orchestrator_config(path: Path = DEFAULT_CONFIG_PATH, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    config.setdefault("mode", "scan_only")
    config.setdefault("output_dir", "automix")
    config.setdefault("references", [])
    config.setdefault("requested_intents", [])
    config.update({key: value for key, value in (overrides or {}).items() if value is not None})
    if config.get("mode") not in WORKFLOW_MODES:
        config["mode"] = "scan_only"
    if config.get("diagnostic_continue"):
        config["mode"] = "diagnostic_continue"
    if config.get("mode") == "real_project_scan_only":
        config["dry_run"] = True
        config["strict_read_only"] = True
        config["allow_recovery_drafts"] = False
        config["allow_placement_drafts"] = False
        config["allow_reference_match_draft"] = False
        config["allow_premaster_draft"] = False
        config["allow_final_export"] = False
    if config.get("mode") == "recovery_only_pilot":
        config["allow_recovery_drafts"] = True
        config["allow_pitch_correction"] = False
        config["allow_placement_drafts"] = False
        config["allow_reference_match_draft"] = False
        config["allow_premaster_draft"] = False
        config["allow_final_export"] = False
    if config.get("mode") in {"recovery_review", "recovery_review_form_only"}:
        config["allow_recovery_drafts"] = False
        config["allow_pitch_correction"] = False
        config["allow_placement_drafts"] = False
        config["allow_reference_match_draft"] = False
        config["allow_premaster_draft"] = False
        config["allow_final_export"] = False
    if config.get("mode") in SAFE_FINALIZATION_MODES:
        config["dry_run"] = True
        config["strict_final_vocal_space_protection"] = True
        config["allow_recovery_drafts"] = False
        config["allow_pitch_correction"] = False
        config["allow_placement_drafts"] = False
        config["allow_reference_match_draft"] = False
        config["allow_premaster_draft"] = False
        config["allow_final_export"] = False
        if config.get("mode") in {"finalize_review_only", "full_safe_automix"}:
            config["package_review"] = True
    if config.get("mode") == "diagnostic_continue":
        config["allow_recovery_drafts"] = False
        config["allow_pitch_correction"] = False
        config["allow_placement_drafts"] = False
        config["allow_reference_match_draft"] = False
        config["allow_premaster_draft"] = False
        config["allow_final_export"] = False
    return config


class AutoMixOrchestrator:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = load_orchestrator_config(overrides=config or {})
        self.output_dir = Path(self.config.get("output_dir", "automix"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stage_results: list[dict[str, Any]] = []
        self.stage_result_map: dict[str, dict[str, Any]] = {}
        self.context: dict[str, Any] = {}
        self.plugin_audit: dict[str, Any] = {}
        self.source_summary: dict[str, Any] = {}
        self.intent_classification: dict[str, Any] = {}
        self.rollback_registry: dict[str, Any] = {}
        self.global_qc: dict[str, Any] = {}
        self.report_index: dict[str, Any] = {}
        self.resume_state: dict[str, Any] = {}
        self.started_at = ""
        self.finished_at = ""
        self.global_status = "failed"
        self.safe_to_export = False
        self.drafts_created: list[str] = []
        self.renders_created: list[str] = []

    @property
    def mode(self) -> str:
        return str(self.config.get("mode", "scan_only"))

    @property
    def project_name(self) -> str:
        if self.context:
            return str(self.context.get("project_name", "project"))
        project_path = self.config.get("project_path")
        return Path(project_path).stem if project_path else "project"

    def load_project_context(self) -> dict[str, Any]:
        self.context = resolve_project_context(
            project_path=self.config.get("project_path", ""),
            output_dir=self.output_dir,
            target_profile=str(self.config.get("target_profile", "")),
            references=list(self.config.get("references", [])),
        )
        return self.context

    def run_plugin_intelligence(self) -> dict[str, Any]:
        result = start_stage("plugin_intelligence")
        inventory = load_inventory(self.output_dir / "plugin_inventory.json")
        self.plugin_audit = audit_plugin_inventory(inventory, output_dir=self.output_dir)
        report = write_plugin_capability_report(self.plugin_audit, self.output_dir)
        warnings = list(self.plugin_audit.get("warnings", []))
        if self.plugin_audit.get("summary", {}).get("validated_safe_count", 0) == 0:
            warnings.append("no_validated_plugin_adapters_available")
        status = StageStatus.PASSED_WITH_WARNINGS if warnings else StageStatus.PASSED
        return finish_stage(
            result,
            status=status,
            reports=[str(self.output_dir / "analysis_reports/plugin_inventory_audit.json"), str(report)],
            warnings=warnings,
            summary="plugin inventory audit completed without applying FX",
        )

    def run_github_integration_smoke_stage(self) -> dict[str, Any]:
        result = start_stage("github_integration_smoke")
        audio_path = self.config.get("github_integration_audio_path")
        payload = build_github_integration_smoke(
            output_dir=self.output_dir,
            audio_path=Path(audio_path) if audio_path else None,
        )
        paths = write_github_integration_smoke(payload, self.output_dir)
        warnings = list(payload.get("warnings", []))
        return finish_stage(
            result,
            status=StageStatus.PASSED_WITH_WARNINGS if warnings else StageStatus.PASSED,
            reports=[paths["json"], paths["markdown"]],
            warnings=warnings,
            summary="GitHub MCP/reapy integration smoke completed in dry-run mode",
        )

    def run_project_scan(self) -> dict[str, Any]:
        result = start_stage("project_scan", inputs=[str(self.config.get("project_path", ""))])
        if not self.context:
            self.load_project_context()
        warnings = list(self.context.get("warnings", []))
        status = StageStatus.PASSED_WITH_WARNINGS if warnings else StageStatus.PASSED
        return finish_stage(
            result,
            status=status,
            outputs=[str(self.output_dir / "orchestrator/project_context.json")],
            reports=[str(self.output_dir / "orchestrator/project_context.json")],
            warnings=warnings,
            summary=f"{self.context.get('tracks_count', 0)} tracks, {self.context.get('media_items_count', 0)} media items",
        )

    def run_track_role_detection(self) -> dict[str, Any]:
        result = start_stage("track_role_detection")
        roles: list[dict[str, Any]] = []
        for track in self.context.get("track_list", []):
            name = str(track.get("name", "")).lower()
            role = "unknown"
            if "vocal" in name or "lead" in name or "vox" in name:
                role = "vocal_like"
            elif "drum" in name or "kick" in name or "snare" in name:
                role = "drum"
            elif "master" in name or "premaster" in name:
                role = "master_or_premaster"
            elif "ref" in name or "reference" in name or "mix" in name:
                role = "full_mix_or_reference"
            roles.append({"track_index": track.get("track_index"), "name": track.get("name"), "role": role})
        role_map = {
            "schema": "automix-track-role-map-v1",
            "project_name": self.project_name,
            "roles": roles,
            "warnings": ["no_tracks_available_for_role_detection"] if not roles else [],
        }
        path = self.output_dir / "orchestrator" / "track_role_map.json"
        write_json(path, role_map)
        return finish_stage(
            result,
            status=StageStatus.PASSED_WITH_WARNINGS if not roles else StageStatus.PASSED,
            outputs=[str(path)],
            reports=[str(path)],
            warnings=role_map["warnings"],
            summary=f"{len(roles)} tracks role-tagged",
        )

    def run_source_classification(self) -> dict[str, Any]:
        result = start_stage("source_classification")
        role_path = self.output_dir / "orchestrator" / "track_role_map.json"
        roles = json.loads(role_path.read_text(encoding="utf-8")).get("roles", []) if role_path.exists() else []
        vocal_like = [item for item in roles if item.get("role") == "vocal_like"]
        full_mix = [item for item in roles if item.get("role") == "full_mix_or_reference"]
        unknown = [item for item in roles if item.get("role") == "unknown"]
        self.source_summary = {
            "schema": "automix-orchestrator-source-classification-summary-v1",
            "project_name": self.project_name,
            "tracks_total": len(roles),
            "vocal_like_tracks": len(vocal_like),
            "full_mix_unsafe_tracks": len(full_mix),
            "stem_required_tracks": 0,
            "unknown_tracks_skipped": len(unknown),
            "classification_source": "offline_track_name_heuristic",
            "warnings": ["audio_source_classification_not_run_no_track_audio"] if not roles else [],
        }
        path = self.output_dir / "analysis_reports" / "orchestrator_source_classification_summary.json"
        write_json(path, self.source_summary)
        return finish_stage(
            result,
            status=StageStatus.PASSED_WITH_WARNINGS if self.source_summary["warnings"] else StageStatus.PASSED,
            reports=[str(path)],
            warnings=self.source_summary["warnings"],
            summary=f"{len(vocal_like)} vocal-like, {len(full_mix)} full-mix/reference, {len(unknown)} unknown",
        )

    def run_intent_classification_stage(self) -> dict[str, Any]:
        result = start_stage("intent_classification")
        self.intent_classification = build_intent_classification(
            project_name=self.project_name,
            output_dir=self.output_dir,
            target_profile=str(self.config.get("target_profile", "digicore_hyperpop_hiphop_vocal_forward")),
            requested_intents=list(self.config.get("requested_intents", [])),
            source_summary=self.source_summary,
            plugin_audit=self.plugin_audit,
        )
        warnings = list(self.intent_classification.get("warnings", []))
        blockers = list(self.intent_classification.get("blockers", []))
        status = StageStatus.PASSED_WITH_WARNINGS if warnings or blockers else StageStatus.PASSED
        return finish_stage(
            result,
            status=status,
            reports=[
                str(self.output_dir / "eval_reports/intent_classification.json"),
                str(self.output_dir / "eval_reports/intent_classification.md"),
            ],
            warnings=warnings + [f"intent_blocker:{item}" for item in blockers[:8]],
            safe_to_continue=True,
            summary=f"intent={self.intent_classification.get('recommended_primary_intent')} next={self.intent_classification.get('safe_next_mode')}",
        )

    def run_vocal_recovery_stage(self, *, draft: bool = False, evaluation: bool = False) -> dict[str, Any]:
        stage = "vocal_recovery_eval" if evaluation else ("vocal_recovery_draft" if draft else "vocal_recovery_analysis")
        result = start_stage(stage)
        if not draft and not evaluation:
            path = self.output_dir / "analysis_reports" / "orchestrator_vocal_recovery_analysis.json"
            data = {
                "schema": "automix-orchestrator-vocal-recovery-analysis-v1",
                "project_name": self.project_name,
                "tracks_analyzed": self.source_summary.get("vocal_like_tracks", 0),
                "drafts_created": 0,
                "warnings": ["analysis_only_no_audio_recovery_rendered"],
            }
            write_json(path, data)
            return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS, reports=[str(path)], warnings=data["warnings"], summary="recovery analysis report-only")
        if evaluation:
            return skipped_stage(stage, "no recovery draft was created; evaluation skipped")
        if self._analysis_only():
            return skipped_stage(stage, f"{self.mode} mode prevents recovery draft creation")
        if self.mode in {"recovery_review", "recovery_review_form_only"}:
            return skipped_stage(stage, f"{self.mode} mode does not create recovery drafts")
        if self.mode == "final_delivery":
            return skipped_stage(stage, "final_delivery mode does not create recovery drafts")
        if not self.config.get("allow_recovery_drafts", True):
            return skipped_stage(stage, "recovery drafts disabled by config")
        if not self._has_validated_plugins():
            return finish_stage(
                result,
                status=StageStatus.REQUIRES_PLUGIN_MAPPING,
                blockers=["plugin_mapping_required_for_requested_effect"],
                requires_manual_action=True,
                manual_action_type="validate_plugin_mapping",
                safe_to_continue=False,
                summary="validated plugin mapping required before recovery draft",
            )
        return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS, warnings=["draft metadata only; no REAPER project modification"], summary="recovery draft metadata ready")

    def run_recovery_review_gate_stage(self) -> dict[str, Any]:
        result = start_stage("recovery_review_gate")
        if self.mode not in RECOVERY_REVIEW_GATE_MODES:
            return skipped_stage("recovery_review_gate", "recovery review gate not requested")
        from automix.review.recovery_review_gate import run_recovery_review_gate

        summary = run_recovery_review_gate(
            project_path=self.config.get("project_path", ""),
            output_dir=self.output_dir,
            generate_form=True,
            acknowledge_warnings=bool(self.config.get("warnings_acknowledged", False)),
            allow_provisional_without_ab=bool(self.config.get("allow_provisional_without_ab", False)),
            update=bool(self.config.get("update_review_decisions", False)),
        )
        blockers = list(summary.get("errors", [])) + list(summary.get("prompt43_blockers", []))
        status = StageStatus.REQUIRES_MANUAL_REVIEW
        if summary.get("accepted_drafts", 0) > 0 and not blockers:
            status = StageStatus.PASSED_WITH_WARNINGS
        elif blockers:
            status = StageStatus.BLOCKED
        elif summary.get("drafts_to_review", 0) == 0:
            status = StageStatus.PASSED_WITH_WARNINGS
        return finish_stage(
            result,
            status=status,
            reports=[
                str(self.output_dir / "review/recovery_review_state.json"),
                str(self.output_dir / "review/accepted_recovery_sources.json"),
                str(self.output_dir / "orchestrator/downstream_recovery_gate.json"),
                str(self.output_dir / "eval_reports/recovery_review_report.md"),
            ],
            blockers=blockers,
            warnings=summary.get("warnings", []),
            requires_manual_action=status in {StageStatus.REQUIRES_MANUAL_REVIEW, StageStatus.BLOCKED},
            manual_action_type="review_recovery_drafts",
            safe_to_continue=summary.get("accepted_drafts", 0) > 0 and not blockers,
            summary=f"{summary.get('accepted_drafts', 0)} accepted, {summary.get('drafts_to_review', 0)} drafts reviewed",
        )

    def run_final_vocal_space_finish_stage(self) -> dict[str, Any]:
        result = start_stage("final_vocal_space_finish")
        if self.mode not in FINAL_VOCAL_SPACE_MODES:
            return skipped_stage("final_vocal_space_finish", "final vocal space finish not requested")
        from automix.final_vocal_space_finish import run_final_vocal_space_finish

        summary = run_final_vocal_space_finish(
            project_path=self.config.get("project_path", ""),
            output_dir=self.output_dir,
            deliverables_root=self.config.get("deliverables_root", "deliverables"),
            apply_placement_draft=bool(self.config.get("apply_final_vocal_space_placement_draft", False)),
            render_ab=bool(self.config.get("render_ab", False)),
            generate_review_form=True,
            accept_placement_review=bool(self.config.get("accept_placement_review", False)),
            apply_safe_premaster_draft=bool(self.config.get("apply_safe_premaster_draft", False)),
            make_review_package=bool(self.config.get("package_review", False)),
            strict_protection=bool(self.config.get("strict_final_vocal_space_protection", True)),
            dry_run=True,
            verbose=bool(self.config.get("verbose", False)),
        )
        blockers = list(summary.get("blockers", []))
        reports = [str(path) for path in summary.get("reports", {}).values() if path]
        warnings = list(summary.get("warnings", []))
        status = StageStatus.PASSED_WITH_WARNINGS
        manual_action_type = None
        if any("plugin_adapter" in blocker for blocker in blockers):
            status = StageStatus.REQUIRES_PLUGIN_MAPPING
            manual_action_type = "validate_plugin_mapping"
        elif "no_accepted_recovery_sources" in blockers:
            status = StageStatus.REQUIRES_MANUAL_REVIEW
            manual_action_type = "review_recovery_drafts"
        elif blockers:
            status = StageStatus.BLOCKED
        elif not summary.get("ab_evaluation_passed", False):
            warnings.append("final_vocal_space_ab_review_required_before_any_application")
            manual_action_type = "manual_mix_revision"
        safe_to_continue = status.value in {StageStatus.PASSED.value, StageStatus.PASSED_WITH_WARNINGS.value}
        return finish_stage(
            result,
            status=status,
            reports=reports,
            warnings=warnings,
            blockers=blockers,
            requires_manual_action=bool(manual_action_type),
            manual_action_type=manual_action_type,
            safe_to_continue=safe_to_continue,
            summary=f"final vocal space dry-run: {summary.get('final_recommendation', 'review_required')}",
        )

    def run_final_placement_adapter_validation_stage(self) -> dict[str, Any]:
        result = start_stage("final_placement_adapter_validation")
        if self.mode not in FINAL_PLACEMENT_ADAPTER_VALIDATION_MODES:
            return skipped_stage("final_placement_adapter_validation", "final placement adapter validation not requested")
        from automix.plugins.final_placement_adapter_mapping import validate_final_placement_adapters

        chain_plan = self.config.get("final_vocal_space_chain_plan_path") or self.output_dir / "chain_plans/final_vocal_space_carving_chain_plan.json"
        inventory = self.config.get("plugin_inventory_path") or self.output_dir / "plugin_inventory.json"
        report = validate_final_placement_adapters(
            output_dir=self.output_dir,
            chain_plan_path=chain_plan,
            inventory_path=inventory,
            min_confidence=float(self.config.get("adapter_min_confidence", 0.85)),
            allow_offline_validated_adapters=bool(self.config.get("allow_offline_validated_adapters", False)),
            generate_applicator_plan=True,
        )
        blockers = list(report.get("blocked_reasons", []))
        reports = [
            str(self.output_dir / "eval_reports/final_placement_adapter_mapping_report.json"),
            str(self.output_dir / "eval_reports/final_placement_adapter_mapping_report.md"),
            str(self.output_dir / "logs/final_placement_adapter_validation_log.json"),
        ]
        outputs = [
            str(self.output_dir / "chain_plans/final_vocal_space_applicator_plan.json"),
            str(self.output_dir / "chain_plans/final_vocal_space_applicator_plan.lua"),
        ]
        if not blockers and report.get("apply_allowed"):
            status = StageStatus.PASSED_WITH_WARNINGS
            manual_action_type = "manual_mix_revision"
            warnings = ["applicator plan is validated but still requires manual REAPER review before use"]
        elif any(reason.endswith("_adapter_not_validated") for reason in blockers):
            status = StageStatus.REQUIRES_PLUGIN_MAPPING
            manual_action_type = "validate_plugin_mapping"
            warnings = list(report.get("warnings", []))
        else:
            status = StageStatus.BLOCKED
            manual_action_type = None
            warnings = list(report.get("warnings", []))
        return finish_stage(
            result,
            status=status,
            outputs=outputs,
            reports=reports,
            warnings=warnings,
            blockers=blockers,
            requires_manual_action=bool(manual_action_type),
            manual_action_type=manual_action_type,
            safe_to_continue=bool(report.get("apply_allowed", False)),
            summary=f"adapter validation apply_allowed={bool(report.get('apply_allowed', False))}",
        )

    def run_pitch_stage(self, *, draft: bool = False, evaluation: bool = False) -> dict[str, Any]:
        stage = "pitch_eval" if evaluation else ("pitch_draft" if draft else "pitch_triage")
        result = start_stage(stage)
        if not self.config.get("allow_pitch_correction", True):
            return skipped_stage(stage, "pitch correction disabled by --no-pitch or config")
        if not draft and not evaluation:
            warnings = ["pitch_triage_report_only_no_audio"] if self.source_summary.get("tracks_total", 0) == 0 else []
            if self.source_summary.get("full_mix_unsafe_tracks", 0) and not self.config.get("allow_full_mix_pitch_experiment", False):
                return finish_stage(
                    result,
                    status=StageStatus.REQUIRES_STEM,
                    blockers=["full_mix_detected_for_pitch_correction"],
                    warnings=warnings,
                    requires_manual_action=True,
                    manual_action_type="provide_isolated_vocal_stem",
                    safe_to_continue=False,
                    summary="full-mix/reference track detected; isolated stem required for pitch",
                )
            path = self.output_dir / "analysis_reports" / "orchestrator_pitch_triage_summary.json"
            write_json(path, {"schema": "automix-orchestrator-pitch-triage-v1", "warnings": warnings, "pitch_drafts_created": 0})
            return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS if warnings else StageStatus.PASSED, reports=[str(path)], warnings=warnings, summary="pitch triage report-only")
        if evaluation:
            return skipped_stage(stage, "no pitch draft was created; evaluation skipped")
        if self.mode == "final_delivery":
            return skipped_stage(stage, "final_delivery mode does not create pitch drafts")
        if self._analysis_only():
            return skipped_stage(stage, f"{self.mode} mode prevents pitch draft creation")
        if not self._has_validated_plugins():
            return finish_stage(
                result,
                status=StageStatus.REQUIRES_PLUGIN_MAPPING,
                blockers=["plugin_mapping_required_for_requested_effect"],
                requires_manual_action=True,
                manual_action_type="validate_plugin_mapping",
                safe_to_continue=False,
                summary="validated pitch adapter required before pitch draft",
            )
        return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS, warnings=["draft metadata only; no REAPER project modification"], summary="pitch draft metadata ready")

    def run_vocal_placement_stage(self, *, draft: bool = False, evaluation: bool = False) -> dict[str, Any]:
        stage = "vocal_placement_eval" if evaluation else ("vocal_placement_draft" if draft else "vocal_placement_analysis")
        result = start_stage(stage)
        if not draft and not evaluation:
            path = self.output_dir / "analysis_reports" / "orchestrator_vocal_placement_analysis.json"
            write_json(path, {"schema": "automix-orchestrator-vocal-placement-analysis-v1", "warnings": ["placement analysis report-only"]})
            return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS, reports=[str(path)], warnings=["placement analysis report-only"], summary="placement analysis report-only")
        if evaluation:
            return skipped_stage(stage, "no placement draft was created; evaluation skipped")
        if self._analysis_only():
            return skipped_stage(stage, f"{self.mode} mode prevents placement draft creation")
        if self.mode == "final_delivery":
            return skipped_stage(stage, "final_delivery mode does not create placement drafts")
        if not self.config.get("allow_placement_drafts", True):
            return skipped_stage(stage, "placement drafts disabled by config")
        if not self._has_validated_plugins():
            return finish_stage(result, status=StageStatus.REQUIRES_PLUGIN_MAPPING, blockers=["plugin_mapping_required_for_requested_effect"], requires_manual_action=True, manual_action_type="validate_plugin_mapping", safe_to_continue=False, summary="validated plugin mapping required before placement draft")
        return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS, warnings=["draft metadata only; no REAPER project modification"], summary="placement draft metadata ready")

    def run_reference_match_stage(self, *, draft: bool = False, evaluation: bool = False) -> dict[str, Any]:
        stage = "reference_match_eval" if evaluation else ("reference_match_draft" if draft else "reference_match_analysis")
        result = start_stage(stage)
        refs = list(self.config.get("references", []))
        if not draft and not evaluation:
            path = self.output_dir / "analysis_reports" / "orchestrator_reference_match_analysis.json"
            warnings = [] if refs else ["no_reference_audio_provided_target_profile_only"]
            write_json(path, {"schema": "automix-orchestrator-reference-analysis-v1", "references": refs, "target_profile": self.config.get("target_profile"), "warnings": warnings})
            return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS if warnings else StageStatus.PASSED, reports=[str(path)], warnings=warnings, summary=f"{len(refs)} references available")
        if evaluation:
            return skipped_stage(stage, "no reference-match draft was created; evaluation skipped")
        if self.mode == "final_delivery":
            return skipped_stage(stage, "final_delivery mode does not create reference-match drafts")
        if self._analysis_only() or not self.config.get("allow_reference_match_draft", False):
            return skipped_stage(stage, "reference match draft disabled by mode or config")
        return finish_stage(result, status=StageStatus.REQUIRES_MANUAL_REVIEW, blockers=["reference_match_draft_requires_manual_review"], requires_manual_action=True, manual_action_type="manual_mix_revision", safe_to_continue=False, summary="reference match draft requires manual review")

    def run_premaster_stage(self, *, draft: bool = False, evaluation: bool = False) -> dict[str, Any]:
        stage = "premaster_eval" if evaluation else ("premaster_draft" if draft else "premaster_analysis")
        result = start_stage(stage)
        if not draft and not evaluation:
            path = self.output_dir / "analysis_reports" / "orchestrator_premaster_analysis.json"
            write_json(path, {"schema": "automix-orchestrator-premaster-analysis-v1", "warnings": ["source_mix_not_supplied_report_only"]})
            return finish_stage(result, status=StageStatus.PASSED_WITH_WARNINGS, reports=[str(path)], warnings=["source_mix_not_supplied_report_only"], summary="premaster analysis report-only")
        if evaluation:
            return skipped_stage(stage, "no premaster draft was created; evaluation skipped")
        if self._analysis_only():
            return skipped_stage(stage, f"{self.mode} mode prevents premaster draft creation")
        if self.mode == "final_delivery":
            return skipped_stage(stage, "final_delivery mode does not create premaster drafts")
        if not self.config.get("allow_premaster_draft", True):
            return skipped_stage(stage, "premaster draft disabled by config")
        return finish_stage(result, status=StageStatus.REQUIRES_MANUAL_REVIEW, blockers=["accepted_mix_or_placement_required_before_premaster"], requires_manual_action=True, manual_action_type="manual_mastering_required", safe_to_continue=False, summary="accepted source mix required before premaster draft")

    def run_final_export_stage(self, *, resolver: bool = False, qc: bool = False, package: bool = False) -> dict[str, Any]:
        stage = "final_export_state_resolver" if resolver else ("final_qc" if qc else ("deliverable_package" if package else "final_export"))
        result = start_stage(stage)
        if resolver:
            state = resolve_final_export_state(project_name=self.project_name, workflow_state={}, output_dir=self.output_dir, output_path=self.output_dir / "export" / "final_export_state.json")
            status = StageStatus.REQUIRES_APPROVAL if self.mode == "final_delivery" and not self.config.get("final_approval_explicit") else StageStatus.PASSED_WITH_WARNINGS
            final_requested = self.mode == "final_delivery" or bool(self.config.get("allow_final_export"))
            blockers = ["final_approval_missing"] if status == StageStatus.REQUIRES_APPROVAL else (state.get("blocked_reasons", []) if final_requested else [])
            return finish_stage(result, status=status, reports=[str(self.output_dir / "export/final_export_state.json")], warnings=state.get("blocked_reasons", []), blockers=blockers, requires_manual_action=status == StageStatus.REQUIRES_APPROVAL, manual_action_type="approve_human_review" if status == StageStatus.REQUIRES_APPROVAL else None, safe_to_continue=status != StageStatus.REQUIRES_APPROVAL, summary="final export source resolution completed")
        if qc:
            return skipped_stage(stage, "final output missing; QC skipped", manual_action_type="rerun_ab_render" if self.mode == "final_delivery" else None)
        if package:
            return skipped_stage(stage, "deliverable package blocked until final QC and approval pass", manual_action_type="approve_human_review" if self.mode == "final_delivery" else None)
        if self.mode != "final_delivery" and not self.config.get("allow_final_export", False):
            return skipped_stage(stage, "final export disabled by default")
        if not self.config.get("final_approval_explicit"):
            return finish_stage(result, status=StageStatus.REQUIRES_APPROVAL, blockers=["final_approval_missing"], requires_manual_action=True, manual_action_type="approve_human_review", safe_to_continue=False, summary="final export requires explicit approval")
        return finish_stage(result, status=StageStatus.BLOCKED, blockers=["no_accepted_export_source", "qc_failure_for_final_delivery"], requires_manual_action=True, manual_action_type="approve_human_review", safe_to_continue=False, summary="final export blocked because no approved QC-passed source exists")

    def run_global_qc(self) -> dict[str, Any]:
        self.global_qc = build_global_qc_summary(
            project_name=self.project_name,
            output_dir=self.output_dir,
            stage_results=self.stage_results,
            final_delivery_requested=self.mode == "final_delivery" or bool(self.config.get("allow_final_export")),
        )
        self.safe_to_export = bool(self.global_qc.get("safe_to_export"))
        return self.global_qc

    def run_professional_readiness_audit_stage(self) -> dict[str, Any]:
        result = start_stage("professional_readiness_audit")
        final_requested = self.mode == "final_delivery" or bool(self.config.get("allow_final_export"))
        self.global_qc = build_global_qc_summary(
            project_name=self.project_name,
            output_dir=self.output_dir,
            stage_results=self.stage_results,
            final_delivery_requested=final_requested,
        )
        audit = build_professional_readiness_audit(
            project_name=self.project_name,
            output_dir=self.output_dir,
            workspace_root=Path.cwd(),
            final_delivery_requested=final_requested,
        )
        reports = [
            str(self.output_dir / "eval_reports/professional_readiness_audit.json"),
            str(self.output_dir / "eval_reports/professional_readiness_audit.md"),
        ]
        if audit.get("ready_for_delivery"):
            status = StageStatus.PASSED
            manual_action_type = None
            safe_to_continue = True
        elif final_requested:
            status = StageStatus.BLOCKED
            manual_action_type = "approve_human_review"
            safe_to_continue = False
        else:
            status = StageStatus.PASSED_WITH_WARNINGS
            manual_action_type = None
            safe_to_continue = True
        return finish_stage(
            result,
            status=status,
            reports=reports,
            warnings=audit.get("warnings", []),
            blockers=audit.get("blockers", []) if final_requested else [],
            requires_manual_action=bool(manual_action_type),
            manual_action_type=manual_action_type,
            safe_to_continue=safe_to_continue,
            summary=f"professional readiness: {audit.get('readiness_status')}",
        )

    def write_orchestration_manifest(self) -> dict[str, Any]:
        reports_created = sorted(set(path for result in self.stage_results for path in result.get("reports", [])))
        failures = sorted(set(item for result in self.stage_results for item in result.get("failures", [])))
        warnings = sorted(set(item for result in self.stage_results for item in result.get("warnings", [])))
        blockers = sorted(set(item for result in self.stage_results for item in result.get("blockers", [])))
        self.global_status = global_status_from_results(self.mode, self.stage_results, self.safe_to_export)
        safety = evaluate_workflow_continuation(mode=self.mode, stage_results=self.stage_results, config=self.config)
        next_actions = next_actions_from_results(self.stage_results, safety.get("hard_blockers", []) + blockers)
        manifest = {
            "schema": ORCHESTRATOR_VERSION,
            "project_name": self.project_name,
            "project_path": str(self.config.get("project_path", "")),
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self._duration_seconds(),
            "target_profile": self.config.get("target_profile"),
            "references": self.config.get("references", []),
            "stage_results": self.stage_results,
            "global_status": self.global_status if self.global_status in GLOBAL_STATUSES else "failed",
            "safe_to_export": self.safe_to_export,
            "drafts_created": self.drafts_created,
            "renders_created": self.renders_created,
            "reports_created": reports_created,
            "rollback_registry": str(self.output_dir / "rollback/global_rollback_registry.json"),
            "next_required_actions": next_actions,
            "warnings": warnings,
            "failures": failures,
        }
        write_json(self.output_dir / "orchestrator" / "automix_orchestration_manifest.json", manifest)
        return manifest

    def write_orchestration_report(self, manifest: dict[str, Any]) -> Path:
        audit_summary = self.plugin_audit.get("summary", {})
        unsafe_plugins = self.plugin_audit.get("unsafe_or_unmapped_plugins", [])
        source = self.source_summary or {}
        intent = self.intent_classification or {}
        rollback = self.rollback_registry or {}
        final_recommendation = self._final_recommendation(manifest)
        lines = [
            "# AutoMix Orchestration Report",
            "",
            "## Summary",
            "",
            f"- Project: `{manifest.get('project_name')}`",
            f"- Mode: `{manifest.get('mode')}`",
            f"- Target profile: `{manifest.get('target_profile')}`",
            f"- References: `{len(manifest.get('references', []))}`",
            f"- Global status: `{manifest.get('global_status')}`",
            f"- Safe to export: `{manifest.get('safe_to_export')}`",
            f"- Drafts created: `{len(manifest.get('drafts_created', []))}`",
            "- Final package: `not created`",
            "",
            "## Stage Results",
            "",
            "| Stage | Status | Key output | Warnings | Required action |",
            "|---|---|---|---|---|",
        ]
        for result in self.stage_results:
            key_output = result.get("summary") or ", ".join(result.get("outputs", [])[:1])
            warnings = "; ".join(result.get("warnings", [])[:3])
            action = result.get("manual_action_type") or ""
            lines.append(f"| `{result.get('stage')}` | `{result.get('status')}` | {key_output} | {warnings} | `{action}` |")
        lines.extend(
            [
                "",
                "## Plugin Safety",
                "",
                f"- Safe adapters: `{audit_summary.get('validated_safe_count', 0)}`",
                f"- Provisional adapters: `{audit_summary.get('detected_count', 0) - audit_summary.get('validated_safe_count', 0)}`",
                f"- Unsafe/unmapped plugins: `{len(unsafe_plugins)}`",
                "- Fallback strategy: `stock/JSFX or manual review only after adapter validation`",
                "",
                "## Source / Track Summary",
                "",
                f"- Total tracks: `{source.get('tracks_total', self.context.get('tracks_count', 0))}`",
                f"- Vocal-like tracks: `{source.get('vocal_like_tracks', 0)}`",
                f"- Full-mix unsafe tracks: `{source.get('full_mix_unsafe_tracks', 0)}`",
                f"- Stem-required tracks: `{source.get('stem_required_tracks', 0)}`",
                f"- Unknown tracks skipped: `{source.get('unknown_tracks_skipped', 0)}`",
                "",
                "## Intent Classification",
                "",
                f"- Status: `{intent.get('status', 'not_run')}`",
                f"- Recommended primary intent: `{intent.get('recommended_primary_intent', '')}`",
                f"- Safe next mode: `{intent.get('safe_next_mode', '')}`",
                f"- Safe draft intents: `{', '.join(intent.get('safe_draft_intents', [])) or 'none'}`",
                f"- Dry-run only: `{intent.get('dry_run_only', True)}`",
                "",
                "## Vocal Recovery",
                "",
                "- Tracks analyzed: `" + str(source.get("vocal_like_tracks", 0)) + "`",
                "- Drafts created: `0`",
                "- Accepted: `0`",
                "- Rejected: `0`",
                "- Manual review required: `" + str(any(r.get("stage") == "vocal_recovery_draft" and r.get("requires_manual_action") for r in self.stage_results)) + "`",
                "",
                "## Pitch Correction",
                "",
                "- Tracks triaged: `" + str(source.get("tracks_total", 0)) + "`",
                "- Pitch drafts created: `0`",
                "- Skipped: `" + str(self._stage_status("pitch_draft") == StageStatus.SKIPPED.value) + "`",
                "- Full mix unsafe: `" + str(source.get("full_mix_unsafe_tracks", 0)) + "`",
                "- Already tuned skipped: `0`",
                "- Stem required: `" + str(self._stage_status("pitch_triage") == StageStatus.REQUIRES_STEM.value) + "`",
                "- Manual tuning required: `" + str(self._stage_status("pitch_draft") == StageStatus.REQUIRES_PLUGIN_MAPPING.value) + "`",
                "",
                "## Vocal Placement",
                "",
                "- Placement drafts: `0`",
                "- A/B status: `not rendered`",
                "- Accepted: `0`",
                "- Rejected: `0`",
                "- Manual review required: `" + str(self._stage_status("vocal_placement_draft") == StageStatus.REQUIRES_PLUGIN_MAPPING.value) + "`",
                "",
                "## Final Vocal Space",
                "",
                f"- Finish stage: `{self._stage_status('final_vocal_space_finish')}`",
                f"- Adapter validation: `{self._stage_status('final_placement_adapter_validation')}`",
                "- Reaper application: `not run by orchestrator`",
                "- Final export: `blocked until review and QC`",
                "",
                "## Reference Matching",
                "",
                f"- Target profile: `{manifest.get('target_profile')}`",
                f"- References used: `{len(manifest.get('references', []))}`",
                "- Safe adjustments: `0`",
                "- Blocked adjustments: `0`",
                f"- Draft status: `{self._stage_status('reference_match_draft')}`",
                "",
                "## Premaster",
                "",
                f"- Premaster draft: `{self._stage_status('premaster_draft')}`",
                "- Loudness: `not measured`",
                "- True peak: `not measured`",
                f"- Translation check: `{self._stage_status('translation_check')}`",
                f"- Status: `{self._stage_status('premaster_analysis')}`",
                "",
                "## Final Export",
                "",
                "- Export source: `none`",
                f"- Approval: `{self.config.get('final_approval_explicit', False)}`",
                f"- QC: `{self.global_qc.get('overall_qc_status', 'review_required')}`",
                "- Package: `not created`",
                f"- Status: `{self._stage_status('final_export')}`",
                "",
                "## Rollback",
                "",
                f"- Rollback registry: `{manifest.get('rollback_registry')}`",
                f"- Original tracks protected: `{rollback.get('original_tracks_protected', True)}`",
                f"- Original master protected: `{rollback.get('original_master_protected', True)}`",
                f"- Safe to rollback: `{rollback.get('validation', {}).get('passed', False)}`",
                "",
                "## Next Required Actions",
                "",
            ]
        )
        for action in manifest.get("next_required_actions", []):
            lines.append(f"- {action}")
        lines.extend(["", "## Final Recommendation", "", f"`{final_recommendation}`", ""])
        path = self.output_dir / "eval_reports" / "automix_orchestration_report.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def run(self) -> dict[str, Any]:
        self.started_at = now_utc()
        self._monotonic_start = time.monotonic()
        self.resume_state = build_resume_state(project_path=self.config.get("project_path", ""), output_dir=self.output_dir)
        self.load_project_context()

        for stage in STAGE_ORDER:
            can_run, dep_failures = can_run_stage(stage, self.stage_result_map, mode=self.mode)
            if not can_run:
                result = finish_stage(
                    start_stage(stage),
                    status=StageStatus.BLOCKED,
                    blockers=dep_failures,
                    safe_to_continue=self.mode in {"scan_only", "diagnostic_continue"},
                    summary="blocked by dependency graph",
                )
            else:
                result = self._dispatch_stage(stage)
            self.stage_results.append(result)
            self.stage_result_map[stage] = result

        applied = [result["stage"] for result in self.stage_results if result.get("stage") in APPLIED_STAGES and result.get("status") in {StageStatus.PASSED.value, StageStatus.PASSED_WITH_WARNINGS.value}]
        self.rollback_registry = build_global_rollback_registry(project_name=self.project_name, output_dir=self.output_dir, applied_stages=applied)
        self.run_global_qc()
        self.finished_at = now_utc()
        manifest = self.write_orchestration_manifest()
        report_path = self.write_orchestration_report(manifest)
        current_state = build_current_state_summary(
            project_name=self.project_name,
            output_dir=self.output_dir,
            manifest=manifest,
            global_qc=self.global_qc,
            report_count=len(manifest.get("reports_created", [])),
        )
        current_state_paths = write_current_state_summary(current_state, self.output_dir)
        self.report_index = build_report_index(project_name=self.project_name, output_dir=self.output_dir, stage_results=self.stage_results)
        manifest["reports_created"] = sorted(
            set(
                manifest.get("reports_created", [])
                + [
                    str(report_path),
                    current_state_paths["json"],
                    current_state_paths["markdown"],
                    str(self.output_dir / "eval_reports/automix_report_index.json"),
                    str(self.output_dir / "eval_reports/global_qc_summary.json"),
                ]
            )
        )
        write_json(self.output_dir / "orchestrator" / "automix_orchestration_manifest.json", manifest)
        return manifest

    def _dispatch_stage(self, stage: str) -> dict[str, Any]:
        handlers: dict[str, Callable[[], dict[str, Any]]] = {
            "plugin_intelligence": self.run_plugin_intelligence,
            "github_integration_smoke": self.run_github_integration_smoke_stage,
            "project_scan": self.run_project_scan,
            "track_role_detection": self.run_track_role_detection,
            "source_classification": self.run_source_classification,
            "intent_classification": self.run_intent_classification_stage,
            "vocal_recovery_analysis": lambda: self.run_vocal_recovery_stage(),
            "vocal_recovery_draft": lambda: self.run_vocal_recovery_stage(draft=True),
            "vocal_recovery_eval": lambda: self.run_vocal_recovery_stage(evaluation=True),
            "recovery_review_gate": self.run_recovery_review_gate_stage,
            "final_vocal_space_finish": self.run_final_vocal_space_finish_stage,
            "final_placement_adapter_validation": self.run_final_placement_adapter_validation_stage,
            "pitch_triage": lambda: self.run_pitch_stage(),
            "pitch_draft": lambda: self.run_pitch_stage(draft=True),
            "pitch_eval": lambda: self.run_pitch_stage(evaluation=True),
            "vocal_placement_analysis": lambda: self.run_vocal_placement_stage(),
            "vocal_placement_draft": lambda: self.run_vocal_placement_stage(draft=True),
            "vocal_placement_eval": lambda: self.run_vocal_placement_stage(evaluation=True),
            "reference_match_analysis": lambda: self.run_reference_match_stage(),
            "reference_match_draft": lambda: self.run_reference_match_stage(draft=True),
            "reference_match_eval": lambda: self.run_reference_match_stage(evaluation=True),
            "premaster_analysis": lambda: self.run_premaster_stage(),
            "premaster_draft": lambda: self.run_premaster_stage(draft=True),
            "premaster_eval": lambda: self.run_premaster_stage(evaluation=True),
            "translation_check": lambda: skipped_stage("translation_check", "no premaster draft; translation check skipped"),
            "final_export_state_resolver": lambda: self.run_final_export_stage(resolver=True),
            "final_export": lambda: self.run_final_export_stage(),
            "final_qc": lambda: self.run_final_export_stage(qc=True),
            "deliverable_package": lambda: self.run_final_export_stage(package=True),
            "professional_readiness_audit": self.run_professional_readiness_audit_stage,
        }
        try:
            return handlers[stage]()
        except Exception as exc:
            return finish_stage(start_stage(stage), status=StageStatus.FAILED, failures=[type(exc).__name__], blockers=[str(exc)], safe_to_continue=False, summary="stage failed")

    def _analysis_only(self) -> bool:
        return self.mode in {"scan_only", "real_project_scan_only", "diagnostic_continue"} or bool(self.config.get("dry_run", False))

    def _has_validated_plugins(self) -> bool:
        return self.plugin_audit.get("summary", {}).get("validated_safe_count", 0) > 0

    def _duration_seconds(self) -> float:
        start = getattr(self, "_monotonic_start", time.monotonic())
        return round(max(0.0, time.monotonic() - start), 6)

    def _stage_status(self, stage: str) -> str:
        return str(self.stage_result_map.get(stage, {}).get("status", "not_started"))

    def _final_recommendation(self, manifest: dict[str, Any]) -> str:
        status = manifest.get("global_status")
        if status == "scan_complete":
            return "scan_review_required"
        if status == "blocked_plugin_mapping_required":
            return "validate_plugins"
        if status == "blocked_stem_required":
            return "provide_stems"
        if status == "drafts_created_review_required":
            return "review_drafts_before_use"
        if status == "final_delivery_ready":
            return "final_delivery_ready"
        if manifest.get("safe_to_export"):
            return "ready_for_final_export"
        if status == "blocked_manual_review_required":
            return "manual_mix_revision_required"
        return "unsafe_to_continue"
