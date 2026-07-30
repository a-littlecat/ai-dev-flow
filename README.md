# ai-dev-flow

[English](README.en.md)

`ai-dev-flow` 是一个按风险启用的 AI 开发治理 Skill，并附带只读的本地任务关系 Dashboard。

它解决两件事：

1. 小任务不强行套完整流程；高风险、跨会话、真实环境和交付任务才启用 TASK、独立 Review 与权限门禁。
2. 把项目中的 TASK、TASK_BOARD、Git 和 Worktree 事实变成可交互关系图，帮助判断下一步、上下游、并行候选和待决事项。

## v0.9.1 新版特性

- **跨项目使用**：项目目录与 Skill 安装目录彻底分离，不再要求每个项目复制或链接 `skills/ai-dev-flow`。
- **可独立运行**：Skill 包内含 Dashboard 后端、已构建前端和启动脚本；日常使用不需要保留本源码仓库，也不需要 Node.js。
- **多实例隔离**：默认自动选择可用端口；每个项目有独立实例 ID、运行目录、状态和缓存，停止一个实例不会影响另一个。
- **版本固定**：启动时检查 Skill 版本、Workflow Contract schema、Scheduling schema 和 Dashboard 支持范围；运行中检测到 Skill 更新会提示重启，不混用新旧规则。
- **实时只读**：TASK、TASK_BOARD、Git dirty、分支、HEAD 和 Worktree 变化通过 SSE 自动刷新。
- **安全边界不变**：仅监听 loopback，没有写 API，不修改项目、Skill 或 Git，不创建 Worktree，也不授予验收、提交、合并、发布或 Closed 权限。

## 工作方式

```text
项目目录                         已安装 Skill
├─ docs/tasks/*.md              ├─ Workflow Contract Reader
├─ docs/TASK_BOARD.md           ├─ schema 与治理规则
└─ .git / Worktree              └─ Dashboard 运行时与静态前端
          │                                  │
          └──────── 只读组合 ────────────────┘
                           │
                 http://127.0.0.1:<动态端口>
```

TASK 是详细事实源，TASK_BOARD 是投影。Dashboard 只展示可由当前证据确定的结果；证据不足时保持 `unknown`，不会猜测任务可并行或必须串行。

## 快速开始

### 从已安装 Skill 启动

支持基线为 Windows 11、Python 3.11+、Git 2.40+ 和现代浏览器。项目必须是 Git 仓库，并至少包含一个 `docs/tasks/*.md` TASK；推荐同时维护 `docs/TASK_BOARD.md`。安装版不需要 Node.js。

```powershell
py -3 -B -X utf8 `
  "$env:USERPROFILE\.agents\skills\ai-dev-flow\scripts\dashboard.py" `
  --project-root "D:\projects\your-project"
```

启动器会自动发现当前 Skill 根目录并选择可用端口。需要显式指定时：

```powershell
py -3 -B -X utf8 `
  "$env:USERPROFILE\.agents\skills\ai-dev-flow\scripts\dashboard.py" `
  --project-root "D:\projects\your-project" `
  --skill-root "$env:USERPROFILE\.agents\skills\ai-dev-flow" `
  --port 5084
```

浏览器只访问输出中的 `127.0.0.1` 地址。按 `Ctrl+C` 只停止当前实例。

### 从源码仓库启动

源码入口额外需要 Node.js 22。首次在干净检出中运行前先安装锁定的前端依赖：

```powershell
Set-Location dashboard/frontend
npm ci
Set-Location ../..
```

```powershell
py -3 -B -X utf8 dashboard/integration/launcher.py `
  --project-root "D:\projects\your-project"
```

源码入口继续兼容，也支持 `--skill-root`、自动端口和实例隔离。

## 安装或更新 Skill

把仓库中的 `skills/ai-dev-flow/` 复制到 Harness 的 Skill 目录，例如：

```text
C:\Users\<user>\.agents\skills\ai-dev-flow
```

完整 Skill 目录已经包含 Dashboard 运行时。目标项目中无需再创建 Skill 副本、junction 或 symlink。

## 治理路由

| 结果 | 适用情况 | 默认行为 |
|---|---|---|
| `DoNotUseSkill` | 低风险、单会话、验证完整 | 不建 TASK，不调用 Reviewer |
| `Tracked` | 跨会话、范围较大或需要留证 | 使用 TASK；风险命中时只读 Review |
| `Controlled` | D 级、高风险、真实环境或交付动作 | 完整 TASK；关键动作前独立 Review |
| `Blocked` | 输入、权限、能力或证据不足 | 停止并报告最小阻塞信息 |

准确规则只维护在 `skills/ai-dev-flow/references/CORE.md` 的 `POLICY_JSON` 中。

## 版本与兼容性

- Skill：`0.9.1`
- Dashboard 支持的 Skill 系列：`0.9.x`
- Workflow Contract：`adf/v0.7.0`
- Scheduling：`ai-dev-flow/scheduling/v1`
- 支持环境：`Windows 11`、`Git 2.40+`、现代浏览器
- Python：`3.11+`

升级 Skill 后，已经运行的 Dashboard 会保持启动时版本并提示重启。

## 开发验证

```powershell
py -3 -B -X utf8 -m unittest discover -s dashboard/backend/tests -p "test_*.py"
py -3 -B -X utf8 -m unittest discover -s dashboard/integration/tests -p "test_*.py"
py -3 -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py"
py -3 -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format human

cd dashboard/frontend
npm ci
npm run verify
```

更多实现与测试说明见 [Dashboard 文档](dashboard/README.md) 和 [Skill 手册](skills/ai-dev-flow/README.md)。

## License

MIT License，详见 [LICENSE](LICENSE)。
