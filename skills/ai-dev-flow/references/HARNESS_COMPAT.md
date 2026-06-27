# Harness Compatibility

本文件说明 ai-dev-flow 在不同 agent、CLI 或 IDE 中的兼容方式。目标是保持 agent-neutral，不假设所有 harness 都支持同样的 Skill、Worktree、subagent 或命令参数。

## 通用原则

- 不依赖某个 harness 的私有能力。
- 不支持 Skill 的 agent 可以直接读取 Markdown。
- 不假设不同 CLI 参数通用。
- 如果 harness 不支持 Worktree，不得启动 Parallel Wave 代码任务。
- 如果 harness 不支持 subagents，应降级为普通总览 / 执行 / 审核会话流程。
- 所有危险命令仍需用户确认。
- 不要声称当前版本具备自动多 agent 调度能力；本文件只说明人工可控的兼容方式和降级路径。

## 角色、会话与子 agent

角色不是会话。ai-dev-flow 中的 Orchestrator、Planner、Engineer、Reviewer、Verifier、Repairer、Archivist 是职责标签，不要求每个角色都开一个独立会话。

默认最小会话模型：

- 总览会话：Orchestrator / Planner / Archivist。
- 执行会话：Engineer / Verifier / Repairer。
- 审核会话：Reviewer。

如果同一会话切换角色，每一轮必须声明当前角色和当前模式，并遵守角色边界：Reviewer 不修复，Engineer / Repairer 不自我批准。

subagents / 子代理是可选加速能力，不是默认依赖。不支持 subagents 的 agent 仍然可以按 Markdown、Git 和 TASK 文件流程稳定运行。

ai-dev-flow 不禁止模型或 harness 自动使用 subagents、ultra mode-like capability 或类似内部并行能力；它限制的是无边界、不可追踪、不可审查、不可回滚的 subagent 行为。

如果 harness 支持可靠 subagents，可以用 Reviewer / Verifier subagents 减少额外审核会话。但中高风险任务仍建议独立审核会话或明确 Reviewer 隔离；写代码的 subagent 不得自我批准。

subagents 不得自动执行 merge、push、release、delete、reset、rebase、删除分支、删除 Worktree 或 GitHub 同步。任何危险操作仍必须用户确认。

代码并行仍必须遵守 Parallel Wave：代码任务默认使用独立分支或 Worktree，多个写代码 subagents 不得默认共享同一工作区修改同一批文件，并且必须逐任务审查。

## Subagent / Ultra Mode Compatibility

不同 model / harness 的 subagent 能力可能不同。不要假设名称、参数、隔离方式、日志格式或权限行为通用。

ai-dev-flow 对 subagents 的兼容原则：

- 不禁止 harness 或模型自动使用 subagents。
- subagents 是可选加速能力，不是默认依赖。
- 不支持 subagents 时，降级为普通总览会话、执行会话和审核会话。
- 不声称当前版本实现自动 subagent 调度、自动脚本或自动 GitHub 同步。
- 所有结果仍必须回到 TASK、Git diff、验证记录、审查结论和用户确认。

### 只读 subagents

只读 subagents 默认允许，适合辅助 Reviewer、Verifier 或 Orchestrator。

适合用途：

- 审查。
- 验证。
- 状态分拣。
- 文档检查。
- 日志整理。
- Markdown 链接检查。
- 测试结果整理。

限制：

- 不得修改业务代码、测试、配置或文档。
- 不得改变任务状态，除非用户或项目规则允许。
- 不得替代最终审查结论；主 agent 必须汇总结果。

### 写代码 subagents

写代码 subagents 谨慎允许，但必须受控。凡是会修改业务代码、测试、配置或文档的 subagent，都按写代码 subagent 处理。

必须满足：

- 声明任务编号。
- 声明当前角色和当前模式。
- 声明允许修改范围和禁止修改范围。
- 声明验证方式。
- 遵守 TASK 边界。
- 记录修改文件、验证结果和遗留风险。
- 不得自我批准。
- 最终仍需 Reviewer 审查。

### 多个写代码 subagents 并行

多个写代码 subagents 并行默认需要用户确认。

默认要求：

- 使用独立分支或 Worktree。
- 检查文件锁、模块锁、依赖关系和 diff 归属。
- 不得默认共享同一工作区修改同一批文件。
- 每个任务独立记录 base commit、HEAD、diff 范围、验证结果和审查结论。
- 如果无法确认工作区隔离和 diff 归属，必须停止并标记 `Blocked` 或待确认。

### 模型内部不可见 subagents

如果 harness / model 内部使用 subagents，但不暴露每个子代理细节，主 agent 不需要为每个内部 subagent 单独创建 TASK 文件，但至少必须保证最终结果可审查：

- TASK 边界清楚。
- 最终 diff 清楚。
- 验证证据完整。
- 未验证项明确。
- 风险明确。
- 不得自动 merge、push、release 或 delete。

主 agent 应汇总 subagent 使用情况或能力使用情况，说明哪些信息不可见。

## Subagent 使用情况汇总

建议写入任务文件、交接摘要或 Review 记录：

```markdown
## Subagent 使用情况

- 是否使用 subagents：是 / 否 / 不可见 / 待确认
- 使用类型：只读 / 写代码 / 混合 / 内部不可见
- 子代理用途：
  - 审查 / 验证 / 状态分拣 / 文档检查 / 写代码 / 其他
- 是否修改文件：是 / 否 / 待确认
- 修改文件：
  - 待填写
- 是否使用独立分支或 Worktree：是 / 否 / 不适用 / 待确认
- 验证结果：
  - 待填写
- 风险：
  - 待填写
- 是否需要用户确认：
  - 是 / 否
```

## Codex

- 可使用 Skill 目录。
- 可读取 Markdown references。
- 是否支持多会话或工具能力取决于当前环境。
- 不得默认启动多个执行会话。

## Claude Code

- 可把 `skills/ai-dev-flow/` 作为自定义 Skill 或 Markdown 说明读取。
- 审查和修复仍应分开。
- 不得假设其 Git / Worktree 行为与其他 CLI 完全一致。

## Cursor

- 可通过项目文档、rules 或 Markdown 引用使用。
- 如果不支持原生 Skill，先读取 `SKILL.md`、`WORKFLOW.md`、`PROMPTS.md`。
- UI 内的多 agent 行为必须用户确认。

## Gemini CLI

- 可读取 Markdown 工作流。
- 不得假设支持 Codex 或 Claude 的私有 Skill 格式。
- 并行代码任务需要独立分支或 Worktree 能力。

## DeepSeek

- 可作为 generic agent 按 Markdown 执行。
- 需要明确给出输入文件、输出文件、禁止操作和用户确认点。

## Generic agent

- 最小读取文件：
  - `skills/ai-dev-flow/SKILL.md`
  - `skills/ai-dev-flow/references/WORKFLOW.md`
  - `skills/ai-dev-flow/references/PROMPTS.md`
- 只能使用通用机制：Markdown、Git、任务文件、任务看板、审查清单。
- 不支持某能力时，必须降级为手动步骤或停止等待用户确认。

## 兼容性检查清单

- 当前 harness 是否支持 Skill？
- 是否能读取项目文件？
- 是否能运行 Git 命令？
- 是否支持 Worktree？
- 是否支持独立会话或独立 Reviewer？
- 是否能写回任务文件？
- 是否需要用户手动复制输出？
- 是否有危险命令确认机制？

## 输出格式

```markdown
## Harness Compatibility 检查

- 当前 agent / harness：
- Skill 支持：是 / 否 / 待确认
- Markdown 读取：是 / 否 / 待确认
- Git 能力：是 / 否 / 待确认
- Worktree 能力：是 / 否 / 待确认
- 独立 Reviewer：支持 / 需独立会话 / 不支持 / 待确认
- Subagents 能力：只读 / 写代码 / 混合 / 内部不可见 / 不支持 / 待确认
- Ultra mode-like 能力：支持 / 不支持 / 内部不可见 / 待确认
- Subagent 降级方案：
- 不可用能力：
- 降级方案：
- 是否需要用户确认：
```
