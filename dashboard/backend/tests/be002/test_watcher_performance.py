from __future__ import annotations

import copy
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from be002 import support
from ai_dev_flow_dashboard.core import canonical_bytes, snapshot_revision, validated_canonical_bytes
from ai_dev_flow_dashboard.core.benchmark import generate_dataset
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.snapshot import PollingWatcher, SnapshotBuilder, SnapshotCoordinator
from ai_dev_flow_dashboard.snapshot.performance import benchmark_summary, nearest_rank


class FakeCoordinator:
    def __init__(self, root: Path):
        self.project_root = root
        self.watch_paths = ()
        self.watcher_state = "starting"
        self.refresh_times = []

    def set_watcher_state(self, state):
        self.watcher_state = state

    def refresh(self):
        self.refresh_times.append(time.monotonic())


def create_watched_project(root: Path):
    task_dir = root / "docs" / "tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "TASK-001.md").write_text("one\n", encoding="utf-8")
    (root / "docs" / "TASK_BOARD.md").write_text("board\n", encoding="utf-8")


class PollingWatcherTests(unittest.TestCase):
    def test_trailing_debounce_coalesces_rapid_saves_and_publishes_within_one_second(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.02,
                debounce_seconds=0.08,
                max_wait_seconds=0.4,
            )
            watcher.start()
            deadline = time.monotonic() + 1
            while coordinator.watcher_state != "ready" and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(watcher.wait_until_idle(1))
            task = root / "docs" / "tasks" / "TASK-001.md"
            first_save = time.monotonic()
            for index in range(3):
                task.write_text(f"save {index}\n", encoding="utf-8")
                time.sleep(0.03)
            deadline = time.monotonic() + 1
            while not coordinator.refresh_times and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(watcher.wait_until_idle(1))
            watcher.stop()
            self.assertEqual("ready", coordinator.watcher_state)
            self.assertEqual(1, len(coordinator.refresh_times))
            self.assertLess(coordinator.refresh_times[0] - first_save, 1.0)

    def test_continuous_changes_hit_max_wait_before_saves_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.02,
                debounce_seconds=0.12,
                max_wait_seconds=0.25,
            )
            watcher.start()
            time.sleep(0.05)
            task = root / "docs" / "tasks" / "TASK-001.md"
            first_save = time.monotonic()
            for index in range(7):
                task.write_text(f"continuous {index}\n", encoding="utf-8")
                time.sleep(0.05)
            deadline = time.monotonic() + 0.5
            while not coordinator.refresh_times and time.monotonic() < deadline:
                time.sleep(0.01)
            watcher.stop()
            self.assertTrue(coordinator.refresh_times)
            self.assertLess(coordinator.refresh_times[0] - first_save, 0.4)

    def test_change_during_refresh_is_not_absorbed_into_new_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)

            class RacingCoordinator(FakeCoordinator):
                def refresh(self):
                    super().refresh()
                    if len(self.refresh_times) == 1:
                        task = self.project_root / "docs" / "tasks" / "TASK-001.md"
                        task.write_text("second event\n", encoding="utf-8")

            coordinator = RacingCoordinator(root)
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.01,
                debounce_seconds=0.04,
                max_wait_seconds=0.15,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            task = root / "docs" / "tasks" / "TASK-001.md"
            task.write_text("first event\n", encoding="utf-8")
            deadline = time.monotonic() + 2
            while len(coordinator.refresh_times) < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(watcher.wait_until_idle(1))
            watcher.stop()
            self.assertEqual(2, len(coordinator.refresh_times))

    def test_linked_worktree_unstaged_clean_dirty_clean_refreshes_revision(self):
        def git(root: Path, *arguments: str):
            return subprocess.run(
                ["git", "-C", str(root), *arguments],
                capture_output=True,
                check=True,
            )

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            linked = base / "linked"
            root.mkdir()
            shutil.copytree(
                support.REPO_ROOT / "skills" / "ai-dev-flow" / "scripts",
                root / "skills" / "ai-dev-flow" / "scripts",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            git(root, "init")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "Test")
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            task = """# TASK-001：watcher

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `TASK-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Ready`
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
- `write_scope`: `file:src/a.py`
- `module_locks`: `watcher`
- `worktree`: `required`
- `branch_hint`: `codex/test-001`
- `risk_flags`: `core_execution_path`

## 目标与边界

- 目标：验证 linked Worktree unstaged 变化。
- 非目标：none
- 允许修改：src/a.py
- 禁止修改：other

## 完成标准与验证

- 完成标准：watcher 刷新。
- 验证命令或检查：自动测试。
"""
            (task_dir / "TASK-001.md").write_text(task, encoding="utf-8")
            (root / "docs" / "TASK_BOARD.md").write_text(
                "# board\n",
                encoding="utf-8",
            )
            source = root / "src" / "a.py"
            source.parent.mkdir()
            original = b"value = 1\n"
            source.write_bytes(original)
            git(root, "add", ".")
            git(root, "commit", "-m", "baseline")
            git(root, "branch", "codex/test-001")
            git(root, "worktree", "add", str(linked), "codex/test-001")

            class RecordingBuilder(SnapshotBuilder):
                def build(self):
                    result = super().build()
                    self.last_result = result
                    return result

            builder = RecordingBuilder(root)
            coordinator = SnapshotCoordinator(root, builder=builder)
            initial = coordinator.refresh()
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.01,
                debounce_seconds=0.04,
                max_wait_seconds=0.2,
                git_probe_interval=0.05,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(2))
            try:
                linked_source = linked / "src" / "a.py"
                linked_original = linked_source.read_bytes()
                linked_source.write_bytes(b"value = 2\n")
                dirty = coordinator.wait_for_revision_change(
                    initial.revision,
                    5,
                )
                self.assertIsNotNone(dirty)
                dirty_event = coordinator.event_payload(
                    initial.revision,
                    current=dirty,
                )
                self.assertEqual(dirty.revision, dirty_event["revision"])
                self.assertFalse(dirty_event["reset_required"])
                dirty_worktree = next(
                    item
                    for item in builder.last_result.git.worktrees
                    if Path(item.root).resolve() == linked.resolve()
                )
                self.assertEqual("dirty", dirty_worktree.dirty_state)
                self.assertEqual(
                    "owned_by_task",
                    dirty_worktree.dirty_ownership,
                    (
                        builder.last_result.snapshot["tasks"],
                        builder.last_result.git.worktrees,
                        builder.last_result.snapshot["diagnostics"],
                    ),
                )

                linked_source.write_bytes(linked_original)
                clean = coordinator.wait_for_revision_change(
                    dirty.revision,
                    5,
                )
                self.assertIsNotNone(
                    clean,
                    (
                        coordinator.health(),
                        builder.last_result.git.worktrees,
                        git(linked, "status", "--porcelain=v1").stdout,
                        watcher.wait_until_idle(0.1),
                    ),
                )
                clean_event = coordinator.event_payload(
                    dirty.revision,
                    current=clean,
                )
                self.assertEqual(clean.revision, clean_event["revision"])
                self.assertFalse(clean_event["reset_required"])
                clean_worktree = next(
                    item
                    for item in builder.last_result.git.worktrees
                    if Path(item.root).resolve() == linked.resolve()
                )
                self.assertEqual("clean", clean_worktree.dirty_state)
                self.assertEqual("clean", clean_worktree.dirty_ownership)
            finally:
                watcher.stop()

    def test_temporary_task_files_are_not_watched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            watcher = PollingWatcher(coordinator)
            before = watcher.capture_manifest()
            (root / "docs" / "tasks" / ".TASK-001.tmp.md").write_text(
                "temp",
                encoding="utf-8",
            )
            self.assertEqual(before, watcher.capture_manifest())

    def test_watcher_failure_is_visible_in_health_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)

            class FailingWatcher(PollingWatcher):
                def capture_manifest(self):
                    raise OSError("unavailable")

            watcher = FailingWatcher(coordinator)
            watcher.start()
            deadline = time.monotonic() + 1
            while coordinator.watcher_state != "failed" and time.monotonic() < deadline:
                time.sleep(0.01)
            watcher.stop()
            self.assertEqual("failed", coordinator.watcher_state)


class PerformanceProtocolTests(unittest.TestCase):
    def test_nearest_rank_and_exact_thirty_sample_protocol(self):
        samples = list(range(1, 31))
        result = benchmark_summary(samples)
        self.assertEqual(15.0, result["p50_ms"])
        self.assertEqual(29.0, result["p95_ms"])
        self.assertEqual(30, len(result["samples_ms"]))
        self.assertEqual(3.0, nearest_rank([1, 2, 3], 0.95))
        with self.assertRaises(ValueError):
            benchmark_summary(samples[:-1])

    def test_all_three_frozen_dataset_sizes_are_runnable_and_deterministic(self):
        for task_count, edge_count in ((50, 200), (500, 2000), (1000, 4000)):
            with self.subTest(task_count=task_count, edge_count=edge_count):
                with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
                    first = generate_dataset(
                        first_dir,
                        task_count=task_count,
                        edge_count=edge_count,
                    )
                    second = generate_dataset(
                        second_dir,
                        task_count=task_count,
                        edge_count=edge_count,
                    )
                    self.assertEqual(first["dataset_sha256"], second["dataset_sha256"])
                    self.assertEqual(task_count, first["task_count"])
                    self.assertEqual(edge_count, first["edge_count"])

    def test_500_task_api_serialization_gate_uses_30_samples(self):
        snapshot = support.snapshot_with_task("BENCH-0001")
        template = snapshot["tasks"][0]
        snapshot["tasks"] = []
        for index in range(1, 501):
            node = copy.deepcopy(template)
            node["task_id"] = f"BENCH-{index:04d}"
            node["title"] = node["task_id"]
            node["source_path"] = f"docs/tasks/{node['task_id']}.md"
            node["branch_hint"] = f"bench/w{((index - 1) % 5) + 1}"
            snapshot["tasks"].append(node)
        snapshot["summary"]["task_total"] = 500
        snapshot["summary"]["counts_by_lifecycle"]["Ready"] = 500
        snapshot["revision"] = snapshot_revision(snapshot)
        validate_contract(snapshot)
        for _ in range(5):
            canonical_bytes(snapshot)
        samples = []
        for _ in range(30):
            started = time.perf_counter_ns()
            payload = validated_canonical_bytes(snapshot)
            samples.append((time.perf_counter_ns() - started) / 1_000_000)
        result = benchmark_summary(samples)
        self.assertLessEqual(result["p95_ms"], 250.0)
        self.assertLessEqual(len(payload), 10 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
