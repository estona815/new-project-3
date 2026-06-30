from __future__ import annotations

from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, control_is_write_safe, safe_float


EXPECTED_THIRD_PARTY = [
    "MAutoPitch",
    "TDR Nova",
    "Decapitator",
    "Valhalla Supermassive",
    "Valhalla reverb/delay",
    "OTT",
    "Ozone",
    "Soothe-like resonance suppressor",
    "DSEQ-like resonance suppressor",
]

FAMILY_ALIASES: dict[str, list[str]] = {
    "mautopitch": ["mautopitch", "meldaproductionmautopitch"],
    "tdr_nova": ["tdrnova", "tokyodawnnova", "nova"],
    "decapitator": ["decapitator", "soundtoysdecapitator"],
    "valhalla": ["valhalla", "valhallasupermassive", "supermassive", "valhallavintageverb", "valhallaroom", "valhallaplate"],
    "ott": ["ott", "xferott", "xferrecordsott"],
    "ozone": ["ozone", "izotopeozone"],
    "soothe_type": ["soothe", "soothe2", "oeksoundsoothe"],
    "dseq_type": ["dseq", "tbproaudiodseq"],
    "melodyne_type": ["melodyne", "celemonymelodyne"],
    "autotune_type": ["autotune", "antaresautotune", "autotuneartist", "autotunepro"],
}

FAMILY_REQUIREMENTS: dict[str, list[str]] = {
    "mautopitch": ["correction_amount", "speed", "dry_wet"],
    "tdr_nova": ["dynamic_eq_amount", "frequency_hz", "gain_db", "q"],
    "decapitator": ["saturation_amount", "dry_wet", "output_gain"],
    "valhalla": ["dry_wet", "decay", "high_cut_hz"],
    "ott": ["amount", "depth", "dry_wet", "output_gain"],
    "ozone": ["limiter_ceiling_dbTP", "limiter_max_gain_db", "true_peak_enable"],
    "soothe_type": ["dynamic_eq_amount", "dry_wet"],
    "dseq_type": ["dynamic_eq_amount", "dry_wet"],
    "autotune_type": ["correction_amount", "speed", "dry_wet"],
    "melodyne_type": [],
}

MANUAL_ONLY_FAMILIES = {"melodyne_type", "autotune_type", "soothe_type", "dseq_type"}


def plugin_family(plugin_name: str | None) -> str | None:
    compact = compact_plugin_name(plugin_name)
    if not compact:
        return None
    for family, aliases in FAMILY_ALIASES.items():
        if any(alias and (alias in compact or compact in alias) for alias in aliases):
            return family
    return None


def is_third_party_plugin(plugin_name: str | None) -> bool:
    return plugin_family(plugin_name) is not None


def _safe_controls(adapter: dict[str, Any] | None, min_confidence: float) -> set[str]:
    if not isinstance(adapter, dict):
        return set()
    out: set[str] = set()
    for semantic, control in adapter.get("semantic_controls", {}).items():
        if isinstance(control, dict) and control_is_write_safe(control, min_confidence):
            out.add(semantic)
    return out


def evaluate_third_party_policy(
    plugin_name: str | None,
    adapter: dict[str, Any] | None = None,
    *,
    source_context: dict[str, Any] | None = None,
    min_confidence: float = 0.90,
) -> dict[str, Any]:
    family = plugin_family(plugin_name)
    source_context = source_context or {}
    warnings: list[str] = []
    reason_codes: list[str] = []
    required = FAMILY_REQUIREMENTS.get(family or "", [])
    safe_controls = _safe_controls(adapter, min_confidence)
    missing = [semantic for semantic in required if semantic not in safe_controls]

    if not family:
        return {
            "family": "unknown_or_stock",
            "third_party": False,
            "allowed": True,
            "write_allowed": True,
            "required_controls": [],
            "missing_controls": [],
            "reason_codes": [],
            "fallback_required": False,
            "warnings": [],
        }

    if family in MANUAL_ONLY_FAMILIES:
        reason_codes.append("THIRD_PARTY_MANUAL_ONLY")
        warnings.append(f"{plugin_name} is treated as manual-only until a dedicated validated adapter exists.")

    if not isinstance(adapter, dict):
        reason_codes.append("ADAPTER_MISSING")
    elif adapter.get("validation", {}).get("status") != "passed":
        reason_codes.append("VALIDATION_MISSING")
    elif safe_float(adapter.get("confidence"), 0.0) < min_confidence:
        reason_codes.append("ADAPTER_CONFIDENCE_LOW")

    if missing:
        reason_codes.append("SEMANTIC_CONTROL_MISSING")
        warnings.append(f"Missing validated semantic controls for {plugin_name}: {', '.join(missing)}")

    if family == "ott" and (
        source_context.get("compressed_source") or safe_float(source_context.get("limiter_pressure_risk"), 0.0) > 0.45
    ):
        reason_codes.append("SOURCE_ALREADY_COMPRESSED")
        warnings.append("OTT-style processing is blocked on compressed or already limited sources.")

    if family == "ozone" and source_context.get("master_bus_original"):
        reason_codes.append("ORIGINAL_MASTER_BUS_BLOCKED")
        warnings.append("Ozone-style mastering control is allowed only on draft premaster copies.")

    allowed = not reason_codes
    return {
        "family": family,
        "third_party": True,
        "allowed": allowed,
        "write_allowed": allowed,
        "required_controls": required,
        "missing_controls": missing,
        "reason_codes": reason_codes,
        "fallback_required": not allowed,
        "warnings": warnings,
    }
