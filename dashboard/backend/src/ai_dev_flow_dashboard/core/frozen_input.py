"""Freeze TASK bytes before invoking independent parsers."""

from __future__ import annotations

import ctypes
import hashlib
import os
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import lru_cache
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
        before_board = self._board_path(root)
        if not before_paths:
            raise FrozenInputError("project contains no Markdown TASK files")
        handles: list[int] = []
        guard = _LeaseGuard()
        try:
            source_paths = before_paths + ((before_board,) if before_board else ())
            first_error: Exception | None = None
            with ThreadPoolExecutor(
                max_workers=min(16, len(source_paths)),
                thread_name_prefix="dashboard-source-lease",
            ) as executor:
                futures = [
                    executor.submit(self._open_windows_read_lease, path)
                    for path in source_paths
                ]
                for future in futures:
                    try:
                        handles.append(future.result())
                    except Exception as exc:
                        if first_error is None:
                            first_error = exc
            if first_error is not None:
                raise first_error
            after_paths = self._task_paths(root, task_dir, inspect_reparse_points=False)
            after_board = self._board_path(root, inspect_reparse_point=False)
            if after_paths != before_paths or after_board != before_board:
                raise FrozenInputChangedError("dashboard source file set changed while acquiring input lease")
            frozen = self._load_paths(
                root,
                before_paths,
                board_path=before_board,
                lease_guard=guard,
                source_handles=tuple(handles),
            )
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
        return self._load_paths(
            root,
            self._task_paths(root, task_dir),
            board_path=self._board_path(root),
            lease_guard=lease_guard,
        )

    def _load_paths(
        self,
        root: Path,
        paths: tuple[Path, ...],
        *,
        board_path: Path | None = None,
        lease_guard: _LeaseGuard | None = None,
        source_handles: tuple[int, ...] | None = None,
    ) -> FrozenProjectInput:
        if lease_guard is not None and not lease_guard.active:
            raise FrozenInputError("input lease is not active")

        source_paths = paths + ((board_path,) if board_path else ())
        if source_handles is not None and len(source_handles) != len(source_paths):
            raise FrozenInputError("input lease handle set does not match frozen source set")
        handles = source_handles or (None,) * len(source_paths)
        with ThreadPoolExecutor(
            max_workers=min(16, len(source_paths)),
            thread_name_prefix="dashboard-source-read",
        ) as executor:
            sources = tuple(
                executor.map(
                    lambda pair: self._freeze_path(
                        root,
                        pair[0],
                        lease_guard,
                        source_handle=pair[1],
                    ),
                    zip(source_paths, handles),
                )
            )
        frozen = sources[:len(paths)]
        if not frozen:
            raise FrozenInputError("project contains no Markdown TASK files")
        board = sources[-1] if board_path else None
        sources = tuple(frozen) + ((board,) if board else ())
        manifest = tuple(
            (item.source_path, item.sha256, item.size)
            for item in sorted(sources, key=lambda value: value.source_path)
        )
        return FrozenProjectInput(
            root,
            tuple(frozen),
            canonical_sha256(manifest),
            lease_guard,
            board,
        )

    def _freeze_path(
        self,
        root: Path,
        path: Path,
        lease_guard: _LeaseGuard | None,
        *,
        source_handle: int | None = None,
    ) -> FrozenTaskInput:
        before = path.stat()
        content = (
            self._read_windows_handle(source_handle)
            if source_handle is not None
            else path.read_bytes()
        )
        after = before if lease_guard is not None else path.stat()
        if self._stat_signature(before) != self._stat_signature(after):
            raise FrozenInputChangedError(f"dashboard source changed while being frozen: {path}")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FrozenInputError(f"dashboard source is not valid UTF-8: {path}") from exc
        return FrozenTaskInput(
            path=path,
            source_path=unicodedata.normalize("NFC", path.relative_to(root).as_posix()),
            content=content,
            text=text,
            mtime_ns=after.st_mtime_ns,
            size=after.st_size,
            sha256=hashlib.sha256(content).hexdigest(),
            ctime_ns=getattr(after, "st_ctime_ns", None),
            file_identity=(after.st_dev, after.st_ino),
        )

    @staticmethod
    def _resolve_root(project_root: str | Path) -> tuple[Path, Path]:
        root = Path(project_root).resolve()
        task_dir = (root / "docs" / "tasks").resolve()
        if not task_dir.is_dir() or not task_dir.is_relative_to(root):
            raise FrozenInputError("project root must contain docs/tasks inside the project")
        return root, task_dir

    @staticmethod
    def _task_paths(
        root: Path,
        task_dir: Path,
        *,
        inspect_reparse_points: bool = True,
    ) -> tuple[Path, ...]:
        result: list[Path] = []
        for path in sorted(task_dir.glob("*.md"), key=lambda item: item.as_posix()):
            if inspect_reparse_points:
                try:
                    stat = path.lstat()
                except OSError as exc:
                    raise FrozenInputError(f"TASK path cannot be inspected: {path}") from exc
                resolved = (
                    path.resolve()
                    if getattr(stat, "st_file_attributes", 0) & 0x400
                    else path.absolute()
                )
            else:
                resolved = path.absolute()
            if not resolved.is_relative_to(task_dir):
                raise FrozenInputError(f"TASK path escapes docs/tasks: {path}")
            result.append(resolved)
        return tuple(result)

    def verify_unchanged(self, frozen: FrozenProjectInput) -> None:
        expected_paths = tuple(item.source_path for item in frozen.tasks)
        task_dir = frozen.project_root / "docs" / "tasks"
        current_paths = tuple(
            item.relative_to(frozen.project_root).as_posix()
            for item in self._task_paths(
                frozen.project_root,
                task_dir,
                inspect_reparse_points=False,
            )
        )
        if current_paths != expected_paths:
            raise FrozenInputChangedError("TASK file set changed after input freeze")
        current_board = self._board_path(
            frozen.project_root,
            inspect_reparse_point=False,
        )
        if current_board != (frozen.board.path if frozen.board else None):
            raise FrozenInputChangedError("TASK_BOARD file set changed after input freeze")
        def verify_item(item: FrozenTaskInput) -> None:
            try:
                stat = item.path.stat()
                digest = (
                    item.sha256
                    if getattr(frozen.lease_guard, "active", False)
                    else hashlib.sha256(item.path.read_bytes()).hexdigest()
                )
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

        items = frozen.tasks + ((frozen.board,) if frozen.board else ())
        with ThreadPoolExecutor(
            max_workers=min(16, len(items)),
            thread_name_prefix="dashboard-source-verify",
        ) as executor:
            tuple(executor.map(verify_item, items))

    @staticmethod
    def _board_path(
        root: Path,
        *,
        inspect_reparse_point: bool = True,
    ) -> Path | None:
        path = root / "docs" / "TASK_BOARD.md"
        if not path.is_file():
            return None
        try:
            stat = path.lstat()
        except OSError as exc:
            raise FrozenInputError(f"TASK_BOARD path cannot be inspected: {path}") from exc
        resolved = (
            path.resolve()
            if inspect_reparse_point and getattr(stat, "st_file_attributes", 0) & 0x400
            else path.absolute()
        )
        if not resolved.is_relative_to(root):
            raise FrozenInputError("TASK_BOARD path escapes the project root")
        return resolved

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
        create_file, _ = _windows_file_api()
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
        _, close_handle = _windows_file_api()
        close_handle(handle)

    @staticmethod
    def _read_windows_handle(handle: int) -> bytes:
        """Read exact bytes through the already-exclusive lease handle."""

        get_size, read_file = _windows_read_api()
        size = ctypes.c_longlong()
        if not get_size(handle, ctypes.byref(size)):
            raise FrozenInputError(
                f"cannot size leased TASK source (winerror={ctypes.get_last_error()})"
            )
        if size.value < 0 or size.value > 0xFFFFFFFF:
            raise FrozenInputError("leased TASK source exceeds the supported Windows read size")
        if size.value == 0:
            return b""
        buffer = ctypes.create_string_buffer(size.value)
        read = ctypes.c_ulong()
        if not read_file(
            handle,
            buffer,
            size.value,
            ctypes.byref(read),
            None,
        ):
            raise FrozenInputError(
                f"cannot read leased TASK source (winerror={ctypes.get_last_error()})"
            )
        if read.value != size.value:
            raise FrozenInputError("leased TASK source returned a short Windows read")
        return buffer.raw


@lru_cache(maxsize=1)
def _windows_file_api():
    """Resolve immutable Win32 file APIs once per process."""

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
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    return create_file, close_handle


@lru_cache(maxsize=1)
def _windows_read_api():
    """Resolve Win32 size/read APIs used by already-open lease handles."""

    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_size = kernel32.GetFileSizeEx
    get_size.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_longlong),
    )
    get_size.restype = wintypes.BOOL
    read_file = kernel32.ReadFile
    read_file.argtypes = (
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    read_file.restype = wintypes.BOOL
    return get_size, read_file
