# ADF-V010-RELEASE：发布 ai-dev-flow v0.10.0

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-RELEASE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Draft`
- `review_status`: `Pending`
- `ua_level`: `UA7`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：在全部前置阶段完成且取得显式发布 authority 后，统一 0.10.0 版本、完成全量验证、发布、安装同步 parity 与回滚收据。
- 非目标：不因代码完成自动推导 tag、Release、正式安装同步、Closed 或删除备份。
- 允许修改：总合同第 12 节列出的版本、兼容声明、release notes、生成资产和收据范围。
- 禁止修改：无发布授权时的任何发布/安装动作；删除旧安装备份；force push、历史改写、未经确认的 deploy。

## 依赖与授权

- 前置依赖：LEGACY-RETIRE 完成；全部程序级 DoD 满足；用户显式发布授权。
- Base commit：待前置阶段 Head 冻结。
- 已有 authority：当前仅允许保留 Draft 计划，不存在发布 authority。
- 未授权动作：merge release PR、tag、GitHub Release、正式安装同步、删除备份、Closed。
- 执行位置：待授权后创建独立 release 分支。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；release、external sync、delivery、不可逆外部状态风险。
- Reviewer 闸门：Required；发布前无开放 P0/P1 且完整验证通过。
- 停止条件：缺发布 authority、版本/manifest/兼容声明不一致、真实安装或多 Harness 验证缺失。

## 完成标准与验证

- [ ] Skill/Dashboard/Contract/runtime/release notes 版本与兼容声明一致。
- [ ] 总合同第 12.4 节全部自动与真实环境验证通过。
- [ ] 独立只读 Review无开放 P0/P1，用户显式发布 authority 已记录。
- [ ] 发布、安装 parity 和回滚路径均有精确收据；旧备份保留。
- [ ] Release、Delivered、Closed 分别记录，不互相推导。

## Repair Chain Ledger（仅进入 repair 时填写）

- 未进入 repair。

## Outcome

- Base / Diff：未开始。修改文件无；验证未运行；Review/UA Pending。
- 状态边界：Draft / Uncommitted / Unmerged / Not Released / Not Delivered / Not Closed。
- 剩余风险：发布与正式安装会改变外部状态，必须逐项核对 authority 和回滚。
- 下一步：等待 LEGACY-RETIRE 完成及用户显式发布授权。
