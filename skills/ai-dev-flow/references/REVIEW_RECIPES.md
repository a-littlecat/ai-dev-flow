# 独立 Review Recipes

选择顺序固定为 `R1 > R2 > R3 > R4 > R5`。先验证能力，再选择 Recipe；不得按 Harness 名称直接放行。

- `R1`：原生隔离上下文 + 原生真只读。必须冻结 diff、稳定 finding ID，并核对 Review 前后工作区。
- `R2`：独立进程 + read-only sandbox。命令参数必须先以当前 `--help` 核对。
- `R3`：独立会话 + 由 Orchestrator 建立的只读 Worktree/副本。副本不得反向写回。
- `R4`：用户明确授权且能力已验证的外部 Harness。跨 Harness 授权必须绑定当前 TASK、冻结 diff 和 Review 范围；授权不能替代外部 Adapter 的上下文/写隔离与读取能力证明。
- `R5`：能力或证据不足。保持 `Pending/Blocked`，不得用主上下文自检冒充独立 Review。

所有可通过 Recipe 都必须满足 `policy/core.json.independent_review`：上下文隔离、冻结 diff、稳定 finding ID，以及 `native_read_only / sandbox_read_only / readonly_copy` 之一；Reviewer 还必须能读取冻结输入。声明矛盾、当前调用证据缺失或外部 Adapter 缺失时进入 R5。Review 结论不授予 UA、commit、merge、release 或 Closed。
