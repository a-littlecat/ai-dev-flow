# FIX-LEGACY-AUTHORITY：Legacy 授权推断

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `FIX-LEGACY-AUTHORITY` |
| 任务类型 | 文档 |
| 任务分级 | A |
| 任务状态 | 待审查（`Review`） |
| 用户动作等级 | UA2 |

## 目标

- 验证 Legacy 授权来源只产生主体不可验证 warning。

## 非目标

- 无

## 允许修改范围

- fixture 文件。

## 禁止修改范围

- 合同规范。

## 完成标准

- [x] Review 的 Review、UA 与正文门禁齐全。

## 验证方式

- 对照 manifest 的精确 diagnostics。

## Git 与交接

- 执行 Base commit：fixture-base
- Diff 范围：fixture-base..fixture-head
- 当前分支：fixture/legacy-authority

## 执行与验证记录

- Legacy Review fixture 已构造并完成静态核对。

## 代码审查

- 审查状态：通过
- 审查结论：无 P0-P3。

## Diff 审查

- 审查状态：通过
- 修改文件清单：`legacy/authority-inferred.md`
- 审查结论：范围内通过。

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：通过
- 实际结果：用户阅读 fixture 方案后确认通过。

## 用户动作等级 / 验收建议

- 用户动作等级：UA2
- agent 已提供的证据：fixture 静态核对结果。
- 验收确认：用户已确认

## 合并状态

- 合并状态：用户已确认待合并

## 提交 / 合并

- Commit 状态：已提交
- Merge 状态：用户已确认待合并
- 回滚方式：回退 fixture commit。
