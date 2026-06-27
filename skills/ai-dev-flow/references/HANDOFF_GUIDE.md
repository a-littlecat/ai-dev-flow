# 会话交接（session_handoff）指南

会话交接（`session_handoff`）用于跨会话、跨角色或跨阶段继续任务。交接摘要应引用项目文件和证据位置，不把聊天记录当作唯一状态来源。

## 适用场景

- 会话即将结束或上下文过长。
- 执行任务（`execute_task`）转审查任务（`review_task`）。
- 审查任务（`review_task`）转修复任务（`repair_task`）。
- Batch / Wave / Loop 汇总需要下一会话继续。
- Bug 诊断、实机信号或 TDD 循环尚未收口。

## 原则

- 引用路径，不复制完整文档。
- 写清已完成、未完成、验证结果、未验证项和风险。
- 写清下一会话建议读取的文件和建议使用的指南。
- 写清不要重复尝试的路线，避免返工。
- 不写密钥、Token、账号、隐私数据、本机敏感路径或聊天全文。

## 输出模板

```markdown
## 会话交接文档（session_handoff）

- 当前任务：
- 当前状态：
- 当前模式：
- 当前角色：
- base commit：
- 当前 HEAD：
- diff 范围：

### 已完成

- 待填写

### 未完成 / 阻塞

- 待填写

### 验证证据

- 命令：
- 结果：
- 证据位置：
- 未验证项：

### 下一会话建议读取

- `AGENTS.md`
- `README.md`
- `docs/TASK_BOARD.md`
- 当前 TASK：
- 其他：

### 下一会话建议使用的指南

- bug_diagnosis / tdd_task / real_env_signal / review_repair_loop / architecture_review / 不适用

### 不要重复尝试

- 无 / 待填写

### 下一步建议

- 进入 review_task / repair_task / bug_diagnosis / real_env_signal / 创建新 TASK / Blocked / 待确认
```
