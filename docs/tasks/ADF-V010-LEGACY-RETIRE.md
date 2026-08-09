# ADF-V010-LEGACY-RETIRE：退役 Legacy Action Center

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-LEGACY-RETIRE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Draft`
- `review_status`: `Pending`
- `ua_level`: `UA5`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：在 Project Console 真实用户 UA 通过且用户明确同意后，删除仅服务 Legacy Action Center 的入口、状态、样式和测试，并重建 portable runtime。
- 非目标：不删除关系诊断、TASK/Git/Snapshot/SSE/ETag/runtime/console 能力，不自动 release。
- 允许修改：总合同第 11 节明确的 Legacy 文件、相关文档、生成 runtime、测试与任务收据。
- 禁止修改：用户 UA 未通过时的任何 Legacy 删除；手工修改生成 asset/hash；loopback 与只读边界。

## 依赖与授权

- 前置依赖：Project Console Review Passed、自动测试通过、用户真实 UA Passed、用户明确同意删除 Legacy、关系诊断已验证、有回滚 commit。
- Base commit：待用户 UA 后冻结。
- 已有 authority：当前无删除 authority；仅允许保留 Draft 计划。
- 未授权动作：删除 Legacy、merge、release、正式 Skill 同步、Accepted/Closed。
- 执行位置：待门禁满足后创建独立阶段分支。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；删除、公共 UI、生成产物、delivery 风险。
- Reviewer 闸门：Required。
- 停止条件：任一前置门禁缺失；当前仅为计划性 Draft。

## 完成标准与验证

- [ ] 用户真实 UA 与删除授权已写回前置 TASK。
- [ ] Legacy 代码/入口完全移除，network 关系诊断和 Project Console 可用。
- [ ] 文档、生成 runtime 与 manifest 一致；安装运行时无需 Node.js。
- [ ] 后端、前端、集成、Skill 全量测试与独立只读 Review通过；不自动 release。

## Repair Chain Ledger（仅进入 repair 时填写）

- 未进入 repair。

## Outcome

- Base / Diff：未开始。修改文件无；验证未运行；Review/UA Pending。
- 状态边界：Draft / blocked by future UA gate / Uncommitted / Unmerged / Not Released / Not Closed。
- 剩余风险：提前执行会移除用户当前已验收回退入口。
- 下一步：等待 Project Console 真实 UA 和用户明确删除授权。
