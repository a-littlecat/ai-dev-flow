"""Dependency-free filesystem change sources for the Dashboard watcher."""

from __future__ import annotations

import ctypes
import os
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


ChangeCallback = Callable[[], None]


class _Overlapped(ctypes.Structure):
    _fields_ = (
        ("Internal", ctypes.c_size_t),
        ("InternalHigh", ctypes.c_size_t),
        ("Offset", ctypes.c_uint32),
        ("OffsetHigh", ctypes.c_uint32),
        ("hEvent", ctypes.c_void_p),
    )


@dataclass
class _DirectoryWatch:
    handle: int
    completion_event: int
    overlapped: _Overlapped
    buffer: Any
    recursive: bool
    stopping: threading.Event
    io_lock: threading.Lock
    pending: bool = False
    thread: threading.Thread | None = None


@dataclass(frozen=True)
class WatchRequest:
    directory: Path
    recursive: bool


class FileEventSource(Protocol):
    failure: BaseException | None

    def start(
        self,
        paths: Iterable[Path | WatchRequest],
        callback: ChangeCallback,
    ) -> None: ...

    def update(self, paths: Iterable[Path | WatchRequest]) -> None: ...

    def stop(self) -> None: ...


class PollingManifestEventSource:
    """Portable low-frequency fallback that never invokes Git."""

    def __init__(
        self,
        capture_manifest: Callable[[], object],
        *,
        interval: float = 1.0,
    ) -> None:
        if interval <= 0:
            raise ValueError("fallback event interval must be positive")
        self.capture_manifest = capture_manifest
        self.interval = interval
        self.failure: BaseException | None = None
        self._callback: ChangeCallback | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(
        self,
        paths: Iterable[Path | WatchRequest],
        callback: ChangeCallback,
    ) -> None:
        del paths
        if self._thread and self._thread.is_alive():
            return
        previous = self.capture_manifest()
        self._callback = callback
        self.failure = None
        self._stop.clear()

        def run() -> None:
            nonlocal previous
            try:
                while not self._stop.wait(self.interval):
                    current = self.capture_manifest()
                    if current != previous:
                        previous = current
                        callback()
            except BaseException as exc:
                self.failure = exc
                callback()

        self._thread = threading.Thread(
            target=run,
            name="dashboard-portable-file-events",
            daemon=True,
        )
        self._thread.start()

    def update(self, paths: Iterable[Path | WatchRequest]) -> None:
        del paths

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(1.0, self.interval * 2))


class WindowsDirectoryEventSource:
    """Use ReadDirectoryChangesW so idle Windows instances perform no polling."""

    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004
    _OPEN_EXISTING = 3
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OVERLAPPED = 0x40000000
    _NOTIFY_FILTER = (
        0x00000001  # FILE_NOTIFY_CHANGE_FILE_NAME
        | 0x00000002  # FILE_NOTIFY_CHANGE_DIR_NAME
        | 0x00000004  # FILE_NOTIFY_CHANGE_ATTRIBUTES
        | 0x00000008  # FILE_NOTIFY_CHANGE_SIZE
        | 0x00000010  # FILE_NOTIFY_CHANGE_LAST_WRITE
        | 0x00000040  # FILE_NOTIFY_CHANGE_CREATION
    )
    _ERROR_OPERATION_ABORTED = 995
    _ERROR_IO_PENDING = 997
    _ERROR_INVALID_HANDLE = 6
    _ERROR_NOTIFY_ENUM_DIR = 1022
    _INFINITE = 0xFFFFFFFF
    _WAIT_OBJECT_0 = 0

    def __init__(
        self,
        *,
        buffer_size: int = 64 * 1024,
        arm_timeout: float = 2.0,
    ) -> None:
        if os.name != "nt":
            raise OSError("ReadDirectoryChangesW is available only on Windows")
        if buffer_size < 4096:
            raise ValueError("directory event buffer is too small")
        if arm_timeout <= 0:
            raise ValueError("directory event arm timeout must be positive")
        self.buffer_size = buffer_size
        self.arm_timeout = arm_timeout
        self.failure: BaseException | None = None
        self._callback: ChangeCallback | None = None
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._start_stop_lock = threading.Lock()
        self._update_lock = threading.Lock()
        self._stop = threading.Event()
        self._watches: dict[Path, _DirectoryWatch] = {}
        self._closing: dict[Path, _DirectoryWatch] = {}
        self._adding: set[Path] = set()
        self._kernel32 = _load_kernel32()

    def start(
        self,
        paths: Iterable[Path | WatchRequest],
        callback: ChangeCallback,
    ) -> None:
        with self._start_stop_lock:
            self._callback = callback
            self.failure = None
            self._stop.clear()
            self.update(paths)

    def update(self, paths: Iterable[Path | WatchRequest]) -> None:
        with self._update_lock:
            self._update(paths)

    def _update(self, paths: Iterable[Path | WatchRequest]) -> None:
        requested = _normalize_requests(paths)
        with self._lock:
            existing = {
                path: watch.recursive
                for path, watch in self._watches.items()
            }
        removed = {
            path
            for path, recursive in existing.items()
            if requested.get(path) != recursive
        }
        added_requests = {
            path: recursive
            for path, recursive in requested.items()
            if existing.get(path) != recursive
        }
        for path in sorted(removed, key=lambda item: str(item).casefold()):
            self._remove(path)
        added: list[Path] = []
        try:
            for path in sorted(added_requests, key=lambda item: str(item).casefold()):
                self._add(path, recursive=added_requests[path])
                added.append(path)
        except BaseException:
            for path in reversed(added):
                self._remove(path)
            raise

    def stop(self) -> None:
        with self._start_stop_lock:
            self._stop.set()
            with self._condition:
                additions_finished = self._condition.wait_for(
                    lambda: not self._adding,
                    timeout=self.arm_timeout,
                )
                if not additions_finished:
                    raise TimeoutError("directory watchers are still starting")
                paths = tuple(self._watches)
            for path in paths:
                self._remove(path)

    def _add(self, path: Path, *, recursive: bool) -> None:
        with self._condition:
            if self._stop.is_set():
                return
            while path in self._closing or path in self._adding:
                closing = self._closing.get(path)
                if closing is not None and closing.thread is threading.current_thread():
                    return
                available = self._condition.wait_for(
                    lambda: path not in self._closing and path not in self._adding,
                    timeout=self.arm_timeout,
                )
                if not available:
                    raise TimeoutError(f"directory watcher is still changing: {path}")
                if self._stop.is_set():
                    return
            existing = self._watches.get(path)
            if existing is not None:
                if existing.recursive == recursive:
                    return
                raise RuntimeError(f"directory watcher already exists: {path}")
            self._adding.add(path)
        try:
            self._add_reserved(path, recursive=recursive)
        finally:
            with self._condition:
                self._adding.discard(path)
                self._condition.notify_all()

    def _add_reserved(self, path: Path, *, recursive: bool) -> None:
        handle = self._kernel32.CreateFileW(
            str(path),
            self._FILE_LIST_DIRECTORY,
            self._FILE_SHARE_ALL,
            None,
            self._OPEN_EXISTING,
            self._FILE_FLAG_BACKUP_SEMANTICS | self._FILE_FLAG_OVERLAPPED,
            None,
        )
        if handle == _invalid_handle_value():
            raise ctypes.WinError(ctypes.get_last_error())
        completion_event = self._kernel32.CreateEventW(None, True, False, None)
        if not completion_event:
            error = ctypes.get_last_error()
            self._kernel32.CloseHandle(handle)
            raise ctypes.WinError(error)
        watch = _DirectoryWatch(
            handle=int(handle),
            completion_event=int(completion_event),
            overlapped=_Overlapped(hEvent=int(completion_event)),
            buffer=ctypes.create_string_buffer(self.buffer_size),
            recursive=recursive,
            stopping=threading.Event(),
            io_lock=threading.Lock(),
        )
        thread = threading.Thread(
            target=self._watch,
            args=(path, watch),
            name=f"dashboard-directory-events-{len(self._watches) + 1}",
            daemon=True,
        )
        watch.thread = thread
        queued = False
        started = False
        cancelled = False
        try:
            self._queue_read(watch)
            queued = True
            with self._condition:
                if self._stop.is_set():
                    cancelled = True
                    raise RuntimeError("directory watcher start was cancelled")
            thread.start()
            started = True
            with self._condition:
                if self._stop.is_set():
                    cancelled = True
                    raise RuntimeError("directory watcher start was cancelled")
                self._watches[path] = watch
                self._adding.discard(path)
                self._condition.notify_all()
        except BaseException:
            watch.stopping.set()
            if queued:
                with watch.io_lock:
                    self._cancel_pending(watch)
            if started and thread is not threading.current_thread():
                thread.join(timeout=self.arm_timeout)
                if thread.is_alive():
                    raise TimeoutError(
                        f"directory watcher did not stop during startup: {path}"
                    )
            if queued:
                self._cancel_and_drain(watch)
            self._kernel32.CloseHandle(watch.completion_event)
            self._kernel32.CloseHandle(watch.handle)
            if cancelled:
                return
            raise

    def _remove(self, path: Path) -> None:
        with self._condition:
            watch = self._watches.pop(path, None)
            if watch is None:
                closing = self._closing.get(path)
                if closing is None or closing.thread is threading.current_thread():
                    return
                closed = self._condition.wait_for(
                    lambda: path not in self._closing,
                    timeout=self.arm_timeout,
                )
                if not closed:
                    raise TimeoutError(f"directory watcher is still closing: {path}")
                return
            self._closing[path] = watch
        try:
            watch.stopping.set()
            with watch.io_lock:
                self._cancel_pending(watch)
            thread = watch.thread
            if thread and thread is not threading.current_thread():
                thread.join(timeout=self.arm_timeout)
                if thread.is_alive():
                    raise TimeoutError(f"directory watcher did not stop: {path}")
            self._cancel_and_drain(watch)
            self._kernel32.CloseHandle(watch.completion_event)
            self._kernel32.CloseHandle(watch.handle)
        except BaseException:
            with self._condition:
                self._closing.pop(path, None)
                self._watches.setdefault(path, watch)
                self._condition.notify_all()
            raise
        else:
            with self._condition:
                self._closing.pop(path, None)
                self._condition.notify_all()

    def _watch(
        self,
        path: Path,
        watch: _DirectoryWatch,
    ) -> None:
        del path
        while True:
            wait_result = self._kernel32.WaitForSingleObject(
                watch.completion_event,
                self._INFINITE,
            )
            if wait_result != self._WAIT_OBJECT_0:
                self._fail(ctypes.WinError(ctypes.get_last_error()))
                return
            ok, error = self._complete_read(watch, wait=False)
            if watch.stopping.is_set() or self._stop.is_set():
                return
            if not ok:
                if error == self._ERROR_OPERATION_ABORTED:
                    try:
                        if not self._rearm(watch):
                            return
                    except BaseException as exc:
                        self._fail(exc)
                        return
                    continue
                if error == self._ERROR_INVALID_HANDLE:
                    self._fail(ctypes.WinError(error))
                    return
                if error == self._ERROR_NOTIFY_ENUM_DIR:
                    self._notify()
                    try:
                        if not self._rearm(watch):
                            return
                    except BaseException as exc:
                        self._fail(exc)
                        return
                    continue
                self._fail(ctypes.WinError(error))
                return
            self._notify()
            try:
                if not self._rearm(watch):
                    return
            except BaseException as exc:
                self._fail(exc)
                return

    def _rearm(self, watch: _DirectoryWatch) -> bool:
        with watch.io_lock:
            if self._stop.is_set() or watch.stopping.is_set():
                return False
            self._queue_read(watch)
            return True

    def _queue_read(self, watch: _DirectoryWatch) -> None:
        if not self._kernel32.ResetEvent(watch.completion_event):
            error = ctypes.get_last_error()
            raise ctypes.WinError(error)
        ok = self._kernel32.ReadDirectoryChangesW(
            watch.handle,
            watch.buffer,
            self.buffer_size,
            watch.recursive,
            self._NOTIFY_FILTER,
            None,
            ctypes.byref(watch.overlapped),
            None,
        )
        if not ok:
            error = ctypes.get_last_error()
            if error != self._ERROR_IO_PENDING:
                raise ctypes.WinError(error)
        watch.pending = True

    def _cancel_and_drain(self, watch: _DirectoryWatch) -> None:
        with watch.io_lock:
            if not watch.pending:
                return
            self._cancel_pending(watch)
            ok, error = self._complete_read_locked(watch, wait=True)
        if not ok and error not in {
            self._ERROR_OPERATION_ABORTED,
            self._ERROR_INVALID_HANDLE,
        }:
            raise ctypes.WinError(error)

    def _cancel_pending(self, watch: _DirectoryWatch) -> None:
        if not watch.pending:
            return
        self._kernel32.CancelIoEx(
            watch.handle,
            ctypes.byref(watch.overlapped),
        )

    def _complete_read(
        self,
        watch: _DirectoryWatch,
        *,
        wait: bool,
    ) -> tuple[bool, int]:
        with watch.io_lock:
            return self._complete_read_locked(watch, wait=wait)

    def _complete_read_locked(
        self,
        watch: _DirectoryWatch,
        *,
        wait: bool,
    ) -> tuple[bool, int]:
        if not watch.pending:
            return True, 0
        returned = ctypes.c_uint32()
        ok = self._kernel32.GetOverlappedResult(
            watch.handle,
            ctypes.byref(watch.overlapped),
            ctypes.byref(returned),
            wait,
        )
        error = 0 if ok else ctypes.get_last_error()
        watch.pending = False
        return bool(ok), error

    def _notify(self) -> None:
        callback = self._callback
        if callback is not None:
            callback()

    def _fail(self, error: BaseException) -> None:
        self.failure = error
        self._notify()


def default_event_source(
    capture_manifest: Callable[[], object],
) -> FileEventSource:
    if os.name == "nt":
        return WindowsDirectoryEventSource()
    return PollingManifestEventSource(capture_manifest)


def _normalize_requests(
    paths: Iterable[Path | WatchRequest],
) -> dict[Path, bool]:
    requested: dict[Path, bool] = {}
    for item in paths:
        if isinstance(item, WatchRequest):
            directory = item.directory.resolve()
            recursive = item.recursive
        else:
            path = Path(item).resolve()
            directory = path if path.is_dir() else path.parent
            recursive = path.is_dir()
        if not directory.is_dir():
            continue
        requested[directory] = requested.get(directory, False) or recursive
    return requested


def _invalid_handle_value() -> int:
    return ctypes.c_void_p(-1).value or -1


def _load_kernel32():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CreateEventW.argtypes = (
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_wchar_p,
    )
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.ResetEvent.argtypes = (ctypes.c_void_p,)
    kernel32.ResetEvent.restype = ctypes.c_int
    kernel32.WaitForSingleObject.argtypes = (
        ctypes.c_void_p,
        ctypes.c_uint32,
    )
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.ReadDirectoryChangesW.argtypes = (
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
        ctypes.c_void_p,
    )
    kernel32.ReadDirectoryChangesW.restype = ctypes.c_int
    kernel32.GetOverlappedResult.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(_Overlapped),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_int,
    )
    kernel32.GetOverlappedResult.restype = ctypes.c_int
    kernel32.CancelIoEx.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    kernel32.CancelIoEx.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    return kernel32
