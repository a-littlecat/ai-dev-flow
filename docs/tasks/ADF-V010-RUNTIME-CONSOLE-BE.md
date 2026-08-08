# ADF-V010-RUNTIME-CONSOLE-BE：Runtime Session 与 Project Console 后端

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-RUNTIME-CONSOLE-BE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Draft`
- `review_status`: `Pending`
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
- Base commit：待前置阶段 Head 冻结。
- 已有 authority：依赖满足后的阶段实现、验证、只读 Review、commit、push、Draft PR。
- 未授权动作：merge、release、正式 Skill 同步、外部写入、Accepted/Closed。
- 执行位置：计划 stacked branch `codex/v010-runtime-console-be`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；runtime 路径安全、公共 API/schema、跨项目隔离和 shared component 风险。
- Reviewer 闸门：Required；隔离且只读，无开放 P0/P1。
- 停止条件：需要 Dashboard 写 API、外部依赖无独立授权、runtime 可越界或可授予 authority。

## 完成标准与验证

- [ ] 原子写入、project-id 隔离、路径/symlink 安全、stale/ended/invalid 语义通过测试。
- [ ] `session` / `status --watch` 与 API 共用同一 Console Builder。
- [ ] `/console` schema、ETag/304、loopback/method allowlist 和敏感字段排除通过。
- [ ] Queue 分组与排序正确；多候选不伪造唯一主任务；Snapshot v1 兼容。
- [ ] 不新增外部 Python 依赖；全量相关测试与独立只读 Review通过。

## Repair Chain Ledger（仅进入 repair 时填写）

- 未进入 repair。

## Outcome

- Base / Diff：未开始，等待 CAPABILITY-REVIEW。
- 修改文件：无。验证未运行；Review/UA Pending。
- 状态边界：Draft / Uncommitted / Unmerged / Not Released / Not Closed。
- 剩余风险：runtime 状态不能覆盖 TASK/Git 或授予动作权限。
- 下一步：前置阶段完成后冻结 base。
