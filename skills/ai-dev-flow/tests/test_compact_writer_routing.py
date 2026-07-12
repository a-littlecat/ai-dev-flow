import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ai-dev-flow"
REFERENCES = SKILL_ROOT / "references"


def markdown_table(text, first_header):
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"| {first_header} |"))
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip().strip("`") for cell in line.strip("|").split("|")])
    return rows


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
            SKILL_ROOT / "README.md",
            SKILL_ROOT / "SKILL.md",
            REFERENCES / "TASK_TEMPLATE.md",
            REFERENCES / "PROMPTS.md",
            REFERENCES / "WORKFLOW.md",
            REFERENCES / "CODE_REVIEW_CHECKLIST.md",
            REFERENCES / "AGENTS_COMPAT.md",
            REFERENCES / "VALIDATION_GUIDE.md",
            REFERENCES / "ACCEPTANCE_GUIDE.md",
        )
        required = ("A/B", "C/D", "Batch", "Wave", "real_env_signal", "existing legacy", "待确认")
        for path in files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("TASK_TEMPLATE_COMPACT.md", text)
                for token in required:
                    self.assertIn(token, text)

    def test_executable_route_matrix_covers_selection_and_writes(self):
        workflow = (REFERENCES / "WORKFLOW.md").read_text(encoding="utf-8")
        selection = dict(markdown_table(workflow, "可执行路由场景"))
        self.assertEqual(selection, {
            "new_ab_none": "TASK_TEMPLATE_COMPACT.md",
            "class_cd": "TASK_TEMPLATE.md",
            "batch": "TASK_TEMPLATE.md",
            "wave": "TASK_TEMPLATE.md",
            "real_env_signal": "TASK_TEMPLATE.md",
            "existing_legacy": "TASK_TEMPLATE.md",
            "unknown": "STOP_PENDING_CONFIRMATION",
        })
        writes = {row[0]: row[1:] for row in markdown_table(workflow, "写回动作")}
        self.assertEqual(set(writes), {"create", "execute", "review", "diff-review", "repair", "acceptance", "close"})
        legacy_headings = ("代码审查", "Diff 审查", "合并状态", "提交 / 合并")
        for operation, (compact_target, full_target) in writes.items():
            with self.subTest(operation=operation):
                self.assertTrue(compact_target)
                self.assertTrue(full_target)
                self.assertFalse(any(heading in compact_target for heading in legacy_headings))

    def test_no_unrouted_prescriptive_writer_entrypoints(self):
        patterns = ("TASK_TEMPLATE.md", "## 验收建议", "写回任务文件", "写入任务文件")
        routed = {
            "README.md", "SKILL.md", "PROMPTS.md", "WORKFLOW.md",
            "TASK_TEMPLATE_COMPACT.md", "CODE_REVIEW_CHECKLIST.md", "AGENTS_COMPAT.md",
            "VALIDATION_GUIDE.md", "ACCEPTANCE_GUIDE.md",
        }
        format_neutral = {"HARNESS_COMPAT.md", "STATUS_MACHINE.md", "TASK_BOARD_TEMPLATE.md"}
        candidates = []
        for path in SKILL_ROOT.rglob("*.md"):
            if "tests" in path.parts or path.name == "CHANGELOG.md":
                continue
            text = path.read_text(encoding="utf-8")
            if any(pattern in text for pattern in patterns):
                candidates.append(path)
        self.assertEqual({path.name for path in candidates}, routed | format_neutral)
        for path in candidates:
            if path.name in format_neutral:
                continue
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.as_posix()):
                self.assertTrue("TASK_TEMPLATE_COMPACT.md" in text or "Compact" in text)

    def test_three_comparisons_remain_smaller_and_unambiguous(self):
        metrics = sorted((SKILL_ROOT / "tests" / "fixtures" / "comparisons").glob("*/metrics.json"))
        self.assertEqual(len(metrics), 3)
        import json
        for path in metrics:
            data = json.loads(path.read_text(encoding="utf-8"))
            ledger = data["ledger"]
            legacy_required = sum(item["legacy_required"] for item in ledger)
            compact_required = sum(item["compact_required"] for item in ledger)
            legacy_duplicates = len(data["duplicate_state_ledger"])
            with self.subTest(path=path.parent.name):
                self.assertEqual(data["legacy_required_inputs"], legacy_required)
                self.assertEqual(data["compact_required_inputs"], compact_required)
                self.assertEqual(data["legacy_duplicate_state_occurrences"], legacy_duplicates)
                self.assertEqual(data["compact_duplicate_state_occurrences"], 0)
                self.assertLess(compact_required, legacy_required)


if __name__ == "__main__":
    unittest.main()
