import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ai-dev-flow"
REFERENCES = SKILL_ROOT / "references"
PROTOTYPE = SKILL_ROOT / "prototypes" / "v0.8-lite"


def read(path):
    return path.read_text(encoding="utf-8")


def policy_from(path):
    text = read(path)
    match = re.search(
        r"<!-- POLICY_JSON_BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- POLICY_JSON_END -->",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise AssertionError(f"POLICY_JSON block missing: {path}")
    return json.loads(match.group(1))


class V08SlimRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.skill = read(SKILL_ROOT / "SKILL.md")
        self.core = read(REFERENCES / "CORE.md")
        self.policy = policy_from(REFERENCES / "CORE.md")

    def test_version_and_contract_identity_are_independent(self):
        self.assertEqual(read(SKILL_ROOT / "VERSION").strip(), "0.8.2")
        for path in (
            ROOT / "README.md",
            ROOT / "README.en.md",
            SKILL_ROOT / "README.md",
            REFERENCES / "TASK_TEMPLATE.md",
            REFERENCES / "V0.8_MIGRATION.md",
        ):
            with self.subTest(path=path.name):
                text = read(path)
                self.assertIn("0.8.2", text)
                self.assertIn("adf/v0.7.0", text)
        self.assertNotIn("adf/v0.8.0", read(REFERENCES / "TASK_TEMPLATE.md"))

    def test_public_lint_examples_use_supported_arguments(self):
        for path in (ROOT / "README.md", ROOT / "README.en.md", SKILL_ROOT / "README.md"):
            text = read(path)
            with self.subTest(path=path.name):
                self.assertNotIn("--check-board", text)
                self.assertIn("workflow_lint.py . --format human", text)

    def test_route_review_and_safety_still_match_the_frozen_prototype(self):
        frozen = policy_from(PROTOTYPE / "references" / "CORE.md")
        for section in ("routes", "review", "safety"):
            with self.subTest(section=section):
                self.assertEqual(self.policy[section], frozen[section])
        self.assertNotEqual(self.policy["repair"], frozen["repair"])

    def test_default_runtime_is_two_files_and_within_budget(self):
        self.assertIn("SKILL.md", read(SKILL_ROOT / "README.md"))
        self.assertIn("CORE.md", self.skill)
        self.assertIn("默认运行时工作流输入只有本文件与 `CORE.md`", self.skill)
        self.assertIn("不要默认加载 `PROMPTS.md`", self.skill)

        total_lines = sum(
            len(read(path).splitlines())
            for path in (SKILL_ROOT / "SKILL.md", REFERENCES / "CORE.md")
        )
        self.assertLessEqual(total_lines, 400)

    def test_lite_formally_exits_the_skill(self):
        for text in (self.skill, self.core, read(SKILL_ROOT / "README.md")):
            self.assertIn("DoNotUseSkill", text)
        lite_section = self.skill.split("## Lite：退出 Skill", 1)[1].split("## Tracked", 1)[0]
        for rule in ("不创建 TASK", "不调用 Reviewer", "不进入 repair loop"):
            self.assertIn(rule, lite_section)

    def test_route_and_review_policy_cover_required_gates(self):
        routes = self.policy["routes"]
        controlled = routes["controlled"]
        self.assertEqual(routes["fallback"], "Tracked")
        self.assertEqual(controlled["task_classes"], ["D"])
        self.assertEqual(controlled["ua_min"], 5)
        for risk in (
            "architecture", "data_migration", "security", "real_environment",
            "release", "irreversible_action", "delivery",
        ):
            self.assertIn(risk, controlled["risk_flags"])

        tracked_flags = self.policy["review"]["Tracked"]["trigger_risk_flags"]
        for risk in (
            "public_api", "shared_component", "build_or_deploy_config",
            "core_execution_path", "tests_do_not_cover_oracle",
        ):
            self.assertIn(risk, tracked_flags)

        controlled_review = self.policy["review"]["Controlled"]
        self.assertTrue(controlled_review["required"])
        self.assertEqual(
            controlled_review["enforcement_points"],
            ["acceptance_recommendation", "delivery", "merge", "release"],
        )
        self.assertEqual(self.policy["review"]["missing_authority_or_capability"], "Blocked")

    def test_repair_policy_has_autonomous_and_user_authorized_boundaries(self):
        repair = self.policy["repair"]
        self.assertEqual(repair["repair_round_definition"], "patch_to_next_independent_review")
        self.assertEqual(repair["base_auto_rounds"], 2)
        self.assertEqual(repair["autonomous_max_rounds"], 3)
        self.assertEqual(repair["history"]["attempt_count_source"], "validated_receipt_chain")
        self.assertEqual(repair["round_3_progress"]["source"], "latest_independent_review_receipt")
        self.assertTrue(repair["round_3_progress"]["require_red_to_green"])
        self.assertTrue(repair["round_3_progress"]["evidence_coverage_must_strictly_increase"])
        self.assertFalse(repair["task_change_resets_budget"])
        self.assertFalse(repair["model_change_resets_budget"])
        self.assertEqual(repair["required_false_fields"], ["external_side_effect"])
        self.assertTrue(repair["post_stop"]["ai_repair_allowed_with_explicit_authority"])
        self.assertFalse(repair["post_stop"]["manual_implementation_required"])
        self.assertEqual(repair["post_stop"]["default_authorized_attempts"], 1)
        self.assertEqual(repair["record_only_finding"]["default_severity"], ["P2", "P3"])
        self.assertIn("authorized_attempt_ids", repair["post_stop"]["authority_must_bind"])
        self.assertEqual(repair["mechanical_decisions"], ["MechanicallyEligible", "Stop", "Blocked"])
        self.assertTrue(repair["promotion_requires_trusted_orchestrator"])

    def test_repair_implementation_plan_keeps_mechanical_and_final_authority_separate(self):
        plan = read(
            ROOT
            / "docs"
            / "plans"
            / "REPAIR-ESCALATION-001-user-authorized-repair.md"
        )
        self.assertIn("只机械判定 `MechanicallyEligible / Stop / Blocked`", plan)
        self.assertIn("只能由持有真实对话、harness 或只读项目证据的 Orchestrator 提升", plan)
        self.assertNotIn(
            "机械判定 `AutoRepairAllowed / ExtendRound3 / Stop / EscalatedRepairAllowed / Blocked`",
            plan,
        )

    def test_new_task_and_migration_contracts_are_small_and_compatible(self):
        template = read(REFERENCES / "TASK_TEMPLATE.md")
        compact = read(REFERENCES / "TASK_TEMPLATE_COMPACT.md")
        migration = read(REFERENCES / "V0.8_MIGRATION.md")

        self.assertIn("Tracked / Controlled", template)
        self.assertIn("Lite", template)
        self.assertIn("不创建 TASK", template)
        self.assertIn("v0.7 Writer/Reader", compact)
        self.assertIn("旧任务无需迁移", compact)
        self.assertIn("不需要一次性迁移", migration)
        self.assertIn("不增加 required dependency", migration)

        steps = re.findall(r"^[1-3]\. ", migration, flags=re.MULTILINE)
        self.assertEqual(len(steps), 3)

    def test_task_template_uses_only_v07_contract_enums(self):
        template = read(REFERENCES / "TASK_TEMPLATE.md")
        expected = (
            "<document|plan|code|review|repair|test>",
            "<Pending|In Review|Passed|Needs Fix|Do Not Merge>",
            "<UA0|UA1|UA2|UA3|UA4|UA5|UA6|UA7|TBD>",
            "<Not Required|Pending|Passed|Failed|Deferred|TBD>",
            "<Not Applicable|Unmerged|Merged|Deferred>",
        )
        for value in expected:
            self.assertIn(value, template)
        self.assertIn("`Skipped by policy` 不等于 `Passed`", template)
        self.assertIn("`review_status` 保持 `Pending`", template)

    def test_brief_template_is_tracked_only_and_v07_compatible(self):
        template = read(REFERENCES / "TASK_TEMPLATE_BRIEF.md")
        for value in (
            "adf/v0.7.0",
            "<document|plan|code|review|repair|test>",
            "<A|B|C>",
            "<Pending|In Review|Passed|Needs Fix|Do Not Merge>",
            "<UA0|UA1|UA2|UA3|UA4|UA5|UA6|UA7|TBD>",
            "<Not Required|Pending|Passed|Failed|Deferred|TBD>",
            "`review_status` 保持 `Pending`",
        ):
            with self.subTest(value=value):
                self.assertIn(value, template)
        self.assertIn("全部 Controlled 任务一律使用 `TASK_TEMPLATE.md`", template)
        self.assertIn("跨会话需求时，升级回完整模板", template)

    def test_active_documents_are_materially_smaller_than_v07(self):
        frozen_v07_lines = {
            "SKILL.md": 288,
            "references/WORKFLOW.md": 615,
            "references/PROMPTS.md": 1182,
            "references/TASK_TEMPLATE.md": 389,
        }
        for relative, baseline in frozen_v07_lines.items():
            lines = len(read(SKILL_ROOT / relative).splitlines())
            with self.subTest(relative=relative):
                self.assertLess(lines, baseline * 0.5)

    def test_on_demand_references_exist(self):
        names = (
            "WORKFLOW.md",
            "TASK_TEMPLATE.md",
            "TASK_TEMPLATE_BRIEF.md",
            "CODE_REVIEW_CHECKLIST.md",
            "ACCEPTANCE_GUIDE.md",
            "GIT_PRECHECK.md",
            "DIFF_REVIEW.md",
            "V0.8_MIGRATION.md",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertTrue((REFERENCES / name).is_file())

    def test_historical_comparison_evidence_remains_readable(self):
        metrics = sorted((SKILL_ROOT / "tests" / "fixtures" / "comparisons").glob("*/metrics.json"))
        self.assertEqual(len(metrics), 3)
        for path in metrics:
            data = json.loads(read(path))
            ledger = data["ledger"]
            legacy_required = sum(item["legacy_required"] for item in ledger)
            compact_required = sum(item["compact_required"] for item in ledger)
            with self.subTest(path=path.parent.name):
                self.assertEqual(data["legacy_required_inputs"], legacy_required)
                self.assertEqual(data["compact_required_inputs"], compact_required)
                self.assertEqual(data["compact_duplicate_state_occurrences"], 0)
                self.assertLess(compact_required, legacy_required)


if __name__ == "__main__":
    unittest.main()
