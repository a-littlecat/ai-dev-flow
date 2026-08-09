from __future__ import annotations

import hashlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "dashboard" / "backend"
SRC_ROOT = BACKEND_ROOT / "src"
CONTRACTS_ROOT = REPO_ROOT / "dashboard" / "contracts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_dev_flow_dashboard.core.models import (  # noqa: E402
    FrozenTaskInput,
    Provenance,
    SchedulingProfile,
    ScopeEntry,
    TaskNode,
    WorktreeSnapshot,
)


def frozen(text: str, source_path: str = "docs/tasks/TEST-001.md") -> FrozenTaskInput:
    content = text.encode("utf-8")
    return FrozenTaskInput(
        path=Path(source_path),
        source_path=source_path,
        content=content,
        text=text,
        mtime_ns=1,
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def scheduling_text(**overrides: str) -> str:
    fields = {
        "scheduling_schema": "ai-dev-flow/scheduling/v1",
        "priority": "high",
        "depends_on": "BASE-001#lifecycle=Accepted",
        "replaces": "none",
        "discovered_from": "none",
        "parent": "BASE-001",
        "conflicts_with": "none",
        "parallel_intent": "consider",
        "write_scope": "file:src/a.py;dir:src/pkg",
        "module_locks": "dashboard;reader",
        "worktree": "required",
        "branch_hint": "codex/test-001",
        "risk_flags": "public_api;shared_component",
    }
    fields.update(overrides)
    lines = ["# TEST-001：test", "", "## Scheduling", ""]
    lines.extend(f"- `{key}`: `{value}`" for key, value in fields.items())
    lines.extend(["", "## Outcome", "", "- Review findings：none", ""])
    return "\n".join(lines)


def provenance(field: str = "write_scope", raw: str | None = None) -> Provenance:
    return Provenance("docs/tasks/TEST.md", "Scheduling", field, 1, raw, "canonical")


def scope(token: str) -> ScopeEntry:
    kind, path = token.split(":", 1)
    return ScopeEntry(kind, path, tuple(item.casefold() for item in path.split("/")), provenance(raw=token))


def profile(
    *,
    state: str = "canonical",
    scopes: tuple[str, ...] = ("file:src/a.py",),
    locks: tuple[str, ...] = (),
    dependencies=(),
    values: dict | None = None,
) -> SchedulingProfile:
    payload = {
        "priority": "medium",
        "depends_on": tuple(
            f"{item.target_task_id}#{item.axis}={item.expected}" for item in dependencies
        ),
        "replaces": (),
        "discovered_from": (),
        "parent": None,
        "conflicts_with": (),
        "parallel_intent": "consider",
        "write_scope": scopes,
        "module_locks": locks,
        "worktree": "required",
        "branch_hint": "codex/test",
        "risk_flags": (),
        "scheduling_schema": "ai-dev-flow/scheduling/v1",
    }
    payload.update(values or {})
    entries = tuple(scope(item) for item in scopes)
    return SchedulingProfile(
        state,
        tuple(payload.items()),
        tuple(dependencies),
        entries,
        (),
        (),
    )


def task(task_id: str, **overrides) -> TaskNode:
    values = {
        "task_id": task_id,
        "title": task_id,
        "source_path": f"docs/tasks/{task_id}.md",
        "task_type": "code",
        "task_class": "B",
        "lifecycle": "Ready",
        "contract_schema_version": "adf/v0.7.0",
        "review_requirement": "Legacy Unspecified",
        "review_state": "Passed",
        "review_status": "Passed",
        "ua_level": "UA3",
        "ua_status": "Pending",
        "acceptance_authority": "None",
        "commit_status": "Uncommitted",
        "merge_status": "Unmerged",
        "merge_authority": "None",
        "close_authority": "None",
        "unsupported_axes": (
            "commit_authority",
            "release_status",
            "release_authority",
            "repair_authority",
        ),
        "scheduling_state": "canonical",
        "priority": "medium",
        "risk_flags": (),
        "write_scope": ("file:src/a.py",),
        "module_locks": (),
        "parallel_intent": "consider",
        "worktree_requirement": "required",
        "branch_hint": f"codex/{task_id.lower()}",
        "freshness": "fresh",
        "diagnostic_ids": (),
        "provenance": (),
    }
    if "review_status" in overrides and "review_state" not in overrides:
        overrides["review_state"] = {
            "Pending": "Not Run",
            "Do Not Merge": "Blocked",
        }.get(overrides["review_status"], overrides["review_status"])
    values.update(overrides)
    return TaskNode(**values)


def worktree(task_id: str, root: str | None = None, **overrides) -> WorktreeSnapshot:
    values = {
        "root": root or f"D:/wt/{task_id.lower()}",
        "head": "a" * 40,
        "branch": f"refs/heads/codex/{task_id.lower()}",
        "detached": False,
        "locked": False,
        "prunable": False,
        "dirty_state": "clean",
        "dirty_paths": (),
        "diagnostic_ids": (),
        "dirty_ownership": "clean",
    }
    values.update(overrides)
    return WorktreeSnapshot(**values)
