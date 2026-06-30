#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.context.compact_mix_context import (  # noqa: E402
    DEFAULT_CONTEXT_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROJECT_NAME,
    build_compact_mix_context,
    write_compact_mix_context,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the token-light compact AutoMix run context.")
    parser.add_argument("--project-name", default=DEFAULT_PROJECT_NAME)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--context-path", type=Path, default=DEFAULT_CONTEXT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = build_compact_mix_context(
        project_name=args.project_name,
        workspace_root=args.workspace_root,
        output_dir=args.output_dir,
    )
    paths = write_compact_mix_context(context, args.context_path, workspace_root=args.workspace_root)
    summary = {
        "status": "written",
        "context_json": paths["json"],
        "context_markdown": paths["markdown"],
        "claim_boundary": context.get("claim_boundary"),
        "readiness": context.get("readiness", {}),
        "blockers": context.get("blockers", []),
        "recommended_next_actions": context.get("recommended_next_actions", []),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

