# ai-dev-flow

[English](README.en.md)

一个按风险启用的 AI 开发工作流。它用项目规则、Git/diff、确定性验证和必要的任务记录约束 agent，但不会让每个小改动都背上完整流程。

v0.8 的核心变化很直接：

- 低风险小任务：不用 Skill，直接做并验证；
- 需要跨会话留证：用 Tracked TASK；
- 高风险、真实环境或交付动作：用 Controlled，并在关键动作前强制独立 Review。

## 为什么做 v0.8

旧版能管理复杂项目，但默认文档、提示词和流程入口太多。对前沿模型而言，这可能增加上下文、额外 Reviewer 调用和用户打断，却不一定提高结果质量。

v0.8 把默认运行时缩成两个文件：

```text
skills/ai-dev-flow/SKILL.md
skills/ai-dev-flow/references/CORE.md
```

其他指南继续保留，但只在当前动作确实需要时读取。

## 三档结果

| 结果 | 什么时候用 | 默认行为 |
|---|---|---|
| `DoNotUseSkill` | 低风险、单会话、少量文件、验证完整 | 不建 TASK、不调用 Reviewer、不进 repair loop |
| `Tracked` | 跨会话、范围较大或需要证据留存 | TASK；风险命中才调用只读 Reviewer |
| `Controlled` | D 级、高风险、真实环境、交付或不可逆动作 | 完整 TASK；关键动作前强制独立 Review |
| `Blocked` | 输入、权限、能力或证据不足 | 停止并说明最小阻塞信息 |

准确规则只维护在 `references/CORE.md` 的 `POLICY_JSON` 中，避免多份文档各写一套。

## 快速使用

把 `skills/ai-dev-flow/` 安装到 agent 的 Skill 目录，然后说：

```text
请使用 ai-dev-flow 执行这个任务；先判断 DoNotUseSkill、Tracked、Controlled 或 Blocked。
```

支持 Skill 的 agent 默认只读 `SKILL.md + CORE.md`。不支持 Skill 的项目可把 `references/AGENTS_COMPAT.md` 的最小规则合并进现有 `AGENTS.md`。

## 保留的核心能力

- 用户要求和项目规则优先；
- Git 状态、base commit、diff 归属和回滚边界；
- Tracked / Controlled 的 TASK 事实源；
- 覆盖完成标准的验证证据；
- 权限、真实环境、敏感数据和外部副作用门禁；
- 隔离、只读的 Reviewer；
- Review、UA、Accepted、commit、merge、release、Closed 分开记录。

## 精简掉的默认成本

以下内容没有删除，但退出默认运行路径：

- 长提示词库；
- Batch、Parallel Wave 和通用 Loop 编排；
- Memory、Project Constitution 和角色声明；
- provider / harness 分支；
- 普遍 Reviewer 和无条件 repair loop。

v0.8 不建设自动调度器、数据库、遥测、计费、模型 Adapter，也不自动 merge、push、release、删除或外部同步。

## TASK 与 v0.7 兼容

- Lite 不创建 TASK。
- 新建 Tracked / Controlled 使用 `references/TASK_TEMPLATE.md`。
- 旧 TASK 不批量迁移，原格式继续可读。
- `TASK_TEMPLATE_COMPACT.md` 只为 v0.7 Writer/Reader 兼容保留。
- Skill 包版本是 `0.8.0`，Workflow Contract schema 继续是 `adf/v0.7.0`。

迁移说明见 `skills/ai-dev-flow/references/V0.8_MIGRATION.md`，用户最多需要 3 步。

## Reviewer 与第 3 轮 repair

- Tracked 仅在确定性风险命中时调用一个隔离、只读 Reviewer。
- Controlled 在验收建议、delivery、merge、release 前强制 Review。
- repair 基础预算为 2 轮；只有范围冻结、finding 单调减少、验证改善等 progress 条件全部满足时才增加第 3 轮。
- 3 是绝对上限；更换模型不重置预算；不可逆外部动作不得自动重试。

## 只读检查

v0.7 的标准库 Reader、`workflow_lint` 和 TASK_BOARD drift 检查继续保留：

```powershell
python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/TASK-001.md --format human
python skills/ai-dev-flow/scripts/workflow_lint.py . --format human
```

lint 通过只说明可确定结构规则通过，不代表 Review、UA、merge、release 或 Closed。

## 仓库结构

```text
ai-dev-flow/
├── README.md
├── README.en.md
├── docs/
├── evaluations/v0.8/
└── skills/ai-dev-flow/
    ├── SKILL.md
    ├── VERSION
    ├── references/
    ├── scripts/
    └── tests/
```

详细手册见 `skills/ai-dev-flow/README.md`。

## 当前版本

```text
0.8.0
```

- 当前发布候选：`0.8.0`。
- Workflow Contract：`adf/v0.7.0`，继续兼容。
- 发布状态：正式发布身份以仓库 `v0.8.0` tag 和 GitHub Release 证据为准。
- v0.7.0 历史 tag 保留，不因 v0.8 实现而改写。

变更记录见 `skills/ai-dev-flow/CHANGELOG.md`。

## License

MIT License，详见 [LICENSE](LICENSE)。
