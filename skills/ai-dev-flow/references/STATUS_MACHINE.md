# 任务状态机

任务状态必须写入任务文件和任务看板。状态不确定时写“待确认”，不要猜测。

Batch 和 Wave 不是任务状态。它们只表示任务的执行 / 审查组织方式，不能替代 Draft、Ready、In Progress、Review、Accepted 或 Closed。

## 状态定义

| 状态 | 含义 |
| --- | --- |
| Draft | 草稿。需求或任务边界尚未确认。 |
| Ready | 可以执行。目标、非目标、完成标准、验证方式和执行边界已明确。 |
| In Progress | 执行中。agent 正在按任务文件工作。 |
| Blocked | 被阻塞。缺少信息、权限、依赖、用户确认或存在冲突。 |
| Review | 等待审查。执行完成，等待独立审查。 |
| Needs Fix | 需要修复。审查发现 P0/P1 或必须修改项。 |
| Accepted | 按用户动作等级完成必要验收或决策。用户或指定验收人确认可接受。 |
| Closed | 已关闭。任务记录、验收、后续建议均已收口，且关闭动作已由用户确认或项目规则授权。 |
| Deferred | 延期。任务暂不执行，但未来可能恢复。 |
| Cancelled | 取消。用户确认不再执行。 |

## 允许的状态流转

- Draft -> Ready
- Draft -> Deferred
- Draft -> Cancelled
- Ready -> In Progress
- Ready -> Blocked
- In Progress -> Review
- In Progress -> Blocked
- In Progress -> Deferred
- Review -> Needs Fix
- Review -> Accepted
- Review -> Blocked
- Needs Fix -> In Progress
- Needs Fix -> Review
- Accepted -> Closed
- Blocked -> Ready
- Blocked -> Deferred
- Deferred -> Ready
- Deferred -> Cancelled

## 不能跳过的状态

- 代码任务不得从 In Progress 直接跳到 Accepted，必须先进入 Review。
- 未审查任务不得标记为 Accepted 或 Closed。
- 未给出用户动作等级，或未完成对应验收 / 决策的任务不得标记为 Accepted。
- UA0 任务不得自动跳到 Closed；agent 默认只能建议关闭，除非用户或项目规则明确授权。
- 未记录完成标准和验证方式的任务不得标记为 Ready。
- Needs Fix 未修复并复核前不得进入 Accepted。

## 谁可以改变状态

- 用户：可以改变任何状态，并可确认 Accepted、Closed、Deferred、Cancelled。
- 主控 agent：可以创建 Draft、更新 Ready、Blocked、Review，并根据用户明确意见或项目规则授权更新状态。
- 执行 agent：可以将 Ready 改为 In Progress，将完成后的任务改为 Review，或在受阻时改为 Blocked。
- 审查 agent：可以将 Review 改为 Needs Fix，或建议进入对应用户动作等级，但不得直接替代用户验收或决策。
- 验收人：可以确认 Accepted 或要求回到 Needs Fix / Blocked。

## 状态记录规则

- 状态变化必须写入任务文件。
- 看板状态必须和任务文件一致。
- 不确定状态必须标记为待确认。
- agent 不得擅自把未审查任务标为 Accepted 或 Closed。
- agent 不得仅因为任务是 UA0 就自动标记 Closed。
- 不得因为 Batch / Wave 整体完成，就自动把其中所有任务标记为 Accepted 或 Closed。
