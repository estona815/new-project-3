from tools.schemas import REFERENCE_TRACK, build_plugin_trace, compute_gate_checks, detect_environment, discover_assets, track_by_name


def test_reference_track_is_muted_and_master_send_disabled(tmp_path):
    trace = build_plugin_trace(discover_assets(tmp_path), detect_environment(tmp_path), tmp_path)
    ref = track_by_name(trace, REFERENCE_TRACK)
    assert ref is not None
    assert ref["muted"] is True
    assert ref["master_send_enabled"] is False
    gates = compute_gate_checks(trace, tmp_path)
    assert gates["full_mix_reference_muted"] is True
    assert gates["full_mix_reference_master_send_disabled"] is True
