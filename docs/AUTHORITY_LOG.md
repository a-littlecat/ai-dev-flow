# 授权流水归档

> 本文件由 `skills/ai-dev-flow/scripts/board_generator.py --migrate-authority-log` 生成并维护；条目为 `docs/TASK_BOARD.md` `## 当前授权边界` 节的历史原文，逐字未改写；对账键 = 条目 ID + 原段落 UTF-8 内容 SHA256。

## AUTH-20260810-001

- sha256: 45e22acc71a1a331bd16053bdc8b2ac0dff7b6ca6a4f12cca5f9a89876837407

用户于 2026-07-31 在比较受控 Goal、交付 Goal、Goal 适配器和零状态组合后，明确确认采用更自动的 `Auto-Land Goal`，允许自动 commit、merge、push、PR/CI，并要求“触发词增加中文”。`GOAL-USAGE-001` 已通过 PR #2 合并到 `main`；未执行 tag、release 或 deploy。

## AUTH-20260810-002

- sha256: c14174b4929bfe6f61585588a4fb3a611ce00214fc33fce8c446bb1119128320

旧 `UNATTENDED-RUN-001` 是未提交、未合并的独立 Worktree 候选；本任务以原生 Goal 零状态组合替代其自定义状态机方向，但保留旧 Worktree，不吸收、不删除其 diff。

## AUTH-20260810-003

- sha256: 0758c6652d8773e8fbb4584b8279f6d6028fdd4fde29d178b6dea0f1bc2a54c1

用户进一步明确回复“性能验收通过，并启动自动落地目标：提交、合并页面修复和性能优化，重建运行时后同步本机 Skill。并关闭任务，删除分支。”该授权覆盖 `DASHBOARD-EDGE-LABEL-001` 与 `DASHBOARD-IDLE-PERF-001` 的验收写回、精确提交、推送、集成、runtime 重建、本机 Skill 同步、Closed 写回和完全合并后任务分支删除；不包含 tag、release、deploy、强制推送、历史改写或覆盖主工作区用户改动。

## AUTH-20260810-004

- sha256: aed685f533b52c623bed323fbdfd398a6cf9656189fa6c0bbb97ee901f680903

用户明确指出原 PLAN-001 只扩展 Review-Repair Loop，并未完成项目瘦身；随后授权修改或推翻 PLAN-001，只要最终满足“前沿模型使用 Skill 有净正收益、避免无效额度与负优化”的需求。

## AUTH-20260810-005

- sha256: 80aee98be11594027930e89e96b5c56b4263771f9050795adefc61de862b4d23

用户随后要求补齐两项缺口：首版应有轻量自动审核流程；两轮修复后如果仍在持续收敛，不应仅因次数耗尽就要求用户接管。

## AUTH-20260810-006

- sha256: 778543802212455834e20c0d3df1cddecef1b952b948e25464f78a57125cdd74

独立 Review 随后记录 4 项 P1；用户明确要求“修改”，因此授权第 1 轮有限 `repair_task` 只处理 Lite 验证边界、Tracked Reviewer 降级路径、收益验证/实施顺序和可复现净收益协议。该授权不包含实施、创建 `LEAN-*`、代替独立复审或任何 delivery 动作。

## AUTH-20260810-007

- sha256: f3a8462a5c010920498ab1101d5f2dd8947b235308494dedf1c356461651ff97

独立复审关闭全部 4 项 P1 后，用户于 2026-07-19 明确确认“审核及验收通过”。该确认写回为 Review Passed、UA2 Passed 和 `Accepted`，不扩展为创建/执行 `LEAN-*`、commit、merge、push、release、本机同步或 `Closed` 授权。

## AUTH-20260810-008

- sha256: 401dda9453cb5dabb25d7502c5af4e454750e4d1babde31f8ebb5b0437c1b91c

用户随后于 2026-07-19 明确要求“提交”，因此仅授权把 RFC、PLAN-001 和本看板形成 Accepted Git baseline；该授权不包含 merge、push、release、本机同步、`Closed` 或后续 `LEAN-*` 实施。

## AUTH-20260810-009

- sha256: b13ef3d38eeb4821d495fc55897ef3c2582449ed1a98eea8f5b040873b8944de

用户随后要求统一澄清模型来源表述。本轮只使用“当前执行模型真实任务对照”和“额外模型供应商”两个术语，明确独立 Reviewer 可以使用同一平台/模型的隔离上下文；不改变三次上限、评估门禁或授权边界。用户随后再次明确要求“提交”，因此仅授权把该三文件澄清形成独立 commit。

## AUTH-20260810-010

- sha256: c4cc32b6dcd90a0675ba3d5dd4d43c6adeba3480acf1e91181f518522ed3cc57

用户于 2026-07-19 进一步明确要求“按 PLAN-001 串行执行 LEAN-001～003”。该授权允许创建并顺序执行最多 3 个 LEAN TASK、在专用实施分支形成逐任务 commit，并在计划规定的确定性门禁触发时使用隔离只读 Reviewer；不授权并行写代码、merge、push、release、本机 Skill 同步或 `Closed`。若阶段 A、阶段 B 或全面实施门禁失败，串行链必须在失败点停止，不能为了执行到 LEAN-003 而改写阈值或证据。

## AUTH-20260810-011

- sha256: 13ba531d0234730d95826fb2e80fc74b6f1f272ccaafc9e18af7ebe5f795c1f0

`LEAN-002` 随后因实际原型未绑定 stage A、平台不暴露精确 backend model/call ID 而被整体 Review 阻断。用户在理解原因后明确要求继续完成 v0.8；该新指令授权同一 `LEAN-002` 创建 `V08-LEAN-EVAL-003`、先修复两项 P1，再在新协议 Review 通过后执行一个新的三次替代周期。V002 不改、不混用；新授权不包含第三个周期、额外 provider、merge、push、release、本机同步或 `Closed`。

## AUTH-20260810-012

- sha256: bb90aeb58679f15ea28f588002624e8a71234921ac55b9ecb8354ab81d3db8ec

用户于 2026-07-19 明确回复“继续，我已确认。完成上述操作”，完成 `LEAN-003` UA3；随后明确要求“合并推送发布，并且同步本机 skill”。当前授权包括：形成验收/发布候选提交，合并到 `main`，推送 `main`，创建并推送 annotated tag `v0.8.0`，创建正式 GitHub Release，以及同步已确认存在的本机 Skill 副本。该授权不包含 `Closed`、删除分支、改写历史或其他项目的外部操作。

## AUTH-20260810-013

- sha256: 6240161e8c227315efa109745f95eb3b574e515d0121e9dd03761a7737ba6670

用户随后于 2026-07-19 明确要求“关闭并删除分支”。该指令授权把 `LEAN-003` 从 Accepted 流转为 Closed，并删除已确认完全合并的本地 `codex/lean-v08-slimming` 分支；远端不存在同名分支。该授权不包含其他分支、tag、Release 或历史改写。

## AUTH-20260810-014

- sha256: 881ccc90b41a1941e7e70d8aeab542f40b344ffb12bf4e4d974fa13b5884d815

用户于 2026-07-21 明确要求审查其提供的 `.agents` Skill 源目录更新；确认无问题后同步到本项目和本机其他 Skill 位置，并推送远端。该授权覆盖 `SYNC-001` 的内容审查、已存在目标的文件同步、精确 commit 和 `main` push；不包含 tag、GitHub Release、删除未知附加文件或创建不存在的安装目录。Review 发现已发布 `v0.8.0` 与新增内容不能共用版本身份，因此 repair 将工作树身份收口为未发布 `0.8.1`，不制造发布事实。

## AUTH-20260810-015

- sha256: 99888db547a950f0d4a3f5a8dec40fb368fd91f20b1b4ce884e2abc35252835b

用户于 2026-07-24 在复盘修改轮数边界和“超限后即使授权 AI 也拒绝”的问题后明确要求实施。`REPAIR-ESCALATION-001` 获准在独立 Worktree 修改 Skill policy、只读判定器、测试和直接冲突文档；独立 Review 通过后可同步已存在的本机 Skill 副本和 CADCat 流程规则。用户随后明确回复“验收通过，提交并推送”，因此 UA2 记为 Passed，并授权精确 commit 当前任务 diff、推送 `codex/repair-escalation-001` 分支；该授权不包含 merge、tag、Release、删除、历史改写或 `Closed`。

## AUTH-20260810-016

- sha256: 3bcd78ded35eb361f9c07be2e718b9883d57ad566f0a84ad5379e0dcaaa10190

用户于 2026-07-27 进一步确认连续无实质进展阈值采用“核心产品 4 次、Harness 5 次”，并明确要求按新方案修改。`REPAIR-CAMPAIGN-001` 获准在 `REPAIR-ESCALATION-001` Accepted baseline 上实现任务级连续修复授权、只读 gate、测试和直接冲突文档；不授权 commit、push、merge、release、本机同步、Accepted 或 Closed。

## AUTH-20260810-017

- sha256: cf39864cef711ef24eb025957d9ce102de5df72b8d212ea6bd447db99a6beb79

用户随后在收到同 Harness 原生隔离 Reviewer、核心 4 次 / Harness 5 次阈值、CAD AutoTest 单一计数权及“尚未同步生效”的 UA2 摘要后明确回复“通过”。该确认写回为 Review Passed、UA2 Passed 和 `Accepted`；不扩展为 commit、push、merge、tag、Release、本机 Skill 同步或 `Closed` 授权。

## AUTH-20260810-018

- sha256: 2770cbb6d427b4c2a12c6a27726c2bf9e644b8dcdf3d384a7445ad6a6d638c34

用户随后明确回复“提交并推送，同时同步本机 Skill”。该指令授权精确提交本任务 diff、推送当前 `codex/repair-campaign-001` 分支，并同步实盘确认存在的本机 `ai-dev-flow` 与 `cad-dotnet-autotest` Skill 副本；不授权 merge、tag、Release、删除、创建不存在的安装目录、其他项目/服务同步或 `Closed`。

## AUTH-20260810-019

- sha256: fac2ad8aeb8ec074898c87921317a8311ee490cc0cecb14d3c1d90c6d39b905f

用户在确认任务分支已推送、本机 Skill 已同步、但尚未 merge / tag / Release 后明确回复“同步并发版”。该指令授权把当前任务分支合并到 `main`、推送 `main`、创建并推送 annotated tag `v0.8.3`、创建正式非 draft/非 prerelease GitHub Release，并按正式发布源复核现有本机 Skill；不授权删除分支、历史改写、其他项目/服务同步或 `Closed`。

## AUTH-20260810-020

- sha256: 8cf095d1b5c2af5ff0d23776c0b5616ed4553d1c4773c5ad1558145665bdf2e8

用户于 2026-07-28 明确要求建立本地任务关系仪表盘任务：本地使用，以观察完整任务关系为首要目标；前端只冻结总体产品要求和风格推荐，具体实施交给 Kimi；后端必须写清楚。本轮 authority 只允许创建 `DASHBOARD-001` 并同步本看板，不授权前端/后端实现、增加依赖、创建后续实施 TASK、commit、merge、push、release、外部同步或 `Closed`。

## AUTH-20260810-021

- sha256: a8e3a7725e8d2722ca92ea657dc485fa43fb60dcf1ebd5ac7936b0971b527ce3

用户随后要求“审核 DASHBOARD-001”。该指令授权当前 Codex Harness 执行隔离、只读 Review 并把 findings / Review 状态写回 TASK 与看板；不授权修复 findings、进入 UA2、Accepted、实现、commit、merge、push、release 或 `Closed`。

## AUTH-20260810-022

- sha256: 3eb362dd692417eff1ee115154b5ad8302e596700e0f1e4abd7b031e5e653e7c

用户在收到 5 个 P1、1 个 P2 和“Kimi 只读是前端运行时边界，不限制 Kimi 承担后端开发”的说明后明确回复“授权”。该指令仅授权 `DASHBOARD-001` Repair Round 1：修订冻结 findings、验证、隔离只读复审和 TASK/看板收据同步；不授权实施、创建后续 TASK、UA2、Accepted、commit、merge、push、release 或 `Closed`。

## AUTH-20260810-023

- sha256: 54fbb210420960f2992a77fbb9fc04a160ddf203748da8cdeed81716fe936ece

用户在最终 Review Passed 和后续开发顺序说明后明确回复“确认，并创建文档”。该指令授权记录 `DASHBOARD-001` UA2 Passed / Accepted，并创建 `DASHBOARD-BE-001`、`DASHBOARD-BE-002`、`DASHBOARD-FE-001`、`DASHBOARD-INTEGRATE-001` 四份 Draft TASK；不授权执行任务、增加依赖、创建 Worktree、Review 子任务、commit、merge、push、release 或 `Closed`。

## AUTH-20260810-024

- sha256: 5047562b4a4473cb721c440d7cc38f48cf37803e4b7c3215475e0ecacf535e4b

用户随后明确要求“审核四份 DASHBOARD 实施任务，如有问题进行修复，直至通过可执行的程度。然后新开对话框执行 BE-001，审核并通过达到可验收程度”。该指令授权四份 TASK 的隔离 Review、有限 repair 和收据同步；规划通过后只授权在新对话执行 `DASHBOARD-BE-001`，并停在 `Review Passed / UA3 Pending`，不代替用户验收。

## AUTH-20260810-025

- sha256: fa96c3dddf0e28ce877b9c4595ece725194882c9d8e7d9d8340160c31fde0cb3

用户进一步明确“规划文件我授权你可以提交”。该指令仅授权精确提交 `DASHBOARD-001`、四份实施 TASK 和本看板，形成后续 Worktree 可引用的 Git baseline；不授权 push、merge、release、删除、历史改写或代码提交。

## AUTH-20260810-026

- sha256: 3ec055f20577b40c0dce7cf7878535f37b1e45e1907f385cd6fd40f9ff34c7c6

用户在 `DASHBOARD-INTEGRATE-001` 完成真实页面 UA6、独立 Review、提交与本地合并后，明确要求继续执行已说明的收口方案。该指令授权 `REL-003` 将当前开发线收口为 `v0.9.0`，同步实盘确认已存在的本机 `ai-dev-flow` Skill，推送 `main` 与 annotated tag `v0.9.0`，并创建正式 GitHub Release；不授权删除分支/Worktree、强制推送、历史改写、创建未知本机目录或 `Closed`。

## AUTH-20260810-027

- sha256: 2e8e615a622b6e972873849f38d80e940d3b9016bd95e60afd598d00086cb078

`DASHBOARD-PORTABLE-001` 最终独立 Review 仅剩 `DASHBOARD-PORTABLE-RVW-P1-002` 开放。用户于 2026-07-30 在收到“创建 repair TASK、只修 `.pyc/__pycache__` 导入前校验缺口、补测试、完整验证并持续独立 Review 到无 P0/P1”的精确范围后回复“授权”。该指令授权 `DASHBOARD-PORTABLE-REPAIR-001` 的 scope-bound Repair Campaign；不授权新增依赖、改变只读/安全边界、UA6 代验收、Accepted、commit、merge、push、release、本机 Skill 同步或 `Closed`。

## AUTH-20260810-028

- sha256: a4608670dea75985a789f16d7b9846cca56355f95f640f973f39d0620459b787

用户于 2026-07-31 提供 CADCat 实际页面截图，确认关系文字仍被任务卡片遮挡，并在收到根因和独立前端修复建议后明确回复“确认”。该指令授权 `DASHBOARD-EDGE-LABEL-001` 在独立 Worktree 内补充碰撞 oracle、修复关系文字几何布局、运行前端验证、启动本机验收页并执行隔离只读 Review；不授权吸收或覆盖主仓库未提交前端改动，也不授权 commit、merge、push、release、外部同步、Accepted 或 `Closed`。Round 3 Review 发现 `EDGE-LABEL-RVW-P2-004` 后停止自动修复，用户再次回复“确认”，单次授权仅处理该 finding 的 chain-bound `EscalatedRepair`。Round 8 Review Passed 后，用户明确确认“界面修复验收通过”，仅据此记录 UA5 Passed / Accepted；commit、merge、push、release 和 `Closed` 仍未授权。

## AUTH-20260810-029

- sha256: 1c878b0b9a292efe02ef1b2948233d58ed052356d5820688de2c26dfc278423e

本轮允许：

## AUTH-20260810-030

- sha256: 0720701b41d182c5b8209bc21e50cc782b5e2ce50bb8bb2db204bc1e3e589122

- 重写 PLAN-001 和对应 RFC；
- 更新本看板；
- 移除同一未提交规划集中被新方案取代的原 Loop RFC、9 个 `LOOP-*` Draft 和临时 PLAN-002。
- 精确提交上述三文件，形成 PLAN-001 Accepted Git baseline。
- 精确提交上述三文件的模型术语澄清。
- 创建并串行执行 `LEAN-001`～`003`，每项保持独立任务合同、diff、验证、Review 和 commit；后项只能在前项门禁通过后开始。
- 写回 `LEAN-003` UA3 Passed / Accepted，并完成已明确授权的 merge、push、`v0.8.0` tag、GitHub Release 和本机 Skill 同步。
- 写回 `LEAN-003` Closed，并在关闭收据提交后安全删除已完全合并的本地实施分支。
- 在独立 Worktree 实现 `REPAIR-CAMPAIGN-001` 的 campaign policy、4 / 5 次连续无进展阈值、硬停止和兼容测试。
- 精确提交并推送 `REPAIR-CAMPAIGN-001` 当前任务分支，同步实盘确认存在的本机 `ai-dev-flow` 与 `cad-dotnet-autotest` Skill 副本，并写回校验收据。
- 将已验收任务分支合并并推送到 `main`，创建并推送 `v0.8.3` annotated tag 与正式 GitHub Release，并按发布源复核现有本机 Skill。
- 创建 `DASHBOARD-001`，冻结本地关系图优先产品要求、Kimi 前端交接边界和详细只读后端合同，并同步本看板。
- 对 `DASHBOARD-001` 执行隔离、只读 Review，并同步 Review 收据与状态。
- 仅在 `docs/tasks/DASHBOARD-001-local-task-relationship-dashboard.md` 和 `docs/TASK_BOARD.md` 内修订 `P1-001～005`、`P2-006`、Kimi 角色歧义，运行验证并执行隔离只读复审。
- 写回 `DASHBOARD-001` 的用户 UA2 确认与 Accepted 状态，创建四份后续 Draft TASK 文档并同步本看板。
- 审核并有限修复四份 DASHBOARD 实施 TASK，复审通过后将合同推进到 Ready。
- 精确提交 `DASHBOARD-001`、四份实施 TASK 和本看板，形成规划 Git baseline。
- 在规划 baseline 形成后，新开对话并在独立 Worktree 实施 `DASHBOARD-BE-001`，运行验证和独立 Review/repair，停在可供用户 UA3 的状态。
- 在独立 Worktree 实施 `GOAL-USAGE-001`，只增加 Codex 原生 Goal 治理预设、中文触发与测试；不修改 CORE policy、repair gate 或 Contract schema。
- `GOAL-USAGE-001` 已完成 Review、UA、commit、push 与 merge；release / deploy 保持未授权。
- 在独立 Worktree 实施 `DASHBOARD-EDGE-LABEL-001`，只处理关系文字与任务卡片遮挡；已由用户 UA5 验收通过并形成候选提交 `38f5940`。
- 在独立 Worktree 实施 `DASHBOARD-IDLE-PERF-001`，以 Windows 原生文件事件、空闲暂停与单实例降低常驻 CPU；已由用户 UA6 验收通过并形成候选提交 `2963353`。

## AUTH-20260810-031

- sha256: 51892da154493468914bf401ae4d1904e983fe4bdd9960f687a34ea38f3607f3

本轮不允许：

## AUTH-20260810-032

- sha256: f6b3aa207ec7d92be510fb37f0b28be098e69b067c490f9c1532d35cf9f5535d

- 在 `LEAN-001` 阶段修改 `skills/ai-dev-flow/**`、现行行为或执行当前模型真实任务对照；
- 绕过阶段门禁提前创建或执行后续 `LEAN-*`；
- 接入或调用额外模型供应商，或在本计划阶段执行当前模型真实任务对照；
- 不删除其他分支、tag 或 Release，不强制删除未合并分支，不改写已提交历史，不执行额外版本发布或同步未确认的本机目录。
- 不在 `REPAIR-CAMPAIGN-001` 中删除分支、改写历史、创建不存在的安装目录、同步其他项目/服务或记录 Closed。
- 不在 `DASHBOARD-001` 规划阶段实现前端/后端、增加依赖、创建项目级 `PRODUCT.md` / `DESIGN.md`、自动写回 TASK、自动启动并行 agent 或创建后续实施 TASK。
- 不把本轮 repair authority 扩大为前端/后端实施、创建后续 TASK、进入 UA2、记录 Accepted、commit、merge、push、release 或 `Closed`。
- 不把“确认，并创建文档”扩大为执行四份 Draft TASK、创建/切换 Worktree、安装依赖、启动服务、独立 Review、commit、merge、push、release 或 `Closed`。
- 不把本轮新增授权扩大为执行 BE-002、FE-001 或 INTEGRATE-001，也不替代用户 UA3，不执行 push、merge、release、删除、历史改写或 `Closed`。
