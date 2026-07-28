"""End-to-end read-only dashboard core orchestration."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Mapping

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
    ) -> CoreResult:
        with self.loader.lease(self.project_root) as frozen:
            return self._inspect_frozen(frozen, worktrees)

    def _inspect_frozen(
        self,
        frozen: FrozenProjectInput,
        worktrees: Mapping[str, WorktreeSnapshot] | None,
    ) -> CoreResult:
        self.loader.verify_unchanged(frozen)
        gateway_report = self.gateway.inspect(frozen)
        self.loader.verify_unchanged(frozen)
        known_task_ids = {contract.task_id for contract in gateway_report.contracts if contract.task_id}
        frozen_by_source = frozen.by_source_path()
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
        edges, relationship_diagnostics = self.relationships.build(tasks, profiles, diagnostics)
        diagnostics = tuple(
            sorted(
                diagnostics + relationship_diagnostics,
                key=lambda item: (item.severity, item.code, item.diagnostic_id),
            )
        )
        tasks = self._replace_diagnostic_ids(tasks, diagnostics)
        actions = self.actions.recommend(tasks, edges, diagnostics)
        parallel = self.parallel.assess(tasks, profiles, edges, worktrees, diagnostics)
        self.loader.verify_unchanged(frozen)
        return CoreResult(
            frozen.manifest_sha256,
            tasks,
            edges,
            actions,
            parallel,
            diagnostics,
            gateway_report.projections,
        )

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
