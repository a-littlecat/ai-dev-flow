"""Read-only Git and linked Worktree snapshot collection."""

from .collector import GitCollection, GitSnapshotCollector
from .parser import GitParseError, parse_status_z, parse_worktree_list_z
from .runner import GitCommandError, GitCommandResult, SafeGitRunner

__all__ = [
    "GitCollection",
    "GitCommandError",
    "GitCommandResult",
    "GitParseError",
    "GitSnapshotCollector",
    "SafeGitRunner",
    "parse_status_z",
    "parse_worktree_list_z",
]
