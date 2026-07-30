# 本地任务关系仪表盘

这是一个只读的 Windows 本地仪表盘。它从任意目标项目的 TASK、TASK_BOARD、Git 和 linked Worktree 派生快照，帮助查看完整任务关系、下一动作、并行候选、强制串行、阻塞原因和证据来源。目标项目与 ai-dev-flow Skill 可以位于不同目录；仪表盘不会修改 TASK、执行写 Git、创建 Worktree 或授予任何 authority。

## 环境要求

- Windows 11；
- Python 3.11 或更新版本；
- Git 2.40 或更新版本；
- 现代浏览器。

使用完整 Skill 安装包时不需要 Node.js、npm、Vite 或本源码仓库。只有开发、重建分发运行时和运行前端回归时，才需要 Node.js 22、Google Chrome 和锁文件中的既有依赖：

```powershell
Set-Location dashboard/frontend
npm ci
Set-Location ../..
```

该命令不会新增或升级依赖；`node_modules/` 已被 Git 忽略。

## 从已安装 Skill 启动（推荐）

完整安装包包含 Python 后端和已构建前端。目标项目不需要 `skills/ai-dev-flow`：

```powershell
py -3 -B -X utf8 "C:\Users\<user>\.agents\skills\ai-dev-flow\scripts\dashboard.py" `
  --project-root "D:\projects\CADCat"
```

入口会：

1. 使用入口所在 Skill，或按 `--skill-root` 指定外部 Skill；
2. 检查 Skill `VERSION`、Workflow Contract schema 和项目中显式 Scheduling schema；
3. 由操作系统分配一个可用 `127.0.0.1` 端口，同源提供页面、API 与 SSE；
4. 创建项目级、实例级独立运行目录并打开页面。

`--port 0` 为默认自动端口；也可用 `--port 9001` 固定当前实例。不希望自动打开浏览器时加 `--no-open`。显式端口被占用时只停止本次启动，不会结束或替换已有实例。

## 从源码仓库启动（向后兼容）

旧入口继续可用，并新增外部 Skill 与自动端口：

```powershell
py -3 -B -X utf8 dashboard/integration/launcher.py `
  --project-root "D:\projects\CADCat" `
  --skill-root "C:\Users\<user>\.agents\skills\ai-dev-flow"
```

该开发入口仍使用源码后端与 Vite，因此需要先执行 `npm ci`。省略端口时会自动分配；原有 `--backend-port 8765 --frontend-port 5173` 显式写法继续支持。

## 停止

在对应启动窗口按 `Ctrl+C`。安装版单进程只关闭当前实例并清理自己的状态目录；其他项目实例继续运行。停止后不应有后台 TASK 写入、自动 Worktree、文件锁、监听端口或子进程残留。

## 构建 Skill 分发运行时

生成器先构建前端，再把标准库后端、严格合同和不含 source map 的静态文件同步到 `skills/ai-dev-flow/dashboard/`，最后生成逐文件 SHA256 manifest：

```powershell
py -3 -B -X utf8 dashboard/integration/build_skill_runtime.py
py -3 -B -X utf8 dashboard/integration/build_skill_runtime.py --check
```

`--check` 不修改文件；任何源码、静态文件、manifest 或文件集合漂移都会失败。不要手工编辑生成目录。

## 验证

从项目根目录运行只读 artifact 门禁和 Python 集成测试：

```powershell
py -3 -B -X utf8 dashboard/integration/artifact_guard.py --project-root .
py -3 -B -X utf8 -m unittest discover -s dashboard/integration/tests -p "test_*.py" -v
```

artifact 报告把 `baseline_preserved`、`accepted_ok` 与
`candidate_consistent` 分开：未获独立授权的候选即使内部哈希一致，
`accepted_ok` / `ok` 仍保持 `false`，命令返回非零；这不是自动验收，
而是防止候选通过自填哈希改写既有 Accepted 基线。候选哈希使用 Git
clean-filter 后的 blob identity，不受 Windows `core.autocrlf` 影响。

运行真实 Chrome 联调：

```powershell
$env:DASHBOARD_PYTHON = (Get-Command py.exe).Source
Set-Location dashboard/frontend
npx playwright test -c ../integration/playwright.config.mjs
Set-Location ../..
```

真实联调会在 `dashboard/integration/artifacts/screenshots/` 保存当前项目
1366×768、1920×1080、2560×1440 三种合同视口的截图。该目录只保存本机验证证据，
已被 Git 忽略。

运行 Windows 参考性能门禁（正式收据需分别执行两次，并使用不同输出目录）：

```powershell
py -3.12 -B -X utf8 dashboard/integration/benchmark.py --output-dir dashboard/integration/artifacts/benchmark/run1
py -3.12 -B -X utf8 dashboard/integration/benchmark.py --output-dir dashboard/integration/artifacts/benchmark/run2
```

每轮都会保留 30 个冷启动、稳定保存到 SSE、API 序列化原始样本，以及 P50/P95、
payload、峰值 RSS 和本机环境。任一冻结门槛或参考环境检查不通过时命令返回失败。
冻结参考环境只接受 Python 3.11 或 3.12；若使用 3.11，把上面的 `-3.12` 改为
`-3.11`。Python 3.13 等其他环境的结果只能作为补充，不能用于首版性能门禁。

如果 `py.exe` 的默认解释器低于 3.11，请把 `DASHBOARD_PYTHON` 设为实际 Python 3.11+ 的 `python.exe` 绝对路径。

完整回归还应运行后端、前端和既有 workflow 测试；命令以本任务 `docs/tasks/DASHBOARD-INTEGRATE-001.md` 的验证收据为准。

## 安全边界

- 页面与 API 仅监听 IPv4 loopback，不提供公网或局域网服务；
- 浏览器只发起同源 GET 与 SSE；没有写接口、CORS、账号、云同步或遥测；
- 安装版页面、API 与 SSE 使用同一随机或显式端口，不经过开发代理；静态服务器限制路径和文件类型，不提供 source map；
- 项目事实与 Skill Reader 分开冻结；多个实例不共享 Python 模块、端口、实例 ID 或运行状态目录；
- 运行中 Skill 指纹变化只设置 `restart_required` 并提示重启，不热加载新 Reader；
- 集成 Vite 配置只把代理请求的 Host 正规化为真实后端 loopback 端口，以满足后端 Host allowlist；它不放宽后端方法、路径、项目根或 schema 校验；
- 前端、后端和共享 contracts 是 Accepted artifact；集成任务通过逐文件 SHA256 门禁保护它们，不在集成层复制或改写业务实现。

## 已知限制

- 需要保留启动窗口；没有系统服务或自动更新；
- 当前正式 `v0.9.0` 发布包尚未包含该安装运行时；只有包含 `dashboard/runtime-manifest.json` 的后续完整 Skill 包可使用推荐入口；
- 自动测试不能替代 UA6：用户仍需用真实项目判断关系图是否直观，并回归原 TASK / TASK_BOARD / workflow_lint 使用习惯；
- 仪表盘展示的是只读派生事实。自动验证、Review、UA、Accepted、commit、merge、release、delivery 和 Closed 始终相互独立；
- 浏览器关闭不等于服务停止，必须回到启动窗口按 `Ctrl+C`。
