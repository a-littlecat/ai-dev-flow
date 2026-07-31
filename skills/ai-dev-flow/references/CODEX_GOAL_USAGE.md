# Codex Goal 治理预设

Codex 原生 Goal 负责持续执行、预算、续跑和 `Active / Complete / Blocked` 状态；TASK 负责项目范围、验证、Review、UA 与交付事实；`ai-dev-flow` 只提供治理门禁。三者不得复制状态。

只有用户明确要求“创建 / 启动 / 开启 Goal（目标）”或使用下列明确触发语句时，才创建 Codex Goal。普通的“继续”“修改”“完成它”不自动创建 Goal。

## 预设与中文触发词

### 受控目标 `governed_goal`

推荐触发词：

- `启动受控目标`
- `开启受控 Goal`
- `持续修到可验收`
- `一直修到 Review Passed`
- `我去休息，修到能验收`
- `不要因普通失败停下来，修到可验收`

默认终点是 `VerificationGreen + ReviewPassed + AcceptanceReady`。允许范围内诊断、修改、测试、独立 Review、repair 和记录同步；不自动 commit、merge、push 或 release，除非启动语句另有明确授权。

### 自动落地 `auto_land`（推荐默认）

推荐触发词：

- `启动自动落地目标`
- `开启自动交付 Goal`
- `全自动做到提交、合并和推送`
- `一直做到 PR 和 CI 通过`
- `我去休息，自动修好并交付`
- `不用中途问我，完成后直接交付`
- `自动处理到合并完成`

在冻结 TASK、允许范围、目标分支和完成标准后，`auto_land` 预授权：

- 创建或使用隔离 Worktree / 分支；
- 诊断、实现、确定性验证、独立 Review 与范围内 repair；
- TASK / TASK_BOARD 记录同步；
- 精确暂存、commit、与最新目标分支集成、任务范围内冲突修复与合并后验证；
- push 当前任务分支或已授权目标分支、创建 / 更新 PR、等待 CI 并修复范围内失败；
- 在分支保护与仓库规则允许时完成 merge。

`auto_land` 不包含 tag、release、deploy、删除、数据迁移、密钥或认证/授权修改、强制推送、历史改写或 `Closed`。

### 自动发布 `auto_release`

推荐触发词：

- `启动自动发布目标，版本为 <version>`
- `自动发版到 <environment>`
- `自动打标签并发布 <version>`
- `完成后发布到 <明确目标>`

只有版本、目标环境、交付物和回滚边界都明确时才启用。缺少其中任一项时先从项目事实源保守补全；若不同选择会改变外部影响或不可逆范围，再请求用户决策。`auto_release` 不隐含删除、数据迁移、密钥或权限变更。

## 触发和授权解释

- 中文触发词按完整意图解释，不做任意子串匹配；例如“自动检查”不等于 `auto_land`，“发布说明”不等于 `auto_release`。
- 触发预设后仍要冻结 TASK、scope、目标分支和完成标准。能从当前仓库与 TASK 唯一确定的内容直接使用，不机械追问。
- Goal 只是运行容器，不是 authority。实际允许动作来自用户触发语句、项目规则和 TASK 中记录的 authority envelope。
- 原生 Goal 不可用时，明确降级为普通会话；不得用 Skill 自建后台循环、预算、恢复协议或伪造 Goal 状态。

## 自动验收

当验收指标在启动前已冻结、当前环境可以直接执行、结果唯一且不依赖主观判断时，可以在 TASK 中指定 Codex 为 `Designated Acceptor`，例如测试、CPU/内存/进程采样、DOM/碰撞 oracle、文件输出或协议合同。

以下情况不能自动代替用户：真实外部宿主或设备不可用、真实业务账号/数据不可用、产品审美或风险取舍、生产发布决策、不可逆操作。此时 Goal 保留已有成果并停在对应 UA / 决策边界。

## 唯一硬停止

- P0、安全边界、数据完整性、秘密信息或权限风险；
- 越出冻结 scope、需要大型依赖或架构/技术栈变化；
- 删除、不可逆动作、test oracle 放宽，或未被当前 `auto_release` authority 明确覆盖 / 超出冻结版本、环境、交付物与回滚边界的生产外部副作用；
- 来源不明且与当前任务重叠的用户改动；
- 必需真实证据不可获得；
- 达到当前 repair campaign 的连续无进展阈值；
- 用户撤销 Goal 或 authority。

普通测试失败、范围内 Review finding、可归属的合并冲突、CI 重跑和基础 repair 轮次耗尽，不单独中断 `auto_land`；仍沿用 `CORE.md` 的 campaign 与独立 Review 规则。

## 推荐启动语句

```text
为 <TASK-ID/需求> 启动自动落地目标。请在冻结范围内持续实现、测试、独立复审、修复、提交、合并、推送并处理 PR/CI；机器可确定的验收由 Codex 作为 Designated Acceptor。只有安全、数据、不可逆、生产发布、范围扩大、来源不明改动或真实人工验收不可替代时才暂停。不要创建 tag、release 或部署。
```

Skill 不保存 Goal 内部预算、剩余量或运行状态，也不向 Workflow Contract 增加 `goal_id` 等字段。需要查看运行状态时使用 Codex 原生 Goal 能力；项目状态始终写回 TASK。
