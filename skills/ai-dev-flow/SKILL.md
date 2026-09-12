---
name: ai-dev-flow
description: 按风险启用的 Git-first AI 开发治理内核。用于任务事实源、权限边界、独立审查、修复上限或验收与交付分离；Codex Goal 支持 governed_goal“启动受控目标”、auto_land“启动自动落地目标”和 auto_release“自动发版”等中文预设；低风险任务明确退出 Skill，完整语义按需读取 references/CODEX_GOAL_USAGE.md。
---

# ai-dev-flow v0.8

`ai-dev-flow` 不是所有任务的必经流程。它先判断是否有净收益：低风险任务退出 Skill；只有需要持续留证或高风险控制时才启用治理。

## 先判断是否适用

先根据用户要求和已知项目规则判断是否需要治理，不为普通请求预先加载 `CORE.md`。

- 普通问答、非交付的文案或格式小改、已有证据与测试覆盖的孤立局部修正，若不涉及下述治理情形，可直接退出本 Skill；修改类请求还须动作已有授权、确定性验证覆盖全部完成标准且无需用户观察。按用户要求完成工作与适用验证，不为取得“不适用”标签而创建 TASK 或加载 policy。
- 用户或项目明确要求治理或独立审查、已有受治理 TASK、跨会话留证，或涉及历史 P1、超过 3 个业务文件、共享组件、核心执行/写入路径、构建部署配置、公共 API、安全、数据迁移、并行写入、真实宿主、用户观察或验收、交付、外部写入及其他高风险动作时，读取下面的运行时内核。验证未覆盖全部完成标准时也进入内核核实。仅点名本 Skill 以判断适用性，不等于要求启动治理。
- 不能确认请求是否属于普通局部工作，或风险、项目门禁和既有 TASK 状态不清时，读取内核核实，不以“改动小、可回滚”绕过治理。

此处只决定是否加载治理工作流，不产生正式 Lite / Tracked / Controlled 结果，也不改变权限或项目门禁。进入治理后的全部路由仍以 `CORE.md` 的 `POLICY_JSON` 为唯一规则源。

## 适用时的必读顺序

1. 完整读取本文件。
2. 完整读取 [CORE.md](references/CORE.md)。其中 `POLICY_JSON` 是路由、Reviewer、repair 计数和超限授权的唯一规则源。
3. 读取用户要求、项目 `AGENTS.md`、Git 状态和与任务直接相关的事实源。
4. 先路由，再决定是否读取一份按需 reference。不要默认加载 `PROMPTS.md` 或整个 `references/`。

进入治理后的默认运行时工作流输入只有本文件与 `CORE.md`。解析失败、输入未知或规则冲突时，按 `Blocked` 处理，不猜测。

## 第一步：路由

把可观察事实整理为 policy 输入：任务等级、UA、请求动作、风险标记、是否有动作授权、是否有确定性验证覆盖、是否需要用户观察或真实环境证据。

按 `CORE.md` 的顺序判断：

1. 命中 `controlled` 条件则进入 `Controlled`。
2. 完整满足 `lite` 条件则输出 `DoNotUseSkill`。
3. 其他已知输入进入 `Tracked`。
4. 信息不足或未知字段为 `Blocked`。

不确定时只能升级或阻塞，不能降级。

## Lite：退出 Skill

路由结果为 `DoNotUseSkill` 后：

- 停止读取本 Skill 的其他文件；
- 不创建 TASK，不调用 Reviewer，不进入 repair loop；
- 只按用户要求、项目规则、Git/diff 和直接相关文件完成最小改动；
- 用确定性验证覆盖全部完成标准，最后报告修改、验证、风险和未完成项。

容易回滚不能代替验证。需要用户观察、真实环境证据、额外授权或高风险动作时，必须重新路由。

## Tracked：按需治理

Tracked 用于跨会话、范围较大或需要留证但尚未达到 Controlled 的任务：

- 新任务按环境选择模板：大上下文模型且预期单会话内完成的 Tracked 任务可用 `references/TASK_TEMPLATE_BRIEF.md`；小上下文或能力较弱的模型、预期跨会话或有交接需求的任务一律使用完整 `references/TASK_TEMPLATE.md`；现有任务继续沿用原格式；
- TASK 是范围、状态和证据事实源，TASK_BOARD 只是投影；
- 记录 base commit、允许/禁止范围、完成标准、验证、diff 和状态边界；
- 仅在 policy 的 Tracked 风险标记命中时调用一个隔离、只读 Reviewer；未命中则跳过，不为流程而调用；
- policy 跳过只表示“没有 Reviewer 调用”，不得伪装成 `review_status=Passed`；在 `adf/v0.7.0` 下保持 `Pending`，如要进入 Accepted / Closed 再完成真实只读 Review；
- 命中但缺少 Reviewer authority/capability 时保持 `Blocked`、合法升级或取得明确授权，不得自批为 Passed。

## Controlled：强制控制

Controlled 使用完整 TASK 和清晰授权边界。执行前冻结范围、风险、完成标准和验证；在 policy 规定的 enforcement point 前必须完成独立 Review。

- `review_task` 只审查，不修改业务代码；
- `repair_task` 只处理稳定 finding ID 指向的问题；
- delivery、merge、release、删除、迁移、外部写入等动作必须分别获得相应授权；
- 真实环境任务必须区分自动证据与用户实机证据；缺少必需证据时保持 `Blocked`。

## 执行与验证

Tracked / Controlled 先核对 TASK、项目规则、Git 状态和事实源，冻结允许/禁止范围与完成标准，再做最小必要改动。按风险运行适用的构建、测试、静态检查或真实环境验证，检查 diff 归属与 `git diff --check`，按 policy 决定是否进入独立 Review，并分别记录下述状态。

验证分两级执行，不把完整套件当成每次迭代的固定成本：

- 迭代验证：patch 期间只运行最贴近风险的快速验证——受影响的构建目标、测试子集和专项自测；相互独立的验证项并行运行。
- 闸门验证：请求独立 Review、UA、merge 或 delivery 前，针对最终 diff 核对完成标准与受影响风险，运行项目规定的适用验证。文档、指令和低风险局部修改只检查相关项；高风险或项目明确要求时执行完整套件。同一最终 diff 且输入/环境未变化的有效证据可复用；新改动或未解决风险才需补跑。真实宿主和用户验收证据不能由普通单测替代。

分层只控制自动验证的范围与时机；repair 轮次计数、独立 Review 触发、权限和证据硬门禁均不因此放宽。

验证失败时可在冻结范围内修复；范围、权限或风险改变时重新路由。任何无法安全继续的条件都写清阻塞原因和所需最小输入。

## Review 与 repair

Reviewer 必须只读、与 Engineer/Repairer 上下文隔离，并默认由当前 Harness 自身建立原生 Reviewer 上下文；不得自动调用其他 Harness，只有用户明确指定时才允许跨 Harness。原生隔离/只读能力缺失时保持 `Blocked/Pending`，主上下文自检不能记为独立 Review；各环境映射见 `CORE.md`。Reviewer 输出稳定 finding ID、P0～P3 和 `Passed / Needs Fix / Blocked`。

Tracked / Controlled 默认有 2 轮 `AutoRepair`；第 3 轮只能由 `CORE.md` 的 progress gate 授予。3 是自主循环上限，不是 AI 永久禁修：`Stop` 后用户可授权单次 `EscalatedRepair`，或授权 TASK/验收合同/外层 scope-bound 的 `RepairCampaignAuthority`；后者在 `core_product` 连续 4 次、`harness` 连续 5 次无实质进展后再回到用户裁决，硬停止条件立即生效。预算和 streak 不因换 TASK、模型、chain 或 finding 改名清零，不可逆外部动作不得自动重试。只读 gate 只给机械资格，最终 Allowed 由持有真实对话/harness/项目证据的 Orchestrator 提升。

## 状态边界

自动验证、Review、UA、Accepted、commit、merge、release、delivery 与 Closed 是独立状态，不能互相推导。

没有授权就不执行 merge、push、release、外部同步、删除或其他高影响动作。没有证据就不写“已完成”“已验收”或“已发布”。

## 按需 reference

只有当前动作确实需要时，最多选择一份最相关文件：

- 创建/更新 Tracked 或 Controlled TASK：`TASK_TEMPLATE.md`（符合单会话条件的 Tracked 任务可用 `TASK_TEMPLATE_BRIEF.md`）
- 需要完整执行细节：`WORKFLOW.md`
- 独立代码审查：`CODE_REVIEW_CHECKLIST.md`
- 用户动作等级：`ACCEPTANCE_GUIDE.md`
- Git/diff 专项：`GIT_PRECHECK.md` 或 `DIFF_REVIEW.md`
- v0.7 兼容/迁移：`V0.8_MIGRATION.md`

其他旧指南是兼容资料，不在 v0.8 默认运行路径内。`PROMPTS.md` 仅供人工复制短提示，不是必读依赖。

## 交接输出

简明说明修改文件及作用、验证及结果、Review / UA / commit / merge / release / Closed 的真实状态，以及剩余风险、未完成项和下一步。
