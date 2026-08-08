"""Harness-neutral `adf session` and `adf status` command line interface."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ai_dev_flow_dashboard.console import ConsoleBuilder
from ai_dev_flow_dashboard.runtime import RuntimeSessionError, RuntimeSessionStore
from ai_dev_flow_dashboard.snapshot import SnapshotCoordinator


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adf")
    subcommands = parser.add_subparsers(dest="command", required=True)
    session = subcommands.add_parser("session")
    session_commands = session.add_subparsers(dest="session_command", required=True)
    for name in ("start", "update", "wait", "end", "list"):
        command = session_commands.add_parser(name)
        command.add_argument("--project-root", default=".")
        command.add_argument("--runtime-root")
        command.add_argument("--format", choices=("human", "json"), default="human")
        if name != "list":
            command.add_argument("--session", required=True)
        if name == "start":
            command.add_argument("--task", required=True)
            command.add_argument("--harness", required=True)
            command.add_argument("--phase", required=True)
            command.add_argument("--next-step", required=True)
            command.add_argument("--status-summary", default="")
            command.add_argument("--branch")
            command.add_argument("--worktree")
            command.add_argument("--stale-after-seconds", type=int, default=180)
            command.add_argument("--replace", action="store_true")
        elif name == "update":
            command.add_argument("--phase")
            command.add_argument("--next-step")
            command.add_argument("--status-summary")
        elif name in {"wait", "end"}:
            command.add_argument("--reason", required=True)
    status = subcommands.add_parser("status")
    status.add_argument("--project-root", default=".")
    status.add_argument("--runtime-root")
    status.add_argument("--skill-root")
    status.add_argument("--format", choices=("human", "json"), default="human")
    status.add_argument("--watch", action="store_true")
    status.add_argument("--interval", type=float, default=2.0)
    return parser


def _store(args) -> RuntimeSessionStore:
    return RuntimeSessionStore(
        Path(args.project_root),
        runtime_root=Path(args.runtime_root) if args.runtime_root else None,
    )


def _session(args) -> object:
    store = _store(args)
    if args.session_command == "start":
        return store.start(
            session_id=args.session,
            task_id=args.task,
            harness_id=args.harness,
            phase=args.phase,
            next_step=args.next_step,
            status_summary=args.status_summary,
            branch=args.branch,
            worktree=args.worktree,
            stale_after_seconds=args.stale_after_seconds,
            replace=args.replace,
        )
    if args.session_command == "update":
        if args.phase is None and args.next_step is None and args.status_summary is None:
            raise RuntimeSessionError("update requires at least one changed field")
        return store.update(
            args.session,
            phase=args.phase,
            next_step=args.next_step,
            status_summary=args.status_summary,
        )
    if args.session_command == "wait":
        return store.wait(args.session, args.reason)
    if args.session_command == "end":
        return store.end(args.session, args.reason)
    return store.list()


def _console(args) -> dict:
    coordinator = SnapshotCoordinator(
        Path(args.project_root),
        skill_root=Path(args.skill_root) if args.skill_root else None,
    )
    published = coordinator.refresh()
    return ConsoleBuilder(_store(args)).build(published)


def _human(value: object) -> str:
    if not isinstance(value, dict) or value.get("schema_version") != "adf/project-console/v1":
        if isinstance(value, list):
            return "\n".join(
                f"{item['session_id']}  {item.get('freshness', 'stored')}  {item.get('phase')}  {item.get('task_id')}"
                for item in value
            ) or "没有运行时会话"
        return json.dumps(value, ensure_ascii=False, indent=2)
    lines = [
        f"Project Console  revision={value['revision'][:12]}  state={value['state']}",
        value["ambiguity"]["message"],
    ]
    for key, label in (
        ("human_attention", "需要你处理"),
        ("active_work", "正在进行"),
        ("ready_queue", "可以开始"),
        ("blocked", "阻塞"),
        ("stale_sessions", "状态过期"),
    ):
        lines.append(f"\n{label} ({len(value[key])})")
        lines.extend(
            f"- {item.get('task_id') or item.get('session_id')}: {item['next_step']}"
            for item in value[key]
        )
    lines.append(f"\n{value['disclaimer']}")
    return "\n".join(lines)


def _emit(value: object, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(_human(value))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "session":
            _emit(_session(args), args.format)
            return 0
        if not args.watch:
            _emit(_console(args), args.format)
            return 0
        if args.interval <= 0:
            raise RuntimeSessionError("watch interval must be positive")
        while True:
            _emit(_console(args), args.format)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeSessionError, ValueError) as exc:
        print(f"adf error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
