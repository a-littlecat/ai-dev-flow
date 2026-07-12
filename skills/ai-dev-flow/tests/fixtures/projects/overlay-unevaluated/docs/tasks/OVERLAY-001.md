# OVERLAY-001：Overlay 样例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `OVERLAY-001`
- `task_type`: `test`
- `task_class`: `C`
- `lifecycle`: `Ready`
- `review_status`: `Pending`
- `ua_level`: `UA3`
- `ua_status`: `Pending`

## 目标与边界

- 目标：验证 Overlay 在 CONTRACT-007 前保持未求值。
- 非目标：none
- 允许修改：fixture 项目。
- 禁止修改：核心规则。

## 完成标准与验证

- 完成标准：只产生 overlay unevaluated warning。
- 验证命令或检查：对照 manifest。
