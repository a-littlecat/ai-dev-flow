"""Deterministic benchmark dataset generator frozen by DASHBOARD-001-P2-006."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes


BENCHMARK_SCHEMA = "ai-dev-flow/dashboard-benchmark/v1"
SEED = 20260728
AXES = (
    ("lifecycle", "Ready"),
    ("review_status", "Pending"),
    ("ua_status", "Pending"),
    ("acceptance_authority", "None"),
    ("commit_status", "Uncommitted"),
    ("merge_status", "Unmerged"),
    ("merge_authority", "None"),
    ("close_authority", "None"),
)

TASK_TEMPLATE = """{h1} {task_id}：benchmark {task_id}

{h2} Workflow Contract

- {bt}schema_version{bt}: {bt}adf/v0.7.0{bt}
- `task_id`: `{task_id}`
- `task_type`: `plan`
- `task_class`: `B`
- `lifecycle`: `Ready`
- `review_status`: `Pending`
- `ua_level`: `UA2`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

{h2} Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `medium`
- `depends_on`: `{depends}`
- `replaces`: `none`
- `discovered_from`: `none`
- `parent`: `none`
- `conflicts_with`: `none`
- `parallel_intent`: `consider`
- `write_scope`: `file:bench/files/{task_id}.txt;dir:bench/modules/m{module_index:02d}`
- `module_locks`: `bench-common;module-{module_index:02d}`
- `worktree`: `required`
- `branch_hint`: `bench/w{worktree_index}`
- `risk_flags`: `public_api;shared_component;tests_do_not_cover_oracle`

{h2} 目标与边界

- 目标：benchmark fixture
- 非目标：production
- 允许修改：`bench/**`
- 禁止修改：`outside/**`

{h2} 完成标准与验证

- 完成标准：fixture 可解析
- 验证命令或检查：benchmark validator

{h2} Outcome

- Base / Diff：benchmark
- 修改文件：none
- 验证证据：generated fixture
- Review findings：none
"""

BOARD_HEADER = b"| \xe4\xbb\xbb\xe5\x8a\xa1 | \xe5\x90\x8d\xe7\xa7\xb0 | \xe7\xad\x89\xe7\xba\xa7 | \xe7\x8a\xb6\xe6\x80\x81 | Review | UA | \xe9\xaa\x8c\xe6\x94\xb6 | \xe4\xba\xa4\xe4\xbb\x98 | \xe4\xbb\xbb\xe5\x8a\xa1\xe6\x96\x87\xe4\xbb\xb6 |\x0a"
BOARD_SEPARATOR = b"|---|---|---|---|---|---|---|---|---|\x0a"


def generate_edges(task_count: int, edge_count: int) -> tuple[tuple[int, int, str, str], ...]:
    if task_count < 2 or edge_count < 0:
        raise ValueError("task_count must be >= 2 and edge_count must be non-negative")
    maximum = sum((source - 1) * len(AXES) for source in range(2, task_count + 1))
    if edge_count > maximum:
        raise ValueError("edge_count exceeds the deterministic DAG capacity")
    rng = random.Random(SEED)
    edges: set[tuple[int, int, str, str]] = set()
    while len(edges) < edge_count:
        source = rng.randrange(2, task_count + 1)
        target = rng.randrange(1, source)
        axis, expected = AXES[rng.randrange(0, len(AXES))]
        edges.add((source, target, axis, expected))
    return tuple(sorted(edges))


def generate_dataset(
    output_dir: str | Path,
    *,
    task_count: int,
    edge_count: int,
) -> dict[str, Any]:
    """Generate a byte-identical source dataset and manifest.

    Dataset digest entries use exactly one NUL byte ``0x00`` and one LF byte
    ``0x0A``.  Visible backslash sequences never participate in the oracle.
    """

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    edges = generate_edges(task_count, edge_count)
    dependencies: dict[int, list[tuple[int, str, str]]] = {index: [] for index in range(1, task_count + 1)}
    for source, target, axis, expected in edges:
        dependencies[source].append((target, axis, expected))

    files: dict[str, bytes] = {
        ".gitattributes": b"* -text\x0a",
    }
    board = bytearray(BOARD_HEADER + BOARD_SEPARATOR)
    for index in range(1, task_count + 1):
        task_id = f"BENCH-{index:04d}"
        depends = ";".join(
            f"BENCH-{target:04d}#{axis}={expected}"
            for target, axis, expected in sorted(dependencies[index])
        ) or "none"
        base = TASK_TEMPLATE.format(
            h1="#",
            h2="##",
            bt="`",
            task_id=task_id,
            depends=depends,
            module_index=(index - 1) % 20 + 1,
            worktree_index=(index - 1) % 5 + 1,
        ).encode("utf-8")
        prefix = b"<!-- PAD:"
        suffix = b" -->\x0a"
        padding = 2048 - len(base) - len(prefix) - len(suffix)
        if padding < 0:
            raise ValueError(f"benchmark TASK base exceeds 2048 bytes: {task_id}")
        files[f"docs/tasks/{task_id}.md"] = base + prefix + (b"x" * padding) + suffix
        board.extend(
            (
                f"| {task_id} | benchmark {task_id} | B | Ready | Pending | UA2 | "
                f"Pending / None | commit=Uncommitted;merge=Unmerged;merge_authority=None | "
                f"[{task_id}](tasks/{task_id}.md) |\n"
            ).encode("utf-8")
        )
    files["docs/TASK_BOARD.md"] = bytes(board)
    worktrees = {
        "schema_version": "ai-dev-flow/dashboard-worktrees-fixture/v1",
        "worktrees": [
            {
                "branch": f"refs/heads/bench/w{index}",
                "dirty_state": "clean",
                "head": "BASE",
                "name": f"w{index}",
            }
            for index in range(1, 6)
        ],
    }
    files["worktrees.json"] = canonical_bytes(worktrees) + b"\x0a"

    digest_input = bytearray()
    for path in sorted(files, key=lambda item: item):
        content_sha = hashlib.sha256(files[path]).hexdigest().encode("ascii")
        digest_input.extend(path.encode("utf-8"))
        digest_input.extend(b"\x00")
        digest_input.extend(content_sha)
        digest_input.extend(b"\x0a")
    dataset_sha256 = hashlib.sha256(bytes(digest_input)).hexdigest()
    manifest = {
        "schema_version": BENCHMARK_SCHEMA,
        "seed": SEED,
        "task_count": task_count,
        "edge_count": edge_count,
        "file_count": len(files),
        "total_bytes": sum(len(content) for content in files.values()),
        "dataset_sha256": dataset_sha256,
    }

    for relative, content in files.items():
        target = root / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (root / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\x0a")
    return manifest


def dataset_digest_entries(files: dict[str, bytes]) -> bytes:
    """Return the exact digest input; exposed solely as a test oracle."""

    payload = bytearray()
    for path in sorted(files):
        payload.extend(path.encode("utf-8"))
        payload.extend(b"\x00")
        payload.extend(hashlib.sha256(files[path]).hexdigest().encode("ascii"))
        payload.extend(b"\x0a")
    return bytes(payload)
