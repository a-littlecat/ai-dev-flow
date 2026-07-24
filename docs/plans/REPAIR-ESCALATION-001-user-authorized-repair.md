# REPAIR-ESCALATION-001：用户授权修复通道实施计划

## 背景

现行 v0.8 规则把第 3 轮写成 repair 的“绝对上限”。这能阻止 AI 无限自动重试，但也错误地把“自主循环上限”扩大成“AI 此后不得再改代码”。结果是：即使用户已经了解风险并明确授权，agent 仍可能机械拒绝，只能要求人工亲自修改。

同时，旧记录常把复审、验收、补证据、同步 TASK 收据和实际修复都叫“轮次”，以及通过更换 TASK 重新计数。这会让预算既容易被无效动作耗尽，又容易被换任务绕过。

## 推荐方案

保留 2 轮基础自动修复和有条件的第 3 轮，但把 3 明确定义为 `AutoRepair` 自主循环上限。达到 `Stop` 后进入“用户裁决”，用户可明确授权一个有边界的 `EscalatedRepair` 尝试，默认一次；失败后回到 `Stop`，不得自动连跑。

修复预算绑定 `repair_chain_id + finding_ids + closure_contract_hash`，不绑定 TASK ID。更换 TASK 或模型不重置历史。

## 实施范围

1. 更新 `SKILL.md + CORE.md` 的默认运行时规则与 `POLICY_JSON`。
2. 更新活跃说明、模板、术语、迁移和安全文档，移除“超限只能人工写代码”的冲突表述。
3. 新增只读 `repair_gate.py`：
   - 只机械判定 `MechanicallyEligible / Stop / Blocked`；
   - 机械资格只输出 eligible mode、下一尝试 ID（`AR-*` / `ER-*`）和 policy digest；
   - 最终 `AutoRepairAllowed / ExtendRound3 / EscalatedRepairAllowed` 只能由持有真实对话、harness 或只读项目证据的 Orchestrator 提升并写回 TASK；
   - 不修改 TASK、代码、Git 或外部系统。
4. 增加回归测试，覆盖换 TASK/模型不重置、第三轮 progress gate、用户授权升级修复和外部副作用硬阻断。
5. 版本进入未发布 `0.8.2` 开发线；不创建 tag / Release。
6. 源仓验证和独立只读 Review 通过后，同步用户已确认存在的本机 Skill 副本，并以逐文件 SHA256 证明一致。
7. 把 CADCat 项目中与 repair 上限直接冲突的规则同步为同一语义；不改业务代码。

## 关键语义

- 一轮 repair：针对冻结 finding 做出意图改变验收结论的 patch，直到下一次独立复审。
- 不计轮次：只读 Review、无 patch 的 UA、诊断取证、原样重跑测试、TASK/看板收据同步、纯记录纠错。
- 第 3 轮 progress：至少一个冻结 closure criterion 从 RED 变 GREEN；不得有 GREEN 变 RED；不得因本 patch 新增阻断 finding；固定证据覆盖向量必须增加。
- 超限后用户可以授权 AI：必须冻结目标、允许文件、RED/GREEN、干净基线、Reviewer 能力和次数；不可逆外部副作用仍不得自动重试。
- 纯记录不一致默认 P2/P3；只有可能授权不安全动作或掩盖阻断 finding 时才升级为 P1。

## 风险与回退

- 风险：升级通道被误用成无限循环。控制：ledger 视为不可信，由独立 trusted context 锚定历史与授权；每次授权默认仅 1 次，失败回到 `Stop`，历史计数不清零。
- 风险：新旧项目规则不一致。控制：源仓先通过测试和 Review，再精确同步已有副本与 CADCat 规则。
- 风险：旧 v0.8 冻结原型失去审计意义。控制：不修改 `prototypes/v0.8-lite/**` 和 `evaluations/v0.8/**`。
- 回退：恢复本任务工作树 diff；本机副本可从同步前哈希清单恢复。不使用破坏性 Git 命令。

## 验证

```powershell
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py" -v
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/REPAIR-ESCALATION-001.md --format human
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format human
python -B -X utf8 C:\Users\92336\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/ai-dev-flow
git diff --exit-code 070267326146924f3e05a94b67c16825bc1777de -- evaluations/v0.8 skills/ai-dev-flow/prototypes/v0.8-lite
git diff --check
```

独立 Reviewer 必须在只读隔离环境中审查 base..worktree diff；P0/P1 未关闭不得同步本机 Skill。

## 验收与交付授权

- 2026-07-24 用户明确确认 UA2 验收通过，并授权精确提交当前任务 diff、推送 `codex/repair-escalation-001` 分支。
- 本授权不包含 merge、tag、GitHub Release、删除、历史改写或 `Closed`。
