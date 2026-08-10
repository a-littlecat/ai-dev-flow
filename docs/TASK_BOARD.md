# ai-dev-flow 任务看板

> 任务状态表为生成区，请勿手改（由 `skills/ai-dev-flow/scripts/board_generator.py` 维护）；生成区标记范围外为人工维护区。
> - 快照日期：2026-08-10
> - 当前模式：PROGRESS-VISIBILITY-001 实施（跨 worktree 进展可见性 + 看板生成器）
> - 当前阶段：`PROGRESS-VISIBILITY-001 In Progress / Review Passed（用户裁决口径） / UA6 Pending`
> - 当前方案：`docs/tasks/PROGRESS-VISIBILITY-001.md`

## 当前执行任务（2026-08-10）

- `PROGRESS-VISIBILITY-001`：`In Progress / Controlled / Review Passed（用户裁决口径） / UA6 Pending / Baseline Committed 733dc14 / Unmerged / Not Released`。在独立 Worktree `ai-dev-flow-wt/progress-visibility-001` 实施；merge、push、release、本机 Skill 安装目录同步、Closed 未授权。
- v0.10 线（`ADF-V010-*`，4 个 `codex/v010-*` worktree）按用户 2026-08-10 裁定暂停扩展，其任务状态由仪表盘跨 worktree 聚合观察。

## 当前授权边界

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

<!-- ADF-GENERATED:BEGIN -->
| 任务 | 名称 | 等级 | 状态 | Review | UA | 验收 | 交付 | 任务文件 |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-001 | 固化 Workflow Contract 语义规范 | C | Closed | Passed | UA2 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/CONTRACT-001-workflow-contract-semantics.md |
| CONTRACT-002 | 建立 Golden fixtures 与填写量基线 | C | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/CONTRACT-002-golden-fixtures.md |
| CONTRACT-003 | 实现 Legacy / v0.7 只读 Reader | C | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/CONTRACT-003-readonly-contract-readers.md |
| CONTRACT-004 | 实现只读 workflow_lint | C | Closed | Passed | UA4 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/CONTRACT-004-workflow-lint-cli.md |
| CONTRACT-005 | 启用 Compact Template 与最小 Writer 路由 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/CONTRACT-005-compact-template-writer-routing.md |
| CONTRACT-006 | 增加 TASK_BOARD 只读投影与 drift 检查 | C | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/CONTRACT-006-task-board-projection.md |
| DASHBOARD-001 | 规划本地任务关系仪表盘与只读调度后端 | C | Closed | Passed | UA2 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-001-local-task-relationship-dashboard.md |
| DASHBOARD-ACTION-CENTER-001 | 将默认关系图改为聚焦的任务执行工作台 | D | Accepted | Passed | UA6 | Passed / Designated Acceptor Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-ACTION-CENTER-001.md |
| DASHBOARD-BE-001 | 实现任务关系与调度核心 | C | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-BE-001.md |
| DASHBOARD-BE-001-REPAIR-001 | 修复核心快照性能与 dirty ownership 合同 | D | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-BE-001-REPAIR-001.md |
| DASHBOARD-BE-002 | 实现 Git 快照、本地只读 API 与实时更新 | D | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-BE-002.md |
| DASHBOARD-EDGE-LABEL-001 | 修复关系文字被任务卡片遮挡 | D | Closed | Passed | UA5 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-EDGE-LABEL-001.md |
| DASHBOARD-EDGE-PERF-INTEGRATE-001 | 集成页面可读性与空闲性能并重建运行时 | D | Closed | Passed | UA6 | Passed / Designated Acceptor Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-EDGE-PERF-INTEGRATE-001.md |
| DASHBOARD-FE-001 | 实现关系图优先的本地任务仪表盘前端 | C | Closed | Passed | UA4 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-FE-001.md |
| DASHBOARD-FE-001-REPAIR-001 | 修复真实任务规模下关系图被并行评估列表挤出首屏 | D | Closed | Passed | UA4 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-FE-001-REPAIR-001.md |
| DASHBOARD-FE-001-REPAIR-002 | 增强关系图选中态可见性 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-FE-001-REPAIR-002.md |
| DASHBOARD-FOCUS-ASSESSMENT-001 | 消除聚焦链与并行评估线的视觉歧义 | B | Review | Passed | UA3 | Pending / None | commit=Committed;merge=Not Recorded;merge_authority=None | docs/tasks/DASHBOARD-FOCUS-ASSESSMENT-001.md |
| DASHBOARD-IDLE-PERF-001 | 降低 Dashboard 常驻扫描 CPU 占用 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-IDLE-PERF-001.md |
| DASHBOARD-INTEGRATE-001 | 集成本地任务仪表盘并完成回归验收 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-INTEGRATE-001.md |
| DASHBOARD-PORTABLE-001 | 支持跨项目 Dashboard 与多实例隔离 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-PORTABLE-001.md |
| DASHBOARD-PORTABLE-REPAIR-001 | 阻止未登记 Python 字节码绕过运行时校验 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-PORTABLE-REPAIR-001.md |
| DASHBOARD-PORTABLE-REPAIR-002 | 修复生产空白页与历史 Scheduling 兼容 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-PORTABLE-REPAIR-002.md |
| DASHBOARD-PORTABLE-REPAIR-003 | 关闭提交前版本固定与干净检出缺口 | D | Closed | Passed | UA6 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/DASHBOARD-PORTABLE-REPAIR-003.md |
| GOAL-USAGE-001 | 增加 Codex Goal 自动落地预设与中文触发词 | D | Closed | Passed | UA2 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/GOAL-USAGE-001.md |
| LEAN-001 | 冻结 v0.8 评估合同并执行零额度回放 | C | Cancelled | Passed | UA3 | Deferred / None | commit=Committed;merge=Deferred;merge_authority=None | docs/tasks/LEAN-001.md |
| LEAN-002 | 构建默认关闭原型并执行阶段 B 对照 | C | Cancelled | Passed | UA3 | Deferred / None | commit=Committed;merge=Not Applicable;merge_authority=None | docs/tasks/LEAN-002.md |
| LEAN-003 | 全面精简 Skill 并收口 v0.8 实现 | D | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/LEAN-003.md |
| PLAN-001 | 规划前沿模型时代的 Skill 瘦身与净收益门禁 | C | Closed | Passed | UA2 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/PLAN-001.md |
| PROGRESS-VISIBILITY-001 | 统一跨 Worktree 进展可见性并瘦身任务看板 | C | In Progress | Passed | UA6 | Pending / None | commit=Committed;merge=Not Recorded;merge_authority=None | docs/tasks/PROGRESS-VISIBILITY-001.md |
| REL-001 | 收口 v0.6 发布身份 | B | Closed | Passed | UA7 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REL-001-close-v06-release-identity.md |
| REL-002 | 收口 v0.7 发布身份并同步本机 Skill | B | Closed | Passed | UA3 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REL-002-close-v07-release-identity-and-sync.md |
| REL-003 | 发布 v0.9.0 本地任务关系仪表盘 | D | Closed | Passed | UA7 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REL-003-release-v090-dashboard.md |
| REL-004 | 发布 v0.9.1 跨项目 Dashboard | D | Closed | Passed | UA7 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REL-004-release-v091-portable-dashboard.md |
| REL-005 | 收口历史治理债务并发布 v0.9.2 | D | Closed | Passed | UA7 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REL-005-release-v092-maintenance.md |
| REPAIR-CAMPAIGN-001 | 实现任务级连续修复授权 | D | Closed | Passed | UA2 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REPAIR-CAMPAIGN-001.md |
| REPAIR-ESCALATION-001 | 实现用户授权的超限修复通道 | D | Closed | Passed | UA2 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/REPAIR-ESCALATION-001.md |
| SYNC-001 | 审查并同步 ai-dev-flow Skill 增量 | D | Cancelled | Passed | UA3 | Deferred / None | commit=Committed;merge=Not Applicable;merge_authority=None | docs/tasks/SYNC-001.md |
| WORKSPACE-CLEANUP-001 | 迁移主工作区前端改动并清理旧工作区 | D | Closed | Passed | UA5 | Passed / User Confirmed | commit=Committed;merge=Merged;merge_authority=User Authorized | docs/tasks/WORKSPACE-CLEANUP-001.md |
<!-- ADF-GENERATED:END -->

## PLAN-001 核心约束与 REPAIR-ESCALATION-001 演进

- Lite 是默认，但必须有覆盖全部关键完成标准的确定性验证；容易回滚不能替代验证，需要用户观察或真实环境证据时升级 Tracked。
- Lite 不建 TASK、不调用独立 Reviewer、不进入 repair loop。
- 首版自动审核只实现确定性闸门：Lite 禁止，Tracked 风险触发，Controlled 交付前强制；Tracked 命中门禁但缺 Reviewer 时必须 Blocked、合法升级或取得明确授权，不能静默跳过。
- Tracked / Controlled `AutoRepair` 基础预算为 2；逐 finding RED→GREEN、无回归且证据覆盖增加时可增加第 3 轮。3 是自主 loop 上限；`Stop` 后用户可明确授权有界 `EscalatedRepair`，换 TASK/模型不重置 chain。
- 可选 `RepairCampaignAuthority` 在同一 TASK、验收合同和外层范围内连续处理新 chain；核心产品连续 4 次无实质进展、Harness 连续 5 次无实质进展后才进入用户裁决，硬停止条件立即生效。
- 当前模型真实任务对照前先冻结样本与计量协议并做零额度回放；通过后只做可整体回退的最小原型，使用当前执行会话所用模型、一个 Lite 任务、最多 3 次执行；不接入额外模型供应商，全面收缩必须等待对照通过。
- 首版候选实施任务不超过 3 个，验收前不创建。
- 如果不能把工作流输入、模型调用和用户流程问题至少降低 50%，或出现更多 P0/P1、权限越界、状态误报，则停止 v0.8 扩建。

## 下一允许动作

继续实施 `PROGRESS-VISIBILITY-001`：完成运行时重建与 artifact 门禁候选判定，写回实施证据后停在等待用户 UA 的状态。merge、push、release、本机 Skill 安装目录同步、Accepted、Closed 均需用户逐项明确授权。

## 停止条件

- PLAN-001 最终范围超出 RFC、TASK_BOARD 和 TASK 文件。
- 瘦身方案仍要求首版执行超过 3 个任务。
- Lite 绕过 authority、真实环境、数据、发布或不可逆动作门禁。
- 自动审核扩张为通用调度平台、数据库、模型 Adapter，或在低风险任务上产生无理由调用。
- 第 3 轮缺少 progress 证据、自主 loop 突破上限、`EscalatedRepair` 缺少有限用户授权/冻结信号，或用于自动重试不可逆外部动作。
- campaign streak 可被换 chain/TASK/模型清零，4 / 5 阈值未按 profile 执行，或 P0、安全、数据、越界、不可逆、oracle 放宽等硬停止被延迟。
- 任一模型成为核心依赖，或模型更换重置额度/repair 计数。
- 需要自动调度器、数据库、遥测或计费系统才能证明收益。
- `DASHBOARD-001` 把 Snapshot、TASK_BOARD 或浏览器提升为事实源，提供写接口，自动启动 agent/Worktree，或把“并行候选”显示为已授权并行。
- Kimi 前端绕过只读 API 自行读取/修改 TASK 或 Git，或后端为配合具体布局而合并 Review、UA、Accepted、delivery、Closed 等正交状态。
- 目标分支未完全合并、当前工作区不干净、远端出现未核对的同名分支，或清理动作需要强制删除、历史改写、额外发布或未确认路径同步。
