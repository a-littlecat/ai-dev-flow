# V08-LEAN-EVAL-003

这是 `V08-LEAN-EVAL-002` 的一次性替代评估周期，用于修复 `LEAN002-P1-001` 和 `LEAN002-P1-002`。旧评估保持只读，新旧 ledger 不合并。

## 固定边界

- stage A 直接读取默认关闭原型 `CORE.md` 中的 `POLICY_JSON`，不在评估器内维护第二套 route/review/repair 规则。
- 新协议和 stage A 必须先经独立 Review；Review 无 P0/P1 前，三次 main 调用数必须保持 0。
- phase B 只允许按 `no-skill -> lite -> full` 串行运行，各一次 main。
- 三次 main 均从同一父任务以 `fork_turns=none` 创建，不传 model 或 reasoning override。
- 平台没有暴露 backend 精确版本，因此结论只限于同一父任务会话内的三次继承默认模型对照，不作跨会话同版本声明。

## 回放命令

```powershell
python -B -X utf8 evaluations/v0.8/v003/replay.py verify
python -B -X utf8 evaluations/v0.8/v003/replay.py replay --write
python -B -X utf8 evaluations/v0.8/v003/replay.py replay --check
python -B -X utf8 -m unittest discover -s evaluations/v0.8/v003 -p "test_*.py" -v
```

phase B 证据形成后执行：

```powershell
python -B -X utf8 evaluations/v0.8/v003/replay.py score-phase-b --runs evaluations/v0.8/v003/results/phase-b/runs.json --write
python -B -X utf8 evaluations/v0.8/v003/replay.py score-phase-b --runs evaluations/v0.8/v003/results/phase-b/runs.json --check
```
