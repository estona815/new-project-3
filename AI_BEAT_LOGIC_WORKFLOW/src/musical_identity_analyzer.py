from __future__ import annotations

from typing import Any

import numpy as np

from hook_identity_detector import detect_hook_identity
from lead_melody_presence import analyze_lead_melody_presence


def analyze_musical_identity(mono_samples: list[float] | np.ndarray, sample_rate: int) -> dict[str, Any]:
    lead = analyze_lead_melody_presence(mono_samples, sample_rate)
    hook = detect_hook_identity(mono_samples, sample_rate)
    lead_score = int(lead["lead_melody_presence"])
    hook_score = int(hook["hook_identity"])
    motif_score = int(hook["motif_repetition_quality"])
    call_response = int(hook["call_response_quality"])
    score = round((lead_score + hook_score + motif_score + call_response) / 4.0, 2)
    diagnosis = "present" if score >= 3.75 else "unclear" if score >= 2.75 else "weak_or_absent"
    return {
        "lead_melody_presence": lead_score,
        "hook_identity": hook_score,
        "motif_repetition_quality": motif_score,
        "call_response_quality": call_response,
        "score": score,
        "diagnosis": diagnosis,
        "lead_melody_analysis": lead,
        "hook_identity_analysis": hook,
    }
