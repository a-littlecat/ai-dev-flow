# REL-002：收口 v0.7 发布身份并同步本机 Skill

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `REL-002`
- `task_type`: `document`
- `task_class`: `B`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/REL-002-close-v07-release-identity-and-sync.md#outcome`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`

## 目标与边界

- 目标：把 Skill 分发包版本从 `0.6.0` 收口为 `0.7.0`，并让 VERSION、CHANGELOG、README 与已 Accepted 的 CONTRACT-001～006 保持一致。
- 目标：明确 `0.7.0` 是包含 Workflow Contract 首批能力的 Skill 包版本，同时保持 `adf/v0.7.0` 为独立的 Contract 接口版本。
- 目标：仓库改动完成验证和独立 Review 后，把同一份 `skills/ai-dev-flow` 同步到 Codex、OpenCode、Gemini/Antigravity，并提供逐文件哈希一致性证据。
- 非目标：不创建或推送 Git tag，不创建 GitHub Release，不执行 push、merge、发布或分支清理。
- 非目标：不新增 v0.7 功能，不修改 Workflow Contract 语义、Reader、lint、Writer 路由、fixture 或测试行为。
- 允许修改：`README.md`、`README.en.md`、`skills/ai-dev-flow/VERSION`、`skills/ai-dev-flow/CHANGELOG.md`、`skills/ai-dev-flow/README.md`、`docs/TASK_BOARD.md` 和本任务文件。
- 允许修改：通过本机同步更新 `C:/Users/92336/.codex/skills/ai-dev-flow`、`C:/Users/92336/.config/opencode/skills/ai-dev-flow`、`C:/Users/92336/.gemini/config/plugins/codex-ai-dev-flow/skills` 及 Gemini 插件清单的版本字段；本机路径不得写入仓库发布文档。
- 禁止修改：`skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md`、Schema、scripts、tests、fixtures、模板和 Prompt 的行为语义。
- 禁止修改：Git tag、GitHub Release、远程仓库、依赖、许可证、密钥、账号和其他本机 Skill。

## 完成标准与验证

- 完成标准：`VERSION`、根目录中英文 README、Skill README 和 CHANGELOG 对当前 Skill 包版本形成唯一的 `0.7.0` 结论，不再把 `0.6.0` 表述为当前版本。
- 完成标准：CHANGELOG 准确概括 CONTRACT-001～006 已交付能力，并明确 release-ready、tag、GitHub Release 和实际发布是不同状态。
- 完成标准：文档明确 Skill `VERSION=0.7.0` 与 Contract `schema_version=adf/v0.7.0` 独立演进，不把 lint 通过夸大为 Review、UA、merge 或 release 完成。
- 完成标准：仓库 Skill、Codex、OpenCode、Gemini/Antigravity 的相对文件清单和逐文件 SHA256 完全一致，均报告 `VERSION=0.7.0`；Gemini 插件清单版本同步为 `0.7.0`，且不存在重复嵌套旧副本。
- 完成标准：独立 Review 无 P0/P1，UA3 只验收版本一致性、验证证据和本机同步证据；任何 tag、push、GitHub Release 或 merge 仍需新的 UA7 明确授权。
- 验证命令或检查：运行 `quick_validate.py skills/ai-dev-flow`、完整 `test_*.py`、workflow lint、JSON/Markdown/UTF-8/链接/版本残留检查、`git diff --check` 和敏感信息扫描。
- 验证命令或检查：同步后比较仓库源与三个 agent 目标的相对文件集合及逐文件 SHA256，并解析 Gemini `plugin.json` 验证版本；运行 `git status --short` 证明本机同步没有污染仓库工作区。

## 执行顺序与授权边界

1. 以执行时的 `main` HEAD 为 Base，在独立分支完成仓库内版本身份修改，不在主工作区直接混入其他任务改动。
2. 运行完整自动验证并记录版本残留、测试、lint、链接、UTF-8、diff hygiene 和敏感信息扫描结果。
3. 由独立 Reviewer 基于 Base 到 HEAD 的 diff 审查版本口径、范围和发布措辞；有 P0/P1 时只进入有限 repair，不同步本机副本。
4. Review 通过后，镜像同步到三个已确认的本机 agent 目录；保留 Gemini 插件外层结构，只更新其 `skills` 内容和 manifest 版本。
5. 重新执行逐文件哈希、版本和 Skill validator 验证，提交 UA3 证据。
6. 本任务即使 Accepted，也不产生 tag、push、GitHub Release、merge 或 Closed 授权。

## 停止条件

- CONTRACT-001～006 的 Accepted 状态、当前 `main` 祖先关系或版本范围无法形成单一结论。
- 版本收口需要改变 Contract 语义、代码行为、依赖、许可证或新增功能。
- 任一目标 agent 目录无法确定、包含来源不明改动，或镜像同步可能覆盖非本 Skill 内容。
- 自动验证失败原因不明，独立 Review 存在 P0/P1，或仓库工作区出现任务范围外改动。
- 执行过程中需要 tag、push、GitHub Release、merge、删除目录或其他未授权外部操作。

## Outcome

- Base / Diff：base=63b4f7e99640e1d09a4fb6efcd2f9496cf732582;diff=63b4f7e99640e1d09a4fb6efcd2f9496cf732582..codex/rel-002-v07-release-identity
- 修改文件：`README.md`、`README.en.md`、`skills/ai-dev-flow/VERSION`、`skills/ai-dev-flow/CHANGELOG.md`、`skills/ai-dev-flow/README.md`、`docs/TASK_BOARD.md`、本任务文件
- 验证证据：41/41 单元测试通过；Skill validator 通过；提交后单任务 lint 为 0 error / 0 violation / 0 warning；UTF-8、链接、JSON、敏感信息和 diff hygiene 检查通过
- Review findings：none
- 验证证据：bounded re-review `63b4f7e..511d02e` 通过，P0-P3 均为无，允许同步三个已确认的本机 Skill 副本
- 验证证据：Codex、OpenCode、Gemini/Antigravity 均为 `VERSION=0.7.0`、85/85 文件，逐文件 SHA256 比较 `Missing=0 / Extra=0 / Changed=0`
- 验证证据：三个本机副本均通过 Skill validator；Gemini `plugin.json=0.7.0` 且重复嵌套副本不存在
- 验证证据：同步后完整单元测试 41/41 通过；单任务 lint 为 0 error / 0 violation / 0 warning；`git diff --check` 通过；仓库工作区干净
- UA 动作与结果：UA3 Passed；用户于 2026-07-12 查看版本、Review、测试、lint 和逐文件哈希证据后明确回复“确认”
- UA 动作与结果：用户于 2026-07-12 明确授权将当前任务分支合并到 `main` 并 push；该授权不包含 tag、GitHub Release 或 Closed
