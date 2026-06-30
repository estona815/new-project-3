from tools.schemas import REFERENCE_TRACK, build_plugin_trace, compute_gate_checks, detect_environment, discover_assets, track_by_name


def test_raw_full_mix_has_no_active_path_by_default(tmp_path):
    trace = build_plugin_trace(discover_assets(tmp_path), detect_environment(tmp_path), tmp_path)
    assert compute_gate_checks(trace, tmp_path)["raw_full_mix_not_active"] is True


def test_raw_full_mix_active_path_fails_gate(tmp_path):
    trace = build_plugin_trace(discover_assets(tmp_path), detect_environment(tmp_path), tmp_path)
    ref = track_by_name(trace, REFERENCE_TRACK)
    ref["sends"].append({"target": "MASTER", "channels": "1/2", "optional": False})
    assert compute_gate_checks(trace, tmp_path)["raw_full_mix_not_active"] is False
