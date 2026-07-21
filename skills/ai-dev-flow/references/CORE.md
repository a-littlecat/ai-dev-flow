# ai-dev-flow v0.8 核心规则

本文件与 `SKILL.md` 构成 v0.8 默认运行时内核。下方 `POLICY_JSON` 从通过 V003 门禁的原型原样提升，是 route、review 和 repair 决策的唯一规则源；其他文档只能解释，不得复制另一套触发列表。

解析失败、未知字段、输入不完整或规则冲突时一律 `Blocked`。

## 导航

- [单一 policy](#单一-policy)
- [路由解释](#路由解释)
- [事实源与状态](#事实源与状态)
- [Reviewer 合同](#reviewer-合同)
- [第 3 轮 repair](#第-3-轮-repair-判定)
- [权限和证据](#权限和证据硬门禁)
- [加载预算](#活跃加载预算)

## 单一 policy

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

## 第 3 轮 repair 判定

基础预算为 2。只有 policy 的所有布尔条件、scope hash、finding 稳定性、P0/P1 下降、严重度不升、验证分数上升和明确 round 3 target 同时满足，才返回 `ExtendRound3`；否则返回 `Stop`。

第 3 轮仍只处理冻结 findings。3 是绝对上限，更换模型不重置计数；发布、迁移、删除、外部同步或其他副作用不得自动重试。

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
