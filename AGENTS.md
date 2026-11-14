# ai-dev-flow 仓库

开发流程 skill 本身。这个仓库也按它自己管：开发相关请求从 `skills/ai-dev-flow/SKILL.md` 进入。结构和版本历史见 `README.md`。

## 项目事实

- **信任等级**：未写，按总览第 4 节为 L0（合并前问用户）。等级由用户在这里改。
- **队列**：`docs/queue.md`，只由编排会话维护。
- **检查**：
  - 改了 `skills/ai-dev-flow/scripts/` 下的 `status.ps1`、`daily.ps1`、`notify.ps1` 或 `watch.ps1`：跑 `pwsh -NoProfile -File tests/status.tests.ps1`，退出码 0 才算通过。测试里 notify 只走 `-DryRun`；真的弹通知、推到手机，要在本机实发一次。
  - 改了 `status.ps1` 解析队列或别的文档的写法：另外对本机总览清单只读跑一次 `status.ps1 -Config <总览仓库>/projects.json -All -Json`，看真实队列的结果对不对，写进提交正文。夹具里的写法总是比真实队列少（10-31、11-05、11-06、11-08 四次都是真实写法没考虑到）。
  - 改了 `skills/ai-dev-flow/scripts/dispatch.ps1`：跑 `pwsh -NoProfile -File tests/dispatch.tests.ps1`，退出码 0 才算通过。它用假的执行方，只覆盖 400 重试、审查 worktree 清理、Claude 执行方去掉登录变量和模型参数，其余部分（包括真的 `claude -p`、`codex exec` 能不能跑通）还要靠独立审查实跑。
  - 改了 `skills/ai-dev-flow/scripts/direction.ps1`：跑 `pwsh -NoProfile -File tests/direction.tests.ps1` 和 `tests/status.tests.ps1`，退出码 0 才算通过。
  - 改了 `skills/ai-dev-flow/scripts/check-md.ps1`：跑 `pwsh -NoProfile -File tests/check-md.tests.ps1`，退出码 0 才算通过。
  - 改了 `skills/ai-dev-flow/scripts/trunk-check.ps1`：跑 `pwsh -NoProfile -File tests/trunk-check.tests.ps1`，退出码 0 才算通过。真的被 `watch.ps1` 拉起、在后台跑完一个项目的全量，要在本机实跑一次。
  - 改了 `skills/ai-dev-flow/scripts/verify-ledger.ps1`：跑 `pwsh -NoProfile -File tests/verify-ledger.tests.ps1`，退出码 0 才算通过。
  - 改了 `skills/ai-dev-flow/scripts/land-check.ps1`：跑 `pwsh -NoProfile -File tests/land-check.tests.ps1`，退出码 0 才算通过。
  - 改了 `skills/ai-dev-flow/scripts/launch.ps1`：跑 `pwsh -NoProfile -File tests/launch.tests.ps1`，退出码 0 才算通过。它用假的 `claude` 命令；真的开后台会话、看它用哪个账号，要在本机实开一次。
  - 改了 `skills/ai-dev-flow/scripts/archive-requests.ps1`：跑 `pwsh -NoProfile -File tests/archive-requests.tests.ps1`，退出码 0 才算通过。
  - 改了 `skills/ai-dev-flow/scripts/cleanup.ps1`：跑 `pwsh -NoProfile -File tests/cleanup.tests.ps1`，退出码 0 才算通过。
  - **这份检查清单就是"改了哪里跑哪些"对照表**（`skills/ai-dev-flow/modules/harness.md` 第 2 节第 1 条）：合并前只跑上面按改动列出的那几条；没列到的脚本、`tests/run-all.ps1` 本身或几个脚本都改了，跑下面的全部检查。合并后的全量由总览清单里这个项目的 `trunkVerify` 在本机后台跑；清单里还没配 `trunkVerify` 时，这条不生效，照旧跑全部检查。
  - 全部检查（`tests/*.tests.ps1` 和 `check-md.ps1`）并行跑：`pwsh -NoProfile -File tests/run-all.ps1`，退出码 0 才算通过，最后一行是快检用时（2026-11-11 空机器上 401 秒；同时跑两份时能到 14 分钟，量用时要在机器空着时量）；对照表选不出来时验证方跑这一条。改了 `tests/run-all.ps1` 另跑 `tests/run-all.tests.ps1`。
  - 改了任何 `.md`：跑 `pwsh -NoProfile -File skills/ai-dev-flow/scripts/check-md.ps1`，退出码 0 才算通过。
  - 只改文档的，另按 `skills/ai-dev-flow/modules/verify.md` 第 1 节逐条核对文档里写的路径、命令和章节引用。
- **安装同步**：合进 `main` 以后，把 `skills/` 下的 `ai-dev-flow`、`next`、`week` 复制到 `~/.agents/skills/`（见 README 的安装一节），再用 `diff -rq` 逐个确认两边一致。Claude Code 的 `~/.claude/skills/<名字>` 是指向它们的目录链接，不用另外复制。
- **云端会话**：这个仓库有远程，可以在云端会话里做。云端没有用户级 skill，开头写"按 `skills/next/SKILL.md` 做 #n"；云端只推分支，回到本地用 `/next 收云端` 合并（`skills/next/cloud.md`）。
- **推送**（用户 2026-10-29 定）：改动审查通过、合进 `main`、同步到本机安装之后，把 `main` 和 `refs/notes/verify` 推到 `origin`。推之前做两件事：
  - 看 `git log origin/main..main`，确认要推的提交都审过；
  - 查一遍提交和 note，确认没有本机路径和密钥。
  
  这是公开仓库。其他项目的推送规则看各自的 `AGENTS.md`，不按这里。
- **不提交**：本机绝对路径、密钥、任何项目的数据或图纸。例子一律写成 `<本机路径>` 这类占位。
