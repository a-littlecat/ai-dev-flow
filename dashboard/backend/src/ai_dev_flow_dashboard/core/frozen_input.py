"""Freeze TASK bytes before invoking independent parsers."""

from __future__ import annotations

import ctypes
import hashlib
import os
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .canonical import canonical_sha256
from .models import FrozenProjectInput, FrozenTaskInput


class FrozenInputError(RuntimeError):
    """The project input cannot be frozen safely."""


class FrozenInputChangedError(FrozenInputError):
    """A source changed between freeze and candidate publication."""


class _LeaseGuard:
    def __init__(self) -> None:
        self.active = True


class FrozenInputLoader:
    """Read project TASK files once and later prove they did not change."""

    @contextmanager
    def lease(self, project_root: str | Path) -> Iterator[FrozenProjectInput]:
        if os.name != "nt":
            raise FrozenInputError("atomic frozen input lease is only supported on Windows")
        root, task_dir = self._resolve_root(project_root)
        before_paths = self._task_paths(root, task_dir)
        if not before_paths:
            raise FrozenInputError("project contains no Markdown TASK files")
        handles: list[int] = []
        guard = _LeaseGuard()
        try:
            for path in before_paths:
                handles.append(self._open_windows_read_lease(path))
            after_paths = self._task_paths(root, task_dir)
            if after_paths != before_paths:
                raise FrozenInputChangedError("TASK file set changed while acquiring input lease")
            frozen = self.load(root, lease_guard=guard)
            if tuple(item.path for item in frozen.tasks) != before_paths:
                raise FrozenInputChangedError("frozen TASK set differs from leased file set")
            yield frozen
            self.verify_unchanged(frozen)
        finally:
            guard.active = False
            for handle in reversed(handles):
                self._close_windows_handle(handle)

    def load(
        self,
        project_root: str | Path,
        *,
        lease_guard: _LeaseGuard | None = None,
    ) -> FrozenProjectInput:
        root, task_dir = self._resolve_root(project_root)
        if lease_guard is not None and not lease_guard.active:
            raise FrozenInputError("input lease is not active")

        frozen: list[FrozenTaskInput] = []
        for resolved in self._task_paths(root, task_dir):
            path = resolved
            before = resolved.stat()
            content = resolved.read_bytes()
            after = resolved.stat()
            before_signature = self._stat_signature(before)
            after_signature = self._stat_signature(after)
            if before_signature != after_signature:
                raise FrozenInputChangedError(f"TASK changed while being frozen: {path}")
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise FrozenInputError(f"TASK is not valid UTF-8: {path}") from exc
            source_path = unicodedata.normalize("NFC", resolved.relative_to(root).as_posix())
            frozen.append(
                FrozenTaskInput(
                    path=resolved,
                    source_path=source_path,
                    content=content,
                    text=text,
                    mtime_ns=after.st_mtime_ns,
                    size=after.st_size,
                    sha256=hashlib.sha256(content).hexdigest(),
                    ctime_ns=getattr(after, "st_ctime_ns", None),
                    file_identity=(after.st_dev, after.st_ino),
                )
            )
        if not frozen:
            raise FrozenInputError("project contains no Markdown TASK files")
        manifest = tuple((item.source_path, item.sha256, item.mtime_ns, item.size) for item in frozen)
        return FrozenProjectInput(
            root,
            tuple(frozen),
            canonical_sha256(manifest),
            lease_guard,
        )

    @staticmethod
    def _resolve_root(project_root: str | Path) -> tuple[Path, Path]:
        root = Path(project_root).resolve()
        task_dir = (root / "docs" / "tasks").resolve()
        if not task_dir.is_dir() or not task_dir.is_relative_to(root):
            raise FrozenInputError("project root must contain docs/tasks inside the project")
        return root, task_dir

    @staticmethod
    def _task_paths(root: Path, task_dir: Path) -> tuple[Path, ...]:
        result: list[Path] = []
        for path in sorted(task_dir.glob("*.md"), key=lambda item: item.as_posix()):
            resolved = path.resolve()
            if not resolved.is_relative_to(task_dir):
                raise FrozenInputError(f"TASK path escapes docs/tasks: {path}")
            result.append(resolved)
        return tuple(result)

    def verify_unchanged(self, frozen: FrozenProjectInput) -> None:
        expected_paths = tuple(item.source_path for item in frozen.tasks)
        task_dir = frozen.project_root / "docs" / "tasks"
        current_paths = tuple(
            item.resolve().relative_to(frozen.project_root).as_posix()
            for item in sorted(task_dir.glob("*.md"), key=lambda path: path.as_posix())
        )
        if current_paths != expected_paths:
            raise FrozenInputChangedError("TASK file set changed after input freeze")
        for item in frozen.tasks:
            try:
                stat = item.path.stat()
                digest = hashlib.sha256(item.path.read_bytes()).hexdigest()
            except OSError as exc:
                raise FrozenInputChangedError(f"TASK disappeared after input freeze: {item.source_path}") from exc
            if (
                stat.st_size != item.size
                or stat.st_mtime_ns != item.mtime_ns
                or (
                    item.ctime_ns is not None
                    and getattr(stat, "st_ctime_ns", None) != item.ctime_ns
                )
                or (
                    item.file_identity is not None
                    and (stat.st_dev, stat.st_ino) != item.file_identity
                )
                or digest != item.sha256
            ):
                raise FrozenInputChangedError(f"TASK changed after input freeze: {item.source_path}")

    @staticmethod
    def _stat_signature(stat) -> tuple[int, int, int | None, int, int]:
        return (
            stat.st_mtime_ns,
            stat.st_size,
            getattr(stat, "st_ctime_ns", None),
            stat.st_dev,
            stat.st_ino,
        )

    @staticmethod
    def _open_windows_read_lease(path: Path) -> int:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            str(path),
            0x80000000,
            0x00000001,
            None,
            3,
            0x00000080,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle == invalid_handle:
            error = ctypes.get_last_error()
            raise FrozenInputError(
                f"cannot acquire read-only TASK lease: {path.name} (winerror={error})"
            )
        return int(handle)

    @staticmethod
    def _close_windows_handle(handle: int) -> None:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        close_handle(handle)
