from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from be003 import support
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.snapshot import PollingWatcher, SnapshotBuilder, SnapshotCoordinator


class WorktreeWatcherTests(unittest.TestCase):
    """Safe-Worktree TASK edits must invalidate and republish in real time."""

    def test_worktree_task_edit_republishes_within_two_seconds(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = support.make_repo(base / "repo")
            linked = support.add_worktree(root, base / "linked", "codex/linked")
            support.write_task(linked, "WT-001", lifecycle="In Progress")

            builder = SnapshotBuilder(root)
            coordinator = SnapshotCoordinator(root, builder=builder)
            initial = coordinator.refresh()
            validate_contract(initial.snapshot)
            self.assertIsNotNone(
                support.task_by_id(initial.snapshot, "WT-001")
            )
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.01,
                debounce_seconds=0.04,
                max_wait_seconds=0.2,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(5))
            try:
                started = time.monotonic()
                support.write_task(linked, "WT-001", lifecycle="Review")
                updated = coordinator.wait_for_revision_change(initial.revision, 5)
                elapsed = time.monotonic() - started
                self.assertIsNotNone(
                    updated,
                    (
                        coordinator.health(),
                        initial.snapshot["diagnostics"],
                    ),
                )
                self.assertLess(elapsed, 2.0)
                validate_contract(updated.snapshot)
                task = support.task_by_id(updated.snapshot, "WT-001")
                self.assertEqual("Review", task["lifecycle"])
                self.assertEqual("fresh", task["freshness"])
                self.assertEqual(
                    linked.resolve().as_posix(), task["worktree_root"]
                )
                event = coordinator.event_payload(
                    initial.revision,
                    current=updated,
                )
                self.assertEqual(updated.revision, event["revision"])
                self.assertIn("WT-001", event["changed_task_ids"])
                self.assertFalse(event["reset_required"])
            finally:
                watcher.stop()

    def test_worktree_lock_during_runtime_marks_source_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = support.make_repo(base / "repo")
            linked = support.add_worktree(root, base / "linked", "codex/linked")
            support.write_task(linked, "WT-001", lifecycle="In Progress")

            builder = SnapshotBuilder(root)
            coordinator = SnapshotCoordinator(root, builder=builder)
            initial = coordinator.refresh()
            self.assertIsNotNone(
                support.task_by_id(initial.snapshot, "WT-001")
            )
            watcher = PollingWatcher(
                coordinator,
                poll_interval=0.01,
                debounce_seconds=0.04,
                max_wait_seconds=0.2,
            )
            watcher.start()
            self.assertTrue(watcher.wait_until_idle(5))
            try:
                support.git(root, "worktree", "lock", str(linked))
                updated = coordinator.wait_for_revision_change(initial.revision, 5)
                self.assertIsNotNone(updated, coordinator.health())
                validate_contract(updated.snapshot)
                task = support.task_by_id(updated.snapshot, "WT-001")
                self.assertIsNotNone(task)
                self.assertEqual("stale", task["freshness"])
                lost = support.diagnostics_by_code(updated.snapshot, "WT_SOURCE_LOST")
                self.assertEqual(1, len(lost))
                self.assertEqual(["WT-001"], lost[0]["task_ids"])
            finally:
                watcher.stop()


if __name__ == "__main__":
    unittest.main()
