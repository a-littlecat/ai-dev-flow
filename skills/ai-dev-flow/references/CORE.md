# ai-dev-flow 核心规则兼容入口

> 本文件自 v0.10 开发线起不再是 canonical policy，也不在默认加载路径中。机器可读规则位于 `../policy/`。

## Canonical policy

- 路由、Review 触发、安全与 unknown 分类：`policy/core.json`
- 普通 Repair：`policy/repair-basic.json`
- 显式严格自动化 / Repair Campaign：`policy/repair-campaign.json`

新代码必须直接读取 JSON，不得从 Markdown 复制或解析规则。旧版 `CORE.md` 中的 `POLICY_JSON` 仅作为迁移输入被 `scripts/policy_loader.py` 和 `repair_gate.py` 兼容读取，并会产生 deprecated 警告。

## 路由摘要

按 `policy/core.json` 的顺序：

1. 命中 Controlled 条件则进入 `Controlled`。
2. 完整满足 Lite 条件则输出 `DoNotUseSkill`。
3. 其他已知输入进入 `Tracked`。
4. 本地可发现的 unknown 先 `InspectAndResolve` 并重新路由；只要仍未解析，最终仍为 `Blocked`，不能进入 Lite/Tracked/Controlled 或授予动作资格。authority、外部证据或规则冲突 unknown 直接为 `Blocked`。

摘要只帮助人阅读；冲突时以 JSON 为准。

## 事实源与状态

- Tracked / Controlled 的 TASK 是细粒度事实源；TASK_BOARD 只是投影。
- 当前 Workflow Contract 仍为 `adf/v0.7.0`；历史 TASK 不在本阶段迁移。
- 自动验证、Review、UA、Accepted、commit、merge、delivery、release 和 Closed 相互独立。
- lint 通过只证明可确定的结构规则通过，不等于 Review 或验收完成。

## 权限与证据

- 用户要求结果不自动授权 merge、push、release、删除、外部同步或 Closed。
- 必需真实环境证据缺失时保持 Blocked，不能用单元测试冒充。
- Dashboard、TASK_BOARD、runtime 投影或 hash 都不能授予 authority。
- 不明确的 authority 和外部证据不能猜测为安全值。

## Repair 加载边界

- 普通 finding：读取 `repair-basic.json` 与 `REPAIR_BASIC.md`。
- 只有显式严格自动化预设、长时间无人值守、Skill 自修改、安全、数据迁移、不可逆操作、正式发布或用户明确要求严格 Campaign 时，才读取 `repair-campaign.json` 与 `REPAIR_CAMPAIGN.md`。
- `repair_gate.py` 是严格 receipt-backed 路径的只读机械判定器；它不会证明用户身份或自行授予 `*Allowed`。
- 历史 rc2/rc3 Markdown policy 仍可在迁移期只读验证，但不是新 policy 的事实源。
