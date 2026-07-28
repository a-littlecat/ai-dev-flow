from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from be001.support import frozen, scheduling_text
from ai_dev_flow_dashboard.core.models import SCHEDULING_FIELDS
from ai_dev_flow_dashboard.core.scheduling import AXIS_VALUES, SchedulingParser


class SchedulingParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.parser = SchedulingParser(self.root)
        self.known = {"TEST-001", "BASE-001", "OTHER-001"}

    def tearDown(self):
        self.temp.cleanup()

    def parse(self, text: str):
        return self.parser.parse(frozen(text), "TEST-001", self.known)

    def test_all_13_fields_normalize_in_registry_order(self):
        profile = self.parse(scheduling_text())
        self.assertEqual("canonical", profile.state)
        self.assertEqual(SCHEDULING_FIELDS, tuple(key for key, _ in profile.values))
        self.assertEqual(("dashboard", "reader"), profile.get("module_locks"))
        self.assertEqual(
            ("BASE-001#lifecycle=Accepted",),
            profile.get("depends_on"),
        )
        self.assertEqual((), profile.diagnostics)

    def test_arbitrary_input_order_has_same_normalized_values(self):
        lines = scheduling_text().splitlines()
        prefix = lines[:4]
        fields = lines[4:17]
        suffix = lines[17:]
        left = self.parse("\n".join(prefix + fields + suffix))
        right = self.parse("\n".join(prefix + list(reversed(fields)) + suffix))
        self.assertEqual(left.values, right.values)

    def test_structural_errors_invalidate_entire_profile(self):
        cases = {
            "missing": scheduling_text().replace("- `priority`: `high`\n", ""),
            "duplicate": scheduling_text().replace(
                "- `priority`: `high`",
                "- `priority`: `high`\n- `priority`: `low`",
            ),
            "unknown": scheduling_text().replace(
                "- `priority`: `high`",
                "- `priority`: `high`\n- `surprise`: `value`",
            ),
            "bare": scheduling_text().replace(
                "- `priority`: `high`",
                "priority is high",
            ),
            "h3": scheduling_text().replace(
                "- `priority`: `high`",
                "### nested\n- `priority`: `high`",
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                profile = self.parse(text)
                self.assertEqual("invalid", profile.state)
                self.assertEqual((), profile.values)
                self.assertTrue(profile.diagnostics)

    def test_multiple_scheduling_sections_are_invalid(self):
        text = scheduling_text() + "\n## Scheduling\n"
        profile = self.parse(text)
        self.assertEqual("invalid", profile.state)
        self.assertEqual("SCHEDULING_PARSE_ERROR", profile.diagnostics[0].code)

    def test_single_value_error_fails_only_affected_field_closed(self):
        profile = self.parse(scheduling_text(priority="urgent"))
        self.assertEqual("canonical", profile.state)
        self.assertIsNone(profile.get("priority"))
        self.assertEqual("consider", profile.get("parallel_intent"))
        self.assertEqual("SCHEDULING_VALUE_INVALID", profile.diagnostics[0].code)

    def test_unsupported_schema_invalidates_entire_profile(self):
        profile = self.parse(
            scheduling_text(scheduling_schema="ai-dev-flow/scheduling/v2")
        )
        self.assertEqual("invalid", profile.state)
        self.assertEqual(
            "SCHEDULING_SCHEMA_UNSUPPORTED",
            profile.diagnostics[0].code,
        )

    def test_dependency_registry_all_axes_and_sorting(self):
        raw = ";".join(
            f"BASE-001#{axis}={values[0]}"
            for axis, values in reversed(tuple(AXIS_VALUES.items()))
        )
        profile = self.parse(scheduling_text(depends_on=raw))
        self.assertEqual(8, len(profile.dependencies))
        self.assertEqual(
            sorted((item.target_task_id, item.axis, item.expected) for item in profile.dependencies),
            [(item.target_task_id, item.axis, item.expected) for item in profile.dependencies],
        )

    def test_dependency_duplicate_conflict_unknown_axis_and_dangling_fail_closed(self):
        cases = {
            "duplicate": "BASE-001#lifecycle=Ready;BASE-001#lifecycle=Ready",
            "conflict": "BASE-001#lifecycle=Ready;BASE-001#lifecycle=Accepted",
            "axis": "BASE-001#authority=Allowed",
            "expected": "BASE-001#lifecycle=Finished",
            "dangling": "MISSING-001#lifecycle=Accepted",
        }
        for name, raw in cases.items():
            with self.subTest(name=name):
                profile = self.parse(scheduling_text(depends_on=raw))
                self.assertIsNone(profile.get("depends_on"))
                self.assertEqual((), profile.dependencies)
                self.assertTrue(profile.diagnostics)

    def test_list_grammar_rejects_spaces_empty_duplicate_and_none_mixing(self):
        for raw in ("reader; dashboard", "reader;;dashboard", "reader;reader", "none;reader"):
            with self.subTest(raw=raw):
                profile = self.parse(scheduling_text(module_locks=raw))
                self.assertIsNone(profile.get("module_locks"))

    def test_windows_paths_are_segment_aware_nfc_and_casefolded(self):
        profile = self.parse(scheduling_text(write_scope="dir:src/a;dir:src/ab;file:src/É.py"))
        self.assertEqual("canonical", profile.state)
        self.assertEqual(3, len(profile.write_scope))
        unicode_scope = next(item for item in profile.write_scope if item.path.endswith("É.py"))
        self.assertEqual(("src", "é.py"), unicode_scope.comparison_segments)

    def test_windows_paths_reject_unsafe_forms(self):
        bad = (
            r"file:src\a.py",
            "file:C:/src/a.py",
            "file:/src/a.py",
            "file:src/../a.py",
            "file:src/NUL.txt",
            "file:src/trailing.",
            "file:src//a.py",
        )
        for token in bad:
            with self.subTest(token=token):
                profile = self.parse(scheduling_text(write_scope=token))
                self.assertIsNone(profile.get("write_scope"))
                self.assertEqual("SCHEDULING_PATH_INVALID", profile.diagnostics[0].code)

    def test_branch_hint_rejects_command_or_ref_metacharacters(self):
        for branch in ("-danger", "bad branch", "bad..name", "bad.lock", "x~1"):
            with self.subTest(branch=branch):
                profile = self.parse(scheduling_text(branch_hint=branch))
                self.assertIsNone(profile.get("branch_hint"))
                self.assertEqual("SCHEDULING_BRANCH_INVALID", profile.diagnostics[0].code)

    def test_absent_profile_does_not_guess_natural_language(self):
        text = "# TEST-001：test\n\n## 依赖与授权\n\n- 前置依赖：完成 BASE-001 后开始\n"
        profile = self.parse(text)
        self.assertEqual("absent", profile.state)
        self.assertEqual((), profile.dependencies)

    def test_legacy_only_accepts_exact_allowlisted_tokens(self):
        text = (
            "# TEST-001：test\n\n## 依赖与授权\n\n"
            "- 前置依赖：`BASE-001#lifecycle=Accepted`\n\n"
            "## 目标与边界\n\n"
            "- 允许修改：`file:src/a.py`;`dir:src/pkg`\n"
        )
        profile = self.parse(text)
        self.assertEqual("legacy_inferred", profile.state)
        self.assertEqual(1, len(profile.dependencies))
        self.assertEqual(2, len(profile.write_scope))
        self.assertEqual("SCHEDULING_LEGACY_INFERRED", profile.diagnostics[0].code)


if __name__ == "__main__":
    unittest.main()
