from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "dashboard" / "backend"
SRC_ROOT = BACKEND_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SKILL_ROOT = REPO_ROOT / "skills" / "ai-dev-flow"


TASK_TEMPLATE = """# {task_id}：worktree aggregation

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `{task_id}`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `{lifecycle}`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `close_authority`: `None`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`

## 目标与边界

- 目标：验证跨 Worktree 任务聚合。
- 非目标：none
- 允许修改：src/a.py
- 禁止修改：other

## 完成标准与验证

- 完成标准：聚合可见。
- 验证命令或检查：自动测试。
"""


def git(root: Path, *arguments: str):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        check=True,
    )


def write_task(root: Path, task_id: str, *, lifecycle: str = "In Progress") -> Path:
    task_dir = root / "docs" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    path = task_dir / f"{task_id}.md"
    path.write_text(
        TASK_TEMPLATE.format(task_id=task_id, lifecycle=lifecycle),
        encoding="utf-8",
    )
    return path


def make_repo(base: Path) -> Path:
    """Real Git repository with the public Skill facade and one main TASK."""

    base.mkdir(parents=True)
    shutil.copytree(
        SKILL_ROOT / "scripts",
        base / "skills" / "ai-dev-flow" / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    git(base, "init")
    git(base, "config", "user.email", "test@example.invalid")
    git(base, "config", "user.name", "Test")
    write_task(base, "MAIN-001", lifecycle="Ready")
    (base / "docs" / "TASK_BOARD.md").write_text("# board\n", encoding="utf-8")
    git(base, "add", ".")
    git(base, "commit", "-m", "baseline")
    return base


def add_worktree(repo: Path, target: Path, branch: str, *, detach: bool = False) -> Path:
    if detach:
        git(repo, "worktree", "add", "--detach", str(target))
    else:
        git(repo, "worktree", "add", "-b", branch, str(target))
    return target


def task_by_id(snapshot, task_id: str):
    return next(
        (item for item in snapshot["tasks"] if item["task_id"] == task_id),
        None,
    )


def diagnostics_by_code(snapshot, code: str):
    return [
        item for item in snapshot["diagnostics"] if item["code"] == code
    ]
