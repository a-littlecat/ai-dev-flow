# 可复制提示词

这些提示词适用于支持或不支持 Skill 的 AI coding agent。使用时请把路径、任务编号和项目名称替换成实际内容。

## 1. 初始化项目工作流

```text
请使用 AI开发流程，为当前项目建立最小 AI 辅助开发工作流。

要求：
1. 先读取项目已有 README、AGENTS.md、docs/ 目录和关键配置。
2. 不要修改业务代码。
3. 如缺少文档，请创建或建议创建：
   - docs/PROJECT_INDEX.md
   - docs/TASK_BOARD.md
   - docs/tasks/
   - docs/plans/
   - docs/DECISIONS.md
   - docs/CODE_REVIEW_CHECKLIST.md
4. 如需完整安装到项目，先读取 GIT_PRECHECK.md、GIT_WORKFLOW.md 和 DIFF_REVIEW.md，再建议创建 docs/workflow/，并放入 GIT_PRECHECK.md、GIT_WORKFLOW.md、DIFF_REVIEW.md、STATUS_MACHINE.md、SAFETY_RULES.md、VALIDATION_GUIDE.md。
5. 建议将 references/AGENTS_COMPAT.md 中适合本项目的关键规则合并到项目 AGENTS.md；只能追加或合并，不要覆盖已有项目规则。
6. 输出你准备创建或修改的文件、风险和验证方式。
7. 完成后说明修改内容和后续使用方式。
```

## 2. 拆任务

```text
请使用 AI开发流程，把下面需求拆成可执行的小任务。

需求：
<粘贴需求>

要求：
1. 先判断是否需要先写 plan 或 RFC。
2. 每个任务都要有任务编号、任务类型、目标、非目标、完成标准、建议执行位置和验证方式。
3. 不要把大范围重构塞进单个任务。
4. 输出可直接写入 docs/TASK_BOARD.md 的任务表。
5. 如需要创建任务文件，请使用 TASK_TEMPLATE.md 的结构。
```

## 3. 执行单个任务

```text
请使用 AI开发流程，执行任务文件：

docs/tasks/<TASK-ID>.md

要求：
1. 先读取 AGENTS.md、docs/PROJECT_INDEX.md、docs/TASK_BOARD.md 和该任务文件。
2. 严格遵守任务的目标、非目标和禁止修改范围。
3. 修改前先给简短计划，说明拟改文件、风险和验证方式。
4. 代码任务应先判断 A/B/C/D 等级，再按等级选择主项目、独立分支或 Worktree；不要机械地让所有代码任务都使用 Worktree 或分支。
5. 修改后更新任务文件，记录修改文件、验证命令、验证结果和遗留问题。
6. 不要自动合并、发布、删除分支或删除 Worktree。
```

## 4. 完成后自查

```text
请使用 AI开发流程，对当前代码任务做完成后自查。

要求：
1. 对照 docs/tasks/<TASK-ID>.md 的完成标准逐项检查。
2. 检查是否修改了无关文件。
3. 检查是否引入额外重构或额外依赖。
4. 汇总已运行的验证命令和结果。
5. 说明未验证项和原因。
6. 更新任务文件中的“执行结果”“修改文件”“遗留问题”和“下一步建议”。
7. 根据 ACCEPTANCE_GUIDE.md 写出用户动作等级和验收建议。
8. 如果是 UA0，只能建议关闭任务；除非用户或项目规则授权，不要自动标记 Closed。
9. 如果不满足完成标准，请不要声称任务完成。
```

## 5. 独立代码审查

```text
请使用 代码审查流程，对任务 docs/tasks/<TASK-ID>.md 做独立代码审查。

要求：
1. 只审查，不直接改代码。
2. 读取任务文件、DIFF_REVIEW.md、CODE_REVIEW_CHECKLIST.md、相关 diff 和验证记录。
3. 判断是否只完成当前任务，是否有无关修改，是否满足完成标准。
4. 输出结论：通过 / 需要修改 / 不建议合并。
5. 必须包含：
   - 必须修改项
   - 建议修改项
   - 风险
   - 推荐验证步骤
6. 将审查结论写回任务文件的“代码审查”和“Diff 审查”段落，必要时更新 docs/TASK_BOARD.md 的 Review 状态。
7. 只在聊天中输出审查意见不算完成审查。
8. 未通过审查时，不要建议合并。
```

## 6. 根据审查修复

```text
请使用 AI开发流程，根据以下审查意见修复任务：

任务文件：
docs/tasks/<TASK-ID>.md

审查意见：<粘贴审查意见>

要求：
1. 只处理审查中的必须修改项，建议修改项需先判断是否属于当前任务。
2. 不要扩大任务范围。
3. 修改后运行必要验证。
4. 更新任务文件中的修复记录、验证结果和审查状态。
5. 如果某条意见不应修改，请说明原因并等待确认。
```

## 7. 验收建议前总结

```text
请使用 验收建议流程，为任务 docs/tasks/<TASK-ID>.md 生成一份验收建议前总结。

要求：
1. 用简洁中文说明任务目标是否完成。
2. 列出修改文件和主要改动。
3. 列出已运行的验证命令和结果。
4. 列出审查结论和剩余风险。
5. 给出用户动作等级和用户具体需要做什么。
6. 说明是否需要用户实机测试。
7. 不要声称已合并，除非项目文件中已有明确记录。
```

## 8. 大任务先写 plan / RFC

```text
请使用 先写方案，为下面的大任务写 plan / RFC，不要直接改代码。

需求：
<粘贴需求>

要求：
1. 先读取项目已有文档和相关代码结构。
2. 写明背景、目标、非目标、方案、风险、验证方式和拆分任务。
3. 明确哪些内容需要用户确认。
4. 把可执行部分拆成多个小任务。
5. 不要创建超大单体任务。
```

## 9. 适配到新项目

```text
请把 AI开发流程 适配到当前项目。

要求：
1. 先读取 skills/ai-dev-flow/SKILL.md、references/WORKFLOW.md 和 references/AGENTS_COMPAT.md。
2. 再读取当前项目已有 AGENTS.md、README.md 和 docs/。
3. 输出一份适配计划，说明哪些规则可以直接使用，哪些需要按项目调整。
4. 如需要修改 AGENTS.md，请只合并必要规则，不要覆盖项目已有规则。
5. 不要修改业务代码。
6. 完成后说明如何创建任务文件、如何更新任务看板、如何进行代码审查和用户动作等级验收。
```

## 10. Git 初始化

```text
请使用 AI开发流程，为当前项目建立 Git baseline。

要求：
1. 先检查是否已经是 Git 仓库。
2. 检查或建议创建 .gitignore。
3. 排除构建产物、依赖目录、日志、本机配置和密钥文件。
4. 不要盲目 git add .。
5. 输出建议提交文件清单和风险点。
6. 等我确认后再执行初始化或提交。
```

## 11. 任务前 Git 检查

```text
请使用 Git检查，在执行 docs/tasks/<TASK-ID>.md 前检查仓库状态。

要求：
1. 检查 Git 仓库、当前分支、HEAD、远程、工作区状态。
2. 记录 base commit。
3. 判断是否有未提交改动和不应提交文件。
4. 如果工作区不清楚，先停止并说明需要确认的内容。
```

## 12. 判断任务等级

```text
请使用 AI开发流程，判断下面任务的 A/B/C/D 等级：
<粘贴任务描述或任务文件路径>

要求：
1. 说明判断依据。
2. 给出是否需要分支、是否需要 Worktree、是否需要独立审查。
3. 不要把每个小任务都机械地升级为分支任务。
```

## 13. A / B 级小任务执行

```text
请使用 AI开发流程，按 A/B 级小任务执行 docs/tasks/<TASK-ID>.md。

要求：
1. 在主项目执行即可，不强制分支。
2. 先记录 base commit。
3. 保持 diff 小而清晰。
4. commit 前执行 pre-commit diff 审查。
5. 不要盲目 git add .。
```

## 14. C 级分支任务执行

```text
请使用 AI开发流程，按 C 级任务执行 docs/tasks/<TASK-ID>.md。

要求：
1. 建议创建 feature/TASK-xxx-short-name 或 fix/TASK-xxx-short-name 分支。
2. 记录 base commit。
3. 修改后基于 <base_commit>..HEAD 做 post-commit diff 审查。
4. 审查通过后再给出用户动作等级和验收建议。
5. 未经我确认不得 merge。
```

## 15. D 级 Worktree 任务执行

```text
请使用 AI开发流程，按 D 级高风险任务执行 docs/tasks/<TASK-ID>.md。

要求：
1. 优先使用 Worktree，且 Worktree 不放在主项目内部。
2. 创建 Worktree 前，先确认主项目任务文件和规则已提交。
3. 记录 base commit 和 Worktree 路径。
4. 必须进行独立 diff 审查。
5. 未经我确认不得 merge、push 或删除 Worktree。
```

## 16. pre-commit diff 审查

```text
请使用 diff审查，对当前 A/B 级任务做 pre-commit diff review。

要求：
1. 运行 git status --short、git diff --stat、git diff --name-only、git diff、git diff --check。
2. 只审查当前任务 diff。
3. 标出范围越界文件和不应提交文件。
4. 给出是否允许 commit、是否允许进入验收建议和建议用户动作等级。
5. 将 diff 审查结论写入任务文件的“Diff 审查”段落；只在聊天中输出不算完成审查。
```

## 17. post-commit diff 审查

```text
请使用 diff审查，对 docs/tasks/<TASK-ID>.md 做 post-commit diff review。

Base commit：<base_commit>

要求：
1. 基于 <base_commit>..HEAD 审查。
2. 查看 diff stat、name-only、完整 diff、diff --check 和 git log。
3. 只审查当前任务改动，不把历史问题算作本任务问题。
4. 给出是否允许进入验收建议、建议用户动作等级和是否允许合并。
5. 将 diff 审查结论写入任务文件的“Diff 审查”段落；只在聊天中输出不算完成审查。
```

## 18. 根据 diff 审查意见修复

```text
请使用 AI开发流程，根据以下 diff 审查意见修复 docs/tasks/<TASK-ID>.md：
<粘贴审查意见>

要求：
1. 只处理当前任务 diff 中的问题。
2. 不要扩大范围。
3. 修复后重新运行对应 diff 审查命令。
4. 更新任务文件中的审查状态、修改文件和验证结果。
```

## 19. 工作区已有未提交改动

```text
请使用 Git检查，处理当前工作区已有未提交改动。

要求：
1. 先运行 git status --short 和必要的 diff 命令。
2. 判断改动是否属于当前任务。
3. 区分应提交、应拆分、应忽略、应停止等待确认的内容。
4. 不要在来源不清时开始新任务。
5. 不要盲目 git add .。
```

## 20. 判断当前模式

```text
请使用 AI开发流程，先判断当前请求属于哪种模式：
init_project / create_task / plan_task / execute_task / review_task / repair_task / close_task / status_report。

要求：
1. 说明判断依据。
2. 说明本模式下可以做什么、不能做什么。
3. 不同模式不得混用。
4. 如果模式不清，先停下并提问。
```

## 21. 初始化项目

```text
请使用 init_project 模式初始化当前项目工作流。

要求：
1. 先读项目现有 README、AGENTS.md、docs/ 和关键入口文档。
2. 建议或创建最小任务文档结构。
3. 补充任务状态机、验证指南、安全规则和审查清单。
4. 如需完整安装到项目，先读取 GIT_PRECHECK.md、GIT_WORKFLOW.md 和 DIFF_REVIEW.md，再建议把 GIT_PRECHECK.md、GIT_WORKFLOW.md、DIFF_REVIEW.md、STATUS_MACHINE.md、SAFETY_RULES.md、VALIDATION_GUIDE.md 放到 docs/workflow/。
5. 建议将 references/AGENTS_COMPAT.md 中适合本项目的关键规则合并到项目 AGENTS.md；只能追加或合并，不要覆盖已有项目规则。
6. 不要直接实现业务需求。
```

## 22. 拆任务

```text
请使用 create_task 模式拆解下面需求：
<粘贴需求>

要求：
1. 每个任务写清模式、类型、状态、优先级、风险等级、完成标准和验证方式。
2. 任务优先级使用高 / 中 / 低 / 待确认；P0/P1/P2/P3 只用于审查严重等级。
3. 大任务先转为 plan_task。
4. 不要一边拆任务一边执行代码。
```

## 23. 大任务写 plan / RFC

```text
请使用 plan_task 模式，为下面需求写 plan / RFC：
<粘贴需求>

要求：
1. 写清背景、目标、非目标、方案、风险、验证方式和任务拆分。
2. 标出需要用户确认的问题。
3. 不要直接实现。
```

## 24. 执行单个任务

```text
请使用 execute_task 模式执行 docs/tasks/<TASK-ID>.md。

要求：
1. 先确认任务状态为 Ready。
2. 先判断 A/B/C/D 等级：A/B 小任务不强制分支，C 级建议分支，D 级必须使用分支或 Worktree。
3. 只做当前任务允许修改范围内的内容。
4. 发现任务膨胀、冲突或风险无法判断时立即停止。
5. 完成后写验证结果、用户动作等级、验收建议和交接摘要。
```

## 25. 任务膨胀时停止并拆分

```text
当前任务出现膨胀迹象，请使用 AI开发流程停止并拆分。

要求：
1. 停止继续修改。
2. 说明膨胀原因：文件数增加 / 多模块影响 / 新依赖 / 架构变化 / 新需求 / 完成标准不足。
3. 更新任务状态为 Blocked 或待确认。
4. 建议拆出的新任务。
5. 等待用户确认。
```

## 26. 独立审查

```text
请使用 review_task 模式审查 docs/tasks/<TASK-ID>.md。

要求：
1. 只审查，不修复。
2. 读取 DIFF_REVIEW.md、CODE_REVIEW_CHECKLIST.md、任务文件、验证记录和 base commit 到 HEAD 或当前工作区 diff。
3. 只审查当前任务范围。
4. 不把历史问题全部压到当前任务。
5. 输出是否允许进入验收建议和建议用户动作等级。
6. 将结论写入任务文件的“代码审查”和“Diff 审查”段落，或项目约定的审查记录。
7. 必要时更新 docs/TASK_BOARD.md 的 Review 状态。
8. 只在聊天中输出审查意见不算完成审查。
```

## 27. 按 P0/P1/P2/P3 输出审查意见

```text
请按 P0/P1/P2/P3 审查严重等级输出审查意见。注意：这不是任务优先级。

要求：
1. P0：阻止合并或验收，必须立即修复。
2. P1：高风险，验收前必须修复。
3. P2：建议修复，可单独开后续任务。
4. P3：风格或可选建议，不阻止验收。
5. 明确是否允许进入验收建议和建议用户动作等级。
```

## 28. 根据审查意见修复

```text
请使用 repair_task 模式，根据以下审查意见修复 docs/tasks/<TASK-ID>.md：
<粘贴审查意见>

要求：
1. 只处理审查指出的问题。
2. 不做无关优化。
3. 修复后更新验证结果、审查状态和交接摘要。
4. 如果意见超出当前任务范围，记录为后续任务。
```

## 29. 验收建议前总结

```text
请使用 close_task 模式前的验收总结，汇总 docs/tasks/<TASK-ID>.md。

要求：
1. 说明完成标准是否满足。
2. 汇总修改文件、验证结果、审查结论、遗留风险。
3. 给出用户动作等级和用户具体需要做什么。
4. 未验收前不要标记 Closed。
```

## 30. 汇总项目状态

```text
请使用 status_report 模式汇总当前项目状态。

要求：
1. 读取 TASK_BOARD 和相关任务文件。
2. 按 Draft、Ready、In Progress、Blocked、Review、Needs Fix、Accepted、Closed、Deferred、Cancelled 分类。
3. 区分已完成、进行中、阻塞和待确认。
4. 不改变任务状态，除非用户明确要求。
```

## 31. 多 agent 并发冲突检查

```text
请检查当前任务是否与其他 agent 或任务冲突。

要求：
1. 读取 TASK_BOARD 和相关任务文件。
2. 判断是否涉及相同模块、相同核心文件或相同交付物。
3. 如果冲突，标记 Blocked 并说明需要串行或用户确认。
4. 冲突未解决前不要继续执行。
```

## 32. 判断用户动作等级

```text
请使用 ai-dev-flow 判断 docs/tasks/<TASK-ID>.md 的用户动作等级。

要求：
1. 读取 ACCEPTANCE_GUIDE.md、任务文件、验证记录和审查结论。
2. 在 UA0 / UA1 / UA2 / UA3 / UA4 / UA5 / UA6 / UA7 / 待确认 中选择一项。
3. 说明判断依据。
4. 不要默认要求用户实机测试。
5. 不要默认跳过用户验收。
6. 不得让用户逐行审代码作为验收方式。
```

## 33. 生成验收建议

```text
请为 docs/tasks/<TASK-ID>.md 生成验收建议，并写回任务文件。

要求：
1. 使用 ACCEPTANCE_GUIDE.md 的输出格式。
2. 明确用户动作等级。
3. 明确是否需要用户实机测试。
4. 写清用户到底要做什么。
5. 汇总 agent 已提供的修改文件、diff 摘要、构建 / 测试、截图 / 日志和审查结论。
6. 如果可跳过实机测试，说明原因。
7. 写清不验收的风险和是否允许关闭任务。
8. 如果判断为 UA0，默认写“建议关闭”，不要自动标记 Closed，除非任务文件、项目规则或用户明确授权。
```

## 34. 轻量风险审查

```text
请对 docs/tasks/<TASK-ID>.md 做轻量风险审查。

要求：
1. 只关注 P0/P1、范围越界、缺少验证和是否允许进入对应用户动作等级。
2. 不做全面代码重审，除非发现 P0/P1 风险。
3. 判断当前用户动作等级是否过低或过高。
4. 如果 UA 等级无法判断，写“待确认”。
5. 输出是否允许进入下一步。
```

## 35. 批量生成验收建议

```text
请对以下多个任务批量生成验收建议：
<粘贴任务列表或任务文件路径>

要求：
1. 逐个读取任务文件、验证记录和审查结论。
2. 按任务分别输出 UA0 / UA1 / UA2 / UA3 / UA4 / UA5 / UA6 / UA7 / 待确认。
3. A/B 小任务不要机械要求用户实机测试。
4. 涉及真实环境、核心流程或回归风险的任务必须提高到 UA5 / UA6 / UA7。
5. 每个任务都写清用户需要做什么和 agent 已提供的证据。
```

## 36. 选择可批量小任务

```text
请使用 ai-dev-flow 从 docs/TASK_BOARD.md 中选择可批量执行的 A/B 小任务。

要求：
1. 读取 BATCH_TASK_GUIDE.md、TASK_BOARD 和候选任务文件。
2. 只选择 A/B 小任务，不把 C/D 任务放入批次。
3. 输出推荐批次、每个任务等级、是否可批量。
4. 列出不可批量的任务及原因。
5. 检查是否存在冲突文件或冲突模块。
6. 建议一次执行的任务数量。
7. 不要直接执行任务。
```

## 37. 创建批次

```text
请使用 ai-dev-flow 创建 docs/batches/BATCH-xxx.md。

要求：
1. 读取 BATCH_TASK_GUIDE.md、TASK_BOARD 和包含的 TASK 文件。
2. 列出包含任务、任务等级、任务文件路径和是否可批量。
3. 记录 base commit、允许修改范围和禁止修改范围。
4. 说明执行位置、批次类型和风险。
5. 不要把 C/D 任务放入批次。
6. 创建或更新批次文件后，同步更新相关 TASK 文件的所属批次字段。
```

## 38. 批量执行 A/B 小任务

```text
请使用 ai-dev-flow 批量执行 docs/batches/BATCH-xxx.md 中的 A/B 小任务。

要求：
1. 读取 BATCH_TASK_GUIDE.md、批次文件和每个 TASK 文件。
2. 只执行列入批次的任务，不加入新任务。
3. 不处理 C/D 任务；发现风险升高时停止并拆分。
4. 同一个执行会话中按顺序完成任务，不并行写代码。
5. 如果包含 B 级小代码任务，推荐每个 TASK 单独 commit；如果不单独 commit，必须记录每个 TASK 的修改文件、per-task diff 归属和验证结果。
6. 多个 B 级任务修改同一文件时，默认停止并建议拆分，除非用户明确确认风险。
7. 每个任务单独更新任务文件、修改文件、验证结果、diff 范围和 UA 等级。
8. 生成批量审查交接包。
9. 不自动合并、push、release、删除分支或删除 Worktree。
```

## 39. 批量审查 A/B 小任务

```text
请使用 Review Hub 审查 docs/batches/BATCH-xxx.md。

要求：
1. 读取 BATCH_TASK_GUIDE.md、DIFF_REVIEW.md、CODE_REVIEW_CHECKLIST.md、批次文件和每个 TASK 文件。
2. 只审查，不修改业务代码。
3. 按任务逐项审查，不得只输出 Batch 总结论。
4. 每个任务输出 P0/P1/P2/P3、审查结论、UA 等级和是否允许进入验收建议。
5. 发现任一任务风险升高、P0/P1、范围越界或 diff 无法按任务拆分时，停止相关批量审查，标记“diff 归属不清”，并建议拆分任务或拆分 commit。
6. 将结论写回每个 TASK 文件和可选 BATCH 文件。
```

## 40. 批量任务拆分

```text
当前 Batch 出现过大、风险升高或 diff 无法拆分，请使用 ai-dev-flow 拆分批次。

要求：
1. 停止继续执行或审查该批次。
2. 列出需要拆出的任务和原因。
3. 说明哪些任务仍可保留在 Batch，哪些必须单独执行或审查。
4. 更新 BATCH 文件、相关 TASK 文件和 TASK_BOARD。
5. 等待用户确认后再继续。
```

## 41. 推荐并行波次

```text
请使用 ai-dev-flow 根据 docs/TASK_BOARD.md 推荐一组可并行任务。

要求：
1. 读取 PARALLEL_WAVE_GUIDE.md、TASK_BOARD 和候选 TASK 文件。
2. 输出推荐 Wave 编号、候选任务、每个任务等级。
3. 列出每个任务预计修改文件和预计影响模块。
4. 检查是否存在文件冲突、模块冲突和依赖关系。
5. 检查代码任务是否能使用独立分支或 Worktree。
6. 检查是否涉及 D 级或 UA5 / UA6 / UA7。
7. 输出是否需要用户确认和推荐执行会话数量。
8. 不要默认启动多个执行会话。
```

## 42. 创建 Parallel Wave

```text
请使用 ai-dev-flow 创建 docs/waves/WAVE-xxx.md。

要求：
1. 读取 PARALLEL_WAVE_GUIDE.md、TASK_BOARD 和候选 TASK 文件。
2. 记录包含任务、文件锁、模块锁、base commit 和执行会话。
3. 检查每个代码任务是否有独立分支或 Worktree，并记录各自执行位置。
4. 标记可并行任务和必须串行任务。
5. 如果多个代码任务共享同一工作区，标记高风险并要求用户确认。
6. 明确是否需要用户确认。
7. 未经用户确认，不要启动多个写代码执行会话或多个写代码 subagents 并行。
8. 如果 harness 自动使用 subagents，必须记录 subagent 使用情况，并确保 TASK 边界、diff、验证和审查可追踪。
```

## 43. 并行任务冲突检查

```text
请检查以下任务是否可以同时进入 Parallel Wave：
<粘贴任务列表>

要求：
1. 读取 PARALLEL_WAVE_GUIDE.md 和每个任务文件。
2. 输出可并行任务、必须串行任务。
3. 列出冲突文件、冲突模块和依赖关系。
4. 说明不建议并行的原因。
5. 文件或模块冲突时不得并行。
6. 代码任务无法确认独立分支或 Worktree 时不得并行。
7. D 级和 UA5 / UA6 / UA7 任务默认不得进入代码并行。
```

## 44. 执行 Wave 中的单个任务

```text
请使用 ai-dev-flow 执行 WAVE-xxx 中分配给本会话的单个任务：docs/tasks/<TASK-ID>.md。

要求：
1. 读取 PARALLEL_WAVE_GUIDE.md、WAVE 文件和当前 TASK 文件。
2. 只执行自己负责的任务，不修改其他 Wave 任务文件的业务内容。
3. 确认当前执行会话只处理分配给自己的任务，不处理其他 Wave 任务。
4. 如果是代码任务，确认本会话使用自己的独立分支或 Worktree；无法确认时停止。
5. 遵守预计修改文件、影响模块、文件锁和模块锁。
6. 记录 base commit、HEAD、diff 范围、验证结果和交接包。
7. 发现冲突、范围越界或风险升高时立即停止并标记 Blocked。
```

## 45. Review Hub 审查 Wave

```text
请使用 Review Hub 审查 docs/waves/WAVE-xxx.md。

要求：
1. 读取 PARALLEL_WAVE_GUIDE.md、DIFF_REVIEW.md、CODE_REVIEW_CHECKLIST.md、Wave 文件和每个 TASK 文件。
2. 只审查，不修改业务代码。
3. 逐任务审查，不得只输出 Wave 总结论。
4. 每个任务输出 P0/P1/P2/P3、UA 等级、是否允许进入验收建议。
5. 检查每个任务的 base commit、HEAD、diff 范围和验证结果。
6. 发现冲突、P0/P1 或 C/D 风险时，将该任务移出 Wave 单独处理。
7. 将结论写回每个 TASK 文件和可选 WAVE 文件。
```

## 46. Wave 异常拆分

```text
当前 Wave 中有任务出现冲突、P0/P1 或风险升高，请使用 ai-dev-flow 拆分处理。

要求：
1. 停止受影响任务的并行执行或审查。
2. 说明异常任务、冲突文件、冲突模块、P0/P1 或风险原因。
3. 将异常任务移出 Wave，建议单独执行、单独审查或转为 Blocked。
4. 不影响其他已通过且无冲突的任务。
5. 更新 WAVE 文件、相关 TASK 文件和 TASK_BOARD。
6. 等待用户确认后再继续。
```

## 47. Intake 需求收集（ADF-0610-01）

```text
请使用 ai-dev-flow 的 Intake 流程整理以下需求。

当前模式：创建任务（create_task）
当前 Loop：不适用
当前子模式：不适用
当前阶段：Intake，不直接创建 TASK
输入文件：用户需求文本、README、AGENTS.md、必要的项目索引
输出文件：docs/intake/INTAKE-xxx.md 草案或聊天中的同结构内容
是否允许修改业务代码：否
是否需要用户确认：如果存在阻塞模糊点，需要

要求：
1. 读取 INTAKE_GUIDE.md。
2. 记录原始需求、目标、非目标、成功标准、约束、模糊点和可逆性判断。
3. 合理假设必须显式标记。
4. 不创建 TASK，不拆任务，不执行代码。
5. 输出建议下一步：plan_task / create_task / status_report / Blocked。
```

## 48. Triage Loop（ADF-0610-02）

```text
请使用 ai-dev-flow 运行只读 triage_loop。

当前模式：状态汇总（status_report）
当前 Loop：分拣循环（triage_loop）
当前子模式：状态汇总（status_report）
输入文件：TASK_BOARD、相关 TASK 文件、BATCH_TASK_GUIDE.md、PARALLEL_WAVE_GUIDE.md
输出文件：docs/loops/LOOP_STATE.md 或同结构总结
是否允许修改业务代码：否
是否需要用户确认：启动执行、Batch 或 Wave 前需要

要求：
1. 读取 LOOP_ENGINEERING_GUIDE.md 和 LOOP_STATE_TEMPLATE.md。
2. 找出 Ready、Review、Needs Fix、Blocked。
3. 推荐可 Batch 的 A/B 小任务。
4. 推荐可 Wave 的互不冲突任务，但不要启动执行会话。
5. 输出 next / blocked / review / repair 候选。
```

## 49. Goal Loop（ADF-0610-03）

```text
请使用 ai-dev-flow 对单个任务运行 goal_loop。

当前模式：执行任务（execute_task）
当前 Loop：目标循环（goal_loop）
当前子模式：执行任务（execute_task）/ 审查任务（review_task）/ 修复任务（repair_task）/ 关闭任务（close_task）（每一步按实际声明一个合法模式）
输入文件：当前 TASK 文件、AGENTS.md、Git precheck、验证记录、审查清单
输出文件：更新后的 TASK 文件和 TASK_BOARD
是否允许修改业务代码：仅在 execute_task / repair_task 子模式中允许
是否需要用户确认：危险操作、范围扩大、超过循环次数或合并前需要

要求：
1. 每一步声明当前子模式，且只能使用合法模式：execute_task、review_task、repair_task、close_task。
2. 不跳过验证和审查。
3. Review 不修复，Repair 只处理审查指出的问题。
4. 达到停止条件后输出用户动作等级和验收建议。
5. 不自动 merge、push、release 或删除文件。
```

## 50. Review Repair Loop（ADF-0610-04）

```text
请使用 ai-dev-flow 对 docs/tasks/<TASK-ID>.md 运行 review_repair_loop。

当前模式：修复任务（repair_task）
当前 Loop：审查-修复循环（review_repair_loop）
当前子模式：审查任务（review_task）/ 修复任务（repair_task）（每轮按实际声明一个合法模式）
输入文件：任务文件、明确 diff、审查结论、REVIEW_REPAIR_LOOP_GUIDE.md
输出文件：任务文件中的每轮 repair / review 记录
是否允许修改业务代码：仅 repair_task 子模式中允许
是否需要用户确认：超过 2 轮、范围扩大、P0/P1 无法修复时需要

要求：
1. 默认最多 2 轮 repair。
2. P0/P1 必须修复。
3. P2 可转后续任务，P3 不阻塞。
4. 每轮结束必须重新进入 review_task。
5. 每轮必须声明当前子模式，且只能使用合法模式：review_task 或 repair_task。
6. repair_task 不得直接标记 Accepted。
```

## 51. Status / Standup（ADF-0610-05）

```text
请使用 ai-dev-flow 生成项目状态 standup。

当前模式：状态汇总（status_report）
当前 Loop：状态循环（status_loop）
当前子模式：状态汇总（status_report）
输入文件：TASK_BOARD、相关 TASK 文件、LOOP_STATE.md
输出文件：状态汇总；如用户确认，可更新 LOOP_STATE.md
是否允许修改业务代码：否
是否需要用户确认：改变任务状态前需要

要求：
1. 按 Ready、In Progress、Blocked、Review、Needs Fix、Accepted 分类。
2. 输出昨天/最近完成、当前阻塞、下一步候选。
3. 不改变任务状态，除非用户明确要求。
```

## 52. What's Next（ADF-0610-06）

```text
请使用 ai-dev-flow 输出下一步候选。

当前模式：状态汇总（status_report）
当前 Loop：分拣循环（triage_loop）
当前子模式：状态汇总（status_report）
输入文件：TASK_BOARD、相关 TASK 文件、LOOP_STATE.md
输出文件：下一步候选列表
是否允许修改业务代码：否
是否需要用户确认：执行任何候选任务前需要

要求：
1. 按优先级和阻塞情况排序。
2. 标出建议动作：execute_task / review_task / repair_task / create_task / plan_task。
3. 标出是否可 Batch 或可 Wave。
4. 不直接执行。
```

## 53. What's Blocked（ADF-0610-07）

```text
请使用 ai-dev-flow 汇总阻塞项。

当前模式：状态汇总（status_report）
当前 Loop：状态循环（status_loop）
当前子模式：状态汇总（status_report）
输入文件：TASK_BOARD、Blocked 任务文件、LOOP_STATE.md
输出文件：阻塞清单
是否允许修改业务代码：否
是否需要用户确认：解除阻塞或改变状态前需要

要求：
1. 列出每个阻塞任务、阻塞原因、需要用户动作。
2. 区分需求不清、权限缺失、验证失败、冲突、风险无法判断。
3. 不猜测状态。
```

## 54. Project Constitution 初始化（ADF-0610-08）

```text
请使用 ai-dev-flow 初始化 PROJECT_CONSTITUTION。

当前模式：初始化项目（init_project）
当前 Loop：不适用
当前子模式：不适用
输入文件：PROJECT_CONSTITUTION_TEMPLATE.md、AGENTS.md、README、项目已有规则
输出文件：docs/PROJECT_CONSTITUTION.md 草案
是否允许修改业务代码：否
是否需要用户确认：写入或修改 MUST / MUST NOT 前需要

要求：
1. 区分 MUST、SHOULD、MUST NOT。
2. 不覆盖已有项目规则。
3. 说明与 CODE_REVIEW_CHECKLIST、DECISIONS、PROJECT_INDEX、docs/memory 的区别。
4. 不把临时偏好写成硬规则。
```

## 55. Memory Hydrate（ADF-0610-09）

```text
请使用 ai-dev-flow 从完成任务中提炼 Memory 更新建议。

当前模式：关闭任务（close_task）
当前 Loop：不适用
当前子模式：不适用
输入文件：已 Accepted 或 Closed 的 TASK、审查记录、验证记录、MEMORY_GUIDE.md
输出文件：docs/memory/ 更新建议；用户确认后才写入
是否允许修改业务代码：否
是否需要用户确认：写入 Memory 前需要

要求：
1. 只提炼稳定、可复用知识。
2. 不写聊天全文、密钥、Token、本机路径、个人隐私或未确认猜测。
3. 如果 Memory 与代码冲突，标记冲突，不编造现状。
```

## 56. Harness Compatibility 检查（ADF-0610-10）

```text
请使用 ai-dev-flow 检查当前 agent / harness 兼容性。

当前模式：状态汇总（status_report）
当前 Loop：不适用
当前子模式：不适用
输入文件：HARNESS_COMPAT.md、SKILL.md、项目 AGENTS.md
输出文件：兼容性检查结果
是否允许修改业务代码：否
是否需要用户确认：降级执行或启动并行前需要

要求：
1. 判断是否支持 Skill、Markdown 读取、Git、Worktree、独立 Reviewer。
2. 如果不支持 Worktree，不得启动 Parallel Wave 代码任务。
3. 判断是否支持 subagents / ultra mode-like capability，并区分只读、写代码、混合或内部不可见。
4. 如果不支持 subagents，降级为普通总览 / 执行 / 审核会话流程。
5. 如果支持自动 subagents，说明是否可用于 Reviewer / Verifier / Orchestrator 辅助工作。
6. 写代码 subagents 必须声明任务编号、角色、模式、允许修改范围、禁止修改范围和验证方式。
7. 多个写代码 subagents 并行默认需要用户确认、独立分支或 Worktree、文件锁 / 模块锁检查和 diff 归属检查。
8. 输出“Subagent 使用情况”汇总；如果内部 subagents 不可见，标记“不可见”并保证最终 diff、验证证据、未验证项和风险清楚。
9. 不假设不同 CLI 参数通用。
```

## 57. GitHub Issues Backend 规划（ADF-0610-11）

```text
请使用 ai-dev-flow 生成 GitHub Issues backend mapping preview。

当前模式：规划任务（plan_task）
当前 Loop：不适用
当前子模式：不适用
输入文件：GITHUB_ISSUES_BACKEND.md、TASK_BOARD、相关 TASK 文件
输出文件：TASK 到 Issue 的字段映射预览
是否允许修改业务代码：否
是否需要用户确认：创建、编辑、关闭 issue 前必须确认

要求：
1. 只生成 mapping preview。
2. 不自动创建 issue。
3. 不自动关闭 issue。
4. 不自动同步 labels。
5. 不把敏感信息、本机路径、私有账号或日志写入公开 issue。
```

## 58. 验收失败反馈闸门 / Acceptance Feedback Gate

```text
请使用 ai-dev-flow 处理下面的用户验收失败反馈。

当前模式：审查任务（review_task）
当前子模式：验收失败反馈分拣（acceptance_feedback_triage）
输入文件：当前 TASK 文件、验收建议、用户实机测试反馈、验证记录、base commit 到 HEAD 或当前工作区 diff
输出文件：更新后的 TASK 文件、必要时更新 TASK_BOARD
是否允许修改业务代码：否
是否需要用户确认：实际进入 repair_task、扩大范围、创建新 TASK、关闭任务或改变已确认状态前需要；记录“证据不足 / 待确认 / Blocked 建议”不需要先确认，但必须列出最小补充信息

用户反馈：
<粘贴实机测试报告、日志、截图描述、复现步骤、期望结果、实际结果>

要求：
1. 先只读诊断，不修改业务代码、测试代码、配置文件、构建脚本或依赖声明；仅允许更新 TASK、TASK_BOARD、审查记录等工作流文档。
2. 读取任务文件、完成标准、验收建议、验证记录、审查结论和当前 diff。
3. 判断反馈属于哪一类：
   - 原任务完成标准未满足；
   - 本轮修改引入的回归；
   - 新需求或范围扩大；
   - 用户环境 / 配置 / 权限 / 数据 / 外部设备问题；
   - 证据不足，无法判断。
4. 输出最可能的 3 个根因；每个根因都必须说明：
   - 证据；
   - 涉及文件 / 模块 / 代码路径；
   - 如何验证；
   - 是否属于当前 TASK 范围。
5. 如果属于“原任务完成标准未满足”或“本轮修改引入回归”，将任务建议转为需修复（Needs Fix），并建议进入审查-修复循环（review_repair_loop）。
6. 如果属于“新需求或范围扩大”，不得在当前任务里顺手修，建议创建新 TASK。
7. 如果属于“用户环境 / 配置 / 权限 / 数据 / 外部设备问题”，将任务建议标记为阻塞（Blocked），并列出用户需要补充的最小信息。
8. 如果证据不足，只输出诊断问题清单和最小补充信息，不进入修复任务（repair_task）。
9. 如果进入审查-修复循环（review_repair_loop），必须遵守默认最多 2 轮 repair；每轮 repair 前说明本轮假设、证据、拟修改文件和验证方式。
10. 不得在没有明确证据时扩大修改范围。

输出格式：

## 验收失败反馈闸门结论

反馈分类：原任务未完成 / 本轮回归 / 新需求或范围扩大 / 环境或配置问题 / 证据不足

是否属于当前 TASK 范围：是 / 否 / 待确认

是否允许进入修复任务（repair_task）：是 / 否 / 待用户确认

建议任务状态：需修复（Needs Fix）/ 阻塞（Blocked）/ 待审查（Review）/ 待确认

根因候选：
1. 根因：
   - 证据：
   - 涉及文件 / 模块 / 代码路径：
   - 验证方式：
   - 是否当前范围：
2. 根因：
   - 证据：
   - 涉及文件 / 模块 / 代码路径：
   - 验证方式：
   - 是否当前范围：
3. 根因：
   - 证据：
   - 涉及文件 / 模块 / 代码路径：
   - 验证方式：
   - 是否当前范围：

Repair 输入清单（仅当建议进入审查-修复循环（review_repair_loop）时输出）：
1. 修复项：
   - 严重等级：P0 / P1 / P2 / P3
   - 证据：
   - 允许修改范围：
   - 禁止修改范围：
   - 验证方式：
2. 修复项：
   - 严重等级：P0 / P1 / P2 / P3
   - 证据：
   - 允许修改范围：
   - 禁止修改范围：
   - 验证方式：

Repairer 只能处理上述 Repair 输入清单，不得扩大范围或自我批准。

下一步：
- 进入审查-修复循环（review_repair_loop）/ 创建新 TASK / 阻塞（Blocked）等待用户补充信息 / 保持待审查（Review）/ 建议关闭

需要用户补充的信息：
- 无 / 待填写
```

## 59. Bug 诊断（bug_diagnosis）

```text
请使用 ai-dev-flow 做一次 Bug 诊断。

当前模式：审查任务（review_task）/ 执行任务（execute_task）
当前子模式：Bug 诊断（bug_diagnosis）
输入文件：当前 TASK、验证记录、用户反馈、相关日志、base commit 到 HEAD 或当前工作区 diff
输出文件：更新后的 TASK 文件；必要时更新审查记录或 TASK_BOARD
是否允许修改业务代码：否，除非用户确认进入 repair_task
是否需要用户确认：进入 repair_task、扩大范围、创建新 TASK、关闭任务或改变已确认状态前需要确认

要求：
1. 先定义 RED 失败信号、GREEN 通过信号和 SIGNAL 证据来源。
2. 判断 agent 是否能自动复现、样例文件 replay、需要用户实机 HITL，还是暂无法复现。
3. 列出 3 到 5 个可证伪根因假设，每个假设都写证据、验证方式和是否属于当前 TASK 范围。
4. 如果证据不足，只列最小补充信息，不修改代码。
5. 如果需要临时诊断日志，必须给唯一前缀，并说明修复后清理方式。
6. 输出下一步：进入 real_env_signal / repair_task / review_repair_loop / 创建新 TASK / Blocked / 待确认。
```

## 60. TDD 执行任务（tdd_task）

```text
请使用 ai-dev-flow 按测试先行方式执行当前任务。

当前模式：执行任务（execute_task）
当前子模式：测试先行（tdd_task）
输入文件：当前 TASK、验证指南、相关测试文件、相关业务入口
输出文件：更新后的 TASK 文件、必要的测试和最小实现
是否允许修改业务代码：按 TASK 允许范围
是否需要用户确认：扩大范围、新增大型依赖或改变已确认状态前需要确认

要求：
1. 先选择一个可观察行为，不测试私有实现细节。
2. 写失败测试或最小复现命令，确认 RED。
3. 做最小实现或修复，确认 GREEN。
4. 运行相关回归测试或替代验证。
5. 记录 RED、GREEN、SIGNAL、测试命令、证据位置和未覆盖风险。
6. 如果项目没有测试缝隙，不要硬凑测试；记录不适用原因并建议后续测试缝隙任务或架构巡检。
```

## 61. 需求拷问（requirement_grilling）

```text
请使用 ai-dev-flow 对下面需求做需求拷问。

当前模式：创建任务（create_task）/ 规划任务（plan_task）
当前子模式：需求拷问（requirement_grilling）
输入文件：README、AGENTS.md、PROJECT_INDEX、TASK_BOARD、相关代码或文档
输出文件：Intake 草案、阻塞问题清单或 TASK 假设
是否允许修改业务代码：否
是否需要用户确认：阻塞问题、默认假设、范围扩大或高风险决策需要确认

要求：
1. 先读取能查清事实的项目文档和相关代码，不要把可查问题直接丢给用户。
2. 只问会阻塞任务边界、验收标准、风险决策或不可逆动作的问题。
3. 交互式场景一次只问一个最关键问题。
4. Codex 场景输出阻塞问题清单，并给推荐默认假设。
5. 非阻塞模糊点写入 Intake、风险或任务假设，不要卡住。
```

## 62. 项目语境更新（project_context）

```text
请使用 ai-dev-flow 更新项目语境。

当前模式：状态汇总（status_report）/ 规划任务（plan_task）
当前子模式：项目语境（project_context）
输入文件：docs/memory/PROJECT_CONTEXT.md、PROJECT_INDEX、DECISIONS、当前 TASK、验证记录
输出文件：docs/memory/PROJECT_CONTEXT.md 或同结构草案
是否允许修改业务代码：否
是否需要用户确认：写入未确认业务规则、敏感信息或长期决策前需要确认

要求：
1. 只沉淀稳定、可复用的项目术语、验证经验、常见误解和已确认约束。
2. 不写聊天全文、密钥、本机路径、私有账号、真实隐私数据或未确认猜测。
3. 区分 PROJECT_INDEX、PROJECT_CONTEXT、DECISIONS / ADR 和 TASK 的职责。
4. 每条语境尽量写来源文件或证据。
```

## 63. 会话交接（session_handoff）

```text
请使用 ai-dev-flow 生成会话交接摘要。

当前模式：状态汇总（status_report）/ 执行任务（execute_task）/ 审查任务（review_task）
当前子模式：会话交接（session_handoff）
输入文件：当前 TASK、TASK_BOARD、验证记录、审查记录、git 状态
输出文件：当前 TASK 的交接摘要或单独 handoff 文档
是否允许修改业务代码：否
是否需要用户确认：改变任务状态、关闭任务或创建新 TASK 前需要确认

要求：
1. 引用路径，不复制完整文档。
2. 写清已完成、未完成、验证证据、未验证项、风险和下一步。
3. 写清下一会话建议读取的文件和建议使用的指南。
4. 写清不要重复尝试的路线。
5. 不把聊天记录作为唯一状态来源。
```

## 64. 架构巡检（architecture_review）

```text
请使用 ai-dev-flow 做一次只读架构巡检。

当前模式：审查任务（review_task）/ 规划任务（plan_task）
当前子模式：架构巡检（architecture_review）
输入文件：PROJECT_INDEX、TASK_BOARD、相关 TASK、相关模块、验证记录、失败反馈
输出文件：架构巡检报告或建议后续 TASK 清单
是否允许修改业务代码：否
是否需要用户确认：创建任务、改架构、改依赖、改协议、改数据或改发布流程前需要确认

要求：
1. 只读分析，不直接重构。
2. 找反复返工、无测试缝隙、边界混乱、AI 容易误改或高风险依赖点。
3. 每个发现都写证据、风险、建议任务和用户动作等级。
4. 涉及架构、依赖、协议、数据或发布流程时标记 UA7。
```

## 65. 把实机反馈转成测试信号（real_env_signal）

```text
请使用 ai-dev-flow 把下面实机反馈转成测试信号。

当前模式：审查任务（review_task）
当前子模式：实机测试信号复现（real_env_signal）
输入文件：当前 TASK、验收建议、用户实机反馈、日志 / 截图 / 录屏 / 输出文件描述
输出文件：更新后的 TASK 文件
是否允许修改业务代码：否
是否需要用户确认：进入 repair_task、扩大范围、创建新 TASK 或改变状态前需要确认

用户反馈：
<粘贴用户反馈>

要求：
1. 判断复现能力分类：agent 可自动复现 / 样例文件 replay / 用户实机 HITL / 暂无法复现 / 不适用。
2. 定义 RED 失败信号、GREEN 通过信号和 SIGNAL 证据来源。
3. 如果需要用户实机 HITL，输出最短复测步骤和回传证据模板。
4. 如果没有 RED，不得建议直接修复。
5. 下一步只能建议：进入 bug_diagnosis / repair_task / review_repair_loop / 创建新 TASK / Blocked / 待确认。
```

## 66. 用户实机回传证据后继续诊断

```text
请使用 ai-dev-flow 根据用户回传证据继续诊断。

当前模式：审查任务（review_task）/ 修复任务（repair_task）
当前子模式：用户实机 HITL 证据复核
输入文件：当前 TASK、real_env_signal 记录、用户回传日志 / 截图 / 录屏 / 输出文件、验证记录
输出文件：更新后的 TASK 文件、必要时输出 Repair 输入清单
是否允许修改业务代码：仅当用户确认进入 repair_task 后允许
是否需要用户确认：进入 repair_task、扩大范围、创建新 TASK 或改变已确认状态前需要确认

要求：
1. 对照 RED / GREEN / SIGNAL 判断失败是否复现、是否已消失或证据仍不足。
2. 如果根因不清，进入 bug_diagnosis。
3. 如果已有明确修复项，输出 Repair 输入清单，包括修复项、严重等级、证据、允许修改范围、禁止修改范围和验证方式。
4. Repairer 只能处理该清单，不得扩大范围或自我批准。
5. 如果两轮修复后仍未 GREEN，停止并建议人工接管或重新拆任务。
```

## 67. 增加最小诊断日志

```text
请使用 ai-dev-flow 为当前问题设计最小诊断日志。

当前模式：执行任务（execute_task）/ 修复任务（repair_task）
当前子模式：最小诊断日志
输入文件：当前 TASK、bug_diagnosis 记录、相关代码路径、验证记录
输出文件：诊断日志方案；只有确认在允许范围内时才修改代码
是否允许修改业务代码：按 TASK 允许范围；无确认时只输出方案
是否需要用户确认：新增持久日志、记录敏感字段、扩大范围或改变状态前需要确认

要求：
1. 说明唯一日志前缀。
2. 说明记录字段、触发位置、如何判断 RED / GREEN。
3. 不记录密钥、Token、账号、隐私数据或完整用户文件内容。
4. 写明修复后清理方式；如果要保留，说明为什么应转为正式日志。
5. 输出验证方式和证据位置。
```
