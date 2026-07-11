# CONTRACT-003：实现 Legacy / v0.7 只读 Reader

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-003` |
| 任务类型 | 代码 / 单元测试 |
| 当前模式 | 创建任务（`create_task`） |
| 下一允许模式 | 前置门禁满足后进入 `execute_task` |
| 任务状态 | 草稿（`Draft`） |
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

- [ ] `CONTRACT-002` 已 `Accepted`，reader-level fixtures 和 oracle 已冻结。
- [ ] `git merge-base --is-ancestor <CONTRACT-002 Accepted commit> <当前 Base>` 成功。
- [ ] `WORKFLOW_CONTRACT.md` 和 schema 无未决字段。
- [ ] 当前工作区干净，Base commit、HEAD、执行位置和 Diff 范围已记录。

## 执行步骤

1. 根据冻结 fixture 新建 reader tests；在写生产实现前运行并确认至少一个目标断言失败，不能把“0 tests / 成功退出”当作 RED。
2. 记录可定位的 RED 证据后，实现 v0.7 唯一 Contract block 和严格键值语法解析。
3. 实现规范列出的 legacy 标题/字段映射，不做模糊匹配。
4. 实现不可变 Normalized View、全部来源 provenance 和稳定排序的 reader diagnostics。
5. 增加 hash/mtime、重复读取、字段换序、冲突和编码测试。
6. 运行全部 reader fixtures，形成 GREEN。
7. 独立 Review 后更新本任务，不开始 CLI 或 TASK_BOARD 功能。

## 完成标准

- [ ] 仅使用 Python 标准库。
- [ ] 接受 UTF-8 和 UTF-8 BOM；不使用本机 locale 猜测其他编码。
- [ ] v0.7 Reader 要求唯一 `## Workflow Contract` 和精确 ``- `key`: `value` `` 语法。
- [ ] 字段顺序不影响结果；重复键、未知键、错误大小写和非法 schema 得到确定 diagnostic。
- [ ] Normalized View 和 provenance 使用不可变结构。
- [ ] provenance 至少包含路径、标题、1-based 行号、原始值和来源类型。
- [ ] 安全默认值标记 `default` provenance；缺失 delivery 只在内存中为 `Not Recorded`。
- [ ] legacy 只识别规范的显式别名，不模糊匹配、不调用模型补全。
- [ ] 多个 legacy 值一致时保留全部 provenance 并产生 `W_LEGACY_INFERRED`。
- [ ] legacy 冲突产生 `E_LEGACY_CONFLICT`，不产生确定 normalized 值。
- [ ] diagnostics 按路径、行号、code 稳定排序。
- [ ] Reader 前后 fixture 内容、SHA-256 和 mtime 不变。
- [ ] reader-level fixtures 全部通过，重复运行结果一致。
- [ ] 生产实现前的测试运行确有目标断言失败；记录测试数和失败数，排除 0-test 假 RED。
- [ ] 实现没有写文件、subprocess、socket/network 或 Git 修改路径。
- [ ] 独立代码 Review 无 P0/P1。

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

## 代码审查

- 审查状态：未审查
- 审查人或审查 agent：待填写
- 审查严重等级：待填写
- P0 / P1 必须修改项：待审查
- 审查结论：待填写
- 是否允许进入验收建议：待确认

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：未审查
- 审查结论：待填写

## 用户动作等级 / 验收建议

- 用户动作等级：UA3
- 用户需要做什么：查看测试、只读证明和独立审查证据
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA3
- 反馈分类：不适用
- 下一步建议：等待任务执行、Review 和证据确认

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：未提交
- Commit hash：待填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`main`（建档时）
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：待执行时填写
- 计划分支：`codex/contract-003-readonly-readers`
- Diff 范围：待执行时填写
- 下一任务：`CONTRACT-004`，仅在本任务 `Accepted` 后转为 `Ready`
- 不要重复尝试：通过修改 fixture expected 结果掩盖 Reader 缺陷
