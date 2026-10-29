# ai-dev-flow

[English](README.en.md)

`ai-dev-flow` 是给 AI 编程助手（Claude Code、Codex 等）用的开发流程 skill。你只和它的总览对话，只管三件事：**方向**（要什么）、**品味**（需要人看的结果对不对）、**单向门**（撤不回的事做不做）。做、证明、独立验证、合并、复盘都由总览调度完成。

v2 把质量押在机器上，不押在流程和询问上：

- **项目自带的验证能力**：一条 verify 命令能判对错，能操作真实产品。项目没有，就先帮它搭。
- **机械约束**：每次都必须发生的事写成 hook、测试或 lint。
- **每天复盘**：看一遍合进去的东西，反复出现的问题升级成规则。

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
  modules/garden.md        每晚复盘、教训升级、每日摘要、每周清理
```

模块不是独立的 skill，由总览按需读取，一次只读当前需要的那一份。

## 怎么用

日常只说这几类话：

| 你说 | 总览会 |
|---|---|
| 想做 X、修 Y | 定档，一直做到需要你的地方 |
| 继续 / 自动推进 | 接着做，或者从队列里一项接一项推进 |
| 现在到哪了 | 三行汇报 |
| 可以 / 可以合并 | 合并落地 |
| 不对 / 报错了 | 先分类，再诊断 |
| 复盘 | 看一遍今天合进去的东西，给你一份每日摘要 |
| 先停 | 停在安全点，把剩下的写进队列 |

它只在四种情况下来找你：单向门要授权、需要你亲眼看、方向要选、卡住了。每次都把问题一次问完，并附上推荐答案。

### 三个档位：按"能不能撤回 × 机器能不能证明"

| 档 | 情况 | 谁说了算 |
|---|---|---|
| 自走 | 能撤回，而且 verify 能证明对错 | 按信任等级合并，写进每日摘要 |
| 看一眼 | 能撤回，但对不对要靠人的眼光（界面、文案、手感） | 做完附截图，等你说"可以" |
| 单向门 | push 和发布、真实数据、删除、对外发送、花钱、安全设置、操作你正在用的软件 | 方案先确认，你授权才执行 |

### 信任等级

每个项目在 `AGENTS.md` 里写一个等级，由你来改；agent 只能在每日摘要里附数据建议升降。没写时按 L0。

| 等级 | 自走档怎么合 | 并行上限 |
|---|---|---|
| L0 | 每次问你 | 2 |
| L1 | 各自验证通过后摞好，你一次合一批 | 3 |
| L2 | agent 直接合进主干，你事后抽查 | 5 |
| L3 | 定时任务自动从队列领单 | 按预算定 |

建议在项目 `AGENTS.md` 里写一句"开发相关请求一律从 `ai-dev-flow` 总览进入"，再列出项目事实：verify 命令、信任等级、北极星数字的口径、单向门补充、预算、禁止项。

## 安装

把 `skills/ai-dev-flow/` 复制到 `~/.agents/skills/ai-dev-flow/`。这是 Codex 的用户级 skill 目录。

Claude Code 的用户级 skill 目录是 `~/.claude/skills/`（也支持项目里的 `.claude/skills/`），需要建一个目录链接指向同一份文件（Windows 下不需要管理员权限）：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-dev-flow" -Target "$env:USERPROFILE\.agents\skills\ai-dev-flow"
```

其他工具按各自的 skill 目录安装。同一个 skill 不要在同一个工具能扫到的两个目录里各放一份，否则会重复出现在 skill 列表里。

## 从 v1 升级

- 新工作不再建 TASK 文件和看板：证据写进提交正文，待办进队列（issues 或 `docs/queue.md`）。已有的 TASK 和看板保持原样。
- 合并不再默认每次都问：由项目的信任等级决定。项目没写等级时按 L0，行为和 v1 一样。
- 跨厂商审查只在单向门档必需；其余档用不低于执行方的同厂商子 agent 也可以。
- `plan.md`、`review.md`、`ship.md`、`compound.md` 分别由 `build.md`、`verify.md`、`land.md`、`garden.md` 代替。

## 版本

- **2.0.0**（2026-10-29）：按"harness + 回路"重组。档位改按可逆性 × 可验证性分；新增信任等级 L0–L3；新增 `harness`（项目验证能力）和 `garden`（每晚复盘、教训升级）模块；证据改写进提交正文；独立验证只报能证明的 P0–P2；合并后主干红了往前修或 revert。
- **1.1.0**（2026-10-18）：新增自动推进模块（后台子 agent＋worktree 接力，项目可授权核对后自动合并）；审查模块补充首选审查方不可用时的顺序，审查模型不得低于执行方。
- **1.0.0**（2026-10-15）：重写为"一个总览加 5 个模块"。去掉了旧版的 repair 计数和收据、Lite / Tracked / Controlled 路由、UA0–UA7 分级、`workflow_lint` 和 Dashboard。
- **0.9.2 及更早**：完整的旧版（含 Dashboard、lint、repair gate、参考文档和测试）见标签 [`v0.9.2`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9.2)。v0.9 线的最后状态见标签 [`v0.9-final`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9-final)。

## 许可

[MIT](LICENSE)
