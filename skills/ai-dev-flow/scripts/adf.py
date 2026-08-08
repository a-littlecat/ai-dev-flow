"""Portable wrapper for the Harness-neutral ai-dev-flow CLI."""

from __future__ import annotations

import sys
from pathlib import Path

from runtime_bundle import BundlePreflightError, preflight_bundle

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
try:
    backend_src = preflight_bundle(SKILL_ROOT)
except BundlePreflightError as exc:
    print(f"adf error: {exc}", file=sys.stderr)
    raise SystemExit(2) from None
sys.path.insert(0, str(backend_src))

from ai_dev_flow_dashboard.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
