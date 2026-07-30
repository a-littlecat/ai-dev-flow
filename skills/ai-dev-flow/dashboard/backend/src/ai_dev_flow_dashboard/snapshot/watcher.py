"""Dependency-free polling watcher with trailing debounce and max wait."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from stat import S_ISREG
from typing import Callable

from .builder import _is_temporary
from .coordinator import SnapshotCoordinator


class PollingWatcher:
    def __init__(
        self,
        coordinator: SnapshotCoordinator,
        *,
        poll_interval: float = 0.05,
        debounce_seconds: float = 0.2,
        max_wait_seconds: float = 1.0,
        git_probe_interval: float = 1.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not (0 < poll_interval <= debounce_seconds <= max_wait_seconds):
            raise ValueError("watcher timing must satisfy poll <= debounce <= max wait")
        if git_probe_interval <= 0:
            raise ValueError("Git probe interval must be positive")
        self.coordinator = coordinator
        self.poll_interval = poll_interval
        self.debounce_seconds = debounce_seconds
        self.max_wait_seconds = max_wait_seconds
        self.git_probe_interval = git_probe_interval
        self._monotonic = monotonic
        self._stop = threading.Event()
        self._idle = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
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
        if self._thread:
            self._thread.join(timeout=timeout)

    def wait_until_idle(self, timeout: float = 5.0) -> bool:
        return self._idle.wait(timeout)

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
        try:
            previous = self.capture_manifest()
            previous_git = self._capture_git_fingerprint()
            next_git_probe = self._monotonic() + self.git_probe_interval
            self.coordinator.set_watcher_state("ready")
            self._idle.set()
            first_change: float | None = None
            last_change: float | None = None
            while not self._stop.wait(self.poll_interval):
                current = self.capture_manifest()
                now = self._monotonic()
                current_git = previous_git
                if now >= next_git_probe:
                    current_git = self._capture_git_fingerprint()
                    next_git_probe = now + self.git_probe_interval
                if current != previous or current_git != previous_git:
                    previous = current
                    previous_git = current_git
                    self._idle.clear()
                    first_change = now if first_change is None else first_change
                    last_change = now
                if first_change is None or last_change is None:
                    continue
                if (
                    now - last_change >= self.debounce_seconds
                    or now - first_change >= self.max_wait_seconds
                ):
                    observed_manifest = previous
                    observed_git = previous_git
                    refresh = getattr(
                        self.coordinator,
                        "refresh_for_watcher",
                        self.coordinator.refresh,
                    )
                    refresh()
                    current = self.capture_manifest()
                    current_git = self._capture_git_fingerprint()
                    candidate_git = getattr(
                        self.coordinator,
                        "last_git_watch_fingerprint",
                        None,
                    )
                    expected_git = (
                        candidate_git
                        if candidate_git is not None
                        else observed_git
                    )
                    now = self._monotonic()
                    next_git_probe = now + self.git_probe_interval
                    previous = current
                    previous_git = current_git
                    if (
                        current != observed_manifest
                        or current_git != expected_git
                    ):
                        first_change = now
                        last_change = now
                    else:
                        first_change = None
                        last_change = None
                        self._idle.set()
        except Exception:
            self.coordinator.set_watcher_state("failed")
            self._idle.set()

    def _capture_git_fingerprint(self) -> str | None:
        probe = getattr(self.coordinator, "probe_git_fingerprint", None)
        return probe() if callable(probe) else None
