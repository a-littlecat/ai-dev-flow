# ai-dev-flow

[English](README.en.md)

`ai-dev-flow` 是一个按风险启用的 AI 开发治理 Skill，并附带只读的本地任务关系 Dashboard。

它解决两件事：

1. 小任务不强行套完整流程；高风险、跨会话、真实环境和交付任务才启用 TASK、独立 Review 与权限门禁。
2. 把项目中的 TASK、TASK_BOARD、Git 和 Worktree 事实变成可交互关系图，帮助判断下一步、上下游、并行候选和待决事项。

## v0.9.2 新版特性

- **Codex Goal 中文预设**：支持“启动受控目标”“启动自动落地目标”“我去休息，自动修好并交付”等入口；Goal 负责持续运行，Skill 继续负责范围、验证、Review、UA 和交付权限。
- **历史任务收口**：修复 6 份旧 Contract 的可解析性；27 个历史任务中 24 个按完整证据 Closed，3 个缺少独立 UA3 的任务保留 UA Deferred 并将任务合法收口为 Cancelled。
- **开发依赖安全更新**：升级 Vite、Vitest、ESLint 与 TypeScript ESLint；保持 Dashboard 89 个浏览器用例和 91 个前端单元测试通过，`npm audit` 为 0。
- **跨项目 Dashboard 保持兼容**：继续提供自包含、只读、多实例隔离和自动端口的安装运行时；日常使用无需 Node.js。
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

源码入口额外需要 Node.js 22.13+（仅 22.x）或 Node.js 24+。首次在干净检出中运行前先安装锁定的前端依赖：

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

- Skill：`0.9.2`
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
