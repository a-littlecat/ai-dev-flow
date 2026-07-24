# 中文术语表

本文件用于把 ai-dev-flow 中常见的英文稳定标识解释成中文。英文标识仍然保留，用于 agent 检索、跨工具协作和文档引用。

## 任务状态

| 中文名称 | 英文标识 | 说明 |
| --- | --- | --- |
| 草稿 | Draft | 需求或任务边界尚未确认。 |
| 可执行 | Ready | 目标、非目标、完成标准、验证方式和执行边界已明确。 |
| 执行中 | In Progress | agent 正在按任务文件工作。 |
| 阻塞 | Blocked | 缺少信息、权限、依赖、用户确认或存在冲突。 |
| 待审查 | Review | 执行完成，等待独立审查。 |
| 需修复 | Needs Fix | 审查发现 P0/P1 或必须修改项。 |
| 已验收 | Accepted | 已按用户动作等级完成必要验收或决策。 |
| 已关闭 | Closed | 任务记录、验收和后续建议均已收口。 |
| 延期 | Deferred | 任务暂不执行，但未来可能恢复。 |
| 已取消 | Cancelled | 用户确认不再执行。 |

## 工作模式

| 中文名称 | 英文标识 | 说明 |
| --- | --- | --- |
| 初始化项目 | init_project | 初始化项目工作流。 |
| 创建任务 | create_task | 把需求拆成任务。 |
| 规划任务 | plan_task | 大任务先写 plan / RFC。 |
| 执行任务 | execute_task | 执行单个任务。 |
| 审查任务 | review_task | 独立审查任务。 |
| 修复任务 | repair_task | 根据审查意见修复。 |
| 关闭任务 | close_task | 按用户动作等级完成验收或决策后关闭任务。 |
| 状态汇总 | status_report | 汇总当前项目状态。 |

## 循环类型

| 中文名称 | 英文标识 | 说明 |
| --- | --- | --- |
| 分拣循环 | triage_loop | 只读分拣任务，推荐下一步、Batch 或 Wave 候选。 |
| 目标循环 | goal_loop | 编排单个任务的执行、验证、审查、修复和验收建议。 |
| 审查-修复循环 | review_repair_loop | 有限次数的审查、修复、复审循环。 |
| 状态循环 | status_loop | 只读状态汇总。 |

## Repair 决策

| 中文名称 | 英文标识 | 说明 |
| --- | --- | --- |
| 自主修复 | AutoRepair | agent 在 policy 预算内自主执行的有界修复；基础 2 轮，第 3 轮需 progress gate。 |
| 停止 | Stop | 当前自主或已授权尝试结束；等待用户裁决，不等于 AI 永久禁修。 |
| 用户裁决 | UserDecisionRequired | 用户选择补证据、缩小范围、人工实现或明确授权有界 AI 修复。 |
| 升级修复 | EscalatedRepair | `Stop` 后由用户明确授权的有限 AI 修复尝试，默认一次，失败回到 `Stop`。 |
| 修复链 | repair_chain_id | 绑定 finding 和 closure contract 的稳定历史；换 TASK 或模型不重置。 |
| 机械资格成立 | MechanicallyEligible | 不可信 ledger 与独立 trusted context 的结构/收据一致；仍需 Orchestrator 用真实上游证据提升为最终 Allowed。 |

## 用户动作等级

| 等级 | 中文说明 |
| --- | --- |
| UA0 | 无需用户验收 |
| UA1 | 用户看摘要确认 |
| UA2 | 用户读文档 / 方案 |
| UA3 | 用户只看验证证据 |
| UA4 | 用户本地运行 |
| UA5 | 真实环境 / 实机业务测试 |
| UA6 | 核心流程 / 回归验收 |
| UA7 | 用户决策 / 高风险确认 |

## 审查严重等级

| 等级 | 中文说明 |
| --- | --- |
| P0 | 阻止合并 / 验收，必须修复 |
| P1 | 高风险，验收前必须修复 |
| P2 | 建议修复，可转后续任务 |
| P3 | 风格或可选建议，不阻塞 |

## 反馈闭环术语

| 中文名称 | 英文标识 | 说明 |
| --- | --- | --- |
| Bug 诊断 | bug_diagnosis | 根因不清时先建立证据、假设和复现信号。 |
| 反馈闭环 | feedback_loop | 从用户反馈到诊断、修复、复测和记录的闭环纪律。 |
| 测试先行 | tdd_task | 先建立 RED / GREEN 行为验证，再做最小实现或修复。 |
| 需求拷问 | requirement_grilling | 对模糊或高风险需求只追问阻塞问题。 |
| 项目语境 | project_context | 长期稳定的项目术语、验证经验和常见误解。 |
| 会话交接 | session_handoff | 跨会话继续任务时的状态、证据和下一步摘要。 |
| 架构巡检 | architecture_review | 只读检查架构阻力、测试缝隙和边界混乱。 |
| 实机测试信号复现 | real_env_signal | 把真实环境失败转成 RED / GREEN / SIGNAL 和 HITL 回传证据。 |
| RED 失败信号 | RED | 当前可观察、可判定的失败现象。 |
| GREEN 通过信号 | GREEN | 修复后应观察到的通过条件。 |
| SIGNAL 证据来源 | SIGNAL | 判断 RED 或 GREEN 的命令、日志、截图、录屏、输出文件或用户步骤。 |
| 用户实机 HITL | human-in-the-loop | agent 无法亲自复现时，由用户在真实环境执行并回传证据。 |
| 回传证据 | returned evidence | 用户提供的日志、截图、录屏、输出文件摘要或脱敏样例。 |
| 临时诊断日志 | temporary diagnostic log | 带唯一前缀、修复后必须清理的临时定位日志。 |
| 测试缝隙 | test seam | 可插入测试、替代验证或可观察信号的位置。 |
| 最小复现 | minimal reproduction | 能触发同一失败的最小输入、步骤或样例。 |
