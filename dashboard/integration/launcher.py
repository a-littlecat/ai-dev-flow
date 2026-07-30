"""Start the real dashboard backend and frontend as one local read-only stack."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.integration.process_tree import (
    process_group_options,
    terminate_process_tree,
    track_process_tree,
)


LOOPBACK = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8765
DEFAULT_FRONTEND_PORT = 5173
STARTUP_TIMEOUT_SECONDS = 60.0
_LOOPBACK_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class LauncherError(RuntimeError):
    """A local stack preflight or process failed."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--startup-timeout", type=float, default=STARTUP_TIMEOUT_SECONDS)
    return parser


def _validate_port(name: str, value: int) -> None:
    if not 1 <= value <= 65535:
        raise LauncherError(f"{name} must be from 1 through 65535")


def _assert_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            probe.bind((LOOPBACK, port))
        except OSError as exc:
            raise LauncherError(f"loopback port {port} is unavailable: {exc}") from exc


def _resolve_runtime(project_root: Path) -> tuple[Path, Path, Path]:
    if sys.version_info < (3, 11):
        raise LauncherError("Python 3.11 or newer is required")
    required = (
        project_root / "docs" / "tasks",
        project_root / "skills" / "ai-dev-flow" / "scripts" / "workflow_contract.py",
    )
    if not all(path.exists() for path in required):
        raise LauncherError("project root is not an ai-dev-flow checkout")
    dashboard_root = Path(__file__).resolve().parents[1]
    backend_src = dashboard_root / "backend" / "src"
    frontend_root = dashboard_root / "frontend"
    vite_entry = frontend_root / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite_entry.is_file():
        raise LauncherError(
            "frontend dependencies are missing; run `npm ci` in dashboard/frontend first"
        )
    node = shutil.which("node")
    if not node:
        raise LauncherError("Node.js is not available on PATH")
    return backend_src, frontend_root, Path(node)


def _prepend_path(env: dict[str, str], key: str, value: Path) -> None:
    current = env.get(key)
    env[key] = str(value) if not current else str(value) + os.pathsep + current


def build_commands(
    project_root: Path,
    backend_src: Path,
    frontend_root: Path,
    node: Path,
    backend_port: int,
    frontend_port: int,
) -> tuple[list[str], list[str], dict[str, str]]:
    env = os.environ.copy()
    _prepend_path(env, "PYTHONPATH", backend_src)
    env["PYTHONUTF8"] = "1"
    env["DASHBOARD_BACKEND_PORT"] = str(backend_port)
    env["DASHBOARD_FRONTEND_PORT"] = str(frontend_port)
    backend = [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        "-m",
        "ai_dev_flow_dashboard",
        "--project-root",
        str(project_root),
        "--host",
        LOOPBACK,
        "--port",
        str(backend_port),
    ]
    vite_entry = frontend_root / "node_modules" / "vite" / "bin" / "vite.js"
    config = Path(__file__).with_name("vite.config.mjs")
    frontend = [str(node), str(vite_entry), "--config", str(config)]
    return backend, frontend, env


def _ready(url: str) -> bool:
    try:
        with _LOOPBACK_OPENER.open(url, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def _wait_until_ready(
    processes: tuple[subprocess.Popen[bytes], ...],
    url: str,
    timeout: float,
    stop_requested: threading.Event,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_requested.is_set():
            return False
        for process in processes:
            code = process.poll()
            if code is not None:
                raise LauncherError(f"dashboard child process exited early with code {code}")
        if _ready(url):
            return True
        if stop_requested.wait(0.2):
            return False
    raise LauncherError(f"dashboard did not become ready within {timeout:g} seconds")


def _stop(processes: tuple[subprocess.Popen[bytes], ...]) -> None:
    for process in reversed(processes):
        terminate_process_tree(process)
    for process in reversed(processes):
        if process.poll() is not None:
            continue
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            terminate_process_tree(process)
            process.wait(timeout=5)


def run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    _validate_port("backend port", args.backend_port)
    _validate_port("frontend port", args.frontend_port)
    if args.backend_port == args.frontend_port:
        raise LauncherError("backend and frontend ports must differ")
    _assert_port_available(args.backend_port)
    _assert_port_available(args.frontend_port)
    backend_src, frontend_root, node = _resolve_runtime(project_root)
    backend_command, frontend_command, env = build_commands(
        project_root,
        backend_src,
        frontend_root,
        node,
        args.backend_port,
        args.frontend_port,
    )
    child_options = process_group_options()
    if "creationflags" in child_options:
        child_options["creationflags"] |= getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0,
        )
    processes: list[subprocess.Popen[bytes]] = []
    stop_requested = threading.Event()
    previous: dict[signal.Signals, object] = {}

    def request_stop(_signum: int, _frame: object) -> None:
        stop_requested.set()

    page_url = f"http://{LOOPBACK}:{args.frontend_port}/"
    readiness_url = (
        f"http://{LOOPBACK}:{args.frontend_port}/api/v1/snapshot"
    )
    try:
        processes.append(
            track_process_tree(
            subprocess.Popen(
                backend_command,
                cwd=project_root,
                env=env,
                **child_options,
            )
            )
        )
        processes.append(
            track_process_tree(
            subprocess.Popen(
                frontend_command,
                cwd=frontend_root,
                env=env,
                **child_options,
            )
            )
        )
        handled = (signal.SIGINT, signal.SIGTERM)
        previous = {item: signal.signal(item, request_stop) for item in handled}
        if hasattr(signal, "SIGBREAK"):
            previous[signal.SIGBREAK] = signal.signal(
                signal.SIGBREAK,
                request_stop,
            )
        if not _wait_until_ready(
            tuple(processes),
            readiness_url,
            args.startup_timeout,
            stop_requested,
        ):
            return 0
        print(f"Dashboard ready: {page_url}", flush=True)
        print("Press Ctrl+C to stop both local processes.", flush=True)
        if not args.no_open:
            webbrowser.open(page_url)
        while not stop_requested.wait(0.25):
            for process in processes:
                code = process.poll()
                if code is not None:
                    raise LauncherError(f"dashboard child process exited with code {code}")
        return 0
    finally:
        _stop(tuple(processes))
        for item, handler in previous.items():
            signal.signal(item, handler)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(_parser().parse_args(argv))
    except (LauncherError, OSError) as exc:
        print(f"dashboard launcher error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
