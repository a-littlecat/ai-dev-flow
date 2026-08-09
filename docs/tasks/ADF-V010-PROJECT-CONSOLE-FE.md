# ADF-V010-PROJECT-CONSOLE-FE：Project Console 默认入口

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-PROJECT-CONSOLE-FE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Draft`
- `review_status`: `Pending`
- `ua_level`: `UA5`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：默认入口改为只读 Project Console，首屏准确展示用户待处理、活跃工作、Ready Queue、阻塞、最近变化和数据新鲜度。
- 非目标：不让前端重排队列，不执行命令或写 TASK/Git/runtime，不在用户 UA 前删除 Legacy Action Center。
- 允许修改：总合同第 10.2 节列出的 frontend、console schema/codegen、测试、design QA 与相关 TASK/TASK_BOARD。
- 禁止修改：暂时删除 Action Center、overview、graph 或旧回退测试；新增写接口或 authority 操作。

## 依赖与授权

- 前置依赖：RUNTIME-CONSOLE-BE 阶段完成。
- Base commit：待前置阶段 Head 冻结。
- 已有 authority：依赖满足后的实现、自动验证、真实浏览器检查、只读 Review、commit、push、Draft PR。
- 验收合同：`requires_user_observation=true`；`acceptance_authority=user_only`；`designated_acceptor_allowed=false`。这些是 v0.10 阶段合同要求，在当前 v0.7 Contract 中以正文冻结，不能伪写成当前已获得的 authority。
- 未授权动作：代替用户 UA、Accepted、Closed、Legacy 删除、merge、release、正式 Skill 同步。
- 执行位置：计划 stacked branch `codex/v010-project-console-fe`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；公共 UI、真实用户观察、shared component、delivery 风险。
- Reviewer 闸门：Required；自动化最多推进到 `Review Passed / UA Pending / Candidate Ready`。
- 停止条件：无法保留 Legacy 回退、真实项目事实被伪造、需要用户体验判断或用户未授权删除旧入口。

## 完成标准与验证

- [ ] 默认 console；network 与 legacy 保持可用。
- [ ] human attention 优先，live/declared/stale 明确区分，多候选不伪造唯一行动。
- [ ] 数据来源、新鲜度、错误/stale 状态有可访问文本；前端不重新排序。
- [ ] `npm run verify`、真实浏览器、集成测试与独立只读 Review通过。
- [ ] 在真实 CADCat 上完成总合同第 10.11 节用户验收；用户未确认前保持 UA Pending。

## Repair Chain Ledger（仅进入 repair 时填写）

- 未进入 repair。

## Outcome

- Base / Diff：未开始，等待 RUNTIME-CONSOLE-BE。
- 修改文件：无。验证未运行；Review Pending；UA5 Pending且 authority=`user_only`。
- 状态边界：Draft / Uncommitted / Unmerged / Not Released / Not Closed。
- 剩余风险：自动化和 Design QA 不能替代真实日常入口体验。
- 下一步：前置阶段完成后冻结 base。
