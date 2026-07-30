"""Single-process, loopback-only Dashboard runtime for an installed Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import sys
import tempfile
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime_compat import (
    RuntimeCompatibilityError,
    resolve_skill_runtime,
    runtime_bundle_fingerprint,
    skill_fingerprint,
    validate_project_schemas,
    verify_runtime_bundle,
)
from .server import create_local_server
from .snapshot import PollingWatcher, SnapshotCoordinator


LOOPBACK = "127.0.0.1"
RUNTIME_ROOT_ENV = "AI_DEV_FLOW_DASHBOARD_RUNTIME_ROOT"
MONITOR_INTERVAL_SECONDS = 2.0


class PortableRuntimeError(RuntimeError):
    """Portable runtime preflight or lifecycle failure."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the installed, read-only ai-dev-flow Dashboard",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--skill-root")
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="loopback port; 0 (default) asks the OS for a free port",
    )
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument(
        "--runtime-root",
        help="instance state root (defaults to the user-local runtime cache)",
    )
    return parser


def _validate_project_root(project_root: Path) -> None:
    if not (project_root / "docs" / "tasks").is_dir():
        raise PortableRuntimeError("project root must contain docs/tasks")
    if not (project_root / ".git").exists():
        raise PortableRuntimeError("project root must be a Git working tree root")


def _static_root() -> Path:
    dashboard_root = Path(__file__).resolve().parents[3]
    candidates = (
        dashboard_root / "static",
        dashboard_root / "frontend" / "dist",
    )
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate.resolve()
    raise PortableRuntimeError(
        "built Dashboard frontend is missing; rebuild the Skill runtime"
    )


def _default_runtime_root() -> Path:
    configured = os.environ.get(RUNTIME_ROOT_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return (
            Path(local_app_data)
            / "ai-dev-flow"
            / "dashboard"
            / "runtime"
        ).resolve()
    return (
        Path(tempfile.gettempdir())
        / "ai-dev-flow"
        / "dashboard"
        / "runtime"
    ).resolve()


def _project_key(project_root: Path) -> str:
    normalized = os.path.normcase(str(project_root.resolve())).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:20]


def _assert_external_runtime_root(
    runtime_root: Path,
    *,
    project_root: Path,
    skill_roots: tuple[Path, ...],
) -> None:
    target = runtime_root.resolve()
    for protected in (project_root.resolve(), *(item.resolve() for item in skill_roots)):
        try:
            target.relative_to(protected)
        except ValueError:
            continue
        raise PortableRuntimeError(
            f"runtime root must not be inside project or Skill: {target}"
        )


class InstanceState:
    def __init__(
        self,
        project_root: Path,
        *,
        runtime_root: Path,
    ) -> None:
        self.runtime_root = runtime_root.resolve()
        self.project_key = _project_key(project_root)
        self.instance_id = f"{os.getpid()}-{uuid.uuid4().hex[:16]}"
        self.instance_dir = (
            self.runtime_root
            / self.project_key
            / self.instance_id
        ).resolve()
        self.state_path = self.instance_dir / "state.json"
        self.instance_dir.mkdir(parents=True, exist_ok=False)

    def write(self, payload: dict[str, Any]) -> None:
        temporary = self.instance_dir / f".state-{uuid.uuid4().hex}.tmp"
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, self.state_path)

    def close(self) -> None:
        try:
            relative = self.instance_dir.relative_to(self.runtime_root)
        except ValueError as exc:
            raise PortableRuntimeError(
                "refusing to clean an instance directory outside runtime root"
            ) from exc
        if len(relative.parts) != 2 or relative.parts != (
            self.project_key,
            self.instance_id,
        ):
            raise PortableRuntimeError("refusing to clean an unexpected runtime path")
        shutil.rmtree(self.instance_dir, ignore_errors=False)
        project_dir = self.instance_dir.parent
        try:
            project_dir.rmdir()
        except OSError:
            pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _runtime_payload(
    *,
    state: InstanceState,
    project_root: Path,
    skill_root: Path,
    skill_version: str,
    skill_fingerprint_value: str,
    bundle_fingerprint_value: str | None,
    port: int,
    restart_required: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "ai-dev-flow/dashboard-instance/v1",
        "instance_id": state.instance_id,
        "pid": os.getpid(),
        "project_key": state.project_key,
        "project_root": str(project_root),
        "skill_root": str(skill_root),
        "skill_version": skill_version,
        "skill_fingerprint": skill_fingerprint_value,
        "runtime_bundle_fingerprint": bundle_fingerprint_value,
        "host": LOOPBACK,
        "port": port,
        "started_at": _utc_now(),
        "restart_required": restart_required,
    }


def run(
    args: argparse.Namespace,
    *,
    entry_skill_root: str | Path | None = None,
) -> int:
    if not isinstance(args.port, int) or not 0 <= args.port <= 65535:
        raise PortableRuntimeError("port must be from 0 through 65535")
    project_root = Path(args.project_root).resolve()
    _validate_project_root(project_root)
    runtime = resolve_skill_runtime(
        project_root,
        explicit=args.skill_root,
        entry_skill_root=entry_skill_root,
    )
    entry_root = (
        Path(entry_skill_root).resolve()
        if entry_skill_root is not None
        else runtime.root
    )
    bundle_fingerprint: str | None = None
    if entry_skill_root is not None:
        verify_runtime_bundle(entry_root)
        bundle_fingerprint = runtime_bundle_fingerprint(entry_root)
    validate_project_schemas(project_root, runtime)
    static_root = _static_root()
    coordinator = SnapshotCoordinator(
        project_root,
        skill_root=runtime.root,
    )
    coordinator.refresh()
    if skill_fingerprint(runtime.root) != runtime.fingerprint:
        raise PortableRuntimeError(
            "Skill changed during startup; restart with a stable installation"
        )
    coordinator.set_server_state("ready")
    watcher = PollingWatcher(coordinator)
    server = create_local_server(
        coordinator,
        host=LOOPBACK,
        port=args.port,
        static_root=static_root,
    )
    if bundle_fingerprint is not None:
        verify_runtime_bundle(entry_root)
    if (
        bundle_fingerprint is not None
        and runtime_bundle_fingerprint(entry_root) != bundle_fingerprint
    ):
        server.server_close()
        raise PortableRuntimeError(
            "Dashboard runtime bundle changed during startup; restart with a stable installation"
        )
    runtime_root = (
        Path(args.runtime_root).expanduser().resolve()
        if args.runtime_root
        else _default_runtime_root()
    )
    _assert_external_runtime_root(
        runtime_root,
        project_root=project_root,
        skill_roots=tuple(dict.fromkeys((runtime.root, entry_root))),
    )
    stop_requested = threading.Event()
    monitor_stopped = threading.Event()
    previous_handlers: dict[signal.Signals, Any] = {}
    state: InstanceState | None = None
    watcher_started = False
    monitor_thread: threading.Thread | None = None
    payload: dict[str, Any] = {}

    def monitor_skill() -> None:
        warned = False
        while not monitor_stopped.wait(MONITOR_INTERVAL_SECONDS):
            try:
                changed = (
                    skill_fingerprint(runtime.root) != runtime.fingerprint
                    or (
                        bundle_fingerprint is not None
                        and runtime_bundle_fingerprint(entry_root)
                        != bundle_fingerprint
                    )
                )
            except RuntimeCompatibilityError:
                changed = True
            if changed and not warned:
                warned = True
                payload["restart_required"] = True
                if state is not None:
                    state.write(payload)
                print(
                    "Dashboard warning: the Skill changed after startup; "
                    "this instance remains pinned to its startup modules. Restart required.",
                    file=sys.stderr,
                    flush=True,
                )

    def request_stop(_signum: int, _frame: object) -> None:
        if stop_requested.is_set():
            return
        stop_requested.set()
        threading.Thread(
            target=server.shutdown,
            name=(
                f"dashboard-stop-{state.instance_id}"
                if state is not None
                else "dashboard-stop"
            ),
            daemon=True,
        ).start()

    try:
        state = InstanceState(project_root, runtime_root=runtime_root)
        port = server.server_port
        payload = _runtime_payload(
            state=state,
            project_root=project_root,
            skill_root=runtime.root,
            skill_version=runtime.version,
            skill_fingerprint_value=runtime.fingerprint,
            bundle_fingerprint_value=bundle_fingerprint,
            port=port,
            restart_required=False,
        )
        state.write(payload)
        watcher.start()
        watcher_started = True
        monitor_thread = threading.Thread(
            target=monitor_skill,
            name=f"dashboard-skill-monitor-{state.instance_id}",
            daemon=True,
        )
        monitor_thread.start()
        handled = (signal.SIGINT, signal.SIGTERM)
        previous_handlers = {
            item: signal.signal(item, request_stop)
            for item in handled
        }
        if hasattr(signal, "SIGBREAK"):
            previous_handlers[signal.SIGBREAK] = signal.signal(
                signal.SIGBREAK,
                request_stop,
            )
        page_url = f"http://{LOOPBACK}:{port}/"
        print(f"Dashboard ready: {page_url}", flush=True)
        print(
            f"Instance: {state.instance_id} | project={project_root} | "
            f"Skill={runtime.version}@{runtime.fingerprint[:12]}",
            flush=True,
        )
        print(f"Runtime state: {state.state_path}", flush=True)
        print("Press Ctrl+C to stop this instance.", flush=True)
        if not args.no_open:
            webbrowser.open(page_url)
        server.serve_forever(poll_interval=0.25)
        return 0
    finally:
        monitor_stopped.set()
        if watcher_started:
            watcher.stop()
        server.server_close()
        if monitor_thread is not None:
            monitor_thread.join(timeout=5)
        for item, handler in previous_handlers.items():
            signal.signal(item, handler)
        if state is not None:
            state.close()


def main(
    argv: list[str] | None = None,
    *,
    entry_skill_root: str | Path | None = None,
) -> int:
    try:
        return run(
            _parser().parse_args(argv),
            entry_skill_root=entry_skill_root,
        )
    except (OSError, PortableRuntimeError, RuntimeCompatibilityError) as exc:
        print(f"dashboard launcher error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
