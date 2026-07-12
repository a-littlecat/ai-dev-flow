import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "ai-dev-flow" / "scripts" / "workflow_lint.py"
FIXTURES = ROOT / "skills" / "ai-dev-flow" / "tests" / "fixtures"


class WorkflowLintTests(unittest.TestCase):
    def run_cli(self, target, fmt):
        return subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), str(target), "--format", fmt], text=True, encoding="utf-8", capture_output=True)

    def test_human_json_equivalence_and_disclaimer(self):
        target = FIXTURES / "violations" / "delivery.md"
        human = self.run_cli(target, "human")
        machine = self.run_cli(target, "json")
        self.assertEqual(human.returncode, 1)
        self.assertEqual(machine.returncode, 1)
        payload = json.loads(machine.stdout)
        self.assertEqual([d["code"] for d in payload["diagnostics"]], ["V_DELIVERY_ORDER", "V_DELIVERY_AUTHORITY"])
        self.assertIn("不代表 Review", human.stdout)
        self.assertIn(payload["disclaimer"], human.stdout)

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(FIXTURES / "valid" / "task-a-document.md", "human").returncode, 0)
        self.assertEqual(self.run_cli(FIXTURES / "violations" / "state-review-ua.md", "human").returncode, 1)
        self.assertEqual(self.run_cli(FIXTURES / "violations" / "parse-duplicate-key.md", "human").returncode, 2)

    def test_invocation_errors_keep_format_and_disclaimer(self):
        human = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--bad"], text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(human.returncode, 2)
        self.assertIn("不代表 Review", human.stdout)
        machine = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--format", "json", "--bad"], text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(machine.returncode, 2)
        payload = json.loads(machine.stdout)
        self.assertEqual(payload["summary"]["exit_code"], 2)
        self.assertIn("不代表 Review", payload["disclaimer"])

    def test_public_facade_and_cli_share_diagnostics_and_provenance(self):
        target = FIXTURES / "violations" / "delivery.md"
        machine = self.run_cli(target, "json")
        payload = json.loads(machine.stdout)
        sys.path.insert(0, str(SCRIPT.parent))
        from workflow_contract import WorkflowContract
        report = WorkflowContract.inspect(target)
        self.assertEqual([d["code"] for d in payload["diagnostics"]], [d.code for d in report.diagnostics])
        human = self.run_cli(target, "human")
        for diagnostic in payload["diagnostics"]:
            for provenance in diagnostic["provenance"]:
                self.assertIn(json.dumps(provenance, ensure_ascii=False, sort_keys=True), human.stdout)


if __name__ == "__main__":
    unittest.main()
