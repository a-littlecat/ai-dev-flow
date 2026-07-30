"""Fail-closed next-action matrix."""

from __future__ import annotations

from collections import defaultdict

from .canonical import stable_text_id
from .models import ActionRecommendation, Diagnostic, RelationshipEdge, TaskNode


ACTION_ORDER = {
    "none": 0,
    "repair": 1,
    "plan": 2,
    "execute": 3,
    "continue": 4,
    "review": 5,
    "user_decision": 6,
    "commit": 7,
    "merge": 8,
    "release": 9,
    "close": 10,
}

EVIDENCE_FIELDS_BY_REASON = {
    "CONTRACT_STATE_INVALID": (),
    "TERMINAL_STATE": ("lifecycle",),
    "REPAIR_AUTHORITY_UNSUPPORTED": ("lifecycle", "review_status"),
    "PLANNING_DECISION_REQUIRED": ("lifecycle",),
    "DEPENDENCY_STATE_UNKNOWN": ("lifecycle", "depends_on"),
    "DEPENDENCY_UNSATISFIED": ("lifecycle", "depends_on"),
    "EXECUTION_AUTHORITY_UNSUPPORTED": ("lifecycle",),
    "CONTINUE_AUTHORITY_UNSUPPORTED": ("lifecycle",),
    "REVIEW_AUTHORITY_UNSUPPORTED": ("lifecycle", "review_status"),
    "USER_DECISION_PENDING": ("lifecycle", "review_status", "ua_status"),
    "ACCEPTANCE_RECORD_PENDING": (
        "lifecycle",
        "review_status",
        "ua_status",
        "acceptance_authority",
    ),
    "COMMIT_AUTHORITY_UNSUPPORTED": ("lifecycle", "commit_status"),
    "MERGE_AUTHORITY_PRESENT": ("merge_status", "merge_authority"),
    "MERGE_AUTHORITY_DENIED": ("merge_status", "merge_authority"),
    "MERGE_AUTHORITY_REQUIRED": ("merge_status", "merge_authority"),
    "RELEASE_AXIS_UNSUPPORTED": ("merge_status",),
    "CLOSE_AUTHORITY_PRESENT": ("merge_status", "close_authority"),
    "CLOSE_AUTHORITY_DENIED": ("merge_status", "close_authority"),
    "CLOSE_AUTHORITY_REQUIRED": ("merge_status", "close_authority"),
    "STATE_COMBINATION_UNMAPPED": ("lifecycle", "review_status", "ua_status"),
}


class ActionEngine:
    def recommend(
        self,
        tasks: tuple[TaskNode, ...],
        edges: tuple[RelationshipEdge, ...],
        diagnostics: tuple[Diagnostic, ...],
    ) -> tuple[ActionRecommendation, ...]:
        dependencies: dict[str, list[RelationshipEdge]] = defaultdict(list)
        for edge in edges:
            if edge.type == "depends_on":
                dependencies[edge.source_task_id].append(edge)
        diagnostic_by_task: dict[str, list[Diagnostic]] = defaultdict(list)
        for diagnostic in diagnostics:
            for task_id in diagnostic.task_ids:
                diagnostic_by_task[task_id].append(diagnostic)

        result: list[ActionRecommendation] = []
        for task in tasks:
            task_diagnostics = tuple(diagnostic_by_task.get(task.task_id, ()))
            if task.scheduling_state == "invalid":
                related = tuple(
                    sorted(
                        item.diagnostic_id
                        for item in task_diagnostics
                        if item.severity in {"error", "violation"}
                    )
                )
                result.append(
                    self._make(
                        task,
                        "none",
                        "unknown",
                        "none",
                        "unknown",
                        "CONTRACT_STATE_INVALID",
                        related=related,
                    )
                )
                continue
            blocking_diagnostics = tuple(
                sorted(
                    (
                        item.diagnostic_id
                        for item in task_diagnostics
                        if self._invalidates_action(item)
                    )
                )
            )
            if blocking_diagnostics:
                result.append(
                    self._make(
                        task,
                        "none",
                        "unknown",
                        "none",
                        "unknown",
                        "CONTRACT_STATE_INVALID",
                        related=blocking_diagnostics,
                    )
                )
                continue

            lifecycle = task.lifecycle
            review = task.review_status
            if (
                task.scheduling_state in {"absent", "legacy_inferred"}
                and lifecycle in {"Ready", "In Progress"}
            ):
                result.append(
                    self._make(
                        task,
                        "none",
                        "unknown",
                        "none",
                        "unknown",
                        "STATE_COMBINATION_UNMAPPED",
                    )
                )
            elif lifecycle in {"Closed", "Cancelled"}:
                result.append(self._make(task, "none", "not_applicable", "none", "not_required", "TERMINAL_STATE"))
            elif review in {"Needs Fix", "Do Not Merge"} or lifecycle == "Needs Fix":
                result.append(
                    self._make(
                        task,
                        "repair",
                        "needs_authority",
                        "repair",
                        "unsupported",
                        "REPAIR_AUTHORITY_UNSUPPORTED",
                    )
                )
            elif lifecycle == "Draft":
                result.append(
                    self._make(
                        task,
                        "plan",
                        "needs_authority",
                        "user_decision",
                        "missing",
                        "PLANNING_DECISION_REQUIRED",
                    )
                )
            elif lifecycle == "Ready":
                task_dependencies = dependencies.get(task.task_id, ())
                dependency_diagnostics = tuple(
                    sorted(
                        item.diagnostic_id
                        for item in task_diagnostics
                        if self._invalidates_dependency_input(item)
                    )
                )
                unknown = [edge for edge in task_dependencies if edge.condition and edge.condition.evaluation == "unknown"]
                unsatisfied = [
                    edge for edge in task_dependencies if edge.condition and edge.condition.evaluation == "unsatisfied"
                ]
                if dependency_diagnostics:
                    result.append(
                        self._make(
                            task,
                            "execute",
                            "unknown",
                            "execution",
                            "unsupported",
                            "DEPENDENCY_STATE_UNKNOWN",
                            related=dependency_diagnostics,
                        )
                    )
                elif unknown:
                    result.append(
                        self._dependency_action(
                            task,
                            unknown,
                            "unknown",
                            "DEPENDENCY_STATE_UNKNOWN",
                        )
                    )
                elif unsatisfied:
                    result.append(
                        self._dependency_action(
                            task,
                            unsatisfied,
                            "blocked",
                            "DEPENDENCY_UNSATISFIED",
                        )
                    )
                else:
                    result.append(
                        self._make(
                            task,
                            "execute",
                            "needs_authority",
                            "execution",
                            "unsupported",
                            "EXECUTION_AUTHORITY_UNSUPPORTED",
                        )
                    )
            elif lifecycle == "In Progress":
                result.append(
                    self._make(
                        task,
                        "continue",
                        "needs_authority",
                        "execution",
                        "unsupported",
                        "CONTINUE_AUTHORITY_UNSUPPORTED",
                    )
                )
            elif lifecycle == "Review" and review in {"Pending", "In Review"}:
                result.append(
                    self._make(
                        task,
                        "review",
                        "needs_authority",
                        "review",
                        "unsupported",
                        "REVIEW_AUTHORITY_UNSUPPORTED",
                    )
                )
            elif lifecycle == "Review" and review == "Passed" and task.ua_status in {"Pending", "TBD"}:
                result.append(
                    self._make(
                        task,
                        "user_decision",
                        "actionable",
                        "user_decision",
                        "not_required",
                        "USER_DECISION_PENDING",
                    )
                )
            elif lifecycle == "Review" and review == "Passed" and task.ua_status in {"Passed", "Not Required"}:
                result.append(
                    self._make(
                        task,
                        "user_decision",
                        "actionable",
                        "user_decision",
                        "not_required",
                        "ACCEPTANCE_RECORD_PENDING",
                    )
                )
            elif lifecycle == "Accepted" and task.commit_status == "Uncommitted":
                result.append(
                    self._make(
                        task,
                        "commit",
                        "needs_authority",
                        "commit",
                        "unsupported",
                        "COMMIT_AUTHORITY_UNSUPPORTED",
                    )
                )
            elif task.commit_status == "Committed" and task.merge_status in {"Unmerged", "Deferred"}:
                if task.merge_authority == "User Authorized":
                    result.append(
                        self._make(task, "merge", "actionable", "merge", "present", "MERGE_AUTHORITY_PRESENT")
                    )
                elif task.merge_authority == "Denied":
                    result.append(
                        self._make(task, "merge", "blocked", "merge", "denied", "MERGE_AUTHORITY_DENIED")
                    )
                else:
                    result.append(
                        self._make(
                            task,
                            "merge",
                            "needs_authority",
                            "merge",
                            "missing",
                            "MERGE_AUTHORITY_REQUIRED",
                        )
                    )
            elif task.merge_status == "Merged" and lifecycle != "Closed":
                result.append(
                    self._make(
                        task,
                        "release",
                        "unknown",
                        "release",
                        "unsupported",
                        "RELEASE_AXIS_UNSUPPORTED",
                    )
                )
                if task.close_authority in {"User Authorized", "Rule Authorized"}:
                    result.append(
                        self._make(task, "close", "actionable", "close", "present", "CLOSE_AUTHORITY_PRESENT")
                    )
                elif task.close_authority == "Denied":
                    result.append(
                        self._make(task, "close", "blocked", "close", "denied", "CLOSE_AUTHORITY_DENIED")
                    )
                else:
                    result.append(
                        self._make(
                            task,
                            "close",
                            "needs_authority",
                            "close",
                            "missing",
                            "CLOSE_AUTHORITY_REQUIRED",
                        )
                    )
            else:
                result.append(
                    self._make(task, "none", "unknown", "none", "unknown", "STATE_COMBINATION_UNMAPPED")
                )
        return tuple(
            sorted(
                result,
                key=lambda item: (item.task_id, ACTION_ORDER[item.action_kind], item.action_id),
            )
        )

    @staticmethod
    def _invalidates_action(diagnostic: Diagnostic) -> bool:
        if diagnostic.severity not in {"error", "violation"}:
            return False
        if diagnostic.code.startswith(("E_", "V_")):
            return True
        if diagnostic.code in {
            "SCHEDULING_PARSE_ERROR",
            "SCHEDULING_UNKNOWN_FIELD",
            "SCHEDULING_DUPLICATE_FIELD",
            "SCHEDULING_MISSING_FIELD",
            "SCHEDULING_SCHEMA_UNSUPPORTED",
            "DEPENDENCY_CYCLE",
        }:
            return True
        return False

    @staticmethod
    def _invalidates_dependency_input(diagnostic: Diagnostic) -> bool:
        if diagnostic.severity not in {"error", "violation"}:
            return False
        if diagnostic.code == "DEPENDENCY_CYCLE":
            return False
        return diagnostic.code.startswith("DEPENDENCY_") or any(
            item.field == "depends_on" for item in diagnostic.provenance
        )

    def _dependency_action(
        self,
        task: TaskNode,
        edges: list[RelationshipEdge],
        eligibility: str,
        reason: str,
    ) -> ActionRecommendation:
        return self._make(
            task,
            "execute",
            eligibility,
            "execution",
            "unsupported",
            reason,
            blocking_tasks=tuple(sorted({edge.target_task_id for edge in edges})),
            blocking_conditions=tuple(sorted(edge.edge_id for edge in edges)),
        )

    @staticmethod
    def _make(
        task: TaskNode,
        action_kind: str,
        eligibility: str,
        required_authority: str,
        authority_state: str,
        reason: str,
        *,
        blocking_tasks: tuple[str, ...] = (),
        blocking_conditions: tuple[str, ...] = (),
        related: tuple[str, ...] = (),
    ) -> ActionRecommendation:
        evidence_fields = EVIDENCE_FIELDS_BY_REASON[reason]
        return ActionRecommendation(
            stable_text_id(task.task_id, action_kind),
            task.task_id,
            action_kind,
            eligibility,
            (reason,),
            blocking_tasks,
            blocking_conditions,
            related,
            required_authority,
            authority_state,
            tuple(
                item
                for item in task.provenance
                if item.field in evidence_fields
            ),
        )
