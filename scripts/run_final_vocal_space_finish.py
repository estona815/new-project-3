#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.final_vocal_space_finish import run_final_vocal_space_finish


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Final accepted-recovery vocal space carving and review package workflow.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--apply-placement-draft", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--generate-review-form", action="store_true")
    parser.add_argument("--accept-placement-review", action="store_true")
    parser.add_argument("--apply-safe-premaster-draft", action="store_true")
    parser.add_argument("--make-review-package", action="store_true")
    parser.add_argument("--strict-protection", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--deliverables-root", type=Path, default=Path("deliverables"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_final_vocal_space_finish(
        project_path=args.project,
        output_dir=args.output_dir,
        deliverables_root=args.deliverables_root,
        apply_placement_draft=args.apply_placement_draft,
        render_ab=args.render_ab,
        generate_review_form=args.generate_review_form,
        accept_placement_review=args.accept_placement_review,
        apply_safe_premaster_draft=args.apply_safe_premaster_draft,
        make_review_package=args.make_review_package,
        strict_protection=args.strict_protection,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
