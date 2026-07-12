# CMP-4A6C417：RED GREEN SIGNAL 顺序门禁收紧（Legacy 回填）

> 基于真实 Git 变更 `4a6c417` 回填；不表示历史上存在此 TASK。

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CMP-4A6C417` |
| 任务类型 | 文档 |
| 任务分级 | A |
| 任务状态 | 待审查（`Review`） |
| 当前模式 | 审查任务（`review_task`） |
| 下一允许模式 | UA2 文档确认 |
| 优先级 | 高 |
| 风险等级 | 中 |
| 执行位置 | 当前文档分支 |
| 独立审查 | 必须 |
| 用户动作等级 | UA2 |

## 目标

- 固定 RED、GREEN、SIGNAL 的顺序门禁。

## 非目标

- 不执行真实环境测试。

## 允许修改范围

- PROMPTS、REAL_ENV_SIGNAL_GUIDE、TASK_TEMPLATE。

## 禁止修改范围

- Skill 脚本与版本文件。

## 完成标准

- [x] 三处规则的信号顺序一致。

## 验证方式

- 检查 `4a6c417^..4a6c417` diff 与信号关键词。

## Git 与交接

- 执行 Base commit：`4a6c417^`
- Diff 范围：`4a6c417^..4a6c417`

## 执行与验证记录

- 验证证据：`git show --stat 4a6c417`

## 代码审查

- 审查状态：通过
- 审查结论：无 P0-P3。

## Diff 审查

- 审查状态：通过
- 修改文件清单：PROMPTS、REAL_ENV_SIGNAL_GUIDE、TASK_TEMPLATE。
- 审查结论：无 P0-P3。

## 用户动作等级 / 验收建议

- 用户动作等级：UA2
- 是否允许关闭任务：否 / 待用户确认

## 提交 / 合并

- Commit 状态：已提交
