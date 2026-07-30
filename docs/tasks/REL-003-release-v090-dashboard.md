# REL-003：发布 v0.9.0 本地任务关系仪表盘

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `REL-003`
- `task_type`: `document`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA7`
- `ua_status`: `Passed`
- `ua_evidence`: `#rel-003-ua7-2026-07-30`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`

## 目标与边界

- 目标：把已 Accepted、Committed、Merged 的 Dashboard 全链路和 v0.8.3 后的 Workflow Contract 校验修复收口为 `ai-dev-flow v0.9.0`。
- 目标：形成一致的 VERSION、CHANGELOG、根目录中英文 README、Skill README、annotated tag 和正式 GitHub Release。
- 目标：把同一版本的 `skills/ai-dev-flow` 同步到实盘确认已存在的本机 Skill 目录，并用逐文件 SHA256 验证源文件一致。
- 非目标：不改变 Dashboard 或 Workflow Contract 行为，不新增依赖，不删除分支/Worktree，不改写历史，不记录任何任务 `Closed`。
- 允许修改：`README.md`、`README.en.md`、`skills/ai-dev-flow/VERSION`、`skills/ai-dev-flow/CHANGELOG.md`、`skills/ai-dev-flow/README.md`、`skills/ai-dev-flow/references/TASK_TEMPLATE.md`、`skills/ai-dev-flow/references/TASK_TEMPLATE_BRIEF.md`、`skills/ai-dev-flow/references/V0.8_MIGRATION.md`、`skills/ai-dev-flow/tests/test_compact_writer_routing.py`、`docs/TASK_BOARD.md` 和本任务文件。
- 允许外部动作：只同步已存在的本机 `ai-dev-flow` Skill 目标；推送 `main` 与 annotated tag `v0.9.0`；创建非 draft、非 prerelease GitHub Release。
- 禁止修改：Dashboard 实现、Contract schema、Skill policy/Reader/lint 行为、依赖、其他项目、密钥和未知本机目录；禁止删除或强制覆盖 Git 历史。

## 依赖与授权

- 前置依赖：`DASHBOARD-INTEGRATE-001` 已达到 `Accepted / Review Passed / UA6 Passed / Committed / Merged`；本地 `main@1cee70e`。
- Base commit：`1cee70e33e61e2f2cdc6be08c7ee7694dac36975`
- 已有 authority：用户明确要求继续执行已说明的 `v0.9.0` 收口方案，授权提交、合并、本机同步、推送 `main`、创建并推送 `v0.9.0` tag 以及创建正式 GitHub Release。
- 未授权动作：删除分支/Worktree、强制推送、历史改写、同步不存在或来源不明的目录、其他项目/服务外部写入和 `Closed`。
- 执行位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\rel-003-v090-dashboard`，分支 `codex/rel-003-v090-dashboard`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 级；requested actions=`delivery, merge, release, external_sync`；risk flags=`delivery, external_sync, release, shared_component`；需要版本、Review、Git、远端与本机哈希证据。
- Reviewer 闸门：`Required`；版本候选必须在合并、push、tag、Release 和本机同步前通过隔离只读 Review。
- 停止条件：版本口径不唯一、测试或 lint 失败、Review 存在开放 P0/P1、目标 Skill 来源不明、远端发生未知分叉、tag 已存在或发布动作需要强推。

## 完成标准与验证

- 完成标准：版本、文档、验证、Review、本机同步、Git push/tag 与 GitHub Release 形成可复核的同一 `v0.9.0` 发布身份。
- 验证命令或检查：运行 Skill validator、ai-dev-flow/backend/integration/frontend 全量测试、workflow lint、版本与文档静态检查、本机逐文件 SHA256、Git/远端/tag/Release 复核。
- [x] `VERSION`、CHANGELOG、README、模板迁移说明和版本测试对 `0.9.0` 形成唯一当前结论，同时保持 Contract schema=`adf/v0.7.0`。
- [x] CHANGELOG 准确覆盖 Dashboard 只读关系图、确定性调度、实时本地 API/UI、集成门禁以及 v0.8.3 后的 Contract 校验修复。
- [x] Dashboard 集成、frontend、backend、ai-dev-flow 全量验证通过；workflow lint、quick_validate、版本残留、UTF-8、链接、敏感信息和 diff hygiene 检查通过。
- [x] 隔离只读 Review 无开放 P0/P1，UA7 授权与发布边界写回。
- [ ] 已存在本机 Skill 目标的全部源文件 `Missing=0 / Changed=0`；目标专有文件不删除，未知目标不创建。
- [ ] 本地/远端 `main` 一致，annotated tag `v0.9.0` 本地与远端 peeled commit 一致，GitHub Release 为正式发布。
- [x] `git diff --check` 通过，diff 只归属当前 TASK。

## Outcome

- Base / Diff：base=1cee70e33e61e2f2cdc6be08c7ee7694dac36975;diff=12a07fec2e2d1ba1b714dc7b8f25d71f9a90aa4d
- 修改文件：VERSION、CHANGELOG、根目录中英文 README、Skill README、两份 TASK 模板、v0.8 迁移说明、版本一致性测试、本 TASK 与 TASK_BOARD；未修改产品代码、Contract schema、policy 或依赖。
- 验证证据：Skill validator `Skill is valid!`；ai-dev-flow `85/85`、backend `130/130`、integration `35/35`、frontend unit `82/82`、Chrome `83/83` 均通过，codegen/typecheck/ESLint/build 通过。
- 验证证据：Artifact Guard 测试前后均为 `100/100` 且 changed/added/missing=`0/0/0`；当前任务 lint=`0 error / 0 violation / 2 expected warnings`；全仓 lint 的 2 个 Board drift 已修正，剩余 `19 errors / 0 violations / 32 warnings` 均来自既有 Legacy CONTRACT-001～006 解析债。
- 验证证据：当前版本入口 `0.8.3` 残留为 0；10 个改动中的已跟踪文件全部严格 UTF-8；相对 Markdown 链接缺失 0；secret-shaped diff 命中 0；`git diff --check` 通过。
- 验证证据：`npm ci` 未修改锁文件；npm audit 报告既有依赖树 `3 moderate / 6 high / 1 critical`，本任务不新增、升级或修复依赖。
- 验证证据：版本候选提交=`12a07fec2e2d1ba1b714dc7b8f25d71f9a90aa4d`；精确 11 文件，未包含产品代码、依赖或生成物。
- Review findings：隔离只读 Review session `019fb0c6-0447-76a3-b675-b6b668be68cf` 为 `Passed`，P0/P1/P2/P3=`0/0/1/0`；唯一 P2 为 TASK_BOARD 顶部当前模式/下一动作过时，已按 Reviewer 建议同步为 REL-003 当前状态。
- UA 动作与结果：UA7 Passed；用户在获知 `v0.9.0` 收口、本机 Skill 同步、push、tag 与正式 GitHub Release 的完整动作后明确回复“那进行吧”，记为 `User Confirmed`；不包含 `Closed` 或删除。
- 状态边界：`Accepted / Review Passed / UA7 Passed / Committed / Unmerged / Not Released / Not Closed`。
- 剩余风险：本机 Skill 目标清单须以执行时实盘存在路径为准；目标专有文件不得删除。全仓 Legacy lint 错误为发布前已存在债，本次不扩范围改写历史 CONTRACT TASK。
- 下一步：按已授权顺序合入本地 `main`，同步已存在本机 Skill，再 push/tag/Release。

<a id="rel-003-ua7-2026-07-30"></a>
## UA7 授权与验收（2026-07-30）

- 用户已明确授权执行此前说明的完整收口方案：`v0.9.0` 发布身份、本机 Skill 同步、远端 `main` push、annotated tag 和正式 GitHub Release。
- 自动验证与独立 Review 已先行通过；本次 UA7 只授权上述发布动作，不授权删除分支/Worktree、强制推送、历史改写或 `Closed`。
