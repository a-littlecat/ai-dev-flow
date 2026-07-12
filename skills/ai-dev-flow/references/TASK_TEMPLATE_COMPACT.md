# <TASK-ID>：<任务标题>

> Compact v0.7 仅用于新建的 A/B 任务，且必须同时满足 `overlays=none`、非 Batch、非 Wave、非 `real_env_signal`。不满足或无法确定时停止并使用 Full/Legacy `TASK_TEMPLATE.md`；已存在的 legacy TASK 保持原格式。

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `<TASK-ID>`
- `task_type`: `<document|plan|code|review|repair|test>`
- `task_class`: `<A|B>`
- `lifecycle`: `<Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled>`
- `review_status`: `<Pending|In Review|Passed|Needs Fix|Do Not Merge>`
- `ua_level`: `<UA0|UA1|UA2|UA3|UA4|UA5|UA6|UA7|TBD>`
- `ua_status`: `<Not Required|Pending|Passed|Failed|Deferred|TBD>`

<!-- 仅在语义要求时增加条件字段：ua_evidence、acceptance_authority、close_authority、commit_status、merge_status、merge_authority。overlays=none 可省略；不要机械填充空状态。 -->

## 目标与边界

- 目标：<可验证目标>
- 非目标：<明确不做的内容；确无非目标时写 none>
- 允许修改：<路径或模块>
- 禁止修改：<路径或模块>

## 完成标准与验证

- 完成标准：<可观察完成条件>
- 验证命令或检查：<可重复命令或人工检查>

## Outcome

<!-- Draft/Ready 阶段可暂不填写 Outcome；进入对应状态后按 WORKFLOW_CONTRACT.md 的正文门禁增加所需字段。 -->

- Base / Diff：base=<base-ref>;diff=<base-ref>..<head-ref>
- 修改文件：<实际文件>
- 验证证据：<命令、日志或报告引用>
- Review findings：none

<!-- C/D、Batch、Wave、real_env_signal、验收失败反馈和未知条件不得继续使用本模板。Compact 后续进入复杂路径时停止并待确认，不得自动迁移，也不得补回 legacy 的双 Review 或双 delivery 段落。 -->
