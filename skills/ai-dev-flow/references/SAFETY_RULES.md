# 安全规则

本文件定义通用权限分级和停止条件。若项目 `AGENTS.md` 有更严格规则，以项目规则为准。

## 可直接执行

- 阅读项目文档。
- 创建任务草稿。
- 更新任务文件。
- 更新 `TASK_BOARD`。
- 小范围文档修改。
- 生成计划。
- 生成审查报告。
- 推荐一组可批量的小任务。
- 推荐一组候选 Parallel Wave，但不启动执行会话。
- 创建 Intake 草稿。
- 运行只读 `triage_loop` 或 `status_loop`。
- 生成 GitHub Issue mapping preview，但不创建或修改 issue。
- 生成 Memory 更新建议，但不写入敏感信息。
- 使用只读 subagents 辅助审查、验证、状态分拣、文档检查、日志整理、Markdown 链接检查或测试结果整理。

## 需要用户确认

- 新增依赖。
- 删除文件。
- 修改构建脚本。
- 修改发布流程。
- 修改架构。
- 大范围重构。
- 修改核心模块。
- 合并代码。
- 发布版本。
- 变更许可证。
- 改动安全、账号、密钥相关逻辑。
- 启动 Parallel Wave 或多个执行会话。
- 让 C 级任务与其他代码任务并行。
- 修改 `PROJECT_CONSTITUTION.md` 中的 MUST / MUST NOT 规则。
- 写入或修改长期 Memory。
- 创建、编辑、关闭 GitHub Issue。
- 让 loop 超过默认最大循环次数。
- 使用不支持 Worktree 的 harness 执行 Parallel Wave 代码任务。
- 启动多个写代码 subagents 并行。
- 让多个写代码 subagents 共享同一工作区修改同一批文件。
- 允许写代码 subagent 处理 C/D、高风险或 UA5 / UA6 / UA7 任务。

## 默认禁止

- 自动 merge。
- 自动发布。
- 删除分支。
- 删除用户数据。
- 提交密钥。
- 提交本机私有配置。
- 执行破坏性命令。
- 未经确认安装大量依赖。
- 绕过审查直接标记完成。
- 用户 UA4 / UA5 / UA6 / UA7 验收失败后，agent 直接猜测修改业务代码。
- 没有复现步骤、期望结果、实际结果或日志 / 证据时，继续扩大修复范围。
- 第 2 轮后未通过 `CORE.md` progress gate 仍继续自修复，或突破第 3 轮绝对上限。
- 将用户实机验收失败直接等同于新需求并顺手实现。
- 未经过验收失败反馈闸门就把任务从失败反馈直接标记为 Accepted 或 Closed。
- 未经用户确认启动多个执行会话。
- 让 subagents 绕过 `review_task`、Git baseline、diff 记录、验证记录或用户确认。
- 让写代码 subagent 自我批准。
- 在无法确认工作区隔离或 diff 归属时继续并行写代码。
- 让 D 级或 UA5 / UA6 / UA7 任务进入代码并行。
- 自动 GitHub issue sync。
- 自动启动多 agent 调度。
- 让 Reviewer 直接修复。
- 让 Engineer 自我批准。
- 将 Loop 写成任务状态。
- 将 Intake 当作 TASK 直接执行。

## Subagent 安全边界

- ai-dev-flow 不禁止 harness 或模型自动使用 subagents。
- subagents 是可选加速能力，不是默认依赖；不支持 subagents 的 agent 仍可按 Markdown、Git 和 TASK 文件流程执行。
- 只读 subagents 默认允许，但不得修改业务代码、测试、配置或文档；不得改变任务状态，除非用户或项目规则允许。
- 写代码 subagents 谨慎允许，但必须声明任务编号、当前角色、当前模式、允许修改范围、禁止修改范围和验证方式。
- 写代码 subagents 必须遵守 TASK 边界，记录修改文件、验证结果和遗留风险，最终仍需 Reviewer 审查。
- 多个写代码 subagents 并行默认需要用户确认和工作区隔离，默认使用独立分支或 Worktree。
- 多个写代码 subagents 并行前必须检查文件锁、模块锁、依赖关系和 diff 归属。
- subagents 不得自动 merge、push、release、delete、reset、rebase、删除分支、删除 Worktree 或 GitHub 同步。
- 如果 model / harness 内部使用不可见 subagents，主 agent 至少必须保证 TASK 边界、最终 diff、验证证据、未验证项和风险清楚。

## 必须停止并询问用户的情况

- 需求不清。
- 任务范围过大。
- 找不到任务文件。
- 发现当前任务和已有任务冲突。
- 需要跨模块重构。
- 需要新增依赖。
- 需要删除文件。
- 测试失败且原因不明。
- 需要修改项目核心架构。
- agent 无法判断风险等级。
- Batch 中出现 C/D 风险、P0/P1 或 diff 无法按任务拆分。
- Wave 候选任务存在文件冲突、模块冲突、依赖不清或锁不清。
- 用户尚未确认并行执行。
- 写代码 subagent 缺少任务编号、角色、模式、修改范围或验证方式。
- 多个写代码 subagents 的工作区隔离、文件锁、模块锁或 diff 归属无法确认。
- Loop 达到最大轮次但仍未满足停止条件。
- Review-Repair Loop 第 2 轮后 progress gate 不通过，或第 3 轮后仍存在 P0/P1。
- 当前 harness 不支持所需能力，且无法安全降级。
- Memory 候选内容包含敏感信息、本机路径或未确认事实。
- GitHub Issue 映射涉及公开敏感信息。
- 需要修改 Project Constitution 的硬规则。

## 停止时应做什么

1. 停止继续修改。
2. 更新任务文件，将状态改为 `Blocked` 或待确认。
3. 写清楚阻塞原因、已完成内容、风险和需要用户确认的问题。
4. 不要用猜测继续推进。
