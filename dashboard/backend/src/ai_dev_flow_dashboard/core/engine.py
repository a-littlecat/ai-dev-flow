"""End-to-end read-only dashboard core orchestration."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Iterator, Mapping

from .actions import ActionEngine
from .contract_gateway import ContractGateway
from .frozen_input import FrozenInputLoader
from .models import (
    CoreResult,
    Diagnostic,
    FrozenProjectInput,
    SchedulingProfile,
    TaskNode,
    UNSUPPORTED_AXES,
    WorktreeSnapshot,
)
from .ownership import resolve_dirty_ownership
from .parallel import ParallelEngine
from .relationships import RelationshipEngine
from .scheduling import SchedulingParser


class DashboardCore:
    """Build deterministic nodes, relationships, actions and pair assessments."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.loader = FrozenInputLoader()
        self.gateway = ContractGateway(self.project_root)
        self.scheduling = SchedulingParser(self.project_root)
        self.relationships = RelationshipEngine()
        self.actions = ActionEngine()
        self.parallel = ParallelEngine()

    def inspect(
        self,
        *,
        worktrees: Mapping[str, WorktreeSnapshot] | None = None,
        worktree_candidates: Iterable[WorktreeSnapshot] | None = None,
    ) -> CoreResult:
        with self.lease_inspect(
            worktrees=worktrees,
            worktree_candidates=worktree_candidates,
        ) as result:
            return result

    @contextmanager
    def lease_inspect(
        self,
        *,
        worktrees: Mapping[str, WorktreeSnapshot] | None = None,
        worktree_candidates: Iterable[WorktreeSnapshot] | None = None,
    ) -> Iterator[CoreResult]:
        """Keep the frozen source lease active while a caller finalizes a candidate."""

        with self.loader.lease(self.project_root) as frozen:
            yield self._inspect_frozen(
                frozen,
                worktrees,
                tuple(worktree_candidates or ()),
            )

    def _inspect_frozen(
        self,
        frozen: FrozenProjectInput,
        worktrees: Mapping[str, WorktreeSnapshot] | None,
        worktree_candidates: tuple[WorktreeSnapshot, ...] = (),
    ) -> CoreResult:
        result, _ = self._inspect_frozen_with_profiles(
            frozen,
            worktrees,
            worktree_candidates,
        )
        return result

    def _inspect_frozen_with_profiles(
        self,
        frozen: FrozenProjectInput,
        worktrees: Mapping[str, WorktreeSnapshot] | None,
        worktree_candidates: tuple[WorktreeSnapshot, ...] = (),
        *,
        defer_parallel: bool = False,
    ) -> tuple[CoreResult, dict[str, SchedulingProfile]]:
        gateway_report = self.gateway.inspect(frozen)
        known_task_ids = frozenset(
            contract.task_id
            for contract in gateway_report.contracts
            if contract.task_id
        )
        frozen_by_source = frozen.by_source_path()
        self.scheduling.begin_inspection()
        profiles: dict[str, SchedulingProfile] = {}
        scheduling_diagnostics: list[Diagnostic] = []
        for contract in gateway_report.contracts:
            source = frozen_by_source.get(contract.source_path)
            if source is None:
                continue
            profile = self.scheduling.parse(source, contract.task_id, known_task_ids)
            profiles[contract.task_id] = profile
            scheduling_diagnostics.extend(profile.diagnostics)

        diagnostics = tuple(gateway_report.diagnostics) + tuple(scheduling_diagnostics)
        tasks = self._nodes(gateway_report.contracts, profiles, diagnostics)
        if worktrees is None and worktree_candidates:
            worktrees = self._map_worktree_candidates(tasks, worktree_candidates)
        edges, relationship_diagnostics = self.relationships.build(tasks, profiles, diagnostics)
        diagnostics = tuple(
            sorted(
                diagnostics + relationship_diagnostics,
                key=lambda item: (item.severity, item.code, item.diagnostic_id),
            )
        )
        tasks = self._replace_diagnostic_ids(tasks, diagnostics)
        actions = self.actions.recommend(tasks, edges, diagnostics)
        parallel = ()
        if not defer_parallel:
            resolved_worktrees = resolve_dirty_ownership(tasks, profiles, worktrees)
            parallel, parallel_diagnostics = self.parallel.assess_with_diagnostics(
                tasks,
                profiles,
                edges,
                resolved_worktrees,
                diagnostics,
            )
            diagnostics = tuple(
                sorted(
                    diagnostics + parallel_diagnostics,
                    key=lambda item: (item.severity, item.code, item.diagnostic_id),
                )
            )
        return CoreResult(
            frozen.manifest_sha256,
            tasks,
            edges,
            actions,
            parallel,
            diagnostics,
            gateway_report.projections,
        ), profiles

    @contextmanager
    def lease_inspect_deferred(
        self,
    ) -> Iterator[tuple[CoreResult, dict[str, SchedulingProfile]]]:
        """Parse frozen sources while Git evidence is collected independently."""

        with self.lease_frozen() as frozen:
            yield self.inspect_frozen_deferred(frozen)

    @contextmanager
    def lease_frozen(self) -> Iterator[FrozenProjectInput]:
        """Expose an active immutable input only to candidate orchestration."""

        with self.loader.lease(self.project_root) as frozen:
            yield frozen

    def inspect_frozen_deferred(
        self,
        frozen: FrozenProjectInput,
    ) -> tuple[CoreResult, dict[str, SchedulingProfile]]:
        if frozen.project_root != self.project_root:
            raise ValueError("frozen input belongs to a different project root")
        if not getattr(frozen.lease_guard, "active", False):
            raise ValueError("frozen input lease is not active")
        return self._inspect_frozen_with_profiles(
            frozen,
            None,
            (),
            defer_parallel=True,
        )

    def complete_parallel(
        self,
        result: CoreResult,
        profiles: dict[str, SchedulingProfile],
        worktree_candidates: Iterable[WorktreeSnapshot],
    ) -> CoreResult:
        mapping = self._map_worktree_candidates(
            result.tasks,
            tuple(worktree_candidates),
        )
        resolved = resolve_dirty_ownership(result.tasks, profiles, mapping)
        parallel, parallel_diagnostics = self.parallel.assess_with_diagnostics(
            result.tasks,
            profiles,
            result.edges,
            resolved,
            result.diagnostics,
        )
        diagnostics = tuple(
            sorted(
                result.diagnostics + parallel_diagnostics,
                key=lambda item: (item.severity, item.code, item.diagnostic_id),
            )
        )
        return replace(
            result,
            parallel_assessments=parallel,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _map_worktree_candidates(
        tasks: tuple[TaskNode, ...],
        candidates: tuple[WorktreeSnapshot, ...],
    ) -> dict[str, WorktreeSnapshot]:
        by_branch: dict[str, list[WorktreeSnapshot]] = defaultdict(list)
        for worktree in candidates:
            if worktree.branch:
                by_branch[worktree.branch].append(worktree)
        result: dict[str, WorktreeSnapshot] = {}
        for task in tasks:
            if not task.branch_hint:
                continue
            matches = by_branch.get(f"refs/heads/{task.branch_hint}", ())
            if len(matches) != 1:
                continue
            candidate = matches[0]
            if candidate.detached or candidate.locked or candidate.prunable:
                continue
            result[task.task_id] = candidate
        return result

    @staticmethod
    def _nodes(
        contracts,
        profiles: dict[str, SchedulingProfile],
        diagnostics: tuple[Diagnostic, ...],
    ) -> tuple[TaskNode, ...]:
        diagnostic_ids: dict[str, list[str]] = defaultdict(list)
        for diagnostic in diagnostics:
            for task_id in diagnostic.task_ids:
                diagnostic_ids[task_id].append(diagnostic.diagnostic_id)
        result: list[TaskNode] = []
        for contract in contracts:
            profile = profiles.get(contract.task_id, SchedulingProfile("absent", (), (), (), (), ()))
            values = dict(contract.normalized)
            result.append(
                TaskNode(
                    task_id=contract.task_id,
                    title=contract.title,
                    source_path=contract.source_path,
                    task_type=values.get("task_type"),
                    task_class=values.get("task_class"),
                    lifecycle=values.get("lifecycle"),
                    review_status=values.get("review_status"),
                    ua_level=values.get("ua_level"),
                    ua_status=values.get("ua_status"),
                    acceptance_authority=values.get("acceptance_authority"),
                    commit_status=DashboardCore._wire_axis_value(
                        "commit_status", values.get("commit_status")
                    ),
                    merge_status=DashboardCore._wire_axis_value(
                        "merge_status", values.get("merge_status")
                    ),
                    merge_authority=values.get("merge_authority"),
                    close_authority=values.get("close_authority"),
                    unsupported_axes=UNSUPPORTED_AXES,
                    scheduling_state=profile.state,
                    priority=profile.get("priority"),
                    risk_flags=tuple(profile.get("risk_flags") or ()),
                    write_scope=tuple(profile.get("write_scope") or ()),
                    module_locks=tuple(profile.get("module_locks") or ()),
                    parallel_intent=profile.get("parallel_intent"),
                    worktree_requirement=profile.get("worktree"),
                    branch_hint=profile.get("branch_hint"),
                    freshness="fresh",
                    diagnostic_ids=tuple(sorted(set(diagnostic_ids.get(contract.task_id, ())))),
                    provenance=tuple(
                        sorted(
                            contract.provenance + profile.provenance,
                            key=lambda item: (
                                item.source_path,
                                item.line,
                                item.field or "",
                                item.raw_value or "",
                            ),
                        )
                    ),
                )
            )
        return tuple(sorted(result, key=lambda item: item.task_id))

    @staticmethod
    def _wire_axis_value(axis: str, value: str | None) -> str | None:
        if axis in {"commit_status", "merge_status"} and value == "Not Recorded":
            return None
        return value

    @staticmethod
    def _replace_diagnostic_ids(
        tasks: tuple[TaskNode, ...],
        diagnostics: tuple[Diagnostic, ...],
    ) -> tuple[TaskNode, ...]:
        from dataclasses import replace

        by_task: dict[str, list[str]] = defaultdict(list)
        for diagnostic in diagnostics:
            for task_id in diagnostic.task_ids:
                by_task[task_id].append(diagnostic.diagnostic_id)
        return tuple(
            replace(task, diagnostic_ids=tuple(sorted(set(by_task.get(task.task_id, ())))))
            for task in tasks
        )
