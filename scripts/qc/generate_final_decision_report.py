#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out = root / "examples" / "reports" / "final_decision_template.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Final Decision Report Template\n\n"
        "- Source: dummy/local_only placeholder\n"
        "- Best candidate: TBD\n"
        "- Rejected candidates: TBD\n"
        "- Reason: listen plus QC required\n"
        "- Plugin chain: TBD after main-computer scan\n"
        "- Remaining problems: TBD\n"
        "- Decision: demo-ready / release-ready / regenerate\n",
        encoding="utf-8",
    )
    print(f"[ok] Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

