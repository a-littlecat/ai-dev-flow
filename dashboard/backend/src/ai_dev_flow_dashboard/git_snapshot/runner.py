"""Allowlisted, shell-free Git command execution."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


GIT_TIMEOUT_SECONDS = 5.0
STDERR_LIMIT = 512


@dataclass(frozen=True)
class GitCommandResult:
    args: tuple[str, ...]
    stdout: bytes
    stderr_summary: str


class GitCommandError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


Executor = Callable[..., subprocess.CompletedProcess[bytes]]


class SafeGitRunner:
    """Run only the command families frozen by DASHBOARD-001."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GIT_TIMEOUT_SECONDS,
        executor: Executor = subprocess.run,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self._executor = executor

    def git_version(self) -> GitCommandResult:
        return self._run(("git", "--version"))

    def rev_parse(self, root: str | Path) -> GitCommandResult:
        normalized = str(Path(root).resolve())
        return self._run(
            (
                "git",
                "-C",
                normalized,
                "rev-parse",
                "--show-toplevel",
                "--git-dir",
                "--git-common-dir",
                "--verify",
                "HEAD",
            )
        )

    def worktree_list(self, root: str | Path) -> GitCommandResult:
        normalized = str(Path(root).resolve())
        return self._run(
            ("git", "-C", normalized, "worktree", "list", "--porcelain", "-z")
        )

    def status(self, worktree: str | Path) -> GitCommandResult:
        normalized = str(Path(worktree).resolve())
        return self._run(
            (
                "git",
                "-C",
                normalized,
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignore-submodules=none",
            )
        )

    def _run(self, args: Sequence[str]) -> GitCommandResult:
        frozen_args = tuple(args)
        self._validate(frozen_args)
        try:
            completed = self._executor(
                list(frozen_args),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                check=False,
                timeout=self.timeout_seconds,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            )
        except subprocess.TimeoutExpired as exc:
            raise GitCommandError("GIT_COMMAND_TIMEOUT", "Git read command timed out") from exc
        except (OSError, ValueError) as exc:
            raise GitCommandError("GIT_COMMAND_UNAVAILABLE", "Git read command is unavailable") from exc
        stderr = bytes(completed.stderr or b"")[:STDERR_LIMIT]
        stderr_summary = stderr.decode("utf-8", errors="replace").replace("\x00", "")[:STDERR_LIMIT]
        if completed.returncode != 0:
            raise GitCommandError(
                "GIT_COMMAND_FAILED",
                f"Git read command failed with exit code {completed.returncode}",
            )
        return GitCommandResult(frozen_args, bytes(completed.stdout or b""), stderr_summary)

    @staticmethod
    def _validate(args: tuple[str, ...]) -> None:
        if args == ("git", "--version"):
            return
        if len(args) < 5 or args[:2] != ("git", "-C"):
            raise GitCommandError("GIT_COMMAND_REJECTED", "Git command is outside the allowlist")
        root = Path(args[2])
        if not root.is_absolute():
            raise GitCommandError("GIT_COMMAND_REJECTED", "Git root must be absolute")
        suffix = args[3:]
        allowed = {
            (
                "rev-parse",
                "--show-toplevel",
                "--git-dir",
                "--git-common-dir",
                "--verify",
                "HEAD",
            ),
            ("worktree", "list", "--porcelain", "-z"),
            (
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignore-submodules=none",
            ),
        }
        if suffix not in allowed:
            raise GitCommandError("GIT_COMMAND_REJECTED", "Git command is outside the allowlist")
