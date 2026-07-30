# 本地任务关系仪表盘

这是一个只读的 Windows 本地仪表盘。它从当前 ai-dev-flow 项目的 TASK、TASK_BOARD、Git 和 linked Worktree 派生快照，帮助查看完整任务关系、下一动作、并行候选、强制串行、阻塞原因和证据来源。仪表盘不会修改 TASK、执行 Git、创建 Worktree 或授予任何 authority。

## 环境要求

- Windows 11；
- Python 3.11 或更新版本；
- Node.js 22 与 npm；
- Git 2.40 或更新版本；
- Google Chrome（用于浏览器验证）；
- `dashboard/frontend/package-lock.json` 中已冻结的前端依赖。

首次在新的 Worktree 使用时，仅安装锁文件中已有依赖：

```powershell
Set-Location dashboard/frontend
npm ci
Set-Location ../..
```

该命令不会新增或升级依赖；`node_modules/` 已被 Git 忽略。

## 启动

在 ai-dev-flow 项目根目录执行：

```powershell
py -3 -B -X utf8 dashboard/integration/launcher.py --project-root .
```

launcher 会：

1. 只绑定 `127.0.0.1:8765`（后端）和 `127.0.0.1:5173`（页面）；
2. 启动真实只读后端与前端；
3. 等待 `/api/v1/snapshot` 发布首个只读快照；
4. 打开 `http://127.0.0.1:5173/`。

不希望自动打开浏览器时加 `--no-open`。端口被占用时 launcher 会直接失败，不会结束或替换已有进程。

## 停止

在启动窗口按 `Ctrl+C`。launcher 会依次停止前端和后端；停止后不应有后台 TASK 写入、自动 Worktree、文件锁或 5173/8765 监听残留。

## 验证

从项目根目录运行只读 artifact 门禁和 Python 集成测试：

```powershell
py -3 -B -X utf8 dashboard/integration/artifact_guard.py --project-root .
py -3 -B -X utf8 -m unittest discover -s dashboard/integration/tests -p "test_*.py" -v
```

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
- 集成 Vite 配置只把代理请求的 Host 正规化为真实后端 loopback 端口，以满足后端 Host allowlist；它不放宽后端方法、路径、项目根或 schema 校验；
- 前端、后端和共享 contracts 是 Accepted artifact；集成任务通过逐文件 SHA256 门禁保护它们，不在集成层复制或改写业务实现。

## 已知限制

- 这是本地开发式启动，需要保留启动窗口；没有安装器、系统服务或自动更新；
- 自动测试不能替代 UA6：用户仍需用真实项目判断关系图是否直观，并回归原 TASK / TASK_BOARD / workflow_lint 使用习惯；
- 仪表盘展示的是只读派生事实。自动验证、Review、UA、Accepted、commit、merge、release、delivery 和 Closed 始终相互独立；
- 浏览器关闭不等于服务停止，必须回到启动窗口按 `Ctrl+C`。
