"""Conservative pairwise parallelism assessment."""

from __future__ import annotations

from collections import defaultdict, deque
from itertools import combinations, islice
from typing import Mapping

from .canonical import stable_text_id
from .models import (
    Diagnostic,
    ParallelAssessment,
    RelationshipEdge,
    SchedulingProfile,
    TaskNode,
    WorktreeSnapshot,
)
from .scheduling import scopes_overlap


REASON_ORDER = (
    "DEPENDENCY_PATH_PRESENT",
    "EXPLICIT_CONFLICT",
    "WRITE_SCOPE_OVERLAP",
    "MODULE_LOCK_OVERLAP",
    "SHARED_HIGH_RISK_SURFACE",
    "HIGH_RISK_SERIAL",
    "UA_LEVEL_SERIAL",
    "WORKTREE_EVIDENCE_UNKNOWN",
    "WORKTREE_SHARED",
    "DIRTY_OWNERSHIP_UNKNOWN",
    "PROJECTION_ONLY_CONFLICT",
    "ALL_CHECKS_PASSED",
)

SERIAL_RISKS = {
    "architecture",
    "data_migration",
    "delivery",
    "external_sync",
    "irreversible_action",
    "real_environment",
    "release",
}
EXCEPTION_RISKS = {"public_api", "security", "shared_component", "core_execution_path"}
MAX_PARALLEL_ASSESSMENTS = 256


class ParallelEngine:
    def assess(
        self,
        tasks: tuple[TaskNode, ...],
        profiles: dict[str, SchedulingProfile],
        edges: tuple[RelationshipEdge, ...],
        worktrees: Mapping[str, WorktreeSnapshot] | None = None,
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> tuple[ParallelAssessment, ...]:
        assessments, _ = self.assess_with_diagnostics(
            tasks,
            profiles,
            edges,
            worktrees,
            diagnostics,
        )
        return assessments

    def assess_with_diagnostics(
        self,
        tasks: tuple[TaskNode, ...],
        profiles: dict[str, SchedulingProfile],
        edges: tuple[RelationshipEdge, ...],
        worktrees: Mapping[str, WorktreeSnapshot] | None = None,
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> tuple[tuple[ParallelAssessment, ...], tuple[Diagnostic, ...]]:
        worktree_map = dict(worktrees or {})
        by_id = {task.task_id: task for task in tasks}
        diagnostic_by_id = {item.diagnostic_id: item for item in diagnostics}
        dependency_graph: dict[str, set[str]] = defaultdict(set)
        explicit_conflicts: set[frozenset[str]] = set()
        for edge in edges:
            if edge.type == "depends_on":
                dependency_graph[edge.source_task_id].add(edge.target_task_id)
            elif edge.type == "conflicts_with":
                explicit_conflicts.add(frozenset((edge.source_task_id, edge.target_task_id)))
        dependency_reachability = {
            task.task_id: self._reachable_nodes(task.task_id, dependency_graph)
            for task in tasks
        }
        profile_known = {
            task.task_id: (
                profiles.get(task.task_id) is not None
                and profiles[task.task_id].state
                not in {"absent", "invalid", "legacy_inferred"}
                and self._parallel_fields_known(profiles[task.task_id])
                and not self._parallel_input_blocked(task, diagnostic_by_id)
            )
            for task in tasks
        }
        lock_sets = {
            task.task_id: frozenset(task.module_locks)
            for task in tasks
        }

        result: list[ParallelAssessment] = []
        pair_count = len(tasks) * (len(tasks) - 1) // 2
        for left, right in islice(
            combinations(tasks, 2),
            MAX_PARALLEL_ASSESSMENTS,
        ):
            reasons: list[str] = []
            hard: list[str] = []
            projection: list[str] = []
            state = "candidate"
            left_profile = profiles.get(left.task_id)
            right_profile = profiles.get(right.task_id)
            if (
                not profile_known[left.task_id]
                or not profile_known[right.task_id]
            ):
                state = "unknown"
            elif (
                left_profile.get("parallel_intent") == "serial"
                or right_profile.get("parallel_intent") == "serial"
            ):
                state = "must_serial"
            elif (
                left_profile.get("parallel_intent") == "unknown"
                or right_profile.get("parallel_intent") == "unknown"
            ):
                state = "unknown"
            elif (
                left_profile.get("parallel_intent") != "consider"
                or right_profile.get("parallel_intent") != "consider"
            ):
                state = "unknown"
            elif (
                right.task_id in dependency_reachability[left.task_id]
                or left.task_id in dependency_reachability[right.task_id]
            ):
                state = "must_serial"
                hard.append("DEPENDENCY_PATH_PRESENT")
            elif frozenset((left.task_id, right.task_id)) in explicit_conflicts:
                state = "must_serial"
                hard.append("EXPLICIT_CONFLICT")
            else:
                overlaps = [
                    (left_scope, right_scope)
                    for left_scope in left_profile.write_scope
                    for right_scope in right_profile.write_scope
                    if scopes_overlap(left_scope, right_scope)
                ]
                if overlaps:
                    if all(
                        item[0].token == item[1].token == "file:docs/TASK_BOARD.md"
                        for item in overlaps
                    ):
                        projection.append("PROJECTION_ONLY_CONFLICT")
                    else:
                        state = "must_serial"
                        hard.append("WRITE_SCOPE_OVERLAP")
                if state == "candidate":
                    if lock_sets[left.task_id] & lock_sets[right.task_id]:
                        state = "must_serial"
                        hard.append("MODULE_LOCK_OVERLAP")

                if state == "candidate":
                    risk_result = self._risk_result(
                        left,
                        right,
                        profiles,
                        by_id,
                        diagnostic_by_id,
                    )
                    if risk_result == "serial":
                        state = "must_serial"
                        hard.append("HIGH_RISK_SERIAL")
                    elif risk_result == "shared":
                        state = "must_serial"
                        hard.append("SHARED_HIGH_RISK_SURFACE")
                    elif risk_result == "unknown":
                        state = "unknown"
                    elif self._ua_number(left.ua_level) >= 5 or self._ua_number(right.ua_level) >= 5:
                        state = "must_serial"
                        hard.append("UA_LEVEL_SERIAL")

                evidence = tuple(
                    item for item in (worktree_map.get(left.task_id), worktree_map.get(right.task_id)) if item
                )
                if state == "candidate":
                    if (
                        left.worktree_requirement != "required"
                        or right.worktree_requirement != "required"
                        or not left.branch_hint
                        or not right.branch_hint
                        or len(evidence) != 2
                    ):
                        state = "unknown"
                        reasons.append("WORKTREE_EVIDENCE_UNKNOWN")
                    elif evidence[0].root.casefold() == evidence[1].root.casefold():
                        state = "must_serial"
                        hard.append("WORKTREE_SHARED")
                    elif any(
                        item.detached
                        or item.locked
                        or item.prunable
                        or item.dirty_state == "unknown"
                        or item.diagnostic_ids
                        for item in evidence
                    ):
                        state = "unknown"
                        reasons.append("WORKTREE_EVIDENCE_UNKNOWN")
                    elif (
                        evidence[0].branch != f"refs/heads/{left.branch_hint}"
                        or evidence[1].branch != f"refs/heads/{right.branch_hint}"
                    ):
                        state = "unknown"
                        reasons.append("WORKTREE_EVIDENCE_UNKNOWN")
                    elif any(
                        not (
                            (item.dirty_state == "clean" and item.dirty_ownership == "clean")
                            or (
                                item.dirty_state == "dirty"
                                and item.dirty_ownership == "owned_by_task"
                            )
                        )
                        for item in evidence
                    ):
                        state = "unknown"
                        reasons.append("DIRTY_OWNERSHIP_UNKNOWN")

            evidence = tuple(
                item for item in (worktree_map.get(left.task_id), worktree_map.get(right.task_id)) if item
            )
            reasons.extend(hard)
            reasons.extend(projection)
            if state == "candidate":
                reasons.append("ALL_CHECKS_PASSED")
            elif state == "unknown" and not reasons:
                reasons.append("WORKTREE_EVIDENCE_UNKNOWN")
            ordered_reasons = tuple(reason for reason in REASON_ORDER if reason in set(reasons))
            ordered_hard = tuple(reason for reason in REASON_ORDER if reason in set(hard))
            ordered_projection = tuple(reason for reason in REASON_ORDER if reason in set(projection))
            left_id, right_id = sorted((left.task_id, right.task_id))
            result.append(
                ParallelAssessment(
                    stable_text_id("parallel", left_id, right_id),
                    left_id,
                    right_id,
                    state,
                    ordered_reasons,
                    ordered_hard,
                    ordered_projection,
                    tuple(sorted(evidence, key=lambda item: item.root.casefold())),
                    True,
                )
            )
        selected = tuple(result)
        if pair_count <= MAX_PARALLEL_ASSESSMENTS:
            return selected, ()
        message = (
            f"Parallel assessments truncated: total={pair_count};"
            f"published={MAX_PARALLEL_ASSESSMENTS};"
            "selection=lexicographic_pair_order"
        )
        diagnostic = Diagnostic(
            stable_text_id("diagnostic", "PARALLEL_ASSESSMENT_TRUNCATED", message),
            "PARALLEL_ASSESSMENT_TRUNCATED",
            "warning",
            message,
            (),
            (),
        )
        return selected, (diagnostic,)

    @staticmethod
    def _parallel_fields_known(profile: SchedulingProfile) -> bool:
        return profile.get("parallel_intent") in {"serial", "consider", "unknown"} and all(
            profile.get(field) is not None
            for field in (
                "depends_on",
                "conflicts_with",
                "write_scope",
                "module_locks",
                "worktree",
                "risk_flags",
            )
        )

    @staticmethod
    def _parallel_input_blocked(
        task: TaskNode,
        diagnostic_by_id: Mapping[str, Diagnostic],
    ) -> bool:
        parallel_fields = {
            "task_type",
            "task_class",
            "lifecycle",
            "review_status",
            "ua_level",
            "ua_status",
            "acceptance_authority",
            "commit_status",
            "merge_status",
            "merge_authority",
            "close_authority",
            "depends_on",
            "conflicts_with",
            "parallel_intent",
            "write_scope",
            "module_locks",
            "worktree",
            "branch_hint",
            "risk_flags",
        }
        for diagnostic_id in task.diagnostic_ids:
            diagnostic = diagnostic_by_id.get(diagnostic_id)
            if diagnostic is None:
                return True
            if diagnostic.severity not in {"error", "violation"}:
                continue
            if diagnostic.code in {
                "E_PARSE",
                "E_TASK_ID_CONFLICT",
                "V_STATE_GUARD",
                "SCHEDULING_PARSE_ERROR",
                "SCHEDULING_UNKNOWN_FIELD",
                "SCHEDULING_DUPLICATE_FIELD",
                "SCHEDULING_MISSING_FIELD",
                "SCHEDULING_SCHEMA_UNSUPPORTED",
                "DEPENDENCY_CYCLE",
            }:
                return True
            if diagnostic.code in {"E_UNKNOWN_VALUE", "E_LEGACY_CONFLICT"} and not diagnostic.provenance:
                return True
            if any(item.field in parallel_fields for item in diagnostic.provenance):
                return True
        return False

    @staticmethod
    def _reachable_nodes(
        source: str,
        graph: Mapping[str, set[str]],
    ) -> frozenset[str]:
        pending = deque([source])
        visited: set[str] = set()
        reachable: set[str] = set()
        while pending:
            current = pending.popleft()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in graph.get(current, ()):
                reachable.add(neighbor)
                pending.append(neighbor)
        reachable.discard(source)
        return frozenset(reachable)

    def _risk_result(
        self,
        left: TaskNode,
        right: TaskNode,
        profiles: dict[str, SchedulingProfile],
        tasks: dict[str, TaskNode],
        diagnostic_by_id: Mapping[str, Diagnostic],
    ) -> str:
        risks = set(left.risk_flags) | set(right.risk_flags)
        if risks & SERIAL_RISKS:
            return "serial"
        exception_surface = risks & EXCEPTION_RISKS
        class_d = left.task_class == "D" or right.task_class == "D"
        if not exception_surface and not class_d:
            return "safe"
        exception = self._accepted_contract_exception(
            left,
            right,
            profiles,
            tasks,
            diagnostic_by_id,
        )
        if exception is True:
            return "safe"
        if exception is None:
            return "unknown"
        return "shared" if exception_surface else "serial"

    @staticmethod
    def _accepted_contract_exception(
        left: TaskNode,
        right: TaskNode,
        profiles: dict[str, SchedulingProfile],
        tasks: dict[str, TaskNode],
        diagnostic_by_id: Mapping[str, Diagnostic],
    ) -> bool | None:
        if left.parallel_intent != "consider" or right.parallel_intent != "consider":
            return False
        if set(left.risk_flags + right.risk_flags) & SERIAL_RISKS:
            return False
        left_profile = profiles[left.task_id]
        right_profile = profiles[right.task_id]
        required = {
            ("commit_status", "Committed"),
            ("lifecycle", "Accepted"),
            ("review_status", "Passed"),
            ("ua_status", "Passed"),
        }
        left_by_target: dict[str, set[tuple[str, str]]] = defaultdict(set)
        right_by_target: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for dependency in left_profile.dependencies:
            left_by_target[dependency.target_task_id].add((dependency.axis, dependency.expected))
        for dependency in right_profile.dependencies:
            right_by_target[dependency.target_task_id].add((dependency.axis, dependency.expected))
        common = sorted(set(left_by_target) & set(right_by_target))
        if not common:
            return None
        owners = [
            target
            for target in common
            if required <= left_by_target[target] and required <= right_by_target[target]
        ]
        if len(owners) != 1:
            return None
        owner_id = owners[0]
        owner = tasks.get(owner_id)
        owner_profile = profiles.get(owner_id)
        if owner is None or owner_profile is None:
            return None
        if ParallelEngine._parallel_input_blocked(owner, diagnostic_by_id):
            return None
        if (
            owner.lifecycle != "Accepted"
            or owner.review_status != "Passed"
            or owner.ua_status != "Passed"
            or owner.commit_status != "Committed"
        ):
            return None
        contract_segments = ("dashboard", "contracts")
        owner_covers = any(
            scope.kind == "dir"
            and len(scope.comparison_segments) <= len(contract_segments)
            and contract_segments[: len(scope.comparison_segments)] == scope.comparison_segments
            for scope in owner_profile.write_scope
        )
        consumer_writes_contract = any(
            scope.comparison_segments[: len(contract_segments)] == contract_segments
            or contract_segments[: len(scope.comparison_segments)] == scope.comparison_segments
            for scope in left_profile.write_scope + right_profile.write_scope
        )
        if consumer_writes_contract:
            return False
        if not owner_covers:
            return None
        return True

    @staticmethod
    def _ua_number(value: str | None) -> int:
        if value and value.startswith("UA") and value[2:].isdigit():
            return int(value[2:])
        return 99
