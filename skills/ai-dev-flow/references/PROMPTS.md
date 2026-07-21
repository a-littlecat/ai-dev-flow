# ai-dev-flow v0.8 短提示词

> 可选人工复制材料，不是 Skill 默认依赖。正常使用只需描述目标；agent 应读取 `SKILL.md + CORE.md` 自行路由。

## 路由

```text
请按 ai-dev-flow v0.8 先判断 DoNotUseSkill / Tracked / Controlled / Blocked。
以 CORE.md 的 POLICY_JSON 为唯一路由依据，说明结论和关键证据；低风险结果为 DoNotUseSkill 时停止加载其余 Skill 文档。
```

## 创建 Tracked / Controlled TASK

```text
请创建 docs/tasks/<TASK-ID>.md。
按 SKILL.md 路由选择 TASK_TEMPLATE_BRIEF.md 或 TASK_TEMPLATE.md；全部 Controlled 使用完整模板。写清模板要求的目标、范围、authority、完成标准、验证、Review 闸门和 UA；同步 TASK_BOARD。
只创建任务，不实现业务。
```

## 执行任务

```text
请执行 docs/tasks/<TASK-ID>.md。
先核对 AGENTS.md、TASK、Git 状态和事实源，只改允许范围；完成后运行约定验证、检查 diff，并分别记录 Review、UA、commit、merge、release 和 Closed 状态。
```

## 只读审查

```text
请只读审查 docs/tasks/<TASK-ID>.md 及其 base..HEAD / 当前 diff。
不要修改业务代码。按稳定 finding ID 输出 P0～P3、证据、范围、验证方式、Passed / Needs Fix / Blocked，以及是否允许进入对应 UA。
```

## 有界修复

```text
请只修复以下稳定 finding ID：<粘贴 finding>。
不得扩大 TASK 范围。修复后运行指定验证并重新进入只读 Review；基础预算 2 轮，第 3 轮只能由 CORE.md progress gate 授予，3 为绝对上限。
```

## 验收失败诊断

```text
请先只读处理这份验收失败反馈：<粘贴反馈>。
区分 RED、GREEN 和 SIGNAL；证据不足时列最小补充信息，不直接改代码。只有根因、当前 TASK 范围、修复清单和验证方式都明确时才建议 repair_task。
```

## 状态汇总

```text
请只读汇总 TASK_BOARD 与相关 TASK。
分开报告 lifecycle、Review、UA、Accepted、commit、merge、release、Closed；不改变状态，不把自动化通过写成已验收或已发布。
```

## 交付前检查

```text
请按 Controlled 做交付前检查。
核对 authority、TASK、diff、验证、独立 Review、UA、真实环境证据和交付范围。没有对应授权不要 merge、push、tag、release、外部同步或关闭任务。
```

## 迁移 v0.7 项目

```text
请读取 V0.8_MIGRATION.md，只做兼容检查。
不要批量改写历史 TASK；确认 adf/v0.7.0 Reader/lint 仍可读取，并说明新任务是否应退出 Skill、进入 Tracked 或 Controlled。
```
