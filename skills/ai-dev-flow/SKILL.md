---
name: ai-dev-flow
description: 按风险启用的 Git-first AI 开发治理内核。用于需要任务事实源、权限边界、独立审查、修复上限或验收与交付状态分离的持续开发任务；低风险单会话任务会明确退出 Skill。
---

# ai-dev-flow v0.8

`ai-dev-flow` 不是所有任务的必经流程。它先判断是否有净收益：低风险任务退出 Skill；只有需要持续留证或高风险控制时才启用治理。

## 必读顺序

1. 完整读取本文件。
2. 完整读取 [CORE.md](references/CORE.md)。其中 `POLICY_JSON` 是路由、Reviewer 和第 3 轮 repair 的唯一规则源。
3. 读取用户要求、项目 `AGENTS.md`、Git 状态和与任务直接相关的事实源。
4. 先路由，再决定是否读取一份按需 reference。不要默认加载 `PROMPTS.md` 或整个 `references/`。

默认运行时工作流输入只有本文件与 `CORE.md`。解析失败、输入未知或规则冲突时，按 `Blocked` 处理，不猜测。

## 第一步：路由

把可观察事实整理为 policy 输入：任务等级、UA、请求动作、风险标记、是否有动作授权、是否有确定性验证覆盖、是否需要用户观察或真实环境证据。

按 `CORE.md` 的顺序判断：

1. 命中 `controlled` 条件则进入 `Controlled`。
2. 完整满足 `lite` 条件则输出 `DoNotUseSkill`。
3. 其他已知输入进入 `Tracked`。
4. 信息不足或未知字段为 `Blocked`。

不确定时只能升级或阻塞，不能降级。

## Lite：退出 Skill

路由结果为 `DoNotUseSkill` 后：

- 停止读取本 Skill 的其他文件；
- 不创建 TASK，不调用 Reviewer，不进入 repair loop；
- 只按用户要求、项目规则、Git/diff 和直接相关文件完成最小改动；
- 用确定性验证覆盖全部完成标准，最后报告修改、验证、风险和未完成项。

容易回滚不能代替验证。需要用户观察、真实环境证据、额外授权或高风险动作时，必须重新路由。

## Tracked：按需治理

Tracked 用于跨会话、范围较大或需要留证但尚未达到 Controlled 的任务：

- 新任务使用 `references/TASK_TEMPLATE.md`，现有任务继续沿用原格式；
- TASK 是范围、状态和证据事实源，TASK_BOARD 只是投影；
- 记录 base commit、允许/禁止范围、完成标准、验证、diff 和状态边界；
- 仅在 policy 的 Tracked 风险标记命中时调用一个隔离、只读 Reviewer；未命中则跳过，不为流程而调用；
- policy 跳过只表示“没有 Reviewer 调用”，不得伪装成 `review_status=Passed`；在 `adf/v0.7.0` 下保持 `Pending`，如要进入 Accepted / Closed 再完成真实只读 Review；
- 命中但缺少 Reviewer authority/capability 时保持 `Blocked`、合法升级或取得明确授权，不得自批为 Passed。

## Controlled：强制控制

Controlled 使用完整 TASK 和清晰授权边界。执行前冻结范围、风险、完成标准和验证；在 policy 规定的 enforcement point 前必须完成独立 Review。

- `review_task` 只审查，不修改业务代码；
- `repair_task` 只处理稳定 finding ID 指向的问题；
- delivery、merge、release、删除、迁移、外部写入等动作必须分别获得相应授权；
- 真实环境任务必须区分自动证据与用户实机证据；缺少必需证据时保持 `Blocked`。

## 执行与验证

Tracked / Controlled 的最小闭环：

1. 核对 TASK、项目规则、Git 状态和 source of truth。
2. 冻结允许修改范围、禁止范围和完成标准。
3. 做最小必要改动，不顺手扩 scope。
4. 运行最贴近风险的构建、测试、静态检查或真实环境验证。
5. 检查 diff 归属与 `git diff --check`。
6. 按 policy 决定跳过或进入独立 Review。
7. 分别记录验证、Review、UA、commit、merge、release 和 Closed 状态。

验证失败时可在冻结范围内修复；范围、权限或风险改变时重新路由。任何无法安全继续的条件都写清阻塞原因和所需最小输入。

## Review 与 repair

Reviewer 必须只读、与 Engineer/Repairer 上下文隔离，并输出稳定 finding ID、P0～P3 和 `Passed / Needs Fix / Blocked`。

Tracked / Controlled 默认最多 2 轮 repair。第 3 轮只能由 `CORE.md` 的 progress gate 授予，3 是绝对上限；更换模型不重置预算。不得用 repair 自动重试不可逆外部动作。

## 状态边界

以下状态相互独立，不能互相推导：

- 自动验证通过；
- Review Passed；
- UA Passed / Accepted；
- committed / merged；
- released / delivered；
- Closed。

没有授权就不执行 merge、push、release、外部同步、删除或其他高影响动作。没有证据就不写“已完成”“已验收”或“已发布”。

## 按需 reference

只有当前动作确实需要时，最多选择一份最相关文件：

- 创建/更新 Tracked 或 Controlled TASK：`TASK_TEMPLATE.md`
- 需要完整执行细节：`WORKFLOW.md`
- 独立代码审查：`CODE_REVIEW_CHECKLIST.md`
- 用户动作等级：`ACCEPTANCE_GUIDE.md`
- Git/diff 专项：`GIT_PRECHECK.md` 或 `DIFF_REVIEW.md`
- v0.7 兼容/迁移：`V0.8_MIGRATION.md`

其他旧指南是兼容资料，不在 v0.8 默认运行路径内。`PROMPTS.md` 仅供人工复制短提示，不是必读依赖。

## 交接输出

最终结果应简明列出：

- 修改了哪些文件、各自做什么；
- 执行了哪些验证及结果；
- Review、UA、commit、merge、release、Closed 的真实状态；
- 剩余风险、未完成项和下一步。
