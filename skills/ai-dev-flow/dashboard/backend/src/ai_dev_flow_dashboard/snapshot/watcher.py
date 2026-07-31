"""Event-driven watcher with debounce and an opt-in integrity sweep."""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from stat import S_ISREG
from typing import Callable

from .builder import _is_temporary
from .coordinator import SnapshotCoordinator
from .events import (
    FileEventSource,
    PollingManifestEventSource,
    WatchRequest,
    default_event_source,
)


class PollingWatcher:
    """Keep the historical public name while avoiding continuous polling on Windows."""

    def __init__(
        self,
        coordinator: SnapshotCoordinator,
        *,
        poll_interval: float = 0.05,
        debounce_seconds: float = 0.2,
        max_wait_seconds: float = 1.0,
        git_probe_interval: float | None = None,
        integrity_interval: float | None = None,
        fallback_interval: float = 5.0,
        pause_without_clients: bool = False,
        event_source: FileEventSource | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not (0 < poll_interval <= debounce_seconds <= max_wait_seconds):
            raise ValueError("watcher timing must satisfy poll <= debounce <= max wait")
        if git_probe_interval is not None:
            integrity_interval = git_probe_interval
        if integrity_interval is not None and integrity_interval <= 0:
            raise ValueError("integrity interval must be positive")
        if fallback_interval <= 0:
            raise ValueError("fallback interval must be positive")
        self.coordinator = coordinator
        self.poll_interval = poll_interval
        self.debounce_seconds = debounce_seconds
        self.max_wait_seconds = max_wait_seconds
        self.integrity_interval = integrity_interval
        self.fallback_interval = fallback_interval
        self.pause_without_clients = pause_without_clients
        self._monotonic = monotonic
        self._event_source = event_source
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._idle = threading.Event()
        self._state_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._active_clients = 0
        self._change_first: float | None = None
        self._change_last: float | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._wake.clear()
        self._idle.clear()
        self.coordinator.set_watcher_state("starting")
        self._thread = threading.Thread(
            target=self._run,
            name="dashboard-readonly-watcher",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def wait_until_idle(self, timeout: float = 5.0) -> bool:
        return self._idle.wait(timeout)

    def client_connected(self) -> None:
        with self._state_lock:
            self._active_clients += 1
        self._wake.set()

    def client_disconnected(self) -> None:
        with self._state_lock:
            self._active_clients = max(0, self._active_clients - 1)
        self._wake.set()

    def notify_change(self) -> None:
        now = self._monotonic()
        with self._state_lock:
            if self._change_first is None:
                self._change_first = now
            self._change_last = now
        self._wake.set()

    def capture_manifest(self) -> tuple[tuple[str, int, int, int, int], ...]:
        root = self.coordinator.project_root
        paths: set[Path] = set()
        task_dir = root / "docs" / "tasks"
        paths.update(
            path.absolute()
            for path in task_dir.glob("*.md")
            if not _is_temporary(path)
        )
        board = root / "docs" / "TASK_BOARD.md"
        paths.add(board.absolute())
        for watch_path in self.coordinator.watch_paths:
            resolved = watch_path.resolve()
            if resolved.is_file():
                paths.add(resolved)
            elif resolved.is_dir():
                for child in resolved.rglob("*"):
                    if not _is_temporary(child):
                        paths.add(child.absolute())
        for watch_root in getattr(self.coordinator, "watch_roots", ()):
            resolved_root = Path(watch_root).resolve()
            if not resolved_root.is_dir():
                continue
            if any(
                _is_relative_to(resolved_root, excluded)
                for excluded in self._excluded_roots()
            ):
                continue
            paths.update(
                _manifest_tree_files(
                    resolved_root,
                    excluded_roots=self._excluded_roots(),
                )
            )

        def stat_entry(path: Path) -> tuple[str, int, int, int, int] | None:
            try:
                value = path.stat()
            except OSError:
                return None
            if not S_ISREG(value.st_mode):
                return None
            return (
                str(path),
                value.st_mtime_ns,
                value.st_ctime_ns,
                value.st_size,
                value.st_ino,
            )

        ordered = sorted(paths, key=lambda item: str(item).casefold())
        with ThreadPoolExecutor(
            max_workers=min(32, max(1, len(ordered))),
            thread_name_prefix="dashboard-watch-stat",
        ) as executor:
            entries = tuple(executor.map(stat_entry, ordered))
        return tuple(item for item in entries if item is not None)

    def _run(self) -> None:
        source: FileEventSource | None = None
        try:
            source = self._start_event_source()
            self._idle.clear()
            self._refresh_with_armed_paths(source)
            self.coordinator.set_watcher_state("ready")
            self._idle.set()
            next_integrity = self._next_integrity_deadline()
            while not self._stop.is_set():
                timeout = self._wait_timeout(next_integrity)
                self._wake.wait(timeout)
                self._wake.clear()
                if self._stop.is_set():
                    break
                failure = getattr(source, "failure", None)
                if failure is not None:
                    if (
                        self._event_source is not None
                        or isinstance(source, PollingManifestEventSource)
                    ):
                        raise failure
                    source.stop()
                    source = self._start_fallback_event_source()
                    with self._state_lock:
                        self._change_first = None
                        self._change_last = None
                    self._idle.clear()
                    self._refresh_with_armed_paths(source)
                    self._idle.set()
                    next_integrity = self._next_integrity_deadline()
                    continue

                now = self._monotonic()
                with self._state_lock:
                    active = self._is_active_locked()
                    change_due = (
                        self._change_first is not None
                        and self._change_last is not None
                        and (
                            now - self._change_last >= self.debounce_seconds
                            or now - self._change_first >= self.max_wait_seconds
                        )
                    )
                integrity_due = (
                    active
                    and next_integrity is not None
                    and now >= next_integrity
                )
                if not (change_due or integrity_due):
                    if not active:
                        next_integrity = None
                    elif (
                        next_integrity is None
                        and self.integrity_interval is not None
                    ):
                        next_integrity = now + self.integrity_interval
                    continue

                with self._state_lock:
                    if change_due:
                        self._change_first = None
                        self._change_last = None
                self._idle.clear()
                self._refresh_with_armed_paths(source)
                next_integrity = (
                    self._monotonic() + self.integrity_interval
                    if self.integrity_interval is not None
                    else None
                )
                self._idle.set()
        except BaseException:
            self.coordinator.set_watcher_state("failed")
            self._idle.set()
        finally:
            if source is not None:
                source.stop()

    def _start_event_source(self) -> FileEventSource:
        source = self._event_source or default_event_source(self.capture_manifest)
        try:
            source.start(self._event_requests(), self.notify_change)
            return source
        except OSError:
            if self._event_source is not None:
                raise
            return self._start_fallback_event_source()

    def _start_fallback_event_source(self) -> PollingManifestEventSource:
        fallback = PollingManifestEventSource(
            self.capture_manifest,
            interval=self.fallback_interval,
        )
        fallback.start(self._event_requests(), self.notify_change)
        return fallback

    def _refresh_with_armed_paths(self, source: FileEventSource) -> None:
        """Refresh only after current roots are armed, then close new-root races."""

        refresh = getattr(
            self.coordinator,
            "refresh_for_watcher",
            self.coordinator.refresh,
        )
        for _ in range(4):
            armed_paths = set(self._event_requests())
            source.update(armed_paths)
            refresh()
            desired_paths = set(self._event_requests())
            if desired_paths == armed_paths:
                return
        raise RuntimeError("watch roots did not stabilize during refresh")

    def _event_requests(self) -> tuple[WatchRequest, ...]:
        requests: dict[Path, bool] = {}

        def add(directory: Path, recursive: bool) -> None:
            resolved = directory.resolve()
            if not resolved.is_dir():
                return
            requests[resolved] = requests.get(resolved, False) or recursive

        roots = tuple(getattr(self.coordinator, "watch_roots", ())) or (
            self.coordinator.project_root,
        )
        excluded_roots = self._excluded_roots()
        for root_value in roots:
            root = Path(root_value).resolve()
            for request in _content_watch_requests(
                root,
                excluded_roots=excluded_roots,
            ):
                add(request.directory, request.recursive)

        for watch_path in self.coordinator.watch_paths:
            path = Path(watch_path).resolve()
            if path.is_dir():
                add(path, True)
            else:
                add(path.parent, False)

        return tuple(
            WatchRequest(directory=path, recursive=recursive)
            for path, recursive in sorted(
                requests.items(),
                key=lambda item: str(item[0]).casefold(),
            )
        )

    def _excluded_roots(self) -> tuple[Path, ...]:
        return tuple(
            Path(item).resolve()
            for item in getattr(
                self.coordinator,
                "watch_excluded_roots",
                (),
            )
        )

    def _is_active_locked(self) -> bool:
        return not self.pause_without_clients or self._active_clients > 0

    def _next_integrity_deadline(self) -> float | None:
        with self._state_lock:
            return (
                self._monotonic() + self.integrity_interval
                if self._is_active_locked() and self.integrity_interval is not None
                else None
            )

    def _wait_timeout(self, next_integrity: float | None) -> float | None:
        now = self._monotonic()
        deadlines: list[float] = []
        with self._state_lock:
            active = self._is_active_locked()
            if self._change_first is not None and self._change_last is not None:
                deadlines.extend(
                    (
                        self._change_last + self.debounce_seconds,
                        self._change_first + self.max_wait_seconds,
                    )
                )
        if active and next_integrity is not None:
            deadlines.append(next_integrity)
        if not deadlines:
            return None
        return max(0.0, min(deadlines) - now)


def _manifest_tree_files(
    root: Path,
    *,
    excluded_roots: tuple[Path, ...] = (),
) -> set[Path]:
    """Capture Worktree content without traversing Git's object database."""

    resolved_root = root.resolve()
    if any(_is_relative_to(resolved_root, excluded) for excluded in excluded_roots):
        return set()
    paths: set[Path] = set()
    for current, directory_names, file_names in os.walk(resolved_root):
        current_path = Path(current)
        directory_names[:] = [
            name
            for name in directory_names
            if name.casefold() != ".git"
            and (current_path / name).resolve() not in excluded_roots
        ]
        for name in file_names:
            path = (current_path / name).absolute()
            try:
                relative = path.relative_to(resolved_root)
            except ValueError:
                continue
            if (
                len(relative.parts) >= 3
                and relative.parts[0].casefold() == "docs"
                and relative.parts[1].casefold() == "tasks"
                and _is_temporary(path)
            ):
                continue
            paths.add(path)
    return paths


def _content_watch_requests(
    root: Path,
    *,
    excluded_roots: tuple[Path, ...],
) -> set[WatchRequest]:
    """Partition content watches so metadata subtrees are never recursive."""

    requests: set[WatchRequest] = set()

    def visit(directory: Path) -> None:
        resolved = directory.resolve()
        if not resolved.is_dir() or any(
            _is_relative_to(resolved, excluded)
            for excluded in excluded_roots
        ):
            return
        requests.add(WatchRequest(resolved, False))
        try:
            children = tuple(resolved.iterdir())
        except OSError:
            return
        for child in children:
            if not child.is_dir() or child.name.casefold() == ".git":
                continue
            child_resolved = child.resolve()
            if child_resolved in excluded_roots:
                continue
            contains_exclusion = any(
                _is_relative_to(excluded, child_resolved)
                for excluded in excluded_roots
            )
            if contains_exclusion:
                visit(child_resolved)
            else:
                requests.add(WatchRequest(child_resolved, True))

    visit(root)
    return requests


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
