# ai-dev-flow

`ai-dev-flow` 是一个可复用的 AI 辅助开发项目工作流 Skill。它面向个人开发者，帮助你把长期软件项目拆成可追踪的小任务，并通过任务文件、任务看板、计划文档、代码审查、用户动作等级和验收建议来管理 AI agent 的工作边界。

它不绑定任何具体项目、编程语言、技术栈或 agent。支持 Skill 的 agent 可以直接加载它；不支持 Skill 的 agent 也可以把它当作普通 Markdown 工作流说明阅读。

## 适合哪些项目

- 会持续维护数周、数月或更久的软件项目。
- 需要把需求拆成多个小任务逐步推进的项目。
- 需要保留任务状态、验证记录和审查结论的项目。
- 需要让 AI agent 在明确边界内修改代码的项目。
- 需要用户按动作等级验收或决策后再决定是否合并的项目。

## 不适合哪些项目

- 一次性小脚本。
- 临时 demo。
- 只需要问答，不需要修改项目文件。
- 用户明确希望快速试验，不想建立任务流程。
- 没有 Git、任务文档或审查需求的小型草稿。

## 使用模式

本 Skill 支持 8 种模式：

- `init_project`：初始化项目工作流。
- `create_task`：把需求拆成任务。
- `plan_task`：大任务先写 plan / RFC。
- `execute_task`：执行单个任务。
- `review_task`：独立审查任务。
- `repair_task`：根据审查意见修复。
- `close_task`：按用户动作等级完成验收或决策后关闭任务。
- `status_report`：汇总当前项目状态。

agent 开始前应先判断模式。不同模式不要混用，例如审查时只审查，不直接修复。

v0.6.0 还增加 Loop 编排概念：

- `triage_loop`：只读分拣任务，推荐下一步、Batch 或 Wave 候选。
- `goal_loop`：编排 execute、validation、review、repair 和验收建议。
- `review_repair_loop`：有限审查修复循环，默认最多 2 轮 repair。
- `status_loop`：只读状态汇总。

Loop 不是任务状态，不替代 TASK、Batch 或 Wave。

## 给支持 Skill 的 agent 使用

把整个 `skills/ai-dev-flow/` 目录放到该 agent 能识别的 Skill 目录中。然后在对话中说明：

```text
请使用 ai-dev-flow，帮我为这个项目建立 AI 辅助开发工作流。
```

也可以直接用中文唤醒词：

```text
用 AI开发流程，帮我拆任务。
```

```text
按项目流程执行 docs/tasks/TASK-001.md。
```

```text
走代码审查流程，复审这个任务。
```

或：

```text
请使用 ai-dev-flow，按 docs/tasks/TASK-001.md 执行这个任务。
```

agent 应先读取 `SKILL.md`，再按任务需要读取 `references/` 下的模板和说明。

## 给不支持 Skill 的 agent 使用

如果 agent 不支持 Skill，请让它先阅读：

- `skills/ai-dev-flow/SKILL.md`
- `skills/ai-dev-flow/references/WORKFLOW.md`
- `skills/ai-dev-flow/references/PROMPTS.md`

常用中文唤醒词：

- `AI开发流程`
- `项目流程`
- `任务流程`
- `任务看板`
- `拆任务`
- `代码审查流程`
- `验收建议流程`
- `用户动作等级`
- `先写方案`

可以直接复制下面这段给 agent：

```text
你不需要原生支持 Skill。请把以下 Markdown 文件当作项目工作流说明读取，并按其中规则执行：

1. skills/ai-dev-flow/SKILL.md
2. skills/ai-dev-flow/references/WORKFLOW.md
3. skills/ai-dev-flow/references/PROMPTS.md

执行时不要依赖任何私有 agent 能力，只使用 Markdown、Git、任务文件、任务看板和审查清单这些通用机制。
```

## 安装方式

### 1. Skill-only 使用

保留完整 `skills/ai-dev-flow/` 目录，由支持 Skill 的 agent 按需读取 `SKILL.md` 和 `references/`。

### 2. 轻量安装到项目

适合小项目或已有流程项目。复制或合并：

- `references/AGENTS_COMPAT.md`
- `references/TASK_TEMPLATE.md`
- `references/TASK_BOARD_TEMPLATE.md`
- `references/CODE_REVIEW_CHECKLIST.md`

### 3. 完整安装到项目

适合长期项目或不支持 Skill 的 agent。建议额外复制到 `docs/workflow/`：

- `GIT_PRECHECK.md`
- `GIT_WORKFLOW.md`
- `DIFF_REVIEW.md`
- `STATUS_MACHINE.md`
- `SAFETY_RULES.md`
- `VALIDATION_GUIDE.md`
- `ACCEPTANCE_GUIDE.md`
- `BATCH_TASK_GUIDE.md`
- `PARALLEL_WAVE_GUIDE.md`
- `INTAKE_GUIDE.md`
- `LOOP_ENGINEERING_GUIDE.md`
- `REVIEW_REPAIR_LOOP_GUIDE.md`
- `ROLE_GUIDE.md`
- `PROJECT_CONSTITUTION_TEMPLATE.md`
- `MEMORY_GUIDE.md`
- `GITHUB_ISSUES_BACKEND.md`
- `HARNESS_COMPAT.md`
- `LOOP_STATE_TEMPLATE.md`

## 合并到项目 AGENTS.md

`references/AGENTS_COMPAT.md` 是一份可复制到项目 `AGENTS.md` 的通用规则。

推荐做法：

1. 先阅读项目已有 `AGENTS.md`。
2. 将 `references/AGENTS_COMPAT.md` 中适合本项目的规则合并进去。
3. 保留项目已有的特殊约定。
4. 删除与项目不相关或重复的规则。
5. 不要把本 Skill 的说明全文塞进 `AGENTS.md`，只保留 agent 执行项目任务时必须遵守的规则。

推荐在 `init_project` 模式中把这一步作为默认建议。这样支持 Skill 的 agent 仍可自动读取全局 Skill，而项目 `AGENTS.md` 也会沉淀一份精简规则，方便后续会话和不支持 Skill 的 agent 使用。

## 为什么需要任务状态机

任务状态机能避免“聊着聊着就当作完成”的问题。每个任务都应在 `Draft`、`Ready`、`In Progress`、`Blocked`、`Review`、`Needs Fix`、`Accepted`、`Closed`、`Deferred`、`Cancelled` 之间明确流转。

关键规则：

- 未审查任务不能直接标为 `Accepted`。
- 未完成必要用户动作或决策的任务不能标为 `Closed`。
- 状态不确定时写“待确认”，不要猜。

## 为什么完成标准必须可验证

AI agent 很容易把“看起来做了”误当成“已经完成”。完成标准必须能证明：

- 能通过命令验证；
- 能通过人工步骤验证；
- 或明确说明为什么验证不适用。

模糊写法如“优化体验”“完善功能”不适合作为完成标准。更好的写法是列出可观察结果、命令输出、截图、日志或人工验收步骤。

## 用户动作等级

任务完成后，agent 必须明确用户到底需要做什么，而不是笼统写“需要人工验收”。

- UA0：无需用户验收，agent 自证即可；适合纯格式整理、模板字段补充、版本同步、无业务影响的文档搬运。
- UA1：用户只看摘要；适合任务看板更新、任务编号整理、小范围文档修订。
- UA2：用户需要读文档 / 方案；适合架构方案、迁移 RFC、任务拆分、`AGENTS.md` 规则和重要提示词模板。
- UA3：用户只看验证证据，不自己运行；适合 agent 能构建、测试、提供日志、截图或 diff 审查证据，且无用户可见变化的任务。
- UA4：用户需要本地运行验收；适合普通前端页面、本地 CLI、本地桌面程序或不依赖真实业务环境的功能。
- UA5：用户需要实机业务测试；适合外部软件插件、真实设备、真实数据、真实账号、文件导出、批处理输出等 agent 无法完整复现的场景。
- UA6：用户需要回归验收；适合核心流程、通信协议、路径输出、登录授权、数据写入删除迁移等可能破坏旧功能的改动。
- UA7：必须用户决策，不能由 agent 接受；适合合并、删除旧实现、切换技术栈、新增大依赖、架构变化、发布或不可逆操作。

关键原则：

- 不是所有任务都需要用户实机测试。
- 不是所有任务都需要用户验收。
- 用户不需要逐行审代码。
- 代码质量和 diff 风险主要由 AI 审查、自动验证和 diff 审查辅助判断。
- 用户主要验证可观察行为、关键流程、输出结果、错误提示、回归影响和是否符合需求。
- UA0 也不等于自动关闭任务；默认只能写“建议关闭”，只有用户明确同意或项目规则已授权，agent 才能把任务状态标记为 `Closed`。

## 为什么审查和修复要分开

审查和修复分开，可以避免审查线程一边发现问题一边擅自改代码，导致任务边界失控。

- `review_task`：只审查，输出结论和严重等级。
- `repair_task`：只处理审查指出的问题。
- 超出当前任务的新问题，应记录为后续任务。

## 为什么任务膨胀时要停止

任务执行中如果发现影响范围扩大，应停止而不是硬做完。常见膨胀信号：

- 修改文件数量明显增加。
- 影响多个模块。
- 需要新增依赖。
- 需要改架构。
- 发现新需求。
- 原完成标准不够。

停止后应更新任务文件，标记 `Blocked` 或待确认，并建议拆分新任务。

## v0.6.0 Unreleased：Intake、Loop、Roles、Memory

v0.6.0 是文档、模板、提示词和路线图升级，不引入自动脚本或 agent runtime。

新增设计级能力：

- Intake：拆任务前记录需求、成功标准、非目标、约束和模糊点。
- Loop Engineering：把已有模式编排成受控循环，但不替代任务状态。
- Review-Repair Loop：默认最多 2 轮修复，Reviewer 不直接修复。
- Role Guide：声明 Orchestrator、Planner、Engineer、Reviewer、Verifier、Repairer、Archivist 的职责边界。
- Project Constitution：用 MUST / SHOULD / MUST NOT 记录项目硬规则。
- Memory：沉淀稳定项目知识，不保存聊天全文或敏感信息。
- GitHub Issues Optional Backend：只提供字段映射设计，不自动创建、关闭或同步 issue。
- Harness Compatibility：说明不同 agent / CLI / IDE 的能力边界。

关键边界：

- Intake 不是 TASK。
- Loop 不是任务状态。
- 角色不是会话，不要求每个角色单独开一个会话。
- Reviewer 不修复。
- Engineer 不自我批准。
- 所有危险操作必须用户确认。

默认最小会话模型：

- 总览会话：Orchestrator / Planner / Archivist。
- 执行会话：Engineer / Verifier / Repairer。
- 审核会话：Reviewer。

同一会话可以在不同阶段切换多个角色，但每一轮都要声明当前角色和当前模式，不能一边写代码一边批准自己的改动。

子 agent 是可选加速手段，不是默认依赖。推荐用于只读审查、验证、状态分拣和文档检查；不推荐默认让多个写代码的子 agent 共享同一工作区。支持可靠子 agent 的 harness 可以用 Reviewer / Verifier 子 agent 减少额外审核会话，但中高风险任务仍建议独立审核会话。

代码并行仍必须遵守 Parallel Wave：代码任务默认使用独立分支或 Worktree，并逐任务审查。子 agent 不得自动 merge、push、release 或 delete。

## 用 PROJECT_OVERLAY_TEMPLATE 适配具体项目

`references/PROJECT_OVERLAY_TEMPLATE.md` 用于把通用流程落到具体项目。推荐做法：

1. 复制模板到项目文档中。
2. 填写项目名称、技术栈、主要目录、构建命令、测试命令和运行命令。
3. 写清禁止修改区域、重点审查项、项目专用风险和用户动作等级 / 验收方式。
4. 将适合本项目的规则合并到 `AGENTS.md`。
5. 保持模板内容项目化，但不要把临时聊天结论当作唯一状态来源。

## 最小推荐项目结构

```text
project-root/
├── AGENTS.md
├── README.md
├── docs/
│   ├── PROJECT_INDEX.md
│   ├── TASK_BOARD.md
│   ├── DECISIONS.md
│   ├── CODE_REVIEW_CHECKLIST.md
│   ├── batches/
│   ├── plans/
│   ├── waves/
│   └── tasks/
└── src/
```

如果项目很小，可以先只建立：

```text
docs/
├── PROJECT_INDEX.md
├── TASK_BOARD.md
└── tasks/
```

## 为什么必须先建立 Git

Git 是本流程的基础，不是额外负担：

- 没有 Git 就没有稳定 diff。
- 没有 diff 就无法做可靠代码审查。
- 没有 base commit 就无法判断任务是否越界。
- AI agent 容易改无关文件，所以必须用 Git 约束范围。

如果项目还不是 Git 仓库，代码任务应先停止，建议建立 Git baseline：

1. 检查或创建 `.gitignore`。
2. 排除构建产物、依赖目录、日志、本机配置和密钥文件。
3. 执行 `git init`。
4. 设置主分支 `main`。
5. 创建初始 baseline commit。
6. 再开始代码任务。

注意：不要盲目执行 `git add .`，先检查要提交的文件。

## 小任务是否需要分支

不需要机械地“每个任务都建分支”。选择分支的依据是风险：

- A 级文档小任务不需要分支。
- B 级小代码任务不强制分支。
- C 级中等代码任务建议分支。
- D 级大任务和高风险任务必须使用分支或 Worktree。

小任务的重点是保持 diff 清晰、可回滚、可审查；大任务的重点是隔离风险。

## 批量小任务 Batch

Batch 用来解决“小任务太碎，每个都单独开会话和审查很麻烦”的问题。

- A/B 小任务可以批量处理。
- C/D 任务仍然默认单独处理。
- Batch 不是并行，是一个执行会话顺序处理多个小任务。
- `TASK` 仍然是最小记录单位，每个任务都要单独记录 diff、验证结果、审查结论和 UA 等级。
- A 级文档 Batch 可以一个 commit。
- B 级小代码 Batch 推荐每个 TASK 单独 commit；不单独 commit 时必须记录每个 TASK 的修改文件、diff 归属和验证结果。
- 多个 B 级任务修改同一文件时，默认拆成单任务或等待用户确认。
- 批量审查可以由一个 Review Hub 会话完成，但必须逐任务输出结论。
- 不得只写“Batch 通过”；必须写清每个任务是通过、需要修改还是不建议合并。

推荐默认规模：

- A 级文档任务：一次 3~8 个。
- B 级小代码任务：一次 2~3 个。
- A+B 混合：一次最多 5 个。
- C/D：不进入批次。

用户只根据每个任务自己的 UA 等级决定后续动作：看摘要、读文档、看证据、运行、实机测试、回归或做决策。

## 任务并行 Parallel Wave

Parallel Wave 用来解决“单个单个执行太慢”的问题，但它比 Batch 风险更高。

- Wave 是多个执行会话同时处理多个互不冲突任务。
- Batch 是顺序批处理，Wave 是真正并行。
- 并行前必须检查文件锁、模块锁、依赖关系、任务等级和 UA 等级。
- 并行执行不是默认行为，必须用户确认。
- 不默认启动多个执行会话，也不默认让 subagent 写代码。
- 进入 Parallel Wave 的代码任务默认使用独立分支或 Worktree。
- 多个代码执行会话不得默认共享同一工作区。
- 无法确认工作区隔离时，不得启动代码并行。
- 每个任务仍然独立记录 base commit、HEAD、diff 范围、验证结果和 UA 等级。
- Review Hub 可以集中审查 Wave，但必须逐任务输出结论。

默认并行规模：

- A 级文档任务：最多同时 5 个。
- B 级小代码任务：最多同时 2 个。
- C 级任务：最多 1 个代码任务，可并行 1~2 个 A 级文档任务。
- D 级任务：不和其他代码任务并行。
- 总执行会话数量建议不超过 3 个。

必须串行的情况：

- 修改同一文件或同一核心模块。
- 修改同一接口、协议、DTO 或 schema。
- 一个任务依赖另一个任务结果。
- 涉及架构、技术栈、构建、发布、依赖、核心服务、通信协议、数据写入删除迁移。
- 涉及真实软件插件、真实设备、真实数据、真实账号。
- 任务需要 UA5 / UA6 / UA7。
- 当前工作区已有来源不明的未提交改动。
- agent 无法判断冲突风险。

文件锁 / 模块锁判断：

- 两个任务预计修改文件重叠，不得并行。
- 两个任务预计影响模块重叠，默认不得并行，除非用户明确确认。
- 项目入口、构建配置、全局状态、协议 / DTO / schema、核心服务和主流程编排文件默认需要独占锁。

## 如何启动 Batch 或 Wave

启动一批小任务：

```text
请使用 ai-dev-flow，从 TASK_BOARD 里选择可批量执行的 A/B 小任务，创建 BATCH-001，但先不要执行。
```

执行一个批次：

```text
请使用 ai-dev-flow，按 docs/batches/BATCH-001.md 顺序执行批次内 A/B 小任务。
```

批量审查：

```text
请使用 Review Hub 审查 docs/batches/BATCH-001.md，必须逐任务输出结论。
```

推荐并行波次：

```text
请使用 ai-dev-flow，根据 TASK_BOARD 推荐一个 Parallel Wave，先做文件锁和模块锁检查，不要启动执行会话。
```

创建 Wave：

```text
请使用 ai-dev-flow，创建 docs/waves/WAVE-001.md，并记录文件锁、模块锁、base commit 和执行会话；等待我确认后再并行执行。
```

## 从需求到合并的完整例子

示例需求：

```text
我想给现有应用增加一个导出设置的功能。
```

推荐流程：

1. 用户提出需求。
2. 主控 agent 读取 `AGENTS.md`、`README.md`、`docs/PROJECT_INDEX.md`。
3. 主控 agent 判断任务是否过大。如果过大，先在 `docs/plans/` 写 plan 或 RFC。
4. 主控 agent 把需求拆成小任务，例如：
   - `TASK-001`：梳理现有设置结构。
   - `TASK-002`：实现导出设置。
   - `TASK-003`：补充验证和文档。
5. 主控 agent 在 `docs/TASK_BOARD.md` 登记任务。
6. 主控 agent 用 `references/TASK_TEMPLATE.md` 创建 `docs/tasks/TASK-002.md`。
7. 主控 agent 执行 Git precheck，记录 base commit，并判断 `TASK-002` 的 A/B/C/D 等级。
8. 执行 agent 按任务等级选择主项目、独立分支或 Worktree。
9. 执行 agent 修改代码后更新任务文件，记录修改文件、diff 范围、验证命令、验证结果和遗留问题。
10. 审查 agent 使用 `references/DIFF_REVIEW.md` 和 `references/CODE_REVIEW_CHECKLIST.md` 基于 diff 独立审查该任务。
11. 如果审查要求修改，执行 agent 按审查意见修复，并更新任务文件。
12. 用户按动作等级进行摘要确认、文档阅读、证据验收、本地运行、实机业务测试、回归验收或决策。
13. 如果任务使用分支或 Worktree，用户确认可以合并后，再执行合并操作。
14. 合并或提交完成后更新 `docs/TASK_BOARD.md` 和任务文件的最终状态。

注意：本 Skill 不要求 agent 自动合并，也不要求自动发布。合并、发布、删除分支等动作必须等用户明确确认。

## 复制到其他项目

可以把整个目录复制到其他项目中：

```text
skills/ai-dev-flow/
```

如果目标 agent 使用统一的全局 Skill 目录，也可以复制到该全局目录。复制后，先让 agent 读取 `README.md` 和 `SKILL.md`，再按项目情况把 `references/AGENTS_COMPAT.md` 的规则合并到目标项目 `AGENTS.md`。

## 后续路线图

v0.6.0 只提供 Markdown 工作流、模板、提示词和路线图，不包含自动脚本。

后续版本可以考虑增加只读检查脚本：

- 校验任务看板字段的脚本。
- 状态机一致性检查脚本。
- Loop State 汇总脚本。
- Batch 候选任务建议脚本。
- Wave 冲突检查脚本。
- Memory 更新候选脚本。
- GitHub Issue mapping preview 脚本。

这些脚本应默认只读，不自动执行 merge、push、release、reset、删除分支、删除文件、GitHub 同步或多 agent 调度。
