# Harness Adapters

Adapter 只描述最近核对到的能力与版本敏感提示，不属于治理核心。`loader.py` 对任意同合同 JSON 执行严格只读加载；新增 Adapter 不需要修改核心 policy 或 Recipe。

`runtime_session_bridge` 是运行时会话事实接入能力；`formal_skill_sync_method` 是另行授权后的正式 Skill 同步说明。两者不得混用，前者永远不授予后者的外部写入权限。

初版包含 `generic`、`codex`、`kimi-code`、`opencode`、`zcode`。每次实际调用前仍须查看当前 `--help`；无法证明隔离或只读时按 fallback Recipe 或 `R5` 处理。
