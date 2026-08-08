"""Portable wrapper for the Harness-neutral ai-dev-flow CLI."""

from __future__ import annotations

import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = (
    SKILL_ROOT / "dashboard" / "backend" / "src",
    SKILL_ROOT.parents[1] / "dashboard" / "backend" / "src",
)
for candidate in CANDIDATES:
    if (candidate / "ai_dev_flow_dashboard" / "cli.py").is_file():
        sys.path.insert(0, str(candidate))
        break
else:
    raise SystemExit("adf error: Dashboard backend runtime is missing")

from ai_dev_flow_dashboard.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
