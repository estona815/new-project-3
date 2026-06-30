"""Plugin intelligence safety layer for the REAPER AutoMix workflow.

The modules in this package deliberately stop short of applying FX. They build
inventory, adapter, validation, and parameter-write metadata so later REAPER
automation can fail closed when a plugin or semantic control is uncertain.
"""

__all__ = [
    "adapter_confidence_gate",
    "plugin_adapter_schema",
    "plugin_availability_decision_gate",
    "plugin_availability_operator_decision_package",
    "plugin_availability_resolution_plan",
    "plugin_inventory_audit",
    "plugin_parameter_learner",
    "plugin_parameter_validator",
    "plugin_semantic_validation_collection_plan",
    "plugin_semantic_validation_queue",
    "plugin_semantic_validation_runtime_collection_package",
    "plugin_semantic_validation_runtime_collector_package",
    "plugin_semantic_validation_runtime_evidence_gate",
    "plugin_semantic_validation_runtime_observation_provenance_gate",
    "plugin_semantic_validation_runtime_report_authoring_gate",
    "plugin_semantic_validation_runtime_observation_gate",
    "plugin_semantic_validation_runtime_report_authoring_package",
    "plugin_validation_action_plan",
    "preset_safety",
    "reaper_runtime_collection_operator_readiness_gate",
    "reaper_runtime_collector_safety_audit",
    "safe_parameter_writer",
    "third_party_plugin_policy",
]
