# ai-dev-flow 任务看板

> - 快照日期：2026-07-21
> - 当前模式：`SYNC-001` 受控同步
> - 当前阶段：审查用户提供的 Skill 增量；通过后同步仓库与已存在的本机副本，并推送 `main`
> - 当前方案：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md`

## 当前授权边界

用户明确指出原 PLAN-001 只扩展 Review-Repair Loop，并未完成项目瘦身；随后授权修改或推翻 PLAN-001，只要最终满足“前沿模型使用 Skill 有净正收益、避免无效额度与负优化”的需求。

用户随后要求补齐两项缺口：首版应有轻量自动审核流程；两轮修复后如果仍在持续收敛，不应仅因次数耗尽就要求用户接管。

独立 Review 随后记录 4 项 P1；用户明确要求“修改”，因此授权第 1 轮有限 `repair_task` 只处理 Lite 验证边界、Tracked Reviewer 降级路径、收益验证/实施顺序和可复现净收益协议。该授权不包含实施、创建 `LEAN-*`、代替独立复审或任何 delivery 动作。

独立复审关闭全部 4 项 P1 后，用户于 2026-07-19 明确确认“审核及验收通过”。该确认写回为 Review Passed、UA2 Passed 和 `Accepted`，不扩展为创建/执行 `LEAN-*`、commit、merge、push、release、本机同步或 `Closed` 授权。

用户随后于 2026-07-19 明确要求“提交”，因此仅授权把 RFC、PLAN-001 和本看板形成 Accepted Git baseline；该授权不包含 merge、push、release、本机同步、`Closed` 或后续 `LEAN-*` 实施。

用户随后要求统一澄清模型来源表述。本轮只使用“当前执行模型真实任务对照”和“额外模型供应商”两个术语，明确独立 Reviewer 可以使用同一平台/模型的隔离上下文；不改变三次上限、评估门禁或授权边界。用户随后再次明确要求“提交”，因此仅授权把该三文件澄清形成独立 commit。

用户于 2026-07-19 进一步明确要求“按 PLAN-001 串行执行 LEAN-001～003”。该授权允许创建并顺序执行最多 3 个 LEAN TASK、在专用实施分支形成逐任务 commit，并在计划规定的确定性门禁触发时使用隔离只读 Reviewer；不授权并行写代码、merge、push、release、本机 Skill 同步或 `Closed`。若阶段 A、阶段 B 或全面实施门禁失败，串行链必须在失败点停止，不能为了执行到 LEAN-003 而改写阈值或证据。

`LEAN-002` 随后因实际原型未绑定 stage A、平台不暴露精确 backend model/call ID 而被整体 Review 阻断。用户在理解原因后明确要求继续完成 v0.8；该新指令授权同一 `LEAN-002` 创建 `V08-LEAN-EVAL-003`、先修复两项 P1，再在新协议 Review 通过后执行一个新的三次替代周期。V002 不改、不混用；新授权不包含第三个周期、额外 provider、merge、push、release、本机同步或 `Closed`。

用户于 2026-07-19 明确回复“继续，我已确认。完成上述操作”，完成 `LEAN-003` UA3；随后明确要求“合并推送发布，并且同步本机 skill”。当前授权包括：形成验收/发布候选提交，合并到 `main`，推送 `main`，创建并推送 annotated tag `v0.8.0`，创建正式 GitHub Release，以及同步已确认存在的本机 Skill 副本。该授权不包含 `Closed`、删除分支、改写历史或其他项目的外部操作。

用户随后于 2026-07-19 明确要求“关闭并删除分支”。该指令授权把 `LEAN-003` 从 Accepted 流转为 Closed，并删除已确认完全合并的本地 `codex/lean-v08-slimming` 分支；远端不存在同名分支。该授权不包含其他分支、tag、Release 或历史改写。

用户于 2026-07-21 明确要求审查其提供的 `.agents` Skill 源目录更新；确认无问题后同步到本项目和本机其他 Skill 位置，并推送远端。该授权覆盖 `SYNC-001` 的内容审查、已存在目标的文件同步、精确 commit 和 `main` push；不包含 tag、GitHub Release、删除未知附加文件或创建不存在的安装目录。Review 发现已发布 `v0.8.0` 与新增内容不能共用版本身份，因此 repair 将工作树身份收口为未发布 `0.8.1`，不制造发布事实。

本轮允许：

- 重写 PLAN-001 和对应 RFC；
- 更新本看板；
- 移除同一未提交规划集中被新方案取代的原 Loop RFC、9 个 `LOOP-*` Draft 和临时 PLAN-002。
- 精确提交上述三文件，形成 PLAN-001 Accepted Git baseline。
- 精确提交上述三文件的模型术语澄清。
- 创建并串行执行 `LEAN-001`～`003`，每项保持独立任务合同、diff、验证、Review 和 commit；后项只能在前项门禁通过后开始。
- 写回 `LEAN-003` UA3 Passed / Accepted，并完成已明确授权的 merge、push、`v0.8.0` tag、GitHub Release 和本机 Skill 同步。
- 写回 `LEAN-003` Closed，并在关闭收据提交后安全删除已完全合并的本地实施分支。

本轮不允许：

- 在 `LEAN-001` 阶段修改 `skills/ai-dev-flow/**`、现行行为或执行当前模型真实任务对照；
- 绕过阶段门禁提前创建或执行后续 `LEAN-*`；
- 接入或调用额外模型供应商，或在本计划阶段执行当前模型真实任务对照；
- 不删除其他分支、tag 或 Release，不强制删除未合并分支，不改写已提交历史，不执行额外版本发布或同步未确认的本机目录。

## 真相源与状态规则

- TASK 是任务边界、验证和验收的细粒度事实源；看板只保留索引、状态、依赖和当前授权。
- Review、UA、Accepted、Commit、Merge、Release、Closed 相互独立。
- 用户需求发生实质变化时可以重开规划任务，但必须记录原因并重新 Review / UA，不能沿用旧验收。
- 未形成 Git baseline 的 Draft 规划可在用户明确授权后被替换；不得把未提交草案伪装成已发布历史。
- 任何新实施任务都必须在 PLAN-001 新方案 Review Passed、UA2 通过并形成 Accepted baseline 后另行创建。

## 已完成 v0.7 依赖链

```text
REL-001
  -> CONTRACT-001
  -> CONTRACT-002
  -> CONTRACT-003
  -> CONTRACT-004
  -> CONTRACT-005
  -> CONTRACT-006
  -> REL-002 Closed / v0.7.0
```

## v0.8 当前入口

```text
REL-002 Closed / main@0422887
  -> PLAN-001 Accepted：整体 Skill 瘦身与净收益门禁
      -> Review Passed + 新 UA2 Passed
          -> LEAN-001 Review Passed / UA3 Pending
              -> LEAN-002 Review / Passed：V003 all_gates_pass=true
                  -> LEAN-003 Closed / Review Passed / UA3 Passed / Merged / Released v0.8.0 / Local Sync Verified / Branch Cleanup Verified
```

原 `V0.8_LOOP_DECISION_RFC`、`LOOP-001`～`LOOP-009` 和临时 PLAN-002 均未提交、未形成 baseline，已由用户授权从当前规划集移除。必要的 risk/progress/stall/authority 语义已作为瘦身 RFC 中 `LEAN-002` 的候选小模块保留，不再建设九任务通用 Loop 平台。

## 当前任务

| 任务 | 名称 | 等级 | 状态 | 优先级 | 风险 | 前置依赖 | Review | UA | 执行组织 | 任务文件 |
|---|---|---|---|---|---|---|---|---|---|---|
| REL-001 | 收口 v0.6 发布身份 | B | Accepted | 高 | 高 | 无 | 通过 / 无 P0-P3 | UA7 已通过 | Single / 独立分支 | [REL-001](tasks/REL-001-close-v06-release-identity.md) |
| CONTRACT-001 | 固化 Workflow Contract 语义规范 | C | Accepted | 高 | 高 | REL-001 Accepted baseline `752b11f` | 通过 / 无 P0-P3 | UA2 已通过 | Single / 独立分支 | [CONTRACT-001](tasks/CONTRACT-001-workflow-contract-semantics.md) |
| CONTRACT-002 | 建立 Golden fixtures 与填写量基线 | C | Accepted | 高 | 中 | CONTRACT-001 Accepted `28e74f8` | 通过 / 无 P0-P1 | UA3 已通过 | Single / 独立分支 | [CONTRACT-002](tasks/CONTRACT-002-golden-fixtures.md) |
| CONTRACT-003 | 实现 Legacy / v0.7 只读 Reader | C | Accepted | 高 | 高 | CONTRACT-002 Accepted `f7d870d` | 通过 / 无 P0-P1 | UA3 已通过 | Single / 独立分支 | [CONTRACT-003](tasks/CONTRACT-003-readonly-contract-readers.md) |
| CONTRACT-004 | 实现只读 workflow_lint | C | Accepted | 高 | 高 | CONTRACT-003 Accepted `95ec566` | 通过 / 无 P0-P1 | UA4 已通过 | Single / 独立分支 | [CONTRACT-004](tasks/CONTRACT-004-workflow-lint-cli.md) |
| CONTRACT-005 | 启用 Compact Template 与最小 Writer 路由 | D | Accepted | 中 | 高 | CONTRACT-004 Accepted `7f0f7e5` | 通过 / 无 P0-P3 | UA6 已通过 | Worktree | [CONTRACT-005](tasks/CONTRACT-005-compact-template-writer-routing.md) |
| CONTRACT-006 | 增加 TASK_BOARD 只读投影与 drift 检查 | C | Accepted | 中 | 高 | CONTRACT-004、005 Accepted | 通过 / 无 P0-P3 | UA6 已通过 | Worktree | [CONTRACT-006](tasks/CONTRACT-006-task-board-projection.md) |
| REL-002 | 收口 v0.7 发布身份并同步本机 Skill | B | Closed | 高 | 高 | CONTRACT-001～006 Accepted | Passed / 无 P0-P3 | UA3 Passed | Released `v0.7.0` / Closed | [REL-002](tasks/REL-002-close-v07-release-identity-and-sync.md) |
| PLAN-001 | 规划前沿模型时代的 Skill 瘦身与净收益门禁 | C | Accepted | 高 | 高 | REL-002 Closed；Base `0422887` | 通过 / 无 P0-P3 | UA2 已通过 | Single / 当前规划分支 | [PLAN-001](tasks/PLAN-001.md) |
| LEAN-001 | 冻结 v0.8 评估合同并执行零额度回放 | C | Review | 高 | 中 | PLAN-001 Accepted；Base `b7938ef` | Passed / 无 P0-P3 | UA3 Pending | Single / `codex/lean-v08-slimming` | [LEAN-001](tasks/LEAN-001.md) |
| LEAN-002 | 构建默认关闭原型并执行阶段 B 对照 | C | Review | 高 | 高 | LEAN-001 Review Passed；V003 all gates Passed | Passed / 无 P0-P3 | UA3 Pending | Single + 串行隔离上下文 / `codex/lean-v08-slimming` | [LEAN-002](tasks/LEAN-002.md) |
| LEAN-003 | 全面精简 Skill 并收口 v0.8 实现 | D | Closed | 高 | 高 | LEAN-002 Review Passed；V003 all gates Passed | Passed / P0-P3=0 | UA3 Passed | Merged / Released `v0.8.0` / Local Sync Verified / Branch Cleanup Verified | [LEAN-003](tasks/LEAN-003.md) |
| SYNC-001 | 审查并同步 ai-dev-flow Skill 增量 | D | Review | 中 | 高 | LEAN-003 Closed；Base `d4854a7` | Passed / P0-P3=0 | UA3 Pending | Single / `main` / Controlled | [SYNC-001](tasks/SYNC-001.md) |

## PLAN-001 核心约束

- Lite 是默认，但必须有覆盖全部关键完成标准的确定性验证；容易回滚不能替代验证，需要用户观察或真实环境证据时升级 Tracked。
- Lite 不建 TASK、不调用独立 Reviewer、不进入 repair loop。
- 首版自动审核只实现确定性闸门：Lite 禁止，Tracked 风险触发，Controlled 交付前强制；Tracked 命中门禁但缺 Reviewer 时必须 Blocked、合法升级或取得明确授权，不能静默跳过。
- Tracked / Controlled repair 基础预算为 2；finding 单调减少、验证改善且范围冻结时自动增加第 3 轮，3 为绝对上限。
- 当前模型真实任务对照前先冻结样本与计量协议并做零额度回放；通过后只做可整体回退的最小原型，使用当前执行会话所用模型、一个 Lite 任务、最多 3 次执行；不接入额外模型供应商，全面收缩必须等待对照通过。
- 首版候选实施任务不超过 3 个，验收前不创建。
- 如果不能把工作流输入、模型调用和用户流程问题至少降低 50%，或出现更多 P0/P1、权限越界、状态误报，则停止 v0.8 扩建。

## 下一允许动作

执行 `SYNC-001`：仅在源增量验证和隔离只读 Review 无阻断 finding 后，同步仓库与已存在的本机副本，精确提交并推送 `main`；保留 `v0.8.0` tag、GitHub Release、历史任务和其他分支不变。

## 停止条件

- PLAN-001 最终范围超出 RFC、TASK_BOARD 和 TASK 文件。
- 瘦身方案仍要求首版执行超过 3 个任务。
- Lite 绕过 authority、真实环境、数据、发布或不可逆动作门禁。
- 自动审核扩张为通用调度平台、数据库、模型 Adapter，或在低风险任务上产生无理由调用。
- 第 3 轮缺少 progress 证据、突破绝对上限，或用于自动重试不可逆外部动作。
- 任一模型成为核心依赖，或模型更换重置额度/repair 计数。
- 需要自动调度器、数据库、遥测或计费系统才能证明收益。
- 目标分支未完全合并、当前工作区不干净、远端出现未核对的同名分支，或清理动作需要强制删除、历史改写、额外发布或未确认路径同步。
