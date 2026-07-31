# DASHBOARD-EDGE-LABEL-001：修复关系文字被任务卡片遮挡

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-EDGE-LABEL-001`
- `task_type`: `repair`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA5`
- `ua_status`: `Passed`
- `ua_evidence`: `user-message-2026-07-31-interface-fix-accepted`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`
- `close_authority`: `None`

## 目标与边界

- 目标：关系图中所有可见关系文字与任务卡片保持可读间距；“并行未知”证据保留在列表/详情而不绘制成遮挡卡片的 N² 连线；无方向关系的任务使用网格而不是伪造一条竖向关系链；页面明确说明当前任务数量来自项目 `docs/tasks/*.md` 中成功解析的 TASK。
- 非目标：不处理性能任务、后端扫描策略、详情面板重构或其他界面改版。
- 允许修改：仅限以下 9 个文件；不得扩大到其他前端、后端、合同、依赖或 Skill 文件。
  - `docs/tasks/DASHBOARD-EDGE-LABEL-001.md`
  - `docs/TASK_BOARD.md`
  - `dashboard/frontend/src/ui/graph/layout.ts`
  - `dashboard/frontend/src/ui/graph/graphView.ts`
  - `dashboard/frontend/src/ui/toolbar.ts`
  - `dashboard/frontend/tests/browser/responsive-a11y.spec.ts`
  - `dashboard/frontend/tests/browser/graph.spec.ts`
  - `dashboard/frontend/tests/browser/real-scale.spec.ts`
  - `dashboard/frontend/tests/parallel-display.test.ts`
- 禁止修改：其他文件；主仓库现有未提交前端改动；依赖、公共 API、数据格式、后端、Skill runtime；自动提交、合并、推送、发布、删除或记录 `Closed`。

## 依赖与授权

- 前置依赖：`REL-004` 已发布；用户提供 CADCat 实际遮挡截图并于 2026-07-31 明确确认实施修复。
- Base commit：`36aae03e944c3b8b7d5ec52d1417190012d1a6d1`
- 已有 authority：创建独立 Worktree；用户要求继续修复至可交付状态，形成当前 TASK 的 `core_product` 连续修复授权；允许在冻结的九个文件内关闭现有视觉 finding、补充任务数量来源说明、运行自动化验证、启动仅本机可访问的验收页面并执行隔离只读 Review。用户于 2026-07-31 进一步明确启动自动落地目标，授权提交、推送、集成至最新 `main`、重建 runtime、本机 Skill 同步、任务关闭及已完全合并任务分支删除。
- 未授权动作：tag、release、deploy、强制推送、历史改写、删除未完全合并分支或覆盖主工作区用户改动。
- 执行位置：`codex/dashboard-edge-label-001` / `D:\open-source\ai-dev-flow-wt\dashboard-edge-label-001`

## 路由与风险

- 路由：`Controlled`
- Policy 输入：task class D；UA5；risk flags=`real_environment, tests_do_not_cover_oracle, shared_component`；用户已授权修复；需要真实页面观察；现有测试未覆盖关系文字与卡片碰撞。
- Reviewer 闸门：Required；验收建议前必须完成当前 Harness 的隔离只读 Review。
- 停止条件：需要修改允许清单之外文件、放宽碰撞判定、引入依赖、影响公共合同、无法复现用户截图或缺少真实页面证据。

## 完成标准与验证

- 完成标准：冻结视口和真实 CADCat 数据中可见关系标签零碰撞；未知并行证据保留但不绘制 N² 连线；无方向任务及混合图孤立任务不形成误导性长竖链；完整前端验证通过。
- 验证命令或检查：运行定向 Playwright RED→GREEN、`npm run verify`、真实本机页面 DOM/视觉检查、targeted Workflow Contract lint、`git diff --check` 和隔离只读 Review。
- [x] 浏览器回归先证明旧实现存在关系文字与卡片碰撞，再证明修复后所有可见 `.edge-label` / `.assessment-label` 均不与任何 `.node` 或其他关系标签相交。
- [x] `unknown` 并行评估继续出现在证据列表/详情中，但不绘制进关系图；无方向关系任务形成多行多列网格。
- [x] `1440x900`、`1024x768` 和窄窗口场景均通过碰撞断言，并保留浏览器截图。
- [x] 14 任务 / 91 候选关系的高密度场景在标签避碰扩展画布后自动重新适配，全部标签保持在 SVG 可视区内。
- [x] 顶部工具栏明确显示成功解析的 TASK 数量及其 `docs/tasks/*.md` 数据来源。
- [x] 前端 `typecheck`、`lint`、单元测试、构建及浏览器测试通过。
- [x] 在独立本机验收地址复核 CADCat 实际任务图；用户于 2026-07-31 明确确认“界面修复验收通过”，UA5 Passed。
- [x] `git diff --check` 通过，diff 可归属当前 TASK。

## Repair Chain Ledger（仅进入 repair 时填写）

- Repair chain：`repair_chain_id=DASHBOARD-EDGE-LABEL-001-RC1`；`finding_ids=EDGE-LABEL-OCCLUSION-P1-001`；closure contract=标签与卡片包围盒在冻结视口和真实数据中零相交；allowed files=本 TASK 的精确允许清单。
- Trigger Review 收据：Codex 原生 `review --uncommitted` / read-only；Round 1=`Needs Fix`，findings=`EDGE-LABEL-RVW-P2-001, EDGE-LABEL-RVW-P2-002`，receipt SHA256=`AA819A9EDB3FA013C9183CC44B50077CED68574957CBD7CAE72F4AF77D08FED9`；Round 2=`Needs Fix`，finding=`EDGE-LABEL-RVW-P2-003`，receipt SHA256=`A48890DBAB997796BFAB832B8B9665B0E549ACD32E96D38EA9A4FCCCC0879FA9`；Round 3=`Needs Fix`，finding=`EDGE-LABEL-RVW-P2-004`，receipt SHA256=`C172763A76216B95C17B0966C1A431BE3D99F5182A98F9FC56129694260DDEFD`；Round 4=`Needs Fix`，finding=`EDGE-LABEL-RVW-P2-005`（纯记录纠错），receipt SHA256=`50971486BF3F0A4A16E956BECD3EF0F32C7A6FFD436357560B09129AD1E28EDA`；Round 5=`Needs Fix`，finding=`EDGE-LABEL-RVW-P2-006`，receipt SHA256=`7186063B64FB9AA3AEF6F80DED77F80BCC9E30E13290DE763E1FA3981F4B9A37`；Round 6 首次调用因外层 15 分钟超时且 ephemeral 输出不可恢复而无有效收据，进程最终结束且未修改工作区；同 diff 重跑后=`Needs Fix`，findings=`EDGE-LABEL-RVW-P2-007, EDGE-LABEL-RVW-P2-008`，receipt SHA256=`52B05043AED22221759049C10D9CEACC65AD11643A84663475E6F5B1FF68EC99`；Round 7 原生 CLI session=`019fb6e4-946e-7391-89f3-4bec35d52dee` 因用量上限在审查开始前中断，不构成结论；同 diff 由隔离只读 collaboration Reviewer `/root/edge_label_round7_review` 替代审查，结论=`Needs Fix`，finding=`EDGE-LABEL-RVW-P2-009`；Round 8 由同一隔离只读 Reviewer 复审 closure，结论=`Review Passed`，P0/P1/P2/P3=`0/0/0/0`。
- Attempt 收据链：`AR-1` 完成初始 patch；Round 1 Review 给出两个 P2；`AR-2` 增加 checked overflow lane、空快照图例重置及回归测试，Round 2 关闭前两项并发现高度单调性 P2；`AR-3` 将 overflow 高度改为单调增大并增加多自环顺序回归；Round 3 关闭该 P2，但发现混合关系图中的孤立节点仍形成竖列；`ER-1` 将混合图孤立节点改为网格并补 RED→GREEN，Round 4 仅发现 TASK 合同记录 P2；非计数记录纠错通过 targeted lint 后，Round 5 关闭记录 P2 并发现高密度候选按需显示后未重新 fit 的 P2；`CR-1` 在 campaign authority 下增加同快照动态边界变化后的自动适配、14/91 RED→GREEN 回归和任务数量来源说明；Round 6 关闭 P2-006 并发现两个可访问性 P2；`CR-2` 保留动态适配后的键盘焦点、将任务来源 live region 持久化并补充回归；Round 7 关闭 P2-007/P2-008，但发现焦点用例没有证明 rAF refit 真正发生；`CR-3` 将焦点 ID 提前到节点清空前捕获，并让回归先等待 91 标签导致 transform 改变，再检查焦点；Round 8 关闭 P2-009 且无新 finding。
- History anchor：attempt_count=`4`；head receipt=`7186063B64FB9AA3AEF6F80DED77F80BCC9E30E13290DE763E1FA3981F4B9A37`；source=当前用户确认、base commit 与 Round 1～5 Review。
- Trusted context：当前 Harness 已确认 main 的未提交前端改动不属于本 Worktree，且现有测试只检查图例遮挡。
- 第 3 轮 progress：Round 1 两项 P2 已由 AR-2 RED→GREEN；无 P0/P1、无严重度上升；固定覆盖从 84→85→86 browser、82→83 unit；Round 2 新 P2 不阻断 authority 但属于同一视觉 closure contract，目标冻结为 `layout.height` 单调覆盖所有 overflow label。
- Escalated authority：用户于 2026-07-31 回复“确认”，授权一次 chain-bound `EscalatedRepair`，仅处理 `EDGE-LABEL-RVW-P2-004`；不得扩展允许文件、功能目标或 delivery 动作。
- Campaign authority（可选）：用户于 2026-07-31 明确要求“继续修复至可交付状态”，绑定 `task_id=DASHBOARD-EDGE-LABEL-001`、当前九文件精确范围、现有视觉可读性验收合同和 `core_product` profile；允许持续修复并独立复审至 `Review Passed / UA5 Pending`，delivery authority 仍独立。
- Campaign state（可选）：activation head=Round 5 receipt `7186063B64FB9AA3AEF6F80DED77F80BCC9E30E13290DE763E1FA3981F4B9A37`；`CR-1` 关闭 P2-006、progress=true；`CR-2` 将 P2-007/P2-008 的确定性反例转为 GREEN，progress=true；`CR-3` 先以 transform 不变复现 P2-009 RED，再以真实 refit 后焦点保持转 GREEN，progress=true，consecutive_no_progress=0，hard-stop flags=none；Round 8 Review Passed，campaign 已达到 `VerificationGreen+ReviewPassed+AcceptanceReady` 终点。
- 非计数动作：根因诊断、建立 TASK、RED 基线测试、真实页面取证、Round 4 后 TASK/看板记录纠错。
- 机械判定：`RepairCampaignAuthority` 生效；当前 patch 有实质进展且未命中 hard-stop，允许进入独立 Review。
- Orchestrator 提升：当前 Harness 持有用户原始授权、Round 5 head receipt、九文件范围和 RED→GREEN 证据，已将 `CR-1` 提升为 scope-bound campaign repair；不得据此执行 commit、merge、push、release、Accepted 或 `Closed`。

## Outcome

- Base / Diff：base=36aae03e944c3b8b7d5ec52d1417190012d1a6d1;diff=38f5940e1baa6748f63800c2a5640e8ac6242ec7
- 隔离位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\dashboard-edge-label-001`，分支 `codex/dashboard-edge-label-001`；主仓库现有未提交前端改动未被吸收或覆盖。
- 回滚方式：对候选提交 `38f5940` 使用普通 `git revert`；不删除 Worktree、不 reset、不改写历史。
- 修改文件：`graphView.ts` 增加关系标签避碰、按需显示并行评估和动态边界变化后的自动适配；`layout.ts` 增加无方向关系网格；`toolbar.ts` 显示当前 TASK 数量与来源；四个测试文件冻结新显示语义、真实规模和碰撞 oracle；TASK/看板记录状态。
- 验证证据：旧实现 1440x900 RED（“依赖·已满足”与 `TASK-BETA` 相交）；Round 5 高密度场景 RED（14 任务/91 标签中 47 个落出 SVG）；`CR-1` 定向浏览器回归 4/4 GREEN；`CR-2` 可访问性回归先 RED；Round 7 将 transform 变化加入 oracle 后复现焦点测试 RED，`CR-3` 后定向 1/1、重复 5/5 GREEN；最终完整 `npm run verify` 通过：codegen、typecheck、lint、84/84 unit、build、89/89 browser。真实 CADCat 候选页统计为 14 节点、3 列×5 行、0 图内未知标签、91 未知证据列表项、0 标签碰撞、0 标签越界，并显示 `显示 14 个 TASK（来源：docs/tasks/*.md）`。
- Review findings：`EDGE-LABEL-OCCLUSION-P1-001` 自动证据已 GREEN；`EDGE-LABEL-RVW-P2-001/002/003/004/005/006/007/008/009` 均已关闭；Round 8 独立只读 Review Passed，无开放 P0～P3。
- UA 动作与结果：UA5 Passed；用户于 2026-07-31 在本机验收地址 `http://127.0.0.1:35173/` 明确确认“界面修复验收通过”。该确认只授权记录验收结果，不推导 commit、merge、push、release 或 `Closed`。
- 状态边界：Committed / Unmerged / Not Pushed / Not Released / Not Closed。
- 剩余风险：主仓库另有未提交的 Dashboard 界面修改，本任务不吸收、不覆盖。
- 下一步：按已授权 Auto-Land Goal 形成精确提交；随后在独立集成 Worktree 与性能候选串行集成、重建 runtime 并完成合并后验证。
