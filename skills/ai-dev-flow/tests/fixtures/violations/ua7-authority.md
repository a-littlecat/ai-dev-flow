# FIX-UA7：UA7 授权反例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-UA7`
- `task_type`: `plan`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA7`
- `ua_status`: `Passed`
- `ua_evidence`: `#decision`
- `acceptance_authority`: `Designated Acceptor Confirmed`

## decision

UA7 不能由指定验收人替代用户决策。

## 目标与边界

- 目标：验证 UA7 只能由用户确认。
- 非目标：none
- 允许修改：fixture 文件。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：只产生 UA guard diagnostic。
- 验证命令或检查：对照 manifest 精确集合。

## Outcome

- Base / Diff：base=fixture-base;diff=fixture-base..fixture-head
- 隔离位置：fixture/ua7-authority
- 回滚方式：删除测试 fixture。
- 修改文件：`violations/ua7-authority.md`
- 验证证据：`manifest.json#FIX-UA7`
- Review findings：none
- UA 动作与结果：指定验收人尝试确认 UA7，必须被拒绝。
