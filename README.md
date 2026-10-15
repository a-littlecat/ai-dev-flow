# ai-dev-flow

[English](README.en.md)

`ai-dev-flow` 是给 AI 编程助手（Claude Code、Codex 等）用的开发流程 skill。你只和它的总览对话：说想要什么、看结果、做关键决定；定档、建任务、验证、独立审查、合并和记录，由总览调度完成。

它为前沿模型设计，目标有两个：

- **关键环节不省**：有证据才说完成；产品代码由另一个模型只读审查；不可挽回的动作先问。
- **不占用你的注意力**：能自己决定的不问，需要问的一次问完，汇报只写三行。

## 结构

```
skills/ai-dev-flow/
  SKILL.md              总览（唯一入口）
  VERSION
  modules/plan.md       计划与建任务
  modules/diagnose.md   诊断：先定义能判定对错的信号再修
  modules/review.md     独立审查：发起、输出格式、处理意见
  modules/ship.md       合并落地
  modules/compound.md   收尾沉淀与交接
```

模块不是独立的 skill，由总览按需读取，一次只读当前需要的那一份。

## 怎么用

日常只说这几类话：

| 你说 | 总览会 |
|---|---|
| 想做 X、修 Y | 定档，一直做到需要你的地方 |
| 继续 | 接着做下一步 |
| 现在到哪了 | 三行汇报 |
| 通过了 / 可以合并 | 合并落地 |
| 不对 / 报错了 | 先分类，再诊断 |
| 先停 | 停在安全点，写好交接 |

它只在四种情况下来找你：方向要选、需要你亲眼看、不可挽回的动作、卡住了。每次都把问题一次问完，并附上推荐答案。

### 三个档位

| 档 | 情况 | 流程 |
|---|---|---|
| 直接做 | 问答、文档、样式微调、验证脚本、局部小修 | 改 → 验证 → 汇报 |
| 标准 | 产品代码、接口、构建配置，或要跨会话 | 计划 → worktree 实现 → 分级验证 → 独立审查 → 合并 → 沉淀 |
| 高风险 | 打包发布、写用户文件、真实业务数据、迁移、不可逆动作 | 标准流程，另加：计划先确认、完整验证、用户验收 |

项目自己的 `AGENTS.md` 可以覆盖档位、验证命令和审查方式。建议在项目 `AGENTS.md` 里写一句"开发相关请求一律从 `ai-dev-flow` 总览进入"，再列出项目事实：验证命令、分工、合并授权、专项 skill。

## 安装

把 `skills/ai-dev-flow/` 复制到 `~/.agents/skills/ai-dev-flow/`。这是 Codex 的用户级 skill 目录。

Claude Code 只读 `~/.claude/skills/`，需要建一个目录链接指向同一份文件（Windows 下不需要管理员权限）：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-dev-flow" -Target "$env:USERPROFILE\.agents\skills\ai-dev-flow"
```

其他工具按各自的 skill 目录安装。同一个 skill 不要在同一个工具能扫到的两个目录里各放一份，否则会重复出现在 skill 列表里。

## 版本

- **1.0.0**（2026-10-15）：重写为"一个总览加 5 个模块"。去掉了旧版的 repair 计数和收据、Lite / Tracked / Controlled 路由、UA0–UA7 分级、`workflow_lint` 和 Dashboard。
- **0.9.2 及更早**：完整的旧版（含 Dashboard、lint、repair gate、参考文档和测试）见标签 [`v0.9.2`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9.2)。v0.9 线的最后状态见标签 [`v0.9-final`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9-final)。

## 许可

[MIT](LICENSE)
