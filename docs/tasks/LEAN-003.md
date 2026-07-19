# LEAN-003：全面精简 Skill 并收口 v0.8 实现

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `LEAN-003`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/LEAN-003.md#outcome`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：把 `LEAN-002` 已验证通过的两文件轻量原型落实为正式 v0.8 默认入口，全面精简活跃 Skill、核心 references、模板与提示词，并给出兼容迁移和发布决策。
- 非目标：不重跑或改写 V002/V003 评估；不批量迁移历史 TASK；不建设调度器、数据库、遥测、计费、模型 Adapter、Batch/Wave/Memory 平台；不执行未经用户明确授权的 merge、push、tag、release、`Closed` 或本机 Skill 同步。
- 允许修改：本任务“允许修改范围”列出的 Skill 入口、references、测试、版本和说明文档。
- 禁止修改：本任务“禁止修改范围”列出的冻结评估、原型、Contract 实现/fixtures、历史 TASK、依赖和外部状态。
- 保留：v0.7 的 `adf/v0.7.0` Contract、Reader、只读 lint、TASK_BOARD drift、历史任务和评估证据继续兼容。
- 默认退出：Lite 场景正式采用 `DoNotUseSkill`；仅 Tracked / Controlled 加载 Skill 治理内核。

## 依赖与授权

- 前置依赖：`LEAN-002` V003 `all_gates_pass=true`，整体独立 Review `Passed`，P0-P3 均为 0。
- Base commit：`1a00b62342268dc6e627fd1ff8a7c90bfc1c97d1`。
- 用户授权：按 PLAN-001 串行执行 `LEAN-001`～`003`，并再次明确要求继续完成 v0.8。
- 用户验收与交付授权：用户于 2026-07-19 明确回复“继续，我已确认。完成上述操作”，完成 LEAN-003 UA3；随后明确要求“合并推送发布，并且同步本机 skill”，授权将获准候选合并到 `main`、推送、创建并推送 `v0.8.0` tag、创建正式 GitHub Release，并同步已确认的本机 Skill 副本。
- `Closed`、删除分支、改写历史或其他外部操作仍未授权。

## 实施决策

1. 正式运行时内核只有 `SKILL.md` 与 `references/CORE.md`；其他文档一律按需读取。
2. Lite 同时满足低风险、单会话、不超过 3 个业务文件、无真实环境/发布/不可逆动作且确定性验证完整时，不使用 Skill、不建 TASK、不调用 Reviewer、不进入 repair loop。
3. Tracked 为默认启用 Skill 的路径：建立或沿用 TASK，Git/diff/验证留证；仅命中确定性风险时调用隔离只读 Reviewer。
4. Controlled 用于 D 级、架构、依赖、数据/安全、真实环境、发布、不可逆动作或 UA5～UA7；验收建议和 delivery 前强制独立 Review。
5. Tracked / Controlled repair 基础预算为 2；仅当范围冻结、finding 单调减少、验证改善且没有权限/安全硬阻断时增加第 3 轮；3 为绝对上限。
6. 旧 Batch、Wave、Memory、Constitution、角色、长提示词仍可作为兼容资料手动读取，但退出默认运行路径，不作为 v0.8 首版能力承诺。
7. Skill 包版本收口为 `0.8.0`；Contract schema 继续为 `adf/v0.7.0`。本任务只形成“实现完成、待用户验收/发布决策”，不制造已发布事实。

## 允许修改范围

- `skills/ai-dev-flow/SKILL.md`
- `skills/ai-dev-flow/README.md`
- `skills/ai-dev-flow/VERSION`
- `skills/ai-dev-flow/references/CORE.md`
- `skills/ai-dev-flow/references/WORKFLOW.md`
- `skills/ai-dev-flow/references/PROMPTS.md`
- `skills/ai-dev-flow/references/TASK_TEMPLATE.md`
- `skills/ai-dev-flow/references/TASK_TEMPLATE_COMPACT.md`
- `skills/ai-dev-flow/references/AGENTS_COMPAT.md`
- 与新路由直接冲突的 review / validation / acceptance / Contract 说明
- `skills/ai-dev-flow/references/V0.8_MIGRATION.md`
- `skills/ai-dev-flow/tests/test_compact_writer_routing.py` 及必要的 v0.8 专项测试
- `README.md`、`README.en.md`、`skills/ai-dev-flow/CHANGELOG.md`、本任务与 `docs/TASK_BOARD.md`
- `CONTEXT.md` 中与当前版本和已实现架构直接冲突的旧事实

## 禁止修改范围

- `evaluations/v0.8/**` 与 `skills/ai-dev-flow/prototypes/v0.8-lite/**`
- `skills/ai-dev-flow/src/**`、`skills/ai-dev-flow/scripts/**` 与 v0.7 golden fixtures
- 历史 TASK、历史 release artifacts、依赖声明和项目技术栈
- 未经用户明确授权的 merge、push、tag、release、外部同步或本机 Skill 安装

## 完成标准与验证

- 完成标准：正式两文件入口、三档 policy、Reviewer/repair 门禁、兼容迁移、版本身份和验证证据全部收口。
- 验证命令或检查：Skill 全套 unittest、v0.8 专项测试、v0.7 Contract/lint 回归、链接检查和 `git diff --check`。

- [x] 正式默认内核仅两文件，Lite/Tracked/Controlled 路由与强制升级条件可机械检查。
- [x] Lite 明确 `DoNotUseSkill`，不建 TASK、不调用 Reviewer、不进入 repair loop。
- [x] Tracked 风险触发和 Controlled 强制 Review 覆盖 V003 policy 的安全/权限边界。
- [x] repair 第 3 轮只有 progress gate 通过才允许，且绝对上限为 3。
- [x] 活跃文档与模板明显缩短，默认路径不再预加载 PROMPTS、Batch、Wave、Memory、Constitution 或角色指南。
- [x] v0.7 Contract / Reader / lint / TASK_BOARD drift 继续通过，无历史 TASK 批量改写、无新依赖。
- [x] 迁移说明最多 3 个用户步骤，并明确旧任务无需迁移。
- [x] 版本身份明确区分“0.8.0 发布候选”和 tag / GitHub Release 形成的实际发布事实。
- [x] 现行 Skill 全套测试、专项 policy/版本/模板测试、TASK lint、本地链接与 diff hygiene 通过；冻结 evaluation/prototype 零改动。
- [x] 独立 Reviewer 完成只读审查且无开放 P0～P3，明确允许进入 UA3 和形成独立 commit。

## 验证计划

```powershell
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py" -v
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/LEAN-003.md --format human
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format human
git diff --exit-code 1a00b62 -- evaluations/v0.8 skills/ai-dev-flow/prototypes/v0.8-lite
git diff --check
```

## Outcome

- Base / Diff：base=1a00b62;diff=1a00b62..HEAD
- 隔离位置：branch=codex/lean-v08-slimming
- 回滚方式：revert 本任务独立 commit；不使用破坏性 reset。
- 修改文件：正式 `SKILL.md + CORE.md` 两文件内核；精简 WORKFLOW/PROMPTS/TASK/AGENTS/README；增加三步迁移说明和 v0.8 回归测试；同步版本、Changelog、兼容指南、本 TASK 与 TASK_BOARD。
- 验证证据：47 / 47 Skill unittest 通过（含 v0.7 Reader/lint/TASK_BOARD 和 v0.8 policy/模板/版本回归）；Skill quick validation 通过；本 TASK lint 为 0 error / 0 violation；17 个变更 Markdown 本地链接缺失 0；frozen evaluation/prototype zero-diff 和 `git diff --check` 通过。
- 精简量：默认运行时 285 行（SKILL 116 + CORE 169）；SKILL 288→116（-59.72%）、WORKFLOW 615→141（-77.07%）、PROMPTS 1182→67（-94.33%）、TASK_TEMPLATE 389→68（-82.52%）。
- Review findings：`LEAN003-P1-001`、`LEAN003-P1-002` 均 Closed；最终 P0=0、P1=0、P2=0、P3=0，结论 Passed。
- UA 动作与结果：UA3 Passed；用户于 2026-07-19 查看精简量、47 / 47 自动测试和独立 Review 证据后明确回复“继续，我已确认。完成上述操作”。
- 发布决策：用户于 2026-07-19 明确授权合并、推送、正式发布 v0.8.0 并同步本机 Skill；实际 merge commit、远端 main、tag、Release 和本机哈希收据在操作完成后补录。
- 历史评估边界：V002/V003 live manifest 绑定实施前 Full workflow，正式入口变化后 full digest 红灯是预期 tripwire；不得修改旧 manifest 造假绿，本任务以 evaluation/prototype 零 diff 和正式 policy 与冻结 prototype 完全相等作为证据。

## 状态边界

- 当前为 `Accepted / Review Passed / UA3 Passed / Committed / Unmerged`，发布交付已获授权、尚待实际收据。
- `VERSION=0.8.0` 与 Accepted 不单独等于 tag、Published、Released、Merged 或 Closed；实际状态以 Git 和 GitHub 收据为准。
