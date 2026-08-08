# scripts 说明

v0.6.0 不提供自动脚本。

本目录仅作为未来扩展预留。默认不要执行任何脚本，也不要假设本 Skill 依赖脚本能力。v0.6.0 只增加文档、模板、提示词和路线图。

## v0.7.0 只读 Workflow Contract lint

当前提供只读 CLI：

```powershell
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/TASK-123.md --format human
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format json
```

- target 只能是单个 Markdown TASK，或包含 `docs/tasks/` 的项目根。
- `--format` 只接受 `human` / `json`。
- 退出码：`0` 无 error/violation，`1` 有 workflow violation，`2` 有 parse/invocation error。
- warning 不阻塞，但 lint 通过不代表 Review、用户验收、merge、release 或关闭完成。
- 单 TASK target 不读取 TASK_BOARD；project-root target 会只读投影/比较 `docs/TASK_BOARD.md`。
- project 报告包含 9 字段 expected projection，并可输出 `V_BOARD_DRIFT`、`W_BOARD_MISSING`、`W_BOARD_ORPHAN`、`E_BOARD_PARSE` 等确定性诊断。
- CLI 不提供 `--fix` / `--write`，不会修改 TASK、TASK_BOARD、Git 或外部系统；TASK 始终是事实源。

## v0.8.3 只读 Repair Gate

`repair_gate.py` 把 repair ledger 视为不可信输入，并读取独立 trusted context 与 `policy/repair-campaign.json`，输出 `MechanicallyEligible / Stop / Blocked`；最终 `*Allowed` 只能由持有真实上游证据的 Orchestrator 提升：

- 非 campaign ledger 可继续使用其原 `rc2` policy 验证旧单次 `EscalatedRepair` receipt；campaign 与新 receipt 使用 `rc3` policy，禁止混用；
- 可选 `RepairCampaignAuthority` 绑定 TASK、验收合同、profile、外层 scope manifest 和生效 chain/history head；同 chain 只统计生效后的 patch，后续新 chain 的 AR/ER 都必须推进 state；
- campaign state receipt 必须匹配 trusted context 唯一指定的当前 expected receipt，campaign TASK/验收合同也必须匹配独立 expected 值，并绑定 history head、最新 Review 和 hard-stop snapshot；核心产品连续无进展阈值为 4，Harness 为 5；
- campaign 硬停止 flag 立即阻断，不等待次数耗尽。

```powershell
python -B -X utf8 skills/ai-dev-flow/scripts/repair_gate.py repair-ledger.json --trusted-context trusted-context.json --format human
python -B -X utf8 skills/ai-dev-flow/scripts/repair_gate.py --policy-digest --format json
```

- 只读，不修改 TASK、代码、Git 或外部系统。
- 退出码：`0` 为机械资格成立（仍需 Orchestrator 提升），`1` 为 `Stop`，`2` 为输入/安全门禁 `Blocked`。
- ledger 使用 `ai-dev-flow/repair-ledger-v1`；计数从连续 attempt/Review receipt 链推导，第 3 轮比较结构化 before/after，升级授权绑定 chain/scope/target/attempt。字段由 `TASK_TEMPLATE.md` 和 `CORE.md` 定义。
- trusted context 使用 `ai-dev-flow/repair-trusted-context-v1`，独立提供 expected history head/count 和已确认的 Review/authority receipt；缺少时固定 `Blocked`。
- policy digest 是规范化 JSON policy 的 SHA256，可用于安装副本策略一致性检查；旧 Markdown `POLICY_JSON` 仅作 deprecated 迁移输入。
- receipt 只能机械验证结构、hash 和绑定，不能密码学证明消息发送者身份；该真实性必须由当前对话、harness 或项目事实源提供。
- `MechanicallyEligible` 只表示结构与 trusted context 一致，不代表最终 Allowed、Review、UA、交付或 Closed。

## 后续只读脚本路线图

未来可以考虑添加只读检查脚本：

- `validate_task_board`：检查任务看板字段是否完整。
- `status_machine_check`：检查任务状态流转是否合理。
- `loop_state_summary`：汇总 Loop State，不修改任务状态。
- `batch_candidate_selector`：建议可批量的 A/B 小任务，但不自动执行。
- `wave_conflict_check`：检查候选 Wave 的文件锁、模块锁和依赖关系，但不自动启动并行会话。
- `memory_update_candidate`：从已完成任务中建议 Memory 更新，但不直接写入。
- `github_issue_mapping_preview`：预览 TASK 到 GitHub Issue 的字段映射，但不创建或修改 issue。

可选的后续脚本仍必须默认只读，不能把本 Skill 改成 CLI-heavy 工具。

## 脚本设计原则

- 默认只读。
- 不自动修改业务代码。
- 不自动 merge / push / release / delete。
- 不自动启动多个 agent。
- 不自动创建、关闭或同步 GitHub Issue。
- 执行前说明输入、输出、影响范围。
- 失败时输出错误原因，不做隐式修复。
