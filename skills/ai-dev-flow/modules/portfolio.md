# 多项目总览

用户同时推进几个项目时使用：用户说"早报""各项目怎么样""周会"（`/week`）"新开一个项目""X 先停"，或者你在总览仓库里被打开。目标：用户只看一页就知道全部项目的情况，花的注意力少；每个项目照常各自推进。

你在这里是**指挥台**：收状态、汇总、按用户的意图排优先级和分额度、把跨项目的决定转给项目。不写任何项目的代码，不替项目派活、合并。

## 1. 结构

- **项目不设常驻主会话**：用户在项目里开会话、发 `/next`，会话按队列一直做到需要用户才收尾（`skills/next/SKILL.md`）。各项目各管各的队列、verify、信任等级和复盘。关联项目之间按 `orchestrate.md` 第 6 节靠接口约定连接。互不相关的项目也一样，只是没有依赖。
- **总览也不设常驻会话**：每天的状态由计划任务跑脚本生成一页（第 6 节），不花模型额度；只在周会（`/week`）和要做跨项目决定时开一个会话，用完就关。
- **一个总览仓库**，只在本地，不加远程。它只放下面这些，不放任何项目的代码、数据、图纸和密钥：

| 文件 | 内容 | 谁写 |
|---|---|---|
| `AGENTS.md` | 入口：写明按本模块工作，列出下面这些文件 | 你 |
| `INTENT.md` | 用户的意图：各项目的优先级和本周目标、长期授权、额度分配、上限、不做的事 | 你起草，用户确认 |
| `projects.json` | 项目清单，格式见第 2 节 | 你 |
| `decisions.md` | 用户做过的跨项目决定，一行一条，带日期和用户原话 | 你 |
| `LESSONS.md` | 跨项目教训，见第 7 节 | 你 |
| `digest/<日期>.md` | 周报 | 你 |
| `scripts/status.ps1` | 收状态的入口，转调本 skill 的 `scripts/status.ps1` | — |

总览仓库只在本地，清单里可以写本机路径；这是总览第 5 节"不提交本机绝对路径"唯一的例外。总览仓库永远不 push。

入口脚本照 `orchestrate.md` 里派活入口的写法，几行转调；多一行 `Stop`，参数写错时入口也返回非零：

```powershell
# 收状态入口：转调 ai-dev-flow 的通用状态脚本，项目清单在 ../projects.json。参数见 ai-dev-flow modules/portfolio.md。
$ErrorActionPreference = 'Stop'
$skill = if ($env:AI_DEV_FLOW) { $env:AI_DEV_FLOW } else { Join-Path $HOME '.agents/skills/ai-dev-flow' }
$script = Join-Path $skill 'scripts/status.ps1'
if (-not (Test-Path -LiteralPath $script)) { throw "ai-dev-flow skill not found: $script (set AI_DEV_FLOW)" }
& $script @args -Config (Join-Path $PSScriptRoot '../projects.json')
exit $LASTEXITCODE
```

## 2. 项目清单

```json
{
  "projects": [
    { "name": "导图", "path": "<本机路径>", "status": "推进中", "priority": 1, "trunk": "master",
      "queue": "docs/queue.md", "dependsOn": ["引擎"], "note": "<一句话：这个项目是什么>",
      "goals": [{ "text": "第 22 项包 A", "items": ["22"] }, { "text": "评分口径切到 v2", "done": false }] }
  ]
}
```

`name`、`path`、`status` 必填；`trunk` 不写就用主检出当前所在的分支；`queue` 不写就是 `docs/queue.md`。信任等级不写在清单里，脚本从项目 `AGENTS.md` 的"信任等级 Lx"读，等级只有一个出处。

`goals` 是本周目标，由周会写。`items` 里的队列项都"完成"时，状态页自动打勾；挂不到队列项的目标，由周会把 `done` 改成 `true`。

| 状态 | 含义 | 总览怎么对待 |
|---|---|---|
| 推进中 | 用户发 `/next` 按队列推进 | 进状态页、占额度 |
| 维护 | 只处理报上来的问题 | 只看提交数、队列和待用户项 |
| 暂停 | 不推进 | 只列名字 |

- **推进中的项目有上限**，写在 `INTENT.md`，默认 4 个。要超过时先请用户选一个转维护或暂停，这是方向问题。
- **新开项目**：清单加一行，`decisions.md` 记一条。项目里没有 `AGENTS.md`、verify 或队列的，告诉用户在那个项目发 `/next`，第一项就是按 `harness.md` 搭。
- **暂停**：正在做的会话按 `/next` 第 6 节收尾；清单改状态，`decisions.md` 记一条。恢复时反过来。

## 3. 收状态

脚本收事实，你做判断。不要自己挨个进项目读 git log 和队列，那会白花额度。

```
pwsh -NoProfile -File scripts/status.ps1             # 推进中的全量，维护中的简要，暂停的列名字
pwsh -NoProfile -File scripts/status.ps1 -Mark       # 周会时用：记下各项目主干位置，下次从这里算新提交
pwsh -NoProfile -File scripts/status.ps1 -Lessons    # 附上各项目的教训标题和 Seen
pwsh -NoProfile -File scripts/status.ps1 -Project '<名字>,<名字>' -Since '7 days ago'
```

每个项目列出：主干新提交（默认从上次 `-Mark` 算，没有就是近 24 小时）、未复盘的提交数（`LESSONS.md` 的 `reviewed-through` 之后）、队列各状态的项数、可领的项数和每一条待用户项、本周目标完成几条、最后活动时间、最近一份复盘摘要的北极星和返工行、worktree 和已合并分支的个数、未提交改动；清单或项目有问题时写"提示"。`LESSONS.md` 里 Seen 达到 3、又没写"升级："一行的教训，和 `docs/requests.md` 里状态"待转"或没写状态的请求，也写成"提示"（第 7 节）。7 天内派出去、没有退出记录、进程也不在了、同一分支后来也没再派过的运行，提示"派出去的运行死了"。推进中的项目有"在做"的项，却超过 `-StaleMinutes`（默认 60）分钟没有动静的，提示"可能停滞"。待用户项的状态格超过 300 字的，提示"写成了过程记录"；写着不急、先停、暂停、等…提出这类话的，提示"像是搁置"，用户说过先不做的应改成 `搁置（<恢复条件>）`（`/next` 第 5 节），`-Json` 里是每项的 `Hint`。加 `-Json` 给机器读。脚本只读：不 fetch，也不刷新项目的 Git 索引，不会和项目会话的提交抢锁。

脚本看不到会话本身是不是还在跑。用户在桌面应用的侧边栏里看得到；你只按脚本的结果说，不猜。

## 4. 统一收件箱

状态页（第 6 节）就是收件箱：所有项目的待用户项按优先级列在一处。每条的问题和推荐答案写在队列那一项里（`/next` 第 5 节），页面照原样显示。

- **项目里的决定在项目里答**：用户到那个项目新建会话，发 `/next #编号 <答复>`，会话记下答复后接着做。不经过总览转达，少一道传话，也就少一处出错。
- **跨项目的决定在周会里定**（优先级、额度、接口、谁先做）。总览会话里给用户的问题，一次最多 3 条（`INTENT.md` 可改），其余写"另有 N 条排着"。
- **转达**：跨项目的决定定下来后，写进受影响项目的 `docs/requests.md`（与 `orchestrate.md` 第 6 节同一个文件），由那边下次发 `/next` 时转进自己的队列。你不直接改项目的队列和代码。
- 消息只能转达决定，不能代替权限审批：项目会话里弹出的审批，仍要用户在那个会话里点。告诉用户去哪个会话、点什么。
- 跨项目的决定（优先级、额度、谁先做）记进 `decisions.md`。

## 5. 意图和额度

- `INTENT.md` 是跨项目意图的唯一出处。用户在总览里说的方向变化，你先改 `INTENT.md`，再转给受影响的项目。意图只从总览流向项目；项目发现意图要改，写进汇报，由用户在总览里定。
- **额度**：同一个订阅的额度是所有会话共用的。按 `INTENT.md` 的分配，优先级低的项目少派、不派；这作为一条请求转给那个项目，由那边按自己 `AGENTS.md` 的额度规则执行。
- **依赖**：使用方的北极星卡在提供方的某一项时，在周报里把那一项排到前面，并写进提供方的 `docs/requests.md`。

## 6. 每天的状态页和通知

每天的状态不靠模型写，靠计划任务跑脚本：

```
pwsh -NoProfile -File <skill>/scripts/daily.ps1 -Config <总览仓库>/projects.json
```

- 生成一页 HTML（默认 `%LOCALAPPDATA%\ai-dev-flow\status.html`），顶上一句话总结，下面固定三块：① 要你做（等你定的、可能停了的、空着能开工的，每条写好要发的命令）；② 本周目标；③ 各项目，每个一张卡：状态标签（可能停了 / 等你 / 在做 / 空着），加"现在、进度、北极星、接下来、最近完成"五行，计数、提交、清理和原始提示收进"细节"。
- 然后发一条系统通知，点开就是这一页。有待用户的项或可能停滞的项目时，同时推到手机；但和上次推过的完全一样时只弹系统通知，不再推手机（记录在 `%LOCALAPPDATA%\ai-dev-flow\daily-state.json`）。"像是搁置"的待用户项不算要你管的事，单列在①里，附改成搁置的命令。推进中的项目没有在做的项、但 `-StaleMinutes` 内有动静的标"刚有动静"，不算空着。
- 用 Windows 计划任务每天跑两次，默认 9:00 和 18:00。这属于持久配置，第一次要用户同意，同意后写进总览的 `AGENTS.md`。电脑关着就不跑，下次开机后按计划任务的"错过后尽快运行"补跑。
- 停滞另外每 15 分钟查一次：`scripts/watch.ps1 -Config <总览仓库>/projects.json`，也用计划任务跑（默认 9:00–23:00 每 15 分钟）。只有项目新变成"可能停滞"时才发一条 `stuck` 通知（会推到手机），停住后最晚约 75 分钟收到，同一次停滞不重复发；记录在 `%LOCALAPPDATA%\ai-dev-flow\watch-state.json`。不花模型额度。
- 计划任务用 `conhost.exe --headless <pwsh 的完整路径> -NoProfile -File ...` 启动，不直接启动 pwsh：`-WindowStyle Hidden` 挡不住窗口先闪一下，每 15 分钟闪一次会打扰用户。

通知统一走 `scripts/notify.ps1`：

- 渠道和 key 放在本机配置里（默认 `%APPDATA%\ai-dev-flow\notify.json`），不入库：
  ```json
  { "bark": "https://api.day.app/<key>", "barkLevels": ["user", "stuck"], "toast": true }
  ```
- 级别：`info` 提醒、`done` 完成、`user` 要用户看或定、`stuck` 卡住或停在安全点。系统通知每次都弹；`barkLevels` 里的级别才推到手机，默认只推要用户出手的两类。
- `/next` 每次收尾都会发一条。Claude Code 的 `Notification` hook 也接到它（`notify.ps1 -Hook`），按事件类型分：等权限、等回答的弹系统通知；回复完一分钟没输入的提醒（`idle_prompt`）不发；额度重置后没能自动继续的（`quota_auto_resume_stale`、`quota_auto_resume_disabled`）按 `stuck` 发，会推到手机。改 hook 属于安全设置，用户同意才改。
- 想在手机上直接批权限、回问题，用 Claude Code 自带的 Remote Control（桌面端 设置 > Code 里打开"Connect new sessions to Remote Control"，再在 `/config` 打开 "Push when actions required"）。它只管连着的会话，会话停了、额度停了它发不出来，这两种仍靠上面的 hook 和 `watch.ps1`。

## 7. 跨项目教训

- 周会时加 `-Lessons` 看各项目的教训。同一条规则在 2 个以上项目出现（措辞不同、意思相同也算），写进总览的 `LESSONS.md`，注明出现在哪些项目、各自的 Seen。
- 跨项目教训不在每个项目各升一遍，按顺序选第一个做得到的：
  1. 本 skill 的脚本或模板：让所有项目自动遵守
  2. 用户级的 hook 或权限规则
  3. 本 skill 某个模块里的一条
- 改 skill 是 ai-dev-flow 仓库的一项改动，作为一条请求交给它；改用户级配置属于安全设置，在"建议"里给出要改的文件和规则原文，用户同意才改。
- **项目可以直接写请求，不等周会**：项目复盘时某条教训的 Seen 达到 3，而它该改的是 skill（换个项目也一样会犯），或者项目用户定了一条想让所有项目都照做的规矩，就由那个项目的会话直接写进 ai-dev-flow 仓库的 `docs/requests.md`：
  - 仓库路径看总览 `projects.json` 里 ai-dev-flow 那一行；清单里没有就写进汇报的"要你做"，不猜路径。
  - 照那份文件已有的格式写一个 `## <日期> 来自一个推进中项目：<主题>` 小节，含"现象""用户决定"（没有就写"无"）"请求"，状态写"待转"；不写项目名和本机路径，那是公开仓库。
  - 只改这一个文件，单独提交（`requests: <主题>`）；那边有未提交的改动或正在提交时，等一会再提交，不动别的文件。
  - 回到本项目，在那条教训里加一行 `升级：已请求 ai-dev-flow（<日期>）`。ai-dev-flow 发出带这条的版本、本机装好之后，下次复盘把它从 `LESSONS.md` 删掉。
- 状态脚本把 Seen 达到 3 还没写"升级："的教训，和各项目 `docs/requests.md` 里还没转的请求（ai-dev-flow 自己的也算）都列进"提示"，不靠周会才看见。
- 各项目复盘摘要的"审批"行里同一类操作反复弹的，同样在"建议"里给一条具体的权限规则。

## 8. 周会

每周一次，用户在总览仓库里发 `/week`，步骤见 `skills/week/SKILL.md`：

- 每个推进中的项目：本周合并数、北极星变化、本周目标完成几条、返工、队列还剩多少。
- 建议：下周目标（写进 `goals`）、哪个转维护或暂停、优先级怎么调、`INTENT.md` 里过时的条目、清单里路径不存在或长期没动的项目（只列，不删）。
- 用户定了的写进 `INTENT.md`、`projects.json` 和 `decisions.md`；周报写进 `digest/<日期>.md`。

## 9. 不做的事

- 不在总览会话里改项目代码、派项目的活、合项目的分支、改项目的队列。
- 不替用户做任何项目的单向门授权；转达授权时引用用户原话。
- 不把 sha、命令、diff 搬进周报，用户问了再答。
- 总览仓库不推远程，不放项目的数据和密钥。
