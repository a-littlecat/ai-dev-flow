from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace as dataclass_replace
from pathlib import Path

from be003 import support
from ai_dev_flow_dashboard.core import WorktreeTaskAggregator
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.snapshot import SnapshotBuilder


class WorktreeAggregationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.root = support.make_repo(base / "repo")
        self.builder = SnapshotBuilder(self.root)

    def build(self):
        result = self.builder.build()
        validate_contract(result.snapshot)
        return result.snapshot

    def test_worktree_task_visible_with_source_marking(self):
        linked = support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")
        support.write_task(linked, "WT-001")

        snapshot = self.build()

        task = support.task_by_id(snapshot, "WT-001")
        self.assertIsNotNone(task)
        self.assertEqual(str(linked.resolve()).replace("\\", "/"), task["worktree_root"])
        self.assertEqual("fresh", task["freshness"])
        self.assertEqual("In Progress", task["lifecycle"])
        main = support.task_by_id(snapshot, "MAIN-001")
        self.assertIsNone(main["worktree_root"])
        self.assertEqual(
            [],
            [d for d in snapshot["diagnostics"] if d["code"].startswith("WT_")],
        )

    def test_main_workspace_precedence_wins_silently(self):
        linked = support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")
        support.write_task(linked, "MAIN-001", lifecycle="In Progress")

        snapshot = self.build()

        task = support.task_by_id(snapshot, "MAIN-001")
        self.assertEqual("Ready", task["lifecycle"])
        self.assertIsNone(task["worktree_root"])
        self.assertEqual(
            [],
            [d for d in snapshot["diagnostics"] if d["code"].startswith("WT_")],
        )

    def test_identical_multi_worktree_content_dedupes_to_first_root(self):
        wt_a = support.add_worktree(self.root, Path(self._tmp.name) / "wt-a", "codex/wt-a")
        wt_b = support.add_worktree(self.root, Path(self._tmp.name) / "wt-b", "codex/wt-b")
        support.write_task(wt_a, "WT-SHARED")
        content = (wt_a / "docs" / "tasks" / "WT-SHARED.md").read_bytes()
        (wt_b / "docs" / "tasks").mkdir(parents=True, exist_ok=True)
        (wt_b / "docs" / "tasks" / "WT-SHARED.md").write_bytes(content)

        snapshot = self.build()

        task = support.task_by_id(snapshot, "WT-SHARED")
        self.assertIsNotNone(task)
        first = min(
            (wt_a.resolve().as_posix(), wt_b.resolve().as_posix()),
            key=str.casefold,
        )
        self.assertEqual(first, task["worktree_root"])
        markers = [
            item for item in task["provenance"] if item["field"] == "worktree_source"
        ]
        self.assertEqual(2, len(markers))
        self.assertEqual(
            sorted((wt_a.resolve().as_posix(), wt_b.resolve().as_posix()), key=str.casefold),
            sorted(item["raw_value"] for item in markers),
        )
        self.assertTrue(all(item["source_type"] == "worktree" for item in markers))
        self.assertEqual(
            [],
            support.diagnostics_by_code(snapshot, "WT_TASK_CONFLICT"),
        )

    def test_divergent_multi_worktree_content_publishes_only_conflict(self):
        wt_a = support.add_worktree(self.root, Path(self._tmp.name) / "wt-a", "codex/wt-a")
        wt_b = support.add_worktree(self.root, Path(self._tmp.name) / "wt-b", "codex/wt-b")
        support.write_task(wt_a, "WT-SHARED", lifecycle="In Progress")
        support.write_task(wt_b, "WT-SHARED", lifecycle="Blocked")

        snapshot = self.build()

        self.assertIsNone(support.task_by_id(snapshot, "WT-SHARED"))
        conflicts = support.diagnostics_by_code(snapshot, "WT_TASK_CONFLICT")
        self.assertEqual(1, len(conflicts))
        conflict = conflicts[0]
        self.assertEqual("warning", conflict["severity"])
        self.assertEqual(["WT-SHARED"], conflict["task_ids"])
        roots = [
            item["raw_value"]
            for item in conflict["provenance"]
            if item["field"] == "worktree_root"
        ]
        shas = [
            item["raw_value"]
            for item in conflict["provenance"]
            if item["field"] == "sha256"
        ]
        self.assertEqual(
            sorted((wt_a.resolve().as_posix(), wt_b.resolve().as_posix()), key=str.casefold),
            sorted(roots, key=str.casefold),
        )
        self.assertEqual(2, len(shas))
        self.assertNotEqual(shas[0], shas[1])
        self.assertTrue(
            all(item["source_type"] == "worktree" for item in conflict["provenance"])
        )

    def test_detached_and_locked_worktrees_are_excluded(self):
        detached = support.add_worktree(
            self.root, Path(self._tmp.name) / "detached", "", detach=True
        )
        support.write_task(detached, "WT-DETACHED")
        locked = support.add_worktree(self.root, Path(self._tmp.name) / "locked", "codex/locked")
        support.write_task(locked, "WT-LOCKED")
        support.git(self.root, "worktree", "lock", str(locked))

        snapshot = self.build()

        self.assertIsNone(support.task_by_id(snapshot, "WT-DETACHED"))
        self.assertIsNone(support.task_by_id(snapshot, "WT-LOCKED"))

    def test_selection_does_not_depend_on_worktree_list_order(self):
        wt_a = support.add_worktree(self.root, Path(self._tmp.name) / "wt-a", "codex/wt-a")
        wt_b = support.add_worktree(self.root, Path(self._tmp.name) / "wt-b", "codex/wt-b")
        support.write_task(wt_a, "WT-SHARED")
        content = (wt_a / "docs" / "tasks" / "WT-SHARED.md").read_bytes()
        (wt_b / "docs" / "tasks").mkdir(parents=True, exist_ok=True)
        (wt_b / "docs" / "tasks" / "WT-SHARED.md").write_bytes(content)
        git = self.builder.git_collector.collect()
        aggregator = self.builder.worktree_aggregator
        main_ids = self.builder._main_task_ids()

        forward = aggregator.collect(
            git.worktrees, main_task_ids=main_ids, last_good={}
        )
        reversed_worktrees = tuple(reversed(git.worktrees))
        backward = aggregator.collect(
            reversed_worktrees, main_task_ids=main_ids, last_good={}
        )

        self.assertEqual(forward.digest, backward.digest)
        forward_roots = {
            item.contract.task_id: item.contract.worktree_root
            for item in forward.extra.items
        }
        backward_roots = {
            item.contract.task_id: item.contract.worktree_root
            for item in backward.extra.items
        }
        self.assertEqual(forward_roots, backward_roots)

    def test_unreadable_task_file_produces_warning_diagnostic(self):
        linked = support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")
        task_dir = linked / "docs" / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "WT-BROKEN.md").write_bytes(b"\xff\xfe invalid utf-8")

        snapshot = self.build()

        unreadable = support.diagnostics_by_code(snapshot, "WT_SOURCE_UNREADABLE")
        self.assertEqual(1, len(unreadable))
        self.assertEqual("warning", unreadable[0]["severity"])
        self.assertEqual(
            linked.resolve().as_posix(),
            unreadable[0]["provenance"][0]["raw_value"],
        )

    def test_locked_after_contribution_keeps_last_known_good_stale(self):
        linked = support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")
        support.write_task(linked, "WT-001")
        first = self.build()
        self.assertEqual(
            "fresh", support.task_by_id(first, "WT-001")["freshness"]
        )

        support.git(self.root, "worktree", "lock", str(linked))
        second = self.build()

        task = support.task_by_id(second, "WT-001")
        self.assertIsNotNone(task)
        self.assertEqual("stale", task["freshness"])
        self.assertEqual(linked.resolve().as_posix(), task["worktree_root"])
        lost = support.diagnostics_by_code(second, "WT_SOURCE_LOST")
        self.assertEqual(1, len(lost))
        self.assertEqual("warning", lost[0]["severity"])
        self.assertEqual(["WT-001"], lost[0]["task_ids"])
        self.assertEqual(1, len(second["stale_sources"]))
        self.assertTrue(
            second["stale_sources"][0]["source_path"].startswith(
                linked.resolve().as_posix()
            )
        )

        support.git(self.root, "worktree", "unlock", str(linked))
        third = self.build()
        self.assertEqual(
            "fresh", support.task_by_id(third, "WT-001")["freshness"]
        )
        self.assertEqual([], support.diagnostics_by_code(third, "WT_SOURCE_LOST"))
        self.assertEqual([], third["stale_sources"])

    def test_deleted_task_file_keeps_last_known_good_stale(self):
        linked = support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")
        path = support.write_task(linked, "WT-001")
        first = self.build()
        self.assertIsNotNone(support.task_by_id(first, "WT-001"))

        path.unlink()
        second = self.build()

        task = support.task_by_id(second, "WT-001")
        self.assertIsNotNone(task)
        self.assertEqual("stale", task["freshness"])
        lost = support.diagnostics_by_code(second, "WT_SOURCE_LOST")
        self.assertEqual(1, len(lost))
        self.assertEqual(["WT-001"], lost[0]["task_ids"])

    def test_worktree_task_edit_produces_new_revision(self):
        linked = support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")
        support.write_task(linked, "WT-001", lifecycle="In Progress")
        first = self.build()

        support.write_task(linked, "WT-001", lifecycle="Review")
        second = self.build()

        self.assertNotEqual(first["revision"], second["revision"])
        task = support.task_by_id(second, "WT-001")
        self.assertEqual("Review", task["lifecycle"])
        self.assertEqual("fresh", task["freshness"])

    def test_worktree_without_task_dir_is_not_a_diagnostic(self):
        support.add_worktree(self.root, Path(self._tmp.name) / "linked", "codex/linked")

        snapshot = self.build()

        self.assertEqual(
            [],
            [d for d in snapshot["diagnostics"] if d["code"].startswith("WT_")],
        )


if __name__ == "__main__":
    unittest.main()
