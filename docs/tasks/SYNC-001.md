# SYNC-001：审查并同步 ai-dev-flow Skill 增量

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `SYNC-001`
- `task_type`: `document`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Not Applicable`

## 目标与边界

- 目标：审查用户提供的 `.agents` Skill 源目录增量；确认无阻断问题后同步到仓库 Skill 源和已存在的本机安装副本，验证一致性，提交并推送 `main`。
- 非目标：不创建 tag 或 GitHub Release；不改写 v0.8.0 历史任务；不新建当前不存在的 harness 安装目录；不清理用户既有未跟踪文件。
- 允许修改：`skills/ai-dev-flow/**` 中源目录增量及其 Review 必需修复；根目录中英文 README 的工作树版本说明；`docs/tasks/SYNC-001.md`；`docs/TASK_BOARD.md`；已确认存在的本机 `ai-dev-flow` 安装副本和用户提供的源目录。
- 禁止修改：历史 release artifacts、评估证据、原型、依赖、其他 Skill 和不存在的安装目录。

## 依赖与授权

- 前置依赖：`LEAN-003` Closed；`v0.8.0` 已发布。
- Base commit：`d4854a791e09115fff0e3490afc725b4161d7acc`。
- 已有 authority：用户明确要求审查通过后同步到本项目和本机其他 Skill 位置，并推送远端。
- 未授权动作：创建 tag / Release、删除文件或目录、改写历史、同步到未确认存在的目标。
- 执行位置：`main`；仓库当前与 `origin/main` 同步。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；请求动作包含 delivery / external sync / push；风险标记为 `delivery`、`external_sync`；本机文件一致性和远端状态需要真实环境证据。
- Reviewer 闸门：Required；同步和 push 前完成隔离只读 Review。
- 停止条件：发现 P0/P1、源目录验证出现与安装边界无关的失败、目标目录存在无法归属的差异、远端发生并发更新、或实际范围超出本任务。

## 完成标准与验证

- 完成标准：源增量无开放 P0/P1；仓库与本机现有副本哈希一致；仓库验证通过；精确提交并确认远端 `main` 到达该提交。
- 验证命令或检查：Skill validator、48 项 unittest、targeted/project workflow lint、本地 Markdown 链接、逐文件 SHA256、`git diff --check`、`git status`、远端 ref 核对。

- [x] 源增量经内容审查，无开放 P0/P1；新增模板与 v0.7 Contract、v0.8 路由和加载预算一致。
- [x] 仓库 Skill 源与用户提供的源目录逐文件 SHA256 一致（忽略运行生成的 `__pycache__` / `.pyc`）。
- [x] 已存在的本机安装副本与仓库 Skill 源逐文件 SHA256 一致；不创建不存在的副本。
- [x] 仓库完整 unittest、Skill validator、TASK lint、本地 Markdown 链接和 `git diff --check` 通过。
- [x] 精确提交本任务 diff，并确认 `origin/main` 到达该提交。

## Outcome

- Base / Diff：base=d4854a791e09115fff0e3490afc725b4161d7acc;diff=d4854a791e09115fff0e3490afc725b4161d7acc..fcd3a3e。
- 隔离位置：`main`；独立只读 Reviewer 使用隔离 subagent。
- 回滚方式：对本任务精确提交执行 `git revert`；本机副本可从提交前哈希清单核对并重新同步已发布 `v0.8.0` 源。
- 修改文件：新增 `TASK_TEMPLATE_BRIEF.md`；更新 Skill 入口、Reviewer 隔离、模板路由、版本/Changelog、根目录中英文 README、专项测试，以及 `SYNC-001` / TASK_BOARD 记录。
- 验证证据：原始源目录 47 项 unittest 中 44 通过、3 项因安装目录缺少仓库根 `README.md` / `README.en.md` 报错，符合已知安装副本测试边界；repair 后仓库 Skill validator、48 / 48 unittest、78 个 Markdown 本地链接与 `git diff --check` 通过；新增 `test_brief_template_is_tracked_only_and_v07_compatible` 专项覆盖。
- 验证证据：用户提供的 `.agents` 源、Codex、OpenCode、cc-switch、Trae 五个目标均为 `VERSION=0.8.1`、90 / 90 文件，逐文件 SHA256 为 `Missing=0 / Extra=0 / Changed=0`，且五个目标的 Skill validator 全部通过；未创建缺失目录。
- 验证证据：同步前 `main...origin/main` divergence 为 `0 / 0`；实现提交 `fcd3a3e` 已成功 push 到 `origin/main`，远端返回 `d4854a7..fcd3a3e main -> main`。
- Review findings：第 1 轮 `Needs Fix`，经两轮有限 repair 与隔离复审后 `SYNC-001-P1-01`～`P1-04`、`P2-01`～`P2-04` 全部 Closed；最终结论 `Passed`，P0-P3 无开放项，允许进入同步、精确 commit 和 push。
- UA 动作与结果：UA3 Pending；用户已授权执行审查、同步和 push，但完成结果尚未交付，不把动作授权写成验收通过。
- 状态边界：本机同步、实现 commit 和 push 已完成；Review Passed；UA3 仍 Pending；未创建或授权 tag、Release、删除或新建不存在的安装目录。
- 剩余风险：`0.8.1` 是未发布开发线，不等于正式 release；用户尚未对最终证据完成 UA3。
- 下一步：提交并 push 本收据记录；用户查看证据后可决定是否接受，未来如需正式发布 `v0.8.1` 应另行授权。
