# FIX-DELIVERY：交付顺序与授权反例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-DELIVERY`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
- `merge_authority`: `Denied`

## 目标与边界

- 目标：验证 merge 顺序和授权。
- 非目标：none
- 允许修改：fixture 文件。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：精确产生 delivery order 与 authority diagnostics。
- 验证命令或检查：对照 manifest 精确集合。

## Outcome

- Base / Diff：base=fixture-base;diff=fixture-base..fixture-head
- 隔离位置：fixture/delivery
- 回滚方式：删除测试 fixture。
- 修改文件：`violations/delivery.md`
- 验证证据：`manifest.json#FIX-DELIVERY`
- Review findings：none
- 合并目标与事实证据：fixture-target@fixture-merge
