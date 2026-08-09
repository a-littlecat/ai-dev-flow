"""Standard-library loopback HTTP server and SSE transport."""

from __future__ import annotations

import mimetypes
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from ai_dev_flow_dashboard.core import canonical_bytes
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.snapshot import SnapshotCoordinator
from ai_dev_flow_dashboard.runtime import RuntimeSessionStore

from .api import ApiResponse, DashboardApi, known_route, task_id_from_path


LOOPBACK_HOST = "127.0.0.1"
SSE_RETRY_MS = 2000
SSE_HEARTBEAT_SECONDS = 15.0
SSE_WRITE_TIMEOUT_SECONDS = 30.0
SSE_MAX_EVENT_BYTES = 64 * 1024
STATIC_SUFFIXES = frozenset({".html", ".js", ".css", ".svg", ".png", ".webp", ".woff2"})


class DashboardHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        coordinator: SnapshotCoordinator,
        *,
        static_root: str | Path | None = None,
        heartbeat_seconds: float = SSE_HEARTBEAT_SECONDS,
        write_timeout_seconds: float = SSE_WRITE_TIMEOUT_SECONDS,
        max_event_bytes: int = SSE_MAX_EVENT_BYTES,
        on_sse_client_change: Callable[[bool], None] | None = None,
        runtime_store: RuntimeSessionStore | None = None,
    ) -> None:
        host, _ = server_address
        if host != LOOPBACK_HOST:
            raise ValueError("dashboard server may bind only to 127.0.0.1")
        self.coordinator = coordinator
        self.api = DashboardApi(coordinator, runtime_store=runtime_store)
        self.static_assets = (
            _load_static_assets(Path(static_root).resolve())
            if static_root is not None
            else {}
        )
        self.heartbeat_seconds = heartbeat_seconds
        self.write_timeout_seconds = write_timeout_seconds
        self.max_event_bytes = max_event_bytes
        self.on_sse_client_change = on_sse_client_change
        super().__init__(server_address, DashboardRequestHandler, bind_and_activate=True)


class DashboardRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ai-dev-flow-dashboard"
    sys_version = ""
    server: DashboardHttpServer

    def __getattr__(self, name: str):
        if name.startswith("do_"):
            return lambda: self._dispatch(self.command)
        raise AttributeError(name)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._dispatch("OPTIONS")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def version_string(self) -> str:
        return self.server_version

    def _dispatch(self, method: str) -> None:
        path = urlsplit(self.path).path
        try:
            host = self.headers.get("Host", "")
            if not self._host_allowed(host):
                self._send(self.server.api.host_not_allowed(host))
                return
            if method != "GET":
                response = (
                    self.server.api.method_not_allowed(method)
                    if known_route(path)
                    else self.server.api.route_not_found(path)
                )
                self._send(response, suppress_body=method == "HEAD")
                return
            if path == "/" and self.server.static_assets:
                self._serve_static("index.html")
            elif path.startswith("/assets/") and self.server.static_assets:
                self._serve_static(path.removeprefix("/"))
            elif path == "/api/v1/snapshot":
                self._send(
                    self.server.api.snapshot(self.headers.get("If-None-Match"))
                )
            elif path == "/api/v1/console":
                self._send(
                    self.server.api.console(self.headers.get("If-None-Match"))
                )
            elif path == "/api/v1/health":
                self._send(self.server.api.health())
            elif path == "/api/v1/events":
                self._serve_events()
            elif path.startswith("/api/v1/tasks/"):
                task_id = task_id_from_path(path)
                self._send(self.server.api.task(task_id or ""))
            else:
                self._send(self.server.api.route_not_found(path))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout):
            self.close_connection = True
        except Exception:
            if not self.wfile.closed:
                try:
                    self._send(self.server.api.internal_error())
                except Exception:
                    self.close_connection = True

    def _host_allowed(self, host: str) -> bool:
        port = self.server.server_port
        return host.casefold() in {
            f"127.0.0.1:{port}",
            f"localhost:{port}",
        }

    def _send(self, response: ApiResponse, *, suppress_body: bool = False) -> None:
        self.send_response(response.status)
        for key, value in response.headers:
            self.send_header(key, value)
        self.end_headers()
        if response.body and not suppress_body:
            self.wfile.write(response.body)
            self.wfile.flush()

    def _serve_static(self, relative: str) -> None:
        asset = self.server.static_assets.get(relative)
        if asset is None:
            self._send(self.server.api.route_not_found("/" + relative))
            return
        content_type, body = asset
        response = ApiResponse(
            200,
            (
                *self.server.api.security_headers(),
                ("Content-Type", content_type),
                ("Content-Length", str(len(body))),
            ),
            body,
        )
        self._send(response)

    def _serve_events(self) -> None:
        current = self.server.coordinator.current()
        if current is None:
            self._send(
                self.server.api.error(
                    503,
                    "SNAPSHOT_UNAVAILABLE",
                    {
                        "server_state": self.server.api._unavailable_server_state(),
                    },
                )
            )
            return
        self.send_response(200)
        for key, value in self.server.api.security_headers():
            if key != "Cache-Control":
                self.send_header(key, value)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        self.connection.settimeout(self.server.write_timeout_seconds)
        self._write_sse(b"retry: 2000\n")
        connected = False
        try:
            if self.server.on_sse_client_change is not None:
                self.server.on_sse_client_change(True)
                connected = True
            last_event_id = self.headers.get("Last-Event-ID")
            initial = self.server.coordinator.event_payload(
                last_event_id,
                current=current,
            )
            if initial is not None:
                self._write_sse(_snapshot_event_bytes(initial))
                last_event_id = initial["revision"]
            elif last_event_id is None:
                last_event_id = current.revision

            while not self.close_connection:
                event = self.server.coordinator.wait_for_event(
                    last_event_id,
                    self.server.heartbeat_seconds,
                )
                if event is None:
                    self._write_sse(b": keep-alive\n\n")
                    continue
                self._write_sse(_snapshot_event_bytes(event))
                last_event_id = event["revision"]
        finally:
            if connected and self.server.on_sse_client_change is not None:
                self.server.on_sse_client_change(False)

    def _write_sse(self, payload: bytes) -> None:
        if len(payload) > self.server.max_event_bytes:
            self.close_connection = True
            raise ConnectionAbortedError("SSE client buffer limit exceeded")
        self.wfile.write(payload)
        self.wfile.flush()


def _snapshot_event_bytes(event: dict[str, Any]) -> bytes:
    validate_contract(event)
    payload = (
        b"event: snapshot\n"
        + f"id: {event['revision']}\n".encode("ascii")
        + b"data: "
        + canonical_bytes(event)
        + b"\n\n"
    )
    return payload


def _load_static_assets(root: Path) -> dict[str, tuple[str, bytes]]:
    """Read the complete static frontend once so a running instance cannot hot-switch."""

    if not root.is_dir() or not (root / "index.html").is_file():
        raise ValueError("dashboard static root must contain index.html")
    assets: dict[str, tuple[str, bytes]] = {}
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(root).as_posix()
        if relative != "index.html" and not relative.startswith("assets/"):
            continue
        suffix = candidate.suffix.casefold()
        if suffix not in STATIC_SUFFIXES:
            continue
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if suffix in {".html", ".js", ".css"}:
            content_type += "; charset=utf-8"
        assets[relative] = (content_type, candidate.read_bytes())
    return assets


def create_local_server(
    coordinator: SnapshotCoordinator,
    *,
    host: str = LOOPBACK_HOST,
    port: int = 0,
    static_root: str | Path | None = None,
    heartbeat_seconds: float = SSE_HEARTBEAT_SECONDS,
    write_timeout_seconds: float = SSE_WRITE_TIMEOUT_SECONDS,
    max_event_bytes: int = SSE_MAX_EVENT_BYTES,
    on_sse_client_change: Callable[[bool], None] | None = None,
    runtime_store: RuntimeSessionStore | None = None,
) -> DashboardHttpServer:
    if host != LOOPBACK_HOST:
        raise ValueError("non-loopback dashboard binding is forbidden")
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    return DashboardHttpServer(
        (host, port),
        coordinator,
        static_root=static_root,
        heartbeat_seconds=heartbeat_seconds,
        write_timeout_seconds=write_timeout_seconds,
        max_event_bytes=max_event_bytes,
        on_sse_client_change=on_sse_client_change,
        runtime_store=runtime_store,
    )
