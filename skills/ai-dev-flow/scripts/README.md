# 脚本

ai-dev-flow 自带的 PowerShell 脚本，都用 `pwsh -NoProfile -File <skill>/scripts/<脚本>` 运行（`<skill>` 是 `$env:AI_DEV_FLOW`，默认 `~/.agents/skills/ai-dev-flow`）。用到哪个再来这里查；参数和细节写在各脚本开头的注释里。

| 脚本 | 用途 |
|---|---|
| `dispatch.ps1` | 把一项交给外部 CLI agent（Codex、Claude 的 `claude -p`、DSH 等）写或审，项目配置在 `scripts/dispatch.json`，每个 agent 可配模型（`modules/orchestrate.md`） |
| `status.ps1` | 按总览仓库的 `projects.json` 收各项目的状态，只读；快检太慢、提速项挂着不动、快检用时未知都提示，超过阈值 2 倍的标 `VerifySlowRed` |
| `direction.ps1` | 读一个项目的基准、预算、决定卡和流程图，判断方向要不要停、有什么要补，只读（`modules/direction.md` 第 5 节） |
| `launch.ps1` | 在一个项目里开命令行后台会话（`claude --bg`，默认 `/next`），用命令行登录的账号；按清单的 `wake`、`session` 决定新开、发消息还是开在桌面，按 `model`、`effort`（或 `-Model`、`-Effort`）定模型和思考强度（`modules/portfolio.md` 第 4 节） |
| `daily.ps1` | 把状态写成一页 HTML 并发通知，给计划任务定时跑；快检超过阈值 2 倍的项目标红 |
| `notify.ps1` | 发系统通知，要用户出手的再推到手机；本机配置在 `%APPDATA%\ai-dev-flow\notify.json` |
| `watch.ps1` | 给计划任务每 15 分钟跑：项目新变成"可能停滞"，有活没人做超过 12 小时（`-IdleHours`）、本周目标挂的项 24 小时没进展而项目在忙别的（`-GoalHours`）时，各推一次手机 |
| `check-md.ps1` | 文档格式检查：`.md` 里的控制字符、被拆断的表格行；各项目放进快检 |
| `archive-requests.ps1` | 把 `docs/requests.md` 里已转、已处理的小节移到 `docs/requests-done.md`，`/next` 开场只读还要转的（`skills/next/SKILL.md` 第 1 节） |
| `cleanup.ps1` | 合并后清理：删已合进主干、没有未提交改动的 worktree 和分支（`modules/land.md` 第 6 节） |
| `land-check.ps1` | 合并前的机械检查：note 覆盖要合并的 head、工作区干净、能快进（`modules/land.md` 第 2 节） |
| `verify-ledger.ps1` | 快检记账：按代码树和命令记绿红、用时、在哪跑，同一棵树、同一条命令已绿就不再跑（`modules/build.md` 第 3 节） |
