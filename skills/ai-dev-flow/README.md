# ai-dev-flow

`ai-dev-flow` v0.9.0 包含按风险启用的 Git-first AI 开发治理内核。当前待发布工作树还把只读本地任务关系 Dashboard 的必要运行时与已构建前端放入完整 Skill 包；治理内核继续采用 v0.8 的精简路由：小任务直接退出 Skill；需要跨会话留证或高风险控制时才启用 TASK、Reviewer 和修复上限。

## 一句话用法

```text
请使用 ai-dev-flow 执行这个任务；先按 v0.8 policy 判断 DoNotUseSkill、Tracked、Controlled 或 Blocked。
```

支持 Skill 的 agent 先读：

1. `SKILL.md`
2. `references/CORE.md`

这两份文件是默认运行时内核。不要预加载整个 `references/`，也不要默认加载 `PROMPTS.md`。

## 三档结果

| 结果 | 适合什么 | 默认成本 |
|---|---|---|
| `DoNotUseSkill` | 低风险、单会话、少量文件、验证完整 | 不建 TASK、不调用 Reviewer、不进入 repair loop |
| `Tracked` | 跨会话、范围较大或需要证据留存 | TASK；风险命中时才调用只读 Reviewer |
| `Controlled` | D 级、高风险、真实环境、交付或不可逆动作 | 完整 TASK；关键动作前强制独立 Review |

准确触发条件只在 `references/CORE.md` 的 `POLICY_JSON` 中维护。输入不完整或权限不明时为 `Blocked`，不猜测降级。

## 默认保留什么

- 用户与项目规则优先；
- Git 状态、base/diff 和可回滚边界；
- Tracked / Controlled 的 TASK 事实源；
- 覆盖完成标准的确定性验证；
- 权限、真实环境和外部副作用门禁；
- 独立只读 Review；
- Review、UA、commit、merge、release、Closed 状态分离。

## 默认不再做什么

- 不为低风险任务创建流程文档；
- 不为证明流程存在而调用 Reviewer 或 subagent；
- 不预加载长提示词、Batch、Wave、Loop、Memory、Constitution、角色或 provider 指南；
- 不建设自动调度器、数据库、遥测、计费或模型 Adapter；
- 不自动 merge、push、release、删除、外部同步或关闭任务。

这些旧指南仍保留为按需兼容资料，不是 v0.8 默认能力承诺。

## 新建任务

- Lite：不创建 TASK。
- Tracked：按环境使用 `references/TASK_TEMPLATE.md` 或单会话简版 `references/TASK_TEMPLATE_BRIEF.md`；Controlled 始终使用完整模板。
- 现有 TASK：继续原格式，不批量迁移。
- `references/TASK_TEMPLATE_COMPACT.md`：只供 v0.7 Writer/Reader 兼容。

TASK 是细粒度事实源，TASK_BOARD 是索引和投影。当前工作树 Skill 包版本为正式发布的 `0.9.0`，Workflow Contract schema 仍为 `adf/v0.7.0`。

## Reviewer 和 repair

- Tracked 只有命中 policy 风险标记时才调用一个隔离、只读 Reviewer。
- Controlled 在验收建议、delivery、merge、release 前强制 Review。
- Reviewer 默认由当前 Harness 自身建立原生只读隔离上下文；不得自动跨 Harness，只有用户明确指定时才允许。
- Reviewer 只审查，Repairer 只处理稳定 finding ID。
- `AutoRepair` 基础预算 2 轮；只有冻结 finding 的 RED→GREEN、无回归且证据覆盖增加时才增加第 3 轮。
- 3 是自主 repair loop 上限。`Stop` 后可授权默认一次的 `EscalatedRepair`，或授权 TASK/验收合同/外层 scope-bound 的 `RepairCampaignAuthority`。
- campaign 在核心产品连续 4 次、Harness 连续 5 次无实质进展后进入用户裁决；硬停止不等待计数耗尽。
- repair chain 绑定 finding 和 closure contract；换 TASK 或模型不重置，失败回到 `Stop`，外部副作用不得自动重试。

## 按需文档

- 执行细节：`references/WORKFLOW.md`
- TASK 模板：`references/TASK_TEMPLATE.md`
- 单会话 Tracked 简版模板：`references/TASK_TEMPLATE_BRIEF.md`
- 代码审查：`references/CODE_REVIEW_CHECKLIST.md`
- 验证：`references/VALIDATION_GUIDE.md`
- 用户动作等级：`references/ACCEPTANCE_GUIDE.md`
- Git/diff：`references/GIT_PRECHECK.md`、`references/DIFF_REVIEW.md`
- v0.7 迁移：`references/V0.8_MIGRATION.md`
- 最小项目规则：`references/AGENTS_COMPAT.md`
- 人工复制提示：`references/PROMPTS.md`

一次只读当前动作真正需要的文件。Controlled 可按风险多读专项文档，但不要整包预加载。

## 安装

把完整 `skills/ai-dev-flow/` 目录复制到 agent 的 Skill 目录。若项目不支持 Skill，优先把 `references/AGENTS_COMPAT.md` 中的最小规则合并到项目 `AGENTS.md`；不要要求 agent 每次读取整套 reference。

迁移现有项目只需最多三步，见 `references/V0.8_MIGRATION.md`。历史 TASK、v0.7 Contract 和只读 lint 无需迁移。

## 只读 Contract 工具

v0.7 Reader、`workflow_lint` 和 TASK_BOARD drift 检查继续保留：

```powershell
python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/TASK-001.md --format human
python skills/ai-dev-flow/scripts/workflow_lint.py . --format human
python skills/ai-dev-flow/scripts/repair_gate.py repair-ledger.json --trusted-context trusted-context.json --format human
```

lint 通过只代表可确定结构规则通过，不代表 Review、UA、merge、release 或 Closed。

## 本地 Dashboard

完整 Skill 安装包中的 `scripts/dashboard.py` 提供只读本地关系图、下一动作、并行候选、需要决定项、任务详情与 SSE 实时更新。目标项目只需是包含 `docs/tasks/` 的 Git 工作树，不需要复制或链接 Skill：

```powershell
py -3 -B -X utf8 "C:\Users\<user>\.agents\skills\ai-dev-flow\scripts\dashboard.py" `
  --project-root "D:\projects\CADCat"
```

入口脚本所在 Skill 是默认 `skill-root`。也可明确指定另一个安装目录：

```powershell
py -3 -B -X utf8 "<installed-skill>\scripts\dashboard.py" `
  --project-root "D:\projects\CADCat" `
  --skill-root "C:\Users\<user>\.agents\skills\ai-dev-flow" `
  --port 0 `
  --no-open
```

- Skill 查找顺序：显式 `--skill-root`、`AI_DEV_FLOW_SKILL_ROOT`、当前入口所在 Skill、常见 Harness 用户目录、最后才是项目内 `skills/ai-dev-flow` 兼容路径。
- `--port 0` 是默认值，由操作系统原子分配可用 loopback 端口；显式端口被占用时只停止当前启动，不结束其他实例。
- 每个进程使用由项目规范路径派生的项目 key，以及独立 instance ID、PID 和运行状态目录。干净停止只清理自己的实例目录。
- 启动前严格检查 Skill `0.9.x` 和 Workflow Contract 的 `adf/v0.7.0` 声明；显式 Scheduling `scheduling_schema` 若畸形、重复或不兼容也会停止。为兼容历史 TASK，存在 Scheduling 区块但从未声明 `scheduling_schema` 时继续交给公共 Reader，以 `unknown` 表示缺失证据，不补写也不猜测。运行中 Reader、后端和静态前端保持启动快照，Skill 文件变化时控制台明确提示重启，不热切换。
- 安装版运行时只需要 Python 3.11+、Git 和浏览器，不需要 Node.js、npm、Vite 或 ai-dev-flow 源码仓库。
- 页面与 API 仍只绑定 `127.0.0.1`，只接受同源读取和 SSE；不会写 TASK、TASK_BOARD、Skill 或 Git，也不会创建/切换 Worktree 或授予治理 authority。

完整的源码开发、构建与验证说明见仓库 `dashboard/README.md`。安装目录必须包含 `dashboard/runtime-manifest.json`；缺少该文件说明仍是旧版或不完整 Skill，启动会明确失败。

## 版本状态

- 当前工作树 Skill 包：`0.9.0`。
- 当前正式发布版本：`0.9.0`，于 2026-07-30 发布。
- Contract schema：`adf/v0.7.0`，继续兼容。
- 发布状态：annotated tag `v0.9.0` 与正式 GitHub Release 均已创建；该正式包仍是仅仓库运行的 Dashboard。跨项目安装运行时属于 `DASHBOARD-PORTABLE-001` 待发布变更，未同步到本机 Skill，也未形成新 tag 或 Release。
- v0.8 评估证据保存在 `evaluations/v0.8/`，冻结原型保存在 `prototypes/v0.8-lite/`，不应在日常使用中加载或改写。
