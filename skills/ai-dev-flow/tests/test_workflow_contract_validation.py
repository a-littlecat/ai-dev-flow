import importlib.util
import json
import pathlib
import hashlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "skills" / "ai-dev-flow" / "tests" / "fixtures"
MODULE = ROOT / "skills" / "ai-dev-flow" / "scripts" / "workflow_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("workflow_contract", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkflowContractValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()
        cls.manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))

    def test_validator_oracles(self):
        for item in self.manifest["fixtures"]:
            if item["phase"] != "validator_004" or not pathlib.Path(item["input"]).suffix == ".md":
                continue
            with self.subTest(item=item["id"]):
                report = self.api.WorkflowContract.inspect(FIXTURES / item["input"], fixture_container=True, git_enabled=None)
                self.assertCountEqual([d.code for d in report.diagnostics], item["expected_diagnostics"])

    def test_valid_single_and_project(self):
        single = self.api.WorkflowContract.inspect(FIXTURES / "valid" / "task-a-document.md", fixture_container=True, git_enabled=None)
        self.assertEqual(single.summary.exit_code, 0)
        project = self.api.WorkflowContract.inspect(FIXTURES / "projects" / "valid-project", git_enabled=None)
        self.assertEqual(len(project.contracts), 1)
        self.assertEqual(project.projections, "not_evaluated")
        self.assertFalse(any("BOARD" in d.code for d in project.diagnostics))

    def test_git_transition_and_unavailable_warning(self):
        self.assertIsNone(self.api._transition_code("Draft", "Ready", True))
        self.assertEqual(self.api._transition_code("Ready", "Draft", True), "V_ILLEGAL_TRANSITION")
        self.assertEqual(self.api._transition_code(None, "Review", False), "W_TRANSITION_UNVERIFIABLE")
        report = self.api.WorkflowContract.inspect(FIXTURES / "valid" / "task-a-document.md", fixture_container=True, git_enabled=False)
        self.assertIn("W_TRANSITION_UNVERIFIABLE", [d.code for d in report.diagnostics])
        self.assertEqual(report.summary.exit_code, 0)

    def test_chinese_path_read_only_and_board_not_evaluated(self):
        source = FIXTURES / "valid" / "task-a-document.md"
        before = (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns)
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "中文目录" / "任意容器.md"
            target.parent.mkdir()
            target.write_bytes(source.read_bytes())
            report = self.api.WorkflowContract.inspect(target, fixture_container=True, git_enabled=None)
            self.assertEqual(report.summary.exit_code, 0)
        self.assertEqual(before, (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns))
        board_project = self.api.WorkflowContract.inspect(FIXTURES / "projects" / "board-drift", git_enabled=None)
        self.assertEqual(board_project.projections, "not_evaluated")
        self.assertFalse(any(d.code in {"V_BOARD_DRIFT", "W_BOARD_MISSING", "W_BOARD_ORPHAN", "E_BOARD_PARSE"} for d in board_project.diagnostics))


if __name__ == "__main__":
    unittest.main()
