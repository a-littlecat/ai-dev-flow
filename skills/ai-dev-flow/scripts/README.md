# scripts 说明

v0.6.0 不提供自动脚本。

本目录仅作为未来扩展预留。默认不要执行任何脚本，也不要假设本 Skill 依赖脚本能力。v0.6.0 只增加文档、模板、提示词和路线图。

## v0.7.0 只读脚本路线图

未来可以考虑添加只读检查脚本：

- `validate_task_board`：检查任务看板字段是否完整。
- `status_machine_check`：检查任务状态流转是否合理。
- `loop_state_summary`：汇总 Loop State，不修改任务状态。
- `batch_candidate_selector`：建议可批量的 A/B 小任务，但不自动执行。
- `wave_conflict_check`：检查候选 Wave 的文件锁、模块锁和依赖关系，但不自动启动并行会话。
- `memory_update_candidate`：从已完成任务中建议 Memory 更新，但不直接写入。
- `github_issue_mapping_preview`：预览 TASK 到 GitHub Issue 的字段映射，但不创建或修改 issue。

可选的后续脚本仍必须默认只读，不能把本 Skill 改成 CLI-heavy 工具。

## 脚本设计原则

- 默认只读。
- 不自动修改业务代码。
- 不自动 merge / push / release / delete。
- 不自动启动多个 agent。
- 不自动创建、关闭或同步 GitHub Issue。
- 执行前说明输入、输出、影响范围。
- 失败时输出错误原因，不做隐式修复。
