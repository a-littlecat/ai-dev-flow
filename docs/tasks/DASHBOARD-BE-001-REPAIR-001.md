# DASHBOARD-BE-001-REPAIR-001：修复核心快照性能与 dirty ownership 合同

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-BE-001-REPAIR-001`
- `task_type`: `repair`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-BE-001-REPAIR-001.md#dashboard-be-001-repair-001-ua3-2026-07-28`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-BE-001#commit_status=Committed;DASHBOARD-BE-001#lifecycle=Accepted;DASHBOARD-BE-001#merge_status=Merged;DASHBOARD-BE-001#review_status=Passed;DASHBOARD-BE-001#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-BE-002`
- `parent`: `DASHBOARD-BE-001`
- `conflicts_with`: `DASHBOARD-BE-002`
- `parallel_intent`: `serial`
- `write_scope`: `dir:dashboard/backend/src/ai_dev_flow_dashboard/core;dir:dashboard/backend/tests/be001;dir:dashboard/contracts;file:docs/tasks/DASHBOARD-BE-001-REPAIR-001.md;file:docs/TASK_BOARD.md;file:skills/ai-dev-flow/scripts/workflow_contract.py;file:skills/ai-dev-flow/tests/test_workflow_contract_reader.py;file:skills/ai-dev-flow/tests/test_workflow_contract_validation.py;file:skills/ai-dev-flow/tests/test_workflow_lint.py`
- `module_locks`: `dashboard-backend;dashboard-contracts;dashboard-core;dashboard-domain;dashboard-parallel`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-be-001-repair-001`
- `risk_flags`: `architecture;core_execution_path;public_api;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：把 BE-001 冷核心读取性能降到足以支撑 BE-002 `500 TASK / 2000 edges` 完整 cold snapshot `p95 <= 2000 ms` 的水平，不跳过输入冻结、公开 Reader、Scheduling 或 schema validation。
- 目标：为 dirty Worktree 增加可验证的 `owned_by_task / unowned / unknown` 证据，使完全落入唯一任务 `write_scope` 的 dirty paths 可以被并行引擎识别，同时任何越界、共享或不确定 dirty 仍 fail closed。
- 非目标：不修改 BE-002 HTTP/SSE/watcher 实现，不新增依赖，不改变 Review/UA/commit/merge 等状态独立性，不放宽现有性能、安全或 schema oracle。
- 允许修改：`dashboard/backend/src/ai_dev_flow_dashboard/core/**`、`dashboard/backend/tests/be001/**`、`dashboard/contracts/**`、`skills/ai-dev-flow/scripts/workflow_contract.py`、`skills/ai-dev-flow/tests/test_workflow_contract_reader.py`、`skills/ai-dev-flow/tests/test_workflow_contract_validation.py`、`skills/ai-dev-flow/tests/test_workflow_lint.py`、本 TASK 和 TASK_BOARD 对应投影。
- 禁止修改：除精确列出的 Reader 文件外的 `skills/ai-dev-flow/**`、`dashboard/backend/pyproject.toml`、BE-002 HTTP/SSE/watcher 实现、前端、其他 TASK、版本/发布文件和本机 Skill；禁止新增依赖、把 dirty 伪装成 clean、删除测试或降低门禁。

## 依赖与授权

- 前置依赖：`DASHBOARD-BE-001` 已 `Accepted / Review Passed / UA3 Passed / Committed / Merged`；`DASHBOARD-BE-002-BLOCK-001/002` 已在 BE-002 Worktree 稳定记录。
- Base commit：`760b40442bcc96f711f12433a2c5d017d118d85c`
- 已有 authority：用户在收到两个阻塞项、所需修复范围和未授权边界后明确回复“授权”；允许创建本修复 TASK/Worktree，在精确 allowlist 内诊断、实现、验证，并执行隔离只读 Review 和最多两轮有限 AutoRepair，直到 `Review Passed / UA3 Pending`。
- 新增 authority：用户在获知公共 Reader 热点、所需精确文件范围和原权限缺口后明确回复“授权，继续修复然后独立审核直至能验收状态”；允许把 `workflow_contract.py` 及三份定向测试纳入 A1，并在原 BE-001 core/schema/tests 与原 BE-002 已授权实现边界内完成组合验证和独立审核。
- 验收 authority：用户查看组合修复、验证、独立 Review 与尾延迟风险说明后明确回复“验收通过”；允许记录本修复 TASK `UA3 Passed / Accepted`。
- 提交与合并 authority：用户在 Accepted 写回后明确回复“提交并合并”；允许提交本任务实现，并与 `DASHBOARD-BE-002` 组合后合并到本地 `main`。
- 当前未授权动作：新增第三方依赖、越界修改、push、release、外部同步、删除 Worktree/分支或 Closed。
- 执行位置：修复位于 `D:\open-source\ai-dev-flow-wt\dashboard-be-001-repair-001`，BE-002 原授权实现位于 `D:\open-source\ai-dev-flow-wt\dashboard-be-002`；组合验证在临时只读副本执行。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：`task_class=D`；风险包含 `architecture`、`core_execution_path`、`public_api`、`shared_component`、`tests_do_not_cover_oracle`；动作 authority 已明确；验收建议前需要隔离只读 Review。
- Reviewer 闸门：`Required`；实现进入 UA3 建议前必须完成当前 Codex Harness 的隔离、只读 Review，P0/P1 必须关闭。
- 主要风险：为了性能削弱 Windows 文件租约；缓存跨 revision 复用过期输入；ownership 错把越界 dirty 判为 owned；wire schema 与 BE-002 消费者漂移。
- 停止条件：需要新增依赖、放宽门禁、弱化冻结/安全 oracle、无法证明缓存失效、schema 需要破坏性版本迁移、diff 越出 allowlist或出现数据完整性/安全风险。

## 完成标准与验证

- 完成标准：两个 blocker 的冻结 RED 均变为 GREEN，且不削弱输入冻结、strict validator、安全边界或 fail-closed 语义。
- 验证命令或检查：运行 BE-001/BE-002 组合回归、三档 30 样本性能协议、target/project lint、diff scope、`git diff --check` 和隔离只读 Review。
- [x] 建立可复现 profiler/计时反馈环，分离 Windows lease、公开 Reader、Scheduling/graph、Git、watcher 和 serialization；保留修复前 RED 与修复后 30 样本 GREEN。
- [x] `50/200`、`500/2000`、`1000/4000` 三档均可运行；参考机 `500/2000 cold snapshot p95 <= 2000 ms`，连续两次 dataset digest 相同。
- [x] stable save 到 revision 的 30 样本 `p95 <= 1000 ms`；真实原子 rename、watcher idle 和 loopback SSE socket 均计入。
- [x] dirty ownership 覆盖 clean、唯一 owned、越界、共享 scope、未映射、多映射、detached、locked/prunable、rename/copy 双路径、submodule、Unicode/空格和 Windows casefold。
- [x] `owned_by_task` 只在 branch/Worktree 唯一且每个 dirty path 完全落入该 TASK canonical `write_scope` 时成立；其他情况为 `unowned/unknown`，不得产生伪 candidate。
- [x] schema、fixtures、BE-001 和 BE-002 组合测试使用同一 validator 全部通过；公共字段变化有明确兼容与前端影响说明。
- [x] Python 3.12 完整组合回归通过。
- [x] `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-BE-001-REPAIR-001.md --format json` 无 error/violation。
- [x] implementation diff 只命中本 TASK 精确 allowlist，`git diff --check` 通过。

## Repair Chain Ledger

- Repair chain：`repair_chain_id=DASHBOARD-BE-BASELINE-RC-001`；`finding_ids=DASHBOARD-BE-002-BLOCK-001;DASHBOARD-BE-002-BLOCK-002`；closure contract 为本 TASK 完成标准；allowed files 为本 TASK write_scope。
- Trigger evidence：BE-002 真实项目 fresh 构建约 `12521～12621 ms`；冻结 `50/200` cold core `4899.208 ms`；冻结 schema/core 无法表达 dirty ownership。
- Attempt 收据链：`A1` 已形成完整候选并由独立只读 Reviewer 判定 `Needs Fix`；`A2` 为用户授权范围内最后一轮修复。
- History anchor：`attempt_count=2`；`base=760b40442bcc96f711f12433a2c5d017d118d85c`；A1 receipt SHA256 `1CA2DB73FB89E93E4C0A40EC85ECF9FF5DC4A2866DE19DB8B45793D328A272F7`。
- Trusted context：用户当前对话的明确“授权”、当前 Git/Worktree 只读快照和 BE-002 阻塞证据。
- 机械判定：A2 已形成 `Stop / UserDecisionRequired`；用户随后授予任务级 `RepairCampaignAuthority`，当前由 Orchestrator 基于真实对话与冻结输入提升为 `EscalatedRepairAllowed / authority_mode=repair_campaign`，历史 attempt count 仍为 2。

## 诊断结果与授权恢复（2026-07-28）

- 反馈环：冻结 `50 TASK / 200 edges` 数据集，入口固定为 `DashboardCore.inspect()`；同一数据连续三次为 `4741.554 / 4435.693 / 4371.890 ms`，稳定复现超过 2 秒总预算。
- 分段证据：Windows lease enter 为 `112.775～124.812 ms`；暂时只读 monkeypatch 掉公共 Reader 的 per-TASK Git transition 后，总耗时降为 `1020.065～1135.328 ms`。
- 无 transition 的一次精细分解：gateway `598.881 ms`、输入 verify `166.423 ms`、Scheduling `73.928 ms`、Parallel `37.523 ms`、Relationships `2.164 ms`、Actions `0.349 ms`、其他/lease `119.584 ms`。
- 已确认根因：`skills/ai-dev-flow/scripts/workflow_contract.py` 的 `WorkflowContract.inspect(project_root)` 对每个 TASK 串行执行 `rev-parse/status/ls-files/log/show` transition 查询；50 TASK 已产生主要冷启动成本，500 TASK 无法靠 BE-001 core 层局部优化满足 `p95 <= 2000 ms`。
- 排除项：lease API 重复初始化不是主因；Scheduling、关系、动作和并行在 50/200 下均不是主导；同进程重复运行仍为 `4.37～4.74s`，不是一次性 Defender 冷读。
- 原权限缺口：正确修复需要扩展到仓库 `skills/ai-dev-flow/scripts/workflow_contract.py` 及其定向测试，通过批量只读 Git transition 证据消除 per-TASK 进程；该缺口现已由用户新增 authority 精确解除。
- 保守替代：不修改 Reader 时只能保持 BLOCK-001，或放宽性能/跳过 transition oracle；后两者均违反冻结合同，不推荐也未执行。
- 当前处置：恢复为 `In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged`；诊断不计 repair round，首个根因 patch 及其独立 Review 记为 A1。

## A1 实施与验证证据（2026-07-28）

- Reader/Git：把逐 TASK transition 子进程改为批量只读查询，所有 Git 子进程固定 `GIT_OPTIONAL_LOCKS=0`；无历史、dirty、rename/copy、Git unavailable 继续 fail closed。
- 冻结与核心：TASK 与 TASK_BOARD 同时持有 Windows 读租约；并发读取、并发元数据复核、Scheduling/Reader 内容键缓存、关系索引和有界并行评估均保持 manifest SHA256 与 strict schema oracle。
- ownership：新增 `clean / owned_by_task / unowned / unknown`，只有唯一安全 Worktree 且全部 dirty paths 落入 canonical `write_scope` 才允许 `owned_by_task`。
- 组合路径：BE-002 的 Git、snapshot、watcher、HTTP/SSE 使用修复后的 BE-001 core/Reader；相同“源 manifest + Git fingerprint”复用已经 strict-validated 的不可变候选，任一输入变化自动 miss。
- 冷启动：同一 `500 TASK / 2000 edges`、dataset SHA256 `3934d0f774c1caa83ffa75d18c48107379847b8cda5e5645f49018c23b559eb0`，两次连续 5 warm-up + 30 measured 分别为 `p50/p95=1516.2575/1771.5024 ms`、`1439.2227/1595.1023 ms`。
- 稳定保存：真实原子 rename → watcher idle → loopback SSE socket 的 30 样本 `p50/p95=712.3870/784.1541 ms`。
- API/体积：strict schema validation + canonical bytes + ETag + Content-Length 的 30 样本 `p50/p95=149.2886/167.0993 ms`；payload `2687116 bytes`。
- 原始证据 SHA256：cold-r9 `C4601C53A79B836459B5E5AF4761AD0A7E067B2041674DCB61194854C5F7F48C`；cold-r10 `49E86DB579F1FFEC0EAA9861BEE18B8B96A4B8747446D0976B8148F9549B1200`；stable-r2 `603B9604CB85D0CBD50CFE11066BBEC6D133410A2293DD1C44088EFA75DA16DE`；api-r1 `FF967403984346D18F978CE378EB276668D4683191C8B22FCDE2A0FB6B2E1250`。

## A1 独立 Review 与 A2 入口（2026-07-28）

- Reviewer：独立 `codex exec --ephemeral --sandbox read-only`，同时读取 BE-001 repair 与 BE-002 两个未提交 diff；未获写权限。
- Decision：`Needs Fix`；`P0/P1/P2/P3=0/8/1/1`；receipt SHA256 `1CA2DB73FB89E93E4C0A40EC85ECF9FF5DC4A2866DE19DB8B45793D328A272F7`。
- P1 finding IDs：`DASHBOARD-BE-A1-P1-001` 至 `DASHBOARD-BE-A1-P1-008`，分别覆盖 linked Worktree unstaged 探测、watcher 吞事件竞态、canonical scope 缓存失效、schema 缓存 oracle、可变候选、未知 HTTP 方法、v1 wire 兼容和 Reader Git timeout/严格 UTF-8。
- A2 closure：逐项以代码与新测试关闭 8 个 P1，重跑组合回归、Reader/治理回归、lint、diff、性能门禁，再执行第二次独立只读 Review；A2 后不再自动进入新一轮。
- 状态边界：`Needs Fix / A2 In Progress / UA3 Pending / Uncommitted / Unmerged`。

## A2 修复与最终验证候选（2026-07-28）

- `DASHBOARD-BE-A1-P1-001/002`：watcher 增加独立 Git fingerprint 探测并在 refresh 后同时复核 source manifest 与候选 Git fingerprint；真实 linked Worktree `clean → unstaged dirty → clean` 与 refresh 期间二次保存均形成两次 revision/event。
- `DASHBOARD-BE-A1-P1-003/004`：Scheduling 的 canonical prefix/topology cache 以单次 frozen inspection 为 generation；schema 与 candidate cache 均按真实 schema content SHA256 失效，同 size/mtime 的 schema 替换也不能命中旧候选。
- `DASHBOARD-BE-A1-P1-005/006`：候选缓存只保存进程内 strict-validated canonical payload，公开 snapshot/current/wait 返回独立对象；HTTP method 保持冻结行为：已知路由不支持的方法返回 405，未知路由返回 404，均使用严格 JSON、安全 header、无 CORS 响应。
- `DASHBOARD-BE-A1-P1-007/008`：A2 候选尝试让 `dirty_ownership` 仅作为内部证据并为公共 Reader 增加 5 秒 timeout、strict UTF-8 与 `GIT_OPTIONAL_LOCKS=0`；最终独立 Review 判定 P1-008 Closed，但 P1-007 因公共 canonical dataclass 路径仍忽略 `wire=False` 而保持 Open。
- 附加性能修复：Windows frozen lease 直接从已独占只读 HANDLE 读取源字节；wire dataclass shape 按类型缓存并为标量走快速路径；无环关系先用 Kahn 线性证明，只有存在环时才进入 SCC 诊断。没有缩短租约、跳过 schema validation 或放宽安全/性能门禁。
- 最终回归：Python 3.12 组合 dashboard suite `128/128 Passed`；公共 Reader/治理 suite `85/85 Passed`；三档 dataset 可运行且 `500/2000` digest 始终为 `3934d0f774c1caa83ffa75d18c48107379847b8cda5e5645f49018c23b559eb0`。
- 最终性能：cold snapshot 两组 `p50/p95=1653.3866/1826.8364 ms`、`1632.2923/1812.1910 ms`；stable save 两组 `760.0730/894.8890 ms`、`739.0891/907.7692 ms`；API serialize 两组 `149.4765/199.9184 ms`、`139.6867/159.3188 ms`；payload 均为 `2673648 bytes`。
- 原始结果 SHA256：cold `23B9330A9AD47B9B295EEF70A449FE3D02002E2CE6C5DAB03A114DD7A3FBC1B2` / `291B13B3A89DFDDCA9C59ACD61D935C086C5CC9C887DB675D7987FC96E51FCC6`；stable `4A3CEDF4F1D1CB18B5171415319FD9A1586E2135B2DD7D6C805A4974E7E514F4` / `69DA03F67C9D7C9C645021CF058F43216A63657E0AF2358127698D6D28092477`；API `6F7E937950F3077BE904EA8270BE9938158022908E3BE6A4A42B186F9FE8763F` / `9B4C41470DE6D4020B3543E626E2A2779F0BF85CFBD6CB5E9D318603E5AB46D0`。
- 状态边界：A2 实现与自动门禁形成了 Review candidate；最终独立 Review 判定 `Needs Fix / Stop`，不得进入 UA3。

## A2 独立 Review 与 Stop（2026-07-28）

- Reviewer：独立只读子任务同时检查 BE-001 repair 与 BE-002 两个未提交 diff；审核前后输入 manifest 不变，repair 为 `A56621C14F2FA402AEA7E9B0CFD8459BC04B291E2D25DEF30BDA9579C746616E`，BE-002 为 `58C2002EF75AD51FAD5D0C2BEC83F6FFF80CB62E67575B049BC78BC0BF30F593`。
- Decision：`Needs Fix / Stop`；`P0/P1/P2/P3=0/2/2/0`；独立审核回执 `C:\Users\92336\AppData\Local\Temp\dashboard-be-a2-independent-review.final.txt`，SHA256 `BAB89BB40FD80A2C85861FF91982896A8947A80BA663B806A1C0345CE66C35B3`。
- A1 closure：`DASHBOARD-BE-A1-P1-001`～`006` 与 `008` Closed；`DASHBOARD-BE-A1-P1-007` Open。
- P1 `DASHBOARD-BE-A1-P1-007`：`canonical_bytes(dataclass)` 仍遍历全部 dataclass 字段并忽略 `metadata={"wire": False}`，会输出内部 `dirty_ownership`；与 `canonical_bytes(primitive(dataclass))` 不等，冻结 v1 wire 兼容尚未闭合。
- P1 `DASHBOARD-BE-A2-P1-001`：无环图由 Kahn 快速路径保护，但环图仍进入递归 Tarjan；独立 Reviewer 复现 900 节点环通过、1000/1100 节点环触发 `RecursionError`，冻结的 1000 TASK 有效输入不能稳定返回确定性环诊断。
- P2 `DASHBOARD-BE-A2-P2-001`：A2 候选文档曾误写未知方法统一 501，现按冻结实现与测试更正为“已知路由 405、未知路由 404”。
- P2 `DASHBOARD-BE-A2-P2-002`：`_COMPILED_VALIDATORS` 持有无界强引用；加载 32 个不同 schema 后仍保留 32 个 compiled entry，需要有界 content-digest cache 与淘汰测试。
- Review 边界：三次原生 Review 尝试（两次通用执行、一次 `review --uncommitted`）均未形成完整回执，只记为 Review 未完成；上述 Decision 来自随后完成的独立只读审核，不混用失败尝试作为结论。
- Stop：A2 是当前授权链最后一轮自动修复。继续处理必须取得绑定 `repair_chain_id=DASHBOARD-BE-BASELINE-RC-001` 与上述开放 finding IDs 的新 `EscalatedRepair` authority；attempt count 保持 2，不重置历史。

## RepairCampaignAuthority 激活（2026-07-28）

- 用户授权原文：`授权，继续直至可验收为止`；解释为绑定 `DASHBOARD-BE-002`、当前验收合同和外层 write scope 的连续修复授权，不包含 commit、merge、push、release、Accepted 或 Closed。
- Campaign：`campaign_id=DASHBOARD-BE-002-RCAMPAIGN-001`；`profile=core_product`；`acceptance_contract_hash=2fc2863341d8e25b27f81deb372079767d0d073775c84669f6ab5d5f7d439cd8`；`allowed_scope_hash=9d148c410b5bd7a4e58b0a90dc343d14c34bc28fcdf6f8e400ddef9518c0c010`。
- Activation：`repair_chain_digest=2f86621cd9e3f8dac5169ff0ae14e7287d1d9b9f34b175699d03b46de9693441`；`activation_history_head_hash=bab89bb40fd80a2c85861ff91982896a8947a80ba663b806a1c0345ce66c35b3`；A2 后 repair/BE2 输入 manifest 分别为 `7C71BAEEE526F0E4E61CA4C0AB430F79434C24C54DA20C1B0E7F6CAB9BB7EAD8` / `08E0924106B0902CBF7F006BF0702B3FEC8F4EFC94550AA314A0E1A55298ACA9`。
- Authority receipt：`C:\Users\92336\AppData\Local\Temp\dashboard-be-002-repair-campaign-authority.json`；canonical receipt hash `ff64874bc24ac2b1670a68b874721fe3121ee8e95e79f0be7de3a2778b7c9dcb`；file SHA256 `32A6DA14CCDCF1641323129E92D14C2F7146AC0DABDA16DB96860AC4B4A597A3`；receipt/scope hash 已机械复算一致。
- 本次 target finding IDs：`DASHBOARD-BE-A1-P1-007`、`DASHBOARD-BE-A2-P1-001`、`DASHBOARD-BE-A2-P2-002`；`closure_contract_hash=d658bb29bbcd13b8fdf4e92ce1ac65278b42d83e65916a681da08ff0c87c70d9`；`allowed_files_hash=5b0ecf08d2d0cf215509d0c6d5c3a6d0c3efaa2ae4f4305711fb4075903c6107`。
- RED：canonical dataclass 仍输出 `wire=False` 字段；1000/1100 节点环仍递归溢出；compiled validator cache 在 32 个 schema 后仍保留 32 项。GREEN：canonical dataclass 与 `primitive()` bytes 完全一致且可嵌入 v1 schema；depends_on/replaces 的至少 1000 节点环稳定诊断；compiled cache 有界并有淘汰 oracle。SIGNAL：定向测试、完整组合回归、性能双跑、独立只读 Review。
- Activation state：`attempt_count=0`、`consecutive_no_progress=0/4`；所有 hard-stop flags 为 false。ER-1 最终 campaign state 见独立 Review 段。
- 当前状态：`Review / Campaign ER-1 / Review Passed / UA3 Pending / Uncommitted / Unmerged`。

## Campaign ER-1 修复与验证候选（2026-07-28）

- `DASHBOARD-BE-A1-P1-007`：canonical dataclass 路径改为复用 `primitive()` 的 wire-field 选择；`metadata={"wire": False}` 不再被直接 canonical serialization 绕过。回归 oracle 同时证明 `canonical_bytes(dataclass) == canonical_bytes(primitive(dataclass))`、不含 `dirty_ownership`，且嵌入完整 snapshot 后通过冻结 v1 schema。
- 内部语义保持：公开 canonical 过滤 ownership 后，BE-2 `GitCollection.fingerprint` 改为显式包含内部 `dirty_ownership`，而 `watch_fingerprint` 和公开 v1 payload 继续排除该字段；原有差异化 fingerprint 测试由 RED 恢复 GREEN。
- `DASHBOARD-BE-A2-P1-001`：递归 Tarjan 替换为显式栈的迭代 Kosaraju SCC；Kahn DAG 快速路径继续保留。新增 depends_on 与 replaces 两类 1000 节点环 oracle，均返回包含全部节点的稳定 cycle diagnostic，不再依赖 Python recursion limit。
- `DASHBOARD-BE-A2-P2-002`：删除按对象 id 持有 schema 强引用的无界 `_COMPILED_VALIDATORS`；compiled validator 改为 `(schema_digest, schema_content)` 内容寻址的 `lru_cache(maxsize=8)`，32 个不同 schema 后 `currsize=8`。
- RED→GREEN：旧实现上定向测试出现 canonical bytes 不等、两类 1000 节点 `RecursionError` 和缺少有界 compiled cache；修复后相同 `3/3` 通过。
- 完整回归：Python 3.12 组合 dashboard suite `130/130 Passed`；公共 Reader/治理 suite `85/85 Passed`；没有新增第三方依赖。
- 性能双跑：cold p50/p95=`1302.0791/1460.0747 ms`、`1311.3760/1418.6262 ms`；stable-save=`679.3220/775.1131 ms`、`693.6479/840.7838 ms`；API=`122.7819/140.5135 ms`、`119.1122/133.4503 ms`；payload 均为 `2673648 bytes`。
- 性能原始结果 SHA256：cold `D6397A7F67A038083C3953D5B1A5464CB105A30CF477260B25397870703A0651` / `274CA4AAB1576BDAB521AB475FABDEA2C2D502C2F89CDDF90F9799B770B31B78`；stable `D32BEB7E6F094C9F328641848CACA58F3F66B07FDFDC55675FED9F9DEDD33208` / `7FB5ED50CDF8FBA75ADF987EA0694222BD08627195BF7B84AFF770D0BD014DEC`；API `7E2E84E6BF04011A8EF821B7B9A24BD4A639021F8FC401A25663A95D0326B884` / `62BB1285BB9C64C3F6A6F30A52628CDF6981C14940FB6BBB6A8B7F2CE1FE2A80`。
- 样本披露：stable-save run2 有一个 `5187.3041 ms` 最大值；冻结 nearest-rank p95 为第 29 顺位 `840.7838 ms`，原始样本完整保留，未删除或重跑替换。
- ER-1 实际 chain：新增必要的 BE-2 internal fingerprint 文件仍为 campaign outer scope 子集；`allowed_files_hash=e67379512aaf6c1633e7961c97502a5859f3aee16c1eedc9744d522aee3af799`；`repair_chain_digest=27767f31a0b4c5293fba3c143c2c46cb3fa8a9f92ce7379ef43eff8a095ee9d1`。历史 attempt count 不重置。
- Candidate progress：三个冻结 RED 均有直接 GREEN oracle，未发现 GREEN→RED、严重度上升、外部副作用或 hard-stop；Campaign `attempt_count=1`、`consecutive_no_progress=0/4` 的最终写回仍等待独立只读 Review receipt。

## Campaign ER-1 独立 Review（2026-07-28）

- Decision：`Passed`；`P0/P1/P2/P3=0/0/1/0`；允许进入 `UA3` 可验收建议。
- Target closure：`DASHBOARD-BE-A1-P1-007`、`DASHBOARD-BE-A2-P1-001`、`DASHBOARD-BE-A2-P2-002` 全部 Closed；独立 Reviewer 额外验证 1100 节点 DAG、depends_on/replaces 环、compiled cache 命中/淘汰和 Git internal/watch/public ownership 边界，均为 GREEN。
- 唯一新 finding `DASHBOARD-BE-ER1-P2-001`：当前 Outcome 仍写旧回归计数 `128/128`；本次随 Review receipt 更正为 `130/130`。Reviewer 判定为 `record_only_correction`，不消耗新 repair round，也无需再次独立 Review。
- Review receipt：`C:\Users\92336\AppData\Local\Temp\dashboard-be-002-campaign-er1-independent-review.final.txt`；SHA256 `A2BA0E8E2239952F7BE31DB6FBAD4488228E682C8E78E7BCA331FC7EDC972AC2`。
- 输入不可变：审核结束时 repair manifest 仍为 `CFBB10234F273BF8473245C966A17A9B620E8709D544648A162B1644DA4CBF44`，BE2 manifest 仍为 `F05A73E415D0382E595CE42C398E3EB7CE045A1B59B878BAC9A25F3FE24F54E0`；Reviewer 未修改输入，两个 Worktree 均无 `__pycache__`。
- Campaign state：`attempt_count=1`、`meaningful_progress=true`、`consecutive_no_progress=0/4`、hard-stop flags 全 false。
- Review 边界：`Review Passed` 只允许邀请 UA3，不等于 `UA Passed / Accepted / commit / merge / push / release / Closed`。

## DASHBOARD-BE-001-REPAIR-001 UA3 2026-07-28

- 用户反馈：用户在查看 BE-002 与依赖修复的组合验证、独立 Review 和尾延迟风险说明后明确回复“验收通过”。
- 验收范围：确认核心快照性能、dirty ownership、canonical wire、1000+ 节点环诊断、有界 schema cache，以及 BE-002 组合回归和性能证据。
- 验收结果：`UA3 Passed / User Confirmed`；据此将 lifecycle 推进为 `Accepted`。
- 已知风险：用户在验收说明中已获知 stable-save run2 存在一个 `5187.3041 ms` 最大样本；冻结 nearest-rank p95 为 `840.7838 ms` 并通过门禁。
- 权限边界：本次用户反馈只构成 UA3 与 Acceptance authority，不授权 commit、stage、merge、push、release、删除 Worktree/分支或 Closed。

## 提交与合并授权 2026-07-28

- 用户授权：用户在 `UA3 Passed / Accepted` 写回后明确回复“提交并合并”。
- 提交策略：先由独立生命周期提交保存 `In Progress` 与 `Review`，本功能提交保存已审查实现树和 `Accepted / Committed / Unmerged` 状态。
- 合并策略：先把本分支合入 `codex/dashboard-be-002` 形成组合树，复验后再合并到本地 `main`。
- 权限边界：不包含 push、release、外部同步、删除分支/Worktree 或 Closed。

## Outcome

- Base / Diff：base=760b40442bcc96f711f12433a2c5d017d118d85c;diff=working-tree
- 修改文件：`core/**`、`tests/be001/**`、dashboard contract schema、公共 Reader 与定向测试、本 TASK 和 TASK_BOARD；没有新增依赖。
- 验证证据：Python 3.12 组合 dashboard 回归 `130/130 Passed`；Skill/Reader 回归 `85/85 Passed`；六份 Campaign ER-1 30 样本结果的 nearest-rank 与 SHA256 已由 Engineer 和独立 Reviewer 分别复算，2 秒/1 秒/250ms/10MiB 门禁连续双跑 GREEN。
- Review findings：Campaign ER-1 独立 Review `Passed`，`P0/P1/P2/P3=0/0/1/0`；三个目标 finding Closed，唯一 P2 已作为纯记录纠错随 receipt 写回。
- UA 动作与结果：用户明确回复“验收通过”；`UA3 Passed / User Confirmed / Accepted`。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-be-001-repair-001`，branch `codex/dashboard-be-001-repair-001`；组合副本位于本机临时目录。
- 回滚方式：本功能提交及独立分支作为恢复点；未经用户授权不删除、reset、revert 或改写历史。
- 状态边界：`Accepted / Passed / Campaign ER-1 / UA3 Passed / User Confirmed / Committed / Unmerged / Not Pushed / Not Released / Not Closed`。
- 剩余风险：stable-save run2 有一个 `5187.3041 ms` 最大样本；冻结 nearest-rank p95 为 `840.7838 ms` 并通过门禁，但这不代表最大延迟低于 1 秒；该风险已在 UA3 前披露并由用户接受。
- 下一步：按用户授权与 `DASHBOARD-BE-002` 形成组合提交并合并到本地 `main`；push、release 与 Closed 继续保持未授权。
