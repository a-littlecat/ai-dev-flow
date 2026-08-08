# ADF-V010-RUNTIME-CONSOLE-BE：Runtime Session 与 Project Console 后端

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-RUNTIME-CONSOLE-BE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：新增 Harness-neutral Runtime Session、通用 `adf session/status` CLI、只读 `/api/v1/console` 与单一 Queue Engine。
- 非目标：不改变 Snapshot v1，不新增写 API、数据库、消息队列、云服务、遥测或第二套 TASK/Git 引擎。
- 允许修改：总合同第 9 节明确的 backend、contracts、Skill CLI 包装、测试与相关 TASK/TASK_BOARD。
- 禁止修改：Project Console UI、Legacy 删除、项目文件写入、Git/Worktree 写动作、authority 写入。

## 依赖与授权

- 前置依赖：CAPABILITY-REVIEW 阶段完成。
- Base commit：`0b82d7c`（CAPABILITY-REVIEW delivery head）。
- 已有 authority：依赖满足后的阶段实现、验证、只读 Review、commit、push、Draft PR。
- 未授权动作：merge、release、正式 Skill 同步、外部写入、Accepted/Closed。
- 执行位置：计划 stacked branch `codex/v010-runtime-console-be`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；runtime 路径安全、公共 API/schema、跨项目隔离和 shared component 风险。
- Reviewer 闸门：Required；隔离且只读，无开放 P0/P1。
- 停止条件：需要 Dashboard 写 API、外部依赖无独立授权、runtime 可越界或可授予 authority。

## 完成标准与验证

- 完成标准：Runtime Session、Console Builder、CLI、只读 API、合同与规范 Runtime bundle 满足本节全部检查项，且独立 Review 无开放 P0/P1。
- 验证命令或检查：backend/Skill/frontend/integration/browser 全量或直接相关测试、runtime bundle check、workflow lint、diff check 与隔离只读 Review。
- [x] 原子写入、project-id 隔离、路径/symlink 安全、stale/ended/invalid 语义通过测试。
- [x] `session` / `status --watch` 与 API 共用同一 Console Builder。
- [x] `/console` schema、ETag/304、loopback/method allowlist 和敏感字段排除通过。
- [x] Queue 分组与排序正确；多候选不伪造唯一主任务；Snapshot v1 兼容。
- [x] 外部复审修复后的全量相关测试与新独立只读 Review 通过。

## Repair Chain Ledger（仅进入 repair 时填写）

- `ADF-V010-STACKED-EXT-P1-CONSOLE-001`：真实 `ActionEngine` 对 Ready 任务返回 `execute + needs_authority`，旧 Builder 将其送入 human_attention。修复：先按阻断事实 fail-closed，再把 Ready 的真实 execute/actionable 或 execute/needs_authority 明确视为 ready candidate；集成测试直接使用真实 ActionEngine 输出，不伪造 actionable。
- 外部 P2：无 Runtime 时 `runtime_facts_at=null`；ConsoleItem 增加 `status_summary`；ambiguity 只统计显式候选的最高排序并列；active_work 同优先级按最近活动降序；首次 Runtime 目录创建用真实双进程回归证明 race-safe。
- 当前外部修复已吸收 #15 `0e4c2ff`，实现与 fresh backend `204/204`、Skill `119/119`、Runtime bundle `43/43` 已通过。新隔离只读 Review session `019fe236-302c-7371-a686-17336916a8fd` 为 `Passed 0/0/0/0`；Reviewer 独立通过真实 ActionEngine 探针、bundle/codegen、合同同步、workflow lint 与 diff check。其只读沙箱不能创建系统临时目录，因此未在该沙箱内重跑会写临时目录的完整 backend/Skill/integration 测试；动态全量证据来自本阶段主执行环境的 fresh run，不把沙箱限制误报为测试通过。
- 上层首次使用默认 Python 3.10 运行 full integration 时，portable singleton 用例暴露仍断言旧 `human_attention` 的测试债务；现改为验证真实 Ready 任务进入 `ready_queue`。该修复属于 #16，必须在下层重新验证、Review、提交并普通 merge 更新 #17；Python 3.10 的启动失败另以合规 Python 3.13 重跑，不计为产品断言失败。
- Follow-up 新隔离只读 Review session `019fe250-5410-7743-a734-2758ad74ebb7` 为 `Passed 0/0/0/0`。主执行环境 Python 3.13 targeted portable singleton `1/1` 通过；Reviewer 沙箱因禁止创建 `TemporaryDirectory` 未动态复跑该用例，但独立完成真实 source/installed bundle `ActionEngine → ConsoleBuilder` 内存探针、manifest SHA256、语法、lint 与 diff 检查。

- Attempt AR-1：独立只读 Review Round 1 为 `Needs Fix 0/5/0/0`；Reviewer 进程未向 Harness 暴露可引用 session id，收据标记为 `harness-not-exposed`。
- RED：目录在检查前可经 symlink/Junction 逃逸；未来时间戳可长期保持 live；并发 start 存在覆盖窗口；Queue Engine 会压缩同任务多动作并使用非正式 eligibility；规范 Skill Runtime 尚未包含 Stage 3 后端与合同。
- GREEN：目录逐级创建并拒绝 symlink/Junction/reparse；所有时间轴限制最大 300 秒时钟偏差；按 session 使用原子互斥创建，非 replace 并发仅一方成功；保留全部 actions，正式处理 `actionable/blocked/needs_authority/unknown/not_applicable`；重建 43/43 文件 Runtime bundle 并纳入三个 schema。
- SIGNAL：Windows Junction 外部目标零写入、三类未来时间戳、并发双 start、真实 Action Engine、多动作降级、临时已安装布局的 `session/status/status --watch` 以及便携 `/api/v1/console` 均有回归测试并通过。后端 `200/200`（普通 symlink 权限 skip 2）、Skill `113/113`、Vitest `95/95`、Playwright `96/96`；跨 autocrlf bundle 一致性通过。
- 基线隔离：integration artifact guard 与 real state-matrix 的隐藏 SVG 节点仍是 Stage 0 已登记债务；本阶段不修改冻结 artifact baseline 或 Legacy UI 几何。
- Round 2：session `019fe16a-c367-7173-8584-504ea776483b` 为 `Needs Fix 0/1/2/0`。首轮未来时间戳、并发覆盖、多 action/eligibility 和安装布局四项 Closed；reparse 点在 Python 3.11 缺少 `Path.is_junction` 时仍 Open。新增 `R2-P1-001`、`R2-P2-001`、`R2-P2-002`。
- Attempt AR-2 RED：Python 3.11 Windows 无 `Path.is_junction`，Junction 可漏检；强制终止会遗留永久阻塞 `.lock`；无 runtime session 时 `recent_changes` 漏掉 `changed_task_ids`。
- GREEN：增加 `FILE_ATTRIBUTE_REPARSE_POINT` 兼容回退；锁改为进程退出自动释放的 OS 非阻塞文件锁，锁文件可安全留存复用；Snapshot 与 runtime 变更由同一 Builder 合并、确定性排序并限 20 条，schema 同步支持 `task_snapshot`。
- SIGNAL：强制禁用 `Path.is_junction` 的真实 Windows Junction 外部零写入用例通过（本机无 Python 3.11 runtime）；终止持锁子进程后同 session 可恢复且并发 winner 语义不变；无 session Snapshot 变更和合同校验通过。后端 `202/202`（skip 2）、Vitest `95/95`，安装布局/跨 autocrlf/便携 Console API 目标集 `3/3`，Runtime bundle `43/43`。
- Round 3：session `019fe173-997c-7ea1-af34-37c61d437857` 在显式 read-only sandbox 中返回 `Passed 0/0/0/0`；`R2-P1-001`、`R2-P2-001`、`R2-P2-002` 全部 Closed，无新增 finding。Reviewer 明确记录本机没有 Python 3.11，Junction 证据是“真实 Windows Junction + Python 3.11 API 缺失路径模拟”，不伪装成 3.11 实跑。

## Outcome

- Base / Diff：base=21ea7ed;diff=21ea7ed..working-tree
- 隔离位置：`codex/v010-runtime-console-be` / `D:/open-source/ai-dev-flow-wt/v010-runtime-console-be`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 CAPABILITY-REVIEW 历史。
- 修改文件：新增 Runtime Session store、Console Builder、通用 CLI/Skill 包装、Console/API 合同与 be003 测试；扩展 loopback `/api/v1/console` 和 runtime bundle 文件数合同；仅机械更新生成类型/校验器，不实现 Project Console UI。
- 验证证据：外部修复 fresh be003 `21/21`（skip 2）、backend `204/204`（skip 2）、Skill `119/119`、Runtime bundle `43/43`、codegen check 与 `git diff --check` 已通过；frontend 与 integration 待在上层 UI 合并后执行完整验证。完整 integration 已知边界为 `51/52`，唯一 artifact guard 失败不得误报为全绿。
- Review findings：历史 Round 1 `Needs Fix 0/5/0/0`；Round 2 session `019fe16a-c367-7173-8584-504ea776483b` 为 `Needs Fix 0/1/2/0`；Round 3 session `019fe173-997c-7ea1-af34-37c61d437857` 为 `Passed 0/0/0/0`。本轮外部修复后的新隔离只读 Review session `019fe236-302c-7371-a686-17336916a8fd` 为 `Passed 0/0/0/0`，无开放 finding。
- Delivery：初始 implementation=`f7f3a63`、receipt=`587bdc1`；外部修复 implementation=`46a16b7`；branch `codex/v010-runtime-console-be` 待推送当前收据；Draft PR [#16](https://github.com/a-littlecat/ai-dev-flow/pull/16)，base=`codex/v010-capability-review`。
- 状态边界：External Repair Follow-up Review Passed / UA3 Pending / Current Follow-up Uncommitted / Draft PR #16 / Unmerged / Not Released / Not Synced / Not Accepted / Not Closed。
- 剩余风险：runtime 状态不能覆盖 TASK/Git 或授予动作权限。
- 下一步：提交/push #16 follow-up，再以普通 merge 更新 #17，并在 #17 用 Python 3.13 重跑 full integration。禁止提前进入正式用户 UA。
