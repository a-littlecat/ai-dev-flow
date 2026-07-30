"""Mutate only an isolated integration fixture into a requested real state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.integration.atomic_write import atomic_replace_bytes
from dashboard.integration.tests.support import matrix_board, matrix_task


def apply_scenario(project: Path, scenario: str) -> None:
    task_one = project / "docs" / "tasks" / "STACK-001.md"
    task_two = project / "docs" / "tasks" / "STACK-002.md"
    board = project / "docs" / "TASK_BOARD.md"
    if scenario == "invalid-utf8":
        atomic_replace_bytes(task_one, b"\xff")
        return
    if scenario == "invalid-board-utf8":
        atomic_replace_bytes(board, b"\xff")
        return
    if scenario == "valid":
        one = matrix_task("STACK-001")
        two = matrix_task("STACK-002")
    elif scenario == "parallel-unknown":
        one = matrix_task("STACK-001", parallel_intent="unknown")
        two = matrix_task("STACK-002", parallel_intent="unknown")
    elif scenario == "dependency-cycle":
        one = matrix_task("STACK-001", depends_on="STACK-002#lifecycle=Ready")
        two = matrix_task("STACK-002", depends_on="STACK-001#lifecycle=Ready")
    elif scenario == "parse-error":
        one = matrix_task("STACK-001").replace(
            "- `priority`: `high`",
            "- invalid scheduling line",
            1,
        )
        two = matrix_task("STACK-002")
    else:
        raise ValueError(f"unsupported state-matrix scenario: {scenario}")
    atomic_replace_bytes(task_one, one.encode("utf-8"))
    atomic_replace_bytes(task_two, two.encode("utf-8"))
    atomic_replace_bytes(board, matrix_board().encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("scenario")
    args = parser.parse_args()
    apply_scenario(args.project.resolve(), args.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
