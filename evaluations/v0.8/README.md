# v0.8 Skill 瘦身评估

本目录是 `PLAN-001` 的可复现评估合同。它先于 v0.8 原型存在，用于防止在看到结果后追溯修改样本、标签、统计单位或通过阈值。

## 冻结边界

- `manifest.json`：6 个路由样本、2 个 repair trace、历史 Git 证据、阶段 B 代表任务、执行顺序和量化门槛。
- `ledger.schema.json`：阶段 A 与阶段 B 原始 ledger 的字段合同。
- `fixtures/`：Lite 合成任务、repair trace 和阶段 B 的同基线代表任务。
- `replay.py`：只读校验、零额度回放和阶段 B 机械评分器；仅使用 Python 标准库。
- `results/`：由冻结输入机械生成的 ledger 与报告。

## 阶段 A

```powershell
python -B -X utf8 evaluations/v0.8/replay.py verify
python -B -X utf8 evaluations/v0.8/replay.py replay --check
```

如需在冻结内容首次形成时生成结果：

```powershell
python -B -X utf8 evaluations/v0.8/replay.py replay --write
```

阶段 A 不调用模型、Reviewer、subagent 或外部服务，也不修改 `skills/ai-dev-flow/**`。

## 阶段 B

`LEAN-002` 必须按 `manifest.json` 中的顺序，在同一冻结基线、同一任务、同一完成标准、同一验证命令和同一模型版本下，依次执行：

1. `no-skill`
2. `lite`
3. `full`

三次执行完成后，把原始结果写入单一 JSON，并运行：

```powershell
python -B -X utf8 evaluations/v0.8/replay.py score-phase-b --runs <runs.json>
```

零分母规则已冻结：当 Full 基线为 0 时，不得伪造百分比；该指标记为 `insufficient` 并阻止全面实施。任务结果、P0/P1、authority、真实环境和 delivery 门禁不允许用其他效率指标抵消。

## 禁止事项

- 不得在看到阶段 A/B 结果后修改 expected label、阈值、计量单位、代表任务或 oracle，并继续沿用旧评估 ID。
- 任何冻结输入变化都必须创建新的评估 ID，旧 ledger 与新结果不得合并。
- 不得把固定样本上的零漏检外推为所有项目都不会漏检。
