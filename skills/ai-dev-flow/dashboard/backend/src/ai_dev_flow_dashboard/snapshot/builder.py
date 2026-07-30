"""Build complete immutable fresh/stale/partial dashboard snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ai_dev_flow_dashboard.core import (
    DashboardCore,
    canonical_bytes,
    resolve_dirty_ownership_for_tasks,
    snapshot_revision,
    validate_contract,
    validated_canonical_bytes,
)
from ai_dev_flow_dashboard.core.canonical import canonical_sha256, stable_text_id
from ai_dev_flow_dashboard.core.models import (
    CoreResult,
    Diagnostic,
    TaskNode,
    primitive,
)
from ai_dev_flow_dashboard.git_snapshot import GitCollection, GitSnapshotCollector
from ai_dev_flow_dashboard.git_snapshot.diagnostics import git_diagnostic


DISCLAIMER = (
    "本快照是只读派生视图；自动验证、Review、UA、Accepted、commit、merge、release、"
    "delivery 与 Closed 相互独立，任何建议均不构成执行或交付授权。"
)
LIFECYCLES = (
    "Draft",
    "Ready",
    "In Progress",
    "Blocked",
    "Review",
    "Needs Fix",
    "Accepted",
    "Closed",
    "Deferred",
    "Cancelled",
)
ACTIONS = (
    "plan",
    "execute",
    "continue",
    "review",
    "repair",
    "user_decision",
    "commit",
    "merge",
    "release",
    "close",
    "none",
)
SEVERITIES = ("error", "violation", "warning", "info")
RELATIONS = ("depends_on", "parent", "replaces", "discovered_from", "conflicts_with")
SUPPORTED_ACTIONS = ACTIONS
UNSUPPORTED_AXES = (
    "commit_authority",
    "release_status",
    "release_authority",
    "repair_authority",
)
AUTHORITY_SOURCES = ("acceptance_authority", "merge_authority", "close_authority")
_TASK_ID_LINE = re.compile(r"^- `task_id`: `([^`\r\n]+)`$")
_BRANCH_HINT_LINE = re.compile(r"^- `branch_hint`: `([^`\r\n]+)`$")
_TASK_SEMANTICS_CACHE: dict[str, dict[str, bytes]] = {}


@dataclass(frozen=True)
class SnapshotBuildResult:
    snapshot: dict[str, Any]
    source_digest: str
    git: GitCollection
    last_good_source_digest: str | None
    payload: bytes | None = None


@dataclass(frozen=True)
class _CachedCandidate:
    source_digest: str
    git: GitCollection
    last_good_source_digest: str | None
    payload: bytes
    snapshot_pickle: bytes | None = None


class SnapshotBuilder:
    def __init__(
        self,
        project_root: str | Path,
        *,
        skill_root: str | Path | None = None,
        core: DashboardCore | None = None,
        git_collector: GitSnapshotCollector | None = None,
        schema_path: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        if not (self.project_root / "docs" / "tasks").is_dir():
            raise ValueError("project root must contain docs/tasks")
        self.core = core or DashboardCore(
            self.project_root,
            skill_root=skill_root,
        )
        self.git_collector = git_collector or GitSnapshotCollector(self.project_root)
        self.schema_path = (
            Path(schema_path).resolve()
            if schema_path is not None
            else (
                Path(__file__).resolve().parents[4]
                / "contracts"
                / "dashboard-contracts-v1.schema.json"
            ).resolve()
        )
        self._startup_schema_content = self.schema_path.read_bytes()
        self._startup_schema_content.decode("utf-8", errors="strict")
        json.loads(self._startup_schema_content)
        self._last_good_payload: bytes | None = None
        self._last_good_source_digest: str | None = None
        self._candidate_cache: dict[
            tuple[str, str, str],
            _CachedCandidate,
        ] = {}

    def build(self) -> SnapshotBuildResult:
        schema_before = self.schema_digest()
        if hasattr(self.core, "lease_inspect_deferred") or (
            hasattr(self.core, "lease_frozen")
            and hasattr(self.core, "inspect_frozen_deferred")
        ):
            return self._build_deferred()
        source_before = canonical_sha256({"source": "unavailable"})
        leased = hasattr(self.core, "lease_inspect")
        if leased:
            git_before = self.git_collector.collect()
            provisional_mapping: dict[str, Any] = {}
            mapping_diagnostics: tuple[Diagnostic, ...] = ()
        else:
            with ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="dashboard-snapshot-read",
            ) as executor:
                git_future = executor.submit(self.git_collector.collect)
                hints_future = executor.submit(self._strict_branch_hints)
            git_before = git_future.result()
            provisional_hints = hints_future.result()
            provisional_mapping, mapping_diagnostics = self._map_hints(
                git_before,
                provisional_hints,
            )
        try:
            inspection = (
                self.core.lease_inspect(
                    worktree_candidates=git_before.worktrees,
                )
                if leased
                else nullcontext(self.core.inspect(worktrees=provisional_mapping))
            )
            with inspection as core_result:
                source_before = core_result.manifest_sha256
                if leased:
                    resolved_mapping, mapping_diagnostics = git_before.map_tasks(
                        core_result.tasks
                    )
                else:
                    resolved_mapping = resolve_dirty_ownership_for_tasks(
                        core_result.tasks,
                        provisional_mapping,
                    )
                source_after = source_before if leased else self.source_digest()
                return self._complete_candidate(
                    core_result,
                    git_before,
                    resolved_mapping,
                    mapping_diagnostics,
                    source_before,
                    source_after,
                    schema_before,
                )
        except Exception as exc:
            current_digest = self._safe_source_digest(source_before, exc)
            diagnostic = self._build_failure_diagnostic(exc)
            snapshot, payload = self._failure_snapshot(
                git_before,
                current_digest=current_digest,
                diagnostic=diagnostic,
            )
            return SnapshotBuildResult(
                snapshot,
                current_digest,
                git_before,
                self._last_good_source_digest,
                payload,
            )

    def _build_deferred(self) -> SnapshotBuildResult:
        schema_before = self.schema_digest()
        if hasattr(self.core, "lease_frozen") and hasattr(
            self.core,
            "inspect_frozen_deferred",
        ):
            return self._build_cached_deferred()
        source_before = canonical_sha256({"source": "unavailable"})
        git_before: GitCollection | None = None
        try:
            with ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="dashboard-snapshot-git",
            ) as executor:
                git_future = executor.submit(self.git_collector.collect)
                with self.core.lease_inspect_deferred() as deferred:
                    core_result, profiles = deferred
                    git_before = git_future.result()
                    core_result = self.core.complete_parallel(
                        core_result,
                        profiles,
                        git_before.worktrees,
                    )
                    source_before = core_result.manifest_sha256
                    resolved_mapping, mapping_diagnostics = git_before.map_tasks(
                        core_result.tasks
                    )
                    return self._complete_candidate(
                        core_result,
                        git_before,
                        resolved_mapping,
                        mapping_diagnostics,
                        source_before,
                        source_before,
                        schema_before,
                        reuse_git_snapshot=True,
                    )
        except Exception as exc:
            if git_before is None:
                git_before = self.git_collector.collect()
            current_digest = self._safe_source_digest(source_before, exc)
            diagnostic = self._build_failure_diagnostic(exc)
            snapshot, payload = self._failure_snapshot(
                git_before,
                current_digest=current_digest,
                diagnostic=diagnostic,
            )
            return SnapshotBuildResult(
                snapshot,
                current_digest,
                git_before,
                self._last_good_source_digest,
                payload,
            )

    def _build_cached_deferred(self) -> SnapshotBuildResult:
        schema_before = self.schema_digest()
        source_before = canonical_sha256({"source": "unavailable"})
        git_before: GitCollection | None = None
        try:
            with ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="dashboard-snapshot-git",
            ) as executor:
                git_future = executor.submit(self.git_collector.collect)
                with self.core.lease_frozen() as frozen:
                    source_before = frozen.manifest_sha256
                    source_is_cached = any(
                        key[0] == source_before and key[2] == schema_before
                        for key in self._candidate_cache
                    )
                    if source_is_cached:
                        git_before = git_future.result()
                        cached = self._candidate_cache.get(
                            (
                                source_before,
                                git_before.fingerprint,
                                schema_before,
                            )
                        )
                        if cached is not None:
                            return self._reuse_candidate(
                                cached,
                                git_before,
                                schema_before,
                                (
                                    source_before,
                                    git_before.fingerprint,
                                    schema_before,
                                ),
                            )
                        core_result, profiles = self.core.inspect_frozen_deferred(
                            frozen
                        )
                    else:
                        core_result, profiles = self.core.inspect_frozen_deferred(
                            frozen
                        )
                        git_before = git_future.result()
                    core_result = self.core.complete_parallel(
                        core_result,
                        profiles,
                        git_before.worktrees,
                    )
                    resolved_mapping, mapping_diagnostics = git_before.map_tasks(
                        core_result.tasks
                    )
                    return self._complete_candidate(
                        core_result,
                        git_before,
                        resolved_mapping,
                        mapping_diagnostics,
                        source_before,
                        source_before,
                        schema_before,
                        reuse_git_snapshot=True,
                    )
        except Exception as exc:
            if git_before is None:
                git_before = self.git_collector.collect()
            current_digest = self._safe_source_digest(source_before, exc)
            diagnostic = self._build_failure_diagnostic(exc)
            snapshot, payload = self._failure_snapshot(
                git_before,
                current_digest=current_digest,
                diagnostic=diagnostic,
            )
            return SnapshotBuildResult(
                snapshot,
                current_digest,
                git_before,
                self._last_good_source_digest,
                payload,
            )

    def _reuse_candidate(
        self,
        cached: _CachedCandidate,
        git: GitCollection,
        schema_before: str,
        cache_key: tuple[str, str, str],
    ) -> SnapshotBuildResult:
        del git
        if self.schema_digest() != schema_before:
            raise SnapshotInputChanged(
                "dashboard contract schema changed during candidate reuse"
            )
        if cached.snapshot_pickle is None:
            import pickle

            snapshot = json.loads(cached.payload)
            cached = replace(
                cached,
                snapshot_pickle=pickle.dumps(
                    snapshot,
                    protocol=pickle.HIGHEST_PROTOCOL,
                ),
            )
            self._candidate_cache[cache_key] = cached
        else:
            import pickle

            snapshot = pickle.loads(cached.snapshot_pickle)
        result = SnapshotBuildResult(
            snapshot,
            cached.source_digest,
            cached.git,
            cached.last_good_source_digest,
            cached.payload,
        )
        self._last_good_payload = cached.payload
        self._last_good_source_digest = cached.source_digest
        return result

    def _complete_candidate(
        self,
        core_result: CoreResult,
        git_before: GitCollection,
        resolved_mapping: dict[str, Any],
        mapping_diagnostics: tuple[Diagnostic, ...],
        source_before: str,
        source_after: str,
        schema_before: str,
        *,
        git_after_future: Future[GitCollection] | None = None,
        reuse_git_snapshot: bool = False,
    ) -> SnapshotBuildResult:
        self._verify_provisional_mapping(core_result.tasks, resolved_mapping)
        resolved_git_before = _with_resolved_ownership(
            git_before,
            resolved_mapping,
        )
        if reuse_git_snapshot:
            snapshot, payload = self._fresh_snapshot(
                core_result,
                resolved_git_before,
                tuple(resolved_git_before.diagnostics)
                + tuple(mapping_diagnostics),
            )
            git_after = git_before
        elif git_after_future is None:
            with ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="dashboard-snapshot-finalize",
            ) as executor:
                local_git_future = executor.submit(self.git_collector.collect)
                snapshot_future = executor.submit(
                    self._fresh_snapshot,
                    core_result,
                    resolved_git_before,
                    tuple(resolved_git_before.diagnostics)
                    + tuple(mapping_diagnostics),
                )
            git_after = local_git_future.result()
            snapshot, payload = snapshot_future.result()
        else:
            snapshot, payload = self._fresh_snapshot(
                core_result,
                resolved_git_before,
                tuple(resolved_git_before.diagnostics)
                + tuple(mapping_diagnostics),
            )
            git_after = git_after_future.result()
        if source_before != source_after:
            raise SnapshotInputChanged(
                "project source manifest changed during snapshot build"
            )
        if git_before.fingerprint != git_after.fingerprint:
            raise SnapshotInputChanged(
                "Git/Worktree evidence changed during snapshot build"
            )
        if schema_before != self.schema_digest():
            raise SnapshotInputChanged(
                "dashboard contract schema changed during snapshot build"
            )
        resolved_git = _with_resolved_ownership(git_after, resolved_mapping)
        self._last_good_payload = payload
        self._last_good_source_digest = source_after
        result = SnapshotBuildResult(
            snapshot,
            source_after,
            resolved_git,
            self._last_good_source_digest,
            payload,
        )
        self._remember_candidate(
            (source_after, git_before.fingerprint, schema_before),
            result,
        )
        return result

    def _remember_candidate(
        self,
        key: tuple[str, str, str],
        result: SnapshotBuildResult,
    ) -> None:
        if len(self._candidate_cache) >= 8 and key not in self._candidate_cache:
            self._candidate_cache.pop(next(iter(self._candidate_cache)))
        payload = result.payload or canonical_bytes(result.snapshot)
        self._candidate_cache[key] = _CachedCandidate(
            result.source_digest,
            result.git,
            result.last_good_source_digest,
            payload,
        )

    def schema_digest(self) -> str:
        content = self.schema_path.read_bytes()
        content.decode("utf-8", errors="strict")
        json.loads(content)
        return hashlib.sha256(content).hexdigest()

    @property
    def startup_schema_digest(self) -> str:
        return hashlib.sha256(self._startup_schema_content).hexdigest()

    @property
    def startup_schema_content(self) -> bytes:
        return self._startup_schema_content

    def validated_payload(self, snapshot: dict[str, Any]) -> bytes:
        return validated_canonical_bytes(
            snapshot,
            schema_content=self._startup_schema_content,
        )

    def source_digest(self) -> str:
        entries: list[tuple[str, str, int]] = []
        task_dir = self.project_root / "docs" / "tasks"
        paths = [
            path
            for path in task_dir.glob("*.md")
            if path.is_file() and not _is_temporary(path)
        ]
        board = self.project_root / "docs" / "TASK_BOARD.md"
        if board.is_file():
            paths.append(board)
        if not paths:
            raise SnapshotSourceError("no dashboard source files are available")
        for path in sorted(paths, key=lambda item: item.relative_to(self.project_root).as_posix()):
            stat = path.lstat()
            resolved = (
                path.resolve()
                if getattr(stat, "st_file_attributes", 0) & 0x400
                else path.absolute()
            )
            if not resolved.is_relative_to(self.project_root):
                raise SnapshotSourceError("dashboard source path escapes project root")
            content = resolved.read_bytes()
            relative = resolved.relative_to(self.project_root).as_posix()
            entries.append((relative, hashlib.sha256(content).hexdigest(), len(content)))
        return canonical_sha256(entries)

    @staticmethod
    def changed_task_ids(
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> tuple[str, ...]:
        if previous is None:
            return tuple(sorted(item["task_id"] for item in current["tasks"]))
        previous_index = _task_semantics(previous)
        current_index = _task_semantics(current)
        return tuple(
            task_id
            for task_id in sorted(set(previous_index) | set(current_index))
            if previous_index.get(task_id) != current_index.get(task_id)
        )

    def _fresh_snapshot(
        self,
        core_result: CoreResult,
        git: GitCollection,
        extra_diagnostics: tuple[Diagnostic, ...],
    ) -> tuple[dict[str, Any], bytes]:
        diagnostics = _unique_diagnostics(core_result.diagnostics + extra_diagnostics)
        snapshot = {
            "schema_version": "ai-dev-flow/dashboard-snapshot/v1",
            "revision": "0" * 64,
            "generated_at": _utc_now(),
            "state": "fresh",
            "project": git.project,
            "tasks": [_wire_value(item) for item in core_result.tasks],
            "edges": [_wire_value(item) for item in core_result.edges],
            "actions": [_wire_value(item) for item in core_result.actions],
            "parallel_assessments": [
                _wire_value(item) for item in core_result.parallel_assessments
            ],
            "diagnostics": [_wire_value(item) for item in diagnostics],
            "stale_sources": [],
            "summary": _summary(core_result, diagnostics),
            "capabilities": _capabilities(),
            "disclaimer": DISCLAIMER,
        }
        return _finalize(
            snapshot,
            schema_content=self._startup_schema_content,
        )

    def _failure_snapshot(
        self,
        git: GitCollection,
        *,
        current_digest: str,
        diagnostic: Diagnostic,
    ) -> tuple[dict[str, Any], bytes]:
        if self._last_good_payload is None:
            diagnostics = _unique_diagnostics(tuple(git.diagnostics) + (diagnostic,))
            snapshot = {
                "schema_version": "ai-dev-flow/dashboard-snapshot/v1",
                "revision": "0" * 64,
                "generated_at": _utc_now(),
                "state": "partial",
                "project": git.project,
                "tasks": [],
                "edges": [],
                "actions": [],
                "parallel_assessments": [],
                "diagnostics": [_wire_value(item) for item in diagnostics],
                "stale_sources": [],
                "summary": _empty_summary(diagnostics),
                "capabilities": _capabilities(),
                "disclaimer": DISCLAIMER,
            }
            return _finalize(
                snapshot,
                schema_content=self._startup_schema_content,
            )

        snapshot = json.loads(self._last_good_payload)
        snapshot.pop("revision", None)
        snapshot.pop("generated_at", None)
        snapshot["revision"] = "0" * 64
        snapshot["generated_at"] = _utc_now()
        snapshot["state"] = "stale"
        snapshot["project"] = git.project
        snapshot["tasks"] = [
            {**item, "freshness": "stale"} for item in snapshot["tasks"]
        ]
        existing = tuple(
            _diagnostic_from_wire(item)
            for item in snapshot["diagnostics"]
        )
        diagnostics = _unique_diagnostics(existing + tuple(git.diagnostics) + (diagnostic,))
        snapshot["diagnostics"] = [_wire_value(item) for item in diagnostics]
        snapshot["stale_sources"] = [
            {
                "source_path": "docs/tasks",
                "current_digest": current_digest,
                "last_good_digest": self._last_good_source_digest,
                "diagnostic_ids": [diagnostic.diagnostic_id],
            }
        ]
        snapshot["summary"] = _summary_from_wire(snapshot, diagnostics)
        return _finalize(
            snapshot,
            schema_content=self._startup_schema_content,
        )

    def _strict_branch_hints(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for path in sorted((self.project_root / "docs" / "tasks").glob("*.md")):
            if _is_temporary(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="strict")
            except (OSError, UnicodeDecodeError):
                continue
            section: str | None = None
            task_ids: list[str] = []
            branch_hints: list[str] = []
            for line in text.splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
                    continue
                if section == "Workflow Contract":
                    match = _TASK_ID_LINE.fullmatch(line)
                    if match:
                        task_ids.append(match.group(1))
                elif section == "Scheduling":
                    match = _BRANCH_HINT_LINE.fullmatch(line)
                    if match:
                        branch_hints.append(match.group(1))
            if len(task_ids) == 1 and len(branch_hints) == 1:
                result[task_ids[0]] = branch_hints[0]
        return result

    @staticmethod
    def _map_hints(
        git: GitCollection,
        hints: dict[str, str],
    ) -> tuple[dict[str, Any], tuple[Diagnostic, ...]]:
        by_branch: dict[str, list[Any]] = {}
        for worktree in git.worktrees:
            if worktree.branch:
                by_branch.setdefault(worktree.branch, []).append(worktree)
        mapping: dict[str, Any] = {}
        diagnostics: list[Diagnostic] = []
        for task_id, hint in hints.items():
            matches = by_branch.get(f"refs/heads/{hint}", [])
            if len(matches) == 1:
                candidate = matches[0]
                if not (candidate.detached or candidate.locked or candidate.prunable):
                    mapping[task_id] = candidate
                    continue
            diagnostics.append(
                git_diagnostic(
                    "GIT_WORKTREE_MAPPING_UNKNOWN",
                    "Task branch maps to zero, multiple, or unsafe Worktrees",
                    task_ids=(task_id,),
                )
            )
        return mapping, tuple(diagnostics)

    @staticmethod
    def _verify_provisional_mapping(
        tasks: Iterable[TaskNode],
        mapping: dict[str, Any],
    ) -> None:
        by_id = {task.task_id: task for task in tasks}
        for task_id, worktree in mapping.items():
            task = by_id.get(task_id)
            if task is None or not task.branch_hint:
                raise SnapshotInputChanged("provisional Worktree mapping was not confirmed")
            if worktree.branch != f"refs/heads/{task.branch_hint}":
                raise SnapshotInputChanged("provisional Worktree branch was not confirmed")

    def _safe_source_digest(self, fallback: str, exc: Exception) -> str:
        try:
            return self.source_digest()
        except Exception:
            return canonical_sha256(
                {
                    "fallback": fallback,
                    "error_type": type(exc).__name__,
                }
            )

    @staticmethod
    def _build_failure_diagnostic(exc: Exception) -> Diagnostic:
        if isinstance(exc, SnapshotInputChanged):
            code = "SOURCE_CHANGED"
            message = "Dashboard input changed during candidate construction"
        elif isinstance(exc, SnapshotSourceError):
            code = "SOURCE_UNAVAILABLE"
            message = "Dashboard source input is unavailable"
        elif type(exc).__name__ in {"FrozenInputChangedError"}:
            code = "SOURCE_CHANGED"
            message = "TASK input changed during candidate construction"
        elif type(exc).__name__ in {
            "FrozenInputError",
            "ContractGatewayError",
            "GitParseError",
        }:
            code = "SOURCE_UNAVAILABLE"
            message = "Dashboard source input could not be validated"
        else:
            code = "SNAPSHOT_BUILD_FAILED"
            message = "Dashboard snapshot candidate could not be built"
        return Diagnostic(
            diagnostic_id=stable_text_id("snapshot-build", code, type(exc).__name__),
            code=code,
            severity="error",
            message=message,
            task_ids=(),
            provenance=(),
        )


class SnapshotInputChanged(RuntimeError):
    pass


class SnapshotSourceError(RuntimeError):
    pass


def _finalize(
    snapshot: dict[str, Any],
    *,
    schema_path: str | Path | None = None,
    schema_content: bytes | None = None,
) -> tuple[dict[str, Any], bytes]:
    snapshot["revision"] = snapshot_revision(snapshot)
    validate_contract(
        snapshot,
        schema_path=schema_path,
        schema_content=schema_content,
    )
    payload = canonical_bytes(snapshot)
    return snapshot, payload


def _with_resolved_ownership(
    git: GitCollection,
    mapping: dict[str, Any],
) -> GitCollection:
    by_root = {
        item.root.casefold(): item
        for item in mapping.values()
    }
    worktrees = tuple(
        replace(
            item,
            dirty_ownership=(
                "clean"
                if item.dirty_state == "clean"
                else by_root.get(item.root.casefold(), item).dirty_ownership
            ),
        )
        for item in git.worktrees
    )
    return replace(git, worktrees=worktrees)


def _summary(core_result: CoreResult, diagnostics: tuple[Diagnostic, ...]) -> dict[str, Any]:
    return {
        "task_total": len(core_result.tasks),
        "edge_total": len(core_result.edges),
        "action_total": len(core_result.actions),
        "counts_by_lifecycle": _complete_counts(
            (item.lifecycle for item in core_result.tasks if item.lifecycle),
            LIFECYCLES,
        ),
        "counts_by_action": _complete_counts(
            (item.action_kind for item in core_result.actions),
            ACTIONS,
        ),
        "counts_by_severity": _complete_counts(
            (item.severity for item in diagnostics),
            SEVERITIES,
        ),
        "counts_by_relation": _complete_counts(
            (item.type for item in core_result.edges),
            RELATIONS,
        ),
    }


def _summary_from_wire(
    snapshot: dict[str, Any],
    diagnostics: tuple[Diagnostic, ...],
) -> dict[str, Any]:
    return {
        "task_total": len(snapshot["tasks"]),
        "edge_total": len(snapshot["edges"]),
        "action_total": len(snapshot["actions"]),
        "counts_by_lifecycle": _complete_counts(
            (item["lifecycle"] for item in snapshot["tasks"] if item["lifecycle"]),
            LIFECYCLES,
        ),
        "counts_by_action": _complete_counts(
            (item["action_kind"] for item in snapshot["actions"]),
            ACTIONS,
        ),
        "counts_by_severity": _complete_counts(
            (item.severity for item in diagnostics),
            SEVERITIES,
        ),
        "counts_by_relation": _complete_counts(
            (item["type"] for item in snapshot["edges"]),
            RELATIONS,
        ),
    }


def _empty_summary(diagnostics: tuple[Diagnostic, ...]) -> dict[str, Any]:
    return {
        "task_total": 0,
        "edge_total": 0,
        "action_total": 0,
        "counts_by_lifecycle": _complete_counts((), LIFECYCLES),
        "counts_by_action": _complete_counts((), ACTIONS),
        "counts_by_severity": _complete_counts(
            (item.severity for item in diagnostics),
            SEVERITIES,
        ),
        "counts_by_relation": _complete_counts((), RELATIONS),
    }


def _complete_counts(values: Iterable[str], keys: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(values)
    return {key: counts[key] for key in keys}


def _capabilities() -> dict[str, Any]:
    return {
        "supported_scheduling_schema": ["ai-dev-flow/scheduling/v1"],
        "supported_actions": list(SUPPORTED_ACTIONS),
        "unsupported_actions": [],
        "unsupported_axes": list(UNSUPPORTED_AXES),
        "authority_sources": list(AUTHORITY_SOURCES),
    }


def _utc_now() -> str:
    value = datetime.now(timezone.utc)
    milliseconds = value.microsecond // 1000
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{milliseconds:03d}Z"


def _unique_diagnostics(items: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    by_id = {item.diagnostic_id: item for item in items}
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (item.severity, item.code, item.diagnostic_id),
        )
    )


def _diagnostic_from_wire(value: dict[str, Any]) -> Diagnostic:
    from ai_dev_flow_dashboard.core.models import Provenance

    return Diagnostic(
        diagnostic_id=value["diagnostic_id"],
        code=value["code"],
        severity=value["severity"],
        message=value["message"],
        task_ids=tuple(value["task_ids"]),
        provenance=tuple(Provenance(**item) for item in value["provenance"]),
    )


def _task_semantics(snapshot: dict[str, Any]) -> dict[str, bytes]:
    revision = snapshot.get("revision")
    if isinstance(revision, str) and revision in _TASK_SEMANTICS_CACHE:
        return _TASK_SEMANTICS_CACHE[revision]
    values = {
        item["task_id"]: {
            "task": item,
            "edges": [],
            "actions": [],
            "parallel_assessments": [],
        }
        for item in snapshot["tasks"]
    }
    for edge in snapshot["edges"]:
        related = {edge["source_task_id"], edge["target_task_id"]}
        for task_id in related:
            if task_id in values:
                values[task_id]["edges"].append(edge)
    for action in snapshot["actions"]:
        task_id = action["task_id"]
        if task_id in values:
            values[task_id]["actions"].append(action)
    for assessment in snapshot["parallel_assessments"]:
        related = {
            assessment["left_task_id"],
            assessment["right_task_id"],
        }
        for task_id in related:
            if task_id in values:
                values[task_id]["parallel_assessments"].append(assessment)
    index: dict[str, bytes] = {}
    for task_id, payload in values.items():
        index[task_id] = canonical_bytes(payload)
    if isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{64}", revision):
        if (
            len(_TASK_SEMANTICS_CACHE) >= 16
            and revision not in _TASK_SEMANTICS_CACHE
        ):
            _TASK_SEMANTICS_CACHE.pop(next(iter(_TASK_SEMANTICS_CACHE)))
        _TASK_SEMANTICS_CACHE[revision] = index
    return index


def _wire_value(value: Any) -> Any:
    """Convert a frozen domain value to its compact wire representation."""

    if isinstance(value, TaskNode):
        provenance = value.provenance
        task_id_provenance = [
            item for item in provenance if item.field == "task_id"
        ]
        value = replace(
            value,
            provenance=tuple(
                replace(
                    item,
                    source_type={
                        "filename": "derived",
                        "heading": "canonical",
                        "legacy": "legacy_inferred",
                    }.get(item.source_type, item.source_type),
                )
                for item in (
                    task_id_provenance[:1]
                    if task_id_provenance
                    else provenance[:1]
                )
            ),
        )
    return primitive(value)


def _is_temporary(path: Path) -> bool:
    name = path.name.casefold()
    return (
        name.startswith((".", "~", "#"))
        or name.endswith((".tmp", ".temp", ".swp", ".bak", "~"))
        or ".tmp." in name
    )
