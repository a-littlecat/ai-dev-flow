from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import replace as dataclass_replace
from pathlib import Path
from types import SimpleNamespace

from be002 import support
from ai_dev_flow_dashboard.core import canonical_bytes, canonical_sha256
from ai_dev_flow_dashboard.core.models import (
    ActionRecommendation,
    CoreResult,
    Diagnostic,
    ParallelAssessment,
    Provenance,
    RelationshipEdge,
    WorktreeSnapshot,
)
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.git_snapshot.collector import GitCollection
from ai_dev_flow_dashboard.snapshot import SnapshotBuildResult, SnapshotBuilder, SnapshotCoordinator


class SequenceCore:
    def __init__(self, values):
        self.values = list(values)
        self.worktree_inputs = []

    def inspect(self, *, worktrees=None):
        self.worktree_inputs.append(dict(worktrees or {}))
        value = self.values.pop(0) if len(self.values) > 1 else self.values[0]
        if isinstance(value, Exception):
            raise value
        return value


class StaticGitCollector:
    def __init__(self, collection):
        self.collection = collection
        self.calls = 0

    def collect(self):
        self.calls += 1
        return self.collection


class CachedDeferredCore:
    def __init__(self, result):
        self.result = result
        self.inspect_calls = 0
        self.complete_calls = 0

    @contextmanager
    def lease_frozen(self):
        yield SimpleNamespace(manifest_sha256=self.result.manifest_sha256)

    def inspect_frozen_deferred(self, frozen):
        self.inspect_calls += 1
        return self.result, {}

    def complete_parallel(self, result, profiles, worktrees):
        self.complete_calls += 1
        return result


class SequenceBuilder:
    changed_task_ids = staticmethod(SnapshotBuilder.changed_task_ids)

    def __init__(self, results):
        self.results = list(results)

    def build(self):
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


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


def core_result(task_node, *, root, edges=(), actions=(), assessments=(), diagnostics=()):
    return CoreResult(
        manifest_sha256=project_source_digest(root),
        tasks=(task_node,),
        edges=tuple(edges),
        actions=tuple(actions),
        parallel_assessments=tuple(assessments),
        diagnostics=tuple(diagnostics),
        projections={},
    )


def git_collection(root: Path, *, dirty_state="clean"):
    worktree = WorktreeSnapshot(
        root=root.as_posix(),
        head="a" * 40,
        branch="refs/heads/codex/test",
        detached=False,
        locked=False,
        prunable=False,
        dirty_state=dirty_state,
        dirty_paths=("docs/tasks/TEST-001.md",) if dirty_state == "dirty" else (),
        diagnostic_ids=(),
    )
    return GitCollection(
        requested_root=root,
        root=root,
        git_dir=root / ".git",
        common_dir=root / ".git",
        head="a" * 40,
        branch="codex/test",
        version="2.50.1",
        state="ok",
        worktrees=(worktree,),
        diagnostics=(),
    )


def project(root: Path):
    task_dir = root / "docs" / "tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "TEST-001.md").write_text(
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
    (root / "docs" / "TASK_BOARD.md").write_text("| task |\n", encoding="utf-8")


class SnapshotBuilderTests(unittest.TestCase):
    def test_identical_frozen_source_and_git_evidence_reuses_validated_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            node = support.task("TEST-001", branch_hint="codex/test")
            core = CachedDeferredCore(core_result(node, root=root))
            collector = StaticGitCollector(git_collection(root))
            builder = SnapshotBuilder(root, core=core, git_collector=collector)

            first = builder.build()
            second = builder.build()

            self.assertEqual("fresh", first.snapshot["state"])
            self.assertEqual(first.snapshot["revision"], second.snapshot["revision"])
            self.assertIsNot(first.snapshot, second.snapshot)
            self.assertIs(first.payload, second.payload)
            self.assertEqual(1, core.inspect_calls)
            self.assertEqual(1, core.complete_calls)
            self.assertEqual(2, collector.calls)
            validate_contract(second.snapshot)
            self.assertEqual(canonical_bytes(second.snapshot), second.payload)
            second.snapshot["state"] = "stale"
            third = builder.build()
            self.assertEqual("fresh", third.snapshot["state"])
            self.assertEqual(canonical_bytes(third.snapshot), third.payload)

    def test_candidate_cache_key_includes_current_schema_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            schema_path = root / "dashboard-contracts-v1.schema.json"
            schema = json.loads(
                (
                    support.CONTRACTS_ROOT
                    / "dashboard-contracts-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            schema["$comment"] = "first"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )
            node = support.task("TEST-001", branch_hint="codex/test")
            core = CachedDeferredCore(core_result(node, root=root))
            builder = SnapshotBuilder(
                root,
                core=core,
                git_collector=StaticGitCollector(git_collection(root)),
                schema_path=schema_path,
            )
            coordinator = SnapshotCoordinator(root, builder=builder)
            self.assertIn(schema_path.resolve(), coordinator.watch_paths)
            first = builder.build()
            schema["$comment"] = "second"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )
            second = builder.build()
            self.assertEqual(2, core.inspect_calls)
            self.assertEqual(2, core.complete_calls)
            self.assertEqual(first.snapshot["revision"], second.snapshot["revision"])
            self.assertEqual(canonical_bytes(second.snapshot), second.payload)

    def test_git_watch_paths_do_not_recursively_watch_object_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            collection = git_collection(root)
            collection = dataclass_replace(
                collection,
                git_dir=root / ".git",
                common_dir=root / ".git",
            )
            watched = collection.watch_paths
            self.assertNotIn((root / ".git").resolve(), watched)
            self.assertIn((root / ".git" / "HEAD").resolve(), watched)
            self.assertIn((root / ".git" / "index").resolve(), watched)
            self.assertNotIn((root / ".git" / "objects").resolve(), watched)
            resolved = dataclass_replace(
                collection,
                worktrees=(
                    dataclass_replace(
                        collection.worktrees[0],
                        dirty_ownership="clean",
                    ),
                ),
            )
            self.assertEqual(
                collection.watch_fingerprint,
                resolved.watch_fingerprint,
            )
            self.assertNotEqual(collection.fingerprint, resolved.fingerprint)

    def test_fresh_candidate_combines_core_git_summary_revision_and_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            node = support.task(
                "TEST-001",
                branch_hint="codex/test",
                provenance=(Provenance("docs/tasks/TEST-001.md", None, "task_id", 1, "TEST-001", "legacy"),),
            )
            core = SequenceCore([core_result(node, root=root)])
            collector = StaticGitCollector(git_collection(root))
            builder = SnapshotBuilder(root, core=core, git_collector=collector)
            result = builder.build()
            self.assertEqual("fresh", result.snapshot["state"])
            self.assertEqual(1, result.snapshot["summary"]["task_total"])
            self.assertEqual("codex/test", result.snapshot["project"]["branch"])
            self.assertNotIn(
                "dirty_ownership",
                result.snapshot["project"]["worktrees"][0],
            )
            self.assertEqual("legacy_inferred", result.snapshot["tasks"][0]["provenance"][0]["source_type"])
            self.assertEqual(64, len(result.snapshot["revision"]))
            validate_contract(result.snapshot)
            self.assertIn("TEST-001", core.worktree_inputs[0])
            self.assertEqual(2, collector.calls)

    def test_same_semantics_has_same_revision_even_when_generated_at_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            node = support.task("TEST-001", branch_hint="codex/test")
            builder = SnapshotBuilder(
                root,
                core=SequenceCore(
                    [core_result(node, root=root), core_result(node, root=root)]
                ),
                git_collector=StaticGitCollector(git_collection(root)),
            )
            first = builder.build().snapshot
            second = builder.build().snapshot
            self.assertEqual(first["revision"], second["revision"])

    def test_first_failure_is_partial_and_later_failure_reuses_last_good_as_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            collection = git_collection(root)
            first_failure = SnapshotBuilder(
                root,
                core=SequenceCore([RuntimeError("secret stack and path")]),
                git_collector=StaticGitCollector(collection),
            ).build().snapshot
            self.assertEqual("partial", first_failure["state"])
            self.assertEqual([], first_failure["tasks"])
            self.assertNotIn("secret", str(first_failure))
            validate_contract(first_failure)

            node = support.task("TEST-001", branch_hint="codex/test")
            builder = SnapshotBuilder(
                root,
                core=SequenceCore(
                    [core_result(node, root=root), RuntimeError("do not leak")]
                ),
                git_collector=StaticGitCollector(collection),
            )
            fresh = builder.build().snapshot
            stale = builder.build().snapshot
            self.assertEqual("fresh", fresh["state"])
            self.assertEqual("stale", stale["state"])
            self.assertEqual("stale", stale["tasks"][0]["freshness"])
            self.assertEqual(1, len(stale["stale_sources"]))
            self.assertNotEqual(fresh["revision"], stale["revision"])
            validate_contract(stale)

    def test_current_failure_digest_changes_stale_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            node = support.task("TEST-001", branch_hint="codex/test")
            builder = SnapshotBuilder(
                root,
                core=SequenceCore(
                    [
                        core_result(node, root=root),
                        RuntimeError("first"),
                        RuntimeError("second"),
                    ]
                ),
                git_collector=StaticGitCollector(git_collection(root)),
            )
            builder.build()
            first_stale = builder.build().snapshot
            task_path = root / "docs" / "tasks" / "TEST-001.md"
            task_path.write_text(task_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            second_stale = builder.build().snapshot
            self.assertNotEqual(first_stale["revision"], second_stale["revision"])

    def test_temporary_files_do_not_enter_source_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            builder = SnapshotBuilder(
                root,
                core=SequenceCore([RuntimeError()]),
                git_collector=StaticGitCollector(git_collection(root)),
            )
            before = builder.source_digest()
            (root / "docs" / "tasks" / ".TEST-001.tmp.md").write_text(
                "temporary",
                encoding="utf-8",
            )
            self.assertEqual(before, builder.source_digest())

    def test_changed_task_ids_include_task_edges_actions_and_pair_assessments(self):
        previous = support.snapshot_with_task()
        changed_task = support.changed_snapshot(previous, lifecycle="In Progress")
        self.assertEqual(
            ("TEST-001",),
            SnapshotBuilder.changed_task_ids(previous, changed_task),
        )

        edge = {
            "edge_id": "1" * 64,
            "type": "parent",
            "source_task_id": "TEST-001",
            "target_task_id": "OTHER-001",
            "condition": None,
            "storage_direction": "child_to_parent",
            "display_direction": "parent_to_child",
            "directional": True,
            "origin": "canonical",
            "provenance": [],
        }
        with_edge = copy.deepcopy(previous)
        with_edge["edges"] = [edge]
        with_edge["revision"] = "2" * 64
        self.assertIn(
            "TEST-001",
            SnapshotBuilder.changed_task_ids(previous, with_edge),
        )


class SnapshotCoordinatorTests(unittest.TestCase):
    def test_coordinator_uses_builder_frozen_schema_identity_and_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            schema_path = root / "dashboard-contracts-v1.schema.json"
            schema = json.loads(
                (
                    support.CONTRACTS_ROOT
                    / "dashboard-contracts-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )
            node = support.task("TEST-001", branch_hint="codex/test")
            core = CachedDeferredCore(core_result(node, root=root))
            builder = SnapshotBuilder(
                root,
                core=core,
                git_collector=StaticGitCollector(git_collection(root)),
                schema_path=schema_path,
            )
            frozen_digest = builder.startup_schema_digest

            schema["$comment"] = "changed between builder and coordinator"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )
            coordinator = SnapshotCoordinator(root, builder=builder)

            self.assertEqual(frozen_digest, coordinator._startup_schema_digest)
            with self.assertRaisesRegex(RuntimeError, "restart required"):
                coordinator.refresh()
            self.assertIsNone(coordinator.current())
            self.assertEqual(0, core.inspect_calls)

            valid = support.snapshot_with_task()
            self.assertEqual(canonical_bytes(valid), builder.validated_payload(valid))

    def test_schema_change_before_first_refresh_aborts_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            schema_path = root / "dashboard-contracts-v1.schema.json"
            schema = json.loads(
                (
                    support.CONTRACTS_ROOT
                    / "dashboard-contracts-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )
            node = support.task("TEST-001", branch_hint="codex/test")
            core = CachedDeferredCore(core_result(node, root=root))
            builder = SnapshotBuilder(
                root,
                core=core,
                git_collector=StaticGitCollector(git_collection(root)),
                schema_path=schema_path,
            )
            coordinator = SnapshotCoordinator(root, builder=builder)

            schema["$comment"] = "changed before first refresh"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "restart required"):
                coordinator.refresh()
            self.assertIsNone(coordinator.current())
            self.assertEqual(0, core.inspect_calls)

    def test_schema_change_during_first_refresh_discards_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project(root)
            schema_path = root / "dashboard-contracts-v1.schema.json"
            schema = json.loads(
                (
                    support.CONTRACTS_ROOT
                    / "dashboard-contracts-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False),
                encoding="utf-8",
            )
            node = support.task("TEST-001", branch_hint="codex/test")
            core = CachedDeferredCore(core_result(node, root=root))
            inner = SnapshotBuilder(
                root,
                core=core,
                git_collector=StaticGitCollector(git_collection(root)),
                schema_path=schema_path,
            )

            class MutatingBuilder:
                changed_task_ids = staticmethod(SnapshotBuilder.changed_task_ids)
                schema_digest = inner.schema_digest
                schema_path = inner.schema_path

                def build(self):
                    result = inner.build()
                    schema["$comment"] = "changed during first refresh"
                    schema_path.write_text(
                        json.dumps(schema, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    return result

            coordinator = SnapshotCoordinator(root, builder=MutatingBuilder())

            with self.assertRaisesRegex(RuntimeError, "restart required"):
                coordinator.refresh()
            self.assertIsNone(coordinator.current())
            self.assertEqual(1, core.inspect_calls)

    def test_schema_change_after_startup_preserves_published_snapshot(self):
        for mutation in ("changed", "invalid", "deleted"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project(root)
                schema_path = root / "dashboard-contracts-v1.schema.json"
                schema = json.loads(
                    (
                        support.CONTRACTS_ROOT
                        / "dashboard-contracts-v1.schema.json"
                    ).read_text(encoding="utf-8")
                )
                schema_path.write_text(
                    json.dumps(schema, ensure_ascii=False),
                    encoding="utf-8",
                )
                node = support.task("TEST-001", branch_hint="codex/test")
                core = CachedDeferredCore(core_result(node, root=root))
                builder = SnapshotBuilder(
                    root,
                    core=core,
                    git_collector=StaticGitCollector(git_collection(root)),
                    schema_path=schema_path,
                )
                coordinator = SnapshotCoordinator(root, builder=builder)
                first = coordinator.refresh()

                if mutation == "changed":
                    schema["$comment"] = "changed after startup"
                    schema_path.write_text(
                        json.dumps(schema, ensure_ascii=False),
                        encoding="utf-8",
                    )
                elif mutation == "invalid":
                    schema_path.write_text("{", encoding="utf-8")
                else:
                    schema_path.unlink()
                (root / "docs" / "TASK_BOARD.md").write_text(
                    "| task |\n| changed |\n",
                    encoding="utf-8",
                )

                second = coordinator.refresh()
                coordinator.refresh_for_watcher()
                schema_path.write_text(
                    json.dumps(schema, ensure_ascii=False),
                    encoding="utf-8",
                )
                restored = coordinator.refresh()
                current = coordinator.current()

                self.assertEqual(first, second)
                self.assertEqual(first, restored)
                self.assertEqual(first, current)
                self.assertEqual(1, core.inspect_calls)
                self.assertEqual(1, core.complete_calls)

    def test_publication_is_atomic_keeps_direct_predecessor_and_skips_same_revision(self):
        first = support.snapshot_with_task()
        second = support.changed_snapshot(first, lifecycle="In Progress")
        root = support.REPO_ROOT
        git = git_collection(root)
        results = [
            SnapshotBuildResult(first, "1" * 64, git, "1" * 64),
            SnapshotBuildResult(second, "2" * 64, git, "2" * 64),
            SnapshotBuildResult(second, "2" * 64, git, "2" * 64),
        ]
        coordinator = SnapshotCoordinator(root, builder=SequenceBuilder(results))
        published_first = coordinator.refresh()
        published_second = coordinator.refresh()
        published_same = coordinator.refresh()
        self.assertEqual(published_first.revision, published_second.previous_revision)
        self.assertEqual(("TEST-001",), published_second.changed_task_ids)
        self.assertIsNot(published_second, published_same)
        self.assertEqual(published_second, published_same)
        event = coordinator.event_payload(published_first.revision)
        self.assertFalse(event["reset_required"])
        self.assertEqual(["TEST-001"], event["changed_task_ids"])
        reset = coordinator.event_payload("f" * 64)
        self.assertTrue(reset["reset_required"])
        self.assertEqual([], reset["changed_task_ids"])

    def test_public_snapshot_mutation_cannot_poison_internal_revision_or_payload(self):
        first = support.snapshot_with_task()
        root = support.REPO_ROOT
        coordinator = SnapshotCoordinator(
            root,
            builder=SequenceBuilder(
                [
                    SnapshotBuildResult(
                        first,
                        "1" * 64,
                        git_collection(root),
                        "1" * 64,
                    )
                ]
            ),
        )
        published = coordinator.refresh()
        published.snapshot["tasks"][0]["lifecycle"] = "Closed"
        published.snapshot["tasks"].append({"task_id": "POISON"})

        current = coordinator.current()
        self.assertEqual("Ready", current.snapshot["tasks"][0]["lifecycle"])
        self.assertEqual(1, len(current.snapshot["tasks"]))
        self.assertEqual(first["revision"], current.revision)
        self.assertEqual(canonical_bytes(current.snapshot), current.payload)

    def test_wait_only_returns_after_revision_changes(self):
        first = support.snapshot_with_task()
        root = support.REPO_ROOT
        coordinator = SnapshotCoordinator(
            root,
            builder=SequenceBuilder(
                [SnapshotBuildResult(first, "1" * 64, git_collection(root), "1" * 64)]
            ),
        )
        coordinator.refresh()
        self.assertIsNone(coordinator.wait_for_revision_change(first["revision"], 0.01))


if __name__ == "__main__":
    unittest.main()
