"""Minimal loopback-only dashboard backend entry point."""

from __future__ import annotations

import argparse
import threading
from pathlib import Path

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
    coordinator = SnapshotCoordinator(project_root)
    watcher = PollingWatcher(coordinator)
    server = create_local_server(
        coordinator,
        host=args.host,
        port=args.port,
    )
    watcher.start()

    def initial_refresh() -> None:
        try:
            coordinator.refresh()
            coordinator.set_server_state("ready")
        except Exception:
            coordinator.set_server_state("degraded")

    initial_thread = threading.Thread(
        target=initial_refresh,
        name="dashboard-initial-refresh",
        daemon=True,
    )
    initial_thread.start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        watcher.stop()
        server.server_close()
        initial_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
