# Changelog

## Unreleased

- Add zero-state Codex Goal governance presets: `governed_goal`, `auto_land`, and separately bounded `auto_release`.
- Add explicit Chinese trigger phrases such as “启动受控目标”, “启动自动落地目标”, “我去休息，自动修好并交付”, and version/environment-bound automatic release phrases.
- Keep native Goal runtime state outside the Skill and Workflow Contract; reuse existing TASK, Review, UA, repair-campaign, and delivery authority boundaries without changing `CORE.md` or `repair_gate.py`.
- Supersede the unmerged custom `UnattendedRun` state-machine candidate without deleting its Worktree.

## 0.9.1 - 2026-07-30

> `ai-dev-flow v0.9.1` 是跨项目 Dashboard 的正式发布身份；Workflow Contract schema 继续为 `adf/v0.7.0`，Scheduling schema 继续为 `ai-dev-flow/scheduling/v1`。

- Separate `project-root` from an external installed `skill-root`; ordinary Git projects no longer need a copied or linked Skill checkout.
- Package the Dashboard backend, built frontend, contracts, and launcher inside the complete Skill distribution.
- Add automatic loopback port selection, explicit port overrides, per-instance IDs, runtime directories, state files, caches, and independent cleanup.
- Pin Skill and Contract inputs at startup, fail closed on incompatible Skill/Workflow/Scheduling versions, and request restart after runtime bundle changes without hot-mixing schemas.
- Preserve loopback-only, no-write API, no project/Skill/Git mutation, no Worktree creation, and no governance authority boundaries.
- Keep source-checkout launch compatibility while adding installed-Skill, two-project isolation, bundle parity, cleanup, schema-freeze, CSP, and Windows LF regressions.

### Delivery facts

- `DASHBOARD-PORTABLE-001` and repairs reached `Accepted / Review Passed / UA6 Passed / Committed / Merged`.
- Final pre-merge Review session `019fb2af-da14-7e20-b515-d1de3beb6663` passed with P0/P1/P2=`0/0/0`.
- The annotated tag, local Skill parity, remote push, and GitHub Release are separate delivery facts; their receipts are tracked in `docs/tasks/REL-004-release-v091-portable-dashboard.md`.

## 0.9.0 - 2026-07-30

> `ai-dev-flow v0.9.0` 正式发布身份；对应 annotated tag `v0.9.0` 和正式 GitHub Release。Skill 包版本升级不改变 Workflow Contract schema，后者继续为 `adf/v0.7.0`。

- Add a read-only local task relationship Dashboard built from TASK and Git facts, with deterministic dependency, scheduling, parallel-candidate, and decision views.
- Add a strict versioned Dashboard contract shared by the Python backend and TypeScript frontend, with fresh, stale, partial, parse-error, cycle, degraded-Git, and unknown-parallel states.
- Add a loopback-only local HTTP/SSE service, relationship-graph frontend, task detail panel, search and structural filters, upstream/downstream focus, responsive layouts, keyboard support, and non-color state cues.
- Add Accepted-artifact integrity checks, real backend-to-frontend state matrices, process-tree cleanup, Windows reference-profile benchmarks, and three contract viewport checks.
- Preserve unknown scheduling evidence as unknown instead of guessing; the Dashboard remains read-only and never writes TASK, TASK_BOARD, Git, or external services.
- Harden Workflow Contract validation for repair-campaign authority and receipt chains added after v0.8.3.

### Release receipt

- `DASHBOARD-INTEGRATE-001` reached `Accepted / Review Passed / UA6 Passed / Committed / Merged` before release preparation.
- Release verification, local Skill parity, tag, remote push, and GitHub Release evidence are recorded in `docs/tasks/REL-003-release-v090-dashboard.md`.

## 0.8.3 - 2026-07-27

> Skill `0.8.3` 的正式发布身份；对应 annotated tag `v0.8.3` 和正式 GitHub Release，Workflow Contract schema 继续为 `adf/v0.7.0`。

- Add optional task/acceptance/scope-bound `RepairCampaignAuthority`; non-campaign ledgers retain their original rc2-policy verification path for existing one-attempt `EscalatedRepair` receipts, while campaign and new receipts use rc3 policy.
- Stop core-product campaigns after four consecutive no-progress attempts and Harness campaigns after five; measurable progress resets the streak.
- Bind campaign state to trusted-context-attested receipts so changing TASKs, models, chains, or finding names cannot self-reset the streak.
- Bind campaign activation to its issuing chain/history head so pre-authority patches stay excluded while every later-chain AutoRepair or EscalatedRepair patch advances campaign freshness.
- Enforce immediate campaign hard stops for P0, security, data, scope, irreversible, external-side-effect, weakened-oracle, dependency, and missing-evidence risks.
- Default independent Review to the current Harness's own native isolated read-only context; block instead of automatically falling back across Harnesses unless the user explicitly selects an external Reviewer.
- Extend the read-only repair gate and regression suite with campaign scope, history, threshold, compatibility, and hard-stop coverage.

## 0.8.2 - Unreleased development snapshot

> `0.8.2` 未单独创建 tag 或 GitHub Release；其累计变更随 `v0.8.3` 正式发布。

- Add a brief TASK template for eligible single-session Tracked work while keeping the full template mandatory for Controlled and handoff-oriented work.
- Clarify that Reviewer isolation requires both independent context and real read-only enforcement.
- Keep template routing consistent across active on-demand references and add focused regression coverage.
- Define three rounds as the autonomous AutoRepair maximum instead of a permanent ban on AI repair.
- Add explicit, bounded user-authorized EscalatedRepair after Stop, with one attempt by default and independent re-review after every attempt.
- Bind repair history to a stable chain/finding/closure contract so TASK or model changes cannot reset the budget.
- Replace raw P0/P1-count and ad hoc validation-score progress with per-finding RED/GREEN, regression, severity, and evidence-coverage gates.
- Add the dependency-free read-only `repair_gate.py` evaluator, external trusted-context comparison, mechanical-eligibility/final-authorization separation, canonical policy digest, and boundary regression tests.

## 0.8.0 - 2026-07-19

> Skill `0.8.0` 已通过 annotated tag `v0.8.0` 与正式 GitHub Release 发布；Workflow Contract schema 继续为 `adf/v0.7.0`。

- Replace the default full workflow with a two-file runtime core: `SKILL.md` and `references/CORE.md`.
- Route eligible low-risk work to `DoNotUseSkill`, with no TASK, Reviewer, or repair loop.
- Keep Tracked TASK evidence while triggering a read-only Reviewer only for deterministic risk flags.
- Require Controlled Review before acceptance recommendation, delivery, merge, and release.
- Allow a third repair round only when the frozen progress gate passes; keep three as the absolute maximum.
- Slim the active workflow, prompt library, TASK template, AGENTS compatibility rules, and package README.
- Move Batch, Wave, Loop, Memory, Constitution, roles, provider, and harness material out of the default runtime path while retaining compatibility files.
- Add a three-step v0.7 migration guide with no historical TASK rewrite and no new dependency.
- Preserve the v0.7 read-only Contract Reader, lint, TASK_BOARD drift checks, fixtures, and `adf/v0.7.0` schema.

### Release receipt

- v0.8 独立 Review 已 Passed，P0-P3 均为 0；LEAN-003 UA3 已 Passed。
- 用户已明确授权合并、推送、创建并推送 `v0.8.0` tag、创建正式 GitHub Release 和同步本机 Skill。
- annotated tag `v0.8.0` 的本地与远端 peeled commit 均为 `e35f3eabe6ed1fd57cc68f62be3adba8a65ff59c`。
- GitHub Release `ai-dev-flow v0.8.0` 已正式发布，状态为非 draft、非 prerelease。

## 0.7.0 - Released

> 仓库保留 `v0.7.0` 历史 tag；Workflow Contract 接口版本独立为 `adf/v0.7.0`。

- Add the canonical Workflow Contract grammar and JSON Schema for `adf/v0.7.0`.
- Add golden fixtures and deterministic comparison baselines for legacy and Compact tasks.
- Add read-only Legacy / v0.7 readers with normalized views and provenance.
- Add the read-only `workflow_lint` CLI with stable Human and JSON diagnostics.
- Add Compact v0.7 task routing for eligible new A/B tasks while preserving Full/Legacy routes for complex paths.
- Add read-only TASK_BOARD projection and drift diagnostics with TASK remaining authoritative.
- Keep Skill `VERSION` and Workflow Contract `schema_version` independently versioned.
- Keep lint, Review, UA, merge, release, and task closure as separate states and authorities.

## 0.6.0 - Release ready (not published)

> 仓库内版本身份已收口为 `0.6.0`。当前提交尚未创建 Git tag 或 GitHub Release，因此这里的 “Release ready” 不表示已经对外发布。

- Add Intake guide for requirement capture before task creation.
- Add Loop Engineering guide for triage, goal, review-repair, and status loops.
- Add Review Repair Loop guide with bounded repair rounds and escalation rules.
- Add Role Guide for Orchestrator, Planner, Engineer, Reviewer, Verifier, Repairer, and Archivist.
- Add Project Constitution template using MUST / SHOULD / MUST NOT rules.
- Add Memory Guide for durable project knowledge under docs/memory/.
- Add optional GitHub Issues backend design without automatic sync.
- Add Harness Compatibility guide for Codex, Claude Code, Cursor, Gemini CLI, DeepSeek, and generic agents.
- Add Loop State template for loop run summaries.
- Update prompts, task template, workflow, safety rules, and scripts roadmap.
- Add Bug Diagnosis guide for evidence-first debugging.
- Add TDD guide for behavior-first red/green development.
- Add Requirement Grilling guide for high-risk or unclear requirements.
- Add Project Context guide for durable domain vocabulary.
- Add Session Handoff guide for cross-session continuity.
- Add Architecture Review guide for read-only architecture friction reports.
- Add Real Environment Signal guide for RED/GREEN/SIGNAL handling of user acceptance failures.
- Integrate feedback-loop guides with Acceptance, Validation, Task Template, Prompts, Glossary, and AGENTS compatibility rules.

### Release gate

- 计划 tag 名称为 `v0.6.0`。
- 只有在独立 Review 无 P0/P1、版本一致性验证通过并取得 UA7 用户明确授权后，才允许从获准的发布提交创建 tag。
- 创建 tag、push tag、创建 GitHub Release、merge 和同步本机 Skill 副本都是独立操作，不由版本号更新自动授权。

## 0.5.2

- 强化 Parallel Wave 中代码任务的工作区隔离规则。
- 明确并行代码任务默认应使用独立分支或 Worktree。
- 强化 B 级小代码 Batch 的 per-task diff / commit 归属要求。
- 明确 Batch diff 无法按任务拆分时不得强行通过审查。

## 0.5.1

- 泛化开源文档中的具体技术示例。
- 移除偏项目化的宿主程序、嵌入式页面和外部软件名称示例。
- 保留 UA、Batch、Wave 等通用流程规则不变。

## 0.5.0

- 增加批量小任务 Batch 流程。
- 增加批量小任务执行规则。
- 增加批量小任务审查规则。
- 增加 `BATCH` 文件建议格式。
- 增加 Parallel Wave 任务并行流程。
- 增加 Batch 和 Wave 区分。
- 增加文件锁 / 模块锁。
- 增加并行任务准入规则。
- 增加 `WAVE` 文件建议格式。
- 增加 Review Hub 审查 Batch / Wave 的规则。
- 明确 A/B 小任务可批量，C/D 任务默认单独。
- 明确批量执行不是多任务并行写代码。
- 明确并行执行必须用户确认。
- 明确 D 级和 UA5 / UA6 / UA7 任务默认不得进入代码并行。
- 明确 Batch / Wave 审查必须逐任务输出结论。

## 0.4.1

- 明确 UA0 任务默认不自动标记为 `Closed`。
- UA0 任务完成后 agent 只能建议关闭，除非用户明确确认或项目规则已授权。
- 将“无需用户验收”和“允许关闭任务”拆开表达，避免 agent 跳过关闭确认。

## 0.4.0

- 增加用户动作等级 UA0~UA7。
- 明确人工验收不等于人工代码审查。
- 增加是否需要用户实机测试字段。
- 增加验收建议输出格式。
- 明确哪些任务无需用户验收，哪些需要文档验收、证据验收、本地运行、实机业务测试、回归验收或用户决策。

## 0.3.0

- 增加 Git baseline 规则。
- 增加 Git precheck。
- 增加 A/B/C/D 任务分级。
- 增加分支 / Worktree 使用规则。
- 增加 pre-commit diff review 和 post-commit diff review。
- 增加 base commit 记录要求。
- 增加不得盲目 `git add .` 规则。
- 修正 `execute_task` / `review_task` 默认参考文件。
- 修正执行任务提示词，避免小任务被机械升级为分支或 Worktree 任务。

## 0.2.0

- 增加使用模式。
- 增加任务状态机。
- 增加停止条件和权限分级。
- 增加验证指南。
- 增加任务膨胀处理。
- 增加并发冲突规则。
- 增加项目适配模板。
- 增加审查严重等级。
- 增加交接摘要。
