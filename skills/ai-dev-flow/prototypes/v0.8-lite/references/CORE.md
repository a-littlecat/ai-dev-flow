# v0.8 Lite 原型核心规则

## 单一事实源

下方 `POLICY_JSON` 是本原型的唯一 route/review/repair 决策源。运行时说明与阶段 A 评估都必须读取同一个 JSON；解析失败、未知字段或不完整输入一律 `Blocked`。不得在脚本或其他文档中维护平行触发列表。

<!-- POLICY_JSON_BEGIN -->
```json
{
  "schema_version": "ai-dev-flow/v0.8-policy-rc1",
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
    "base_rounds": 2,
    "absolute_max_rounds": 3,
    "required_true_fields": [
      "dependencies_frozen",
      "authority_frozen",
      "root_cause_known",
      "reviewer_capable",
      "repairer_capable",
      "within_cost_boundary"
    ],
    "required_false_fields": ["external_side_effect"],
    "scope_hashes_must_match": true,
    "finding_ids_must_be_stable": true,
    "p0_p1_counts_strictly_decrease": true,
    "severity_must_not_increase": true,
    "validation_scores_strictly_increase": true,
    "round_3_target_required": true,
    "model_change_resets_budget": false,
    "extend_decision": "ExtendRound3",
    "stop_decision": "Stop"
  }
}
```
<!-- POLICY_JSON_END -->

## 执行边界

- Lite 不建 TASK、不调用 Reviewer、不进入 repair loop。
- Tracked/Controlled 的 TASK 是事实源，看板只是投影。
- Reviewer 只读且与 Engineer/Repairer 上下文隔离；输出稳定 finding ID、P0～P3 与 `Passed / Needs Fix / Blocked`。
- 缺少 Reviewer authority/capability 时保持 `Blocked`、合法升级或取得明确授权，不得自批。
- Review Passed、验证、UA、Accepted、commit、merge、release、Closed 互不推导。
- 不得用第 3 轮自动重试发布、迁移、删除或其他外部副作用。
