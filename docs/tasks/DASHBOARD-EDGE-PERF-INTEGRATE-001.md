# DASHBOARD-EDGE-PERF-INTEGRATE-001：集成页面可读性与空闲性能并重建运行时

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-EDGE-PERF-INTEGRATE-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `#dashboard-edge-perf-integrate-001-ua6-2026-07-31`
- `acceptance_authority`: `Designated Acceptor Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`
- `close_authority`: `None`

## 目标与边界

- 目标：在 `origin/main@8bea393` 的隔离 Worktree 合并已验收的页面修复与性能优化候选，解决 TASK_BOARD 投影冲突，重建安装版 Dashboard runtime，并证明源码、bundle、Skill 与本机同步源一致。
- 目标：保持主工作区 8 个未提交前端文件逐文件 SHA256 不变；不吸收、不覆盖其 diff。
- 非目标：不新增功能、不改变合同 schema、不发布版本、不创建 tag、不部署、不删除未完全合并分支或旧 UnattendedRun Worktree。
- 允许修改：两个已合并候选分支带入的精确文件；`docs/tasks/DASHBOARD-EDGE-PERF-INTEGRATE-001.md`；`docs/TASK_BOARD.md`；`dashboard/integration/accepted-artifacts.json` 的 candidate 区；`dashboard/integration/tests/test_artifact_guard.py` 的组合候选数量与 root digest 断言；生成器唯一产生的 `skills/ai-dev-flow/dashboard/static/index.html`、`skills/ai-dev-flow/dashboard/static/assets/index-BBzm13vu.js` 删除、`skills/ai-dev-flow/dashboard/static/assets/index-7LHWcuMt.js` 新增及 `skills/ai-dev-flow/dashboard/runtime-manifest.json`。
- 禁止修改：其他业务源码、合同、依赖、版本/发布文件、本地主工作区、本机 Skill（验证通过和远端合并前）、Git 历史；禁止 force push、reset、tag、release 或 deploy。

## 依赖与授权

- 前置依赖：`DASHBOARD-EDGE-LABEL-001` Review Passed / UA5 Passed / Accepted / commit `38f5940`；`DASHBOARD-IDLE-PERF-001` Round 11 Review Passed / UA6 Passed / Accepted / commit `2963353`；`GOAL-USAGE-001` 已合并。
- Base commit：`8bea393eafb2c4335f55c07ee1cfe8ae65084ea4`
- 已有 authority：用户于 2026-07-31 明确启动 Auto-Land Goal，授权提交、合并页面与性能候选、重建 runtime、同步本机 Skill、关闭任务并删除完全合并的任务分支。
- 未授权动作：tag、release、deploy、强制推送、历史改写、删除未完全合并分支、删除旧 UnattendedRun Worktree、覆盖主工作区用户改动。
- 执行位置：`D:\open-source\ai-dev-flow-wt\dashboard-edge-perf-integrate-001` / `codex/dashboard-edge-perf-integrate-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 类；requested actions=`delivery, merge, external_sync, close, branch_delete`；risk flags=`core_execution_path, shared_component, real_environment, delivery, external_sync`。
- Reviewer 闸门：Required；runtime 重建和合并后全量验证 GREEN 后，push / PR / merge 前执行当前 Harness 隔离只读 Review。
- 停止条件：生成文件超出冻结集合；页面碰撞或性能门禁回归；runtime/source parity 失败；主工作区指纹变化；需要依赖、schema、release 或历史改写。

## 完成标准与验证

- 完成标准：页面标签碰撞修复、Windows 原生事件与单实例性能候选在同一最新主线快照工作；安装版 static/backend runtime 全部由生成器重建；合并后、本机同步后均通过确定性验证。
- 验证命令或检查：frontend `npm run verify`；backend 174 tests；integration 51 tests；Skill 全套 unittest；runtime build + `--check`；Artifact Guard；`DASHBOARD-EDGE-LABEL-001`、`DASHBOARD-IDLE-PERF-001`、`GOAL-USAGE-001` 与 `DASHBOARD-EDGE-PERF-INTEGRATE-001` 四个 TASK lint；`git diff --check`；主工作区文件 SHA256；独立只读 Review；本机相对路径 + SHA256 parity。
- [x] 两候选原始提交均为集成分支祖先，TASK_BOARD 冲突只做事实合并。
- [x] runtime 生成文件集合与预期完全一致，source/build 后再次 `--check` 通过。
- [x] 合并后 frontend、backend、integration、Skill、Contract lint、Artifact Guard candidate 全部 GREEN。
- [x] 独立只读 Review Passed，无开放 P0/P1/P2。
- [ ] 远端 `main` 包含集成提交；本机物理 Skill 同步并与主线 SHA256 一致。
- [ ] 页面、性能、Goal 与本集成 TASK 写回 Closed；仅删除已确认完全合并的任务分支。

## Outcome

<a id="dashboard-edge-perf-integrate-001-ua6-2026-07-31"></a>
### 组合 UA6（Designated Acceptor，2026-07-31）

- 冻结判据：两个用户已验收候选均保持原提交身份；frontend、backend、integration、Skill、runtime parity、Artifact Guard candidate、四个 TASK lint 与主工作区保护门禁全部通过；独立 Review 无开放 P0/P1/P2。
- 结果：上述判据均由当前环境的确定性验证满足，Round 3 独立 Review Passed，`P0/P1/P2/P3=0/0/0/0`；记录 `UA6 Passed / Designated Acceptor Confirmed`。
- authority 边界：仅确认当前组合候选可提交并进入已授权 PR/merge；不授权 tag、release、deploy、强制推送、历史改写或覆盖主工作区用户改动。

- Base / Diff：base=8bea393eafb2c4335f55c07ee1cfe8ae65084ea4;diff=f3022f498cf46e55f8abca37743f1c769485edfa
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-edge-perf-integrate-001` / `codex/dashboard-edge-perf-integrate-001`。
- 回滚方式：合并前对集成提交使用普通 `git revert`；本机同步前保留时间戳备份；不 reset、不改写历史。
- 修改文件：合并两个候选的原始提交与 TASK 收据；组合 Artifact Guard candidate 从 20 扩展为 27 路径并冻结 digest；runtime 以无 source map 生成，静态 JS 从 `index-BBzm13vu.js` 替换为 `index-7LHWcuMt.js`，同步 `index.html` 与 manifest；新增本集成 TASK 和看板投影。
- 验证证据：frontend codegen/typecheck/lint/build + 84/84 unit + 89/89 browser；backend 174/174；integration 首轮以旧 20-path 断言 RED，更新为 27-path + digest 后 51/51；Skill 91/91；runtime build 与 `--check` 均 `file_count=36, ok=true`；Artifact Guard `baseline_preserved=true / candidate_consistent=true / mismatches=[]`；四个 TASK lint 0 errors / 0 violations；diff checks 通过。
- 主工作区保护收据（2026-07-31）：保护对象为 `dashboard/frontend/src/ui/graph/graphView.ts`、`dashboard/frontend/src/ui/graph/layout.ts`、`dashboard/frontend/src/ui/overlays.ts`、`dashboard/frontend/tests/browser/graph.spec.ts`、`dashboard/frontend/tests/browser/real-scale.spec.ts`、`dashboard/frontend/tests/derive.test.ts`、`dashboard/frontend/tests/parallel-display.test.ts`、`dashboard/frontend/tests/overlays.test.ts`；执行前基线聚合 SHA256=`ECED3A9161E9A076FC5E218CF6B7C4A586E3057375C76AA875E81F5E7E5AABFB`，集成验证后复核聚合 SHA256 相同，结果 `8/8 unchanged`；主工作区仍为 `main@36aae03` 且上述 8 项保持用户未提交状态。
- Review findings：Round 1 `Needs Fix` 的 `P2-001/P2-002/P3-003` 均为记录缺口；修正来源 TASK 陈旧状态、主工作区保护收据和 lint 对象表述后，Round 2 关闭全部 finding；Round 3 对保护路径笔误做最终只读复核，结论 `Review Passed`，`P0/P1/P2/P3=0/0/0/0`。
- UA 动作与结果：页面 UA5 与性能 UA6 已由用户确认；组合 runtime 的冻结生成/parity/全套测试、主工作区保护和独立 Review 判据全部满足，由 Designated Acceptor 记录组合 `UA6 Passed`。
- 状态边界：Accepted / Review Passed / UA6 Passed / Committed `f3022f498cf46e55f8abca37743f1c769485edfa` / Unmerged / Not Synced / Not Closed。
- 剩余风险：生成 bundle 的 hashed asset 名必须以实际构建输出为准；任何偏离冻结集合均停止。
- 下一步：形成集成提交并执行已授权 push / PR / merge；远端合并后同步本机物理 Skill，再写回 Closed 并删除已完全合并分支。
