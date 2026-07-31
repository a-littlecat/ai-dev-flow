from __future__ import annotations

import copy
import hashlib
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from be002 import support
from ai_dev_flow_dashboard.core import (
    canonical_bytes,
    canonical_sha256,
    snapshot_revision,
    validated_canonical_bytes,
)
from ai_dev_flow_dashboard.core.benchmark import generate_dataset
from ai_dev_flow_dashboard.core.models import CoreResult
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.snapshot import PollingWatcher, SnapshotBuilder, SnapshotCoordinator
from ai_dev_flow_dashboard.snapshot.events import PollingManifestEventSource
from ai_dev_flow_dashboard.snapshot.performance import benchmark_summary, nearest_rank


class FakeCoordinator:
    def __init__(self, root: Path):
        self.project_root = root
        self.watch_paths = ()
        self.watch_roots = (root,)
        self.watcher_state = "starting"
        self.refresh_times = []

    def set_watcher_state(self, state):
        self.watcher_state = state

    def refresh(self):
        self.refresh_times.append(time.monotonic())


class FakeEventSource:
    def __init__(self):
        self.callback = None
        self.paths = ()
        self.stopped = False
        self.failure = None
        self.started = False

    def start(self, paths, callback):
        self.paths = tuple(paths)
        self.callback = callback
        self.started = True

    def update(self, paths):
        self.paths = tuple(paths)

    def emit(self):
        if self.callback is None:
            raise AssertionError("event source has not started")
        self.callback()

    def stop(self):
        self.stopped = True


def create_watched_project(root: Path):
    task_dir = root / "docs" / "tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "TASK-001.md").write_text("one\n", encoding="utf-8")
    (root / "docs" / "TASK_BOARD.md").write_text("board\n", encoding="utf-8")


def project_source_digest(root: Path) -> str:
    paths = sorted(
        (*((root / "docs" / "tasks").glob("*.md")), root / "docs" / "TASK_BOARD.md"),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    return canonical_sha256(
        tuple(
            (
                path.relative_to(root).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
                path.stat().st_size,
            )
            for path in paths
        )
    )


class PollingWatcherTests(unittest.TestCase):
    def test_client_connection_does_not_trigger_redundant_refresh_or_periodic_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            events = FakeEventSource()
            watcher = PollingWatcher(
                coordinator,
                event_source=events,
                pause_without_clients=True,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            self.assertEqual(1, len(coordinator.refresh_times))
            coordinator.refresh_times.clear()
            time.sleep(0.15)
            self.assertEqual([], coordinator.refresh_times)

            watcher.client_connected()
            time.sleep(0.15)
            self.assertEqual([], coordinator.refresh_times)

            watcher.client_disconnected()
            time.sleep(0.15)
            watcher.stop()
            self.assertEqual([], coordinator.refresh_times)
            self.assertTrue(events.stopped)

    def test_file_event_refreshes_without_client_but_idle_has_no_integrity_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            events = FakeEventSource()
            watcher = PollingWatcher(
                coordinator,
                event_source=events,
                pause_without_clients=True,
                poll_interval=0.01,
                debounce_seconds=0.02,
                max_wait_seconds=0.1,
                integrity_interval=10,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            coordinator.refresh_times.clear()
            events.emit()
            deadline = time.monotonic() + 1
            while len(coordinator.refresh_times) < 1 and time.monotonic() < deadline:
                time.sleep(0.01)
            time.sleep(0.15)
            watcher.stop()
            self.assertEqual(1, len(coordinator.refresh_times))

    def test_explicit_integrity_interval_is_measured_after_slow_refresh_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)

            class SlowCoordinator(FakeCoordinator):
                def refresh(self):
                    self.refresh_times.append(time.monotonic())
                    time.sleep(0.08)

            coordinator = SlowCoordinator(root)
            watcher = PollingWatcher(
                coordinator,
                event_source=FakeEventSource(),
                integrity_interval=0.05,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            time.sleep(0.32)
            watcher.stop()
            self.assertGreaterEqual(len(coordinator.refresh_times), 2)
            gaps = [
                right - left
                for left, right in zip(
                    coordinator.refresh_times,
                    coordinator.refresh_times[1:],
                )
            ]
            self.assertTrue(all(gap >= 0.12 for gap in gaps), gaps)

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
            coordinator.refresh_times.clear()
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
            coordinator.refresh_times.clear()
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
                race_enabled = False

                def refresh(self):
                    super().refresh()
                    if self.race_enabled and len(self.refresh_times) == 1:
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
            coordinator.refresh_times.clear()
            coordinator.race_enabled = True
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

    def test_manifest_fallback_detects_ordinary_worktree_file_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            ordinary = root / "src" / "value.txt"
            ordinary.parent.mkdir()
            ordinary.write_text("one\n", encoding="utf-8")
            coordinator = FakeCoordinator(root)
            watcher = None
            fallback = PollingManifestEventSource(
                lambda: watcher.capture_manifest(),
                interval=0.02,
            )
            watcher = PollingWatcher(
                coordinator,
                event_source=fallback,
                poll_interval=0.01,
                debounce_seconds=0.02,
                max_wait_seconds=0.1,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            coordinator.refresh_times.clear()
            ordinary.write_text("two\n", encoding="utf-8")
            deadline = time.monotonic() + 2
            while not coordinator.refresh_times and time.monotonic() < deadline:
                time.sleep(0.01)
            watcher.stop()
            self.assertEqual(1, len(coordinator.refresh_times))

    def test_manifest_fallback_detects_tracked_dotfile_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            dotfile = root / ".gitattributes"
            dotfile.write_text("* text=auto\n", encoding="utf-8")
            coordinator = FakeCoordinator(root)
            watcher = None
            fallback = PollingManifestEventSource(
                lambda: watcher.capture_manifest(),
                interval=0.02,
            )
            watcher = PollingWatcher(
                coordinator,
                event_source=fallback,
                poll_interval=0.01,
                debounce_seconds=0.02,
                max_wait_seconds=0.1,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            coordinator.refresh_times.clear()
            dotfile.write_text("* text=auto eol=lf\n", encoding="utf-8")
            deadline = time.monotonic() + 2
            while not coordinator.refresh_times and time.monotonic() < deadline:
                time.sleep(0.01)
            watcher.stop()
            self.assertEqual(1, len(coordinator.refresh_times))

    def test_runtime_native_failure_switches_to_manifest_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            native = FakeEventSource()
            with mock.patch(
                "ai_dev_flow_dashboard.snapshot.watcher.default_event_source",
                return_value=native,
            ):
                watcher = PollingWatcher(
                    coordinator,
                    fallback_interval=0.02,
                    poll_interval=0.01,
                    debounce_seconds=0.02,
                    max_wait_seconds=0.1,
                )
                watcher.start()
                self.assertTrue(watcher.wait_until_idle(1))
                coordinator.refresh_times.clear()
                native.failure = OSError("native read failed")
                native.emit()
                deadline = time.monotonic() + 2
                while not coordinator.refresh_times and time.monotonic() < deadline:
                    time.sleep(0.01)
                watcher.stop()
            self.assertTrue(native.stopped)
            self.assertEqual("ready", coordinator.watcher_state)
            self.assertEqual(1, len(coordinator.refresh_times))

    def test_new_watch_roots_are_armed_before_follow_up_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linked = root.parent / f"{root.name}-linked"
            linked.mkdir()
            self.addCleanup(shutil.rmtree, linked, True)
            create_watched_project(root)
            events = FakeEventSource()

            class GrowingCoordinator(FakeCoordinator):
                def refresh(self):
                    super().refresh()
                    if len(self.refresh_times) == 1:
                        self.watch_roots = (self.project_root, linked)

            coordinator = GrowingCoordinator(root)
            watcher = PollingWatcher(coordinator, event_source=events)
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            watcher.stop()
            self.assertEqual(2, len(coordinator.refresh_times))
            self.assertIn(
                linked.resolve(),
                {request.directory for request in events.paths},
            )

    def test_existing_new_top_level_directory_is_armed_before_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            coordinator = FakeCoordinator(root)
            events = FakeEventSource()
            watcher = PollingWatcher(
                coordinator,
                event_source=events,
                poll_interval=0.01,
                debounce_seconds=0.02,
                max_wait_seconds=0.1,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(1))
            created = root / "created"
            created.mkdir()
            coordinator.refresh_times.clear()
            events.emit()
            deadline = time.monotonic() + 1
            while not coordinator.refresh_times and time.monotonic() < deadline:
                time.sleep(0.01)
            watcher.stop()
            by_path = {
                request.directory: request.recursive
                for request in events.paths
            }
            self.assertTrue(by_path[created.resolve()])

    def test_event_requests_keep_precise_external_git_paths_and_exclude_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "worktree"
            external_git = Path(directory) / "metadata"
            create_watched_project(root)
            (root / ".git" / "objects").mkdir(parents=True)
            (external_git / "refs" / "heads").mkdir(parents=True)
            (external_git / "worktrees").mkdir()
            (external_git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (external_git / "index").write_bytes(b"index")
            coordinator = FakeCoordinator(root)
            coordinator.watch_excluded_roots = (root / ".git",)
            coordinator.watch_paths = (
                external_git / "HEAD",
                external_git / "index",
                external_git / "refs" / "heads",
                external_git / "worktrees",
            )
            requests = PollingWatcher(coordinator)._event_requests()
            by_path = {
                request.directory: request.recursive
                for request in requests
            }
            self.assertFalse(by_path[root.resolve()])
            self.assertNotIn((root / ".git").resolve(), by_path)
            self.assertFalse(by_path[external_git.resolve()])
            self.assertTrue(by_path[(external_git / "refs" / "heads").resolve()])
            self.assertTrue(by_path[(external_git / "worktrees").resolve()])

    def test_manifest_prunes_git_object_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            git_object = root / ".git" / "objects" / "aa" / "object"
            git_object.parent.mkdir(parents=True)
            git_object.write_bytes(b"one")
            watcher = PollingWatcher(FakeCoordinator(root))
            before = watcher.capture_manifest()
            self.assertNotIn(str(git_object.absolute()), {item[0] for item in before})
            git_object.write_bytes(b"two")
            self.assertEqual(before, watcher.capture_manifest())

    def test_manifest_prunes_internal_custom_git_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_watched_project(root)
            metadata = root / "metadata"
            git_object = metadata / "objects" / "aa" / "object"
            git_object.parent.mkdir(parents=True)
            git_object.write_bytes(b"one")
            coordinator = FakeCoordinator(root)
            coordinator.watch_excluded_roots = (metadata,)
            coordinator.watch_paths = (
                metadata / "HEAD",
                metadata / "index",
            )
            (metadata / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (metadata / "index").write_bytes(b"index")
            watcher = PollingWatcher(coordinator)
            manifest = watcher.capture_manifest()
            manifest_paths = {item[0] for item in manifest}
            self.assertIn(str((metadata / "HEAD").absolute()), manifest_paths)
            self.assertIn(str((metadata / "index").absolute()), manifest_paths)
            self.assertNotIn(str(git_object.absolute()), manifest_paths)
            requests = watcher._event_requests()
            by_path = {
                request.directory: request.recursive
                for request in requests
            }
            self.assertFalse(by_path[metadata.resolve()])
            self.assertFalse(by_path[root.resolve()])

    def test_real_coordinator_prunes_internal_separate_git_directory(self):
        if shutil.which("git") is None:
            self.skipTest("git is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            metadata = root / "custom-git-metadata"
            create_watched_project(root)
            (root / "docs" / "tasks" / "TASK-001.md").write_text(
                "\n".join(
                    (
                        "# TEST-001：test",
                        "",
                        "## Workflow Contract",
                        "",
                        "- `task_id`: `TEST-001`",
                        "",
                        "## Scheduling",
                        "",
                        "- `branch_hint`: `codex/test`",
                        "",
                    )
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "git",
                    "init",
                    f"--separate-git-dir={metadata}",
                    str(root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Dashboard Test"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "add", "docs"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "fixture"],
                check=True,
                capture_output=True,
                text=True,
            )
            linked_worktree = Path(directory) / "linked-worktree"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "worktree",
                    "add",
                    "--detach",
                    str(linked_worktree),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            class StaticCore:
                def inspect(self, *, worktrees=None):
                    del worktrees
                    return CoreResult(
                        manifest_sha256=project_source_digest(root),
                        tasks=(support.task("TEST-001", branch_hint="codex/test"),),
                        edges=(),
                        actions=(),
                        parallel_assessments=(),
                        diagnostics=(),
                        projections={},
                    )

            builder = SnapshotBuilder(root, core=StaticCore())
            coordinator = SnapshotCoordinator(root, builder=builder)
            coordinator.refresh()
            watcher = PollingWatcher(coordinator)

            self.assertIn(metadata.resolve(), coordinator.watch_excluded_roots)
            self.assertNotIn(metadata.resolve(), coordinator.watch_roots)
            self.assertIn(linked_worktree.resolve(), coordinator.watch_roots)
            self.assertIn((metadata / "HEAD").resolve(), coordinator.watch_paths)
            self.assertIn((metadata / "index").resolve(), coordinator.watch_paths)
            refs_heads = (metadata / "refs" / "heads").resolve()
            self.assertIn(refs_heads, coordinator.watch_paths)

            git_object = metadata / "objects" / "aa" / "object"
            git_object.parent.mkdir(parents=True, exist_ok=True)
            git_object.write_bytes(b"one")
            manifest_paths = {item[0] for item in watcher.capture_manifest()}
            self.assertNotIn(str(git_object.absolute()), manifest_paths)
            self.assertIn(str((metadata / "HEAD").absolute()), manifest_paths)
            self.assertIn(str((metadata / "index").absolute()), manifest_paths)

            by_path = {
                request.directory: request.recursive
                for request in watcher._event_requests()
            }
            self.assertFalse(by_path[metadata.resolve()])
            self.assertTrue(by_path[refs_heads])
            self.assertFalse(by_path[linked_worktree.resolve()])
            self.assertTrue(by_path[(linked_worktree / "docs").resolve()])
            self.assertFalse(by_path[root.resolve()])

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

            class FailingEventSource(FakeEventSource):
                def start(self, paths, callback):
                    del paths, callback
                    raise OSError("unavailable")

            watcher = PollingWatcher(
                coordinator,
                event_source=FailingEventSource(),
            )
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
