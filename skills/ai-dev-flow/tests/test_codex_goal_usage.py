from __future__ import annotations

import pathlib
import unittest


SKILL_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
README = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
CORE = (SKILL_ROOT / "references" / "CORE.md").read_text(encoding="utf-8")
GUIDE = (SKILL_ROOT / "references" / "CODEX_GOAL_USAGE.md").read_text(encoding="utf-8")
TASK_TEMPLATE = (SKILL_ROOT / "references" / "TASK_TEMPLATE.md").read_text(encoding="utf-8")
REPAIR_GATE = (SKILL_ROOT / "scripts" / "repair_gate.py").read_text(encoding="utf-8")


class CodexGoalUsageTests(unittest.TestCase):
    def test_goal_is_native_execution_container_not_project_authority(self) -> None:
        for text in (SKILL, GUIDE):
            self.assertIn("Goal", text)
            self.assertIn("TASK", text)
        self.assertIn("Goal 只是运行容器，不是 authority", GUIDE)
        self.assertIn("项目状态始终写回 TASK", GUIDE)

    def test_chinese_trigger_phrases_cover_all_three_profiles(self) -> None:
        phrases = (
            "启动受控目标",
            "持续修到可验收",
            "启动自动落地目标",
            "我去休息，自动修好并交付",
            "不用中途问我，完成后直接交付",
            "启动自动发布目标，版本为 <version>",
            "自动发版到 <environment>",
        )
        for phrase in phrases:
            self.assertIn(phrase, GUIDE)
        for profile in ("governed_goal", "auto_land", "auto_release"):
            self.assertIn(profile, SKILL)
            self.assertIn(profile, GUIDE)
        self.assertIn("中文触发词按完整意图解释，不做任意子串匹配", GUIDE)
        self.assertIn("“自动检查”不等于 `auto_land`", GUIDE)
        self.assertIn("“发布说明”不等于 `auto_release`", GUIDE)

    def test_auto_land_and_release_authorities_remain_separate(self) -> None:
        self.assertIn("commit", GUIDE)
        self.assertIn("push", GUIDE)
        self.assertIn("PR", GUIDE)
        self.assertIn("CI", GUIDE)
        self.assertIn(
            "`auto_land` 不包含 tag、release、deploy、删除、数据迁移、密钥或认证/授权修改、强制推送、历史改写或 `Closed`",
            GUIDE,
        )
        self.assertIn("只有版本、目标环境、交付物和回滚边界都明确时才启用", GUIDE)
        self.assertIn("缺少其中任一项时先从项目事实源保守补全", GUIDE)
        self.assertIn(
            "未被当前 `auto_release` authority 明确覆盖 / 超出冻结版本、环境、交付物与回滚边界的生产外部副作用",
            GUIDE,
        )

    def test_machine_acceptance_does_not_replace_irreducible_human_evidence(self) -> None:
        self.assertIn("Designated Acceptor", GUIDE)
        self.assertIn(
            "验收指标在启动前已冻结、当前环境可以直接执行、结果唯一且不依赖主观判断",
            GUIDE,
        )
        self.assertIn("以下情况不能自动代替用户", GUIDE)
        self.assertIn("真实外部宿主或设备不可用", GUIDE)

    def test_zero_state_composition_does_not_extend_contract_or_repair_gate(self) -> None:
        self.assertNotIn("goal_id", TASK_TEMPLATE.lower())
        self.assertNotIn("UnattendedRunAuthority", SKILL + GUIDE)
        self.assertNotIn("auto_land", CORE)
        self.assertNotIn("auto_land", REPAIR_GATE)

    def test_public_readme_exposes_chinese_auto_land_entry(self) -> None:
        self.assertIn("自动落地目标", README)
        self.assertIn("CODEX_GOAL_USAGE.md", README)


if __name__ == "__main__":
    unittest.main()
