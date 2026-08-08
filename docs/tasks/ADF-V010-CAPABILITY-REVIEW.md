# ADF-V010-CAPABILITY-REVIEW：能力驱动的独立 Review 与新 Contract

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-CAPABILITY-REVIEW`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Draft`
- `review_status`: `Pending`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：建立 Harness-neutral 能力要求、Review Recipe、薄 Adapter 与 `adf/v0.10.0` Workflow Contract，使新任务可合法表达 `Review Not Required`。
- 非目标：不批量迁移历史 v0.7 TASK，不重做 Dashboard UI，不把具体 Harness 命令写入核心 policy。
- 允许修改：总合同第 8.2 节列出的 Skill、Contract、Adapter、测试和最小 Dashboard 兼容范围，以及相关 TASK/TASK_BOARD。
- 禁止修改：Runtime Session、Project Console 产品实现、Legacy 删除、release/安装同步。

## 依赖与授权

- 前置依赖：CORE-SPLIT 阶段验证、Review、commit 完成。
- Base commit：待 CORE-SPLIT Head 冻结。
- 已有 authority：依赖满足后的阶段实现、验证、只读 Review、commit、push、Draft PR。
- 未授权动作：merge、release、正式 Skill 同步、自动 Accepted/Closed。
- 执行位置：计划 stacked branch `codex/v010-capability-review`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；公共合同、兼容、核心 Review 语义和 shared component 风险。
- Reviewer 闸门：Required；隔离且只读，无开放 P0/P1。
- 停止条件：前置阶段未完成、需破坏旧 Contract、需让 Adapter 授予核心 authority。

## 完成标准与验证

- [ ] 新 Adapter 接入无需修改核心，generic/codex/kimi-code/opencode/zcode 初版可用。
- [ ] v0.7 TASK 继续解析且不改义；v0.10 TASK 支持 `Required` / `Not Required`。
- [ ] Not Required 可合法完成；Required 在 Accepted/Closed 前仍需 Passed。
- [ ] Brief/Full 选择不依赖模型名；Dashboard 合同、codegen 与兼容测试通过。
- [ ] 全量相关测试、workflow lint、`git diff --check` 和独立只读 Review通过。

## Repair Chain Ledger（仅进入 repair 时填写）

- 未进入 repair。

## Outcome

- Base / Diff：未开始，等待 CORE-SPLIT。
- 修改文件：无。验证未运行；Review/UA Pending。
- 状态边界：Draft / Uncommitted / Unmerged / Not Released / Not Closed。
- 剩余风险：Contract 双读必须保持历史完成语义。
- 下一步：前置阶段收据完成后冻结 base。
