# Diff 审查

代码审查不是泛泛读文件，而是审查本任务从 base commit 到当前工作区或 HEAD 的具体改动。

## Diff 审查目标

- 确认本任务实际修改了什么。
- 判断 diff 是否只包含当前任务相关文件。
- 发现范围越界、无关重构和不应提交文件。
- 检查格式、空白、冲突标记和基础质量问题。
- 给出是否允许进入验收建议、建议用户动作等级、是否允许合并的结论。

## 1. pre-commit diff review

适合 A / B 级任务。

命令：

```powershell
git status --short
git diff --stat
git diff --name-only
git diff
git diff --check
```

特点：

- commit 前先审查。
- 如果发现问题，可以直接修改或恢复。
- 通过后再 commit。

## 2. post-commit diff review

适合 C / D 级任务。

命令：

```powershell
git status --short
git diff --stat <base_commit>..HEAD
git diff --name-only <base_commit>..HEAD
git diff <base_commit>..HEAD
git diff --check <base_commit>..HEAD
git log --oneline <base_commit>..HEAD
```

特点：

- 基于 base commit 到 HEAD 审查。
- 适合分支、Worktree、PR 前审查。
- 可明确本任务全部改动。

## 审查范围规则

- 只审查当前任务 diff。
- 不把历史遗留问题都算作本任务问题。
- 如果发现历史问题，记录为“历史风险 / 后续任务”。
- 如果 diff 中出现无关文件，标记为范围越界。
- 如果任务没有记录 base commit，审查前必须补充或停止。
- 如果存在未提交改动，需要明确是否属于当前任务。
- Batch 审查必须能按任务拆分 diff；拆不清时不得强行通过。
- Wave 审查必须按任务使用各自 base commit、HEAD 和 diff 范围。
- 不得让多个任务共享一个模糊 diff 作为审查依据。

## 审查结论格式

```markdown
## Diff 审查结论

结论：通过 / 需要修改 / 不建议合并

Diff 范围：<base_commit>..HEAD 或 当前工作区未提交 diff

修改文件：
- 待填写

范围越界文件：
- 无

必须修改项：
- 无

建议修改项：
- 无

风险：
- 无

推荐验证：
1. 待填写

是否允许进入验收建议：是 / 否

建议用户动作等级：UA0 / UA1 / UA2 / UA3 / UA4 / UA5 / UA6 / UA7 / 待确认

是否允许合并：是 / 否 / 不适用
```

## Batch / Wave diff 审查

- Batch 适合 A/B 小任务，仍需逐任务列出修改文件和 diff 范围。
- Wave 中每个任务必须单独记录 base commit、当前 HEAD 和 diff 范围。
- Review Hub 可以集中审查 Batch / Wave，但输出必须逐任务给结论。
- 如果发现任务间 diff 交叉、文件冲突或模块冲突，应标记为范围越界或并行风险。
