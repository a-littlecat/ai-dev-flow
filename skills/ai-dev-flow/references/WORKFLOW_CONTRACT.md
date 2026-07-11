# Workflow Contract 语义规范

> - Contract schema：`adf/v0.7.0`
> - 规范状态：候选规范，等待独立 Review 与 UA2 冻结
> - 适用范围：`CONTRACT-001`–`CONTRACT-006`
> - 设计来源：`docs/plans/V0.7_WORKFLOW_CONTRACT_RFC.md`

本文是 Workflow Contract 字段、枚举、语法、不变量、兼容读取、诊断码和阶段边界的唯一规范入口。RFC 说明设计理由；`STATUS_MACHINE.md`、`ACCEPTANCE_GUIDE.md` 和 `GIT_WORKFLOW.md` 继续说明人工工作方式。若示例、模板或 Prompt 与本文冲突，Validator 不得猜测，应报告冲突并以本文为语义依据。

## 1. 边界与真相源

- TASK Markdown 是细粒度任务事实源。
- `TASK_BOARD.md` 只是 TASK 的只读投影；不得反向覆盖 TASK。
- JSON Schema 只约束默认值注入前的内存 `CanonicalContractInput`，不是 JSON sidecar，也不得落盘成第二真相源。
- `mode` 是调用上下文，不是持久任务状态，不得写入 Contract。
- lifecycle、Review、UA、acceptance authority、delivery 和 action authority 是正交状态轴。
- lint 只做确定性读取和校验，不执行 Review、验收、merge、release 或状态修复。
- 核心实现必须离线、只读、仅依赖 Python 标准库；不得调用模型、网络或外部平台。

首批唯一 public 语义入口是：

```text
WorkflowContract.inspect(target) -> WorkflowReport
```

`target` 只能是：

1. 单个 `.md` TASK；或
2. 含 `docs/tasks/` 的项目根目录。

项目根扫描只读取 `docs/tasks/*.md`。任意 fixture 分类目录、父目录递归搜索或其他 Markdown 目录都不是 public project target。

概念返回值：

```text
WorkflowReport
├─ contracts[]
├─ diagnostics[]
├─ projections[]
└─ summary
```

Human、JSON 和未来解释 Adapter 必须读取同一个不可变 `WorkflowReport`，不得各自重新判断 pass/fail。

## 2. Reader 选择与受限 Markdown grammar

### 2.1 Reader 选择

选择规则以显式 schema declaration 为 opt-in，不以标题猜版本：

1. 先扫描精确 canonical 行 ``- `schema_version`: `<value>` ``，但此阶段不接受近似 key、缩进或模糊匹配。
2. 文件没有任何精确 schema declaration 时进入 Legacy Reader；即使存在 `## Workflow Contract` 标题，也只把它当普通 legacy 标题，不启用 v0.7 严格规则。
3. 文件存在精确 schema declaration 时，必须恰好有一个精确 `## Workflow Contract` block，且 declaration 必须位于该 block 内并只出现一次；否则输出 `E_PARSE`，不得降级 Legacy。
4. declaration value 为 `adf/v0.7.0` 时进入 v0.7 Reader；未知 schema token 仍视为显式 opt-in，使用严格 block grammar 并输出 `E_UNKNOWN_VALUE`。
5. 大小写或空白不同的近似标题/key 不是 Contract 标题/key，也不是 legacy 别名；不得模糊匹配。

### 2.2 Contract block

Contract block 从精确标题 `## Workflow Contract` 后一行开始，到下一个 ATX 标题或文件结尾结束。空行可以出现在块的开头、结尾和键值行之间；非空行只能使用以下 grammar：

```text
- `key`: `value`
```

规范正则（不启用 locale 或忽略大小写）：

```regex
^- `([a-z][a-z0-9_]*)`: `([^`\r\n]+)`$
```

规则：

- key、枚举和值大小写敏感。
- 行首、行尾不得增加空白；冒号后只能有一个 ASCII 空格。
- 每个 key 只能出现一次；重复 key 为 `E_PARSE`，不采用首值或末值。
- 未知 key 为 `E_PARSE`；扩展只能通过已知的 `extensions_optional` / `extensions_required` 声明。
- 值不得为空、换行或包含反引号。
- 多值使用 `;` 分隔；每个分隔符后不得附加空格。
- `none` 必须单独出现，不得与其他值组合。
- Reader 不依赖字段顺序；Writer 必须使用第 3.1 节顺序。
- 文件编码只接受 UTF-8 或带 UTF-8 BOM 的 UTF-8；不得用本机 locale 猜测其他编码。

## 3. 字段

### 3.1 已知字段和 Writer 顺序

8 个核心字段在每个 v0.7 TASK 中始终存在：

| 顺序 | 字段 | 含义 |
|---|---|---|
| 1 | `schema_version` | Contract 语义版本 |
| 2 | `task_id` | 项目内唯一任务编号 |
| 3 | `task_type` | 交付物性质 |
| 4 | `task_class` | 任务复杂度 A–D |
| 5 | `lifecycle` | 任务生命周期 |
| 6 | `review_status` | 唯一 Review 状态 |
| 7 | `ua_level` | 用户动作等级 |
| 8 | `ua_status` | 用户动作结果 |

条件字段按下列顺序追加，仅在真实条件触发时写入：

| 顺序 | 字段 | 值形状 | 触发条件 |
|---|---|---|---|
| 9 | `ua_evidence` | 单个引用或 `;` 分隔引用 | UA 结果为 Passed / Failed / Deferred |
| 10 | `acceptance_authority` | 枚举 | `ua_status=Passed`、UA7 已得出结果，或 lifecycle 为 Accepted / Closed |
| 11 | `close_authority` | 枚举 | lifecycle 为 Closed，或已明确拒绝关闭 |
| 12 | `commit_status` | 枚举 | Git 项目进入 Review 起 |
| 13 | `merge_status` | 枚举 | 存在合并路径或已经发生 merge |
| 14 | `merge_authority` | 枚举 | `merge_status=Merged`，或已明确授权/拒绝 merge |
| 15 | `overlays` | `none` 或 `;` 分隔引用 | 复杂路径触发；未写时内存默认 `none` |
| 16 | `extensions_optional` | `none` 或 `;` 分隔扩展 id | 声明可忽略扩展 |
| 17 | `extensions_required` | `none` 或 `;` 分隔扩展 id | 声明阻塞型扩展 |

不得为了“字段齐全”提前写一排 `none` / `Not Applicable`。省略 delivery 只能在内存中归一化为 `Not Recorded`，该 token 不得落盘。

### 3.2 枚举

| 字段 | 唯一合法值 |
|---|---|
| `schema_version` | `adf/v0.7.0` |
| `task_type` | `document` / `plan` / `code` / `review` / `repair` / `test` |
| `task_class` | `A` / `B` / `C` / `D` |
| `lifecycle` | `Draft` / `Ready` / `In Progress` / `Blocked` / `Review` / `Needs Fix` / `Accepted` / `Closed` / `Deferred` / `Cancelled` |
| `review_status` | `Pending` / `In Review` / `Passed` / `Needs Fix` / `Do Not Merge` |
| `ua_level` | `UA0`–`UA7` / `TBD` |
| `ua_status` | `Not Required` / `Pending` / `Passed` / `Failed` / `Deferred` / `TBD` |
| `acceptance_authority` | `None` / `User Confirmed` / `Designated Acceptor Confirmed` |
| `close_authority` | `None` / `User Authorized` / `Rule Authorized` / `Denied` |
| `commit_status` | `Not Applicable` / `Uncommitted` / `Committed` |
| `merge_status` | `Not Applicable` / `Unmerged` / `Merged` / `Deferred` |
| `merge_authority` | `None` / `User Authorized` / `Denied` |
| `overlays` | `none` 或 `isolation` / `batch` / `wave` / `real_env_signal` 的唯一引用列表 |

`task_id` 必须匹配 `^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$`。核心不规定 `TASK-` 前缀；文件名必须是 `<task_id>.md` 或 `<task_id>-<slug>.md`。H1 只有在首个 `：` 或 `: ` 前的完整 token 匹配同一正则时才提供 ID provenance，该 token 必须与 `task_id` 一致；没有分隔符的自由标题不参与 ID 推断。

`ua_evidence` 的每个引用必须是仓库相对路径、当前文档 Markdown 锚点或项目约定 evidence id。引用存在不证明记录者身份；无法从当前输入验证时输出 `W_AUTHORITY_UNVERIFIABLE`。

`ua_status=Not Required` 只适用于 `ua_level=UA0`。多值字段不得重复同一 token；JSON Schema 负责值形状，唯一性由语义 Validator 检查。

反向条件同样成立：

- UA0 的 `ua_status` 只能是 Not Required / Pending / TBD。
- Pending / TBD 不得写 `ua_evidence`；`acceptance_authority` 只能省略或显式 `None`。
- Not Required 不得写 `ua_evidence`；lifecycle 未到 Accepted/Closed 时，acceptance authority 只能省略或显式 `None`。
- 非 UA7 的 Failed / Deferred 必须有 evidence，acceptance authority 只能省略或显式 `None`；UA7 的结果必须由 User Confirmed。
- lifecycle 不是 Closed 时，`close_authority` 只允许省略、显式 `None` 或 `Denied`；不得提前写 User/Rule Authorized。
- 多值 token 重复，或 `none` 与其他 token 混用，均为已知字段的非法值 `E_UNKNOWN_VALUE`。

扩展 id 固定为 `<owner>.<name>@<interface-version>`；owner/name 仅用小写字母、数字和连字符，interface-version 为正整数。

## 4. schema_version 与 Skill VERSION

- `schema_version` 描述 Contract 接口；Skill `VERSION` 描述分发包版本，两者独立演进。
- 本规范只接受精确 token `adf/v0.7.0`。`adf/v0.7.1` 在规范和所有 Reader 同步发布前仍为 `E_UNKNOWN_VALUE`。
- “0.7.x 兼容”是演进承诺，不是通配读取：patch 版本只能增加可选字段或澄清规则，且必须先更新规范、Schema、fixture 和 Reader。
- 删除、改名、改变核心字段语义或枚举含义必须升级 Contract minor 版本。
- Legacy 文件没有 `schema_version`；不得自动把其内容改写为 v0.7。

## 5. Normalized View 与 provenance

### 5.1 Reader-level View

成功读取时，Normalized View 至少携带：

- Contract 已归一化字段；
- `title`：TASK 的 H1 标题；
- `source_path`：稳定展示路径；
- `provenance`：每个字段的全部来源；
- `sections`：Validator 所需的精确正文标题和字段索引；
- reader diagnostics。

`title` 和 `source_path` 是投影元数据，不是 Contract block 字段。标题取首个 H1 文本；若开头是精确 `<task_id>：` 或 `<task_id>: `，投影标题移除该前缀并 trim。多个 H1、H1 编号冲突或空标题为 `E_PARSE` / `E_TASK_ID_CONFLICT`。

Normalized View、provenance、diagnostics、report 和 projection 必须深度不可变。Legacy 冲突字段保留所有 provenance，但 normalized 值缺失；不得填 `null` 后假装是确定值。

### 5.2 路径和排序

- 项目 target：路径基准是传入的项目根。
- 单 TASK：若文件位于某个最近的 `docs/tasks/` 下，则基准是该目录的项目根；否则基准是文件父目录。
- `source_path` 使用相对路径和 `/`，不得包含盘符、绝对路径或 `..`。
- Windows 路径比较先把 `\` 转为 `/`，再按 Unicode code point 排序；不得按 locale 排序。
- diagnostics 固定排序键：`(source_path, line_or_0, column_or_0, code, message)`。
- contracts 固定按 `(task_id, source_path)` 排序；projections 固定按 `task_id` 排序。

### 5.3 provenance 记录

每条 provenance 至少包含：

| 字段 | 含义 |
|---|---|
| `source_path` | 上述稳定相对路径 |
| `heading` | 来源 Markdown 标题；无标题时为空 |
| `line` | 1-based 行号；default 为 0 |
| `raw_value` | 文件中的原始值；default 为规范默认 token |
| `source_type` | `canonical` / `legacy` / `default` / `filename` / `heading` / `board` / `git` |

处理顺序固定为：解析 Markdown -> 形成默认值注入前的 `CanonicalContractInput` -> 使用 JSON Schema 校验可表达条件 -> 构造 Normalized View 并注入安全默认 -> 运行正文/Git/board 语义 Validator。

安全默认：省略 `overlays`、`acceptance_authority`、`close_authority`、`merge_authority` 分别归一化为 `none` / `None` / `None` / `None`；必须使用 `source_type=default`、`line=0`。省略 delivery 归一化为内部 `Not Recorded`，同样标记 default。`Not Recorded` 只属于 Normalized View，不是 Schema 或落盘 token。默认值不得覆盖冲突或解析失败。

## 6. 正文语义与条件必填

正文不复制状态，但为状态提供边界和证据。Canonical body 只把顶格、非空的 `- <精确 label>：<value>` 视为机器可校验字段；label 不加反引号，分隔符固定为全角冒号 `：`。未知正文和自由文本可以保留，但不满足门禁。

### 6.1 精确正文骨架

`## 目标与边界` 下识别：

- `目标`：至少 1 条；可重复。
- `非目标`：至少 1 条；可重复。
- `允许修改`：至少 1 条；可重复。
- `禁止修改`：至少 1 条；可重复。

`## 完成标准与验证` 下识别：

- `完成标准`：至少 1 条；可重复。
- `验证命令或检查`：至少 1 条；可重复。

`## Outcome` 下识别：

- `Base / Diff`：单值，grammar 为 `base=<ref>` 或 `base=<ref>;diff=<range>`；ref/range 不得为空、含空白/反引号/分号。`diff=pending` 只允许 Review 前使用。
- `隔离位置`：C/D code/test/repair 单值，值为分支或 Worktree 引用。
- `回滚方式`：C/D code/test/repair 单值。
- `修改文件`：至少 1 条；可重复。
- `验证证据`：至少 1 条；可重复。
- `Review findings`：至少 1 条；可重复；无 finding 时显式写 `none`。
- `UA 动作与结果`：当 UA 结果已产生时至少 1 条；可重复。
- `合并目标与事实证据`：`merge_status=Merged` 时至少 1 条；可重复。

单值字段重复且 trim 后不一致时为 `E_PARSE`；多值字段按文档顺序保存，空值不计入满足条件。相同多值可以作为证据重复保留，但不会产生额外状态。

占位值 `待填写`、`待确认`、`TBD`、`N/A`、`不适用` 不满足任何正文门禁。精确 token `none` 只允许满足 `非目标` 和 `Review findings` 的显式空集合；其他字段写 `none` 仍按缺失处理。

### 6.2 状态条件

“Ready 起”精确定义为 lifecycle 属于 `Ready / In Progress / Blocked / Review / Needs Fix / Accepted / Closed`；“Review 起”精确定义为 `Review / Needs Fix / Accepted / Closed`。

| 条件 | 必须存在的内容 |
|---|---|
| 所有 v0.7 TASK | 8 个核心字段 |
| Ready 起 | 第 6.1 节目标、边界、完成标准和验证的 6 类内容 |
| code/test/repair 且为 In Progress | `Base / Diff` 至少含 `base=<ref>`；C/D 另需 `隔离位置` 与 `回滚方式` |
| code/test/repair 且为 Review 起 | `Base / Diff` 必须同时含 `base=<ref>;diff=<range>`，且 range 不是 pending/TBD；C/D 隔离与回滚信息继续保留 |
| Review 起 | `修改文件`、`验证证据`、`Review findings`；Review 状态只来自 Contract |
| `ua_status=Passed/Failed/Deferred` | `ua_evidence` 可定位，且 Outcome 含 `UA 动作与结果` |
| `ua_status=Passed` 或 lifecycle 为 Accepted/Closed | 非 `None` 的 `acceptance_authority` |
| `Needs Fix` | 非 `none` finding，或第 8 节允许的 feedback scope 与证据 |
| `Closed` | Git 历史可证明曾 Accepted，且 `close_authority` 为 User/Rule Authorized |
| Git 项目进入 Review 起 | `commit_status`；有合并路径时另需 `merge_status` |
| `merge_status=Merged` | `merge_authority=User Authorized` 与 `合并目标与事实证据` |

缺失、空值或冲突正文导致 `V_STATE_GUARD`；更专门的 Review/UA/authority diagnostic 仍按第 13 节触发，避免用通用 code 替代明确原因。

JSON Schema 只表达字段形状和可局部表达的条件。正文存在性、引用可定位性、Git 历史、Diff、merge target 和事实证据必须由语义 Validator 校验，不能因 Schema 通过而跳过。

## 7. lifecycle 与跨轴不变量

### 7.1 合法流转

沿用 `STATUS_MACHINE.md` 的 18 条流转，不新增状态：

```text
Draft -> Ready
Draft -> Deferred
Draft -> Cancelled
Ready -> In Progress
Ready -> Blocked
In Progress -> Review
In Progress -> Blocked
In Progress -> Deferred
Review -> Needs Fix
Review -> Accepted
Review -> Blocked
Needs Fix -> In Progress
Needs Fix -> Review
Accepted -> Closed
Blocked -> Ready
Blocked -> Deferred
Deferred -> Ready
Deferred -> Cancelled
```

### 7.2 不变量

1. TASK 是事实源，TASK_BOARD 只能投影。
2. `review_status=Needs Fix/Do Not Merge` 不得与 Accepted/Closed 并存。
3. Accepted 必须满足适用的 Review、UA 和 acceptance authority 门禁。
4. Closed 必须来自 Accepted，并具有用户或项目规则关闭授权。
5. UA0 只能让 UA 为 Not Required 或提供关闭建议，不能自行产生关闭授权。
6. delivery 只记录事实，不反推 lifecycle。
7. 自动化 GREEN 不等于 Review Passed；Review Passed 不等于 UA Passed；Committed/Merged 不等于 Accepted/Closed。
8. UA4–UA7 失败后，只有分类为 `original_incomplete` / `regression` 且 task scope 为 `current` 才可能进入当前任务修复。
9. 修复前必须同时存在 RED、GREEN 和 SIGNAL；scope expansion、environment、insufficient evidence 不得带入当前任务盲修。
10. 已 Accepted/Closed 后收到失败反馈，默认新建回归 TASK 或等待用户授权，不把原任务直接跳回 Needs Fix。
11. UA7 的 Passed、Failed 或 Deferred 都必须是 `acceptance_authority=User Confirmed`。
12. `merge_status=Merged` 只允许 `merge_authority=User Authorized`；项目规则不能代替本次 merge 授权。
13. Legacy 同一语义字段冲突时不生成确定 normalized 值。
14. 未知 required extension 阻塞；未知 optional extension 只警告并保留原值。

### 7.3 Delivery 触发矩阵

| 条件 | 结果 |
|---|---|
| `commit_status=Committed` 且 lifecycle 为 Review / Needs Fix / Accepted / Closed | 正常；post-commit Review 不构成顺序违规 |
| `commit_status=Committed` 且 lifecycle 为 Draft / Ready / In Progress / Blocked / Deferred / Cancelled | 不单独产生 `V_DELIVERY_ORDER`；commit 可能只是任务记录或准备 baseline，Validator 不猜其业务含义 |
| `merge_status=Unmerged/Deferred/Not Applicable` | 不产生 `V_DELIVERY_ORDER` |
| `merge_status=Merged` 且 lifecycle 不是 Accepted/Closed | `V_DELIVERY_ORDER` |
| `merge_status=Merged` 且 `merge_authority` 不是 User Authorized | `V_DELIVERY_AUTHORITY`；可与顺序违规同时出现 |
| `merge_status=Merged` 且 lifecycle 为 Accepted/Closed、authority 合法 | 顺序与授权通过；仍不反推 Closed |

因此 `V_DELIVERY_ORDER` 首批只判断已经发生的 merge 是否早于 Accepted。commit evidence 缺失、Review 起未记录 commit_status 等问题属于 `V_STATE_GUARD`，不是 delivery order。

## 8. Feedback Gate 的首批可校验边界

`CONTRACT-004` 不实现 Overlay Reader，但仍要校验已有 TASK 正文中的反馈闸门。首批只识别顶格行 `- <精确字段名>：<value>` 或 legacy 的 `- <精确字段名>: <value>`；不得在任意段落做关键词搜索。

`## 用户验收反馈 / 实机测试反馈` 下读取：`反馈分类`、`是否属于当前 TASK 范围`、`复现步骤`、`期望结果`、`实际结果`、`日志 / 截图 / 视频`、`验收失败反馈闸门结论` 和 `下一步建议`。

| 正文语义 | Legacy 精确值 | 归一化值 |
|---|---|---|
| `feedback_class` | `原任务未完成` / `本轮回归` / `新需求或范围扩大` / `环境或配置问题` / `证据不足` | `original_incomplete` / `regression` / `scope_expansion` / `environment` / `insufficient_evidence` |
| `task_scope` | `是` / `否` / `待确认` | `current` / `outside` / `unknown` |
| `repair_intent` | `进入修复任务（repair_task）` / `进入审查-修复循环（review_repair_loop）` | `repair_task` / `review_repair_loop` |

`反馈分类=待确认`、`不适用` 或缺失时不产生确定 `feedback_class`。其他未映射的说明值只保留 provenance；没有 repair intent 时不产生 `E_UNKNOWN_VALUE` 或 scope diagnostic，有 repair intent 时按分类不确定输出 `V_ACCEPTANCE_SCOPE`。`下一步建议` 的其他精确值可以保留，但不构成 repair intent。

`## 实机测试信号复现（real_env_signal）` 下只读取 `RED 失败信号`、`GREEN 通过信号`、`SIGNAL 证据来源`。占位值按第 6.1 节处理。

诊断路由固定如下：

1. `ua_status=Failed` 本身不表示已经进入 repair；没有 repair intent 时只保留失败事实和证据。
2. 出现 repair intent，但 `feedback_class` 不是 `original_incomplete/regression`、`task_scope` 不是 `current`，或任一值不确定时，只输出 `V_ACCEPTANCE_SCOPE`。
3. scope 合法后，RED / GREEN / SIGNAL 任一缺失时输出 `V_SIGNAL_GATE`；不再重复输出 `V_ACCEPTANCE_SCOPE`。
4. lifecycle 已是 Accepted/Closed，却在原 TASK 记录 failure + repair intent 时输出 `V_ACCEPTANCE_SCOPE`，不检查 signal 以避免级联噪声。
5. 显式 `overlays=real_env_signal` 但没有可读正文时：有 repair intent 则按第 2 条输出 `V_ACCEPTANCE_SCOPE`；没有 repair intent 只输出 `V_STATE_GUARD`。

004 可据此产生 core diagnostics，但不得声称已经评估 Overlay。Overlay 自身的稳定字段、Registry 和“是否放宽核心”到 `CONTRACT-007` 才启用。

## 9. Git 历史只读验证

`CONTRACT-004` 的历史检查固定如下：

1. 只在 target 位于可用 Git worktree 且文件已被 HEAD 跟踪时启用。
2. 使用只读 Git 命令读取 HEAD 中当前文件和最近一次修改该路径的父快照；不 checkout、不创建临时文件、不修改 index。
3. 通过 Reader 的 bytes/text 入口解析 blob；不得依赖落盘中间文件。
4. 只在两侧都能确定读取 lifecycle 时判断：值相同表示该次文件修改没有 lifecycle transition，直接通过；值不同时才检查是否属于 18 条合法流转。
5. untracked、dirty、rename 无法追踪、浅克隆、无父快照、Git 不可用或任一侧冲突时输出 `W_TRANSITION_UNVERIFIABLE`，不得猜测 `V_ILLEGAL_TRANSITION`。
6. 当前状态组合即使 Git 不可用仍须执行 core validation。

CLI 和文档调用统一使用 `python -B -X utf8`。入口脚本还必须在导入项目模块前设置 `sys.dont_write_bytecode = True`，避免普通调用产生 `__pycache__`，这是只读承诺的一部分。

## 10. Legacy 精确兼容矩阵

### 10.1 读取原则

- 只识别本节列出的精确标题、表格字段和值；不做相似度、关键词或模型推断。
- 值可去掉一层成对反引号，并 trim 两端空白；不得改写内部文字。
- 同一语义字段的所有来源都要读取。归一化值一致时保留全部 provenance，并输出一次 `W_LEGACY_INFERRED`；冲突时输出 `E_LEGACY_CONFLICT`，该字段不产生确定值。
- 单个 legacy 推断同样输出 `W_LEGACY_INFERRED`，用于明确它不是 canonical 原值。
- 缺失字段保持缺失；不得用 TASK_BOARD 或最后出现的值补齐。

### 10.2 标题与字段别名

| 语义字段 | 精确位置或字段别名 |
|---|---|
| `task_id` | H1 的精确 `<id>：` / `<id>: ` 前缀；`## 任务编号` 的首个标量；`## 任务元数据` 表中的 `任务编号` |
| `title` | 首个 H1；移除已确认一致的 task_id + `：` / `: ` 前缀 |
| `task_type` | `## 任务类型` 首个标量；元数据表 `任务类型` |
| `task_class` | `## 任务分级` 的 `等级`；元数据表 `任务分级` |
| `lifecycle` | `## 任务状态` 首个标量；元数据表 `任务状态` |
| `review_status` | `## 代码审查` / `## Diff 审查` 下的 `审查状态`；自由文本 `审查结论` 只作为 finding/provenance，不参与状态归一化 |
| `ua_level` | `## 用户动作等级 / 验收建议` 下的 `用户动作等级`；元数据表 `用户动作等级` |
| `ua_status` | `## 用户验收反馈 / 实机测试反馈` 下的 `验收反馈状态` |
| `ua_evidence` | `## 用户动作等级 / 验收建议` 下非占位的 `agent 已提供的证据`；或反馈区块中的实际结果/日志证据 |
| `acceptance_authority` | 同区块的精确字段 `验收确认`，或 `验收反馈状态` 中明确包含确认主体的精确短语；`测试人` / `验收人` 只记录操作者，不产生 authority |
| `close_authority` | `## 用户动作等级 / 验收建议` 下的 `是否允许关闭任务` |
| `commit_status` | `## 提交 / 合并` 下的 `Commit 状态` |
| `merge_status` | `## 合并状态` 下的 `合并状态`；`## 提交 / 合并` 下的 `Merge 状态` |
| `merge_authority` | `合并状态=用户已确认待合并`，或精确字段 `合并授权` |

`代码审查` 与 `Diff 审查`、两组合并字段都没有优先级；它们是同一语义轴的多个来源。

### 10.3 值别名

| 字段 | Legacy 精确值 | Canonical 值 |
|---|---|---|
| `task_type` | 文档 / 协议文档 / 模板 / 工作流核心改动 | document |
| `task_type` | 方案 | plan |
| `task_type` | 代码 | code |
| `task_type` | 审查 | review |
| `task_type` | 修复 | repair |
| `task_type` | 测试 / 测试数据 / 单元测试 | test |
| `lifecycle` | 草稿 / 可执行 / 执行中 / 阻塞 / 待审查 / 需修复 / 已验收 / 已关闭 / 延期 / 已取消 | Draft / Ready / In Progress / Blocked / Review / Needs Fix / Accepted / Closed / Deferred / Cancelled |
| `review_status` | 未审查 / 待独立审查 / 审查中 / 通过 / 已通过 / 复审通过 / 需要修改 / 不建议合并 | Pending / Pending / In Review / Passed / Passed / Passed / Needs Fix / Do Not Merge |
| `ua_status` | 无反馈 / 待复测 / 通过 / UA7 已确认通过 / 失败 / UA7 已确认失败 / 延期 / UA7 已确认延期 / 暂缓 / 待确认 / 不适用 | Pending / Pending / Passed / Passed / Failed / Failed / Deferred / Deferred / Deferred / TBD / Not Required |
| `commit_status` | 未提交 / 已提交 / 已提交执行结果 / 不适用 | Uncommitted / Committed / Committed / Not Applicable |
| `merge_status` | 未合并 / 用户已确认待合并 / 已合并 / 暂不合并 / 不适用 | Unmerged / Unmerged / Merged / Deferred / Not Applicable |
| `acceptance_authority` | 用户已确认 / UA7 已确认通过 / UA7 已确认失败 / UA7 已确认延期 / 指定验收人已确认 / 无 / 待确认 | User Confirmed / User Confirmed / User Confirmed / User Confirmed / Designated Acceptor Confirmed / None / None |
| `close_authority` | `是（用户已确认）` / `是（项目规则已授权）` / `否` / `否 / 待用户确认` / `建议关闭` / `待确认` | User Authorized / Rule Authorized / Denied / None / None / None |
| `merge_authority` | 用户已确认待合并 / User Authorized / 否 / 待确认 | User Authorized / User Authorized / Denied / None |

Legacy `task_type` 还接受以下完整 composite aliases；它们在逐 token 冲突检查之前匹配：

| 规范化 composite value | Canonical 值 |
|---|---|
| `方案 / 协议文档 / Schema` | plan |
| `测试数据 / 文档` | test |
| `代码 / 单元测试` | code |
| `代码 / CLI / 单元测试` | code |
| `工作流核心改动 / 模板 / Prompt` | document |
| `代码 / 投影 Adapter / 模板` | code |
| `文档 / 发布治理` | document |

补充 parsing 规则：

- 中文 lifecycle 常写成 `中文（English）` 或 ``中文（`English`）``；去掉 English 外的一层成对反引号后，仅当两侧按上表归一化为同一值时接受，否则 `E_LEGACY_CONFLICT`。
- 除 task_id、lifecycle 和引用外，表中精确枚举别名可以跟一个说明后缀，分隔符只能是 `（`、`:`、`：` 或 `；`；Reader 只在分隔符前完整命中别名时忽略后缀，并保留完整 raw value。lifecycle 必须先执行上一条双语一致性检查，不能走通用后缀忽略规则；不得用 starts-with 匹配其他后缀。
- `task_type` 和 `task_class` 可在值后带 `：` / `:` 说明；只解析分隔符前的精确 token。`任务类型` 先用 literal `/` 分割，并对每个 token 单独 trim 两端空白，完整 raw value 仍保留 provenance。Reader 先把 token 用 ` / ` 重组并查完整 composite alias；未命中时，第一个 token 是 primary type且必须命中简单别名表，后续 token 若命中不同 canonical type 则 `E_LEGACY_CONFLICT`，未知描述 token 忽略，同 canonical token 可保留 provenance。
- `task_class` 只接受开头独立 token A/B/C/D，后接空格、`：` 或 `:`；不得从任意字符串中搜索字母。
- `ua_level` 只接受开头 `UA0`–`UA7` 或精确 `待确认`；后续中文说明不参与值判断。
- Legacy Diff 审查的 `审查状态=不适用` 表示该来源不作状态断言：保留 provenance，但不生成 review_status，也不与其他 Review 来源冲突；若所有来源都为不适用/缺失，则 review_status 保持缺失。其他字段的 `不适用` 仍必须按各自显式别名处理，不得泛化。
- “用户已确认待合并”可以归一化为 `merge_status=Unmerged` 与 `merge_authority=User Authorized`，但仍输出 `W_AUTHORITY_UNVERIFIABLE`。
- 从 legacy 文案得到任何 User/Designated authority 都输出 `W_AUTHORITY_UNVERIFIABLE`；Validator 只能确认记录形状，不能证明说话主体。
- `测试人=用户/agent/其他` 或 `验收人=<名称>` 只进入 sections/provenance，不得生成 `acceptance_authority`，也不得满足 Accepted/Closed 门禁。

### 10.4 Legacy 正文标题映射

Legacy body 只按下表建立 section index；它不把正文状态句重新写入 Contract：

| Canonical 语义 | Legacy 精确标题 / 字段 |
|---|---|
| 目标 | `## 目标` 的非占位 list item |
| 非目标 | `## 非目标` 的非占位 list item |
| 允许修改 | `## 允许修改范围` 的非占位 list item |
| 禁止修改 | `## 禁止修改范围` 的非占位 list item |
| 完成标准 | `## 完成标准` 的 checkbox 或 list item；勾选状态不影响“标准是否已定义” |
| 验证命令或检查 | `## 验证方式` / `## 自动验证命令` 的非空 code fence 或 list item |
| Base / Diff | `## Git 信息` / `## Git 与交接` 下的 `Base commit` / `执行 Base commit` / `Diff 范围` |
| 隔离位置 | `## 执行位置`，或 Git 区块中的 `当前分支` / `Worktree` |
| 回滚方式 | `## 提交 / 合并` / Git 区块中的 `回滚方式` |
| 修改文件 | `## 修改文件` 的有效表格行，或 `## Diff 审查` 下的 `修改文件清单` |
| 验证证据 | `## 验证结果` / `## 执行与验证记录` 的非占位内容，或 `实际验证结果` |
| Review findings | `## 代码审查` / `## Diff 审查` 中 P0–P3、必须修改项、风险和自由文本 `审查结论` |
| UA 动作与结果 | `## 用户动作等级 / 验收建议` 和 `## 用户验收反馈 / 实机测试反馈` 的非占位证据 |
| 合并目标与事实证据 | `## 合并状态` / `## 提交 / 合并` 中的 `合并目标`、实际 merge hash 或等价事实引用 |

第 6.1 节的占位值规则也适用于 Legacy body。Legacy 标题近似词、大小写变化或任意段落关键词不满足门禁。

Legacy `ua_evidence` 的归一化引用固定为：非占位 `agent 已提供的证据` 产生当前文档锚点 `#用户动作等级--验收建议`；反馈区块中非占位的 `实际结果`、`日志 / 截图 / 视频` 或等价 evidence 字段产生 `#用户验收反馈--实机测试反馈`。两处都存在时按文档顺序用 `;` 组合，并保留原字段 provenance；不得把“待执行后填写 / 无反馈”转换为 evidence。

Legacy 额外占位/空集合规则：

- 精确 `目标 1/2/3`、`非目标 1/2/3`、`完成标准 1/2/3`、`原因待填写`、`待执行时填写`、`待执行后填写`、`待审查`、`待复测` 都是模板占位，不构成证据。
- checkbox 是否勾选不影响“完成标准是否已定义”，但 checkbox 文本命中上述占位时仍无效。
- 只含空行和注释 `# 示例：按项目实际情况替换` 的 code fence 不构成验证命令。
- 精确 `无` 在“非目标”和“Review findings / P0–P3 项”中归一化为显式空集合 `none`；在其他正文语义中不构成证据。
- Needs Fix 必须至少有一条非 `none` finding，或满足第 8 节 feedback 路径；`无` 不能让 Needs Fix 通过门禁。

## 11. 扩展与阶段性 Writer 兼容

- `CONTRACT-001`–`CONTRACT-006` 的 core `known_extensions` 集合为空；Overlay id 不是 extension id。
- `extensions_optional` 与 `extensions_required` 归一化为两个集合后必须互斥；同一 id 同时出现时输出唯一 `E_PARSE`，不再为该 id 同时发 optional warning 和 required violation。该交叉集合约束由语义 Validator 检查，不由字符串形状 Schema 猜测。
- 未知 optional extension：保留原值，输出 `W_EXTENSION_OPTIONAL_UNKNOWN`，核心流程继续。
- 未知 required extension：保留原值，输出 `V_EXTENSION_REQUIRED_UNKNOWN`；summary 计为 violation，任务应 Blocked。
- `V_OVERLAY_WEAKENS_CORE` 只有 `CONTRACT-007` 的确定性 Overlay Reader 完成后启用。
- `dual-read, single-write` 的长期含义是：能写 v0.7 的入口不再新建 legacy。
- 首批阶段例外：`CONTRACT-005` 只为新建 A/B、`overlays=none`、非 Batch/Wave/real_env 的任务启用 Compact v0.7；C/D、Batch、Wave、real_env 与现有 legacy TASK 继续使用 Full/Legacy，直到 `CONTRACT-007/008` 提供相应 Writer 路由。
- 已存在 Compact TASK 后续触发尚未实现的 complex path 时必须停止并待确认；可创建新的 Full/Legacy follow-up TASK 或等待 Overlay 支持，不得自动迁移或把旧段落写回 Compact。

## 12. TASK_BOARD projection 契约（CONTRACT-006）

Board compare 只在 project-root target 启用。单 TASK target 不读取看板，`projections` 标记为 `not_evaluated: single_task_target`。004 阶段任何 target 都不读取看板。

Canonical 看板只有 9 个字段：

| 规范 key | Canonical 表头 | expected 值 |
|---|---|---|
| `task_id` | `任务` | Contract task_id |
| `title` | `名称` | 第 5.1 节归一化标题 |
| `task_class` | `等级` | A/B/C/D |
| `lifecycle` | `状态` | lifecycle token |
| `review_status` | `Review` | review_status token |
| `ua_level` | `UA` | ua_level token |
| `acceptance` | `验收` | `<ua_status> / <acceptance_authority>` |
| `delivery` | `交付` | `commit=<status>;merge=<status>;merge_authority=<status>`，未记录 delivery 使用内部 `Not Recorded` |
| `task_path` | `任务文件` | 项目根相对路径，使用 `/` |

Board 格式判别先看完整 header sequence：只有表头与上表 9 列精确相同且没有额外列时才是 Canonical table。其他 table 不推测“残缺 canonical”，统一尝试 Legacy board 解析；Legacy 允许额外展示列，但至少必须能确定 `task_id/title/task_class/lifecycle/task_path`，缺少的 optional projection 字段标记为 `not_projected`，不伪造 drift。

Legacy board 表头只接受以下显式别名（Canonical 表头本身也可作为 legacy partial 列）：

| 规范 key | Legacy 表头别名 |
|---|---|
| `task_id` | `任务编号` / `Task` / `Task ID` |
| `title` | `任务名称` / `标题` |
| `task_class` | `任务等级` |
| `lifecycle` | `任务状态` |
| `review_status` | `Review 状态` / `审查状态` |
| `ua_level` | `UA 等级` / `用户动作等级` |
| `acceptance` | `验收状态`；或 `UA 状态` + 可选 `验收权限` 两列组合 |
| `delivery` | `Delivery`；或 `Commit 状态` + `Merge 状态` + 可选 `Merge 授权` 组合 |
| `task_path` | `路径` / `Task Path`；`备注` 仅在单元格只含一个 TASK 链接时可用 |

Legacy 值解析固定如下：

- `Review` 单元格只取 ` / ` 或 `；` 前的首段：canonical review_status token 直接接受，否则按第 10.3 节 Review 别名映射；额外摘要只保留 provenance。
- `UA` / `UA 等级` 单元格以独立 `UA0`–`UA7` / `TBD` token 开头；可选后缀 `待确认 / 待验收 / 通过 / 已通过 / 失败 / 延期 / 暂缓` 分别给出 Pending / Pending / Passed / Passed / Failed / Deferred / Deferred。仅有 level 时 acceptance 不投影。
- `验收状态` 是 legacy 重载列：值以 UA token 开头时按上一条解析；否则只接受 `未验收 / 待确认 / 通过 / 已通过 / 未通过 / 失败 / 暂缓 / 延期`，归一化为 Pending / Pending / Passed / Passed / Failed / Failed / Deferred / Deferred。它不能自行生成 acceptance authority。
- `验收权限` 只接受第 10.3 节 acceptance authority 别名；缺列时只投影 `<ua_status>`，不补 authority。
- `Commit 状态`、`Merge 状态` 和 `Merge 授权` 分别按第 10.3 节映射后组合为 delivery；缺列的轴为 `not_projected`。
- `任务文件` / `路径` / `Task Path` 接受项目相对路径或单个 Markdown link；link target 先相对 `docs/TASK_BOARD.md` 所在目录解析，再转为项目根相对 `/` 路径。`备注` 只有在单元格精确为 `任务文件：<path-or-link>` 时可用。

Parser 可忽略其他 legacy 展示列，但不得让它们覆盖 9 个投影字段。一个表同时含 canonical 组合列与 legacy 拆分列时，两者必须一致，否则 `V_BOARD_DRIFT`。Legacy partial 只比较实际投影的字段，并输出 `W_LEGACY_INFERRED`；缺失 acceptance/delivery 列本身不是 `E_BOARD_PARSE`。看板内容永远不得补齐 TASK 缺失值。

候选表必须位于唯一一个包含上述 5 个必需语义列且至少有一行数据的 Markdown table；0 个或多个候选都为 `E_BOARD_PARSE`。

Board diagnostics：

- `E_BOARD_PARSE`：候选表无法唯一确定、非 canonical table 又缺少 5 个 legacy 必需语义列、列数损坏或同一语义表头重复。
- `E_TASK_ID_CONFLICT`：看板 task_id 重复，或 board/TASK/file task_id 冲突。
- `V_BOARD_DRIFT`：已配对行的任一字段不同；必须包含字段、expected、actual 和两侧 provenance。
- `W_BOARD_MISSING`：TASK 没有投影行。
- `W_BOARD_ORPHAN`：看板行没有对应 TASK。

如果 TASK 自身解析失败或关键字段冲突，不生成该 TASK 的伪 expected row，也不级联产生 drift。Legacy partial 缺少的 optional 字段不参与 compare；已表示字段的不一致仍产生 `V_BOARD_DRIFT`。

## 13. 诊断模型与阶段

severity 只有：

- `error`：输入结构或确定值无法解析；CLI 退出码 2。
- `violation`：可解析，但违反工作流不变量；CLI 退出码 1。
- `warning`：不阻塞，但报告不得夸大。

当同一报告同时存在多种 severity，退出码优先级为 `error(2) > violation(1) > warning/none(0)`。

| Code | Severity | 首次启用 | 含义 |
|---|---|---|---|
| `E_PARSE` | error | 003 | Markdown/Contract 结构、未知/重复 key、optional/required extension 重叠或编码无法解析 |
| `E_UNKNOWN_VALUE` | error | 003 | 已知字段值不在枚举/别名表 |
| `E_TASK_ID_CONFLICT` | error | 003 单文件；004 project；006 board | file/H1/Contract 冲突；project TASK ID 重复；board ID 重复/冲突 |
| `E_LEGACY_CONFLICT` | error | 003 | Legacy 同一语义轴出现冲突值 |
| `E_BOARD_PARSE` | error | 006 | 看板结构无法确定性解析 |
| `V_STATE_GUARD` | violation | 004 | lifecycle 条件内容或前置门禁缺失 |
| `V_ILLEGAL_TRANSITION` | violation | 004 | Git 历史可证明非法流转 |
| `V_REVIEW_GUARD` | violation | 004 | Accepted/Closed 未满足 Review 门禁 |
| `V_UA_GUARD` | violation | 004 | UA 动作、证据或确认来源不满足 |
| `V_CLOSE_AUTHORITY` | violation | 004 | Closed 缺少/拒绝有效授权，或非 Closed 提前声明 User/Rule Authorized |
| `V_ACCEPTANCE_SCOPE` | violation | 004 | 反馈分类/scope 不允许进入当前任务修复，或 Accepted/Closed 被非法复用 |
| `V_SIGNAL_GATE` | violation | 004 | 验收失败修复缺 RED/GREEN/SIGNAL |
| `V_DELIVERY_ORDER` | violation | 004 | 第 7.3 节定义的 Merged 早于 Accepted |
| `V_DELIVERY_AUTHORITY` | violation | 004 | Merged 缺本次用户授权 |
| `V_EXTENSION_REQUIRED_UNKNOWN` | violation | 004 | required extension 未被当前实现识别 |
| `V_BOARD_DRIFT` | violation | 006 | 看板投影与 TASK 不一致 |
| `V_OVERLAY_WEAKENS_CORE` | violation | 007 | Overlay 放宽核心安全规则 |
| `W_LEGACY_INFERRED` | warning | 003 TASK；006 board | 值来自显式 legacy TASK/board 兼容映射 |
| `W_TRANSITION_UNVERIFIABLE` | warning | 004 | Git 历史不可证明 |
| `W_AUTHORITY_UNVERIFIABLE` | warning | 004 | 记录了 authority，但当前输入不能证明主体 |
| `W_EXTENSION_OPTIONAL_UNKNOWN` | warning | 004 | optional extension 未知，核心继续 |
| `W_BOARD_MISSING` | warning | 006 | TASK 缺看板行 |
| `W_BOARD_ORPHAN` | warning | 006 | 看板行缺 TASK |
| `W_PROJECT_OVERLAY_UNEVALUATED` | warning | 004，007 前 | 发现 `docs/PROJECT_OVERLAY.md`，但未启用确定性 Overlay Reader |

`CONTRACT-002` fixture 可以为未来阶段记录 oracle，但 003/004 不得提前发出 006/007 diagnostics。`WorkflowReport.projections` 在 004 固定为 `not_evaluated`，不能用空集合暗示“没有 drift”。

每条 diagnostic 至少包含：`code`、`severity`、中文 message、可执行 suggestion、source path、line/column 和相关 provenance。Human/JSON Adapter 的 diagnostic 集合、顺序、source 和 provenance 必须完全一致。

## 14. JSON Schema 的责任边界

`../schemas/workflow-contract.schema.json` 校验默认值注入前、可由 Writer 直接渲染的内存 `CanonicalContractInput`，覆盖：

- 8 个核心字段；
- 已知条件字段；
- 枚举、字符串形状和禁止额外属性；
- UA result/evidence、UA7 authority、Accepted/Closed、close authority 和 merged authority 的可表达条件。

Schema 不校验注入了 `Not Recorded` 的 Normalized View，也不覆盖 Markdown grammar、provenance、legacy 冲突、optional/required extension 集合互斥、正文引用、Git 历史、看板、真实用户身份或外部事实。Reader/Validator 失败结果不要求伪装成一个 Schema-valid Contract。Schema 可接受显式安全 token `None`，但 Writer 仍应按第 3.1 节省略未触发的条件字段。

Schema keyword 失败不得一律改写为 parse error；domain diagnostic 映射固定为：

| Schema/语义失败 | Diagnostic |
|---|---|
| 8 个核心字段缺失、额外 property、对象/字符串形状损坏 | `E_PARSE` |
| schema version、枚举、task_id pattern、多值 pattern/唯一性非法 | `E_UNKNOWN_VALUE`；task_id 与文件/H1 不一致另用 `E_TASK_ID_CONFLICT` |
| UA level/status/evidence/acceptance authority 条件失败 | `V_UA_GUARD` |
| Accepted/Closed 与 review_status 条件失败 | `V_REVIEW_GUARD` |
| Closed 缺少/拒绝授权，或非 Closed 提前声明关闭授权 | `V_CLOSE_AUTHORITY` |
| Merged 与 merge_authority 条件失败 | `V_DELIVERY_AUTHORITY` |

同一根因优先输出最专门的 domain diagnostic，不再为同一条件追加通用 `E_PARSE`。

## 15. 强制免责声明

所有 Human/JSON 输出都必须表达同一含义：

> lint 通过只代表 Contract 结构和当前可确定规则通过，不代表 Review、用户验收、merge、release 或任务关闭已经完成。

不得根据 warning 为空、自动化 GREEN、commit 或 merge 事实删除这条声明。
