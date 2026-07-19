# ai-dev-flow

`ai-dev-flow` v0.8 是按风险启用的 Git-first AI 开发治理内核。它不再要求所有任务走完整流程：小任务直接退出 Skill；需要跨会话留证或高风险控制时才启用 TASK、Reviewer 和修复上限。

## 一句话用法

```text
请使用 ai-dev-flow 执行这个任务；先按 v0.8 policy 判断 DoNotUseSkill、Tracked、Controlled 或 Blocked。
```

支持 Skill 的 agent 先读：

1. `SKILL.md`
2. `references/CORE.md`

这两份文件是默认运行时内核。不要预加载整个 `references/`，也不要默认加载 `PROMPTS.md`。

## 三档结果

| 结果 | 适合什么 | 默认成本 |
|---|---|---|
| `DoNotUseSkill` | 低风险、单会话、少量文件、验证完整 | 不建 TASK、不调用 Reviewer、不进入 repair loop |
| `Tracked` | 跨会话、范围较大或需要证据留存 | TASK；风险命中时才调用只读 Reviewer |
| `Controlled` | D 级、高风险、真实环境、交付或不可逆动作 | 完整 TASK；关键动作前强制独立 Review |

准确触发条件只在 `references/CORE.md` 的 `POLICY_JSON` 中维护。输入不完整或权限不明时为 `Blocked`，不猜测降级。

## 默认保留什么

- 用户与项目规则优先；
- Git 状态、base/diff 和可回滚边界；
- Tracked / Controlled 的 TASK 事实源；
- 覆盖完成标准的确定性验证；
- 权限、真实环境和外部副作用门禁；
- 独立只读 Review；
- Review、UA、commit、merge、release、Closed 状态分离。

## 默认不再做什么

- 不为低风险任务创建流程文档；
- 不为证明流程存在而调用 Reviewer 或 subagent；
- 不预加载长提示词、Batch、Wave、Loop、Memory、Constitution、角色或 provider 指南；
- 不建设自动调度器、数据库、遥测、计费或模型 Adapter；
- 不自动 merge、push、release、删除、外部同步或关闭任务。

这些旧指南仍保留为按需兼容资料，不是 v0.8 默认能力承诺。

## 新建任务

- Lite：不创建 TASK。
- Tracked / Controlled：使用 `references/TASK_TEMPLATE.md`。
- 现有 TASK：继续原格式，不批量迁移。
- `references/TASK_TEMPLATE_COMPACT.md`：只供 v0.7 Writer/Reader 兼容。

TASK 是细粒度事实源，TASK_BOARD 是索引和投影。Skill 包版本为 `0.8.0`，Workflow Contract schema 仍为 `adf/v0.7.0`。

## Reviewer 和 repair

- Tracked 只有命中 policy 风险标记时才调用一个隔离、只读 Reviewer。
- Controlled 在验收建议、delivery、merge、release 前强制 Review。
- Reviewer 只审查，Repairer 只处理稳定 finding ID。
- repair 基础预算 2 轮；只有范围冻结、finding 单调减少、验证改善和其他 progress 条件全部满足时才增加第 3 轮。
- 3 是绝对上限，更换模型不重置预算，外部副作用不得自动重试。

## 按需文档

- 执行细节：`references/WORKFLOW.md`
- TASK 模板：`references/TASK_TEMPLATE.md`
- 代码审查：`references/CODE_REVIEW_CHECKLIST.md`
- 验证：`references/VALIDATION_GUIDE.md`
- 用户动作等级：`references/ACCEPTANCE_GUIDE.md`
- Git/diff：`references/GIT_PRECHECK.md`、`references/DIFF_REVIEW.md`
- v0.7 迁移：`references/V0.8_MIGRATION.md`
- 最小项目规则：`references/AGENTS_COMPAT.md`
- 人工复制提示：`references/PROMPTS.md`

一次只读当前动作真正需要的文件。Controlled 可按风险多读专项文档，但不要整包预加载。

## 安装

把完整 `skills/ai-dev-flow/` 目录复制到 agent 的 Skill 目录。若项目不支持 Skill，优先把 `references/AGENTS_COMPAT.md` 中的最小规则合并到项目 `AGENTS.md`；不要要求 agent 每次读取整套 reference。

迁移现有项目只需最多三步，见 `references/V0.8_MIGRATION.md`。历史 TASK、v0.7 Contract 和只读 lint 无需迁移。

## 只读 Contract 工具

v0.7 Reader、`workflow_lint` 和 TASK_BOARD drift 检查继续保留：

```powershell
python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/TASK-001.md --format human
python skills/ai-dev-flow/scripts/workflow_lint.py . --format human
```

lint 通过只代表可确定结构规则通过，不代表 Review、UA、merge、release 或 Closed。

## 版本状态

- Skill 包：`0.8.0` 发布候选。
- Contract schema：`adf/v0.7.0`，继续兼容。
- 发布状态：以仓库 tag / Release 证据为准；仅修改 `VERSION` 不等于已发布。
- v0.8 评估证据保存在 `evaluations/v0.8/`，冻结原型保存在 `prototypes/v0.8-lite/`，不应在日常使用中加载或改写。
