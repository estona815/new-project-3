from pathlib import Path

from tools.qc_audio import analyze_audio


def test_missing_render_qc_is_explicitly_blocked(tmp_path: Path):
    report = analyze_audio(tmp_path / "missing.wav")
    assert report["status"] == "BLOCKED"
    assert report["metrics"]["integrated_lufs"]["value"] is None
    assert report["metrics"]["true_peak_db_tp"]["status"] == "unavailable"
    assert "render file does not exist" in report["summary"]
