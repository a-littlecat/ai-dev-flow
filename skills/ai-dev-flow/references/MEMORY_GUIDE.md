# Memory Guide

Memory 用于沉淀长期项目知识，避免 AI 只依赖聊天记录，也避免把一次性经验遗忘。

## 建议目录

```text
docs/memory/
├── README.md
├── architecture.md
├── domain.md
├── gotchas.md
├── review-lessons.md
└── validation-lessons.md
```

## Memory 适合记录什么

- 稳定架构约定。
- 领域语言和关键概念。
- 常见坑点。
- 审查中反复出现的问题。
- 可靠验证命令和验证环境说明。
- 用户做出的长期决策。
- 后续任务可复用的摘要、经验和踩坑记录。

## Memory 与 DECISIONS 的边界

- 重大架构、依赖、接口或方向决策优先写入 `DECISIONS.md`。
- Memory 可以记录后续任务可复用的摘要和经验，并链接对应的 `DECISIONS.md` 条目。
- 不要用 Memory 替代正式决策记录；如果内容会改变项目方向，应先进入决策记录或等待用户确认。

## Memory 不应记录什么

- 聊天全文。
- 一次性临时问题。
- 密钥、Token、证书、私有账号。
- 本机绝对路径。
- 个人隐私。
- 未确认的猜测。

## memory_hydrate

`memory_hydrate` 是从完成任务中提炼长期知识的动作。

来源：

- Accepted / Closed 任务。
- Review 中的常见错误。
- 验证中的可靠命令和坑点。
- 用户决策和长期约束。

规则：

- 只提炼稳定、可复用知识。
- 不自动写入敏感信息。
- 不把未验证猜测写成事实。
- 重大架构、依赖、接口或方向决策优先沉淀到 `DECISIONS.md`，Memory 只记录可复用摘要或经验。
- 如果 Memory 与代码冲突，必须标记冲突，不得编造现状。

## 输出格式

```markdown
## Memory Hydrate 建议

- 来源任务：
- 是否建议更新 Memory：是 / 否 / 待确认
- 建议文件：
- 建议新增内容：
- 风险：
- 是否需要用户确认：
```

## 示例

```markdown
## docs/memory/validation-lessons.md

- 某类测试需要先启动本地服务；如果服务未启动，测试失败不能直接判定为代码失败。
```
