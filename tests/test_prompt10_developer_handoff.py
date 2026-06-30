from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "docs"

REQUIRED_DOCS = [
    "repository_audit.md",
    "signal_path.md",
    "development_milestones.md",
    "audio_quality_guardrails.md",
    "issue_breakdown.md",
    "testing_plan.md",
    "preset_policy.md",
    "release_candidate_checklist.md",
    "known_risks.md",
    "developer_handoff_master.md",
]


def read_doc(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_prompt10_required_handoff_docs_exist() -> None:
    for name in REQUIRED_DOCS:
        path = DOCS / name
        assert path.exists(), name
        assert path.stat().st_size > 500, name


def test_repository_audit_maps_actual_jsfx_architecture_and_missing_cpp() -> None:
    text = read_doc("repository_audit.md")

    assert "vocal_ai_artifact_split_tamer.jsfx" in text
    assert "No C++ `AudioProcessor` class" in text
    assert "No APVTS" in text
    assert "No model loading or inference runtime" in text
    assert "Issue 0.1" in text


def test_signal_path_documents_bypass_drywet_residual_and_non_paths() -> None:
    text = read_doc("signal_path.md")

    assert "REAPER input L/R" in text
    assert "bad-input and silence checks" in text
    assert "smoothed dry/wet blend" in text
    assert "optional residual monitor output" in text
    assert "No STFT/FFT" in text
    assert "No model inference call" in text


def test_audio_quality_guardrails_block_clean_but_low_quality_release() -> None:
    text = read_doc("audio_quality_guardrails.md")

    assert "source-preserving AI noise and artifact suppressor" in text
    assert "Moderate remaining noise is acceptable" in text
    assert "Source damage is not acceptable" in text
    assert "No exciter" in text
    assert "No high-shelf boost" in text
    assert "Strong mode must be isolated" in text


def test_development_milestones_and_dependency_graph_are_complete() -> None:
    text = read_doc("development_milestones.md")

    for idx in range(10):
        assert f"Milestone {idx}" in text
    assert "Dependency Graph" in text
    assert "Do not implement multiband DSP before safety baseline" in text
    assert "Definition Of Done" in text
    assert "Definition Of Release Ready" in text


def test_issue_breakdown_contains_required_priorities_and_first_five() -> None:
    text = read_doc("issue_breakdown.md")

    for priority in ("P0", "P1", "P2", "P3"):
        assert priority in text
    for issue in ("0.1", "0.2", "1.1", "1.2", "1.4"):
        assert f"Issue {issue}" in text
    assert "[P0] Repository architecture and signal-path audit" in text
    assert "[P0] Build and test baseline" in text
    assert "[P0] Unify denoise parameter defaults" in text
    assert "[P0] Add processBlock parameter snapshot" in text
    assert "[P0] Safe fallback behavior" in text
    assert "Do not begin with multiband" in text


def test_pr_policy_and_definition_of_done_are_locked() -> None:
    issue_text = read_doc("issue_breakdown.md")
    milestone_text = read_doc("development_milestones.md")

    assert "No drive-by DSP changes" in issue_text
    assert "No preset tuning without evaluation" in issue_text
    assert "No Strong mode as default" in issue_text
    assert "no new audio-thread unsafe operation" in milestone_text
    assert "defaults not made more aggressive" in milestone_text


def test_testing_preset_release_and_risk_docs_cover_release_blockers() -> None:
    testing = read_doc("testing_plan.md")
    preset = read_doc("preset_policy.md")
    checklist = read_doc("release_candidate_checklist.md")
    risks = read_doc("known_risks.md")

    assert "Block Sizes" in testing
    assert "Sample Rates" in testing
    assert "Manual Listening" in testing
    assert "Strong is never default" in preset
    assert "Do not approve RC" in checklist
    assert "P0 - Safety / Crash / Destructive Audio" in risks
    assert "P1 - Source Preservation / Audio Quality" in risks
    assert "Clean but low-fidelity output" in risks


def test_developer_handoff_master_points_to_all_required_docs_and_agent_sequence() -> None:
    text = read_doc("developer_handoff_master.md")

    for name in REQUIRED_DOCS:
        assert name in text
    assert "Every coding task must follow this sequence" in text
    assert "Do not claim audio improvement unless tested" in text
    assert "Maximum noise remover" in text
    assert "Source-preserving AI noise and artifact suppressor" in text
