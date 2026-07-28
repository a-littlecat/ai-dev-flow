"""Relationship graph construction, condition evaluation and cycle detection."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import replace
from typing import Iterable

from .canonical import stable_text_id
from .models import (
    DependencyCondition,
    Diagnostic,
    Provenance,
    RelationshipEdge,
    SchedulingProfile,
    TaskNode,
)


DIRECTIONS = {
    "depends_on": ("dependent_to_prerequisite", "prerequisite_to_dependent", True),
    "parent": ("child_to_parent", "parent_to_child", True),
    "replaces": ("replacement_to_replaced", "replaced_to_replacement", True),
    "discovered_from": ("discovered_to_origin", "origin_to_discovered", True),
    "conflicts_with": ("symmetric", "symmetric", False),
}


def _graph_diag(code: str, message: str, task_ids: Iterable[str], provenance: Iterable[Provenance]) -> Diagnostic:
    tasks = tuple(sorted(set(task_ids)))
    prov = tuple(provenance)
    path = prov[0].source_path if prov else ""
    line = prov[0].line if prov else 0
    return Diagnostic(
        stable_text_id("diagnostic", code, path, str(line), message, *tasks),
        code,
        "error",
        message,
        tasks,
        prov,
    )


class RelationshipEngine:
    def build(
        self,
        tasks: tuple[TaskNode, ...],
        profiles: dict[str, SchedulingProfile],
        contract_diagnostics: tuple[Diagnostic, ...] = (),
    ) -> tuple[tuple[RelationshipEdge, ...], tuple[Diagnostic, ...]]:
        by_id = {task.task_id: task for task in tasks}
        diagnostics_by_task: dict[str, list[Diagnostic]] = defaultdict(list)
        for diagnostic in contract_diagnostics:
            for task_id in diagnostic.task_ids:
                diagnostics_by_task[task_id].append(diagnostic)
        edges: dict[str, RelationshipEdge] = {}
        diagnostics: list[Diagnostic] = []

        for task in tasks:
            profile = profiles.get(task.task_id)
            if profile is None or profile.state not in {"canonical", "legacy_inferred"}:
                continue
            origin = "canonical" if profile.state == "canonical" else "legacy_inferred"
            for dependency in profile.dependencies:
                target = by_id.get(dependency.target_task_id)
                if target is None:
                    diagnostics.append(
                        _graph_diag(
                            "RELATIONSHIP_DANGLING_REFERENCE",
                            f"depends_on target does not exist: {dependency.target_task_id}",
                            (task.task_id,),
                            (dependency.provenance,),
                        )
                    )
                    continue
                actual = getattr(target, dependency.axis, None)
                evaluation = (
                    "unknown"
                    if actual is None
                    or self._target_axis_is_blocked(
                        target,
                        dependency.axis,
                        tuple(diagnostics_by_task.get(target.task_id, ())),
                    )
                    else ("satisfied" if actual == dependency.expected else "unsatisfied")
                )
                condition = DependencyCondition(
                    dependency.axis,
                    "eq",
                    dependency.expected,
                    actual,
                    evaluation,
                )
                edge_id = stable_text_id(
                    "depends_on",
                    task.task_id,
                    target.task_id,
                    dependency.axis,
                    dependency.expected,
                )
                edges[edge_id] = RelationshipEdge(
                    edge_id,
                    "depends_on",
                    task.task_id,
                    target.task_id,
                    condition,
                    *DIRECTIONS["depends_on"],
                    origin,
                    (dependency.provenance,),
                )

            for relation in ("parent", "replaces", "discovered_from", "conflicts_with"):
                raw_targets = profile.get(relation)
                if raw_targets is None:
                    continue
                targets = (raw_targets,) if isinstance(raw_targets, str) else tuple(raw_targets)
                for target_id in targets:
                    if target_id not in by_id:
                        diagnostics.append(
                            _graph_diag(
                                "RELATIONSHIP_DANGLING_REFERENCE",
                                f"{relation} target does not exist: {target_id}",
                                (task.task_id,),
                                tuple(item for item in profile.provenance if item.field == relation),
                            )
                        )
                        continue
                    source_id = task.task_id
                    if relation == "conflicts_with":
                        source_id, target_id = sorted((source_id, target_id))
                    edge_id = stable_text_id(relation, source_id, target_id)
                    provenance = tuple(item for item in profile.provenance if item.field == relation)
                    previous = edges.get(edge_id)
                    if previous is not None:
                        combined = tuple(
                            sorted(
                                set(previous.provenance + provenance),
                                key=lambda item: (
                                    item.source_path,
                                    item.line,
                                    item.field or "",
                                    item.raw_value or "",
                                ),
                            )
                        )
                        edges[edge_id] = RelationshipEdge(
                            previous.edge_id,
                            previous.type,
                            previous.source_task_id,
                            previous.target_task_id,
                            previous.condition,
                            previous.storage_direction,
                            previous.display_direction,
                            previous.directional,
                            previous.origin,
                            combined,
                        )
                        continue
                    storage, display, directional = DIRECTIONS[relation]
                    edges[edge_id] = RelationshipEdge(
                        edge_id,
                        relation,
                        source_id,
                        target_id,
                        None,
                        storage,
                        display,
                        directional,
                        origin,
                        provenance,
                    )

        ordered_edges = tuple(sorted(edges.values(), key=lambda item: item.edge_id))
        dependency_cycle_diagnostics = self._cycle_diagnostics(
            ordered_edges,
            "depends_on",
            "DEPENDENCY_CYCLE",
        )
        diagnostics.extend(dependency_cycle_diagnostics)
        diagnostics.extend(self._cycle_diagnostics(ordered_edges, "replaces", "REPLACES_CYCLE"))
        ordered_edges = self._propagate_dependency_cycle_unknown(
            ordered_edges,
            tuple(dependency_cycle_diagnostics),
        )
        return ordered_edges, tuple(sorted(diagnostics, key=lambda item: item.diagnostic_id))

    @staticmethod
    def _propagate_dependency_cycle_unknown(
        edges: tuple[RelationshipEdge, ...],
        diagnostics: tuple[Diagnostic, ...],
    ) -> tuple[RelationshipEdge, ...]:
        blocked = {
            task_id
            for diagnostic in diagnostics
            for task_id in diagnostic.task_ids
        }
        if not blocked:
            return edges
        dependency_edges = tuple(edge for edge in edges if edge.type == "depends_on")
        changed = True
        while changed:
            changed = False
            for edge in dependency_edges:
                if edge.target_task_id in blocked and edge.source_task_id not in blocked:
                    blocked.add(edge.source_task_id)
                    changed = True
        return tuple(
            replace(
                edge,
                condition=replace(edge.condition, evaluation="unknown"),
            )
            if (
                edge.type == "depends_on"
                and edge.condition is not None
                and edge.target_task_id in blocked
            )
            else edge
            for edge in edges
        )

    @staticmethod
    def _target_axis_is_blocked(
        task: TaskNode,
        axis: str,
        diagnostics: tuple[Diagnostic, ...],
    ) -> bool:
        """Fail closed when the target contract cannot prove the requested axis."""

        known_ids = {item.diagnostic_id for item in diagnostics}
        if any(diagnostic_id not in known_ids for diagnostic_id in task.diagnostic_ids):
            return True
        for diagnostic in diagnostics:
            if diagnostic.severity not in {"error", "violation"}:
                continue
            if diagnostic.code in {"E_PARSE", "E_TASK_ID_CONFLICT", "V_STATE_GUARD"}:
                return True
            if not diagnostic.provenance:
                return True
            fields = {item.field for item in diagnostic.provenance}
            if None in fields or axis in fields:
                return True
        return False

    def _cycle_diagnostics(
        self,
        edges: tuple[RelationshipEdge, ...],
        relation: str,
        code: str,
    ) -> list[Diagnostic]:
        relevant = [edge for edge in edges if edge.type == relation]
        if not relevant:
            return []
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in relevant:
            adjacency[edge.source_task_id].append(edge.target_task_id)
        for targets in adjacency.values():
            targets.sort()

        nodes = {
            edge.source_task_id
            for edge in relevant
        } | {
            edge.target_task_id
            for edge in relevant
        }
        indegree = {node: 0 for node in nodes}
        for targets in adjacency.values():
            for target in targets:
                indegree[target] += 1
        ready = deque(node for node, degree in indegree.items() if degree == 0)
        visited = 0
        while ready:
            node = ready.popleft()
            visited += 1
            for target in adjacency.get(node, ()):
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
        if visited == len(nodes):
            # Most project graphs are DAGs.  Avoid the more expensive SCC pass
            # unless Kahn's linear proof shows that a cycle actually exists.
            return []

        # Use an iterative Kosaraju pass for cyclic graphs.  The supported
        # 1000-TASK contract must not depend on Python's recursion limit.
        finish_order: list[str] = []
        visited: set[str] = set()
        for start in sorted(nodes):
            if start in visited:
                continue
            visited.add(start)
            frames: list[tuple[str, int]] = [(start, 0)]
            while frames:
                node, offset = frames[-1]
                targets = adjacency.get(node, ())
                if offset < len(targets):
                    target = targets[offset]
                    frames[-1] = (node, offset + 1)
                    if target not in visited:
                        visited.add(target)
                        frames.append((target, 0))
                    continue
                finish_order.append(node)
                frames.pop()

        reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        for source, targets in adjacency.items():
            for target in targets:
                reverse_adjacency[target].append(source)
        for sources in reverse_adjacency.values():
            sources.sort()

        components: list[tuple[str, ...]] = []
        assigned: set[str] = set()
        for start in reversed(finish_order):
            if start in assigned:
                continue
            assigned.add(start)
            component: list[str] = []
            pending = [start]
            while pending:
                node = pending.pop()
                component.append(node)
                for source in reversed(reverse_adjacency.get(node, ())):
                    if source not in assigned:
                        assigned.add(source)
                        pending.append(source)
            components.append(tuple(sorted(component)))

        result: list[Diagnostic] = []
        for component in sorted(components):
            cyclic = len(component) > 1 or any(
                edge.source_task_id == edge.target_task_id == component[0] for edge in relevant
            )
            if not cyclic:
                continue
            component_set = set(component)
            cycle_edges = [
                edge
                for edge in relevant
                if edge.source_task_id in component_set and edge.target_task_id in component_set
            ]
            provenance = tuple(item for edge in cycle_edges for item in edge.provenance)
            result.append(
                _graph_diag(
                    code,
                    f"{relation} cycle detected: {' -> '.join(component)}",
                    component,
                    provenance,
                )
            )
        return result
