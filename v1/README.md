# ai-dev-flow v1（精简版）

v1 是面向前沿模型重写的精简版：一个总览入口，加上 5 个按需读取的模块。仓库根目录下 `skills/ai-dev-flow/` 的 v0.9.2 保持不变，Dashboard 和相关脚本仍然从那里运行。

## 设计目标

- 用户只和总览对话；总览负责定档、分发、控制和记录。
- 流程尽量精简，关键环节不省：有证据才说完成、产品代码要独立审查、不可挽回的动作先问。
- 不占用用户的注意力：只在四种情况打扰用户，问题一次问完，汇报只写三行。

## 结构

```
v1/ai-dev-flow/
  SKILL.md              总览（唯一入口）
  VERSION
  modules/plan.md       计划与建任务
  modules/diagnose.md   诊断
  modules/review.md     独立审查
  modules/ship.md       合并落地
  modules/compound.md   收尾沉淀与交接
```

## 从 v0.9.2 迁移

| v0.9.2 | v1 |
|---|---|
| 路由、SAFETY_RULES、STATUS_MACHINE、ACCEPTANCE（UA0–UA7） | 总览 |
| TASK_TEMPLATE_BRIEF、REQUIREMENT_GRILLING、INTAKE | modules/plan.md |
| BUG_DIAGNOSIS、REAL_ENV_SIGNAL、TDD、验收失败分类 | modules/diagnose.md |
| CODE_REVIEW_CHECKLIST、DIFF_REVIEW、REVIEW_REPAIR_LOOP | modules/review.md |
| GIT_WORKFLOW、GIT_PRECHECK | modules/ship.md、modules/plan.md |
| HANDOFF、MEMORY、PROJECT_CONTEXT | modules/compound.md |
| repair ledger、收据哈希、campaign 授权及其余参考文件 | v1 不再使用 |

行为上的主要变化：

- 信息不全时，不再直接判 `Blocked`，而是按高一档处理并继续推进。
- 修复不再按轮次和收据计数，改为修到验证全绿；同一根因连续 3 次没有进展时停下。
- 状态精简为 `Ready / Doing / Review / UA / Done / Blocked`。
- 旧格式的 TASK 不迁移。

## 安装

把 `v1/ai-dev-flow/` 复制到 `~/.agents/skills/ai-dev-flow/`，这是 Codex 的用户级 skill 目录。

Claude Code 不读 `~/.agents/skills`，需要建一个目录链接：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-dev-flow" -Target "$env:USERPROFILE\.agents\skills\ai-dev-flow"
```

## 待办

- Dashboard 运行时目前锁定 0.9.x 的 skill 指纹（`runtime_compat.py`），还没有和 v1 解耦。
- 中英文 README 与 CHANGELOG 待 v1 试用稳定后再更新。
