"""Strict UTF-8 and NUL-delimited Git porcelain parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


_HEX_RE = re.compile(r"[0-9a-fA-F]{40,64}")
_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


class GitParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedWorktree:
    root: Path
    head: str | None
    branch: str | None
    detached: bool
    locked: bool
    prunable: bool


def decode_utf8(data: bytes, *, label: str) -> str:
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise GitParseError(f"{label} is not valid UTF-8") from exc


def parse_rev_parse(data: bytes) -> tuple[Path, Path, Path, str]:
    text = decode_utf8(data, label="rev-parse output")
    lines = text.splitlines()
    if len(lines) != 4:
        raise GitParseError("rev-parse output must contain exactly four lines")
    root = _absolute_path(lines[0], "repository root")
    git_dir = _absolute_or_relative_path(lines[1], root, "Git directory")
    common_dir = _absolute_or_relative_path(lines[2], root, "Git common directory")
    head = lines[3]
    if _HEX_RE.fullmatch(head) is None:
        raise GitParseError("HEAD is not a hexadecimal object id")
    return root, git_dir, common_dir, head.lower()


def parse_worktree_list_z(data: bytes) -> tuple[ParsedWorktree, ...]:
    text = decode_utf8(data, label="worktree list output")
    if not text.endswith("\x00"):
        raise GitParseError("worktree list output is not NUL terminated")
    tokens = text.split("\x00")
    records: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token:
            current.append(token)
        elif current:
            records.append(current)
            current = []
    if current:
        raise GitParseError("worktree list output has an unterminated record")
    parsed: list[ParsedWorktree] = []
    roots: set[str] = set()
    for fields in records:
        if not fields or not fields[0].startswith("worktree "):
            raise GitParseError("worktree record does not begin with worktree")
        root = _absolute_path(fields[0][9:], "worktree root")
        head: str | None = None
        branch: str | None = None
        detached = False
        locked = False
        prunable = False
        seen: set[str] = {"worktree"}
        for field in fields[1:]:
            key, _, value = field.partition(" ")
            if key in seen and key in {"HEAD", "branch", "detached", "locked", "prunable"}:
                raise GitParseError(f"duplicate worktree field: {key}")
            seen.add(key)
            if key == "HEAD":
                if _HEX_RE.fullmatch(value) is None:
                    raise GitParseError("worktree HEAD is not a hexadecimal object id")
                head = value.lower()
            elif key == "branch":
                if not value.startswith("refs/heads/") or any(ord(char) < 32 for char in value):
                    raise GitParseError("worktree branch is not a safe local branch ref")
                branch = value
            elif key == "detached":
                if value:
                    raise GitParseError("detached field must not have a value")
                detached = True
            elif key == "locked":
                locked = True
            elif key == "prunable":
                prunable = True
            elif key in {"bare"}:
                continue
            else:
                raise GitParseError(f"unknown worktree porcelain field: {key}")
        if head is None:
            raise GitParseError("worktree record is missing HEAD")
        if detached == (branch is not None):
            raise GitParseError("worktree must have exactly one of branch or detached")
        root_key = str(root).casefold()
        if root_key in roots:
            raise GitParseError("worktree list contains duplicate roots")
        roots.add(root_key)
        parsed.append(ParsedWorktree(root, head, branch, detached, locked, prunable))
    if not parsed:
        raise GitParseError("worktree list contains no records")
    return tuple(parsed)


def parse_status_z(data: bytes) -> tuple[str, ...]:
    text = decode_utf8(data, label="status output")
    if text and not text.endswith("\x00"):
        raise GitParseError("status output is not NUL terminated")
    tokens = text.split("\x00")
    if tokens and tokens[-1] == "":
        tokens.pop()
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if len(token) < 4 or token[2] != " ":
            raise GitParseError("status record has an invalid XY prefix")
        status = token[:2]
        if any(char not in " MADRCU?!T" for char in status):
            raise GitParseError("status record contains an unknown status code")
        primary = token[3:]
        paths.append(_repo_path(primary))
        if "R" in status or "C" in status:
            index += 1
            if index >= len(tokens):
                raise GitParseError("rename/copy status is missing its second path")
            paths.append(_repo_path(tokens[index]))
        index += 1
    return tuple(sorted(set(paths), key=lambda item: (item.casefold(), item)))


def _repo_path(value: str) -> str:
    if not value or "\\" in value or "\x00" in value or any(ord(char) < 32 for char in value):
        raise GitParseError("status path is not a safe repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ":" in path.parts[0]:
        raise GitParseError("status path must be repository-relative")
    for segment in path.parts:
        base = segment.split(".", 1)[0].casefold()
        if (
            segment in {"", ".", ".."}
            or segment.endswith((" ", "."))
            or base in _RESERVED_NAMES
        ):
            raise GitParseError("status path contains an unsafe segment")
    return path.as_posix()


def _absolute_path(value: str, label: str) -> Path:
    if not value or "\x00" in value or any(ord(char) < 32 for char in value):
        raise GitParseError(f"{label} is invalid")
    path = Path(value)
    if not path.is_absolute():
        raise GitParseError(f"{label} must be absolute")
    return path.resolve()


def _absolute_or_relative_path(value: str, root: Path, label: str) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_absolute():
        raise GitParseError(f"{label} must resolve to an absolute path")
    return resolved
