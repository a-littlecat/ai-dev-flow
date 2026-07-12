# BOARD-001：看板漂移样例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `BOARD-001`
- `task_type`: `test`
- `task_class`: `B`
- `lifecycle`: `Ready`
- `review_status`: `Pending`
- `ua_level`: `UA3`
- `ua_status`: `Pending`

## 目标与边界

- 目标：验证 TASK 与看板 lifecycle drift。
- 非目标：none
- 允许修改：fixture 项目。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：只产生 drift 与 orphan diagnostics。
- 验证命令或检查：对照 manifest。
