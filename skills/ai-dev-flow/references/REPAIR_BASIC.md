# 普通 Repair

普通 Repair 只在出现稳定 finding 后按需启用。机器规则以 `../policy/repair-basic.json` 为准，本文件只解释执行方式。

## 最小记录

```yaml
repair_chain_id: <stable id>
finding_ids: [F-001]
attempt: 1
before: {F-001: RED}
after: {F-001: GREEN}
review_status: Needs Fix
next: Continue
```

## 边界

- 一轮是一次针对冻结 finding 的 patch 到下一次独立 Review。
- 只读 Review、诊断、原样重跑测试、TASK/看板收据同步不计轮次。
- 默认两轮；只有 RED→GREEN、无 GREEN→RED、无新阻断 finding、严重度不升时才可增加一轮。
- 每次 patch 后必须独立 Review；预算耗尽或无进展时回到用户决定。
- 普通路径不要求 receipt chain、trusted context、history head、attestation hash 或 campaign state。
- merge、push、release、删除、外部同步、Accepted 和 Closed 仍需要各自 authority。
