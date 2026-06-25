# Git 前置检查

Git precheck 用于在任务开始前确认项目是否有可审查、可回滚的基线。代码任务没有 Git baseline 时不得开始。

## Git 检查目标

- 判断是否是 Git 仓库。
- 判断当前分支。
- 判断当前 HEAD。
- 判断工作区是否干净。
- 判断是否有远程仓库。
- 判断是否有未提交改动。
- 判断是否存在不应提交的文件。
- 如果是 Batch，判断批次内任务是否共享同一清晰 base commit，并确认 B 级代码任务是否能按 TASK 拆分 diff / commit。
- 如果是 Wave，判断每个任务是否有独立 base commit、执行位置和清晰工作区；代码任务默认应使用独立分支或 Worktree。

## 推荐命令

```powershell
git rev-parse --show-toplevel
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
git log --oneline -5
```

## 如果不是 Git 仓库

agent 必须停止代码任务，并建议用户先建立 Git baseline。不要在没有 Git 的项目里直接开始代码修改。

建议步骤：

1. 创建或检查 `.gitignore`。
2. 排除 `bin/`、`obj/`、`.vs/`、`node_modules/`、`dist/`、`build/`、`logs/`、`*.user`、`*.suo`、本机配置和密钥文件。
3. 执行 `git init`。
4. 设置主分支 `main`。
5. 创建初始 baseline commit。
6. 再开始任务。

注意：

- 不得盲目执行 `git add .`。
- 必须先检查是否包含密钥、账号、构建产物、依赖目录、日志、本机绝对路径配置。
- 如果用户不希望初始化 Git，只能执行只读分析或非代码说明，不应继续代码任务。

## 如果已有未提交改动

agent 必须先判断：

- 这些改动是否属于当前任务。
- 是否需要先提交为 baseline。
- 是否需要拆分。
- 是否需要用户确认。
- 是否应该停止当前任务。

不得在不清楚改动来源时直接开始新任务。

## Batch / Wave 前置检查

- Batch 仍需记录 base commit，并确认批次内 A/B 小任务之间没有冲突文件；B 级代码 Batch 推荐 per-task commit。
- Wave 必须为每个任务记录 base commit、分支或 Worktree、预计修改文件和影响模块；并行代码任务必须能确认工作区隔离。
- 当前工作区已有来源不明的未提交改动时，不得启动 Batch 或 Wave。
- 不得因为批量或并行跳过 `git status --short`、diff 范围记录和不应提交文件检查。

## 不应提交文件常见例子

- 密钥、Token、证书、账号密码。
- `.env`、本机私有配置、IDE 用户配置。
- 构建产物和缓存目录。
- 依赖目录。
- 日志、崩溃转储、临时文件。
- 包含本机绝对路径的配置文件。

## 任务文件记录要求

代码任务开始前，至少在任务文件记录：

- 当前分支。
- Base commit。
- 当前 HEAD。
- 是否有未提交改动。
- 是否存在不应提交文件。
- 任务等级。
- 执行位置。
