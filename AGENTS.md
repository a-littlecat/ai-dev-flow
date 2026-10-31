# ai-dev-flow 仓库

开发流程 skill 本身。这个仓库也按它自己管：开发相关请求从 `skills/ai-dev-flow/SKILL.md` 进入。结构和版本历史见 `README.md`。

## 项目事实

- **信任等级**：未写，按总览第 4 节为 L0（合并前问用户）。等级由用户在这里改。
- **队列**：`docs/queue.md`，只由编排会话维护。
- **检查**：
  - 改了 `skills/ai-dev-flow/scripts/status.ps1`：跑 `pwsh -NoProfile -File tests/status.tests.ps1`，退出码 0 才算通过。
  - `skills/ai-dev-flow/scripts/dispatch.ps1` 还没有自动检查，改它要靠独立审查实跑。
  - 只改文档的，按 `skills/ai-dev-flow/modules/verify.md` 第 1 节逐条核对文档里写的路径、命令和章节引用。
- **安装同步**：合进 `main` 以后，把 `skills/ai-dev-flow/` 复制到 `~/.agents/skills/ai-dev-flow/`（见 README 的安装一节），再用 `diff -rq` 确认两边一致。Claude Code 的 `~/.claude/skills/ai-dev-flow` 是指向它的目录链接，不用另外复制。
- **推送**（用户 2026-10-29 定）：改动审查通过、合进 `main`、同步到本机安装之后，把 `main` 和 `refs/notes/verify` 推到 `origin`。推之前做两件事：
  - 看 `git log origin/main..main`，确认要推的提交都审过；
  - 查一遍提交和 note，确认没有本机路径和密钥。
  
  这是公开仓库。其他项目的推送规则看各自的 `AGENTS.md`，不按这里。
- **不提交**：本机绝对路径、密钥、任何项目的数据或图纸。例子一律写成 `<本机路径>` 这类占位。
