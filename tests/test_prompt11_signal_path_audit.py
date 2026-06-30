from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "docs"

REQUIRED_PROMPT11_DOCS = [
    "repository_audit.md",
    "signal_path.md",
    "parameter_audit.md",
    "model_path_audit.md",
    "realtime_safety_audit.md",
    "risk_register.md",
    "first_patch_plan.md",
]


def read_doc(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_prompt11_required_audit_docs_exist_and_are_substantial() -> None:
    for name in REQUIRED_PROMPT11_DOCS:
        path = DOCS / name
        assert path.exists(), name
        assert path.stat().st_size > 1000, name


def test_repository_audit_identifies_actual_jsfx_runtime_and_missing_cpp_paths() -> None:
    text = read_doc("repository_audit.md")

    assert "vocal_ai_artifact_split_tamer.jsfx" in text
    assert "No C++ `AudioProcessor` class" in text
    assert "No APVTS" in text
    assert "No model loading or inference runtime" in text
    assert "Issue 0.1" in text
    assert "cmake: command not found" in text
    assert "No module named pytest" in text
    assert "plugin/` directory is NOT FOUND" in text or "plugin/` sources" in text


def test_signal_path_maps_real_entry_point_and_answers_a_to_z() -> None:
    text = read_doc("signal_path.md")

    assert "Function: JSFX `@sample`" in text
    assert "Lines: `" in text
    assert "REAPER input L/R" in text
    assert "bad-input and silence checks" in text
    assert "smoothed dry/wet blend" in text
    assert "optional residual monitor output" in text
    assert "No STFT/FFT" in text
    assert "No model inference call" in text

    for question in (
        "A. Where is the input buffer first modified?",
        "B. Is a dry copy made before processing?",
        "C. Where is bypass handled?",
        "D. Is bypass true dry passthrough?",
        "E. Where is dry/wet applied?",
        "F. Is dry/wet applied before or after denoising?",
        "G. Are parameters read once per block or repeatedly in loops?",
        "H. Are parameters clamped?",
        "I. Where is Amount used?",
        "J. Is Amount linear or nonlinear?",
        "K. Where is threshold used?",
        "L. Is there a hard mask?",
        "M. Can any mask/gain become 0.0?",
        "N. Is there a MaxSuppressionDb or equivalent?",
        "O. Does any code zero spectral bins?",
        "P. Does any code subtract noise magnitude directly?",
        "Q. Is there time smoothing?",
        "R. Is there frequency smoothing?",
        "S. Is there STFT overlap-add normalization?",
        "T. Can log(0), divide-by-zero, sqrt negative, NaN, or Inf occur?",
        "U. Is model output shape checked?",
        "V. Is model output finite-checked?",
        "W. What happens if model is missing?",
        "X. What happens if model output is invalid?",
        "Y. Does model output directly replace waveform?",
        "Z. Can processBlock allocate memory?",
    ):
        assert question in text


def test_parameter_audit_covers_required_parameters_and_missing_non_paths() -> None:
    text = read_doc("parameter_audit.md")

    for required in (
        "Amount",
        "DryWet",
        "MaxSuppressionDb",
        "AttackMs",
        "ReleaseMs",
        "Bypass",
        "MaskStrength",
        "ProcessingEnabled",
        "ResidualMonitor",
        "HarmonicPreserve",
    ):
        assert required in text

    assert "APVTS: NOT FOUND" in text
    assert "Threshold: NOT FOUND as user parameter" in text
    assert "FFT size: NOT FOUND" in text
    assert "Hop size: NOT FOUND" in text
    assert "InferenceEnabled: NOT FOUND" in text
    assert "ModelMode: NOT FOUND in active plugin" in text
    assert "QualityMode: NOT FOUND" in text


def test_model_realtime_risk_and_patch_plan_do_not_invent_new_dsp() -> None:
    model = read_doc("model_path_audit.md")
    realtime = read_doc("realtime_safety_audit.md")
    risks = read_doc("risk_register.md")
    plan = read_doc("first_patch_plan.md")

    assert "No active AI model path was found" in model
    assert "MODEL OUTPUT TYPE UNKNOWN - MUST NOT BE TRUSTED WITHOUT CONTRACT" in model
    assert "Contract only" in model or "not active" in model
    assert "NO OBVIOUS REAL-TIME UNSAFE OPERATION FOUND IN INSPECTED PATH" in realtime
    assert "bad input now uses last stable safe output" in realtime
    assert "| R-001 | P1 | Invalid output |" in risks
    assert "| R-006 | P1 | Destructive full-band suppression |" in risks
    assert "Do not implement multiband" in plan
    assert "Patch 2 - JSFX Fallback Tightening" in plan
    assert "NOT APPLICABLE in current repo" in plan
