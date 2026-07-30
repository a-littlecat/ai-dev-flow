from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from dashboard.integration.atomic_write import atomic_replace_bytes


TASK = """# STACK-001：integration fixture

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `STACK-001`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `{lifecycle}`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `close_authority`: `None`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `none`
- `replaces`: `none`
- `discovered_from`: `none`
- `parent`: `none`
- `conflicts_with`: `none`
- `parallel_intent`: `consider`
- `write_scope`: `file:fixture/value.txt`
- `module_locks`: `fixture`
- `worktree`: `required`
- `branch_hint`: `codex/stack-001`
- `risk_flags`: `shared_component`

## 目标与边界

- 目标：真实栈集成测试。
- 非目标：生产写入。
- 允许修改：`fixture/value.txt`
- 禁止修改：其他路径。

## 完成标准与验证

- 完成标准：真实 API 和 SSE 可观察 revision 更新。
- 验证命令或检查：integration test。
"""

BOARD = """# fixture board

## 当前任务

| 任务 | 名称 | 等级 | 状态 | 优先级 | 风险 | 前置依赖 | Review | UA | 执行组织 | 任务文件 |
|---|---|---|---|---|---|---|---|---|---|---|
| STACK-001 | integration fixture | C | {lifecycle} | 高 | 中 | 无 | Passed | UA3 Pending | Worktree | [STACK-001](tasks/STACK-001.md) |
"""


def _git(root: Path, *arguments: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Dashboard Integration",
            "GIT_AUTHOR_EMAIL": "integration@example.invalid",
            "GIT_COMMITTER_NAME": "Dashboard Integration",
            "GIT_COMMITTER_EMAIL": "integration@example.invalid",
            "GIT_AUTHOR_DATE": "2026-07-29T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-07-29T00:00:00Z",
        }
    )
    subprocess.run(
        ["git", "-C", str(root), "-c", "core.autocrlf=false", *arguments],
        check=True,
        capture_output=True,
        env=env,
    )


def create_project(root: Path, source_repo: Path) -> Path:
    scripts = source_repo / "skills" / "ai-dev-flow" / "scripts"
    shutil.copytree(scripts, root / "skills" / "ai-dev-flow" / "scripts")
    task_dir = root / "docs" / "tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "STACK-001.md").write_text(
        TASK.format(lifecycle="Ready"),
        encoding="utf-8",
        newline="\n",
    )
    (root / "docs" / "TASK_BOARD.md").write_text(
        BOARD.format(lifecycle="Ready"),
        encoding="utf-8",
        newline="\n",
    )
    (root / ".gitattributes").write_text("* -text\n", encoding="utf-8", newline="\n")
    _git(root, "init", "-b", "main")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "integration fixture")
    return root


def advance_project(root: Path) -> None:
    task = root / "docs" / "tasks" / "STACK-001.md"
    board = root / "docs" / "TASK_BOARD.md"
    atomic_replace_bytes(
        task,
        TASK.format(lifecycle="In Progress").encode("utf-8"),
    )
    atomic_replace_bytes(
        board,
        BOARD.format(lifecycle="In Progress").encode("utf-8"),
    )


def matrix_task(
    task_id: str,
    *,
    depends_on: str = "none",
    parallel_intent: str = "consider",
) -> str:
    text = TASK.format(lifecycle="Ready")
    text = text.replace("STACK-001", task_id)
    text = text.replace("codex/stack-001", f"codex/{task_id.casefold()}")
    text = text.replace("fixture/value.txt", f"fixture/{task_id.casefold()}.txt")
    text = text.replace(
        "- `depends_on`: `none`",
        f"- `depends_on`: `{depends_on}`",
    )
    return text.replace(
        "- `parallel_intent`: `consider`",
        f"- `parallel_intent`: `{parallel_intent}`",
    )


def matrix_board() -> str:
    header, separator = BOARD.splitlines()[4:6]
    return "\n".join(
        (
            "# fixture board",
            "",
            "## 当前任务",
            "",
            header,
            separator,
            "| STACK-001 | integration fixture | C | Ready | 高 | 中 | 无 | Passed | UA3 Pending | Worktree | [STACK-001](tasks/STACK-001.md) |",
            "| STACK-002 | integration fixture | C | Ready | 高 | 中 | 无 | Passed | UA3 Pending | Worktree | [STACK-002](tasks/STACK-002.md) |",
            "",
        )
    )


def create_matrix_project(root: Path, source_repo: Path) -> Path:
    project = create_project(root, source_repo)
    atomic_replace_bytes(
        project / "docs" / "tasks" / "STACK-001.md",
        matrix_task("STACK-001").encode("utf-8"),
    )
    atomic_replace_bytes(
        project / "docs" / "tasks" / "STACK-002.md",
        matrix_task("STACK-002").encode("utf-8"),
    )
    atomic_replace_bytes(
        project / "docs" / "TASK_BOARD.md",
        matrix_board().encode("utf-8"),
    )
    _git(project, "add", ".")
    _git(project, "commit", "-m", "integration matrix fixture")
    return project
