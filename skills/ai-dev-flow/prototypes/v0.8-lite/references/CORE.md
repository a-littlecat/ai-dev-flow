# v0.8 Lite 原型核心规则

## 三档判定

| 档位 | 判定 | TASK | Reviewer |
|---|---|---|---|
| Lite | A/B、低风险、无外部副作用、全部标准可确定性验证 | 不创建 | 禁止 |
| Tracked | 非 Lite 的可隔离仓库改动 | 必须 | 风险触发 |
| Controlled | 外部副作用、真实环境、delivery、发布、不可逆或高风险 authority | 必须 | 交付前强制 |

任一条件未知时按更严格档处理。可回滚不能替代验证，测试通过不能替代用户验收、真实环境证据或 delivery authority。

## 确定性审核闸门

Tracked 命中以下任一项时触发一个隔离只读 Reviewer：核心执行路径、业务文件超过 3 个、历史 P0/P1、跨模块状态变更、用户明确要求独立审查。Controlled 在任何交付动作前强制触发。

Reviewer 输入固定为 TASK、base/diff、允许范围、完成标准和验证证据；输出为 `Passed`、`Needs Fix` 或 `Blocked`，并给出稳定 finding ID 与 P0～P3。Engineer/Repairer 不得修改 Reviewer 结论或自批。

Tracked 命中闸门但 Reviewer 不可用时，只能：

1. 保持 `Blocked`；
2. 在原 authority 内合法升级到有 Reviewer 的 Controlled 流程；
3. 取得用户对独立人工/agent Reviewer 的明确授权。

## 修复与停止

- 基础 repair 预算为 2 轮。
- 只有范围冻结、P0/P1 finding 按稳定 ID 单调减少、严重度不升级且确定性验证改善时，自动授予第 3 轮。
- 第 3 轮是绝对上限；更换模型或 Reviewer 不重置计数。
- 新增 P0/P1、P1 升为 P0、验证退化、范围漂移、无进展或缺 authority 时立即停止并报告。
- 每轮只修当前 findings，修复后必须回到隔离 Reviewer；不得顺手扩建通用调度器、数据库、模型 Adapter 或遥测系统。

## 状态与安全

- TASK 是 Tracked/Controlled 的事实源；看板只是投影。
- Review Passed、验证通过、UA、Accepted、commit、merge、release、Closed 互不推导。
- 未经授权不提交敏感信息，不修改依赖、数据库结构、技术栈或外部状态。
- 任何真实环境、用户观察或 delivery 证据缺失时，不得报告完成。

