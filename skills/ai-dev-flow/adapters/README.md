# Harness Adapters

Adapter 只描述最近核对到的能力与版本敏感提示，不属于治理核心。`loader.py` 对任意同合同 JSON 执行严格只读加载；新增 Adapter 不需要修改核心 policy 或 Recipe。

初版包含 `generic`、`codex`、`kimi-code`、`opencode`、`zcode`。每次实际调用前仍须查看当前 `--help`；无法证明隔离或只读时按 fallback Recipe 或 `R5` 处理。
