# FIX-EXT：扩展反例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-EXT`
- `task_type`: `test`
- `task_class`: `B`
- `lifecycle`: `Ready`
- `review_status`: `Pending`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `extensions_optional`: `example.optional@1`
- `extensions_required`: `example.required@1`

## 目标与边界

- 目标：验证未知 optional 与 required extension 的不同处理。
- 非目标：none
- 允许修改：fixture 文件。
- 禁止修改：扩展 Registry。

## 完成标准与验证

- 完成标准：保留两个扩展并产生精确 warning/violation。
- 验证命令或检查：对照 manifest。
