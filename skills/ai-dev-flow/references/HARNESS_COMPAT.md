# Harness Compatibility

本文件说明 ai-dev-flow 在不同 agent、CLI 或 IDE 中的兼容方式。目标是保持 agent-neutral，不假设所有 harness 都支持同样的 Skill、Worktree、subagent 或命令参数。

## 通用原则

- 不依赖某个 harness 的私有能力。
- 不支持 Skill 的 agent 可以直接读取 Markdown。
- 不假设不同 CLI 参数通用。
- 如果 harness 不支持 Worktree，不得启动 Parallel Wave 代码任务。
- 如果 harness 不支持 subagent，应使用独立会话替代 Reviewer。
- 所有危险命令仍需用户确认。

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
- 不可用能力：
- 降级方案：
- 是否需要用户确认：
```
