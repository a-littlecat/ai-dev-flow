# ADF-V010-RUNTIME-CONSOLE-BE：Runtime Session 与 Project Console 后端

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-RUNTIME-CONSOLE-BE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Needs Fix`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
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
- [x] 外部 findings 修复后的全量相关测试与 same-Harness 内部隔离只读 Review 通过；跨 Harness 外部复审仍 Pending。

## Repair Chain Ledger（仅进入 repair 时填写）

- `ADF-V010-STACKED-EXT-P1-CONSOLE-001`：真实 `ActionEngine` 对 Ready 任务返回 `execute + needs_authority`，旧 Builder 将其送入 human_attention。修复：先按阻断事实 fail-closed，再把 Ready 的真实 execute/actionable 或 execute/needs_authority 明确视为 ready candidate；集成测试直接使用真实 ActionEngine 输出，不伪造 actionable。
- 外部 P2：无 Runtime 时 `runtime_facts_at=null`；ConsoleItem 增加 `status_summary`；ambiguity 只统计显式候选的最高排序并列；active_work 同优先级按最近活动降序；首次 Runtime 目录创建用真实双进程回归证明 race-safe。
- 当前外部修复已吸收 #15 `0e4c2ff`，实现与 fresh backend `204/204`、Skill `119/119`、Runtime bundle `43/43` 已通过。新隔离只读 Review session `019fe236-302c-7371-a686-17336916a8fd` 为 `Passed 0/0/0/0`；Reviewer 独立通过真实 ActionEngine 探针、bundle/codegen、合同同步、workflow lint 与 diff check。其只读沙箱不能创建系统临时目录，因此未在该沙箱内重跑会写临时目录的完整 backend/Skill/integration 测试；动态全量证据来自本阶段主执行环境的 fresh run，不把沙箱限制误报为测试通过。
- 上层首次使用默认 Python 3.10 运行 full integration 时，portable singleton 用例暴露仍断言旧 `human_attention` 的测试债务；现改为验证真实 Ready 任务进入 `ready_queue`。该修复属于 #16，必须在下层重新验证、Review、提交并普通 merge 更新 #17；Python 3.10 的启动失败另以合规 Python 3.13 重跑，不计为产品断言失败。
- Follow-up 新隔离只读 Review session `019fe250-5410-7743-a734-2758ad74ebb7` 为 `Passed 0/0/0/0`。主执行环境 Python 3.13 targeted portable singleton `1/1` 通过；Reviewer 沙箱因禁止创建 `TemporaryDirectory` 未动态复跑该用例，但独立完成真实 source/installed bundle `ActionEngine → ConsoleBuilder` 内存探针、manifest SHA256、语法、lint 与 diff 检查。
- `ADF-V010-EXT-R2-P1-001`：`ambiguity` 曾把 active/human/Ready 混为一个主候选概念，与前端 Ready 区域语义冲突。修复为 `ready_ambiguity`，仅统计 Ready 最高语义排名并列，稳定 `task_id` 仅用于展示排序而不破坏并列；真实 ActionEngine + live Runtime 链路覆盖 `active=1/ready=2` 与 `active=1/ready=0`。
- `ADF-V010-EXT-R2-P1-002`：新增按需 `RUNTIME_SESSION_USAGE.md`、显式 heartbeat CLI、结构化 command bridge 与五个 Hook；Codex session `019fe35f-012a-7460-af50-493f3b3f646a` 与 Kimi Code session `session_9844ef5a-b477-450a-a622-3a597815aac5` 均亲自执行 9 条命令，实际观测 `active_work → active_work → human_attention → ended`。OpenCode 在命令执行前因本机 CodingPlan 过期 exit 1，不记为通过证据。
- 本轮 P2：`adf.py` 与 `dashboard.py` 共用同一 Runtime Bundle manifest/SHA256 预检，缺 manifest 与篡改 runtime 均在 import/写 Runtime 前 exit 2；Ready 文案收敛为“可以作为下一项开始 / 尚未授权自动执行 / 开始执行任务”；`source_kinds` 只保留实际参与当前卡片的 TASK/Git/Runtime。历史 Passed 收据未被用于本轮 diff。
- 本轮新隔离只读 Review：首次进程 184 秒超时无结论，不计通过；重跑 session `019fe369-bbb2-7de3-b9f9-724dfe22ea6f` 在 `sandbox=read-only` 中审查 base `626e65d` 到当前完整 diff，结论 `Passed 0/0/0/0`。当前状态改为 `Review Passed / UA3 Pending`；Review 不授予 merge/release/同步/Accepted/Closed。
- `ADF-V010-EXT-R3-P1-001`：Grok 外部只读复审 session `019fe6d7-ffa2-7272-92a8-e24ee5779860` 发现真实 `ActionEngine` 对无 live session 的 In Progress 任务返回 `continue + needs_authority`，旧 Builder 在 lifecycle 分支前按通用 `needs_authority` 错送 `human_attention`。修复为显式 `user_decision` 仍优先进入人工注意、In Progress 无 session 进入 `active_work`，其余缺 authority 再进入 `human_attention`；回归直接使用真实 ActionEngine 并断言 `continue + needs_authority / active_work=1 / human_attention=0`。
- 同轮 P2/P3：原空 actions 的 In Progress 断言已替换为真实 ActionEngine 链路；portable preflight 集成现同时参数化 `adf.py` 与 `dashboard.py`，两入口的 missing manifest 与 tampered runtime 均在创建 Runtime 前 exit 2。修复后 fresh Console Builder `12/12`、portable runtime `4/4`、Skill `121/121`、bundle `43/43`、target lint `0/0/0` 通过；backend full `204 passed / 2 skipped / 1 known baseline failed`，唯一失败仍为未触及的 Windows non-recursive native event 用例。当前等待 GPT Pro 对冻结远端完整 head 复审，不沿用旧 Passed 收据。
- 修复提交 `71c452644c750639515139000c26ab746ae07679` 的 Grok fresh 外部只读复审 session `019fe6e3-b6ad-7aa0-bb63-cfd8248f6601` 为 `Passed 0/0/0/0`，Reviewer 亲自完成真实 ActionEngine 队列探针、两入口四种 preflight 失败探针及 be003 定向测试。Kimi 在同一 head 完成静态检查并确认合同差异仅为换行后，因本计费周期额度耗尽返回 403，未能形成终局 receipt，明确不计通过；因此整体 External Re-review 仍 Pending。
- Reviewer authority 更新：用户明确取消 Kimi 复审要求，改由 GPT Pro 作为第二外部 Reviewer。既有 Kimi 403 仅保留为历史事实，不再是当前门禁；GPT Pro 必须绑定当前远端完整 commit SHA 并输出 Passed / Needs Fix / Blocked，固定版本确认失败不计 Review。
- `ADF-V010-PR16-P1-001`：GPT Pro 对冻结范围 `8922238cff30d85d66919740d2c714e2a6aca39d..5483bfc33c0d51c8116a35f0f03d74203d7d3c85` 给出 `Needs Fix 0/1/0/0`。公开 CLI 原可写入 `phase=done / ended_at=null / end_reason=null`，Builder 随后仍把 task 加入 `assigned`，导致 TASK 从全部队列消失；`heartbeat` 还能续活该隐藏态。PR #17 自身差异在 `5483bfc..95b43ba` 获得 `Passed 0/0/0/0`，但完整 stack 继承此 P1，故不进入 UA。
- 修复提交 `4c8dcb7114fe0d8fcf3053846a3794cedf14fd09`：`done` 改为仅允许 `end()` 产生；CLI `start/update --phase done` 均 exit 2；Store 与 Runtime Session Schema 同时约束终态字段；Builder 对异常 live/done 增加第二道 invalid 投影且不写入 `assigned`；真实 ActionEngine + 磁盘篡改回归证明异常会话进入 `stale_sessions` 的同时 Ready TASK 仍进入 `ready_queue`，公开 heartbeat exit 2。fresh backend `210/210`（skip 2）、Skill `121/121`、build/portable integration `12/12`、定向 `27/27`（skip 2）与 Runtime bundle `43/43` 全部通过；GPT Pro 对新冻结 head 的外部复审仍 Pending，本记录不自行关闭 finding。
- Codex 隔离预检首次审查 `5483bfc..4c8dcb7` 为 `Needs Fix 0/1/0/0`：Schema 的 `ended_at` 只约束 string，空字符串仍可通过，和 Store 不一致。`26c6d43088e5a51c59aae1e4bfb905df24410383` 为 `ended_at` 增加 `minLength=1`，并分别覆盖空时间、空原因和合法 end 产物；第二次冻结预检 `5483bfc..26c6d43` 为 `Passed 0/0/0/0`，实际检查 source/bundle 一致、manifest 43 files 和公开链路。该预检不冒充 GPT Pro，外部 finding 仍等待 GPT Pro 关闭。
- #17 首次吸收 `6ed794a` 后的 fresh Vitest 为 `108/109`：Builder 防御分支新写入 `INVALID_SESSION`，使前端固定原因码集合增至 8。该问题归属 #16，`a8cbc4a3bd41e921fbe51fc03c58b2502f70909a` 改为复用已有且具用户文案的 `INVALID_RUNTIME_SESSION`，并在 Builder 防御测试中固定该输出；定向 be003 `27/27`（skip 2）、bundle 43-file check 与 diff check 通过。失败证据未被误报为全绿，#17 必须重新 merge 后复跑。
- 最终 Codex 隔离预检发现 `ADF-V010-FINAL-P2-001`：真实磁盘无效记录仍由 Store 输出 `INVALID_SESSION`，模拟防御虽已统一但公共链路会让前端退化为未知条件。`5970ff5de04d9ccd4cf4deff808346800ff83d58` 将 Store 无效记录统一为 `INVALID_RUNTIME_SESSION`，并在真实磁盘篡改 → Store → Builder 测试中断言公开 `why_now_codes`；定向 be003 `27/27`（skip 2）和 Runtime bundle `43/43` 通过。短范围关闭复审 `3f9865f..7bd4bb6` 为 `Passed 0/0/0/0`，P2 Closed；该 Codex 预检不替代 GPT Pro 对完整新 head 的外部门禁。

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

- Base / Diff：base=21ea7ed;diff=21ea7ed..981079a
- 隔离位置：`codex/v010-runtime-console-be` / `D:/open-source/ai-dev-flow-wt/v010-runtime-console-be`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 CAPABILITY-REVIEW 历史。
- 修改文件：新增 Runtime Session store、Console Builder、通用 CLI/Skill 包装、Console/API 合同与 be003 测试；扩展 loopback `/api/v1/console` 和 runtime bundle 文件数合同；仅机械更新生成类型/校验器，不实现 Project Console UI。
- 验证证据：本轮 terminal-state 修复 fresh 定向 `27/27`（skip 2）、backend `210/210`（skip 2）、Skill `121/121`、build/portable integration `12/12`、Runtime bundle `43/43`、codegen/build 与 `git diff --check` 已通过；frontend 与 full integration 在 #17 吸收新 #16 head 后复跑。历史 full integration 失败边界不得误报为全绿。
- Review findings：GPT Pro 当前结论仍为 `Needs Fix 0/1/0/0`，开放 finding=`ADF-V010-PR16-P1-001`；实现已按四层终态不变量修复。最终 Codex 短范围预检为 `Passed 0/0/0/0`，但外部关闭权仍属于 GPT Pro 对新冻结范围的复审。
- Delivery：本轮最终 implementation=`5970ff5de04d9ccd4cf4deff808346800ff83d58`；branch `codex/v010-runtime-console-be`；Draft PR [#16](https://github.com/a-littlecat/ai-dev-flow/pull/16)，base=`codex/v010-capability-review`。最终 GPT Pro 复审 head 以包含本收据的后续冻结提交为准，不把 implementation SHA 冒充最终 reviewed head。
- 状态边界：Grok 历史 External Re-review Passed / GPT Pro Needs Fix / Overall External Re-review Needs Fix / UA3 Pending / Draft PR #16 / Unmerged / Not Released / Not Synced / Not Accepted / Not Closed。
- 剩余风险：runtime 状态不能覆盖 TASK/Git 或授予动作权限。
- 下一步：推送包含本收据的新冻结完整 head，并由 GPT Pro 对新 base/head 做外部只读复审；在其关闭 P1 前不得进入正式用户 UA。
