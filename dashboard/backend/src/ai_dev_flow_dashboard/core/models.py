"""Frozen domain objects shared by the dashboard core and wire contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping


SCHEDULING_FIELDS = (
    "scheduling_schema",
    "priority",
    "depends_on",
    "replaces",
    "discovered_from",
    "parent",
    "conflicts_with",
    "parallel_intent",
    "write_scope",
    "module_locks",
    "worktree",
    "branch_hint",
    "risk_flags",
)

UNSUPPORTED_AXES = (
    "commit_authority",
    "release_status",
    "release_authority",
    "repair_authority",
)


def primitive(value: Any) -> Any:
    """Convert frozen domain values into JSON-compatible primitives."""

    if is_dataclass(value):
        return {key: primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [primitive(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


@dataclass(frozen=True)
class Provenance:
    source_path: str
    heading: str | None
    field: str | None
    line: int
    raw_value: str | None
    source_type: str


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    code: str
    severity: str
    message: str
    task_ids: tuple[str, ...]
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True)
class FrozenTaskInput:
    path: Path
    source_path: str
    content: bytes
    text: str
    mtime_ns: int
    size: int
    sha256: str
    ctime_ns: int | None = None
    file_identity: tuple[int, int] | None = None


@dataclass(frozen=True)
class FrozenProjectInput:
    project_root: Path
    tasks: tuple[FrozenTaskInput, ...]
    manifest_sha256: str
    lease_guard: Any = None

    def by_source_path(self) -> dict[str, FrozenTaskInput]:
        return {item.source_path: item for item in self.tasks}


@dataclass(frozen=True)
class CoreContract:
    task_id: str
    title: str
    source_path: str
    normalized: tuple[tuple[str, str | None], ...]
    diagnostics: tuple[Diagnostic, ...]
    provenance: tuple[Provenance, ...]

    def get(self, field: str, default: str | None = None) -> str | None:
        return dict(self.normalized).get(field, default)


@dataclass(frozen=True)
class ContractGatewayReport:
    contracts: tuple[CoreContract, ...]
    diagnostics: tuple[Diagnostic, ...]
    projections: Any
    summary: tuple[tuple[str, int], ...]
    disclaimer: str


@dataclass(frozen=True)
class DependencySpec:
    target_task_id: str
    axis: str
    expected: str
    provenance: Provenance


@dataclass(frozen=True)
class ScopeEntry:
    kind: str
    path: str
    comparison_segments: tuple[str, ...]
    provenance: Provenance

    @property
    def token(self) -> str:
        return f"{self.kind}:{self.path}"


@dataclass(frozen=True)
class SchedulingProfile:
    state: str
    values: tuple[tuple[str, Any], ...]
    dependencies: tuple[DependencySpec, ...]
    write_scope: tuple[ScopeEntry, ...]
    diagnostics: tuple[Diagnostic, ...]
    provenance: tuple[Provenance, ...]

    def get(self, field: str, default: Any = None) -> Any:
        return dict(self.values).get(field, default)


@dataclass(frozen=True)
class DependencyCondition:
    axis: str
    operator: str
    expected: str
    actual: str | None
    evaluation: str


@dataclass(frozen=True)
class TaskNode:
    task_id: str
    title: str
    source_path: str
    task_type: str | None
    task_class: str | None
    lifecycle: str | None
    review_status: str | None
    ua_level: str | None
    ua_status: str | None
    acceptance_authority: str | None
    commit_status: str | None
    merge_status: str | None
    merge_authority: str | None
    close_authority: str | None
    unsupported_axes: tuple[str, ...]
    scheduling_state: str
    priority: str | None
    risk_flags: tuple[str, ...]
    write_scope: tuple[str, ...]
    module_locks: tuple[str, ...]
    parallel_intent: str | None
    worktree_requirement: str | None
    branch_hint: str | None
    freshness: str
    diagnostic_ids: tuple[str, ...]
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True)
class RelationshipEdge:
    edge_id: str
    type: str
    source_task_id: str
    target_task_id: str
    condition: DependencyCondition | None
    storage_direction: str
    display_direction: str
    directional: bool
    origin: str
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True)
class ActionRecommendation:
    action_id: str
    task_id: str
    action_kind: str
    eligibility: str
    reason_codes: tuple[str, ...]
    blocking_task_ids: tuple[str, ...]
    blocking_condition_ids: tuple[str, ...]
    related_diagnostic_ids: tuple[str, ...]
    required_authority: str
    authority_state: str
    evidence: tuple[Provenance, ...]


@dataclass(frozen=True)
class WorktreeSnapshot:
    root: str
    head: str | None
    branch: str | None
    detached: bool
    locked: bool
    prunable: bool
    dirty_state: str
    dirty_paths: tuple[str, ...]
    diagnostic_ids: tuple[str, ...]


@dataclass(frozen=True)
class ParallelAssessment:
    assessment_id: str
    left_task_id: str
    right_task_id: str
    result: str
    reason_codes: tuple[str, ...]
    hard_conflicts: tuple[str, ...]
    projection_conflicts: tuple[str, ...]
    worktree_evidence: tuple[WorktreeSnapshot, ...]
    requires_user_confirmation: bool = True


@dataclass(frozen=True)
class CoreResult:
    manifest_sha256: str
    tasks: tuple[TaskNode, ...]
    edges: tuple[RelationshipEdge, ...]
    actions: tuple[ActionRecommendation, ...]
    parallel_assessments: tuple[ParallelAssessment, ...]
    diagnostics: tuple[Diagnostic, ...]
    projections: Any

    def to_dict(self) -> dict[str, Any]:
        return primitive(self)
