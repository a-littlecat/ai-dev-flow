import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ai-dev-flow"
REFERENCES = SKILL_ROOT / "references"


class CompactWriterRoutingTests(unittest.TestCase):
    def test_compact_template_is_single_source_contract(self):
        text = (REFERENCES / "TASK_TEMPLATE_COMPACT.md").read_text(encoding="utf-8")
        for field in ("schema_version", "task_id", "task_type", "task_class", "lifecycle", "review_status", "ua_level", "ua_status"):
            self.assertEqual(text.count(f"`{field}`"), 1)
        for legacy_heading in ("## 代码审查", "## Diff 审查", "## 合并状态", "## 提交 / 合并"):
            self.assertNotIn(legacy_heading, text)
        for heading in ("## Workflow Contract", "## 目标与边界", "## 完成标准与验证", "## Outcome"):
            self.assertEqual(text.count(heading), 1)
        self.assertNotRegex(text, r"Not Applicable|N/A|不适用")

    def test_routing_matrix_is_present_at_every_writer_entrypoint(self):
        files = (
            SKILL_ROOT / "SKILL.md",
            REFERENCES / "TASK_TEMPLATE.md",
            REFERENCES / "PROMPTS.md",
            REFERENCES / "WORKFLOW.md",
            REFERENCES / "CODE_REVIEW_CHECKLIST.md",
            REFERENCES / "AGENTS_COMPAT.md",
        )
        required = ("A/B", "C/D", "Batch", "Wave", "real_env_signal", "existing legacy", "待确认")
        for path in files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("TASK_TEMPLATE_COMPACT.md", text)
                for token in required:
                    self.assertIn(token, text)

    def test_update_routes_cover_all_modes_without_legacy_revival(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        prompts = (REFERENCES / "PROMPTS.md").read_text(encoding="utf-8")
        combined = skill + prompts
        for mode in ("create_task", "execute_task", "review_task", "repair_task", "close_task"):
            self.assertRegex(combined, rf"{mode}[\s\S]{{0,900}}Compact")
        for operation in ("diff-review", "acceptance"):
            self.assertIn(operation, combined)
        self.assertIn("不得在 Compact TASK 中重建", combined)

    def test_three_comparisons_remain_smaller_and_unambiguous(self):
        metrics = sorted((SKILL_ROOT / "tests" / "fixtures" / "comparisons").glob("*/metrics.json"))
        self.assertEqual(len(metrics), 3)
        import json
        for path in metrics:
            data = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(path=path.parent.name):
                self.assertLess(data["compact_required_inputs"], data["legacy_required_inputs"])
                self.assertEqual(data["compact_duplicate_state_occurrences"], 0)


if __name__ == "__main__":
    unittest.main()
