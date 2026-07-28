"""Thread-safe atomic publication and direct-successor revision history."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_dev_flow_dashboard.core import validated_canonical_bytes

from .builder import SnapshotBuildResult, SnapshotBuilder, _utc_now


@dataclass(frozen=True)
class PublishedSnapshot:
    snapshot: dict[str, Any]
    payload: bytes
    etag: str
    previous_revision: str | None
    changed_task_ids: tuple[str, ...]

    @property
    def revision(self) -> str:
        return str(self.snapshot["revision"])


class SnapshotCoordinator:
    def __init__(
        self,
        project_root: str | Path,
        *,
        builder: SnapshotBuilder | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.builder = builder or SnapshotBuilder(self.project_root)
        self._condition = threading.Condition(threading.RLock())
        self._refresh_lock = threading.Lock()
        self._current: PublishedSnapshot | None = None
        self._last_refresh_at: str | None = None
        self._server_state = "starting"
        self._watcher_state = "starting"
        self._watch_paths: tuple[Path, ...] = ()
        self._last_git_watch_fingerprint: str | None = None

    def refresh(self) -> PublishedSnapshot:
        return self._refresh(copy_for_caller=True)

    def refresh_for_watcher(self) -> None:
        """Refresh and publish without materializing a public snapshot copy."""

        self._refresh(copy_for_caller=False)

    def _refresh(
        self,
        *,
        copy_for_caller: bool,
    ) -> PublishedSnapshot | None:
        with self._refresh_lock:
            result: SnapshotBuildResult = self.builder.build()
            payload = result.payload or validated_canonical_bytes(result.snapshot)
            revision = str(result.snapshot["revision"])
            published: PublishedSnapshot
            with self._condition:
                previous = self._current
                self._last_refresh_at = _utc_now()
                self._watch_paths = result.git.watch_paths
                self._last_git_watch_fingerprint = result.git.watch_fingerprint
                if previous is not None and previous.revision == revision:
                    published = previous
                else:
                    changed = self.builder.changed_task_ids(
                        previous.snapshot if previous else None,
                        result.snapshot,
                    )
                    published = PublishedSnapshot(
                        snapshot=result.snapshot,
                        payload=payload,
                        etag=f'"sha256-{revision}"',
                        previous_revision=previous.revision if previous else None,
                        changed_task_ids=changed,
                    )
                    self._current = published
                    self._condition.notify_all()
            return _clone_published(published) if copy_for_caller else None

    def current(self) -> PublishedSnapshot | None:
        with self._condition:
            return (
                _clone_published(self._current)
                if self._current is not None
                else None
            )

    def wait_for_revision_change(
        self,
        last_revision: str,
        timeout: float,
    ) -> PublishedSnapshot | None:
        with self._condition:
            self._condition.wait_for(
                lambda: self._current is not None
                and self._current.revision != last_revision,
                timeout=timeout,
            )
            if self._current is None or self._current.revision == last_revision:
                return None
            current = self._current
        return _clone_published(current)

    def wait_for_event(
        self,
        last_revision: str,
        timeout: float,
    ) -> dict[str, Any] | None:
        """Wait for a successor and return only the immutable wire event."""

        with self._condition:
            self._condition.wait_for(
                lambda: self._current is not None
                and self._current.revision != last_revision,
                timeout=timeout,
            )
            if self._current is None or self._current.revision == last_revision:
                return None
            current = self._current
            return self.event_payload(last_revision, current=current)

    def event_payload(
        self,
        last_event_id: str | None,
        *,
        current: PublishedSnapshot | None = None,
    ) -> dict[str, Any] | None:
        record = current or self.current()
        if record is None:
            return None
        all_task_ids = tuple(sorted(item["task_id"] for item in record.snapshot["tasks"]))
        if last_event_id is None:
            changed = all_task_ids
            reset = True
        elif last_event_id == record.revision:
            return None
        elif last_event_id == record.previous_revision:
            changed = record.changed_task_ids
            reset = False
        else:
            changed = ()
            reset = True
        return {
            "schema_version": "ai-dev-flow/dashboard-event/v1",
            "revision": record.revision,
            "state": record.snapshot["state"],
            "changed_task_ids": list(changed),
            "reset_required": reset,
        }

    def health(self) -> dict[str, Any]:
        with self._condition:
            current = self._current
            counts = (
                dict(current.snapshot["summary"]["counts_by_severity"])
                if current
                else {"error": 0, "violation": 0, "warning": 0, "info": 0}
            )
            server_state = self._server_state
            if current and current.snapshot["state"] != "fresh":
                server_state = "degraded"
            if current and current.snapshot["project"]["git_state"] != "ok":
                server_state = "degraded"
            if self._watcher_state == "failed":
                server_state = "degraded"
            return {
                "schema_version": "ai-dev-flow/dashboard-health/v1",
                "server_state": server_state,
                "watcher_state": self._watcher_state,
                "last_refresh_at": self._last_refresh_at,
                "snapshot_state": current.snapshot["state"] if current else None,
                "revision": current.revision if current else None,
                "diagnostic_counts": counts,
            }

    @property
    def watch_paths(self) -> tuple[Path, ...]:
        with self._condition:
            schema_path = getattr(self.builder, "schema_path", None)
            paths = (
                (Path(schema_path).resolve(),)
                if schema_path is not None
                else ()
            )
            return tuple(dict.fromkeys((*self._watch_paths, *paths)))

    def probe_git_fingerprint(self) -> str:
        """Collect a read-only status token so unstaged linked-Worktree changes wake the watcher."""

        return self.builder.git_collector.collect().watch_fingerprint

    @property
    def last_git_watch_fingerprint(self) -> str | None:
        with self._condition:
            return self._last_git_watch_fingerprint

    def set_server_state(self, state: str) -> None:
        if state not in {"starting", "ready", "degraded"}:
            raise ValueError("invalid server state")
        with self._condition:
            self._server_state = state

    def set_watcher_state(self, state: str) -> None:
        if state not in {"starting", "ready", "failed"}:
            raise ValueError("invalid watcher state")
        with self._condition:
            self._watcher_state = state


def _clone_published(value: PublishedSnapshot) -> PublishedSnapshot:
    return PublishedSnapshot(
        snapshot=json.loads(value.payload),
        payload=value.payload,
        etag=value.etag,
        previous_revision=value.previous_revision,
        changed_task_ids=value.changed_task_ids,
    )
