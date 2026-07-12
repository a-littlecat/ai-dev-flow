# FIX-VALID-A：合法文档任务

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-VALID-A`
- `task_type`: `document`
- `task_class`: `A`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA1`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标

验证合法 Compact Core。

## 范围

只包含 fixture。

## 完成标准

- [x] Contract 可解析。

## 验证

- 命令：标准库 fixture 检查。
- 结果：待 Reader 实现验证。

## 证据

- `manifest.json#FIX-VALID-A`
