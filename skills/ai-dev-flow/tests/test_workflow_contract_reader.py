import hashlib
import importlib.util
import ast
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "skills" / "ai-dev-flow" / "tests" / "fixtures"
MODULE_PATH = ROOT / "skills" / "ai-dev-flow" / "scripts" / "_workflow_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("workflow_contract_reader", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkflowContractReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = load_module()
        cls.manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))

    def reader_fixture(self, fixture_id):
        item = next(x for x in self.manifest["fixtures"] if x["id"] == fixture_id)
        return item, FIXTURES / item["input"]

    def test_reader_level_golden_oracles(self):
        ids = ["FIX-VALID-A", "FIX-E-PARSE", "FIX-E-UNKNOWN", "FIX-ID-H1", "FIX-LEGACY-CONFLICT", "FIX-LEGACY-MERGE-CONFLICT"]
        for fixture_id in ids:
            with self.subTest(fixture_id=fixture_id):
                oracle, path = self.reader_fixture(fixture_id)
                report = self.reader.inspect_task(path, validate_filename=False)
                self.assertEqual([d.code for d in report.diagnostics], oracle["expected_diagnostics"])
                for key, value in (oracle["expected_normalized"] or {}).items():
                    self.assertEqual(report.get(key), value)

    def test_valid_defaults_are_in_memory_and_immutable(self):
        _, path = self.reader_fixture("FIX-VALID-A")
        text = path.read_text(encoding="utf-8")
        text = "\n".join(line for line in text.splitlines() if "`commit_status`" not in line and "`merge_status`" not in line)
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "FIX-VALID-A.md"
            target.write_text(text, encoding="utf-8")
            report = self.reader.inspect_task(target)
            self.assertEqual(report.get("merge_status"), "Not Recorded")
            self.assertEqual(report.get("acceptance_authority"), "None")
            self.assertTrue(any(p.source_type == "default" and p.field == "merge_status" for p in report.provenance))
            self.assertTrue(all(p.line == 0 for p in report.provenance if p.source_type == "default"))
            with self.assertRaises((AttributeError, TypeError)):
                report.normalized[0] = ("task_id", "changed")

    def test_reader_level_projection_metadata_and_sections(self):
        _, path = self.reader_fixture("FIX-VALID-A")
        report = self.reader.inspect_task(path, validate_filename=False)
        self.assertEqual(report.title, "合法文档任务")
        self.assertEqual(report.source_path, "task-a-document.md")
        self.assertNotRegex(report.source_path, r"^[A-Za-z]:")
        section = next(item for item in report.sections if item.heading == "目标与边界")
        self.assertEqual(section.fields[0].name, "目标")
        self.assertGreaterEqual(section.fields[0].line, 1)
        with self.assertRaises((AttributeError, TypeError)):
            report.sections[0].fields += ()

    def test_order_bom_repeat_and_read_only(self):
        _, source = self.reader_fixture("FIX-VALID-A")
        before = (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns)
        first = self.reader.inspect_task(source, validate_filename=False)
        second = self.reader.inspect_task(source, validate_filename=False)
        self.assertEqual(first, second)
        self.assertEqual(before, (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns))
        text = source.read_text(encoding="utf-8")
        contract, rest = text.split("\n\n## 目标与边界", 1)
        lines = contract.splitlines()
        prefix, fields = lines[:4], lines[4:]
        with tempfile.TemporaryDirectory() as td:
            reordered = pathlib.Path(td) / "FIX-VALID-A-reordered.md"
            reordered.write_text("\ufeff" + "\n".join(prefix + list(reversed(fields))) + "\n\n## 目标与边界" + rest, encoding="utf-8")
            report = self.reader.inspect_task(reordered)
            self.assertEqual(dict(first.normalized), dict(report.normalized))

    def test_unknown_key_case_schema_and_encoding(self):
        base = (FIXTURES / "valid" / "task-a-document.md").read_text(encoding="utf-8")
        cases = {
            "unknown": base.replace("- `task_id`:", "- `mystery`:\n- `task_id`:", 1),
            "case": base.replace("`task_id`", "`Task_ID`", 1),
            "schema": base.replace("adf/v0.7.0", "adf/v0.7.1", 1),
        }
        with tempfile.TemporaryDirectory() as td:
            for name, text in cases.items():
                path = pathlib.Path(td) / f"FIX-{name}.md"
                path.write_text(text, encoding="utf-8")
                codes = [d.code for d in self.reader.inspect_task(path).diagnostics]
                self.assertIn("E_PARSE" if name != "schema" else "E_UNKNOWN_VALUE", codes)
            bad = pathlib.Path(td) / "bad.md"
            bad.write_bytes(b"\xff\xfe\x00")
            self.assertEqual([d.code for d in self.reader.inspect_task(bad).diagnostics], ["E_PARSE"])

    def test_legacy_single_and_consistent_duplicate(self):
        authority = self.reader.inspect_task(FIXTURES / "legacy" / "authority-inferred.md", validate_filename=False)
        self.assertEqual(authority.get("task_id"), "FIX-LEGACY-AUTHORITY")
        self.assertEqual(authority.get("lifecycle"), "Review")
        self.assertEqual(authority.get("acceptance_authority"), "User Confirmed")
        self.assertEqual(authority.get("merge_authority"), "User Authorized")
        self.assertIn("#用户验收反馈--实机测试反馈", authority.get("ua_evidence"))
        self.assertEqual([d.code for d in authority.diagnostics], ["W_LEGACY_INFERRED"])
        text = """# LEGACY-OK：一致 Review\n\n## 任务元数据\n\n| 字段 | 当前值 |\n|---|---|\n| 任务编号 | `LEGACY-OK` |\n| 任务类型 | 文档 |\n| 任务分级 | A |\n| 任务状态 | 待审查（`Review`） |\n| 用户动作等级 | UA2 |\n\n## 代码审查\n\n- 审查状态：通过\n\n## Diff 审查\n\n- 审查状态：通过\n"""
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "LEGACY-OK.md"
            path.write_text(text, encoding="utf-8")
            report = self.reader.inspect_task(path)
            self.assertEqual(report.get("review_status"), "Passed")
            review_sources = [p for p in report.provenance if p.field == "review_status"]
            self.assertEqual(len(review_sources), 2)
            self.assertEqual([d.code for d in report.diagnostics], ["W_LEGACY_INFERRED"])

    def test_all_reader_fixtures_are_unchanged_and_diagnostics_sorted(self):
        files = sorted(path for path in FIXTURES.rglob("*") if path.is_file())
        before = {path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in files}
        for item in self.manifest["fixtures"]:
            if item["phase"] == "reader_003":
                report = self.reader.inspect_task(FIXTURES / item["input"], validate_filename=False)
                keys = [(d.path, d.line, d.code) for d in report.diagnostics]
                self.assertEqual(keys, sorted(keys))
        after = {path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in files}
        self.assertEqual(before, after)

    def test_production_imports_are_standard_library_and_no_write_surfaces(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        self.assertLessEqual(imports, {"dataclasses", "pathlib", "re", "typing"})
        for forbidden in ("write_text(", "write_bytes(", "subprocess", "socket", "requests", "urlopen"):
            self.assertNotIn(forbidden, source)

    def test_canonical_comment_schema_placement_and_diagnostic_payload(self):
        base = (FIXTURES / "valid" / "task-a-document.md").read_text(encoding="utf-8")
        cases = {
            "comment": base.replace("- `task_id`:", "<!-- forbidden -->\nfree text\n- `task_id`:", 1),
            "outside": base + "\n- `schema_version`: `adf/v0.7.0`\n",
        }
        with tempfile.TemporaryDirectory() as td:
            for name, text in cases.items():
                path = pathlib.Path(td) / f"FIX-VALID-A-{name}.md"
                path.write_text(text, encoding="utf-8")
                report = self.reader.inspect_task(path)
                errors = [d for d in report.diagnostics if d.code == "E_PARSE"]
                self.assertGreaterEqual(len(errors), 1)
                for diagnostic in errors:
                    self.assertEqual(diagnostic.severity, "error")
                    self.assertGreaterEqual(diagnostic.column, 1)
                    self.assertTrue(diagnostic.suggestion)
            comment_report = self.reader.inspect_task(pathlib.Path(td) / "FIX-VALID-A-comment.md")
            self.assertEqual(len([d for d in comment_report.diagnostics if d.code == "E_PARSE"]), 2)

    def test_legacy_scalar_conflicts_and_pending_does_not_grant_authority(self):
        text = """# LEGACY-SCALAR：scalar\n\n## 任务编号\nLEGACY-SCALAR\n## 任务类型\n文档 / 代码\n## 任务分级\nA\n## 任务状态\n待审查（`Ready`）\n## 用户验收反馈 / 实机测试反馈\n- 验收反馈状态：待确认\n"""
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "LEGACY-SCALAR.md"
            path.write_text(text, encoding="utf-8")
            report = self.reader.inspect_task(path)
            self.assertIn("E_LEGACY_CONFLICT", [d.code for d in report.diagnostics])
            self.assertIsNone(report.get("task_type"))
            self.assertIsNone(report.get("lifecycle"))
            self.assertIsNone(report.get("acceptance_authority"))

    def test_filename_conflict_sections_and_provenance_contract(self):
        base = (FIXTURES / "valid" / "task-a-document.md").read_text(encoding="utf-8")
        base = base.replace("- 目标：验证合法 Compact Core。", "- 目标: ignored ASCII field\n- 目标：验证合法 Compact Core。")
        with tempfile.TemporaryDirectory() as td:
            task_dir = pathlib.Path(td) / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            path = task_dir / "OTHER.md"
            path.write_text(base, encoding="utf-8")
            report = self.reader.inspect_task(path)
            self.assertIn("E_TASK_ID_CONFLICT", [d.code for d in report.diagnostics])
            self.assertEqual(report.source_path, "docs/tasks/OTHER.md")
            section = next(s for s in report.sections if s.heading == "目标与边界")
            self.assertNotIn("ignored ASCII field", [f.value for f in section.fields])
        authority = self.reader.inspect_task(FIXTURES / "legacy" / "authority-inferred.md", validate_filename=False)
        self.assertTrue(all(p.source_type in {"canonical", "legacy", "default", "filename", "heading"} for p in authority.provenance))
        evidence = [p for p in authority.provenance if p.field == "ua_evidence"]
        self.assertTrue(any("fixture 静态核对结果" in p.raw_value for p in evidence))
        self.assertTrue(all(p.line >= 1 for p in evidence))

    def test_explicit_legacy_alias_matrix_and_conflict_provenance(self):
        lifecycle = ["草稿", "可执行", "执行中", "阻塞", "待审查", "需修复", "已验收", "已关闭", "延期", "已取消"]
        expected = ["Draft", "Ready", "In Progress", "Blocked", "Review", "Needs Fix", "Accepted", "Closed", "Deferred", "Cancelled"]
        for raw, value in zip(lifecycle, expected):
            self.assertEqual(self.reader._legacy_value("lifecycle", f"{raw}（`{value}`）"), value)
        self.assertEqual(self.reader._legacy_value("lifecycle", "待审查（`Ready`）"), "__CONFLICT__")
        for raw, value in self.reader.TASK_TYPE_COMPOSITE.items():
            self.assertEqual(self.reader._legacy_value("task_type", raw), value)
        for raw, value in self.reader.REVIEW.items():
            self.assertEqual(self.reader._legacy_value("review_status", raw), value)
        for raw, value in self.reader.UA_STATUS.items():
            self.assertEqual(self.reader._legacy_value("ua_status", raw), value)
        conflict = self.reader.inspect_task(FIXTURES / "legacy" / "review-conflict.md", validate_filename=False)
        diagnostic = next(d for d in conflict.diagnostics if d.code == "E_LEGACY_CONFLICT")
        self.assertGreaterEqual(len(diagnostic.provenance), 2)
        self.assertTrue(all(p.source_type == "legacy" for p in diagnostic.provenance))

    def test_legacy_suffix_rules_and_structured_sections(self):
        self.assertEqual(self.reader._legacy_value("review_status", "通过：复审无问题"), "Passed")
        self.assertEqual(self.reader._legacy_value("ua_status", "通过（用户证据已记录"), "Passed")
        self.assertEqual(self.reader._legacy_value("commit_status", "已提交；commit=abc"), "Committed")
        self.assertEqual(self.reader._legacy_value("merge_authority", "待确认：尚未授权"), "None")
        self.assertEqual(self.reader._legacy_value("close_authority", "未知授权"), "__UNKNOWN__")
        self.assertEqual(self.reader._legacy_value("lifecycle", "待审查（Review）垃圾"), "__UNKNOWN__")
        text = """# LEGACY-SECTION：sections\n\n## 任务元数据\n| 字段 | 当前值 |\n|---|---|\n| 任务编号 | LEGACY-SECTION |\n| 任务类型 | 文档 |\n| 任务分级 | A |\n| 任务状态 | 待审查（Review） |\n| 用户动作等级 | UA2 |\n\n## 验证方式\n```powershell\necho ok\n```\n\n## 修改文件\n| 文件 | 说明 |\n|---|---|\n| README.md | 更新 |\n\n## 完成标准\n- [ ] 待执行时填写\n"""
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "LEGACY-SECTION.md"
            path.write_text(text, encoding="utf-8")
            report = self.reader.inspect_task(path)
            verification = next(s for s in report.sections if s.heading == "验证方式")
            self.assertEqual([(f.kind, f.value) for f in verification.fields], [("code_fence", "echo ok")])
            modified = next(s for s in report.sections if s.heading == "修改文件")
            self.assertEqual(len(modified.fields), 1)
            self.assertEqual(modified.fields[0].kind, "table_row")
            criterion = next(s for s in report.sections if s.heading == "完成标准")
            self.assertEqual(criterion.fields[0].kind, "checkbox")

    def test_filename_validation_is_explicit_context_not_path_guessing(self):
        _, fixture = self.reader_fixture("FIX-VALID-A")
        strict = self.reader.inspect_task(fixture)
        relaxed = self.reader.inspect_task(fixture, validate_filename=False)
        self.assertIn("E_TASK_ID_CONFLICT", [d.code for d in strict.diagnostics])
        self.assertNotIn("E_TASK_ID_CONFLICT", [d.code for d in relaxed.diagnostics])


if __name__ == "__main__":
    unittest.main()
