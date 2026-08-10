"""Discover and select TASK sources from safe linked Worktrees.

The dashboard snapshot is Worktree-first: safe linked Worktrees (never
detached / locked / prunable) contribute their ``docs/tasks/*.md`` files as
read-only supplementary sources. The main workspace stays the winner for any
``task_id`` it contains; ties between Worktrees are broken deterministically
by the casefolded lexicographic order of the canonical Worktree root path,
never by the order ``git worktree list`` returns. Worktree ``TASK_BOARD.md``
files are never used as a source: TASK files are the only source of truth, so
board-related diagnostics produced by the public Workflow Contract facade are
filtered out of Worktree reports.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping

from .canonical import canonical_sha256, stable_text_id
from .contract_gateway import ContractGateway
from .frozen_input import _LeaseGuard
from .models import (
    CoreContract,
    Diagnostic,
    FrozenProjectInput,
    FrozenTaskInput,
    Provenance,
    WorktreeExtra,
    WorktreeSnapshot,
    WorktreeTaskItem,
)

WT_SOURCE_UNREADABLE = "WT_SOURCE_UNREADABLE"
WT_TASK_CONFLICT = "WT_TASK_CONFLICT"
WT_SOURCE_LOST = "WT_SOURCE_LOST"

_TASK_ID_LINE = re.compile(r"^- `task_id`: `([^`\r\n]+)`$")
_WORKTREE_SOURCE_TYPE = "worktree"


@dataclass(frozen=True)
class WorktreeSourceFile:
    """One readable TASK candidate file inside a safe linked Worktree."""

    path: Path
    worktree_root: str
    source_path: str
    sha256: str
    size: int
    content: bytes
    text: str
    task_id: str


@dataclass(frozen=True)
class StaleTaskRecord:
    """Last-known-good parsed contribution of one Worktree TASK file."""

    worktree_root: str
    source_path: str
    sha256: str
    size: int
    contract: CoreContract
    source: FrozenTaskInput
    diagnostics: tuple[Diagnostic, ...]

    @property
    def digest(self) -> str:
        return canonical_sha256(
            (self.worktree_root, self.source_path, self.sha256, self.size)
        )


@dataclass(frozen=True)
class _Scan:
    digest: str
    fresh_files: tuple[WorktreeSourceFile, ...]
    diagnostics: tuple[Diagnostic, ...]
    # Last-known-good records whose Worktree or file is currently lost.
    lost_records: tuple[StaleTaskRecord, ...]
    stale_sources: tuple[dict, ...]
    lost_diagnostics: tuple[Diagnostic, ...]
    # Casefolded roots that were safely enumerated during this scan.
    healthy_root_keys: frozenset[str]


@dataclass(frozen=True)
class WorktreeAggregation:
    extra: WorktreeExtra
    digest: str
    diagnostics: tuple[Diagnostic, ...]
    stale_sources: tuple[dict, ...]
    # Freshly selected records, folded into last-known-good after a
    # successful build.
    contributed: tuple[StaleTaskRecord, ...]
    healthy_root_keys: frozenset[str]


class WorktreeTaskAggregator:
    """Collect, select and parse TASK files from safe linked Worktrees."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        skill_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.skill_root = (
            Path(skill_root).resolve()
            if skill_root is not None
            else (self.project_root / "skills" / "ai-dev-flow").resolve()
        )

    @staticmethod
    def safe_worktrees(
        git_worktrees: Iterable[WorktreeSnapshot],
        project_root: Path,
    ) -> tuple[WorktreeSnapshot, ...]:
        """Safe linked Worktrees, ordered by casefolded root for determinism."""

        root_key = str(project_root).casefold()
        safe = [
            item
            for item in git_worktrees
            if not (item.detached or item.locked or item.prunable)
            and str(Path(item.root).resolve()).casefold() != root_key
        ]
        return tuple(sorted(safe, key=lambda item: item.root.casefold()))

    @staticmethod
    def task_id_from_text(text: str) -> str | None:
        """Extract the Workflow Contract task_id like the strict branch-hint scan."""

        section: str | None = None
        task_ids: list[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            if section == "Workflow Contract":
                match = _TASK_ID_LINE.fullmatch(line)
                if match:
                    task_ids.append(match.group(1))
        return task_ids[0] if len(task_ids) == 1 else None

    def collect(
        self,
        git_worktrees: Iterable[WorktreeSnapshot],
        *,
        main_task_ids: frozenset[str],
        last_good: Mapping[str, tuple[StaleTaskRecord, ...]],
    ) -> WorktreeAggregation:
        """Read safe Worktree TASK files and select publishable candidates."""

        worktrees = tuple(git_worktrees)
        scan = self._scan_all(worktrees, last_good)
        diagnostics: list[Diagnostic] = list(scan.diagnostics)
        diagnostics.extend(scan.lost_diagnostics)

        fresh_by_id: dict[str, list[WorktreeSourceFile]] = {}
        for item in scan.fresh_files:
            fresh_by_id.setdefault(item.task_id, []).append(item)

        chosen_fresh: list[WorktreeSourceFile] = []
        co_sources: dict[str, tuple[WorktreeSourceFile, ...]] = {}
        conflicted: set[str] = set()
        for task_id in sorted(fresh_by_id):
            # Rule (a): the main workspace always wins, silently.
            if task_id in main_task_ids:
                continue
            candidates = sorted(
                fresh_by_id[task_id],
                key=lambda item: item.worktree_root.casefold(),
            )
            # Rule (b): exactly one safe Worktree contains the task_id.
            if len(candidates) == 1:
                chosen_fresh.append(candidates[0])
                continue
            distinct = {item.sha256 for item in candidates}
            # Rule (c): identical content is one logical task; the first
            # Worktree by casefolded root order is the marked source.
            if len(distinct) == 1:
                chosen_fresh.append(candidates[0])
                co_sources[task_id] = tuple(candidates)
                continue
            # Rule (d): diverging content publishes no candidate at all.
            conflicted.add(task_id)
            diagnostics.append(
                _conflict_diagnostic(task_id, candidates, source_kind="worktree")
            )

        chosen_ids = {item.task_id for item in chosen_fresh} | set(main_task_ids)
        lost_by_id: dict[str, list[StaleTaskRecord]] = {}
        for record in scan.lost_records:
            lost_by_id.setdefault(record.contract.task_id, []).append(record)
        chosen_stale: list[StaleTaskRecord] = []
        for task_id in sorted(lost_by_id):
            if task_id in chosen_ids or task_id in conflicted:
                continue
            records = sorted(
                lost_by_id[task_id],
                key=lambda item: item.worktree_root.casefold(),
            )
            distinct = {item.sha256 for item in records}
            if len(distinct) == 1:
                chosen_stale.append(records[0])
            else:
                diagnostics.append(
                    _conflict_diagnostic(task_id, records, source_kind="stale")
                )

        items: list[WorktreeTaskItem] = []
        contributed: list[StaleTaskRecord] = []
        # Per-task diagnostics travel inside the extra so the core links them
        # into TaskNode.diagnostic_ids; scan/selection diagnostics are merged
        # by the builder at snapshot level.
        extra_diagnostics: list[Diagnostic] = []
        for item in sorted(
            chosen_fresh,
            key=lambda entry: (entry.worktree_root.casefold(), entry.source_path),
        ):
            parsed = self._parse_file(item, co_sources.get(item.task_id, ()))
            if parsed is None:
                diagnostics.append(
                    _unreadable_diagnostic(
                        item.worktree_root,
                        item.source_path,
                        "Worktree TASK could not be parsed by the public contract facade",
                    )
                )
                continue
            items.append(parsed[0])
            contributed.append(parsed[1])
            extra_diagnostics.extend(parsed[2])
        for record in chosen_stale:
            items.append(
                WorktreeTaskItem(
                    contract=replace(record.contract, stale=True),
                    source=record.source,
                    stale=True,
                )
            )
            extra_diagnostics.extend(record.diagnostics)

        extra = WorktreeExtra(
            items=tuple(items),
            diagnostics=tuple(extra_diagnostics),
        )
        return WorktreeAggregation(
            extra=extra,
            digest=scan.digest,
            diagnostics=tuple(diagnostics),
            stale_sources=scan.stale_sources,
            contributed=tuple(contributed),
            healthy_root_keys=scan.healthy_root_keys,
        )

    def verify_unchanged(
        self,
        git_worktrees: Iterable[WorktreeSnapshot],
        aggregation: WorktreeAggregation,
        last_good: Mapping[str, tuple[StaleTaskRecord, ...]],
    ) -> bool:
        """Prove the observable Worktree source state still matches the build."""

        rescan = self._scan_all(tuple(git_worktrees), last_good)
        return rescan.digest == aggregation.digest

    def updated_last_good(
        self,
        last_good: Mapping[str, tuple[StaleTaskRecord, ...]],
        aggregation: WorktreeAggregation,
    ) -> dict[str, tuple[StaleTaskRecord, ...]]:
        """Fold a successful build into the retained last-known-good records."""

        updated = dict(last_good)
        contributed_by_root: dict[str, list[StaleTaskRecord]] = {}
        for record in aggregation.contributed:
            contributed_by_root.setdefault(
                record.worktree_root.casefold(), []
            ).append(record)
        for key in aggregation.healthy_root_keys:
            records = tuple(contributed_by_root.get(key, ()))
            if records:
                updated[key] = records
            else:
                updated.pop(key, None)
        for key, records in contributed_by_root.items():
            if key not in aggregation.healthy_root_keys:
                updated[key] = tuple(records)
        # Bound retained last-known-good sources (FIFO, mirrors the builder's
        # candidate cache discipline).
        while len(updated) > 8:
            updated.pop(next(iter(updated)))
        return updated

    def _scan_all(
        self,
        git_worktrees: tuple[WorktreeSnapshot, ...],
        last_good: Mapping[str, tuple[StaleTaskRecord, ...]],
    ) -> _Scan:
        diagnostics: list[Diagnostic] = []
        digest_entries: list[tuple] = []
        fresh_files: list[WorktreeSourceFile] = []
        healthy_root_keys: set[str] = set()
        readable: set[tuple[str, str]] = set()
        for worktree in self.safe_worktrees(git_worktrees, self.project_root):
            root = _canonical_root(worktree.root)
            root_key = root.casefold()
            files, scan_diagnostics, entries, ok = self._scan_worktree(root)
            diagnostics.extend(scan_diagnostics)
            digest_entries.extend(entries)
            if ok:
                healthy_root_keys.add(root_key)
                fresh_files.extend(files)
                readable.update((root_key, item.source_path) for item in files)

        lost_records: list[StaleTaskRecord] = []
        lost_diagnostics: list[Diagnostic] = []
        stale_sources: list[dict] = []
        for key in sorted(last_good):
            records = tuple(last_good[key])
            if not records:
                continue
            if key not in healthy_root_keys:
                lost = list(records)
                digest_entries.append(("lost", records[0].worktree_root))
            else:
                lost = [
                    record
                    for record in records
                    if (key, record.source_path) not in readable
                ]
                digest_entries.extend(
                    ("lost-file", record.worktree_root, record.source_path)
                    for record in lost
                )
            if not lost:
                continue
            lost_records.extend(lost)
            diagnostic = _source_lost_diagnostic(lost)
            lost_diagnostics.append(diagnostic)
            stale_sources.extend(
                {
                    "source_path": f"{record.worktree_root}/{record.source_path}",
                    "current_digest": canonical_sha256(
                        ("lost", record.worktree_root, record.source_path)
                    ),
                    "last_good_digest": record.digest,
                    "diagnostic_ids": [diagnostic.diagnostic_id],
                }
                for record in lost
            )

        digest = canonical_sha256(
            tuple(
                sorted(digest_entries, key=lambda entry: tuple(str(part) for part in entry))
            )
        )
        return _Scan(
            digest=digest,
            fresh_files=tuple(fresh_files),
            diagnostics=tuple(diagnostics),
            lost_records=tuple(lost_records),
            stale_sources=tuple(stale_sources),
            lost_diagnostics=tuple(lost_diagnostics),
            healthy_root_keys=frozenset(healthy_root_keys),
        )

    def _scan_worktree(
        self,
        root: str,
    ) -> tuple[list[WorktreeSourceFile], list[Diagnostic], list[tuple], bool]:
        root_path = Path(root)
        task_dir = root_path / "docs" / "tasks"
        files: list[WorktreeSourceFile] = []
        diagnostics: list[Diagnostic] = []
        entries: list[tuple] = []
        try:
            if not task_dir.is_dir():
                return files, diagnostics, entries, True
            paths = sorted(task_dir.glob("*.md"), key=lambda item: item.as_posix())
        except OSError:
            return (
                files,
                [_unreadable_diagnostic(root, "docs/tasks", "TASK directory cannot be listed")],
                [("unreadable", root, "docs/tasks")],
                False,
            )
        for path in paths:
            if _is_temporary(path):
                continue
            relative_name = f"docs/tasks/{path.name}"
            try:
                stat = path.lstat()
                resolved = (
                    path.resolve()
                    if getattr(stat, "st_file_attributes", 0) & 0x400
                    else path.absolute()
                )
                if not resolved.is_relative_to(root_path):
                    raise WorktreeSourceEscape(f"TASK path escapes the Worktree root: {path}")
                content = resolved.read_bytes()
                text = content.decode("utf-8", errors="strict")
            except (OSError, UnicodeError, WorktreeSourceEscape) as exc:
                diagnostics.append(
                    _unreadable_diagnostic(root, relative_name, str(exc))
                )
                entries.append(("unreadable-file", root, relative_name))
                continue
            task_id = self.task_id_from_text(text)
            if task_id is None:
                continue
            source_path = unicodedata.normalize(
                "NFC", resolved.relative_to(root_path).as_posix()
            )
            sha256 = hashlib.sha256(content).hexdigest()
            files.append(
                WorktreeSourceFile(
                    path=resolved,
                    worktree_root=root,
                    source_path=source_path,
                    sha256=sha256,
                    size=len(content),
                    content=content,
                    text=text,
                    task_id=task_id,
                )
            )
            entries.append(("file", root, source_path, sha256, len(content)))
        return files, diagnostics, entries, True

    def _parse_file(
        self,
        item: WorktreeSourceFile,
        co_sources: tuple[WorktreeSourceFile, ...],
    ) -> tuple[WorktreeTaskItem, StaleTaskRecord, tuple[Diagnostic, ...]] | None:
        """Parse one selected file through the public Workflow Contract facade.

        The facade is invoked with the single TASK file as target, so the
        Worktree's TASK_BOARD.md is never evaluated: TASK files are the only
        source of truth.
        """

        source = FrozenTaskInput(
            path=item.path,
            source_path=item.source_path,
            content=item.content,
            text=item.text,
            mtime_ns=0,
            size=item.size,
            sha256=item.sha256,
        )
        frozen = FrozenProjectInput(
            item.path,
            (source,),
            canonical_sha256(((item.source_path, item.sha256, item.size),)),
            _LeaseGuard(),
            None,
        )
        gateway = ContractGateway(item.path, self.skill_root)
        try:
            report = gateway.inspect(frozen)
        except Exception:
            return None
        if len(report.contracts) != 1:
            return None
        contract = report.contracts[0]
        if contract.task_id != item.task_id or contract.source_path != item.source_path:
            return None
        task_diagnostics = tuple(
            _mark_worktree_diagnostic(diagnostic)
            for diagnostic in report.diagnostics
            if not _is_board_diagnostic(diagnostic)
        )
        provenance = tuple(
            replace(entry, source_type=_WORKTREE_SOURCE_TYPE)
            for entry in contract.provenance
        )
        provenance += tuple(
            _provenance_entry(
                source_path=source_file.source_path,
                field="worktree_source",
                raw_value=source_file.worktree_root,
            )
            for source_file in co_sources
        )
        marked = replace(
            contract,
            provenance=provenance,
            worktree_root=item.worktree_root,
        )
        task_item = WorktreeTaskItem(contract=marked, source=source)
        record = StaleTaskRecord(
            worktree_root=item.worktree_root,
            source_path=item.source_path,
            sha256=item.sha256,
            size=item.size,
            contract=marked,
            source=source,
            diagnostics=task_diagnostics,
        )
        return task_item, record, task_diagnostics


class WorktreeSourceEscape(RuntimeError):
    """A Worktree TASK path resolves outside its Worktree root."""


def _canonical_root(root: str) -> str:
    return Path(root).resolve().as_posix()


def _is_temporary(path: Path) -> bool:
    # Keep in sync with snapshot.builder._is_temporary; core must not import
    # the snapshot package (snapshot already depends on core).
    name = path.name.casefold()
    return (
        name.startswith((".", "~", "#"))
        or name.endswith((".tmp", ".temp", ".swp", ".bak", "~"))
        or ".tmp." in name
    )


def _provenance_entry(
    *,
    source_path: str,
    field: str,
    raw_value: str | None,
) -> Provenance:
    return Provenance(
        source_path=source_path,
        heading=None,
        field=field,
        line=0,
        raw_value=raw_value,
        source_type=_WORKTREE_SOURCE_TYPE,
    )


def _unreadable_diagnostic(root: str, source_path: str, detail: str) -> Diagnostic:
    return Diagnostic(
        diagnostic_id=stable_text_id(
            "worktree", WT_SOURCE_UNREADABLE, root, source_path
        ),
        code=WT_SOURCE_UNREADABLE,
        severity="warning",
        message=f"Worktree TASK source is unreadable or escapes its root: {detail}",
        task_ids=(),
        provenance=(
            _provenance_entry(
                source_path=source_path,
                field="worktree_root",
                raw_value=root,
            ),
        ),
    )


def _conflict_diagnostic(
    task_id: str,
    candidates,
    *,
    source_kind: str,
) -> Diagnostic:
    provenance: list[Provenance] = []
    for candidate in candidates:
        provenance.append(
            _provenance_entry(
                source_path=candidate.source_path,
                field="worktree_root",
                raw_value=candidate.worktree_root,
            )
        )
        provenance.append(
            _provenance_entry(
                source_path=candidate.source_path,
                field="sha256",
                raw_value=candidate.sha256,
            )
        )
    return Diagnostic(
        diagnostic_id=stable_text_id(
            "worktree",
            WT_TASK_CONFLICT,
            task_id,
            *(entry.raw_value or "" for entry in provenance),
        ),
        code=WT_TASK_CONFLICT,
        severity="warning",
        message=(
            f"Multiple {source_kind} Worktree sources contain task {task_id} "
            "with different content; no candidate is published"
        ),
        task_ids=(task_id,),
        provenance=tuple(provenance),
    )


def _source_lost_diagnostic(records: list[StaleTaskRecord]) -> Diagnostic:
    root = records[0].worktree_root
    task_ids = tuple(sorted({record.contract.task_id for record in records}))
    return Diagnostic(
        diagnostic_id=stable_text_id("worktree", WT_SOURCE_LOST, root, *task_ids),
        code=WT_SOURCE_LOST,
        severity="warning",
        message=(
            "Worktree TASK source was lost (locked, prunable, deleted, or "
            "unreadable); last-known-good content is marked stale"
        ),
        task_ids=task_ids,
        provenance=tuple(
            _provenance_entry(
                source_path=record.source_path,
                field="worktree_root",
                raw_value=record.worktree_root,
            )
            for record in records
        ),
    )


def _mark_worktree_diagnostic(diagnostic: Diagnostic) -> Diagnostic:
    return replace(
        diagnostic,
        provenance=tuple(
            replace(entry, source_type=_WORKTREE_SOURCE_TYPE)
            for entry in diagnostic.provenance
        ),
    )


def _is_board_diagnostic(diagnostic: Diagnostic) -> bool:
    if "BOARD" in diagnostic.code:
        return True
    return any(
        entry.source_path == "docs/TASK_BOARD.md" for entry in diagnostic.provenance
    )
