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

## 目标与边界

- 目标：验证合法 Compact Core。
- 非目标：none
- 允许修改：fixture 文件。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：Contract 与 Review checkpoint 语义完整。
- 验证命令或检查：对照 manifest 精确集合。

## Outcome

- Base / Diff：base=fixture-base;diff=fixture-base..fixture-head
- 修改文件：`valid/task-a-document.md`
- 验证证据：`manifest.json#FIX-VALID-A`
- Review findings：none
