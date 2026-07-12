import importlib.util
import json
import pathlib
import hashlib
import sys
import tempfile
import unittest
from unittest import mock


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
                report = self.api.WorkflowContract.inspect(FIXTURES / item["input"])
                self.assertCountEqual([d.code for d in report.diagnostics], item["expected_diagnostics"])

    def test_valid_single_and_project(self):
        single = self.api.WorkflowContract.inspect(FIXTURES / "valid" / "task-a-document.md")
        self.assertEqual(single.summary.exit_code, 0)
        project = self.api.WorkflowContract.inspect(FIXTURES / "projects" / "valid-project")
        self.assertEqual(len(project.contracts), 1)
        self.assertEqual(project.projections, "not_evaluated")
        self.assertFalse(any("BOARD" in d.code for d in project.diagnostics))

    def test_git_transition_and_unavailable_warning(self):
        self.assertIsNone(self.api._transition_code("Draft", "Ready", True))
        self.assertEqual(self.api._transition_code("Ready", "Draft", True), "V_ILLEGAL_TRANSITION")
        self.assertEqual(self.api._transition_code(None, "Review", False), "W_TRANSITION_UNVERIFIABLE")
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "TASK-UNAVAILABLE.md"
            text = (FIXTURES / "valid" / "task-a-document.md").read_text(encoding="utf-8").replace("FIX-VALID-A", "TASK-UNAVAILABLE")
            target.write_text(text, encoding="utf-8")
            with mock.patch.object(self.api.subprocess, "run", side_effect=FileNotFoundError("git unavailable")):
                report = self.api.WorkflowContract.inspect(target)
        self.assertIn("W_TRANSITION_UNVERIFIABLE", [d.code for d in report.diagnostics])
        self.assertEqual(report.summary.exit_code, 0)

    def test_chinese_path_read_only_and_board_not_evaluated(self):
        source = FIXTURES / "valid" / "task-a-document.md"
        before = (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns)
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "中文目录" / "TASK-ZH.md"
            target.parent.mkdir()
            target.write_text(source.read_text(encoding="utf-8").replace("FIX-VALID-A", "TASK-ZH"), encoding="utf-8")
            report = self.api.WorkflowContract.inspect(target)
            self.assertEqual(report.summary.exit_code, 0)
        self.assertEqual(before, (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns))
        board_project = self.api.WorkflowContract.inspect(FIXTURES / "projects" / "board-drift")
        self.assertEqual(board_project.projections, "not_evaluated")
        self.assertFalse(any(d.code in {"V_BOARD_DRIFT", "W_BOARD_MISSING", "W_BOARD_ORPHAN", "E_BOARD_PARSE"} for d in board_project.diagnostics))

    def canonical(self, *, lifecycle="Review", task_type="code", task_class="C", extra="", outcome=True):
        outcome_text = "" if not outcome else """\n## Outcome\n\n- Base / Diff：base=base123;diff=base123..head456\n- 隔离位置：branch/test\n- 回滚方式：revert commit\n- 修改文件：file.py\n- 验证证据：tests pass\n- Review findings：none\n"""
        return f"""# TASK-CHECK：validator\n\n## Workflow Contract\n\n- `schema_version`: `adf/v0.7.0`\n- `task_id`: `TASK-CHECK`\n- `task_type`: `{task_type}`\n- `task_class`: `{task_class}`\n- `lifecycle`: `{lifecycle}`\n- `review_status`: `Passed`\n- `ua_level`: `UA3`\n- `ua_status`: `Pending`\n- `commit_status`: `Committed`\n{extra}\n## 目标与边界\n\n- 目标：check\n- 非目标：none\n- 允许修改：file.py\n- 禁止修改：other.py\n\n## 完成标准与验证\n\n- 完成标准：passes\n- 验证命令或检查：python test\n{outcome_text}"""

    def codes_for_text(self, text):
        contract = self.api.reader.inspect_text(text, pathlib.Path("TASK-CHECK.md"))
        return [item.code for item in self.api._validate(contract, require_commit=True)]

    def test_complete_core_state_ua_delivery_and_overlay_guards(self):
        self.assertNotIn("V_STATE_GUARD", self.codes_for_text(self.canonical()))
        self.assertIn("V_STATE_GUARD", self.codes_for_text(self.canonical(outcome=False)))
        needs_fix = self.canonical(lifecycle="Needs Fix").replace("- Review findings：none", "- Review findings：none")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(needs_fix))
        ua = self.canonical().replace("- `ua_status`: `Pending`", "- `ua_status`: `Passed`\n- `ua_evidence`: `#ua`\n- `acceptance_authority`: `User Confirmed`")
        self.assertIn("V_UA_GUARD", self.codes_for_text(ua))
        merged = self.canonical(lifecycle="Accepted", extra="- `merge_status`: `Merged`\n- `merge_authority`: `User Authorized`\n").replace("- `ua_status`: `Pending`", "- `ua_status`: `Passed`\n- `ua_evidence`: `#ua`\n- `acceptance_authority`: `User Confirmed`").replace("- 验证证据：tests pass", "- 验证证据：tests pass\n- UA 动作与结果：用户确认")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(merged))
        overlay = self.canonical(lifecycle="In Progress", extra="- `overlays`: `real_env_signal`\n").replace("base=base123;diff=base123..head456", "base=base123")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(overlay))

    def test_real_git_history_legal_dirty_and_illegal(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            task = root / "docs" / "tasks" / "TASK-HIST.md"
            task.parent.mkdir(parents=True)
            subprocess_commands = [
                ["git", "init"], ["git", "config", "user.email", "test@example.invalid"], ["git", "config", "user.name", "Test"]
            ]
            for command in subprocess_commands:
                __import__("subprocess").run(command, cwd=root, check=True, capture_output=True)
            draft = self.canonical(lifecycle="Draft", task_type="document", task_class="A", outcome=False).replace("TASK-CHECK", "TASK-HIST")
            task.write_text(draft, encoding="utf-8")
            __import__("subprocess").run(["git", "add", "docs/tasks/TASK-HIST.md"], cwd=root, check=True)
            __import__("subprocess").run(["git", "commit", "-m", "draft"], cwd=root, check=True, capture_output=True)
            ready = self.canonical(lifecycle="Ready", task_type="document", task_class="A", outcome=False).replace("TASK-CHECK", "TASK-HIST")
            task.write_text(ready, encoding="utf-8")
            __import__("subprocess").run(["git", "commit", "-am", "ready"], cwd=root, check=True, capture_output=True)
            legal = self.api.WorkflowContract.inspect(task)
            self.assertNotIn("V_ILLEGAL_TRANSITION", [d.code for d in legal.diagnostics])
            task.write_text(draft, encoding="utf-8")
            dirty = self.api.WorkflowContract.inspect(task)
            self.assertIn("W_TRANSITION_UNVERIFIABLE", [d.code for d in dirty.diagnostics])
            __import__("subprocess").run(["git", "commit", "-am", "illegal"], cwd=root, check=True, capture_output=True)
            illegal = self.api.WorkflowContract.inspect(task)
            self.assertIn("V_ILLEGAL_TRANSITION", [d.code for d in illegal.diagnostics])


if __name__ == "__main__":
    unittest.main()
