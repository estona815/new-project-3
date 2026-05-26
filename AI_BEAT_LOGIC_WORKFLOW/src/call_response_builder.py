from __future__ import annotations

from typing import Any


def _sections_from_plan(rescue_arrangement_plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    sections = list((rescue_arrangement_plan or {}).get("sections") or [])
    if sections:
        return sections
    return [
        {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3},
        {"name": "main_hook", "start_time": 4.0, "duration": 16.0, "energy": 5},
        {"name": "verse", "start_time": 20.0, "duration": 16.0, "energy": 2},
        {"name": "hook_return", "start_time": 36.0, "duration": 16.0, "energy": 5},
        {"name": "breakdown", "start_time": 52.0, "duration": 16.0, "energy": 2},
        {"name": "final_hook", "start_time": 68.0, "duration": 20.0, "energy": 5},
        {"name": "outro", "start_time": 88.0, "duration": 12.0, "energy": 1},
    ]


def _role_lookup(selected_samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("role")): item for item in selected_samples}


def _section_name(section: dict[str, Any]) -> str:
    return str(section.get("name") or section.get("section") or "section")


def _is_hook(section_name: str) -> bool:
    lowered = section_name.lower()
    return "hook" in lowered or "drop" in lowered


def _section_usage_item(section: dict[str, Any], role_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    name = _section_name(section)
    lowered = name.lower()
    energy = int(section.get("energy", 3) or 3)
    if "intro" in lowered and _is_hook(name):
        sample_role = "main_motif_filtered"
        sample_id = (role_map.get("main_motif") or {}).get("sample_id")
        density = "low"
    elif _is_hook(name) and "final" in lowered:
        sample_role = "main_motif_full_plus_response"
        sample_id = (role_map.get("main_motif") or {}).get("sample_id")
        density = "high"
    elif _is_hook(name):
        sample_role = "main_motif_full"
        sample_id = (role_map.get("main_motif") or {}).get("sample_id")
        density = "high" if energy >= 4 else "medium"
    elif "verse" in lowered:
        sample_role = "texture_only"
        sample_id = (role_map.get("texture_layer") or role_map.get("main_motif") or {}).get("sample_id")
        density = "low"
    elif "break" in lowered or "bridge" in lowered:
        sample_role = "response_motif_filtered"
        sample_id = (role_map.get("response_motif") or role_map.get("main_motif") or {}).get("sample_id")
        density = "low"
    elif "transition" in lowered or "pre" in lowered:
        sample_role = "transition_element"
        sample_id = (role_map.get("transition_element") or role_map.get("response_motif") or {}).get("sample_id")
        density = "intentional"
    elif "outro" in lowered:
        sample_role = "texture_tail"
        sample_id = (role_map.get("texture_layer") or role_map.get("main_motif") or {}).get("sample_id")
        density = "low"
    else:
        sample_role = "response_motif"
        sample_id = (role_map.get("response_motif") or role_map.get("main_motif") or {}).get("sample_id")
        density = "medium_low"
    return {
        "section": name,
        "sample_role": sample_role,
        "sample_id": sample_id,
        "density": density,
        "start_time": section.get("start_time", section.get("start")),
        "duration": section.get("duration"),
    }


def build_call_response_plan(
    selected_samples: list[dict[str, Any]],
    rescue_arrangement_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_map = _role_lookup(selected_samples)
    sections = _sections_from_plan(rescue_arrangement_plan)
    section_usage = [_section_usage_item(section, role_map) for section in sections]
    hook_usages = [item for item in section_usage if "hook" in item["section"].lower()]
    main_id = (role_map.get("main_motif") or {}).get("sample_id")
    response_id = (role_map.get("response_motif") or role_map.get("main_motif") or {}).get("sample_id")
    if main_id and not any(item.get("sample_id") == main_id and "hook" in item["section"].lower() for item in section_usage):
        section_usage.insert(
            0,
            {
                "section": "main_hook",
                "sample_role": "main_motif_full",
                "sample_id": main_id,
                "density": "high",
                "start_time": 4.0,
                "duration": 16.0,
            },
        )
    return {
        "schema_version": "sample_call_response_plan.v1",
        "main_motif_id": main_id,
        "response_motif_id": response_id,
        "section_usage": section_usage,
        "hook_return_count": len(hook_usages),
        "call_response_rules": [
            "Main motif states the hook.",
            "Response motif answers only in gaps or second half of hook.",
            "Texture layer supports verse/breakdown and must not become a random lead.",
            "Transition element appears only at section boundaries.",
        ],
        "anti_spam": {
            "max_active_sample_roles_per_section": 2,
            "avoid_over_chopping": True,
            "minimum_hook_return_required": True,
        },
    }
