# REPAIR-CAMPAIGN-001：连续修复授权实施计划

## 背景

`REPAIR-ESCALATION-001` 已解决“自主 repair 上限耗尽后，即使用户授权也拒绝继续编码”的问题，但其默认授权仍绑定单个 repair chain、单个允许文件 hash 和一次 `ER-*` attempt。真实 CAD / 宿主软件全链验证会逐层暴露新的同范围 finding，导致流程反复进入 `Stop / UserDecisionRequired`，用户需要重复发送“授权”，而诊断、修复、验证和复审本身仍属于同一任务目标。

用户于 2026-07-27 明确要求把连续无实质进展阈值提高，并采用以下默认值：

- 核心产品代码：连续 4 次无实质进展后才进入用户裁决；
- 测试工具 / Harness：连续 5 次无实质进展后才进入用户裁决；
- P0、安全、数据、越界、不可逆副作用等硬停止条件不等待计数耗尽。

在原实现 Review Passed、UA2 Pending 后，用户补充确认：使用 Kimi Code 时应由 Kimi 自己启动原生独立 Reviewer，不得默认借助 Codex、Claude、OpenCode 或其他外部 Harness；只有用户明确指定时才允许跨 Harness。用户随后回复“认可，继续”，因此本计划在验收前修订并重新进入实现/复审。

## 推荐方案

在现有单次 `EscalatedRepair` 旁新增可选的任务级 `RepairCampaignAuthority`：

1. 用户授权绑定 TASK、验收合同、外层允许范围和生效 chain/history head，不绑定未来尚未产生的 finding 或 attempt ID。
2. 同一 chain 只统计授权生效后的 patch；后续新 chain 的每个 AR/ER patch 都建立独立 attempt、冻结 RED/GREEN/SIGNAL、实际文件 hash，并在 patch 后接受独立只读 Review、推进 campaign state。
3. `repair_gate.py` 只机械验证：
   - campaign authority 的来源、TASK、验收合同和范围绑定；
   - 当前 chain 的实际文件是否落在 campaign 外层范围；
   - trusted context 中唯一的当前 campaign state receipt，以及独立 expected TASK / acceptance contract（绑定 history anchor、最新 Review 和连续无进展计数）；
   - profile 对应的 4 / 5 次阈值；
   - 硬停止 flag 是否全部为 false。
4. 只读 gate 仍只返回 `MechanicallyEligible`；最终 `EscalatedRepairAllowed` 由持有当前对话、harness 或只读项目证据的 Orchestrator 提升。
5. Reviewer 选择遵循“当前 Harness 原生优先”：
   - Kimi Code 默认使用 Kimi 原生 `Agent` 建立新上下文 Reviewer；
   - Codex 默认使用 Codex 自身只读隔离 Reviewer；
   - 原生 Reviewer 缺少上下文或写权限隔离时返回 `Blocked/Pending`；
   - 不得自动跨 Harness；只有用户明确指定外部 Reviewer 来源时才允许。
6. `cad-dotnet-autotest` 与本 Skill 同时启用时只上报 core/harness/progress/hard-stop 分类，不再用“两次同类环境失败”提前停止；campaign 计数由 `ai-dev-flow` 唯一管理。

## 计数语义

- 计数单位仍是 `patch → 独立 Review`，只读诊断、原样重跑、Reviewer 重试、UA、TASK/看板同步和记录纠错不计数。
- 连续无进展计数是 campaign 级状态，不因新建 TASK、换模型、换 repair chain 或重命名 finding 清零。
- 独立 Review 证明至少一个冻结 closure 从 RED 变 GREEN、阻断 finding 减少、严重度下降，或在无回归前提下新增可证伪证据并关闭一个冻结根因假设时，计为“有实质进展”并清零。
- 新回归、严重度上升、测试标准放宽、仅改名/改记录或没有新的可证伪证据，不得计为进展。

## 硬停止条件

以下任一条件为 true 时立即 `Blocked` 或 `Stop / UserDecisionRequired`，不等待 4 / 5 次阈值：

- P0 finding；
- 安全边界变化；
- 数据完整性风险；
- 超出 campaign 范围；
- 不可逆动作或外部副作用；
- 放宽测试 oracle / PASS 标准；
- 未授权依赖或技术栈变化；
- 缺少独立 Reviewer、trusted context 或真实环境必需证据。

merge、push、release、删除、外部同步、Accepted 和 Closed 不属于 campaign authority。

## 实施范围

1. 新建 `REPAIR-CAMPAIGN-001` TASK，并更新任务板投影。
2. 更新 `SKILL.md + CORE.md`：
   - 新增 campaign policy；
   - 核心产品阈值 4，Harness 阈值 5；
   - 明确 soft stop / hard stop、跨 chain 继承和 delivery 独立授权。
3. 扩展只读 `repair_gate.py`：
   - 非 campaign ledger 使用原 `rc2` policy 继续验证旧单次 authority receipt；campaign 与新 receipt 使用 `rc3` policy；
   - 新增 campaign authority / scope manifest / trusted campaign state 校验；
   - 输出 campaign profile、阈值和当前连续无进展计数。
4. 扩展测试：
   - 第 1～3 次核心产品无进展继续，第 4 次停止；
   - Harness 第 4 次继续、第 5 次停止；
   - 有进展清零；
   - 新 chain / TASK / 模型不清零；
   - 越界和硬停止立即阻断；
   - 旧单次授权行为不变。
5. 更新直接冲突的 Workflow、模板、AGENTS 兼容规则、脚本说明、README、CHANGELOG 和版本号。
6. 固化同 Harness 原生 Reviewer 路由：
   - `SKILL.md + CORE.md` 规定 native-first、external-only-with-explicit-user-authority、native-unavailable=`Blocked`；
   - `WORKFLOW.md` 给出 Kimi/Codex 原生 Reviewer 执行与前后只读证明；
   - 测试覆盖 Kimi 默认不调用 Codex、缺原生能力不自动降级、用户显式指定才允许外部 Reviewer。
7. 从唯一可确认的本机 `cad-dotnet-autotest` 安装副本复制隔离候选，不改正在加载的安装文件；候选仅修改计数所有权和 core/harness 分类，验收/同步保持独立。
8. 执行全套测试、Skill validator、workflow lint、链接/版本检查、候选补丁检查和 `git diff --check`。
9. 由当前 Codex Harness 自身的隔离、只读 Reviewer 审查完整 diff；P0/P1 未关闭不得建议验收或同步，不自动调用其他 Harness。

## 非目标

- 不实现通用调度器、数据库、遥测、计费或自动状态写入器。
- 不修改冻结的 `evaluations/v0.8/**` 和 `prototypes/v0.8-lite/**`。
- 不自动同步本机 Skill、副本或 CADCat 项目规则。
- 不把隔离候选 `cad-dotnet-autotest` 补丁直接覆盖到本机安装副本。
- 不在原生 Reviewer 不可用时自动调用其他 Harness 或把同一上下文自检记为独立 Review。
- 不提交、推送、合并、发布或关闭任务。

## 回退

所有修改位于独立 Worktree `D:\open-source\ai-dev-flow-wt\repair-campaign-001` 和分支 `codex/repair-campaign-001`。回退时只恢复本任务 diff，不改写历史、不删除其他 Worktree，也不触碰主工作区的未跟踪缓存。

## 验证

```powershell
python -B -X utf8 -m unittest skills.ai-dev-flow.tests.test_repair_gate -v
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py" -v
python -B -X utf8 C:\Users\92336\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/ai-dev-flow
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/REPAIR-CAMPAIGN-001.md --format human
git diff --exit-code 8df7399 -- evaluations/v0.8 skills/ai-dev-flow/prototypes/v0.8-lite
git diff --check
git diff --no-index --check -- C:\Users\92336\.agents\skills\cad-dotnet-autotest\SKILL.md C:\Users\92336\.codex\visualizations\2026\07\27\019fa15f-d6c2-7421-ba69-91f55b2196ff\cad-dotnet-autotest-staging\SKILL.md
```
