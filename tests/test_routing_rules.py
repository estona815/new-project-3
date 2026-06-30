from tools.schemas import ROUTES, build_plugin_trace, compute_gate_checks, detect_environment, discover_assets


def test_required_routing_exists_in_trace(tmp_path):
    manifest = discover_assets(tmp_path)
    trace = build_plugin_trace(manifest, detect_environment(tmp_path), tmp_path)
    route_pairs = {
        (track["name"], send["target"])
        for track in trace["tracks"]
        for send in track["sends"]
        if not send.get("optional")
    }
    assert all(route in route_pairs for route in ROUTES)
    assert compute_gate_checks(trace, tmp_path)["required_routing_exists"] is True
