#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rescue_renderer import run_bad_ai_song_rescue_render  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a bad AI song rescue plan/demo/final WAV.")
    parser.add_argument("input_path", help="Full stereo working WAV input.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Workflow project root.")
    parser.add_argument("--final", action="store_true", help="Also render and verify final_bad_ai_song_rescue_24bit_48k.wav.")
    parser.add_argument("--plan-only", action="store_true", help="Write plans and QC report without audio rendering.")
    parser.add_argument("--no-lead-render", action="store_true", help="Do not render generated lead motif audio.")
    parser.add_argument("--sample-folder", default=None, help="Optional local sample folder.")
    parser.add_argument("--sample-analysis", default=None, help="Optional sample_analysis.json path.")
    parser.add_argument("--creative-brief", default=None, help="Optional creative_brief.json path.")
    parser.add_argument("--style-cluster", default="system_seoul_adjacent", help="Broad style cluster, not exact copying.")
    parser.add_argument("--length-mode", default="under_2min", help="reels_15sec, short_30sec, under_2min, or full_song.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_bad_ai_song_rescue_render(
        args.input_path,
        project_root=args.project_root,
        final_mode=bool(args.final),
        render_audio=not bool(args.plan_only),
        render_generated_lead=not bool(args.no_lead_render),
        render_sample_motif=bool(args.sample_folder or args.sample_analysis),
        sample_folder=args.sample_folder,
        sample_analysis_path=args.sample_analysis,
        creative_brief_path=args.creative_brief,
        style_cluster=args.style_cluster,
        length_mode=args.length_mode,
    )
    print(f"status: {result['status']}")
    print(f"complete: {str(bool(result['complete'])).lower()}")
    print(f"rescue demo: {result['paths']['rescue_demo']}")
    if result["paths"].get("final_wav"):
        print(f"final wav: {result['paths']['final_wav']}")
    print(f"qc report: {result['paths']['rescue_qc_report']}")
    if result["status"] == "COMPLETE":
        print("completion_gate: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
