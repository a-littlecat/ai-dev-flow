# DASHBOARD-PORTABLE-REPAIR-003：关闭提交前版本固定与干净检出缺口

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-PORTABLE-REPAIR-003`
- `task_type`: `repair`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-PORTABLE-001.md#dashboard-portable-001-ua6-复验通过-2026-07-30`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
- `merge_authority`: `User Authorized`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-PORTABLE-001#ua_status=Passed;DASHBOARD-PORTABLE-REPAIR-002#review_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-PORTABLE-001`
- `parent`: `DASHBOARD-PORTABLE-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `file:.gitattributes;file:dashboard/backend/src/ai_dev_flow_dashboard/core/schema_validator.py;file:dashboard/backend/src/ai_dev_flow_dashboard/snapshot/builder.py;file:dashboard/backend/src/ai_dev_flow_dashboard/snapshot/coordinator.py;file:dashboard/backend/tests/be002/test_snapshot.py;file:dashboard/integration/accepted-artifacts.json;file:dashboard/integration/tests/test_artifact_guard.py;dir:skills/ai-dev-flow/dashboard;file:docs/tasks/DASHBOARD-PORTABLE-001.md;file:docs/tasks/DASHBOARD-PORTABLE-REPAIR-003.md;file:docs/TASK_BOARD.md`
- `module_locks`: `dashboard-runtime;dashboard-artifact-integrity`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-portable-001`
- `risk_flags`: `build_or_deploy_config;core_execution_path;historical_p1;shared_component`

## 目标与边界

- 目标：为生成的 `contracts.validators.ts` 固定 LF，确保启用 `core.autocrlf` 的 Windows 干净检出仍通过严格 codegen 校验。
- 目标：Dashboard 运行期间固定启动时的 Contract schema；检测到 Skill schema 改变、损坏或删除后，保留已发布快照并等待重启，不使用更新后的规则继续解析。
- 非目标：不改变用户可见功能、Dashboard wire schema、Workflow/Scheduling schema、治理规则、依赖或安全边界；不重复 UA6。
- 允许修改：仅限本 TASK `write_scope`，其中 Skill Dashboard 运行时仅由既有生成器同步。
- 禁止修改：不得写入真实项目或本机安装 Skill，不得放宽 loopback/CSP/只读 API，不得删除、强制推送、改写历史或 `Closed`。

## 依赖、授权与 Reviewer 收据

- Base commit：`51d4eaa30dfb7a88dc0a7bb035b31beccabab053`。
- 用户已于 2026-07-30 明确完成 UA6 并授权提交、合并、本机同步、push 与正式发版；本修复是上述交付动作前的确定性门禁，不新增用户验收要求。
- 独立只读 Review：session=`019fb25c-9a06-7953-8825-ebb6f80c21b0`，结论 `Needs Fix`，开放 P1=`2`。
- Finding `DASHBOARD-PORTABLE-PREMERGE-P1-001`：生成 validator 缺少 LF 属性，Windows 干净检出可能破坏 codegen 校验。
- Finding `DASHBOARD-PORTABLE-PREMERGE-P1-002`：运行中 Skill 更新后 watcher 仍可能用更新后的 Contract schema 构建快照，违反启动版本固定要求。
- 第一次复审：session=`019fb25c-9a06-7953-8825-ebb6f80c21b0` 的两个 P1 已关闭；复审新增 P2=`DASHBOARD-PORTABLE-PREMERGE-P2-001`，要求 schema 在首次 refresh 前或期间改变时明确中止启动，不能发布混合版本候选。
- 第二次复审：session=`019fb285-8d15-7f10-9232-aed4684de3f1`，P0/P1/P2=`0/0/1`；指出最终摘要检查到发布之间仍有竞态，且 schema 恢复后漂移状态未永久锁存。
- 第三次复审：session=`019fb294-019e-7d82-ae4a-a93fe97902e0`，P0/P1/P2=`0/1/0`；确认内存冻结与永久锁存方向正确，但发现 Builder/Coordinator 启动摘要仍是两次独立读取，且无 payload 回退路径仍读取实时 schema。
- 第四次复审：session=`019fb2a4-154f-7ae1-9a97-e8c9170fa5f2`，P0/P1/P2=`0/1/0`；正式 Builder 路径已共用冻结内容，但注入 Builder 缺少冻结接口时仍存在实时默认 schema 回退与漂移检测绕过。
- 最终复审：session=`019fb2af-da14-7e20-b515-d1de3beb6663`，结论 `Passed`，P0/P1/P2=`0/0/0`；确认同一冻结 schema、payload 回退、漂移永久锁存、注入 Builder fail-closed 与 LF pin 全部关闭。
- 路由：`Controlled`；Reviewer 闸门 `Required`。修复与自动验证后必须重新进行独立只读 Review，无开放 P0/P1 才可提交。

## 完成标准与验证

- 完成标准：关闭两个提交前 P1，且既有多实例、只读、安全、schema 兼容与分发一致性行为不回归。
- 验证命令或检查：定向 coordinator 回归、backend/integration/frontend/Skill 全量、bundle build/check、artifact guard、workflow lint、Git 属性与 `git diff --check`、独立只读 Review。
- [x] `.gitattributes` 对两个生成 TypeScript 文件均固定 `text eol=lf`。
- [x] schema 在启动后变化、损坏或删除时不发布新快照，实例状态仍由现有运行时监视器提示重启。
- [x] schema 在首次 refresh 前或期间改变时明确中止启动，并保持当前快照为空。
- [x] schema 内容在启动时冻结于内存，最终检查后的文件竞态也不能改变候选使用的版本；漂移状态永久锁存至实例重启。
- [x] Coordinator 直接复用 Builder 的冻结摘要，且无 payload 回退也只使用同一份冻结 schema。
- [x] 注入 Builder 缺少 schema API 时由 Coordinator 构造期冻结默认 schema；所有 payload 回退和漂移检测均 fail-closed，不保留实时 schema 后门。
- [x] 定向回归、backend/integration/frontend、Skill、bundle parity、artifact guard、workflow lint 与 `git diff --check` 通过。
- [x] 独立只读 Review 无开放 P0/P1。

## Outcome

- Base / Diff：base=51d4eaa30dfb7a88dc0a7bb035b31beccabab053;diff=current-working-tree-premerge-repair
- 提交事实证据：随父任务形成提交 `47548134ad4168850f919f53a4bf5453dc818bde`。
- 合并目标与事实证据：随父任务通过 merge commit `17ab9be39da028ac08dab8ced267125498db0f56` 合入本地 `main`。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-portable-001` / `codex/dashboard-portable-001`。
- 回滚方式：当前无提交；只逆向应用本 TASK 冻结 scope 的增量，不删除 Worktree、不改写历史。
- 修改文件：为生成 validator 增加 LF 属性；Snapshot Builder/Coordinator 共用启动时冻结 schema，磁盘漂移永久锁存并拒绝实时回退；同步候选 manifest、安装 runtime、回归测试与任务收据。
- 验证证据：backend 144/144、integration 50/50、frontend unit 82/82 + Chrome 83/83、Skill 85/85、bundle build/check 35 files、artifact candidate consistent、Skill quick validate、四个 portable TASK lint 0 error/violation、`git diff --check` 通过。
- Review findings：最终独立只读 Review session=`019fb2af-da14-7e20-b515-d1de3beb6663` 为 `Passed`，P0/P1/P2=`0/0/0`；此前 schema freeze、实时回退与 LF findings 全部关闭。
- 当前状态：`Accepted / Review Passed / UA6 Passed / Committed / Merged / Not Released / Not Closed`。
- UA 动作与结果：用户已经在父任务完成真实双项目验收并明确回复“验收通过”；本 TASK 继承该 `UA6 Passed / User Confirmed` 证据，只提供交付可靠性修复，不要求重复验收。
- 下一步：随父任务提交和本地合并；发布与本机同步由独立发布任务记录。
