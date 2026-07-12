# CONTRACT-003：实现 Legacy / v0.7 只读 Reader

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-003` |
| 任务类型 | 代码 / 单元测试 |
| 当前模式 | 第 2 轮最终独立复审已通过，等待 UA3 证据确认 |
| 下一允许模式 | 用户完成 UA3 后更新为 Accepted；未确认前保持 Review |
| 任务状态 | 待审查（`Review`） |
| 优先级 | 高 |
| 风险等级 | 高 |
| 任务分级 | C：新增双格式 Reader 和不可变 Normalized View |
| 执行位置 | 独立分支，建议 Worktree；顺序执行 |
| 独立代码审查 | 必须 |
| 用户动作等级 | UA3：用户查看测试、只读证明和 diff 证据 |
| 前置任务 | `CONTRACT-002` 达到 `Accepted` |
| Batch / Wave | 禁止；Single Task |

## 背景

v0.7 与 legacy TASK 必须在同一语义层被确定性读取，但旧格式存在中英文标题、重复 Review 和两组合并字段。Reader 必须保守归一化并保留 provenance；遇到冲突时报告，不得选择首值、末值、多数值或模型认为“更合理”的值。

## 目标

- 使用 Python 标准库实现 v0.7 受限 Markdown Reader 和 Legacy Reader。
- 返回不可变的 reader-level Normalized View、provenance 和解析 diagnostics。
- 严格处理 UTF-8、BOM、字段顺序、重复键、未知键和值域。
- 仅依据 `WORKFLOW_CONTRACT.md` 的显式 legacy 别名表读取旧 TASK。
- 为 `CONTRACT-004` 的 validator、`inspect()` facade 和 CLI 提供内部实现。

## 非目标

- 不实现用户可见 CLI、Human/JSON Output Adapter 或退出码。
- 不实现完整跨轴 Validator、Git 历史检查或 TASK_BOARD 对照。
- 不实现 Writer、迁移 preview、自动修复、状态流转或文件重排。
- 不解析 Project Overlay，不调用网络、模型或外部平台。
- 不修改 fixture 或规范来让测试通过。

## 允许修改范围

- 新增 `skills/ai-dev-flow/scripts/_workflow_contract.py`
- 新增 `skills/ai-dev-flow/tests/test_workflow_contract_reader.py`
- 必要的测试包初始化文件
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `skills/ai-dev-flow/tests/fixtures/`
- `skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md`
- `skills/ai-dev-flow/schemas/workflow-contract.schema.json`
- `skills/ai-dev-flow/references/TASK_TEMPLATE.md`
- `skills/ai-dev-flow/references/TASK_BOARD_TEMPLATE.md`
- `skills/ai-dev-flow/SKILL.md` 和 `references/PROMPTS.md`
- 第三方依赖、构建、VERSION、CHANGELOG
- 任何运行时写 TASK、TASK_BOARD 或 Git 的逻辑

## Readiness Gate

- [x] `CONTRACT-002` 已 `Accepted`，reader-level fixtures 和 oracle 已冻结；Accepted commit `f7d870d`。
- [x] `git merge-base --is-ancestor f7d870d f7d870d` 成功。
- [x] `WORKFLOW_CONTRACT.md` 和 schema 无未决字段。
- [x] 当前工作区干净，Base commit、HEAD、执行位置和 Diff 范围已记录。

## 执行步骤

1. 根据冻结 fixture 新建 reader tests；在写生产实现前运行并确认至少一个目标断言失败，不能把“0 tests / 成功退出”当作 RED。
2. 记录可定位的 RED 证据后，实现 v0.7 唯一 Contract block 和严格键值语法解析。
3. 实现规范列出的 legacy 标题/字段映射，不做模糊匹配。
4. 实现不可变 Normalized View、全部来源 provenance 和稳定排序的 reader diagnostics。
5. 增加 hash/mtime、重复读取、字段换序、冲突和编码测试。
6. 运行全部 reader fixtures，形成 GREEN。
7. 独立 Review 后更新本任务，不开始 CLI 或 TASK_BOARD 功能。

## 完成标准

- [x] 仅使用 Python 标准库。
- [x] 接受 UTF-8 和 UTF-8 BOM；不使用本机 locale 猜测其他编码。
- [x] v0.7 Reader 要求唯一 `## Workflow Contract` 和精确 ``- `key`: `value` `` 语法。
- [x] 字段顺序不影响结果；重复键、未知键、错误大小写和非法 schema 得到确定 diagnostic。
- [x] Normalized View 和 provenance 使用不可变结构。
- [x] provenance 至少包含路径、标题、1-based 行号、原始值和来源类型；default 按规范使用 line 0。
- [x] 安全默认值标记 `default` provenance；缺失 delivery 只在内存中为 `Not Recorded`。
- [x] legacy 只识别规范的显式别名，不模糊匹配、不调用模型补全。
- [x] 多个 legacy 值一致时保留全部 provenance 并产生 `W_LEGACY_INFERRED`。
- [x] legacy 冲突产生 `E_LEGACY_CONFLICT`，不产生确定 normalized 值。
- [x] diagnostics 按路径、行号、code 稳定排序。
- [x] Reader 前后 fixture 内容、SHA-256 和 mtime 不变。
- [x] reader-level fixtures 全部通过，重复运行结果一致。
- [x] 生产实现前的测试运行确有目标断言失败；记录测试数和失败数，排除 0-test 假 RED。
- [x] 实现没有写文件、subprocess、socket/network 或 Git 修改路径。
- [x] 独立代码 Review 无 P0/P1。

## 验证方式

```powershell
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_workflow_contract_reader.py" -v
git diff --exit-code HEAD -- skills/ai-dev-flow/tests/fixtures
git diff --check
git diff --name-only
```

测试矩阵至少覆盖：

- v0.7 valid、duplicate key、unknown key/value、错误大小写、非法 schema。
- 字段换序结果等价。
- legacy 单值、一致重复值、Review 冲突、merge 冲突。
- UTF-8、UTF-8 BOM 和不可确定编码。
- fixture 前后 hash/mtime 不变。
- 相同输入重复读取得到完全相同结果。
- import 集合只属于 Python 标准库。

## 停止条件

- fixture 与规范冲突或 expected result 不唯一。
- legacy 映射需要模糊匹配、最后值优先、多数投票或模型推断。
- 必须新增第三方 Markdown/YAML parser。
- 需要修改 fixture、schema 或规范才能让实现通过。
- 实现必须写文件、修改 Git、联网或调用外部模型。
- 范围扩展到 validator、CLI、TASK_BOARD、Overlay、Writer 或迁移。

## 执行与验证记录

- RED：先出现一次缺少生产模块的 0-test error，该次不计有效 RED；随后加入最小不可用 stub，运行 4 个测试产生 8 个目标 assertion failure，确认非假 RED。
- GREEN：`python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_workflow_contract_reader.py" -v` 通过，8 tests / 0 failures / 0 errors。
- 新增 `_workflow_contract.py`：strict v0.7 reader、显式 Legacy reader、深度不可变 report/provenance/sections/diagnostics、稳定相对 source path、安全默认和严格 UTF-8。
- 新增 `test_workflow_contract_reader.py`：覆盖 golden oracle、重复/未知/大小写/schema、BOM/坏编码、字段换序、Legacy 一致/冲突、全 fixture hash/mtime、重复读取、只读 surface 与标准库 import。
- fixture 只读证明：`git diff --exit-code HEAD -- skills/ai-dev-flow/tests/fixtures` 通过。
- import/写入面静态检查：生产模块 import 仅 `dataclasses/pathlib/re/typing`，不含 write、subprocess、socket、requests 或 urlopen。
- 未实现 Validator、CLI、Git 历史、TASK_BOARD、Overlay 或 Writer。

## 代码审查

- 审查状态：最终复审通过
- 审查人或审查 agent：Codex 独立 Reviewer（2 轮修复后最终复审）
- 审查严重等级：无 P0/P1；1 项 P2 不阻塞
- P0 / P1 必须修改项：
  1. Legacy scalar 来源、完整别名、token 冲突和 lifecycle 双语一致性未实现完整。
  2. Canonical block 错误忽略 HTML comment；schema declaration 全文件唯一性/归属不完整。
  3. Diagnostic 缺 severity/suggestion/column/provenance，且按 code 全局去重会吞掉独立根因。
  4. acceptance authority 推断过宽，`待确认` 不得产生确认权限。
  5. filename/H1/Contract/Legacy task_id provenance 与冲突检查不完整。
  6. canonical/legacy sections 未按正文精确 grammar 和 10.4 映射。
  7. provenance source_type、真实行号、raw value 不符合规范；ua_evidence raw 被 anchor 覆盖。
  8. 当前测试未覆盖上述完成标准。
- 审查结论：通过；允许进入 UA3
- 是否允许进入验收建议：是（UA3）

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：最终复审通过
- 审查结论：范围无越界，无 P0/P1；保留 1 项 P2

## 审查-修复循环（review_repair_loop）记录

- 当前轮次：1 / 2。
- 修复范围：仅 `_workflow_contract.py`、Reader tests、当前 TASK 与 TASK_BOARD。
- 禁止扩大：fixture、规范、Schema、Validator、CLI、Git history、board、Overlay、Writer。
- 修复目标：关闭第 1 轮 Review 的全部 P1，并新增逐规则回归测试。
- 第 1 轮修复结果：
  1. 补齐 Legacy scalar 来源、完整 composite alias/token 冲突、lifecycle 双语一致性和 UA/authority/evidence 精确来源。
  2. Canonical block 不再忽略 comment/free text；schema declaration 全文件扫描并验证唯一性与 block 归属。
  3. Diagnostic 增加 severity、suggestion、column、related provenance，按完整 identity 去重和五元排序。
  4. `待确认` 不再推导 acceptance authority；只允许规范的明确确认短语。
  5. 增加真实相对 source path 与真实 TASK filename provenance/conflict；fixture 容器文件名不冒充 TASK 文件名。
  6. canonical sections 只接受精确全角字段；Legacy sections 映射目标/范围/完成标准/验证/Outcome 证据。
  7. provenance source_type 收口为规范枚举，H1 使用真实行号，ua_evidence 保留原文并单独生成 normalized anchor。
  8. 测试扩展为 12 tests，覆盖上述全部回归点和 alias matrix。
- 第 1 轮修复验证：12/12 GREEN；py_compile 通过；fixture diff 为空；`git diff --check` 通过。
- 未处理意见：无。
- 下一步：提交修复候选并独立复审。

### 第 1 轮复审结果

- 通过证据：12/12 tests GREEN、fixture diff 空、完整 diff check 通过。
- 未关闭 P1：Legacy 枚举说明后缀/异常 lifecycle 双语；Legacy fenced command/table/placeholder section index；硬编码 `/tests/fixtures/` filename 例外。
- P2：部分 diagnostic 的 related provenance 与 suggestion 仍偏弱。
- 结论：Needs Fix，不允许 UA3；进入第 2 轮（上限）修复。

### 第 2 轮修复结果

- Legacy enum 统一支持规范允许的 `（` / `:` / `：` / `；` 说明后缀；lifecycle 单独要求完整闭合双语且值一致，authority 未知值产生 `E_UNKNOWN_VALUE`。
- `SectionField` 增加 `kind`，Legacy index 可区分 field/list/checkbox/code_fence/table_row；fenced verification command 被保留，表头/分隔行不冒充修改文件，placeholder 原文保留供 Validator 判定。
- 删除生产代码对 `/tests/fixtures/` 的路径猜测；`inspect_task(..., validate_filename=False)` 作为显式 fixture-container context，默认真实 TASK 仍严格校验文件名。
- Diagnostic 按 code 提供可执行 suggestion；已解析枚举和 Legacy conflict 关联 provenance。
- 测试扩展到 14 tests，覆盖 suffix 正反例、fence/table/placeholder、显式 filename context。
- 第 2 轮验证：14/14 GREEN；fixture diff 空；标准库 import/只读 surface 检查继续通过。
- 当前轮次达到 2 / 2；提交后必须最终独立复审，仍有 P0/P1 则停止。

### 第 2 轮最终复审结果

- 结论：通过；无 P0/P1，允许进入 UA3。
- 14/14 tests GREEN；fixture Base→HEAD diff 空；完整 diff check 通过；只读 surface 无 write/subprocess/socket/network。
- 原 3 项 P1 全部关闭。
- 保留 P2：部分可关联来源的 diagnostic 尚未附带 related provenance；不影响 diagnostic code/位置/排序或 Reader 正确性，建议 CONTRACT-004 facade 接入时补齐。
- 已达到 2 轮修复上限，但因无 P0/P1，不触发人工接管。

## 用户动作等级 / 验收建议

- 用户动作等级：UA3
- 用户需要做什么：查看测试、只读证明和独立审查证据
- agent 已提供的证据：14/14 Reader tests、RED 4 tests/8 failures、fixture hash/mtime 与 Base→HEAD diff、只读 surface、两轮独立 Review
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA3
- 反馈分类：不适用
- 下一步建议：等待用户完成 UA3；未确认前保持 Review，不启动 `CONTRACT-004`

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现 `0e1d746`、首审记录 `6922cd9`、第 1 轮修复 `013cae2`、复审记录 `806b08c`；第 2 轮修复候选待提交
- Commit hash：待提交后填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/contract-003-readonly-readers`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：`f7d870d`
- 计划分支：`codex/contract-003-readonly-readers`
- Diff 范围：`f7d870d..HEAD`（执行中）
- 下一任务：`CONTRACT-004`，仅在本任务 `Accepted` 后转为 `Ready`
- 不要重复尝试：通过修改 fixture expected 结果掩盖 Reader 缺陷
