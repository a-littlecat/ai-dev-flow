# v0.8-lite 原型关闭收据

- 关闭原因：LEAN-002 整体独立 Review 为 `Blocked`，存在 `LEAN002-P1-001` 与 `LEAN002-P1-002` 两项 P1。
- 当前行为：原型从未接入现行 `skills/ai-dev-flow/SKILL.md`，不得再显式激活或作为 v0.8 实施入口。
- 保留方式：原型两文件原样保留为 `V08-LEAN-EVAL-002` 的 hash-bound 评估输入，便于从当前 commit 复算 scorer。
- 状态边界：保留评估输入不代表原型通过 Review、UA、Accepted、发布或生效。
- 后续动作：不创建 LEAN-003；若未来平台可提供精确模型/version 与 call receipts，且用户重新授权新的评估预算，应使用新 evaluation ID 从头冻结，不得合并本次 ledger。
