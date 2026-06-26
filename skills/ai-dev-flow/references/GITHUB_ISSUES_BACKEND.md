# GitHub Issues Optional Backend

GitHub Issues Optional Backend 是一个可选设计，用于未来开源协作时把 TASK 映射到 GitHub Issue。v0.6.0 不实现自动同步。

## 设计目标

- 保持 Markdown-first 默认模式。
- 为开源协作提供 Issue 字段映射。
- 支持 agent 生成 mapping preview。
- 不强制 GitHub Projects API。

## 支持模式

| 模式 | 真相源 | 用途 | v0.6.0 状态 |
| --- | --- | --- | --- |
| Markdown-only | `docs/TASK_BOARD.md` + `docs/tasks/` | 默认个人项目 | 支持 |
| GitHub-projected | Markdown 是真相源，Issue 是同步视图 | 开源协作 | 设计，不自动同步 |
| GitHub-primary | Issue 是真相源，Markdown 是本地缓存 | 团队协作 | 仅未来方向 |

## 字段映射建议

| TASK 字段 | GitHub Issue 字段 |
| --- | --- |
| 任务编号 | Issue title 前缀或 label |
| 任务标题 | Issue title |
| 目标 / 非目标 | Issue body |
| 状态 | label 或 issue state |
| 优先级 | label |
| A/B/C/D 分级 | label |
| UA 等级 | label 或 issue body |
| 审查状态 | label / comment |
| 验证结果 | comment |
| PR | linked pull request |

## v0.6.0 明确不做

- 不自动创建 issue。
- 不自动关闭 issue。
- 不自动同步 labels。
- 不自动创建 PR。
- 不自动 merge。
- 不要求 GitHub Projects。

## Mapping Preview 输出格式

```markdown
## GitHub Issue Mapping Preview

- TASK 文件：
- 建议 Issue 标题：
- 建议 labels：
- 建议 body 摘要：
- 验证结果如何同步：
- 审查结论如何同步：
- 是否需要用户确认：是
```

## 安全规则

- 任何创建、关闭、编辑 issue 的动作都需要用户确认。
- 不把敏感信息写入公开 issue。
- 不把本机路径、私有账号、日志或密钥写入 issue。
- Markdown 仍是默认真相源，除非项目明确采用其他模式。
