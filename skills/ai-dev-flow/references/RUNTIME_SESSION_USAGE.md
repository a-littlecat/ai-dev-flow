# Runtime Session 按需使用

Runtime Session 只向 Project Console 提供 Harness 当前在做什么的短期事实。它不修改 TASK、Git、Review、UA 或 authority，也不安装、同步或更新正式 Skill。

## 何时读取

只有当当前 Harness 可执行命令，且用户需要 Console 展示 live session 时读取本文件。不需要 live session 时不得为了流程而写 Runtime。

## 可执行入口

以下命令中，`<skill-root>` 是当前候选 Skill 根目录，`<project-root>` 是含 `docs/tasks` 的项目，`<session-id>` 在本次 Harness 会话内保持不变。如无隔离证据需求，可省略 `--runtime-root` 使用本机默认 Runtime 目录。

```text
python -B <skill-root>/scripts/adf.py session <command> --project-root <project-root> ...
```

Runtime Bundle manifest 缺失、文件集不一致或 SHA256 被篡改时，入口必须在导入 Runtime 前以 exit code `2` 失败关闭。

## 生命周期 Hook

1. 任务开始：立即 `session start`，写入真实 `task/harness/phase/next-step/status-summary`。
2. 阶段切换：每次 planning / implementing / validating / reviewing / repairing 切换时执行 `session update`，同时更新下一步与状态摘要。
3. 长时间无阶段变化：在 `stale_after_seconds` 到期前执行 `session heartbeat`，只刷新存活时间，不改变阶段或文案。
4. 等待用户：在让出控制前执行 `session wait --reason ...`，Console 应进入 human attention。
5. 会话结束：无论成功、失败还是取消，均执行 `session end --reason ...`；不得用删除 Runtime 文件代替 end。

```powershell
$adf = "<skill-root>/scripts/adf.py"
py -3 -B $adf session start --project-root "<project-root>" --session "<session-id>" --task "<task-id>" --harness "<harness-id>" --phase planning --next-step "核对任务" --status-summary "正在启动"
py -3 -B $adf session update --project-root "<project-root>" --session "<session-id>" --phase validating --next-step "运行验证" --status-summary "正在验证"
py -3 -B $adf session heartbeat --project-root "<project-root>" --session "<session-id>"
py -3 -B $adf session wait --project-root "<project-root>" --session "<session-id>" --reason "等待用户决定"
py -3 -B $adf session end --project-root "<project-root>" --session "<session-id>" --reason "Harness 会话结束"
```

## 核对

用 `adf.py session list --format json` 核对原始 Runtime，用 `adf.py status --format json` 核对 Console 投影。证据必须记录 Harness 真实进程、session id、阶段序列、结束状态和隔离 Runtime 路径；仅运行 Python 脚本或单元测不能写成“真实 Harness 桥接”。
