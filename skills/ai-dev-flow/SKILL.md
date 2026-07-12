---
name: ai-dev-flow
description: A reusable Git-first AI development workflow for solo developers. Use it to intake requirements, create tasks, plan changes, run bounded loops, batch low-risk work, coordinate waves, review diffs, hydrate memory, check harness compatibility, and manage acceptance.
---

# AI Dev Flow

这是一个面向个人开发者的通用 AI 辅助开发工作流 Skill。它帮助 AI coding agent 在长期软件项目中用 Markdown、Git、任务文件、任务看板、代码审查清单、用户动作等级和验收建议来管理状态。

本 Skill 不绑定任何具体业务、框架、语言或 agent 私有能力。支持 Skill 的 agent 可以按 Skill 使用；不支持 Skill 的 agent 可以把这些文件当作普通 Markdown 工作流说明读取。

## 中文唤醒词

日常可以用以下中文短句触发本 Skill：

- `AI开发流程`
- `开发流程`
- `项目流程`
- `项目工作流`
- `AI工作流`
- `Git检查`
- `Git基线`
- `任务流程`
- `任务看板`
- `拆任务`
- `diff审查`
- `代码审查流程`
- `验收建议流程`
- `用户动作等级`
- `批量小任务`
- `并行波次`
- `Parallel Wave`
- `先写方案`
- `状态汇总`
- `验收总结`
- `需求 Intake`
- `Loop Engineering`
- `triage_loop`
- `goal_loop`
- `review_repair_loop`
- `项目宪法`
- `项目记忆`
- `Harness 兼容`
- `Bug 诊断`
- `反馈闭环`
- `测试先行`
- `TDD`
- `需求拷问`
- `项目语境`
- `会话交接`
- `架构巡检`
- `实机信号`
- `实机复现`
- `测试信号`
- `RED GREEN`
- `HITL 复现`
- `用户回传证据`

推荐说法：

- `用 AI开发流程，帮我拆任务。`
- `按项目流程执行这个任务。`
- `走任务看板流程，先建任务文件。`
- `先做 Git检查，再执行任务。`
- `基于 diff审查这个任务。`
- `按代码审查流程复审这个任务。`
- `这个需求太大，先写方案。`
- `先做 Intake，不要直接拆任务。`
- `跑一次 triage_loop，只输出下一步建议。`

## 使用模式

开始工作前必须判断当前属于哪种模式，并在回复或任务文件中写明。不同模式不得混用。

- `init_project`：初始化项目工作流。
- `create_task`：把需求拆成任务。
- `plan_task`：大任务先写 plan / RFC。
- `execute_task`：执行单个任务。
- `review_task`：独立审查任务。
- `repair_task`：根据审查意见修复。
- `close_task`：按用户动作等级完成验收或决策后关闭任务。
- `status_report`：汇总当前项目状态。

格式路由（v0.7）：`create_task` 新建 A/B 且 `overlays=none`、非 Batch、非 Wave、非 `real_env_signal` 时使用 `references/TASK_TEMPLATE_COMPACT.md`；C/D、Batch、Wave、`real_env_signal` 和 existing legacy TASK 使用 Full/Legacy `references/TASK_TEMPLATE.md`。条件未知时停止并写“待确认”。`execute_task`、`review_task`、diff-review、`repair_task`、acceptance、`close_task` 必须保持任务现有格式；不得在 Compact TASK 中重建“代码审查”“Diff 审查”“合并状态”“提交 / 合并”等 legacy 双写段落。Compact 后续触发复杂路径时停止并待确认，不自动迁移。

模式边界：

- `create_task` 模式只拆任务，不直接执行代码。
- `review_task` 模式只审查，不直接修复。
- `repair_task` 模式只处理审查意见，不扩大范围。
- `close_task` 模式只能基于验收结果关闭任务，不补做开发。

## 什么时候使用

在以下场景使用本 Skill：

- 初始化一个长期维护的软件项目工作流。
- 把需求拆成小任务，并建立可追踪的任务文件。
- 建立 `docs/tasks/` 和 `docs/TASK_BOARD.md`。
- 让 AI agent 在明确边界内执行任务。
- 检查 Git 状态、建立 Git baseline、记录 base commit。
- 按任务等级决定是否在主项目、独立分支或 Worktree 执行。
- 对代码任务进行独立审查。
- 按用户动作等级完成验收或决策后，再由用户确认是否合并回主项目。

## 什么时候不要使用

以下场景不要启用完整流程：

- 一次性小脚本。
- 临时 demo 或试验性草稿。
- 用户明确要求不要建立流程。
- 只需要简单回答问题，不涉及项目文件。
- 当前项目没有长期维护、审查、验收或状态沉淀需求。

## 核心工作流

优先按下面顺序执行：

1. 初始化项目工作流。
2. 写 `docs/PROJECT_INDEX.md`，说明项目入口、关键目录、运行和验证方式。
3. 写 `docs/TASK_BOARD.md`，作为任务总看板。
4. 为每个任务写 `docs/tasks/<TASK-ID>.md`。
5. 每个任务必须有明确模式、状态、完成标准、验证方式和停止条件。
6. 任务开始前执行 Git precheck：确认是否是 Git 仓库、当前分支、HEAD、工作区状态、远程和不应提交文件。
7. 如果当前项目不是 Git 仓库，代码任务不得开始；先建议建立 Git baseline。
8. 代码任务开始前记录 base commit，并判断任务等级。
9. 大任务先写 `docs/plans/` 下的 plan 或 RFC，再拆成可执行任务。
10. 执行时按任务状态机流转，不能跳过 Review 和验收建议。
11. 执行后更新任务文件，记录修改文件、验证命令、验证结果、审查结论、用户动作等级和交接摘要。
12. 审查通过后给出用户动作等级和验收建议。
13. 按用户动作等级完成必要的摘要确认、文档阅读、证据验收、本地运行、实机业务测试、回归验收或用户决策后，再关闭任务。
14. 仅在用户明确确认后，执行需要确认的操作并更新最终状态。

v0.6.0 新增设计级能力：

- Intake：需求进入 `plan_task` / `create_task` 前的记录层，不是 TASK，不直接执行代码。
- Loop Engineering：编排已有模式，不替代 TASK、Batch、Wave 或任务状态。
- Review-Repair Loop：有限轮次审查修复循环，Reviewer 不修复，Repairer 不扩大范围。
- Role Guide：声明 Orchestrator / Planner / Engineer / Reviewer / Verifier / Repairer / Archivist 当前角色。
- Project Constitution：项目 MUST / SHOULD / MUST NOT 硬规则模板。
- Memory：长期项目知识沉淀，不写聊天全文、密钥、本机路径或未确认猜测。
- GitHub Issues Optional Backend：仅提供映射设计，不自动同步 issue。
- Harness Compatibility：说明不同 agent / CLI / IDE 的能力边界和降级方式。
- Bug 诊断（bug_diagnosis）：根因不清时先建立证据、假设和复现信号，不直接猜测修复。
- 测试先行（tdd_task）：用 RED / GREEN 记录行为级失败和通过信号。
- 需求拷问（requirement_grilling）：需求模糊或高风险时先问阻塞问题并记录默认假设。
- 项目语境（project_context）：沉淀长期项目术语、验证经验和常见误解。
- 会话交接（session_handoff）：跨会话继续任务时记录下一会话应读文件和不要重复尝试的路线。
- 架构巡检（architecture_review）：只读分析反复返工、无测试缝隙或边界混乱，不直接重构。
- 实机测试信号复现（real_env_signal）：把用户实机反馈转换成 RED / GREEN / SIGNAL 和 HITL 回传证据。

## Single / Batch / Wave

- Single Task：一个执行会话只执行一个任务，适合 C/D、高风险、边界不清、核心模块、真实环境、回归验收或用户决策任务。
- Batch：一个执行会话顺序执行多个 A/B 小任务，不是并行；任务仍独立记录，批量审查必须逐任务输出结论。
- Parallel Wave：多个执行会话同时执行多个互不冲突任务；并行前必须检查文件锁、模块锁、依赖、UA 等级和用户确认。
- `TASK` 是最小责任单位；Batch 是小任务执行 / 审查打包方式；Wave 是多个执行会话的并行调度方式。
- Batch / Wave 都不得吞掉 TASK 边界，不得只输出“Batch 通过”或“Wave 通过”。
- Loop 不得吞掉 TASK 边界；Loop 完成不等于任务 Accepted 或 Closed。

## Agent 行为规则

执行本 Skill 时遵守以下规则：

- 先读项目已有规则，包括 `AGENTS.md`、`README.md`、`docs/PROJECT_INDEX.md`、`docs/TASK_BOARD.md` 和相关任务文件。
- 开始前必须判断当前工作模式，不同模式不得混用。
- 如果需求模糊，先做 Intake；Intake 不是 TASK，不直接执行代码。
- 如果使用 Loop，必须声明 Loop 类型和当前子模式；Loop 不是任务状态。
- 当前轮输出应声明角色；Reviewer 不修复，Engineer 不自我批准。
- 代码任务开始前必须检查 Git 状态；没有 Git baseline 不得开始代码任务。
- 代码任务必须记录 base commit；审查必须基于 base commit 到当前工作区或 HEAD 的 diff。
- 任务是否需要分支取决于任务等级：小任务不强制分支，中等任务建议分支，大任务或高风险任务必须使用分支或 Worktree。
- 工作区已有未提交改动时，不得直接开始新任务；必须先判断这些改动属于哪个任务。
- 不要跨任务修改无关模块。
- 不要一次性执行超大任务；先拆分，必要时先写 plan 或 RFC。
- 不要一边拆任务一边执行代码。
- 不要一边审查一边修复。
- 不要在任务范围不清时继续执行。
- 支持 A/B 小任务批量执行和批量审查；C/D 任务默认单独执行和单独审查。
- Batch 和 Wave 不同：批量执行不是多任务并行写代码，Parallel Wave 才是多执行会话并行。
- 并行执行不是默认行为，必须用户确认；ai-dev-flow 不禁止 harness 或模型自动使用 subagents，但写代码 subagents 必须受控，并且不得绕过 TASK 边界、diff 记录、验证、审查和用户确认。
- 并行前必须检查文件锁、模块锁、依赖、任务等级和 UA 等级。
- Parallel Wave 中代码任务默认需要独立分支或 Worktree。
- 多个代码执行会话不得默认共享同一工作区。
- D 级和 UA5 / UA6 / UA7 任务默认不得进入代码并行。
- Batch / Wave 中每个任务仍是独立记录、审查和验收单位。
- Review Hub 可以审查 Batch / Wave，但必须逐任务输出结论。
- B 级小代码 Batch 必须保持 per-task diff 归属清晰。
- 批量任务必须保持 diff 可按任务拆分；diff 无法拆分时必须标记“diff 归属不清”并停止强行通过。
- 修改前先给简短计划，说明目标、拟改文件、风险和验证方式。
- 修改后更新任务状态，不要只把状态留在聊天记录里。
- 所有状态必须写入项目文件；不要把聊天记录作为唯一状态来源。
- 面向用户的状态、模式、Loop、UA、P 等字段应优先显示中文说明，并保留英文标识；示例：任务状态：需修复（Needs Fix）；当前模式：审查任务（review_task）。
- 完成标准必须可验证；没有验证方式的任务不能标记为验收通过。
- 完成任务后必须给出用户动作等级：UA0 / UA1 / UA2 / UA3 / UA4 / UA5 / UA6 / UA7 / 待确认。
- UA0 表示无需用户验收，不表示 agent 默认可以把任务标记为 `Closed`；除非用户或项目规则授权，agent 只能建议关闭。
- 人工验收不等于人工代码审查；用户不需要逐行审代码。
- 不要默认要求用户实机测试，也不要默认跳过验收。
- 用户主要验证可观察行为、关键流程、输出结果、错误提示、回归影响和是否符合需求。
- 当用户反馈 UA4 / UA5 / UA6 / UA7 验收失败时，先执行 Acceptance Feedback Gate：只读诊断、分类并记录证据；只有确认属于当前 TASK 范围内的原任务未完成或本轮回归，才建议进入 `review_repair_loop`。
- 用户反馈 bug、变慢、不符合预期或验收失败时，先定义 RED 失败信号、GREEN 通过信号和 SIGNAL 证据来源；agent 不能亲自复现时，应进入 `real_env_signal` 并给出用户实机 HITL 回传模板。
- 根因不清时先进入 Bug 诊断（bug_diagnosis）；没有测试信号或证据时，任务应建议阻塞（Blocked）或等待补充，不得盲修。
- 可测试代码优先使用测试先行（tdd_task）；bug 修复验证必须证明用户描述的 RED 消失，而不只是构建通过。
- 临时诊断日志必须有唯一前缀，修复后必须清理或明确转为正式日志。
- 代码质量和 diff 风险由 AI 审查、自动验证和 diff 审查辅助判断。
- 未通过代码审查时，不得建议合并。
- 审查线程只做审查和判断，不直接改代码。
- Review-Repair Loop 默认最多 2 轮 repair，超过次数或仍有 P0/P1 时必须人工接管。
- `review_task` 必须按现有格式写回：Compact 更新 Workflow Contract / Outcome，Full/Legacy 更新“代码审查”和“Diff 审查”，也可使用项目约定的审查记录；只在聊天中输出审查意见不算完成审查。
- 审查线程可以更新审查记录和 `docs/TASK_BOARD.md` 的 Review 状态，但不得修改业务代码。
- 不要盲目执行 `git add .`；提交前必须检查暂存内容。
- 不要自动执行危险 Git 操作，包括未确认的 merge、push、release、reset、rebase、删除分支或清理文件。
- 不要自动创建、关闭或同步 GitHub Issue；v0.6.0 只提供可选后端设计。
- 不要声称当前 Skill 具备自动脚本、自动 GitHub 同步或自动多 agent 调度能力。
- 不依赖某个 agent 的私有能力；默认使用 Markdown、Git、命令行和项目内文档。
- 状态必须写入项目文件，聊天记录只能作为补充说明。

## 需要读取的参考文件

根据任务类型加载 `references/` 下的文件：

- 完整流程：[`references/WORKFLOW.md`](references/WORKFLOW.md)
- Git 前置检查：[`references/GIT_PRECHECK.md`](references/GIT_PRECHECK.md)
- Git 任务分级和执行规则：[`references/GIT_WORKFLOW.md`](references/GIT_WORKFLOW.md)
- Diff 审查机制：[`references/DIFF_REVIEW.md`](references/DIFF_REVIEW.md)
- 任务状态机：[`references/STATUS_MACHINE.md`](references/STATUS_MACHINE.md)
- 安全规则和停止条件：[`references/SAFETY_RULES.md`](references/SAFETY_RULES.md)
- 验证指南：[`references/VALIDATION_GUIDE.md`](references/VALIDATION_GUIDE.md)
- 用户动作等级和验收指南：[`references/ACCEPTANCE_GUIDE.md`](references/ACCEPTANCE_GUIDE.md)
- Intake 指南：[`references/INTAKE_GUIDE.md`](references/INTAKE_GUIDE.md)
- Loop Engineering 指南：[`references/LOOP_ENGINEERING_GUIDE.md`](references/LOOP_ENGINEERING_GUIDE.md)
- Review-Repair Loop：[`references/REVIEW_REPAIR_LOOP_GUIDE.md`](references/REVIEW_REPAIR_LOOP_GUIDE.md)
- 角色指南：[`references/ROLE_GUIDE.md`](references/ROLE_GUIDE.md)
- 项目宪法模板：[`references/PROJECT_CONSTITUTION_TEMPLATE.md`](references/PROJECT_CONSTITUTION_TEMPLATE.md)
- 项目记忆指南：[`references/MEMORY_GUIDE.md`](references/MEMORY_GUIDE.md)
- GitHub Issues 可选后端：[`references/GITHUB_ISSUES_BACKEND.md`](references/GITHUB_ISSUES_BACKEND.md)
- Harness 兼容说明：[`references/HARNESS_COMPAT.md`](references/HARNESS_COMPAT.md)
- Bug 诊断：[`references/BUG_DIAGNOSIS_GUIDE.md`](references/BUG_DIAGNOSIS_GUIDE.md)
- 测试先行：[`references/TDD_GUIDE.md`](references/TDD_GUIDE.md)
- 需求拷问：[`references/REQUIREMENT_GRILLING_GUIDE.md`](references/REQUIREMENT_GRILLING_GUIDE.md)
- 项目语境：[`references/PROJECT_CONTEXT_GUIDE.md`](references/PROJECT_CONTEXT_GUIDE.md)
- 会话交接：[`references/HANDOFF_GUIDE.md`](references/HANDOFF_GUIDE.md)
- 架构巡检：[`references/ARCHITECTURE_REVIEW_GUIDE.md`](references/ARCHITECTURE_REVIEW_GUIDE.md)
- 实机测试信号复现：[`references/REAL_ENV_SIGNAL_GUIDE.md`](references/REAL_ENV_SIGNAL_GUIDE.md)
- Loop 状态模板：[`references/LOOP_STATE_TEMPLATE.md`](references/LOOP_STATE_TEMPLATE.md)
- 批量小任务：[`references/BATCH_TASK_GUIDE.md`](references/BATCH_TASK_GUIDE.md)
- 并行波次：[`references/PARALLEL_WAVE_GUIDE.md`](references/PARALLEL_WAVE_GUIDE.md)
- 项目适配模板：[`references/PROJECT_OVERLAY_TEMPLATE.md`](references/PROJECT_OVERLAY_TEMPLATE.md)
- Compact A/B 任务模板：[`references/TASK_TEMPLATE_COMPACT.md`](references/TASK_TEMPLATE_COMPACT.md)
- Full/Legacy 任务模板：[`references/TASK_TEMPLATE.md`](references/TASK_TEMPLATE.md)
- 任务看板模板：[`references/TASK_BOARD_TEMPLATE.md`](references/TASK_BOARD_TEMPLATE.md)
- 代码审查清单：[`references/CODE_REVIEW_CHECKLIST.md`](references/CODE_REVIEW_CHECKLIST.md)
- 决策记录模板：[`references/DECISIONS_TEMPLATE.md`](references/DECISIONS_TEMPLATE.md)
- 中文术语表：[`references/GLOSSARY.zh-CN.md`](references/GLOSSARY.zh-CN.md)
- 可复制提示词：[`references/PROMPTS.md`](references/PROMPTS.md)
- 可合并到项目 `AGENTS.md` 的规则：[`references/AGENTS_COMPAT.md`](references/AGENTS_COMPAT.md)
- 脚本预留说明：[`scripts/README.md`](scripts/README.md)

## 默认执行建议

如果用户只是要求“建立项目工作流”，按 `init_project` 模式读取 `WORKFLOW.md`、`STATUS_MACHINE.md`、`VALIDATION_GUIDE.md`、`ACCEPTANCE_GUIDE.md`、`TASK_TEMPLATE_COMPACT.md`、`TASK_TEMPLATE.md`、`TASK_BOARD_TEMPLATE.md` 和 `AGENTS_COMPAT.md`，然后在项目中创建最小文档结构。初始化时应建议将 `AGENTS_COMPAT.md` 中适合本项目的关键规则合并到项目 `AGENTS.md`，但不得覆盖已有项目规则。如需完整安装到项目，还必须读取 `GIT_PRECHECK.md`、`GIT_WORKFLOW.md` 和 `DIFF_REVIEW.md`。

如果用户要求“先收集需求”或需求边界不清，按 Intake 流程读取 `INTAKE_GUIDE.md`，输出 `INTAKE-xxx.md` 草案或同结构内容；不得直接拆任务或改代码。

如果用户反馈 bug、慢、不符合预期或验收失败，读取 `BUG_DIAGNOSIS_GUIDE.md` 和 `ACCEPTANCE_GUIDE.md`；先建立证据和 RED / GREEN / SIGNAL，不得直接猜测修复。

如果用户反馈 UA4 / UA5 / UA6 / UA7 验收失败且 agent 无法亲自复现，读取 `ACCEPTANCE_GUIDE.md`、`REAL_ENV_SIGNAL_GUIDE.md` 和 `BUG_DIAGNOSIS_GUIDE.md`；先输出用户实机 HITL 步骤和回传证据模板。

如果用户要求测试先行、TDD、RED GREEN，或 bug 已有复现路径、涉及复杂逻辑，读取 `TDD_GUIDE.md`，优先建立行为级失败测试或替代验证信号。

如果需求模糊、高风险或可能扩大范围，读取 `REQUIREMENT_GRILLING_GUIDE.md` 和 `INTAKE_GUIDE.md`；只问阻塞问题，非阻塞模糊点写入 Intake 或风险。

如果需要沉淀项目术语、长期知识或跨任务验证经验，读取 `PROJECT_CONTEXT_GUIDE.md` 和 `MEMORY_GUIDE.md`，更新 `docs/memory/` 前不得记录聊天全文、密钥、本机路径或未确认猜测。

如果用户要求交接、换会话或当前任务需要后续会话继续，读取 `HANDOFF_GUIDE.md`，输出会话交接（session_handoff）摘要。

如果任务反复返工、没有测试缝隙、AI 容易误改或架构边界混乱，读取 `ARCHITECTURE_REVIEW_GUIDE.md`；架构巡检只读，不直接重构。

如果用户要求“跑 Loop”或“下一步建议”，先读取 `LOOP_ENGINEERING_GUIDE.md` 和 `LOOP_STATE_TEMPLATE.md`。`triage_loop` 和 `status_loop` 默认只读；`goal_loop` 必须逐步声明子模式；`review_repair_loop` 还需读取 `REVIEW_REPAIR_LOOP_GUIDE.md`。

如果用户要求“执行某个任务”，按 `execute_task` 模式读取当前 TASK 文件、`AGENTS.md`、`README.md`、`docs/PROJECT_INDEX.md`、`docs/TASK_BOARD.md`、`SAFETY_RULES.md`、`VALIDATION_GUIDE.md`、`GIT_PRECHECK.md`、`GIT_WORKFLOW.md` 和 `CODE_REVIEW_CHECKLIST.md`，确认状态、边界、等级、完成标准、验证方式和停止条件，再开始修改。

如果用户要求“批量执行小任务”或“批量审查小任务”，先读取 `BATCH_TASK_GUIDE.md`、`TASK_BOARD.md` 和候选 TASK 文件，只允许 A/B 小任务进入 Batch；批量执行顺序完成，批量审查逐任务给结论。

如果用户要求“并行处理任务”或“开一组 Wave”，先读取 `PARALLEL_WAVE_GUIDE.md`、`TASK_BOARD.md` 和候选 TASK 文件，完成文件锁、模块锁、依赖、UA 等级、工作区隔离和用户确认检查后，才允许启动并行执行会话。代码任务默认使用独立分支或 Worktree，多个代码执行会话不得默认共享同一工作区。

如果用户要求“审查任务”，按 `review_task` 模式只读取当前 TASK 文件、`DIFF_REVIEW.md`、`CODE_REVIEW_CHECKLIST.md`、验证记录，以及 base commit 到 HEAD 或当前工作区 diff。必须按当前格式写回审查结论：Compact 更新 Workflow Contract / Outcome，Full/Legacy 更新“代码审查”和“Diff 审查”；必要时更新 `docs/TASK_BOARD.md` 的 Review 状态。只在聊天中输出不算完成审查，不得直接改业务代码。
