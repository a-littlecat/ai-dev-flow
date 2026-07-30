from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from be001.support import REPO_ROOT
from ai_dev_flow_dashboard.core.canonical import canonical_sha256
from ai_dev_flow_dashboard.core.contract_gateway import ContractGateway, ContractGatewayError
from ai_dev_flow_dashboard.core.engine import DashboardCore
from ai_dev_flow_dashboard.core.frozen_input import (
    FrozenInputChangedError,
    FrozenInputError,
    FrozenInputLoader,
)
from ai_dev_flow_dashboard.core.models import CoreContract


class ContractGatewayIntegrationTests(unittest.TestCase):
    def test_gateway_calls_public_project_inspection_and_preserves_report(self):
        loader = FrozenInputLoader()
        gateway = ContractGateway(REPO_ROOT)
        with loader.lease(REPO_ROOT) as frozen:
            public_report = gateway._load_public_module().WorkflowContract.inspect(REPO_ROOT)
            report = gateway.inspect(frozen)
            ids = {item.task_id for item in report.contracts}
            self.assertIn("DASHBOARD-BE-001", ids)
            self.assertTrue(report.projections)
            self.assertIn("exit_code", dict(report.summary))
            contract = next(item for item in report.contracts if item.task_id == "DASHBOARD-BE-001")
            public_contract = next(
                item
                for item in public_report.contracts
                if dict(item.normalized).get("task_id") == "DASHBOARD-BE-001"
            )
            self.assertEqual(dict(public_contract.normalized), dict(contract.normalized))
            self.assertTrue(contract.provenance)
            loader.verify_unchanged(frozen)

    def test_gateway_rejects_unleased_frozen_input(self):
        frozen = FrozenInputLoader().load(REPO_ROOT)
        with self.assertRaises(ContractGatewayError):
            ContractGateway(REPO_ROOT).inspect(frozen)

    def test_gateway_reads_an_external_skill_without_a_project_local_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            (task_dir / "TEST-001.md").write_text(
                "\n".join(
                    (
                        "# TEST-001：external",
                        "",
                        "## Workflow Contract",
                        "",
                        "- `schema_version`: `adf/v0.7.0`",
                        "- `task_id`: `TEST-001`",
                        "- `task_type`: `code`",
                        "- `task_class`: `B`",
                        "- `lifecycle`: `Ready`",
                        "- `review_status`: `Pending`",
                        "- `ua_level`: `UA3`",
                        "- `ua_status`: `Pending`",
                        "- `commit_status`: `Uncommitted`",
                        "- `merge_status`: `Unmerged`",
                        "",
                    )
                ),
                encoding="utf-8",
                newline="\n",
            )
            loader = FrozenInputLoader()
            gateway = ContractGateway(
                root,
                REPO_ROOT / "skills" / "ai-dev-flow",
            )
            with loader.lease(root) as frozen:
                report = gateway.inspect(frozen)
            self.assertEqual(["TEST-001"], [item.task_id for item in report.contracts])
            self.assertFalse((root / "skills").exists())

    def test_gateway_source_does_not_import_private_reader(self):
        source = (
            REPO_ROOT
            / "dashboard"
            / "backend"
            / "src"
            / "ai_dev_flow_dashboard"
            / "core"
            / "contract_gateway.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import _workflow_contract", source)
        self.assertNotIn("from _workflow_contract", source)

    def test_dashboard_core_is_read_only_and_deterministic_on_real_project(self):
        task_paths = sorted((REPO_ROOT / "docs" / "tasks").glob("*.md"))
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in task_paths
        }
        first = DashboardCore(REPO_ROOT).inspect()
        second = DashboardCore(REPO_ROOT).inspect()
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in task_paths
        }
        self.assertEqual(before, after)
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        self.assertEqual(canonical_sha256(first), canonical_sha256(second))
        self.assertIn("DASHBOARD-BE-001", {item.task_id for item in first.tasks})
        be001 = next(item for item in first.tasks if item.task_id == "DASHBOARD-BE-001")
        self.assertEqual("canonical", be001.scheduling_state)
        self.assertEqual(13, len(dict(next(
            DashboardCore(REPO_ROOT).scheduling.parse(
                FrozenInputLoader().load(REPO_ROOT).by_source_path()[be001.source_path],
                be001.task_id,
                {item.task_id for item in first.tasks},
            ).values
            for _ in (0,)
        ))))

    def test_frozen_input_rejects_digest_change_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            path = task_dir / "TEST-001.md"
            path.write_text("# TEST-001：test\n", encoding="utf-8", newline="\n")
            loader = FrozenInputLoader()
            frozen = loader.load(root)
            path.write_text("# TEST-001：changed\n", encoding="utf-8", newline="\n")
            with self.assertRaises(FrozenInputChangedError):
                loader.verify_unchanged(frozen)

    @unittest.skipUnless(os.name == "nt", "Windows CreateFileW lease contract")
    def test_windows_lease_blocks_write_metadata_rename_replace_delete_and_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            board = root / "docs" / "TASK_BOARD.md"
            board.write_text("| task |\n", encoding="utf-8", newline="\n")
            path = task_dir / "TEST-001.md"
            original = "# TEST-001：test\n"
            alternate = "# TEST-001：best\n"
            self.assertEqual(len(original.encode("utf-8")), len(alternate.encode("utf-8")))
            path.write_text(original, encoding="utf-8", newline="\n")
            replacement = task_dir / "replacement.tmp"
            replacement.write_text(alternate, encoding="utf-8", newline="\n")
            renamed = task_dir / "RENAMED-001.md"
            loader = FrozenInputLoader()
            with loader.lease(root) as frozen:
                self.assertTrue(frozen.lease_guard.active)
                self.assertIsNotNone(frozen.board)
                self.assertEqual(original, path.read_text(encoding="utf-8"))
                with self.assertRaises(OSError):
                    path.write_text(alternate, encoding="utf-8", newline="\n")
                try:
                    os.utime(
                        path,
                        ns=(
                            path.stat().st_atime_ns,
                            frozen.tasks[0].mtime_ns - 1_000_000_000,
                        ),
                    )
                except OSError:
                    pass
                else:
                    with self.assertRaises(FrozenInputChangedError):
                        loader.verify_unchanged(frozen)
                    os.utime(
                        path,
                        ns=(path.stat().st_atime_ns, frozen.tasks[0].mtime_ns),
                    )
                with self.assertRaises(OSError):
                    path.rename(renamed)
                with self.assertRaises(OSError):
                    os.replace(replacement, path)
                with self.assertRaises(OSError):
                    path.unlink()
                with self.assertRaises(OSError):
                    board.write_text("| changed |\n", encoding="utf-8", newline="\n")
                loader.verify_unchanged(frozen)
            self.assertFalse(frozen.lease_guard.active)
            path.write_text(alternate, encoding="utf-8", newline="\n")
            self.assertEqual(alternate, path.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.name == "nt", "Windows CreateFileW lease contract")
    def test_windows_lease_rejects_preexisting_write_handle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            path = task_dir / "TEST-001.md"
            original = "# TEST-001：test\n"
            path.write_text(original, encoding="utf-8", newline="\n")
            with path.open("r+b"):
                with self.assertRaises(FrozenInputError):
                    with FrozenInputLoader().lease(root):
                        self.fail("lease must not be acquired")
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.name == "nt", "Windows CreateFileW lease contract")
    def test_windows_lease_detects_new_task_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            (task_dir / "TEST-001.md").write_text(
                "# TEST-001：test\n",
                encoding="utf-8",
                newline="\n",
            )
            added = task_dir / "TEST-002.md"
            loader = FrozenInputLoader()
            with self.assertRaises(FrozenInputChangedError):
                with loader.lease(root):
                    added.write_text(
                        "# TEST-002：added\n",
                        encoding="utf-8",
                        newline="\n",
                    )
            added.unlink()

    def test_non_windows_lease_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            (task_dir / "TEST-001.md").write_text(
                "# TEST-001：test\n",
                encoding="utf-8",
                newline="\n",
            )
            with patch("ai_dev_flow_dashboard.core.frozen_input.os.name", "posix"):
                with self.assertRaises(FrozenInputError):
                    with FrozenInputLoader().lease(root):
                        self.fail("non-Windows lease must fail closed")

    def test_reader_not_recorded_sentinel_maps_to_wire_null(self):
        contract = CoreContract(
            "LEGACY-001",
            "legacy",
            "docs/tasks/LEGACY-001.md",
            (
                ("task_id", "LEGACY-001"),
                ("commit_status", "Not Recorded"),
                ("merge_status", "Not Recorded"),
            ),
            (),
            (),
        )
        node = DashboardCore._nodes((contract,), {}, ())[0]
        self.assertIsNone(node.commit_status)
        self.assertIsNone(node.merge_status)

    def test_invalid_reader_identity_is_omitted_and_invalid_enums_stay_unknown(self):
        invalid_identity = CoreContract(
            "",
            "legacy without canonical identity",
            "docs/tasks/legacy.md",
            (("task_id", None),),
            (),
            (),
        )
        invalid_enums = CoreContract(
            "LEGACY-002",
            "legacy enum values",
            "docs/tasks/LEGACY-002.md",
            (
                ("task_id", "LEGACY-002"),
                ("lifecycle", "Merged"),
                ("ua_status", "Not Started"),
            ),
            (),
            (),
        )
        nodes = DashboardCore._nodes(
            (invalid_identity, invalid_enums),
            {},
            (),
        )
        self.assertEqual(["LEGACY-002"], [node.task_id for node in nodes])
        self.assertIsNone(nodes[0].lifecycle)
        self.assertIsNone(nodes[0].ua_status)


if __name__ == "__main__":
    unittest.main()
