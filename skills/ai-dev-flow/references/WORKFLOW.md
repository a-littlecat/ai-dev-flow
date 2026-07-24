# ai-dev-flow v0.8 按需工作流

> 本文件不是默认必读。先按 `SKILL.md + CORE.md` 路由；只有 Tracked / Controlled 需要更完整执行细节时才读取。

## 导航

- [路由结果](#1-路由结果)
- [模式边界](#2-模式边界)
- [TASK 写入](#3-task-写入规则)
- [执行与验证](#4-执行流程)
- [Reviewer](#5-reviewer-闸门)
- [Repair](#6-repair-与第-3-轮)
- [Git 与交付](#7-git-与交付)
- [UA 与状态](#8-ua-与状态)
- [兼容能力](#9-兼容能力)

## 1. 路由结果

`CORE.md` 的 `POLICY_JSON` 是唯一决策源，本文件不复制风险触发列表。

| 结果 | TASK | Reviewer | repair |
|---|---|---|---|
| `DoNotUseSkill` | 不创建 | 不调用 | 不进入 loop |
| `Tracked` | 新建或沿用 | 风险命中才调用 | `AutoRepair` 基础 2 轮；`Stop` 后可由用户授权有界升级 |
| `Controlled` | 必须有 | enforcement point 前强制 | 同上，且禁止重试外部副作用 |
| `Blocked` | 记录阻塞（如已有 TASK） | 不得自批 | 不猜测继续 |

Lite 退出后只用项目规则、Git/diff、直接相关文件和确定性验证，不再读取本文件。

## 2. 模式边界

Tracked / Controlled 仍可使用以下动作名，但不要求每轮声明角色，也不建立通用 Loop 平台：

- `init_project`：只建立最小项目规则和任务入口，不实现业务。
- `create_task`：创建有边界、完成标准和验证方式的 TASK。
- `plan_task`：大任务先写方案，不同时执行实现。
- `execute_task`：只做当前 TASK 允许的修改。
- `review_task`：只读审查，不修复。
- `repair_task`：只修稳定 finding ID 指向的问题。
- `close_task`：汇总状态；没有相应 authority 不关闭。
- `status_report`：只读汇总事实，不改变状态。

一个步骤只能有一个主要模式。用户若只要求诊断或审查，不得顺手实现。

## 3. TASK 写入规则

- v0.8 新建任务遵循 `SKILL.md` 的模板路由：仅大上下文、预期单会话且无需交接的 Tracked 任务可用 `TASK_TEMPLATE_BRIEF.md`；其他 Tracked 和全部 Controlled 使用 `TASK_TEMPLATE.md`。
- v0.7 以前的 TASK 原格式继续有效，不批量迁移。
- `TASK_TEMPLATE_COMPACT.md` 只保留给 v0.7 Writer/Reader 兼容，不是 v0.8 默认入口。
- TASK 是范围、状态、验证和审查事实源；TASK_BOARD 只记录索引和投影。
- 更新 TASK 后再同步看板；看板不得反向覆盖更细的 TASK 事实。

最少记录：

1. Contract 字段和当前状态；
2. 目标、非目标、允许/禁止范围；
3. authority、base commit、完成标准和验证；
4. 修改文件、diff、Review findings、UA 和剩余风险。

## 4. 执行流程

### 4.1 开始前

1. 读取用户请求、项目 `AGENTS.md`、TASK 和 source of truth。
2. 运行 Git precheck，识别已有改动，不覆盖用户工作。
3. 确认 authority、任务等级、风险、UA、执行位置和停止条件。
4. 冻结允许修改范围、禁止范围、完成标准和验证命令。
5. 若事实与 TASK 冲突，先更新或阻塞，不凭聊天猜状态。

### 4.2 修改中

- 只做完成当前标准所需的最小改动。
- 新依赖、架构变化、数据库/协议迁移、范围扩大或不可逆动作必须停下重新取得授权。
- 发现来源不明的重叠改动时停止，不擅自回退。
- 失败应保留可复现证据；不要为了“全绿”修改 oracle 或阈值。

### 4.3 验证

- 每项完成标准都要有自动命令、人工步骤或明确的不适用理由。
- 优先运行最贴近风险的测试，再运行合理范围的回归。
- 真实环境、真实账号、真实数据或外部宿主所需证据不能由普通单元测试替代。
- 记录命令、退出码、关键结果、未覆盖项和 `git diff --check`。
- 自动化通过不等于 Review、UA、merge、release 或 Closed。

### 4.4 交接

更新 TASK 的 Outcome 和 TASK_BOARD 投影，列出修改文件、验证、finding、状态边界、风险和下一步。没有做过的动作明确写未做，不制造完成状态。

## 5. Reviewer 闸门

Reviewer 是否需要由 `CORE.md` policy 决定：

- Tracked 未命中风险时跳过，记录 `Skipped by policy`。
- `Skipped by policy` 只写入 Outcome，不得写成 `review_status=Passed`；v0.7 Contract 保持 `Pending`，需要进入 Accepted / Closed 时再完成真实只读 Review。
- Tracked 命中风险时调用一个隔离、只读 Reviewer。
- Controlled 在 acceptance recommendation、delivery、merge、release 前强制 Review。
- 缺少独立 Reviewer authority/capability 时为 `Blocked`；不能由 Engineer 自批。

Reviewer 输入至少包括 TASK、base/diff、验证证据、项目规则和允许范围。输出至少包括：

- 结论：`Passed / Needs Fix / Blocked`；
- finding：稳定 ID、P0～P3、证据、范围和验证方式；
- 是否允许进入对应 UA 或 delivery；
- 未验证项和结论边界。

## 6. Repair、自主上限与用户授权升级

一轮 repair 只计“针对冻结 finding 的 patch → 验证 → 下一次独立复审”。只读 Review、无 patch 的 UA、诊断取证、原样重跑测试、TASK/看板收据同步和纯记录纠错不计轮次。

预算绑定 `repair_chain_id + finding_ids + closure_contract_hash`；换 TASK 或模型不重置。`AutoRepair` 基础预算为 2，第 2 轮后只有 `CORE.md` policy 的 progress 条件全部满足才允许第 3 轮。记录建议结构：

```text
repair_chain: <stable id + finding/closure/allowed-files hashes>
trigger_review: <independent read-only receipt>
attempts: [<AR-1 receipt>, <AR-2 receipt>]
history_anchor: <attempt count + head receipt hash + TASK source ref>
trusted_context: <external expected head/count + attested Review/authority receipt hashes>
latest_review.progress:
  closure_before / closure_after: <RED/GREEN vectors>
  blocking_findings_before / after: <sets>
  severity_before / after: <maps>
  evidence_vector / before / after: <fixed vector and coverage>
  round_3_target: <single frozen target>
decision: ExtendRound3 / Stop
```

第 3 轮后自主 loop 必须 `Stop`。这不是 AI 永久禁修：进入用户裁决后，用户可在查看证据/风险后明确授权默认一次的 `EscalatedRepair`。授权时必须冻结干净基线、RED/GREEN、目标、允许范围和独立 Reviewer；失败回到 `Stop`，不得自动连跑。外部副作用或不可逆动作仍为硬阻断。

可用 `scripts/repair_gate.py` 对不可信 ledger 与独立 trusted context 做只读比较。脚本只返回 `MechanicallyEligible`，持有真实当前对话、harness 或只读项目证据的 Orchestrator 才能提升为最终 `*Allowed`；缺 trusted context 固定 `Blocked`。其通过不替代 Review 或 UA。

## 7. Git 与交付

- A/B 不机械建分支；C 建议独立分支；D 或高风险必须隔离。
- commit 只包含当前 TASK 可归属 diff；先检查状态和 staged diff。
- merge、push、tag、release、外部同步、删除分支/Worktree 都是独立动作，需要各自 authority。
- delivery 前重新核对 diff、验证、Review、UA 和交付范围。

## 8. UA 与状态

UA0～UA7 的细节按需读取 `ACCEPTANCE_GUIDE.md`。最低原则：用户只做无法由 agent 自证的观察、实机测试、回归或决策；不要求用户逐行审代码。

生命周期、Review、UA、Accepted、commit、merge、release 和 Closed 分开记录。状态不清时写 `Pending`、`Blocked` 或“待确认”。

## 9. 兼容能力

旧 Batch、Wave、Loop、Memory、Constitution、角色、GitHub backend 和 harness 指南仍保留为手动兼容资料，但退出 v0.8 默认路径。若用户明确要求其中一项，应先重新路由并只读取对应指南；这不代表 v0.8 提供自动调度、数据库或外部同步。
