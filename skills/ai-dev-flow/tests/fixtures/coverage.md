# Fixture Coverage

本表以 `manifest.json` 的 ID 为准。`reader_003`、`validator_004`、`board_006` 分阶段启用；`V_OVERLAY_WEAKENS_CORE` 仅登记为 `future_contract_007`。

| 规则 / diagnostic | 正例或不触发样例 | 反例 / 触发样例 | 阶段 |
|---|---|---|---|
| 8 个核心字段、受限 grammar、Review checkpoint | `FIX-VALID-A` | `FIX-E-PARSE` | reader_003 |
| 枚举和值域 | `FIX-VALID-A` | `FIX-E-UNKNOWN` | reader_003 |
| task_id provenance 一致 | `FIX-VALID-A` | `FIX-ID-H1` | reader_003 |
| Legacy 确定映射 | `FIX-LEGACY-AUTHORITY` | `FIX-LEGACY-CONFLICT`、`FIX-LEGACY-MERGE-CONFLICT` | reader_003 |
| lifecycle 正文门禁 | `FIX-VALID-A` | `FIX-GUARDS` | validator_004 |
| 合法 / 非法流转 | `FIX-VALID-A` | `FIX-ILLEGAL-TRANSITION` | validator_004 |
| Git 历史不可验证 | `FIX-VALID-A` | `FIX-TRANSITION-UNVERIFIABLE` | validator_004 |
| Review / UA 门禁 | `FIX-VALID-A` | `FIX-GUARDS` | validator_004 |
| UA7 必须 User Confirmed | `FIX-VALID-A` | `FIX-UA7` | validator_004 |
| Closed authority | `FIX-VALID-A` | `FIX-CLOSE` | validator_004 |
| Feedback scope | `FIX-VALID-A` | `FIX-FEEDBACK-SCOPE` | validator_004 |
| RED / GREEN / SIGNAL | `FIX-FEEDBACK-SCOPE`（scope 先阻塞） | `FIX-SIGNAL` | validator_004 |
| merge 顺序与本次用户授权 | `FIX-VALID-A` | `FIX-DELIVERY` | validator_004 |
| optional / required extension | `FIX-VALID-A` | `FIX-EXT` | validator_004 |
| authority provenance | `FIX-VALID-A` | `FIX-LEGACY-AUTHORITY` | validator_004 |
| Overlay 未求值 | `FIX-VALID-A` | `FIX-PROJECT-OVERLAY` | validator_004 |
| Board 缺行 / 孤儿 / 漂移 / 解析 | `FIX-VALID-A` | `FIX-BOARD-MISSING`、`FIX-BOARD-DRIFT`、`FIX-E-BOARD-PARSE` | board_006 |
| Overlay 不得放宽核心 | 不适用 | `FIX-OVERLAY-WEAKENS` | future_contract_007 |

## Diagnostic 全量索引

- Error：`E_PARSE` → `FIX-E-PARSE`；`E_UNKNOWN_VALUE` → `FIX-E-UNKNOWN`；`E_TASK_ID_CONFLICT` → `FIX-ID-H1`；`E_LEGACY_CONFLICT` → `FIX-LEGACY-CONFLICT`；`E_BOARD_PARSE` → `FIX-E-BOARD-PARSE`。
- Violation：`V_STATE_GUARD` / `V_REVIEW_GUARD` / `V_UA_GUARD` → `FIX-GUARDS`；`V_ILLEGAL_TRANSITION` → `FIX-ILLEGAL-TRANSITION`；`V_CLOSE_AUTHORITY` → `FIX-CLOSE`；`V_ACCEPTANCE_SCOPE` → `FIX-FEEDBACK-SCOPE`；`V_SIGNAL_GATE` → `FIX-SIGNAL`；`V_DELIVERY_ORDER` / `V_DELIVERY_AUTHORITY` → `FIX-DELIVERY`；`V_EXTENSION_REQUIRED_UNKNOWN` → `FIX-EXT`；`V_BOARD_DRIFT` → `FIX-BOARD-DRIFT`；`V_OVERLAY_WEAKENS_CORE` → `FIX-OVERLAY-WEAKENS`（future_contract_007）。
- Warning：`W_LEGACY_INFERRED` / `W_AUTHORITY_UNVERIFIABLE` → `FIX-LEGACY-AUTHORITY`；`W_TRANSITION_UNVERIFIABLE` → `FIX-TRANSITION-UNVERIFIABLE`；`W_EXTENSION_OPTIONAL_UNKNOWN` → `FIX-EXT`；`W_BOARD_MISSING` → `FIX-BOARD-MISSING`；`W_BOARD_ORPHAN` → `FIX-BOARD-DRIFT`；`W_PROJECT_OVERLAY_UNEVALUATED` → `FIX-PROJECT-OVERLAY`。

## Comparison 基线

三个样本都基于真实 Git 变更回填，统一处于 `Review` checkpoint；两侧保留相同目标、范围、完成标准和验证事实。Compact 只保留 8 个核心字段，无 `N/A` 填充。

| 来源 commit | Legacy required | Compact required | Legacy 重复状态 | Compact 重复状态 |
|---|---:|---:|---:|---:|
| `81a8837` | 22 | 18 | 3 | 0 |
| `12b3dc0` | 23 | 18 | 3 | 0 |
| `4a6c417` | 24 | 18 | 3 | 0 |
