from tools.schemas import MALE_MAIN_TRACK, build_plugin_trace, detect_environment, discover_assets, track_by_name


def test_plugin_trace_contains_required_fields(tmp_path):
    manifest = discover_assets(tmp_path)
    env = detect_environment(tmp_path)
    trace = build_plugin_trace(manifest, env, tmp_path)
    assert "timestamp" in trace
    assert "OS" in trace
    assert "REAPER executable path" in trace
    assert "source manifest hash" in trace
    assert isinstance(trace["tracks"], list)

    male = track_by_name(trace, MALE_MAIN_TRACK)
    assert male is not None
    first_fx = male["fx_chain"][0]
    assert first_fx["slot_index"] == 0
    assert first_fx["requested_plugin_name"] == "JS: Codex Vocal AI Artifact Split Tamer"
    assert first_fx["resolved_plugin_name"] == "JS: Codex Vocal AI Artifact Split Tamer"
    assert "parameters_written" in first_fx
