# 自动推进

用户说"继续推进""自动推进"，或项目 `AGENTS.md` 已授权自动推进时使用。目标：用户不用点、不用盯，队列里的项一项接一项做下去，只在第 5 节的情况找用户。

你在这里是**编排者**：只负责分派、核对、发起验证和排合并顺序，不自己写业务代码。业务代码交给子 agent。

**日常推进用 `/next`**：用户在项目里开会话、发 `/next`，会话按队列一项接一项往下做，一直做到需要用户（要用户定、卡住、额度快用完或上下文太长）才收尾（见 `skills/next/SKILL.md`）。防止无声停下靠的是两条：派出去的活等到结束才收工，停下时一定发通知。进度都在队列里，换账号、换会话都能接着做。本模块讲的是一个会话内部怎么派活、等待和接力。用户要一个会话连续推进时，也按本模块做，第 3 节"等到结束"和第 4 节的收尾同样适用。

## 1. 前提

- 项目是 Git 仓库，主干干净。没有 Git 时，先问用户要不要初始化，说明好处是能并行、能回滚。初始化时：
  - 只在本地，不加远程，除非用户另外授权。
  - 需要逐字节保留的文件（证据、样例输出）用 `.gitattributes` 写 `* -text`，避免换行转换改变散列。
- 项目有 verify 命令。没有的，第一项就是按 `harness.md` 把它搭起来。
- 有队列，而且下一项的方向已经定了。方向没定的，先按总览第 3 节问。

## 2. 队列

- 有远程时用 issues（`gh` 可以读写，天然支持并发）；没有远程时用 `docs/queue.md`，一行一项，只由你写。
- 每一项写：目标、完成标准、档位、依赖、状态（待做 / 在做 / 待验证 / 待用户 / 待放行 / 完成 / 搁置；待放行见 `skills/next/SKILL.md` 第 4 节）、负责的子 agent。
- 方向原型和方向的正式项，目标开头写 `[方向原型 <方向名>]`、`[方向 <方向名>]`（`direction.md` 第 2 节）。
- 用户在对话里提的新想法、复盘发现的问题、验证方报的、实际使用中会碰到的 P2（`verify.md` 第 3 节）、主干上原来就红的测试，都进队列。

## 3. 派活

- 用后台子 agent 加 worktree 隔离（Agent 工具：`isolation: "worktree"`，后台运行），任何轮次都能派，不用用户点击。
- 会话由用户开（发 `/next`），你不替用户开会话。桌面应用规定，由通知触发的轮次只能提议会话卡片，要用户点了才开，所以这条路靠不住。
- 所有项目同时开着的会话，合计不超过总览 `INTENT.md` 写的上限（默认 3 个）。多了，用户看不过来，额度也撑不住。
- 子 agent 的 worktree 默认从仓库默认分支开出，见 Claude Code 设置 `worktree.baseRef`。
- Codex 执行时，用它原生的子 agent 或并行机制，每项各自一个 worktree。原则与本节相同。
- **并行上限取信任等级对应的数字**（总览第 4 节），项目 `AGENTS.md` 定了更小的以项目为准。`/next` 会话默认**有空位就补**（`skills/next/SKILL.md` 第 4 节）：手上的项在等派出去的活时，队列里有方向已定、依赖已满足、互不改同一批核心文件的项，就派到上限，不等手上的做完；复核也占一个位。没有这样的项就空着，不为凑数拆活、编新项或派方向没定的项。项目 `AGENTS.md` 写了额度判断的，补位前按它查一次，额度紧时按它少派。会改同一批核心文件的项不并行。用到独占资源的验证（宿主软件、设备），走项目的慢验证队列，不各自去抢。
- **一次只交一件能独立验证、单独提交的事**。大的结构改写先拆成几步，每步有自己的完成标准，做完一步交回再派下一步。一次交整段改写，执行方判断做不完就撤回或空转（有一次 3 分钟就撤回了）；拆成小步才推得动。
- 派活说明要自包含，写清楚：
  - 目标、先读哪些文件、完成标准；
  - 按 `build.md` 做和证明，要跑哪些验证；
  - 边界：不 push、不合并、不改哪些共享文件，方向性选择不自己定（`direction.md` 第 3 节），以及项目的其他禁止项；
  - 失败产物照常保留并提交；
  - 结束报告的格式：三行汇报，加上提交正文草稿（模板见 `land.md`）。
- 队列、计划、`LESSONS.md` 这些共享文件只由你维护。子 agent 把要同步的内容写进结束报告。

### 交给外部 agent 做（省总览的额度）

总览所用模型的额度紧时，执行交给一个 CLI agent（Codex、Claude 的 `claude -p`、DSH 等），你只派活、核对、汇报。不要用自己的子 agent 去做，那样花的还是你的额度。

执行方和审查方都是配置：`scripts/dispatch.json` 里配几个 agent，派活时 `-Agent` 选哪边有额度用哪边。项目 `AGENTS.md` 只写分工规则（下面的"谁审谁"），不写死"写交给 Codex"，换执行方时不用改项目规矩。

- **怎么调**：用本 skill 的 `scripts/dispatch.ps1`（PowerShell 7），在项目仓库里运行。它负责开 worktree、拼任务说明、后台启动对方、记录结果：
  ```
  pwsh -NoProfile -File <skill>/scripts/dispatch.ps1 -Name <分支名> -Agent codex -BriefFile <说明.md> -Wait          # 写
  pwsh -NoProfile -File <skill>/scripts/dispatch.ps1 -Name <运行名> -Agent codex -BriefFile <标准.md> -Review <分支> -Wait  # 审
  pwsh -NoProfile -File <skill>/scripts/dispatch.ps1 -Name <分支名> -Agent claude -Model <模型名> -BriefFile <说明.md> -Wait  # Claude 写，这次指定模型
  pwsh -NoProfile -File <skill>/scripts/dispatch.ps1 -Name <运行名> -Agent dsh -BriefFile <意见.md> -Continue <分支> -Wait # 修
  pwsh -NoProfile -File <skill>/scripts/dispatch.ps1 -List
  pwsh -NoProfile -File <skill>/scripts/dispatch.ps1 -CleanReviews                                    # 清已结束的审查 worktree
  ```
  `-Wait` 放进你自己的后台任务里跑，跑完你会收到通知。不加 `-Wait` 就不会有通知，要自己另起一个等待任务。**派出去的活还在跑，就不结束回合**：手上没别的事，就前台等它。派完就收工，没人会把你叫醒，这正是 2026-10-31 几个会话无声停下的原因。退出码 4 表示写代码的一轮没留下新提交，或留了未提交的改动；5 表示没写出最终回复；127 表示 agent 命令找不到：先看 `final.md` 和工作区再决定，不要直接派审查。
- **项目配置** `scripts/dispatch.json`（入库）：
  ```json
  {
    "verify": "pwsh -NoProfile -File scripts/verify.ps1",
    "verifyReview": "pwsh -NoProfile -File scripts/verify.ps1 -Base {base}",
    "readFirst": ["AGENTS.md", "docs/DEVELOPMENT.md"],
    "protected": ["docs/queue.md"],
    "rules": ["真实数据只读，只用副本", "启动宿主软件只用 scripts/host-probe.ps1"],
    "docsOnly": ["*.md"],
    "sparse": ["/*", "!/evidence/"],
    "agents": {
      "codex": { "model": "<模型名>",
                 "build": "Get-Content -Raw -Encoding UTF8 {prompt} | codex exec --profile <完全访问的 profile> {model} -C {wt} -o {final} - *> {log}",
                 "review": "Get-Content -Raw -Encoding UTF8 {prompt} | codex exec --sandbox workspace-write {model} -C {wt} -o {final} - *> {log}" },
      "claude": { "vendor": "claude", "model": "<模型名>",
                  "build": "Get-Content -Raw -Encoding UTF8 {prompt} | claude -p {model} --permission-mode bypassPermissions 2> {log} | Set-Content -LiteralPath {final} -Encoding utf8NoBOM",
                  "review": "Get-Content -Raw -Encoding UTF8 {prompt} | claude -p {model} --permission-mode acceptEdits --allowedTools 'Bash(pwsh -NoProfile -File *)' 'Bash(git *)' 2> {log} | Set-Content -LiteralPath {final} -Encoding utf8NoBOM" },
      "dsh":   { "build": "Get-Content -Raw -Encoding UTF8 {prompt} | & '<dsh.cmd 的路径>' headless - 2> {log} | Set-Content -LiteralPath {final} -Encoding utf8NoBOM",
                 "env": { "DSH_PERMISSION_MODE": "danger-full-access" } }
    }
  }
  ```
  遇接口 400 脚本会自己等一等再试（默认等 120、300、900 秒，配置 `retry400Seconds` 可改，写 `[]` 不重试），不用手动重派；试完还不行，`-Wait` 会说明。审查结束脚本自己删 worktree，要留着写 `"keepReviewWorktree": true`。快检太慢、项目决定执行方不跑全量的（启用条件见 `build.md` 第 3 节），写 `"builderVerify": "related"`；不写等于 `"full"`。项目开了合并后全量（总览清单配了 `trunkVerify`，`build.md` 第 3 节）的，配置里写 `"trunkVerify": true`：执行方和审查方都只跑对照表选出的测试，审查回复写"全量：合并后由 trunk-check 跑"、不写快检用时，脚本也不再把审查回复的用时记进 `verify-last.json`；它优先于 `builderVerify`。内存紧张、派活被杀过的项目写 `"minFreeMemoryMB": <兆字节>`：可用内存低于它，脚本不派，退出码 6，并列出还在跑的运行；等其中一个结束再派，不要硬派。`-List` 里没有退出记录、进程也不在了的运行显示 `died`，多半是被杀了；同一分支后来没再派过的，要重派。

  `verify` 必填；`readFirst`、`protected`、`rules` 会写进每份任务说明；`docsOnly` 按文件名匹配（如 `*.md`、`*.txt`），不按目录；`sparse` 填了就做稀疏检出（`-Full` 关掉），大仓库开 worktree 从几分钟降到几秒；`env` 只对那一个 agent 进程生效，不改用户的全局配置。没写 `review` 的 agent 审查时也用 `build` 的命令，也就带着 `build` 的权限；`build` 是完全访问的（如样例里 Claude 的 `bypassPermissions`），另写一条收紧的 `review`，审查方只需要改它自己的 worktree、跑项目的 verify 和 `git`。

  每个 agent 可以配模型：`model` 写默认模型，派活时 `-Model <模型名>` 优先；命令里的 `{model}` 换成 `--model '<模型名>'`，参数名不是 `--model` 的写 `"modelFlag"`（如 `"-m"`）；两边都没写时 `{model}` 换成空，不传模型，由 CLI 用它自己的默认。配了模型、命令里却没有 `{model}` 的，脚本不派，免得以为换了模型其实没换。`vendor` 写 `"claude"` 的（`claude -p`），脚本在后台那个进程里去掉继承来的、名字以 `CLAUDE` 或 `ANTHROPIC` 开头的环境变量（含 `CLAUDECODE`，不分大小写）再运行，和 `launch.ps1` 一样，用命令行登录的账号，不沿用桌面应用的登录；派活的会话自己的环境不变，`env` 里写的照样设上。只配了 Codex、DSH、没写这几个字段的配置，行为和以前一样。用完全访问前，先按 `harness.md` 第 4 节把底线收进脚本，并取得用户同意。
- **项目里的入口**：在项目里放一个几行的 `scripts/dispatch.ps1` 转调本 skill 的脚本，`AGENTS.md` 里写这个入口就行，接手的 AI 不用知道 skill 装在哪：
  ```powershell
  # 派活入口：转调 ai-dev-flow 的通用派活脚本，本项目的设置在 scripts/dispatch.json。参数见 ai-dev-flow modules/orchestrate.md。
  $skill = if ($env:AI_DEV_FLOW) { $env:AI_DEV_FLOW } else { Join-Path $HOME '.agents/skills/ai-dev-flow' }
  $script = Join-Path $skill 'scripts/dispatch.ps1'
  if (-not (Test-Path -LiteralPath $script)) { throw "ai-dev-flow skill not found: $script (set AI_DEV_FLOW)" }
  & $script @args -Config (Join-Path $PSScriptRoot 'dispatch.json')
  exit $LASTEXITCODE
  ```
- `.agents/` 写进 `.gitignore`：派活的 worktree 在 `.agents/worktrees/`，每次的说明、日志、回复在 `.agents/runs/`。用 `.agents` 而不是某个工具专属的目录，换别的 AI 接手也找得到。
- **任务说明的固定尾部**由脚本自动附上，你写说明时只写目标、完成标准和提示：
  - 改了代码、脚本或配置的：完成前跑 verify，退出码必须是 0，并做一次改坏验证（改坏后只跑相关的测试，不再跑一遍完整 verify）。配置了 `"builderVerify": "related"` 的，执行方把 verify 换成构建和相关测试，审查方照旧跑一次完整 verify；配置了 `"trunkVerify": true` 的，两边都只跑对照表选出的测试。
  - 只改了文档的：不跑 verify、不做改坏验证，改成把文档里写的路径、命令逐条实际查一遍或跑一遍。审查时脚本按 diff 自动判断（改名算删＋增，子模块和链接不算文档）。只改文档也跑全量 verify，每轮会白花好几分钟。
  - 写下的每条事实都要先自己用命令确认过，确认不了的写"未查到"。不这样要求，对方会写出想当然的路径和命令，审查一轮只能挑出一部分，要来回好几轮。
  - 临时文件放系统临时目录，结束时工作区只能有已提交的改动。
  - 碰到方向性选择不自己定，做不依赖它的部分，写进回复，由你报决定卡。
  - 提交正文按 `land.md` 模板。不写长报告，最后的回复只写三行白话：结果 / 跑了 / 风险。这样对方的输出你读得快，也不会把难懂的长文转给用户。
- **按难度分工**：便宜的那个只接照章执行的机械活（批量跑回归、补用例、按明确规则整理文件）；要逐条核对事实、做判断、改核心代码的交给能力强的那个。看起来简单的文档活往往要逐条核对事实，不算机械活。具体分工写在项目 `AGENTS.md`。
- **记得给要查历史证据的活加 `-Full`**：稀疏检出里没有的文件，对方会当作"不存在"。
- **谁审谁**：写和审不是同一个会话，审的模型不低于写的。可以换一个 agent 审，也可以用同一个 agent 新开的会话审（`-Review` 每次都是新会话，用 `-Model` 保证模型不低于写的那次，写的那次用的模型记在 `.agents/runs/<运行名>/meta.json` 的 `Model`；那里是空的，说明写的那次没传模型、用的是 CLI 自己的默认，审查也不传或传更强的）。单向门档仍按 `verify.md` 跨厂商：Claude 写的派 Codex 审，Codex 写的派 Claude 审。
- **你怎么核对**：不读完整 diff。只看三样东西：对方的三行回复、验证方跑的快检结果（命令、退出码、对应的 head）、验证方的结论。三者对不上，或结论是 Fix，再去看 diff 的相关部分。
- **跟用户汇报**：用你自己的话写，不转发对方原文。

## 4. 接力

子 agent 完成的通知到了以后，按顺序做：

1. **核对**：读结束报告，再亲自核证据，例如看输出文件、确认分支 head 就是报告里说的那个。结束报告是自述，不算证据。快检不在这里重跑：验证方会在同一个 head 上独立跑一次，那次就算数（`land.md` 第 2 节）。
2. **验证**：对分支的 diff 发起独立验证，见 `verify.md`。子 agent 一般不能再派验证方，所以由你发起。要修的意见交回原子 agent（发消息续上它的上下文；外部 agent 就在同一分支上再派一次，说明里附上要修的意见），修完复验。
3. **合并**：按 `land.md` 和项目的信任等级处理：该你合的直接合，L1 的摞好等用户，看一眼档的等用户看。
4. **收尾**：合并后按 `land.md` 第 6 节判断要不要在主干复跑 verify（快进合并的不用），更新队列。已合并的 worktree 按 `land.md` 第 6 节处理。
5. **汇报**：按总览第 6 节写三行，不等用户回复。
6. **补位**：一项结束空出位子，按第 3 节补；没有能并行的项，就按 `skills/next/SKILL.md` 第 5 节领下一项。
7. **结束回合前**：派出去的活都已结束或已等到结果，再按 `skills/next/SKILL.md` 第 6 节收尾：更新队列、写三行汇报、发通知。

## 5. 必须停下找用户

停下前照第 4 节第 7 步收尾，用户会收到通知，不用自己来看。总览第 3 节的情况，加上：

- 被平台安全审查拦截。被拦的内容不得换写法、拆分或换个子 agent 重做。
- 方向性选择：按 `direction.md` 第 3 节报决定卡。
- 同一项从头重来以后仍然通不过验证。
- 需要超出授权的动作：单向门清单里的任何一项。
- 主干红了，往前修和 revert 都没能恢复。

## 6. 关联项目

一个项目用另一个项目的产出时（例如应用调用另一个仓库编译出的引擎），仍然一个项目一个会话，各自开在自己的仓库里，各管各的队列、verify 和信任等级。两边靠**接口约定**连起来，不靠同一个会话记住两边：

- **先定合同再开工**：新接口或不兼容的改动，提供方先写合同草案（输入输出格式、版本、拒绝什么、错误怎么报），交使用方复核，通过后两边各自按合同做，不边做边对。
- **合同测试放进提供方的 verify**：使用方给的最小复现和正例，做成提供方快检里的用例。提供方改坏了合同，自己的 verify 就红，不等使用方发现。
- **提供方发版**：合并后，把对方要用的东西做成带版本的冻结包（文件清单加散列，写明支持的输入格式版本），连同兼容性说明写进提交正文。接口有不兼容的改动，版本号要变，并在说明里写清楚怎么迁移。
- **使用方锁版本**：只用明确指定的那一版冻结包，不直接引用提供方的工作目录。升级是使用方队列里的一项：换版本 → 跑自己的 verify 和北极星 → 通过才合。
- **需求单向流动**：使用方发现缺什么（新对象、格式问题、缺陷），写成一项需求，附最小复现，写进提供方的 `docs/requests.md`，由那边的编排者转进自己的队列，再叫它接：提供方有会话就发消息；没有就用 `scripts/launch.ps1` 在提供方的文件夹开一个 `/next` 会话（做法和退出码同 `portfolio.md` 第 4 节"开会话和叫醒会话"）。不让用户去传话，也不要在使用方的会话里直接改提供方的代码。
- **优先级跟着使用方走**：提供方排队列时，优先做使用方北极星卡住的那几项，汇报时说明是哪个需求驱动的。
- 同时推进几个项目时（关联的、不关联的都算），优先级、额度和跨项目的决定由多项目总览统一管（单个项目的决定用户在项目会话里说），见 `portfolio.md`。项目这边照常按本模块推进，`docs/requests.md` 里也会收到总览转来的决定和请求。
