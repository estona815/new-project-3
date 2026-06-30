from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import (
    create_adapter,
    default_semantic_control,
    now_utc,
    safe_float,
    slugify,
    write_json,
)


PROVISIONAL_LEARNER_VERSION = "automix-plugin-parameter-learner-v1"

DO_NOT_TOUCH_HINTS = [
    "bypass",
    "enable",
    "preset",
    "random",
    "learn",
    "midi",
    "cc",
    "license",
    "activation",
    "oversampling",
    "quality",
    "mode",
    "a/b",
    "compare",
]

SEMANTIC_HINTS: list[tuple[str, list[str], float]] = [
    ("correction_amount", ["correction amount", "correction", "tune amount", "pitch amount"], 0.78),
    ("speed", ["retune speed", "speed", "response"], 0.78),
    ("depth", ["depth", "strength"], 0.72),
    ("formant_preserve", ["formant", "formant preserve"], 0.76),
    ("humanize", ["humanize", "humanise"], 0.76),
    ("vibrato_preserve", ["vibrato"], 0.70),
    ("dry_wet", ["dry/wet", "dry wet", "mix", "wet"], 0.74),
    ("output_gain", ["output", "output gain", "makeup", "make-up"], 0.72),
    ("input_trim_db", ["input", "input trim", "trim"], 0.70),
    ("threshold_db", ["threshold"], 0.74),
    ("ratio", ["ratio"], 0.72),
    ("attack_ms", ["attack"], 0.74),
    ("release_ms", ["release"], 0.74),
    ("frequency_hz", ["frequency", "freq", "hz"], 0.70),
    ("gain_db", ["gain", "band gain"], 0.70),
    ("q", ["q", "bandwidth"], 0.70),
    ("low_cut_hz", ["low cut", "high pass", "hipass", "hp freq"], 0.76),
    ("high_cut_hz", ["high cut", "low pass", "lopass", "lp freq"], 0.76),
    ("dynamic_eq_amount", ["dynamic amount", "dyn amount", "range"], 0.70),
    ("deesser_amount", ["de ess", "de-ess", "sibilance"], 0.72),
    ("saturation_amount", ["saturation", "drive", "distortion"], 0.68),
    ("clipper_drive_db", ["clip", "clipper drive"], 0.68),
    ("decay", ["decay", "size"], 0.70),
    ("pre_delay_ms", ["pre delay", "predelay"], 0.70),
    ("feedback", ["feedback"], 0.70),
    ("limiter_ceiling_dbTP", ["ceiling", "true peak ceiling"], 0.78),
    ("limiter_max_gain_db", ["limiter gain", "max gain"], 0.74),
    ("true_peak_enable", ["true peak"], 0.72),
    ("low_end_mono_hz", ["mono below", "low mono", "bass mono"], 0.72),
    ("ms_side_gain_db", ["side gain", "width"], 0.68),
]


def _name_from_parameter(parameter: str | dict[str, Any]) -> str:
    if isinstance(parameter, dict):
        return str(parameter.get("name") or parameter.get("parameter_name") or "")
    return str(parameter)


def _index_from_parameter(parameter: str | dict[str, Any]) -> int | None:
    if isinstance(parameter, dict) and parameter.get("index") is not None:
        try:
            return int(parameter["index"])
        except (TypeError, ValueError):
            return None
    return None


def _contains_hint(name: str, hint: str) -> bool:
    clean = name.lower().replace("_", " ").replace("-", " ")
    h = hint.lower().replace("_", " ").replace("-", " ")
    if h == "q":
        return clean.strip() == "q" or " q" in clean or "q " in clean
    return h in clean


def is_do_not_touch_parameter(parameter_name: str) -> bool:
    clean = parameter_name.lower()
    return any(hint in clean for hint in DO_NOT_TOUCH_HINTS)


def infer_semantic_control(parameter_name: str) -> dict[str, Any]:
    if is_do_not_touch_parameter(parameter_name):
        return {
            "semantic": None,
            "confidence": 0.0,
            "reason": "do_not_touch_parameter",
        }
    best: tuple[str | None, float, str] = (None, 0.0, "no_match")
    for semantic, hints, confidence in SEMANTIC_HINTS:
        for hint in hints:
            if _contains_hint(parameter_name, hint) and confidence > best[1]:
                best = (semantic, confidence, f"matched_hint:{hint}")
    return {
        "semantic": best[0],
        "confidence": best[1],
        "reason": best[2],
    }


def learn_adapter_from_parameter_list(
    plugin_name: str,
    parameters: list[str | dict[str, Any]] | None,
    *,
    plugin_type: str = "unknown",
    manufacturer: str = "unknown",
    platform: str | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    parameters = parameters or []
    controls: dict[str, dict[str, Any]] = {}
    unknown_parameters: list[dict[str, Any]] = []
    do_not_touch: list[dict[str, Any]] = []
    matched_confidences: list[float] = []

    for parameter in parameters:
        name = _name_from_parameter(parameter)
        index = _index_from_parameter(parameter)
        inference = infer_semantic_control(name)
        semantic = inference.get("semantic")
        if inference.get("reason") == "do_not_touch_parameter":
            do_not_touch.append({"name": name, "index": index, "reason": "do_not_touch_parameter"})
            continue
        if not semantic:
            unknown_parameters.append({"name": name, "index": index, "reason": "no_semantic_match"})
            continue
        confidence = safe_float(inference.get("confidence"), 0.0)
        matched_confidences.append(confidence)
        existing = controls.get(str(semantic))
        if existing and safe_float(existing.get("confidence"), 0.0) >= confidence:
            continue
        controls[str(semantic)] = default_semantic_control(
            str(semantic),
            target_name=name,
            parameter_index=index,
            confidence=min(confidence, 0.84),
            write_allowed=False,
            validation_notes="provisional learner match; validation required before write",
        )

    adapter_confidence = min(max(matched_confidences, default=0.0), 0.84)
    adapter = create_adapter(
        adapter_id=f"{slugify(plugin_name)}_adapter",
        plugin_name_patterns=[plugin_name],
        plugin_type=plugin_type,
        manufacturer=manufacturer,
        platform=platform,
        semantic_controls=controls,
        confidence=adapter_confidence,
        safe_for_automix=False,
        warnings=["Provisional learned adapter. write_allowed remains false until validation passes."],
        source=PROVISIONAL_LEARNER_VERSION,
    )
    adapter["unknown_parameters"] = unknown_parameters
    adapter["do_not_touch_parameters"] = do_not_touch
    adapter["learning"] = {
        "status": "provisional",
        "learned_at": now_utc(),
        "parameter_count": len(parameters),
        "matched_parameter_count": len(controls),
        "unknown_parameter_count": len(unknown_parameters),
        "do_not_touch_count": len(do_not_touch),
        "requires_validation": True,
    }
    if output_dir:
        write_learned_adapter(adapter, output_dir)
    return adapter


def write_learned_adapter(adapter: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "plugins" / "learned_adapters" / f"{slugify(adapter.get('adapter_id'))}.json"
    return write_json(path, adapter)
