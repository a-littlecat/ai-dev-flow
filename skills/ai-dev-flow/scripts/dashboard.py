"""Installed ai-dev-flow Skill entry point for the portable local Dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

from runtime_bundle import BundlePreflightError, preflight_bundle


sys.dont_write_bytecode = True
SKILL_ROOT = Path(__file__).resolve().parents[1]
try:
    BACKEND_SRC = preflight_bundle(SKILL_ROOT)
except BundlePreflightError as exc:
    print(f"dashboard launcher error: {exc}", file=sys.stderr)
    raise SystemExit(2) from None

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

try:
    from ai_dev_flow_dashboard.portable import main
except ImportError as exc:
    raise SystemExit(
        "dashboard launcher error: installed Dashboard runtime is missing; "
        "install a complete ai-dev-flow Skill package"
    ) from exc


if __name__ == "__main__":
    raise SystemExit(main(entry_skill_root=SKILL_ROOT))
