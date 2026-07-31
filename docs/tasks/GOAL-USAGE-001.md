# GOAL-USAGE-001：增加 Codex Goal 自动落地预设与中文触发词

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `GOAL-USAGE-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：把 Codex 原生 Goal 定义为持续执行容器，增加 `governed_goal`、`auto_land`、`auto_release` 三个治理预设；用户可用自然中文明确触发，其中 `auto_land` 在冻结范围内自动推进实现、验证、独立 Review、修复、commit、merge、push、PR 与 CI。
- 目标：机器可确定且在当前环境可执行的验收可预先指定 Codex 为 Designated Acceptor；只有真实人工判断不可替代时才停在 UA。
- 目标：不复制 Goal 的预算、恢复、Active/Complete/Blocked 状态，不增加 `UnattendedRunAuthority`、新 policy 版本或第二套运行状态机。
- 非目标：不实现 Goal API、不自动创建未被用户明确要求的 Goal；不把中文子串机械识别成无限授权；不默认授权 tag、release、deploy、删除、数据迁移、密钥/权限修改或 `Closed`。
- 允许修改：`docs/tasks/GOAL-USAGE-001.md`、`docs/TASK_BOARD.md`、`skills/ai-dev-flow/SKILL.md`、`skills/ai-dev-flow/README.md`、`skills/ai-dev-flow/CHANGELOG.md`、`skills/ai-dev-flow/references/CODEX_GOAL_USAGE.md`、`skills/ai-dev-flow/tests/test_codex_goal_usage.py`。
- 禁止修改：`skills/ai-dev-flow/references/CORE.md`、`repair_gate.py`、Workflow Contract schema、TASK 模板、Dashboard、依赖、本机 Skill 副本、旧 `unattended-run-001` Worktree 内容；禁止删除 Worktree、tag、release、deploy、强制推送、改写历史或 `Closed`。

## 依赖与授权

- 前置依赖：`REPAIR-CAMPAIGN-001` 已发布；Codex Harness 原生 Goal 能力由平台提供，不成为 Skill 的内部实现。
- Base commit：`36aae03e944c3b8b7d5ec52d1417190012d1a6d1`
- 已有 authority：用户于 2026-07-31 确认采用更自动的 `Auto-Land Goal`，允许自动 commit、merge、push、PR/CI，并要求增加中文触发词；授权在本任务精确范围内实现、验证、独立 Review，并在所有门禁 GREEN 后形成 commit、推送任务分支及按安全条件执行可归属的集成动作。
- 未授权动作：tag、release、deploy、删除、数据迁移、密钥/认证/授权修改、本机 Skill 同步、旧 Worktree 删除、强制推送、历史改写、`Closed`。
- 执行位置：`D:\open-source\ai-dev-flow-wt\goal-usage-001` / `codex/goal-usage-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 类；共享 Skill 入口与交付权限语义；risk flags=`core_execution_path, shared_component, delivery, explicit_independent_review`；中文触发与授权边界可确定性验证，最终文案需 UA2。
- Reviewer 闸门：Required；commit / push / merge 前必须完成同 Harness 隔离只读 Review。
- 停止条件：需要修改 CORE policy、repair gate、Contract schema 或依赖；中文触发可绕过显式 Goal 请求；`auto_land` 隐式包含 release/deploy/delete；机器验收替代真实不可复现人工证据；目标分支存在来源不明的重叠改动。

## 完成标准与验证

- 完成标准：原生 Goal 与 Skill 零状态组合；三种预设含中文触发、分级 authority、自动验收边界和 hard stop；不改变 CORE policy、repair gate 或 Contract schema。
- 验证命令或检查：定向与全套 unittest、Skill quick validator、Workflow Contract lint、默认运行时 400 行预算、`git diff --check` 和独立只读 Review。
- [x] `SKILL.md` 明确 Goal 是执行容器、TASK 是项目事实源、Skill 是治理层；不复制 Goal 状态。
- [x] 中文触发词覆盖受控目标、自动落地和自动发布；英文别名继续可用，模糊表达不会自动扩权。
- [x] `auto_land` 自动范围与 hard stop 清晰；`auto_release` 只有明确版本/环境才生效。
- [x] 可机器验证验收与真实人工验收边界清晰，Goal Complete 不等于 UA、merge、release 或 Closed。
- [x] 旧 `UNATTENDED-RUN-001` 候选被本任务替代但不删除其 Worktree；本任务不吸收其约 695 行自定义状态机 diff。
- [x] 定向规则测试、Skill 全套 unittest、Workflow Contract lint 和 `git diff --check` 通过。
- [x] 独立只读 Review Passed，无开放 P0/P1。

## Outcome

- Base / Diff：base=36aae03e944c3b8b7d5ec52d1417190012d1a6d1;diff=f2056794a3fa09c47067fd4cdb4fa734564c1829
- 隔离位置：`D:\open-source\ai-dev-flow-wt\goal-usage-001` / `codex/goal-usage-001`。
- 回滚方式：对任务提交 `f205679` 使用普通 `git revert`；不删除 Worktree、不 reset、不改写历史。
- 修改文件：`SKILL.md` 增加零成本按需入口；`CODEX_GOAL_USAGE.md` 定义三种预设、中文词表、authority、自动验收与 hard stop；README/CHANGELOG 对外说明；定向测试冻结零状态与权限边界；TASK/看板记录事实。
- 验证证据：初始及 AR-1 后定向 Goal 规则均为 `6/6`、Skill 全套 unittest 均为 `91/91`；Skill quick validator `Skill is valid!`、默认运行时预算断言 `<=400`、Workflow Contract lint `0 errors / 0 violations / 1 transition-provenance warning`、`git diff --check` 通过；七个变更文件与精确允许清单一致。
- Review findings：Round 1=`Needs Fix`，`GOAL-USAGE-RVW-P2-001` 指出 `auto_release` 与生产外部副作用硬停止冲突；`GOAL-USAGE-RVW-P2-002` 指出定向测试未冻结完整意图、安全排除、Designated Acceptor 和不完整发布信息边界。AR-1 限定显式发布 authority 的外部副作用边界并补充确定性断言；Round 2 独立只读 Review Passed，两个 P2 均 Closed，新增 P0/P1/P2/P3=`0/0/0/0`。
- UA 动作与结果：UA2 Pending；用户需确认中文触发词和自动落地权限上限是否符合预期。
- 交付证据：功能提交 `f205679` 已推送至 `origin/codex/goal-usage-001`；Draft PR=`https://github.com/a-littlecat/ai-dev-flow/pull/2`，GitHub 当前未报告 CI checks。
- 状态边界：Committed / Unmerged / Pushed / Draft PR / No CI Checks Reported / Not Released / Not Synced / Not Closed。
- 剩余风险：Goal 是 Codex 平台能力；其他 Harness 不得伪装或模拟同名能力。
- 下一步：等待 UA2 确认中文触发词与自动落地权限上限；通过后将 PR 转为 Ready 并按可用门禁继续集成。目标 `main` 有用户未提交前端改动，不执行本地 merge，并保持旧 Worktree 不删除。
