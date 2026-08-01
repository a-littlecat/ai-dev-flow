# DASHBOARD-FOCUS-ASSESSMENT-001：消除聚焦链与并行评估线的视觉歧义

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-FOCUS-ASSESSMENT-001`
- `task_type`: `repair`
- `task_class`: `B`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`

## 目标与边界

- 目标：聚焦上游或下游时，链外并行评估线同步退居背景，并明确说明它们不代表上下游关系；退出聚焦后恢复选中任务的并行评估证据。
- 非目标：不改变上下游闭包、并行判断、任务框高亮条件、关系方向或后端数据。
- 允许修改：`dashboard/frontend/src/ui/graph/graphView.ts`、`dashboard/frontend/src/styles.css`、`dashboard/frontend/tests/browser/graph.spec.ts`、本 TASK、`docs/TASK_BOARD.md`。
- 禁止修改：后端关系/并行判断、合同与 schema、布局算法、依赖与构建配置、已安装 Skill 和其他既有 TASK 事实。
- 未授权动作：commit、merge、push、release、外部同步、删除、Accepted、Closed。

## 完成标准与验证

- 完成标准：聚焦链外评估线与暗化任务框保持一致的背景层级，图例不再把并行评估误导为上下游，退出聚焦后恢复原显示，自动验证通过。
- [x] 聚焦链外的“并行候选 / 必须串行”线与暗化任务框保持一致的背景层级，聚焦链内评估线仍可见。
- [x] 图例明确说明并行评估线不代表上下游；退出聚焦后恢复原显示。
- [x] 定向浏览器测试和前端完整验证通过。
- [x] `git diff --check` 通过，diff 可归属当前 TASK。
- 验证命令或检查：定向 Playwright 聚焦用例、`npm run verify`、targeted workflow lint、`git diff --check` 和隔离只读 Review。

## Outcome

- Base / Diff：base=7e9ad6418b516ea419ea3ba429de4d260d7a8597;diff=working-tree
- 修改文件：`graphView.ts` 计算并标记聚焦链外评估线并补充解释文字；`styles.css` 将其降至 15% 层级；`graph.spec.ts` 覆盖上游、下游和退出聚焦恢复；本 TASK 与看板记录范围和证据。
- 验证证据：定向 Playwright `1/1` 通过；fresh `npm ci` 后 `npm run verify` exit `0`，codegen/typecheck/ESLint/production build 通过，Vitest `91/91`、Playwright `89/89`。
- Review findings：独立只读 Review session `019fbbe3-49c7-7bc1-acd0-673cb7e123b7` 为 `Passed`，未发现会破坏现有行为或阻碍合并的缺陷，P0/P1/P2/P3=`0/0/0/0`；审查环境 `approval=never / sandbox=read-only`，审查前后工作区文件清单不变。
- Review / UA：Review Passed；UA3 Pending，未以自动测试或 Reviewer 代替用户验收。
- 剩余风险与下一步：源码实现尚未重建或同步到已安装 Skill；commit、merge、push、release、外部同步、Accepted 和 Closed 均未授权。
