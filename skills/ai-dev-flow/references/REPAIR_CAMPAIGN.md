# 严格 Repair Campaign

本路径只用于显式严格自动化、高风险交付或用户明确要求的 Campaign。机器规则以 `../policy/repair-campaign.json` 为准。

## 启用条件

至少命中一项：显式 auto_land / auto_release、长时间无人值守、Skill 自修改、安全、数据迁移、不可逆操作、正式发布、用户明确要求严格 Repair Campaign。

## 保留机制

- receipt chain、canonical hash、trusted context 与 history anchor；
- chain-bound EscalatedRepair；
- TASK/验收合同/外层 scope-bound RepairCampaignAuthority；
- campaign profile、no-progress streak、hard-stop flags；
- 每轮 patch 后独立 Review 与 authority binding。

`repair_gate.py` 只校验 schema、结构、连续性、hash/binding 和机械资格。hash 只能发现意外漂移或重放，不能证明用户身份；真实 authority 必须来自当前 Harness、对话、GitHub 或其他可信边界。

## 调用

```powershell
python -B -X utf8 scripts/repair_gate.py repair-ledger.json `
  --trusted-context trusted-context.json `
  --format human
```

默认 policy 已指向 `policy/repair-campaign.json`。迁移期仍可通过 `--policy <old CORE.md>` 读取 rc2/rc3 `POLICY_JSON`，但会发出 deprecated 警告。

`MechanicallyEligible` 不等于 `*Allowed`，也不等于 Review、UA、交付或 Closed。不可逆外部动作不得自动重试。
