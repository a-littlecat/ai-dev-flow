# scripts 说明

当前 Skill v1 不包含自动脚本。

本目录仅作为未来扩展预留。默认不要执行任何脚本，也不要假设本 Skill 依赖脚本能力。

未来可以添加：

- `create_task` 脚本：根据模板创建任务文件。
- `validate_task_board` 脚本：检查任务看板字段是否完整。
- `status_machine_check` 脚本：检查任务状态流转是否合理。
- `validation_summary` 脚本：汇总验证命令、人工验证和未验证项。
- `handoff_summary` 脚本：生成任务交接摘要。
- `task_expansion_guard` 脚本：提示任务是否出现膨胀迹象。
- `git_precheck` 脚本：汇总 Git 仓库、分支、HEAD、工作区和远程状态。
- `task_level_detector` 脚本：根据任务范围建议 A/B/C/D 等级。
- `create_task_branch` 脚本：按任务编号创建建议分支，但必须由用户确认后执行。
- `git_status_check` 脚本：生成 Git 状态检查摘要。
- `diff_review_summary` 脚本：基于 base commit 汇总 diff 文件和统计信息。
- `dirty_worktree_guard` 脚本：检测未提交改动并提示归属判断。
- `review_summary` 脚本：汇总代码审查结果。
- `batch_candidate_selector` 脚本：建议可批量的 A/B 小任务，但不自动执行。
- `wave_conflict_check` 脚本：检查候选 Wave 的文件锁、模块锁和依赖关系，但不自动启动并行会话。
- `review_hub_summary` 脚本：汇总 Batch / Wave 审查结论，但必须保留逐任务结论。

脚本设计原则：

- 默认只读或低风险。
- 不自动执行 merge、push、release、reset、rebase、删除分支、删除 Worktree 或删除文件。
- 执行前应说明输入、输出和影响范围。
- 失败时应输出清楚错误原因，不做隐式修复。
