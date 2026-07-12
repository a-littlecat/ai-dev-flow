# RED GREEN SIGNAL 顺序门禁收紧（Compact 回填）

> 基于真实 Git 变更 `4a6c417` 回填；不表示历史上存在此 TASK。

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `CMP-4A6C417`
- `task_type`: `document`
- `task_class`: `A`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Pending`

## 目标

固定 RED、GREEN、SIGNAL 的顺序门禁。

## 范围

PROMPTS、REAL_ENV_SIGNAL_GUIDE、TASK_TEMPLATE。

## 完成标准

三处规则顺序一致。

## 验证

检查 diff 与信号关键词。
