"""Minimal loopback-only dashboard backend entry point."""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

from .runtime_compat import (
    RuntimeCompatibilityError,
    resolve_skill_runtime,
    skill_fingerprint,
    validate_project_schemas,
)
from .server import create_local_server
from .snapshot import PollingWatcher, SnapshotCoordinator


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local read-only ai-dev-flow dashboard API")
    parser.add_argument(
        "--project-root",
        default=".",
        help="ai-dev-flow project root (defaults to the current directory)",
    )
    parser.add_argument(
        "--skill-root",
        help="external ai-dev-flow Skill root; auto-detected when omitted",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        choices=("127.0.0.1",),
        help="fixed loopback bind address",
    )
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_root = Path(args.project_root).resolve()
    try:
        runtime = resolve_skill_runtime(
            project_root,
            explicit=args.skill_root,
        )
        validate_project_schemas(project_root, runtime)
    except RuntimeCompatibilityError as exc:
        raise SystemExit(f"dashboard runtime error: {exc}") from exc
    coordinator = SnapshotCoordinator(
        project_root,
        skill_root=runtime.root,
    )
    coordinator.refresh()
    if skill_fingerprint(runtime.root) != runtime.fingerprint:
        raise SystemExit(
            "dashboard runtime error: Skill changed during startup; restart required"
        )
    coordinator.set_server_state("ready")
    watcher = PollingWatcher(coordinator)
    server = create_local_server(
        coordinator,
        host=args.host,
        port=args.port,
    )
    monitor_stopped = threading.Event()

    def monitor_skill() -> None:
        warned = False
        while not monitor_stopped.wait(2.0):
            try:
                changed = skill_fingerprint(runtime.root) != runtime.fingerprint
            except RuntimeCompatibilityError:
                changed = True
            if changed and not warned:
                warned = True
                print(
                    "Dashboard warning: the Skill changed after startup; "
                    "this instance remains pinned. Restart required.",
                    file=sys.stderr,
                    flush=True,
                )

    watcher.start()
    monitor_thread = threading.Thread(
        target=monitor_skill,
        name="dashboard-skill-monitor",
        daemon=True,
    )
    monitor_thread.start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        monitor_stopped.set()
        watcher.stop()
        server.server_close()
        monitor_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
