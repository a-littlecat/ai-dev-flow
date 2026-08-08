"""Pure API response construction with strict wire validation."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from ai_dev_flow_dashboard.core import validated_canonical_bytes
from ai_dev_flow_dashboard.console import ConsoleBuilder
from ai_dev_flow_dashboard.runtime import RuntimeSessionStore
from ai_dev_flow_dashboard.snapshot import PublishedSnapshot, SnapshotCoordinator


TASK_ID_RE = re.compile(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*")
CSP = (
    "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
    "style-src 'self'; script-src 'self'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'"
)


@dataclass(frozen=True)
class ApiResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


class DashboardApi:
    def __init__(
        self,
        coordinator: SnapshotCoordinator,
        *,
        runtime_store: RuntimeSessionStore | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.console_builder = ConsoleBuilder(
            runtime_store or RuntimeSessionStore(coordinator.project_root)
        )

    def snapshot(self, if_none_match: str | None = None) -> ApiResponse:
        current = self.coordinator.current()
        if current is None:
            return self.error(
                503,
                "SNAPSHOT_UNAVAILABLE",
                {"server_state": self._unavailable_server_state()},
            )
        headers = [("ETag", current.etag)]
        if if_none_match == current.etag:
            return self._response(304, b"", headers)
        return self._response(200, current.payload, headers, content_type="application/json; charset=utf-8")

    def task(self, task_id: str) -> ApiResponse:
        current = self.coordinator.current()
        if TASK_ID_RE.fullmatch(task_id) is None:
            return self.error(400, "INVALID_TASK_ID", {"task_id": task_id})
        if current is None:
            return self.error(
                503,
                "SNAPSHOT_UNAVAILABLE",
                {"server_state": self._unavailable_server_state()},
            )
        snapshot = current.snapshot
        task = next((item for item in snapshot["tasks"] if item["task_id"] == task_id), None)
        if task is None:
            return self.error(404, "TASK_NOT_FOUND", {"task_id": task_id})
        diagnostic_ids = set(task["diagnostic_ids"])
        diagnostics = [
            item
            for item in snapshot["diagnostics"]
            if task_id in item["task_ids"] or item["diagnostic_id"] in diagnostic_ids
        ]
        payload = {
            "schema_version": "ai-dev-flow/dashboard-task-detail/v1",
            "revision": current.revision,
            "task": task,
            "edges": [
                item
                for item in snapshot["edges"]
                if task_id in {item["source_task_id"], item["target_task_id"]}
            ],
            "actions": [
                item for item in snapshot["actions"] if item["task_id"] == task_id
            ],
            "parallel_assessments": [
                item
                for item in snapshot["parallel_assessments"]
                if task_id in {item["left_task_id"], item["right_task_id"]}
            ],
            "diagnostics": diagnostics,
        }
        return self.json(200, payload)

    def health(self) -> ApiResponse:
        return self.json(200, self.coordinator.health())

    def console(self, if_none_match: str | None = None) -> ApiResponse:
        current = self.coordinator.current()
        if current is None:
            return self.error(
                503,
                "SNAPSHOT_UNAVAILABLE",
                {"server_state": self._unavailable_server_state()},
            )
        payload = self.console_builder.build(current)
        etag = f'"sha256-{payload["revision"]}"'
        headers = [("ETag", etag)]
        if if_none_match == etag:
            return self._response(304, b"", headers)
        return self._response(
            200,
            validated_canonical_bytes(payload),
            headers,
            content_type="application/json; charset=utf-8",
        )

    def method_not_allowed(self, method: str) -> ApiResponse:
        return self.error(
            405,
            "METHOD_NOT_ALLOWED",
            {"method": method, "allow": ["GET"]},
            extra_headers=(("Allow", "GET"),),
        )

    def route_not_found(self, path: str) -> ApiResponse:
        return self.error(404, "ROUTE_NOT_FOUND", {"path": path})

    def host_not_allowed(self, host: str) -> ApiResponse:
        return self.error(400, "HOST_NOT_ALLOWED", {"host": host})

    def internal_error(self) -> ApiResponse:
        return self.error(
            500,
            "INTERNAL_ERROR",
            {"incident_id": uuid.uuid4().hex},
        )

    def json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> ApiResponse:
        return self._response(
            status,
            validated_canonical_bytes(payload),
            list(extra_headers),
            content_type="application/json; charset=utf-8",
        )

    def error(
        self,
        status: int,
        code: str,
        details: dict[str, Any],
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> ApiResponse:
        messages = {
            "INVALID_TASK_ID": "任务 ID 形状非法",
            "HOST_NOT_ALLOWED": "Host 不允许",
            "TASK_NOT_FOUND": "任务不存在",
            "ROUTE_NOT_FOUND": "路由不存在",
            "METHOD_NOT_ALLOWED": "方法不允许",
            "SNAPSHOT_UNAVAILABLE": "快照尚不可用",
            "INTERNAL_ERROR": "内部错误",
        }
        current = self.coordinator.current()
        payload = {
            "schema_version": "ai-dev-flow/dashboard-error/v1",
            "error": {
                "code": code,
                "message": messages[code],
                "details": details,
                "provenance": [],
            },
            "revision": current.revision if current else None,
        }
        return self.json(status, payload, extra_headers=extra_headers)

    @staticmethod
    def security_headers() -> tuple[tuple[str, str], ...]:
        return (
            ("Content-Security-Policy", CSP),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("Cache-Control", "private, no-cache"),
        )

    def _response(
        self,
        status: int,
        body: bytes,
        headers: list[tuple[str, str]],
        *,
        content_type: str | None = None,
    ) -> ApiResponse:
        combined = list(self.security_headers())
        combined.extend(headers)
        if content_type is not None:
            combined.append(("Content-Type", content_type))
        combined.append(("Content-Length", str(len(body))))
        return ApiResponse(status, tuple(combined), body)

    def _unavailable_server_state(self) -> str:
        state = self.coordinator.health()["server_state"]
        return "degraded" if state == "degraded" else "starting"


def known_route(path: str) -> bool:
    return path in {
        "/api/v1/snapshot",
        "/api/v1/console",
        "/api/v1/health",
        "/api/v1/events",
    } or path.startswith("/api/v1/tasks/")


def task_id_from_path(path: str) -> str | None:
    prefix = "/api/v1/tasks/"
    if not path.startswith(prefix):
        return None
    return path[len(prefix):]
