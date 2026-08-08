# ai-dev-flow

`ai-dev-flow` v0.9.2 包含按风险启用的 Git-first AI 开发治理内核，并把只读本地任务关系 Dashboard 的必要运行时与已构建前端放入完整 Skill 包。治理内核继续采用 v0.8 的精简路由：小任务直接退出 Skill；需要跨会话留证或高风险控制时才启用 TASK、Reviewer 和修复上限。

## 一句话用法

```text
请使用 ai-dev-flow 执行这个任务；先按 v0.8 policy 判断 DoNotUseSkill、Tracked、Controlled 或 Blocked。
```

支持 Skill 的 agent 先读：

1. `SKILL.md`
2. `policy/core.json`

这两份文件是默认运行时内核。不要预加载 Repair、整个 `references/` 或 `PROMPTS.md`。

## Codex Goal 自动落地

Codex 原生 Goal 负责持续运行，`ai-dev-flow` 负责范围、验证、Review、UA 和交付权限。推荐中文入口：

```text
启动自动落地目标：在冻结范围内持续实现、测试、复审、修复、提交、合并、推送并处理 PR/CI；不要创建 tag、release 或部署。
```

也支持“启动受控目标”“持续修到可验收”“我去休息，自动修好并交付”“不用中途问我，完成后直接交付”，以及带明确版本/环境的“自动发版”。完整语义见 `references/CODEX_GOAL_USAGE.md`。

## 三档结果

| 结果 | 适合什么 | 默认成本 |
|---|---|---|
| `DoNotUseSkill` | 低风险、单会话、少量文件、验证完整 | 不建 TASK、不调用 Reviewer、不进入 repair loop |
| `Tracked` | 跨会话、范围较大或需要证据留存 | TASK；风险命中时才调用只读 Reviewer |
| `Controlled` | D 级、高风险、真实环境、交付或不可逆动作 | 完整 TASK；关键动作前强制独立 Review |

准确触发条件只在 `policy/core.json` 中维护。本地可发现的信息先检查；权限、外部证据或规则冲突不明时为 `Blocked`。

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
- 没有明确 Goal / delivery authority 时，不自动 merge、push、release、删除、外部同步或关闭任务；显式 `auto_land` 只预授权 commit、merge、push、PR/CI，仍不包含 release、deploy、删除或 `Closed`。

这些旧指南仍保留为按需兼容资料，不是 v0.8 默认能力承诺。

## 新建任务

- Lite：不创建 TASK。
- Tracked：按环境使用 `references/TASK_TEMPLATE.md` 或单会话简版 `references/TASK_TEMPLATE_BRIEF.md`；Controlled 始终使用完整模板。
- 现有 TASK：继续原格式，不批量迁移。
- `references/TASK_TEMPLATE_COMPACT.md`：只供 v0.7 Writer/Reader 兼容。

TASK 是细粒度事实源，TASK_BOARD 是索引和投影。当前 Skill 包版本为 `0.9.2`，Workflow Contract schema 仍为 `adf/v0.7.0`。

## Reviewer 和 repair

- Tracked 只有命中 policy 风险标记时才调用一个隔离、只读 Reviewer。
- Controlled 在验收建议、delivery、merge、release 前强制 Review。
- Reviewer 默认由当前 Harness 自身建立原生只读隔离上下文；不得自动跨 Harness，只有用户明确指定时才允许。
- Reviewer 只审查，Repairer 只处理稳定 finding ID。
- 普通 finding 才读取 `policy/repair-basic.json` 与 `references/REPAIR_BASIC.md`：基础预算 2 轮，有进展时最多增加 1 轮，每次 patch 后独立 Review。
- receipt chain、trusted context、EscalatedRepair 与 Campaign 只在显式严格场景读取 `policy/repair-campaign.json` 与 `references/REPAIR_CAMPAIGN.md`。
- 严格 campaign 保留 4/5 次无进展阈值和 hard stop；外部副作用不得自动重试。

## 按需文档

- 执行细节：`references/WORKFLOW.md`
- 核心 policy：`policy/core.json`
- 普通 Repair：`policy/repair-basic.json`、`references/REPAIR_BASIC.md`
- 严格 Campaign：`policy/repair-campaign.json`、`references/REPAIR_CAMPAIGN.md`
- TASK 模板：`references/TASK_TEMPLATE.md`
- 单会话 Tracked 简版模板：`references/TASK_TEMPLATE_BRIEF.md`
- 代码审查：`references/CODE_REVIEW_CHECKLIST.md`
- 验证：`references/VALIDATION_GUIDE.md`
- 用户动作等级：`references/ACCEPTANCE_GUIDE.md`
- Git/diff：`references/GIT_PRECHECK.md`、`references/DIFF_REVIEW.md`
- v0.7 迁移：`references/V0.8_MIGRATION.md`
- Codex Goal 预设与中文触发：`references/CODEX_GOAL_USAGE.md`
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

`repair_gate.py` 默认直接读取 JSON campaign policy；旧 `CORE.md POLICY_JSON` 只作 deprecated 迁移输入。lint 或机械 gate 通过都不代表 Review、UA、merge、release 或 Closed。

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

- 当前 Skill 包身份：`0.9.2`。
- Contract schema：`adf/v0.7.0`，继续兼容。
- 正式发布事实以同名 annotated tag 和 GitHub Release 为准，交付收据记录在 `docs/tasks/REL-005-release-v092-maintenance.md`。
- `0.9.2` 完整包包含跨项目 Dashboard 运行时，项目目录与 Skill 安装目录可以分离。
- v0.8 评估证据保存在 `evaluations/v0.8/`，冻结原型保存在 `prototypes/v0.8-lite/`，不应在日常使用中加载或改写。
