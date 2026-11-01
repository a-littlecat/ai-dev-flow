# ai-dev-flow

[English](README.en.md)

`ai-dev-flow` 是给 AI 编程助手（Claude Code、Codex 等）用的开发流程 skill。你只和它的总览对话，只管三件事：**方向**（要什么）、**品味**（需要人看的结果对不对）、**单向门**（撤不回的事做不做）。做、证明、独立验证、合并、复盘都由总览调度完成。

v2 把质量押在机器上，不押在流程和询问上：

- **项目自带的验证能力**：一条 verify 命令能判对错，能操作真实产品。项目没有，就先帮它搭。
- **机械约束**：每次都必须发生的事写成 hook、测试或 lint。
- **定期复盘**：攒够一批就看一遍合进去的东西，反复出现的问题升级成规则。

能撤回的事不停下来问"要不要"：直接做，给出结果，你事后可以推翻。设计依据和调研见 [docs/v2-design.md](docs/v2-design.md)。

## 结构

```
skills/ai-dev-flow/
  SKILL.md                 总览（唯一入口）：定档、信任等级、什么时候找你、汇报
  VERSION
  modules/harness.md       给项目搭验证能力：verify、操作产品、功能地图、hooks、慢验证队列
  modules/build.md         理解 → 做 → 证明（含亲手改坏验证）
  modules/verify.md        独立验证：只报能证明的问题、跨厂商规则
  modules/land.md          合并落地：提交正文模板、往前修和 revert
  modules/diagnose.md      诊断：先定义能判定对错的信号再修
  modules/orchestrate.md   自动推进：队列、后台子 agent＋worktree、并行上限
  modules/garden.md        复盘、教训升级、复盘摘要、清理
  modules/portfolio.md     多项目总览：项目清单、状态页和通知、收件箱、周会、跨项目教训
  scripts/dispatch.ps1     把一项交给外部 CLI agent（Codex、DSH 等）写或审
  scripts/status.ps1       按总览仓库的项目清单收各项目的状态（只读）
  scripts/daily.ps1        把状态写成一页 HTML 并发通知，给计划任务定时跑
  scripts/notify.ps1       系统通知；要你出手的再推到手机（Bark）
  scripts/watch.ps1        每 15 分钟查一次停滞，新停住的项目才推到手机
skills/next/SKILL.md       /next：在项目里按队列一项接一项做，直到需要你才收尾、发通知
skills/week/SKILL.md       /week：在总览仓库里开周会
tests/status.tests.ps1     status.ps1、daily.ps1、notify.ps1、watch.ps1 的检查：pwsh -NoProfile -File tests/status.tests.ps1
```

模块不是独立的 skill，由总览按需读取，一次只读当前需要的那一份。

## 怎么用

日常只说这几类话：

| 你说 | 总览会 |
|---|---|
| `/next`（可带答复，如 `/next #7 按你的`） | 按队列一项接一项做、验证、合并，直到需要你才收尾、发通知 |
| 想做 X、修 Y | 定档，一直做到需要你的地方 |
| 继续 / 自动推进 | 接着做，或者从队列里一项接一项推进 |
| 现在到哪了 | 三行汇报 |
| 可以 / 可以合并 | 合并落地 |
| 不对 / 报错了 | 先分类，再诊断 |
| 复盘 | 看一遍最近合进去的东西，给你一份复盘摘要 |
| 先停 | 停在安全点，把剩下的写进队列 |
| `/week`、周会（在总览仓库里） | 收齐所有项目一周的进展，提议下周目标 |

它只在四种情况下来找你：单向门要授权、需要你亲眼看、方向要选、卡住了。每次都把问题一次问完，并附上推荐答案。

### 三个档位：按"能不能撤回 × 机器能不能证明"

| 档 | 情况 | 谁说了算 |
|---|---|---|
| 自走 | 能撤回，而且 verify 能证明对错 | 按信任等级合并，写进复盘摘要 |
| 看一眼 | 能撤回，但对不对要靠人的眼光（界面、文案、手感） | 做完附截图，等你说"可以" |
| 单向门 | push 和发布、真实数据、删除、对外发送、花钱、安全设置、操作你正在用的软件 | 方案先确认，你授权才执行 |

### 信任等级

每个项目在 `AGENTS.md` 里写一个等级，由你来改；agent 只能在复盘摘要里附数据建议升降。没写时按 L0。

| 等级 | 自走档怎么合 | 并行上限 |
|---|---|---|
| L0 | 每次问你 | 2 |
| L1 | 各自验证通过后摞好，你一次合一批 | 3 |
| L2 | agent 直接合进主干，你事后抽查 | 5 |
| L3 | 定时任务自动从队列领单 | 按预算定 |

建议在项目 `AGENTS.md` 里写一句"开发相关请求一律从 `ai-dev-flow` 总览进入"，再列出项目事实：verify 命令、信任等级、北极星数字的口径、单向门补充、预算、禁止项。

### 同时推进几个项目

项目不设常驻会话：你在项目里新建会话、发 `/next`，它按队列一项接一项往下做，直到要你定、卡住、额度快用完或做满 5 项才收尾。进度都在队列里，换账号、换会话都能接着做。另建一个只在本地的总览仓库，放你的意图（`INTENT.md`）、项目清单（`projects.json`，含本周目标）、决定记录和跨项目教训：

- **每天**：计划任务定时跑 `scripts/daily.ps1`，生成一页状态（要你做的、空闲可领的、各项目的目标和进度），再弹一条通知，点开就是这一页。不花模型额度。
- **平时**：每个会话收尾时都发通知；要你看、要你定或卡住了，会同时推到手机。项目里的问题到项目里答（`/next #编号 答复`）。
- **每周**：在总览仓库里发 `/week`，看一周的进展，定下周目标。同一条教训在几个项目里都出现，就升到 skill 或用户级配置。

做法见 `modules/portfolio.md`。

## 安装

把 `skills/` 下的三个目录 `ai-dev-flow`、`next`、`week` 复制到 `~/.agents/skills/`。这是 Codex 的用户级 skill 目录。

Claude Code 的用户级 skill 目录是 `~/.claude/skills/`（也支持项目里的 `.claude/skills/`），每个目录建一个目录链接指向同一份文件（Windows 下不需要管理员权限）：

```powershell
foreach ($n in 'ai-dev-flow', 'next', 'week') {
    New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\$n" -Target "$env:USERPROFILE\.agents\skills\$n"
}
```

通知和状态页（可选）：

- 要推到手机，就在本机写 `%APPDATA%\ai-dev-flow\notify.json`（不入库）：`{ "bark": "https://api.day.app/<key>", "barkLevels": ["user", "stuck"] }`。不写就只弹系统通知。
- 会话等权限或等输入时弹通知：在 `~/.claude/settings.json` 的 `hooks.Notification` 里加一条命令 `pwsh -NoProfile -File <~/.agents/skills/ai-dev-flow 的完整路径>/scripts/notify.ps1 -Hook`。
- 每天的状态页：用 Windows 计划任务定时运行 `pwsh -NoProfile -File <同上>/scripts/daily.ps1 -Config <总览仓库>\projects.json`。
- 停滞提醒：再用计划任务每 15 分钟运行一次 `pwsh -NoProfile -File <同上>/scripts/watch.ps1 -Config <总览仓库>\projects.json`。

其他工具按各自的 skill 目录安装。同一个 skill 不要在同一个工具能扫到的两个目录里各放一份，否则会重复出现在 skill 列表里。

## 从 v1 升级

- 新工作不再建 TASK 文件和看板：证据写进提交正文，待办进队列（issues 或 `docs/queue.md`）。已有的 TASK 和看板保持原样。
- 合并不再默认每次都问：由项目的信任等级决定。项目没写等级时按 L0，行为和 v1 一样。
- 跨厂商审查只在单向门档必需；其余档用不低于执行方的同厂商子 agent 也可以。
- `plan.md`、`review.md`、`ship.md`、`compound.md` 分别由 `build.md`、`verify.md`、`land.md`、`garden.md` 代替。

## 版本

- **2.4.0**（2026-11-01）：通知减噪、停滞早发现。`notify.ps1 -Hook` 按事件类型分：回复完一分钟没输入的提醒不再弹；额度重置后会话没能自动继续的，推到手机。新增 `scripts/watch.ps1`，给计划任务每 15 分钟跑，只在项目新变成"可能停滞"时推一次手机。
- **2.3.0**（2026-11-01）：`/next` 默认一直往下做：一项完成就领下一项，有项要你定时先发通知、再接着做不依赖它的项；遇到没有能领的、做满 5 项、额度快用完或上下文太长才收尾。复盘改成开工前顺手做完，不单独占一个会话；一项里的审、修、复审、合并都在同一个会话里走完。`/next 连做` 由 `/next 只做一项` 代替。
- **2.2.0**（2026-11-01）：日常推进改成"一项一会话"：新增 `/next` 和 `/week` 两个入口，取消常驻的主会话、总览会话和每晚定时任务；派出去的活在会话里等到结束才收工，每次收尾都更新队列并发通知。新增 `scripts/daily.ps1`（状态页加通知，给计划任务跑）和 `scripts/notify.ps1`（系统通知加 Bark 推送）；`status.ps1` 新增最后活动时间、可领的项、本周目标和"可能停滞"提示。复盘改为攒够 20 个提交或满 7 天时由 `/next` 触发，每日摘要改称复盘摘要。
- **2.1.0**（2026-10-31）：新增 `portfolio` 模块（多项目总览：项目清单、统一收件箱和全局上限、合并摘要、跨项目教训升级）和只读的状态收集脚本 `scripts/status.ps1`；关联项目先定合同再开工，合同测试放进提供方的 verify；每日摘要写进 `.agents/digest/`，反复弹的审批给出具体的权限规则建议。2.0.0 之后加的派活脚本 `scripts/dispatch.ps1` 也计入本版。
- **2.0.0**（2026-10-29）：按"harness + 回路"重组。档位改按可逆性 × 可验证性分；新增信任等级 L0–L3；新增 `harness`（项目验证能力）和 `garden`（每晚复盘、教训升级）模块；证据改写进提交正文；独立验证只报能证明的 P0–P2；合并后主干红了往前修或 revert。
- **1.1.0**（2026-10-18）：新增自动推进模块（后台子 agent＋worktree 接力，项目可授权核对后自动合并）；审查模块补充首选审查方不可用时的顺序，审查模型不得低于执行方。
- **1.0.0**（2026-10-15）：重写为"一个总览加 5 个模块"。去掉了旧版的 repair 计数和收据、Lite / Tracked / Controlled 路由、UA0–UA7 分级、`workflow_lint` 和 Dashboard。
- **0.9.2 及更早**：完整的旧版（含 Dashboard、lint、repair gate、参考文档和测试）见标签 [`v0.9.2`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9.2)。v0.9 线的最后状态见标签 [`v0.9-final`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9-final)。

## 许可

[MIT](LICENSE)
