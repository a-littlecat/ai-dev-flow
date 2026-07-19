# Lite 代表任务：单文件内部重构

只修改 `task_summary.py`：把 `format_task_summary` 内重复的字段清洗收敛为一个按 `FIELDS` 顺序构造的 normalized mapping。

完成标准：

- `format_task_summary` 的所有既有输出保持不变。
- 未知字段继续被忽略，缺失值继续输出为空字符串。
- 只修改 `task_summary.py`；不修改测试、任务合同或其他文件。
- `python -B -X utf8 -m unittest -v` 全部通过。
- `git diff --check` 通过。

本任务可逆、无敏感数据、无外部写入、无用户观察项，全部完成标准都有确定性验证。
