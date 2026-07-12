import ast
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "skills" / "ai-dev-flow" / "tests" / "fixtures" / "projects"
MODULE = ROOT / "skills" / "ai-dev-flow" / "scripts" / "workflow_contract.py"
CLI = ROOT / "skills" / "ai-dev-flow" / "scripts" / "workflow_lint.py"


def load_api():
    spec = importlib.util.spec_from_file_location("workflow_contract_board", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TaskBoardProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_api()

    def test_board_oracles_and_field_level_provenance(self):
        missing = self.api.WorkflowContract.inspect(FIXTURES / "valid-project")
        self.assertEqual([d.code for d in missing.diagnostics if "BOARD" in d.code], ["W_BOARD_MISSING"])
        drift = self.api.WorkflowContract.inspect(FIXTURES / "board-drift")
        self.assertEqual(set(d.code for d in drift.diagnostics if "BOARD" in d.code), {"V_BOARD_DRIFT", "W_BOARD_ORPHAN"})
        item = next(d for d in drift.diagnostics if d.code == "V_BOARD_DRIFT" and "field=lifecycle" in d.message)
        self.assertIn("field=lifecycle", item.message)
        self.assertIn("expected=Ready", item.message)
        self.assertIn("actual=Review", item.message)
        self.assertGreaterEqual(len(item.provenance), 2)
        bad = self.api.WorkflowContract.inspect(FIXTURES / "bad-board")
        self.assertIn("E_BOARD_PARSE", [d.code for d in bad.diagnostics])

    def test_projection_has_exact_nine_fields_and_is_read_only(self):
        project = FIXTURES / "board-drift"
        tracked = [project / "docs" / "TASK_BOARD.md", project / "docs" / "tasks" / "BOARD-001.md"]
        before = [(hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in tracked]
        report = self.api.WorkflowContract.inspect(project)
        self.assertEqual(len(report.projections), 1)
        self.assertEqual(tuple(name for name, _ in report.projections[0].values), ("task_id", "title", "task_class", "lifecycle", "review_status", "ua_level", "acceptance", "delivery", "task_path"))
        self.assertEqual(before, [(hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in tracked])

    def test_single_task_does_not_read_board(self):
        task = FIXTURES / "board-drift" / "docs" / "tasks" / "BOARD-001.md"
        report = self.api.WorkflowContract.inspect(task)
        self.assertEqual(report.projections, "not_evaluated: single_task_target")
        self.assertFalse(any("BOARD" in d.code for d in report.diagnostics))

    def project_with_board(self, board):
        temporary = tempfile.TemporaryDirectory()
        root = pathlib.Path(temporary.name)
        task_dir = root / "docs" / "tasks"
        task_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "board-drift" / "docs" / "tasks" / "BOARD-001.md", task_dir / "BOARD-001.md")
        (root / "docs" / "TASK_BOARD.md").write_text(board, encoding="utf-8")
        return temporary, root

    def test_consistent_duplicate_and_legacy_partial(self):
        canonical = """# Board\n\n| 任务 | 名称 | 等级 | 状态 | Review | UA | 验收 | 交付 | 任务文件 |\n|---|---|---|---|---|---|---|---|---|\n| BOARD-001 | 看板漂移样例 | B | Ready | Pending | UA3 | Pending / None | commit=Not Recorded;merge=Not Recorded;merge_authority=None | docs/tasks/BOARD-001.md |\n"""
        temporary, root = self.project_with_board(canonical)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        self.assertFalse(any(d.code in {"V_BOARD_DRIFT", "W_BOARD_MISSING", "W_BOARD_ORPHAN", "E_BOARD_PARSE"} for d in report.diagnostics))

        duplicate = canonical + "| BOARD-001 | duplicate | B | Ready | Pending | UA3 | Pending / None | commit=Not Recorded;merge=Not Recorded;merge_authority=None | docs/tasks/BOARD-001.md |\n"
        temporary, root = self.project_with_board(duplicate)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        self.assertIn("E_TASK_ID_CONFLICT", [d.code for d in report.diagnostics])

        legacy = """# Board\n\n| 任务编号 | 任务名称 | 任务等级 | 任务状态 | Review 状态 | UA 等级 | 验收状态 | 路径 | 展示备注 |\n|---|---|---|---|---|---|---|---|---|\n| BOARD-001 | 看板漂移样例 | B | Ready | Pending | UA3 | 待确认 | docs/tasks/BOARD-001.md | ignored |\n"""
        temporary, root = self.project_with_board(legacy)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        self.assertIn("W_LEGACY_INFERRED", [d.code for d in report.diagnostics])
        self.assertNotIn("V_BOARD_DRIFT", [d.code for d in report.diagnostics])

    def test_legacy_combined_split_conflict_is_drift(self):
        legacy = """# Board\n\n| 任务 | 名称 | 等级 | 状态 | 验收 | UA 状态 | 任务文件 |\n|---|---|---|---|---|---|---|\n| BOARD-001 | 看板漂移样例 | B | Ready | Failed / None | 待确认 | docs/tasks/BOARD-001.md |\n"""
        temporary, root = self.project_with_board(legacy)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        self.assertTrue(any(d.code == "V_BOARD_DRIFT" and "field=acceptance" in d.message for d in report.diagnostics))

        authority = legacy.replace("Failed / None", "Pending / User Confirmed")
        temporary, root = self.project_with_board(authority)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        self.assertTrue(any(d.code == "V_BOARD_DRIFT" and "field=acceptance" in d.message for d in report.diagnostics))

        delivery = """# Board\n\n| 任务 | 名称 | 等级 | 状态 | Delivery | Commit 状态 | 任务文件 |\n|---|---|---|---|---|---|---|\n| BOARD-001 | 看板漂移样例 | B | Ready | commit=Not Recorded;merge=Merged;merge_authority=User Authorized | Not Recorded | docs/tasks/BOARD-001.md |\n"""
        temporary, root = self.project_with_board(delivery)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        self.assertTrue(any(d.code == "V_BOARD_DRIFT" and "field=delivery" in d.message for d in report.diagnostics))

    def test_id_path_conflict_has_no_missing_or_orphan_cascade(self):
        board = """# Board\n\n| 任务 | 名称 | 等级 | 状态 | Review | UA | 验收 | 交付 | 任务文件 |\n|---|---|---|---|---|---|---|---|---|\n| WRONG-001 | 看板漂移样例 | B | Ready | Pending | UA3 | Pending / None | commit=Not Recorded;merge=Not Recorded;merge_authority=None | docs/tasks/BOARD-001.md |\n"""
        temporary, root = self.project_with_board(board)
        with temporary:
            report = self.api.WorkflowContract.inspect(root)
        codes = [d.code for d in report.diagnostics if "BOARD" in d.code or d.code == "E_TASK_ID_CONFLICT"]
        self.assertEqual(codes.count("E_TASK_ID_CONFLICT"), 1)
        self.assertNotIn("W_BOARD_MISSING", codes)
        self.assertNotIn("W_BOARD_ORPHAN", codes)
        diagnostic = next(d for d in report.diagnostics if d.code == "E_TASK_ID_CONFLICT")
        self.assertEqual(diagnostic.path, "docs/TASK_BOARD.md")
        self.assertTrue(all(item.path == "docs/TASK_BOARD.md" or item.path.endswith("BOARD-001.md") for item in diagnostic.provenance))

    def test_task_path_bases_and_public_target_boundary(self):
        adapter = self.api.task_board
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            docs = root / "docs"
            docs.mkdir()
            board = docs / "TASK_BOARD.md"
            def parsed(value):
                board.write_text(f"# Board\n\n| 任务 | 名称 | 等级 | 状态 | 任务文件 |\n|---|---|---|---|---|\n| X-1 | X | A | Draft | {value} |\n", encoding="utf-8")
                return adapter.parse_board(board, root)
            self.assertEqual(parsed("skills/X.md").rows[0].get("task_path"), "skills/X.md")
            self.assertEqual(parsed("[X](tasks/X.md)").rows[0].get("task_path"), "docs/tasks/X.md")
            self.assertTrue(parsed("../outside.md").error_message)
            self.assertTrue(parsed("C:\\outside.md").error_message)
            report = self.api.WorkflowContract.inspect(root)
            self.assertEqual([d.code for d in report.diagnostics], ["E_PARSE"])

    def test_human_json_board_diagnostics_are_equivalent(self):
        target = FIXTURES / "board-drift"
        human = subprocess.run([sys.executable, "-B", "-X", "utf8", str(CLI), str(target), "--format", "human"], text=True, encoding="utf-8", capture_output=True)
        machine = subprocess.run([sys.executable, "-B", "-X", "utf8", str(CLI), str(target), "--format", "json"], text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(human.returncode, 1)
        self.assertEqual(machine.returncode, 1)
        payload = json.loads(machine.stdout)
        self.assertEqual(len(payload["projections"]), 1)
        self.assertIn(json.dumps(payload["projections"][0], ensure_ascii=False, sort_keys=True), human.stdout)
        for diagnostic in payload["diagnostics"]:
            if "BOARD" in diagnostic["code"]:
                self.assertIn(diagnostic["code"], human.stdout)
                self.assertIn(diagnostic["message"], human.stdout)

    def test_board_adapter_is_standard_library_and_read_only(self):
        source = (ROOT / "skills" / "ai-dev-flow" / "scripts" / "_task_board.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        self.assertLessEqual(imports, {"dataclasses", "pathlib", "re", "typing"})
        for forbidden in ("write_text(", "write_bytes(", "subprocess", "socket", "requests", "urlopen"):
            self.assertNotIn(forbidden, source)
        cli = CLI.read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--fix"', cli)
        self.assertNotIn('add_argument("--write"', cli)


if __name__ == "__main__":
    unittest.main()
