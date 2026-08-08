# Harness-neutral 能力要求

本文件只定义治理 Recipe 可依赖的能力词汇，不按 Harness 名称授予权限。Adapter 是可替换的数据声明；声明缺失、失效或与当前 `--help` 不一致时，降级到更保守的 Recipe 或 `R5`，不得改变核心 route、Review requirement 或 authority。

## 能力词汇

```yaml
skill_loading: [native, markdown, unsupported]
read_files: boolean
write_files: boolean
run_commands: boolean
git: boolean
context_isolation: [native, independent_process, independent_session, none]
write_isolation: [native_read_only, sandbox_read_only, readonly_copy, none]
subagents: [native, opaque, none]
approval_gate: [native, manual, none]
runtime_hooks: [native, plugin, none]
session_events: [native, adapter, manual, none]
```

`context_isolation` 只说明上下文边界，不能代替写隔离；`readonly_copy` 必须由 Orchestrator 在调用前建立且在 Review 后核对原工作区未变化。任何 `none` 都不能被解释为已经满足对应能力。

## Adapter 合同

每份 `adapters/*.json` 必须包含：

```text
adapter_id, verified_at, skill_loading, read_files, write_files,
run_commands, git, context_isolation, write_isolation, subagents,
approval_gate, runtime_hooks, session_events, preferred_review_recipe,
fallback_review_recipe, runtime_sync_method, version_sensitive_notes
```

命令参数是版本敏感事实。调用前必须查看当前 `--help`；Adapter 中的说明只是最近核对结果，不是永久保证。
