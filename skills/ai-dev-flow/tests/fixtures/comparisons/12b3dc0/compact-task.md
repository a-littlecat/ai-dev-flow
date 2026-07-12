# CMP-12B3DC0：验收反馈闸门文档收紧

> 基于真实 Git 变更 `12b3dc0` 回填；不表示历史上存在此 TASK。

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `CMP-12B3DC0`
- `task_type`: `document`
- `task_class`: `A`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Pending`
- `commit_status`: `Committed`

## 目标与边界

- 目标：收紧验收反馈闸门规则与提示词。
- 非目标：不实现自动修复。
- 允许修改：ACCEPTANCE_GUIDE、PROMPTS、WORKFLOW。
- 禁止修改：Skill 脚本与版本文件。

## 完成标准与验证

- 完成标准：三份文档的反馈闸门边界一致。
- 验证命令或检查：检查 `12b3dc0^..12b3dc0` diff 与关键词。

## Outcome

- Base / Diff：base=12b3dc0^;diff=12b3dc0^..12b3dc0
- 修改文件：ACCEPTANCE_GUIDE、PROMPTS、WORKFLOW。
- 验证证据：`git show --stat 12b3dc0`
- Review findings：none
