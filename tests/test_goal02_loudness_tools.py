from __future__ import annotations

from tools.analyze_goal02_runtime_loudness import parse_loudnorm_json


def test_parse_loudnorm_json_uses_last_block() -> None:
    text = """
noise before
{
        "input_i" : "-12.11",
        "input_tp" : "-1.18",
        "input_lra" : "1.50",
        "input_thresh" : "-22.17",
        "output_i" : "-14.00",
        "target_offset" : "0.04"
}
noise between
{
        "input_i" : "-9.50",
        "input_tp" : "-1.06",
        "input_lra" : "1.00",
        "input_thresh" : "-19.54",
        "output_i" : "-14.00",
        "target_offset" : "-0.02"
}
"""

    payload = parse_loudnorm_json(text)

    assert payload["input_i"] == "-9.50"
    assert payload["input_tp"] == "-1.06"
