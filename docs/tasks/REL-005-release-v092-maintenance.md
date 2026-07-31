# REL-005：收口历史治理债务并发布 v0.9.2

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `REL-005`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA7`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/REL-005-release-v092-maintenance.md#rel-005-ua7-2026-08-01`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`
- `close_authority`: `None`

## 目标与边界

- 目标：在不修改 CADCat 仓库或其任务数据的前提下，修复 `ai-dev-flow` 六份旧 Contract 的 19 个全仓 lint error，并准确处置 21 个非终态历史任务；证据完整者 Closed，缺少独立 UA 者 Deferred。
- 目标：把 frontend 开发依赖升级到当前相互兼容的安全版本，使 `npm audit` 与 `npm audit --omit=dev` 均为 0 vulnerability，并保持完整前端回归通过。
- 目标：以已验收页面、空闲性能和 Goal 变更为 canonical source，重建 `skills/ai-dev-flow/dashboard` runtime，发布 `v0.9.2`，同步全部实盘已存在的本机 Skill 入口并形成逐文件 parity 收据。
- 非目标：不修改 `D:\0 个人资料\04 工作\03 爱好\08 CADCat` 或任何其他业务项目；不改变 Workflow/Scheduling/wire schema，不新增产品能力，不创建已不存在的历史 Skill 安装目录。
- 允许修改：`docs/TASK_BOARD.md`、本 TASK；六份 `docs/tasks/CONTRACT-001`～`006`；现场投影为非 Closed 的 21 份既有 TASK；`dashboard/frontend/package.json`、`dashboard/frontend/package-lock.json`、仅为 ESLint 10 兼容所需的 `dashboard/frontend/scripts/generate-types.mjs`；生成器唯一产生的 `skills/ai-dev-flow/dashboard/**`；发布身份文件 `README.md`、`README.en.md`、`dashboard/README.md`、`skills/ai-dev-flow/{VERSION,CHANGELOG.md,README.md}`、版本引用模板/测试；必要的 `dashboard/integration/accepted-artifacts.json` 及其精确断言测试。
- 禁止修改：CADCat 与其他业务仓库、核心 policy/Reader/linter/后端/前端业务源码、公共 schema；禁止 force push、移动旧 tag、改写历史、删除目标专有文件、创建不存在的 Skill 目标或自动执行破坏性依赖修复。

## 依赖与授权

- 前置依赖：`WORKSPACE-CLEANUP-001` Closed；页面/性能/Goal 已分别完成 Review、真实 UA、merge；`main@f5e5e95e09ed6996c4831107ddbb29a00a95f35e` 干净并等于 `origin/main`。
- Base commit：`f5e5e95e09ed6996c4831107ddbb29a00a95f35e`
- 已有 authority：用户于 2026-08-01 在获知完整遗留清单和推荐处理顺序后明确要求“除 CADCat 项目的任务数据等后续由项目会话执行外，完成剩余任务”；据此授权本 TASK 范围内的历史任务核对/关闭、依赖升级、runtime 构建、本机已存在 Skill 同步、commit、push、PR、merge、`v0.9.2` annotated tag、正式 GitHub Release、Closed 与已完全合并分支/Worktree 清理。
- 未授权动作：任何 CADCat 文件写入、部署、强推、旧 tag 移动、历史改写、未知安装目录创建或 scope 外依赖/产品变更。
- 执行位置：`codex/rel-005-v092-maintenance` / `D:\open-source\ai-dev-flow-wt\rel-005-v092-maintenance`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 类；UA7；requested actions=`delivery, merge, release, external sync, irreversible cleanup`；risk flags=`security, shared_component, business_files_gt_3, real_environment, release, external_side_effect`。
- Reviewer 闸门：Required；发布候选 commit/push/PR/merge/tag/Release/同步前必须完成同 Harness 隔离只读 Review，P0/P1 必须为 0。
- 停止条件：需要修改禁止范围、CADCat 文件、公共 schema 或产品业务源码；依赖升级无法消除漏洞且保持完整回归；历史任务缺少可核验的 Review/UA/交付事实；runtime/Skill parity 不一致；Review 有开放 P0/P1；远端或 tag 状态漂移。

## 完成标准与验证

- 完成标准：全仓 Contract 与依赖审计为 0 error，历史任务状态真实，完整回归、runtime parity、独立 Review、本机同步、tag/Release/Closed 全部形成可复现证据。
- 验证命令或检查：workflow lint；frontend audit/codegen/typecheck/lint/unit/build/Playwright；backend/integration/Skill 全量；runtime build/check；Artifact Guard；版本引用、Git、远端 tag/Release、安装目标相对 manifest 与 SHA256 parity。
- [x] 全仓 Workflow Contract lint 为 0 error / 0 violation；每个历史 TASK 的状态与 Git/Release/后继任务证据一致，不把未知状态伪写 Closed。
- [x] frontend `npm audit` 与 `npm audit --omit=dev` 均为 0；codegen、typecheck、lint、unit、build、Playwright 全量通过。
- [x] backend、integration、Skill 全量测试通过；runtime build/check、Artifact Guard candidate consistency 与 `git diff --check` 通过。
- [ ] 实盘安装目标物理路径审计完成；只同步已存在的物理副本，所有入口 VERSION、相对文件和 SHA256 parity 一致。
- [x] 发布候选完成独立只读 Review，P0/P1=0；`main`、annotated tag `v0.9.2`、正式 GitHub Release 和发布收据仍待实际交付后写回。
- [ ] 发布与同步回执合并后，本 TASK Closed；交付分支/Worktree 仅在完全合并且干净后普通删除。
- [ ] `git diff --check` 通过，diff 可归属当前 TASK。

## Repair Chain Ledger（仅进入 repair 时填写）

- Review Round 1：`Needs Fix`，P0/P1/P2/P3=`0/1/2/0`；冻结 staged diff SHA `8fdae06e7a4a23b93ffda8e356c260629dea33c4`。
- `REL005-RVW-P1-001`：把总体收口授权误写成 LEAN-001、LEAN-002、SYNC-001 的独立 UA3 Passed。修复为三项任务和 UA3 均明确 `Deferred`、acceptance authority 与 close authority 不补写；记录后继版本已采用且无剩余执行动作，不伪写验收或 Closed。
- `REL005-RVW-P2-002`：历史 TASK 内仍有“当前 Not Closed”等旧时点措辞。为 27 份处置 TASK 增加顶部唯一当前结论，明确旧状态边界均为历史快照且不改写原 UA 事实。
- `REL005-RVW-P2-003`：开发环境最低 Node 版本过宽。统一文档与 `package.json#engines` 为 Node.js 22.13+，并刷新 lockfile 与 Artifact Guard 候选摘要。
- Review Round 2：`Needs Fix`，P0/P1/P2/P3=`0/0/1/0`；P1-001 与 P2-002 已关闭。P2-003 指出 `>=22.13.0` 会意外放行 ESLint 10.8.0 不支持的 Node 23，进一步收紧为 `^22.13.0 || >=24.0.0`，文档同步写明仅 22.x 或 24+。
- Review Round 3：`Passed`，P0/P1/P2/P3=`0/0/0/0`；三个稳定 finding 全部关闭，冻结 staged diff SHA `afb7b4dfc359574bc8a01a81d30c2be699de625f`，审查前后无 unstaged 或写入。
- Repair 范围未扩大：未修改 CADCat、公共 schema、核心 policy、Reader、linter、后端或前端业务源码。

## Outcome

- Base / Diff：base=f5e5e95e09ed6996c4831107ddbb29a00a95f35e;diff=f5e5e95..working-tree-review-candidate
- 隔离位置：`D:\open-source\ai-dev-flow-wt\rel-005-v092-maintenance` / `codex/rel-005-v092-maintenance`。
- 回滚方式：发布前仅用普通反向 patch/revert；发布后不移动 tag，通过新版本修正；本机同步前创建精确备份并可恢复。
- 修改文件：历史 TASK 与 TASK_BOARD 状态；frontend 开发依赖与 ESLint 10 兼容修复；v0.9.2 发布身份；生成的安装 runtime；Artifact Guard 候选清单与精确测试。
- 验证证据：Workflow lint `0 error / 0 violation`；frontend `npm audit=0`、91/91 unit、89/89 Playwright、build/typecheck/lint/codegen 通过；Python 3.13 下 backend 174/174、integration 51/51、Skill 91/91；runtime `36 files / check ok`；Artifact Guard `baseline_preserved=true / candidate_consistent=true / candidate_mismatches=0 / candidate_index_mismatches=0`；`git diff --check` 通过。
- Review findings：Round 1 `Needs Fix`（`0/1/2/0`）、Round 2 `Needs Fix`（`0/0/1/0`）、Round 3 `Passed`（`0/0/0/0`）；`REL005-RVW-P1-001`、`P2-002`、`P2-003` 全部 Closed。

<a id="rel-005-ua7-2026-08-01"></a>

- UA 动作与结果：页面 UA5、性能/集成 UA6 和 Goal UA2 已分别由用户验收；用户在获知 ai-dev-flow 完整遗留清单、排除 CADCat 数据边界和推荐处理顺序后明确要求“完成剩余任务”，并明确授权提交、合并、v0.9.2 发布、本机 Skill 同步、关闭与清理。记录本发布收口为 `UA7 Passed / User Confirmed`。
- 状态边界：Accepted / Review Passed / UA7 Passed / Uncommitted / Unmerged / Not Released / Not Synced / Not Closed。
- 剩余风险：本机 Skill 尚未备份/同步；`v0.9.2` tag 与 GitHub Release 尚未创建。
- 下一步：提交并通过 PR 合入 `main`，随后执行本机现存 Skill 同步、annotated tag、正式 GitHub Release 和最终 Closed 收据。
