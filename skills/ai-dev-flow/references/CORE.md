# ai-dev-flow v0.8 核心规则

本文件与 `SKILL.md` 构成 v0.8 默认运行时内核。下方 `POLICY_JSON` 的 route/review/safety 继承通过 V003 门禁的冻结原型，repair 在后续开发线中独立演进；它是当前 route、review 和 repair 决策的唯一规则源，其他文档只能解释。

解析失败、未知字段、输入不完整或规则冲突时一律 `Blocked`。

## 导航

- [单一 policy](#单一-policy)
- [路由解释](#路由解释)
- [事实源与状态](#事实源与状态)
- [Reviewer 合同](#reviewer-合同)
- [Repair 边界](#repair-边界与用户授权升级)
- [权限和证据](#权限和证据硬门禁)
- [加载预算](#活跃加载预算)

## 单一 policy

<!-- POLICY_JSON_BEGIN -->
```json
{
  "schema_version": "ai-dev-flow/v0.8-policy-rc2",
  "unknown_input": "Blocked",
  "routes": {
    "controlled": {
      "task_classes": ["D"],
      "ua_min": 5,
      "risk_flags": [
        "architecture",
        "data_migration",
        "delivery",
        "external_sync",
        "irreversible_action",
        "parallel_writers",
        "real_environment",
        "release",
        "security"
      ],
      "requested_actions": [
        "acceptance_recommendation",
        "delivery",
        "merge",
        "release"
      ],
      "when_delivery_action": true,
      "when_real_environment_required": true
    },
    "lite": {
      "task_classes": ["A", "B"],
      "requires_action_authority": "Allowed",
      "requires_deterministic_coverage": true,
      "requires_user_observation": false,
      "disallowed_risk_flags": [
        "business_files_gt_3",
        "build_or_deploy_config",
        "core_execution_path",
        "core_writer_path",
        "explicit_independent_review",
        "historical_p1",
        "public_api",
        "shared_component",
        "tests_do_not_cover_oracle"
      ]
    },
    "fallback": "Tracked"
  },
  "review": {
    "Lite": "Skipped",
    "Tracked": {
      "trigger_risk_flags": [
        "business_files_gt_3",
        "build_or_deploy_config",
        "core_execution_path",
        "core_writer_path",
        "explicit_independent_review",
        "historical_p1",
        "public_api",
        "shared_component",
        "tests_do_not_cover_oracle"
      ],
      "otherwise": "Skipped"
    },
    "Controlled": {
      "required": true,
      "enforcement_points": [
        "acceptance_recommendation",
        "delivery",
        "merge",
        "release"
      ]
    },
    "missing_authority_or_capability": "Blocked"
  },
  "safety": {
    "allowed_action_authority": "Allowed",
    "require_real_environment_evidence": true,
    "delivery_requires_controlled": true,
    "missing_required_evidence": "Blocked"
  },
  "repair": {
    "repair_round_definition": "patch_to_next_independent_review",
    "non_counting_actions": [
      "diagnostic_evidence_only",
      "record_only_correction",
      "review_only",
      "task_or_board_receipt_sync",
      "test_rerun_without_patch",
      "ua_without_patch"
    ],
    "chain_identity_fields": [
      "repair_chain_id",
      "finding_ids",
      "closure_contract_hash",
      "allowed_files_hash"
    ],
    "ledger_schema": "ai-dev-flow/repair-ledger-v1",
    "evidence_trust_boundary": "ledger_is_untrusted_trusted_context_is_supplied_by_project_or_harness",
    "record_only_finding": {
      "default_severity": ["P2", "P3"],
      "p1_only_if": [
        "can_authorize_unsafe_action",
        "can_hide_blocking_finding"
      ]
    },
    "base_auto_rounds": 2,
    "autonomous_max_rounds": 3,
    "history": {
      "attempt_count_source": "validated_receipt_chain",
      "receipt_hash_algorithm": "sha256_canonical_json",
      "require_history_anchor": true,
      "require_trusted_context": true,
      "trusted_context_schema": "ai-dev-flow/repair-trusted-context-v1",
      "require_independent_review_receipt_after_each_attempt": true
    },
    "required_true_fields": [
      "dependencies_frozen",
      "authority_frozen",
      "root_cause_known",
      "reviewer_capable",
      "repairer_capable",
      "within_cost_boundary"
    ],
    "required_false_fields": ["external_side_effect"],
    "round_3_progress": {
      "source": "latest_independent_review_receipt",
      "require_red_to_green": true,
      "forbid_green_to_red": true,
      "forbid_new_blocking_findings": true,
      "severity_must_not_increase": true,
      "evidence_coverage_must_strictly_increase": true,
      "round_3_target_required": true
    },
    "task_change_resets_budget": false,
    "model_change_resets_budget": false,
    "post_stop": {
      "state": "UserDecisionRequired",
      "mode": "EscalatedRepair",
      "ai_repair_allowed_with_explicit_authority": true,
      "manual_implementation_required": false,
      "default_authorized_attempts": 1,
      "authority_source": "trusted_context_attested_chain_bound_authority_receipt",
      "authority_must_bind": [
        "repair_chain_digest",
        "closure_contract_hash",
        "allowed_files_hash",
        "target_finding_ids",
        "authorized_attempt_ids"
      ],
      "independent_review_after_each_attempt": true,
      "history_resets": false,
      "failure_decision": "Stop"
    },
    "mechanical_decisions": [
      "MechanicallyEligible",
      "Stop",
      "Blocked"
    ],
    "promotion_decisions": [
      "AutoRepairAllowed",
      "ExtendRound3",
      "EscalatedRepairAllowed"
    ],
    "promotion_requires_trusted_orchestrator": true,
    "eligible_modes": [
      "AutoRepair",
      "ExtendRound3",
      "EscalatedRepair"
    ]
  }
}
```
<!-- POLICY_JSON_END -->

## 路由解释

按优先级先判 Controlled，再判 Lite，其他已知情况进入 Tracked：

- Lite 的正式结果名为 `DoNotUseSkill`。即使用户先点名本 Skill，完成路由后也应停止加载其余工作流文件。
- Tracked 只为范围和证据建立 TASK；Reviewer 是否调用完全由 policy 风险标记决定。
- Tracked 的 `Skipped` 不映射为 v0.7 Contract 的 `Passed`：不调用 Reviewer 时 `review_status` 保持 `Pending`；若要进入 Accepted / Closed，再完成一次真实只读 Review。
- Controlled 不代表已经获得操作授权，只表示需要最严格的事实源、证据和 Review。
- task class、UA、风险、请求动作、authority、验证覆盖或用户观察需求有任一未知时，不得选择 Lite。

## 事实源与状态

- Tracked / Controlled 的 TASK 是细粒度事实源；TASK_BOARD 是索引和投影。
- `adf/v0.7.0` 仍是当前 TASK Contract schema；Skill 包 `0.8.0` 不迁移或改写旧 Contract。
- Review、验证、UA、Accepted、commit、merge、delivery、release、Closed 相互独立。
- lint 通过只证明可确定的结构规则通过，不等于 Review 或验收完成。

## Reviewer 合同

- Reviewer 只读，不修改业务代码，也不代替用户验收。
- Reviewer 与执行/修复上下文隔离；同平台模型可以使用，但不得伪造平台未暴露的身份或调用证据。
- finding 必须有稳定 ID、P0～P3、证据、范围、验证方式和处置结论。
- P0/P1 在验收或交付前必须关闭；P2 可拆后续任务；P3 不阻塞。
- Tracked 命中风险但缺 Reviewer 时只能 `Blocked`、合法升级或取得明确授权；不能静默跳过。

### 隔离实现映射

- 原则：Reviewer 必须同时具备上下文隔离和写权限隔离。上下文隔离可由 subagent、独立进程或沙箱任务提供；写权限隔离必须由真实只读 sandbox、只读副本或等效机制提供。主上下文内切换角色、自称审查员不算隔离，仅启动普通可写子进程也不算只读，此类结果一律记为 `Pending`。
- 已知环境映射（示例，非准入名单）：
  - kimi-code：`Agent` 工具的 subagent（独立上下文，优先只读类型）。
  - codex：subagent，或 `codex exec` 只读沙箱子进程；注意 subagent 继承父级 sandbox/approval 策略，只读约束须在任务定义中明确。
  - opencode：Task 工具调用配置中禁用写权限的 reviewer 子代理。
- 其他环境：存在等效的上下文隔离与写权限隔离机制时按本原则映射；没有或不确定时保持 `Blocked` / `Pending`，并说明所需最小输入。兜底 CLI 进程必须显式启用只读 sandbox 或面向只读副本运行，并在前后核对工作区状态；进程级隔离本身不授予只读能力。
- 新环境核实后可向本表追加映射，本原则不变。

## Repair 边界与用户授权升级

一轮 repair 只指：针对冻结 finding 做出意图改变验收结论的 patch，直到下一次独立复审。只读 Review、无 patch 的 UA、诊断取证、原样重跑测试、TASK/看板收据同步和纯记录纠错不计轮次。

预算绑定 `repair_chain_id + finding_ids + closure_contract_hash`，不绑定 TASK ID。处理同一 finding 或同一 closure contract 时，更换 TASK 或模型均不重置历史；只有独立的 RED、根因和 closure contract 才能建立新 chain。

基础 `AutoRepair` 预算为 2。第 3 轮只在至少一个冻结 closure criterion 从 RED 变 GREEN、没有 GREEN 变 RED、没有因 patch 新增阻断 finding、严重度不升、固定证据覆盖向量增加且目标冻结时返回 `ExtendRound3`。3 是自主 repair loop 上限，不是 AI 编码的永久禁令。

达到 `Stop` 后进入用户裁决（`UserDecisionRequired`）。用户了解证据和风险后可明确授权 AI 执行有界 `EscalatedRepair`，默认一次；必须冻结干净基线、RED/GREEN、finding/closure target、允许范围和 Reviewer 能力。每次尝试后独立复审，失败回到 `Stop`，不得自动连跑；历史计数不清零。发布、迁移、删除、外部同步或其他不可逆副作用仍不得自动重试。

纯记录不一致默认按 P2/P3 处理；只有它可能授权不安全动作或掩盖阻断 finding 时才升级为 P1。可用 `scripts/repair_gate.py` 对 repair ledger 的 chain、hash、Review、progress 和 authority 绑定做只读机械判定。

ledger 一律视为不可信输入。判定器还必须接收由当前对话、harness 或只读项目快照提供的独立 trusted context，用它核对 expected history head/count 和已确认的 Review/authority receipt；缺失或不匹配时必须 `Blocked`。

脚本只返回 `MechanicallyEligible + eligible_mode`，永不自行产生最终 `*Allowed`。持有真实上游证据的 Orchestrator 才能把机械资格提升为 policy 的 `AutoRepairAllowed / ExtendRound3 / EscalatedRepairAllowed`；该提升及证据必须写回 TASK。这样既允许用户授权 AI 继续修复，也不把自填 JSON 当成授权。

## 权限和证据硬门禁

- 用户要求的结果不自动授权 merge、push、release、删除、外部写入或 `Closed`。
- 必需真实环境证据缺失时保持 `Blocked`，不得用普通单元测试冒充。
- 敏感数据、安全、不可逆动作和 delivery 必须按 Controlled 处理。
- 状态不清写“待确认”或 `Blocked`，不要用更好听的状态代替事实。
- harness 原生权限确认（如 CLI 的逐次授权提示）可作为收集授权的手段，但不免除记录义务；授权与状态以 TASK 和交接输出为准，不依赖 harness 的提示日志。
- harness 自带的执行期跟踪（如任务清单工具）只作过程管理，不复制 TASK 状态；冲突时以 TASK 为事实源。

## 活跃加载预算

- 默认：`SKILL.md` + 本文件。
- Tracked：默认内核外最多读取 1 份与当前动作直接相关的 reference。
- Controlled：可按风险读取必要专项文档，但不要整包预加载。
- `PROMPTS.md`、Batch、Wave、Loop、Memory、Constitution、角色和 provider/harness 指南均不默认加载。
