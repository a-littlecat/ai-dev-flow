"""Read-only Git/Worktree collection and task branch mapping."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ai_dev_flow_dashboard.core import resolve_dirty_ownership_for_tasks
from ai_dev_flow_dashboard.core.canonical import canonical_sha256
from ai_dev_flow_dashboard.core.models import Diagnostic, TaskNode, WorktreeSnapshot

from .diagnostics import git_diagnostic
from .parser import GitParseError, parse_rev_parse, parse_status_z, parse_worktree_list_z
from .runner import GitCommandError, SafeGitRunner


@dataclass(frozen=True)
class GitCollection:
    requested_root: Path
    root: Path
    git_dir: Path | None
    common_dir: Path | None
    head: str | None
    branch: str | None
    version: str | None
    state: str
    worktrees: tuple[WorktreeSnapshot, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def fingerprint(self) -> str:
        return canonical_sha256(
            {
                "root": self.root.as_posix(),
                "git_dir": self.git_dir.as_posix() if self.git_dir else None,
                "common_dir": self.common_dir.as_posix() if self.common_dir else None,
                "head": self.head,
                "branch": self.branch,
                "state": self.state,
                "worktrees": [
                    {
                        "root": item.root,
                        "head": item.head,
                        "branch": item.branch,
                        "detached": item.detached,
                        "locked": item.locked,
                        "prunable": item.prunable,
                        "dirty_state": item.dirty_state,
                        "dirty_paths": item.dirty_paths,
                        "diagnostic_ids": item.diagnostic_ids,
                        # Internal candidate invalidation must include derived
                        # ownership even though the public v1 wire shape does not.
                        "dirty_ownership": item.dirty_ownership,
                    }
                    for item in self.worktrees
                ],
                "diagnostics": self.diagnostics,
            }
        )

    @property
    def watch_fingerprint(self) -> str:
        """Hash only Git-observable evidence; derived ownership is intentionally excluded."""

        return canonical_sha256(
            {
                "root": self.root.as_posix(),
                "git_dir": self.git_dir.as_posix() if self.git_dir else None,
                "common_dir": self.common_dir.as_posix() if self.common_dir else None,
                "head": self.head,
                "branch": self.branch,
                "state": self.state,
                "worktrees": [
                    {
                        "root": item.root,
                        "head": item.head,
                        "branch": item.branch,
                        "detached": item.detached,
                        "locked": item.locked,
                        "prunable": item.prunable,
                        "dirty_state": item.dirty_state,
                        "dirty_paths": item.dirty_paths,
                        "diagnostic_ids": item.diagnostic_ids,
                    }
                    for item in self.worktrees
                ],
                "diagnostics": self.diagnostics,
            }
        )

    @property
    def project(self) -> dict:
        current = next(
            (
                item
                for item in self.worktrees
                if Path(item.root).resolve() == self.requested_root.resolve()
            ),
            None,
        )
        dirty = None
        if current is not None:
            dirty = (
                False
                if current.dirty_state == "clean"
                else True
                if current.dirty_state == "dirty"
                else None
            )
        return {
            "root": self.root.as_posix(),
            "branch": self.branch,
            "head": self.head,
            "dirty": dirty,
            "git_state": self.state,
            "worktrees": [
                {
                    "root": item.root,
                    "head": item.head,
                    "branch": item.branch,
                    "detached": item.detached,
                    "locked": item.locked,
                    "prunable": item.prunable,
                    "dirty_state": item.dirty_state,
                    "dirty_paths": list(item.dirty_paths),
                    "diagnostic_ids": list(item.diagnostic_ids),
                }
                for item in self.worktrees
            ],
        }

    @property
    def watch_paths(self) -> tuple[Path, ...]:
        dot_git = self.requested_root / ".git"
        paths = [dot_git] if dot_git.is_file() else []
        if self.git_dir:
            paths.extend((self.git_dir / "HEAD", self.git_dir / "index"))
        if self.common_dir:
            paths.extend(
                (
                    self.common_dir / "HEAD",
                    self.common_dir / "packed-refs",
                    self.common_dir / "refs" / "heads",
                    self.common_dir / "worktrees",
                )
            )
        return tuple(dict.fromkeys(path.resolve() for path in paths))

    def map_tasks(self, tasks: Iterable[TaskNode]) -> tuple[dict[str, WorktreeSnapshot], tuple[Diagnostic, ...]]:
        task_values = tuple(tasks)
        by_branch: dict[str, list[WorktreeSnapshot]] = {}
        for worktree in self.worktrees:
            if worktree.branch:
                by_branch.setdefault(worktree.branch, []).append(worktree)
        mapping: dict[str, WorktreeSnapshot] = {}
        diagnostics: list[Diagnostic] = []
        for task in task_values:
            if not task.branch_hint:
                continue
            expected = f"refs/heads/{task.branch_hint}"
            matches = by_branch.get(expected, [])
            if len(matches) == 1:
                candidate = matches[0]
                if candidate.detached or candidate.locked or candidate.prunable:
                    diagnostics.append(
                        git_diagnostic(
                            "GIT_WORKTREE_UNSAFE",
                            "Task Worktree is detached, locked, or prunable",
                            task_ids=(task.task_id,),
                        )
                    )
                    continue
                mapping[task.task_id] = candidate
            else:
                diagnostics.append(
                    git_diagnostic(
                        "GIT_WORKTREE_MAPPING_UNKNOWN",
                        "Task branch maps to zero or multiple Worktrees",
                        task_ids=(task.task_id,),
                    )
                )
        return resolve_dirty_ownership_for_tasks(task_values, mapping), tuple(diagnostics)


class GitSnapshotCollector:
    def __init__(self, project_root: str | Path, *, runner: SafeGitRunner | None = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.runner = runner or SafeGitRunner()
        self._version: str | None = None

    def collect(self) -> GitCollection:
        diagnostics: list[Diagnostic] = []
        try:
            with ThreadPoolExecutor(
                max_workers=3,
                thread_name_prefix="dashboard-git-metadata",
            ) as executor:
                version_future = executor.submit(self._git_version)
                rev_parse_future = executor.submit(
                    self.runner.rev_parse,
                    self.project_root,
                )
                worktree_list_future = executor.submit(
                    self.runner.worktree_list,
                    self.project_root,
                )
            version = version_future.result()
            root, git_dir, common_dir, head = parse_rev_parse(
                rev_parse_future.result().stdout
            )
            parsed_worktrees = parse_worktree_list_z(
                worktree_list_future.result().stdout
            )
        except UnicodeDecodeError:
            diagnostics.append(
                git_diagnostic("GIT_DECODE_ERROR", "Git output is not valid UTF-8", severity="error")
            )
            return self._unavailable(diagnostics)
        except GitCommandError as exc:
            code = (
                "GIT_CAPABILITY_UNSUPPORTED"
                if exc.code == "GIT_COMMAND_FAILED"
                else exc.code
            )
            diagnostics.append(git_diagnostic(code, str(exc), severity="error"))
            return self._unavailable(diagnostics)
        except GitParseError as exc:
            diagnostics.append(
                git_diagnostic("GIT_PARSE_ERROR", str(exc), severity="error")
            )
            return self._unavailable(diagnostics)

        worktrees: list[WorktreeSnapshot] = []
        state = "ok"
        with ThreadPoolExecutor(
            max_workers=max(1, min(8, len(parsed_worktrees))),
            thread_name_prefix="dashboard-git-read",
        ) as executor:
            status_futures = [
                executor.submit(self._collect_status, parsed.root)
                for parsed in parsed_worktrees
            ]
        for parsed, future in zip(parsed_worktrees, status_futures):
            item_diagnostics: list[Diagnostic] = []
            dirty_state = "unknown"
            dirty_paths: tuple[str, ...] = ()
            try:
                dirty_paths = future.result()
                dirty_state = "dirty" if dirty_paths else "clean"
            except GitCommandError as exc:
                item_diagnostics.append(
                    git_diagnostic(
                        exc.code,
                        "Worktree status could not be collected",
                    )
                )
            except GitParseError as exc:
                item_diagnostics.append(
                    git_diagnostic(
                        "GIT_STATUS_PARSE_ERROR",
                        str(exc),
                    )
                )
            if item_diagnostics:
                state = "degraded"
                diagnostics.extend(item_diagnostics)
            worktrees.append(
                WorktreeSnapshot(
                    root=parsed.root.as_posix(),
                    head=parsed.head,
                    branch=parsed.branch,
                    detached=parsed.detached,
                    locked=parsed.locked,
                    prunable=parsed.prunable,
                    dirty_state=dirty_state,
                    dirty_paths=dirty_paths,
                    diagnostic_ids=tuple(item.diagnostic_id for item in item_diagnostics),
                    dirty_ownership=(
                        "clean"
                        if dirty_state == "clean"
                        else "unknown"
                    ),
                )
            )
        current = next(
            (item for item in worktrees if Path(item.root).resolve() == self.project_root),
            None,
        )
        branch = (
            current.branch.removeprefix("refs/heads/")
            if current and current.branch
            else None
        )
        return GitCollection(
            requested_root=self.project_root,
            root=root,
            git_dir=git_dir,
            common_dir=common_dir,
            head=head,
            branch=branch,
            version=version,
            state=state,
            worktrees=tuple(sorted(worktrees, key=lambda item: item.root.casefold())),
            diagnostics=tuple(
                sorted(diagnostics, key=lambda item: (item.severity, item.code, item.diagnostic_id))
            ),
        )

    def _git_version(self) -> str:
        if self._version is not None:
            return self._version
        version_output = self.runner.git_version().stdout.decode(
            "utf-8",
            errors="strict",
        ).strip()
        if not version_output.startswith("git version "):
            raise GitParseError("Git version output is not recognized")
        self._version = version_output.removeprefix("git version ")
        return self._version

    def _unavailable(self, diagnostics: list[Diagnostic]) -> GitCollection:
        return GitCollection(
            requested_root=self.project_root,
            root=self.project_root,
            git_dir=None,
            common_dir=None,
            head=None,
            branch=None,
            version=None,
            state="unavailable",
            worktrees=(),
            diagnostics=tuple(diagnostics),
        )

    def _collect_status(self, root: Path) -> tuple[str, ...]:
        return parse_status_z(self.runner.status(root).stdout)
