# LITE-SYN-001：单文件文档错字

目标：把 `Workflow Cotnract` 更正为 `Workflow Contract`。

边界：

- 只允许修改一个 Markdown 文件中的一个拼写错误。
- 不改变术语含义、链接、代码、配置或用户可观察行为。
- 完成标准由精确文本搜索和 `git diff --check` 全部覆盖。
- 不需要用户观察、真实环境、外部写入或独立 Review。

预期路由：Lite；Reviewer 调用数为 0。
