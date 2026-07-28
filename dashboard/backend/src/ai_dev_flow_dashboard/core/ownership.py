"""Resolve dirty Worktree ownership from canonical task scheduling evidence."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Mapping

from .models import (
    Provenance,
    SchedulingProfile,
    ScopeEntry,
    TaskNode,
    WorktreeSnapshot,
)
from .scheduling import canonical_repo_path


def resolve_dirty_ownership(
    tasks: tuple[TaskNode, ...],
    profiles: Mapping[str, SchedulingProfile],
    worktrees: Mapping[str, WorktreeSnapshot] | None,
) -> dict[str, WorktreeSnapshot]:
    """Return copied evidence with fail-closed dirty ownership classifications."""

    mapping = dict(worktrees or {})
    if not mapping:
        return mapping
    by_id = {task.task_id: task for task in tasks}
    root_counts = Counter(item.root.casefold() for item in mapping.values())
    branch_counts = Counter(
        item.branch.casefold() for item in mapping.values() if item.branch
    )
    resolved: dict[str, WorktreeSnapshot] = {}
    for task_id, worktree in mapping.items():
        ownership = _classify(
            task_id,
            worktree,
            by_id,
            profiles,
            root_counts,
            branch_counts,
        )
        resolved[task_id] = replace(worktree, dirty_ownership=ownership)
    return resolved


def resolve_dirty_ownership_for_tasks(
    tasks: tuple[TaskNode, ...],
    worktrees: Mapping[str, WorktreeSnapshot] | None,
) -> dict[str, WorktreeSnapshot]:
    """Resolve ownership from already-canonical TaskNode wire fields."""

    profiles: dict[str, SchedulingProfile] = {}
    for task in tasks:
        entries = []
        valid = task.scheduling_state == "canonical"
        for token in task.write_scope:
            if ":" not in token:
                valid = False
                break
            kind, raw_path = token.split(":", 1)
            canonical = canonical_repo_path(raw_path)
            if kind not in {"file", "dir"} or canonical is None:
                valid = False
                break
            entries.append(
                ScopeEntry(
                    kind,
                    canonical[0],
                    canonical[1],
                    Provenance(
                        task.source_path,
                        "Scheduling",
                        "write_scope",
                        0,
                        token,
                        "canonical",
                    ),
                )
            )
        profiles[task.task_id] = SchedulingProfile(
            "canonical" if valid else "invalid",
            (),
            (),
            tuple(entries),
            (),
            (),
        )
    return resolve_dirty_ownership(tasks, profiles, worktrees)


def _classify(
    task_id: str,
    worktree: WorktreeSnapshot,
    tasks: Mapping[str, TaskNode],
    profiles: Mapping[str, SchedulingProfile],
    root_counts: Counter,
    branch_counts: Counter,
) -> str:
    if worktree.dirty_state == "clean":
        return "clean" if not worktree.dirty_paths else "unknown"
    if worktree.dirty_state != "dirty":
        return "unknown"
    task = tasks.get(task_id)
    profile = profiles.get(task_id)
    if (
        task is None
        or profile is None
        or profile.state != "canonical"
        or not task.branch_hint
        or worktree.branch != f"refs/heads/{task.branch_hint}"
        or worktree.detached
        or worktree.locked
        or worktree.prunable
        or worktree.diagnostic_ids
        or root_counts[worktree.root.casefold()] != 1
        or branch_counts[worktree.branch.casefold()] != 1
        or not worktree.dirty_paths
    ):
        return "unknown"
    if any(
        candidate.state != "canonical"
        for candidate in profiles.values()
    ):
        return "unknown"

    paths = []
    for dirty_path in worktree.dirty_paths:
        canonical = canonical_repo_path(dirty_path)
        if canonical is None:
            return "unknown"
        paths.append(canonical[1])

    if any(
        not any(_scope_covers_path(scope, path) for scope in profile.write_scope)
        for path in paths
    ):
        return "unowned"

    for other_task_id, other_profile in profiles.items():
        if other_task_id == task_id:
            continue
        if any(
            _scope_covers_path(scope, path)
            for scope in other_profile.write_scope
            for path in paths
        ):
            return "unowned"
    return "owned_by_task"


def _scope_covers_path(scope, path_segments: tuple[str, ...]) -> bool:
    if scope.kind == "file":
        return scope.comparison_segments == path_segments
    return (
        len(scope.comparison_segments) <= len(path_segments)
        and path_segments[: len(scope.comparison_segments)] == scope.comparison_segments
    )
