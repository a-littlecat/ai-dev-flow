# FIX-CLOSE：关闭授权反例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-CLOSE`
- `task_type`: `document`
- `task_class`: `A`
- `lifecycle`: `Closed`
- `review_status`: `Passed`
- `ua_level`: `UA1`
- `ua_status`: `Passed`
- `ua_evidence`: `#ua`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `Denied`

## ua

用户确认了验收，但未授权关闭。

## 目标与边界

- 目标：验证关闭授权被拒绝。
- 非目标：none
- 允许修改：fixture 文件。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：关闭授权产生精确 diagnostic。
- 验证命令或检查：对照 manifest 精确集合。

## Outcome

- Base / Diff：base=fixture-base;diff=fixture-base..fixture-head
- 修改文件：`violations/close-authority.md`
- 验证证据：`manifest.json#FIX-CLOSE`
- Review findings：none
- UA 动作与结果：UA1 已通过。
