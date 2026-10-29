param(
    [string]$Name,
    [string]$Agent,
    [string]$BriefFile,
    [string]$Base = 'main',
    [string]$Review,
    [string]$Continue,
    [string]$Config,
    [switch]$Wait,
    [switch]$Full,
    [switch]$List
)
# 派活：把一项任务交给外部 CLI agent（Codex、DSH 等）在后台做，总览只派活、核对、汇报。
# 在项目仓库里任意目录运行，或用 -Config 指定配置（仓库按配置所在位置找）；
# 项目配置默认读 <仓库>/scripts/dispatch.json（格式见 ai-dev-flow modules/orchestrate.md）。
#   派活  dispatch.ps1 -Name <分支名> -Agent <agent> -BriefFile <任务说明.md> [-Base main]
#         新开 worktree .agents/worktrees/<分支名>（从 -Base 开出），执行方在里面改、跑 verify、提交到该分支。
#   审查  dispatch.ps1 -Name <运行名> -Agent <agent> -BriefFile <目标与完成标准.md> -Review <要审的分支> [-Base main]
#         在 <要审的分支> 的最新提交上开临时 worktree（分离头），执行方只审不提交。
#   续做  dispatch.ps1 -Name <运行名> -Agent <agent> -BriefFile <要修的意见.md> -Continue <已有分支>
#         在已有分支的 worktree 里接着做（例如修审查意见），没有 worktree 就为它新开一个。
#   查看  dispatch.ps1 -List
#   加 -Wait：等执行方跑完才返回，打印它的最终回复。退出码：执行方的退出码；写代码的轮次没有新提交或留了未提交改动时为 4。
#   加 -Full：配置了稀疏检出时改为检出全部文件。
# 任务说明之后自动附上固定要求（边界、自查、verify、改坏验证、提交正文、三行交付）；只改文档时免 verify 和改坏验证。
# 每次运行的记录在 .agents/runs/<运行名>/：prompt.md、run.log、final.md（执行方最后的回复）、meta.json、exit.json。
# 脚本本身不 push、不合并。
$ErrorActionPreference = 'Stop'
# 仓库按 -Config 所在位置找（项目里的入口脚本会传它）；没传就按当前目录。
$root = if ($Config) { git -C ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Config))) rev-parse --show-toplevel } else { git rev-parse --show-toplevel }
if ($LASTEXITCODE) { throw 'Run dispatch.ps1 inside a git repository' }
$root = [IO.Path]::GetFullPath($root)
# worktree 和运行记录一律放在主仓库下：从某个 worktree 里调用时不嵌套，否则 Windows 上路径容易超过 260 字符。
$repo = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath((git -C $root rev-parse --path-format=absolute --git-common-dir)))
$runsRoot = Join-Path $repo '.agents/runs'

if ($List) {
    if (-not (Test-Path -LiteralPath $runsRoot)) { 'no runs'; exit 0 }
    $rows = foreach ($dir in Get-ChildItem -LiteralPath $runsRoot -Directory | Sort-Object CreationTime) {
        $metaFile = Join-Path $dir.FullName 'meta.json'
        if (-not (Test-Path -LiteralPath $metaFile)) { continue }
        $meta = Get-Content -LiteralPath $metaFile -Raw | ConvertFrom-Json
        $exitFile = Join-Path $dir.FullName 'exit.json'
        $exit = if (Test-Path -LiteralPath $exitFile) { Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json } else { $null }
        $alive = [bool](Get-Process -Id $meta.Pid -ErrorAction SilentlyContinue)
        $state = if ($exit) {
            if ($exit.ExitCode -ne 0) { 'failed' } elseif ($meta.Mode -ne 'review' -and ($exit.NewCommits -eq 0 -or $exit.Uncommitted)) { 'not-done' } else { 'done' }
        } elseif ($alive) { 'running' } else { 'died' }
        $finalFile = Join-Path $dir.FullName 'final.md'
        $final = if (Test-Path -LiteralPath $finalFile) { ((Get-Content -LiteralPath $finalFile -Encoding UTF8 | Where-Object { $_.Trim() }) | Select-Object -Last 3) -join ' / ' } else { '' }
        $end = if ($exit) { [datetime]$exit.Finished } else { Get-Date }
        $minutes = [math]::Round(($end - [datetime]$meta.Started).TotalMinutes)
        [pscustomobject]@{ Run = $dir.Name; Agent = $meta.Agent; Mode = $meta.Mode; State = $state; Minutes = $minutes; Final = $final }
    }
    $rows | Format-Table -AutoSize -Wrap | Out-String -Width 220
    exit 0
}

if (-not $Config) { $Config = Join-Path $root 'scripts/dispatch.json' }
if (-not (Test-Path -LiteralPath $Config)) { throw "No dispatch config: $Config (see ai-dev-flow modules/orchestrate.md)" }
$cfg = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $cfg.verify) { throw 'dispatch config needs "verify"' }
$agents = @($cfg.agents.PSObject.Properties.Name)
if (-not $Name -or -not $Agent -or -not $BriefFile) { throw 'Need -Name, -Agent and -BriefFile (or -List)' }
if ($Agent -notin $agents) { throw "Unknown agent '$Agent'; config has: $($agents -join ', ')" }
if ($Name -notmatch '^[a-z0-9][a-z0-9-]{1,60}$') { throw 'Name must be lowercase ASCII letters, digits and hyphens' }
$agentCfg = $cfg.agents.$Agent
$readFirst = if ($cfg.readFirst) { @($cfg.readFirst) } else { @('AGENTS.md') }
$docsPatterns = if ($cfg.docsOnly) { @($cfg.docsOnly) } else { @('*.md') }
$sparse = if ($cfg.sparse -and -not $Full) { @($cfg.sparse) } else { @() }
$sparseNote = if ($sparse) { "`n- 这个 worktree 是稀疏检出，只检出这些路径：$($sparse -join ' ')。任务要用到没检出的文件时，停下来在回复里说明，由总览用 -Full 重派，不要自己改检出范围。" } else { '' }
$tick = [char]96
function Format-Code([object[]]$items) { ($items | ForEach-Object { $tick + $_ + $tick }) -join '、' }
$rules = @($cfg.rules | Where-Object { $_ }) | ForEach-Object { "- $_" }
$protected = if ($cfg.protected) { '不改 ' + (Format-Code @($cfg.protected)) + '。' } else { '' }

$brief = Get-Content -LiteralPath $BriefFile -Raw -Encoding UTF8
$runDir = Join-Path $runsRoot $Name
if (Test-Path -LiteralPath $runDir) { throw "Run already exists: $runDir" }
$wt = Join-Path $repo ".agents/worktrees/$Name"
$baseSha = git -C $root rev-parse --verify "$Base^{commit}"
if ($LASTEXITCODE) { throw "Unknown base: $Base" }
function New-Worktree([string]$path, [string[]]$addArgs) {
    git -C $root worktree add --no-checkout @addArgs
    if ($LASTEXITCODE) { throw 'git worktree add failed' }
    if ($sparse) { git -C $path sparse-checkout set --no-cone @sparse; if ($LASTEXITCODE) { throw 'sparse-checkout failed' } }
    git -C $path checkout -q
    if ($LASTEXITCODE) { throw 'checkout failed' }
}
if ($Continue) {
    git -C $root rev-parse --verify --quiet "refs/heads/$Continue" | Out-Null
    if ($LASTEXITCODE) { throw "Unknown branch to continue: $Continue" }
    $lines = @(git -C $root worktree list --porcelain)
    $existing = for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -ceq "branch refs/heads/$Continue") { $lines[$i - 2] -replace '^worktree ', '' } }
    if ($existing) {
        $wt = [IO.Path]::GetFullPath(@($existing)[0])
        # 已有的 worktree 可能是稀疏检出的；这一轮要 -Full 时把它放开。
        if ($Full -and (git -C $wt config --get core.sparseCheckout) -eq 'true') { git -C $wt sparse-checkout disable; if ($LASTEXITCODE) { throw 'sparse-checkout disable failed' } }
    }
    else { $wt = Join-Path $repo ".agents/worktrees/$Continue"; New-Worktree $wt @($wt, $Continue) }
    # 上一轮没提交的改动留给本轮接着处理（例如执行方写好了却没能提交），在固定要求里列出来。
    $leftover = @(git -C $wt status --porcelain)
}
elseif (Test-Path -LiteralPath $wt) { throw "Worktree path already exists: $wt" }

$readNote = '先读 ' + (Format-Code $readFirst) + '。'
if ($Review) {
    $headSha = git -C $root rev-parse --verify "refs/heads/$Review^{commit}"
    if ($LASTEXITCODE) { throw "Unknown branch to review: $Review" }
    $baseSha = git -C $root merge-base $baseSha $headSha
    New-Worktree $wt @('--detach', $wt, $headSha)
    $mode = 'review'
    # 只改文档才免 verify：改名拆成删＋增；只认普通文件，子模块（160000）和链接（120000）不算文档；
    # docsOnly 只按文件名匹配（如 *.md），不按目录，免得 docs/ 下的脚本被当成文档。
    $changed = @(git -C $root -c core.quotepath=false diff --raw --no-renames "$baseSha..$headSha")
    $docsOnly = $changed.Count -gt 0 -and -not ($changed | Where-Object {
            if ($_ -notmatch '^:(100644|100755|000000) (100644|100755|000000) [^\t]*\t(.*)$') { return $true }
            $path = $Matches[3]
            $leaf = [IO.Path]::GetFileName($path)
            -not ($docsPatterns | Where-Object { $leaf -like $_ })
        })
    $verifyReview = if ($cfg.verifyReview) { $cfg.verifyReview.Replace('{base}', $baseSha) } else { $cfg.verify }
    $footer = @"

---
## 固定要求（审查，派活脚本自动附加）

- 你是独立审查方。工作目录是临时 worktree ``$wt``，检出分支 ``$Review`` 的 $headSha。审查范围：``git diff $baseSha..$headSha``。$sparseNote
- 只在这个目录里工作。不提交，不改任何分支，不碰其他目录。构建产物可以留在这里；做改坏检查时可以临时改源码，改完改回原样，并用 ``git diff --stat`` 确认没有差异。
$(($rules) -join "`n")
- $readNote$(if ($docsOnly) { '这次只改了文档，不跑 verify；把文档里写的路径、命令、源码位置逐条实际查一遍或跑一遍。' } else { "自己运行 ``$verifyReview``，把结果写进回复。" })
- 对照上面的目标和完成标准审。不报命名、格式、写法偏好。只报 P0–P2，每条附可执行的证明（命令、会失败的测试、具体输入和输出）；拿不出证明的写进"没覆盖"。没有带证明的 P0/P1，就给 Pass。
- 不写长报告。最后的回复只写下面三行，用白话：

结论：Pass 或 Fix
问题：无，或每条一行：P级 ｜ 文件:行 ｜ 问题 ｜ 证明
没覆盖：一句话
"@
}
else {
    $branch = if ($Continue) { $Continue } else { $Name }
    if (-not $Continue) {
        if (git -C $root branch --list $Name) { throw "Branch already exists: $Name" }
        New-Worktree $wt @('-b', $Name, $wt, $baseSha)
    }
    $mode = if ($Continue) { 'continue' } else { 'build' }
    $footer = @"

---
## 固定要求（派活脚本自动附加）

- 你的工作目录是 worktree ``$wt``，分支 ``$branch``（相对 ``$Base`` $baseSha）。只改这个目录。$(if ($Continue) { '这个分支上已有之前的提交，在它们之上接着改，不要改写已有提交。' })$(if ($leftover) { "`n- 工作区里有上一轮没提交的改动，先检查它们是否符合目标，再接着做：$($leftover -join '；')" })$sparseNote
- $readNote
- 不 push，不合并，不切换或删除其他分支。$($protected)不删除、覆盖、改名已有报告和失败产物。
$(($rules) -join "`n")
- 修 bug 要修到所有同类位置。只做目标需要的部分，不留 TODO。
- 写进文档或回复的每条事实（文件路径、命令、函数在哪个文件、某项能跑通、某项已验收）都要先自己用命令确认过；确认不了的写"未查到"，不要推测。提交前把改动从头核对一遍。
- 改了代码、脚本或配置：完成前在本目录运行 ``$($cfg.verify)``，退出码必须是 0。再把修复撤掉或改坏一处，确认 verify 会变红，然后恢复。
- 只改了文档：不跑 verify，不做改坏验证；把文档里写的路径、命令逐条实际查一遍或跑一遍。
- 核对过程中产生的临时文件放到系统临时目录下，结束时工作目录里只能有已提交的改动。
- 提交到本分支。提交正文写四行：为什么 / 跑了（命令 → 结果）/ 改坏验证（撤掉什么 → 哪一步红了；只改文档写"不适用"）/ 没试。
- 不写长报告。最后的回复只写下面三行，用白话，让不看代码的人也能懂：

结果：做成了什么，或卡在哪
跑了：verify 结果；改坏验证结果
风险：无，或一句话
"@
}

[IO.Directory]::CreateDirectory($runDir) | Out-Null
$prompt = Join-Path $runDir 'prompt.md'; $log = Join-Path $runDir 'run.log'; $final = Join-Path $runDir 'final.md'; $exitFile = Join-Path $runDir 'exit.json'
Set-Content -LiteralPath $prompt -Value ($brief.TrimEnd() + "`n" + $footer) -Encoding utf8NoBOM

# 配置里的命令模板：{prompt} {final} {log} {wt} {root} 一次替换成加了单引号的路径，由 PowerShell 执行。
# 必须一次替换：逐个替换时，前面换进去的路径里若含 {log} 之类的字样，会被再换一遍、拆坏引号。
$q = { param($s) "'" + ($s -replace "'", "''") + "'" }
$template = if ($mode -eq 'review' -and $agentCfg.review) { $agentCfg.review } else { $agentCfg.build }
if (-not $template) { throw "Agent '$Agent' needs a ""build"" command in the config" }
$slots = @{ prompt = $prompt; final = $final; log = $log; wt = $wt; root = $root }
$command = [regex]::Replace($template, '\{(prompt|final|log|wt|root)\}', { param($m) & $q $slots[$m.Groups[1].Value] })
$envLines = if ($agentCfg.env) { foreach ($p in $agentCfg.env.PSObject.Properties) { "`$env:$($p.Name) = $(& $q ([string]$p.Value))" } } else { @() }
$startHead = git -C $wt rev-parse HEAD
$runner = Join-Path $runDir 'run.ps1'
# 执行方输出 UTF-8；Windows 中文系统控制台默认 GBK，不设置的话管道读进来是乱码。
# 退出码 0 不代表做完了：另记本轮新增提交数和未提交的改动数，由 -Wait 和 -List 判断。
# 配置的命令里没有调用外部程序时退出码为空：看最后一条是否成功、有没有找不到的命令。
# 退出码为 0 却没写出最终回复的，记为 5（例如 agent 启动了但什么都没输出）。
Set-Content -LiteralPath $runner -Encoding utf8NoBOM -Value @"
[Console]::OutputEncoding = [Text.Encoding]::UTF8; `$OutputEncoding = [Text.Encoding]::UTF8
$($envLines -join "`n")
Set-Location -LiteralPath $(& $q $wt)
`$global:LASTEXITCODE = `$null; `$Error.Clear()
$command
`$ok = `$?
`$code = if (`$Error | Where-Object { `$_.FullyQualifiedErrorId -like 'CommandNotFoundException*' }) { 127 } elseif (`$null -ne `$LASTEXITCODE) { `$LASTEXITCODE } elseif (`$ok) { 0 } else { 1 }
if (`$code -eq 0 -and -not ((Test-Path -LiteralPath $(& $q $final)) -and (Get-Item -LiteralPath $(& $q $final)).Length -gt 0)) { `$code = 5 }
[ordered]@{ ExitCode = `$code; Finished = (Get-Date).ToString('o'); Head = (git rev-parse HEAD); NewCommits = [int](git rev-list --count $startHead..HEAD); Uncommitted = @(git status --porcelain).Count } | ConvertTo-Json | Set-Content -LiteralPath $(& $q $exitFile) -Encoding utf8NoBOM
"@
# 参数整体传一个带引号的字符串：路径含空格时，数组形式会被拆开。
$process = Start-Process -FilePath (Get-Command pwsh).Source -ArgumentList "-NoProfile -File `"$runner`"" -WindowStyle Hidden -PassThru
[ordered]@{ Name = $Name; Agent = $Agent; Mode = $mode; Sparse = [bool]$sparse; Branch = $(if ($Review) { $Review } elseif ($Continue) { $Continue } else { $Name }); Worktree = $wt; Base = $Base; BaseSha = $baseSha; Started = (Get-Date).ToString('o'); Pid = $process.Id } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDir 'meta.json') -Encoding utf8NoBOM
Write-Output "started $Agent $mode '$Name' (pid $($process.Id)); worktree $wt; records $runDir"
if ($Wait) {
    $process.WaitForExit()
    $exit = if (Test-Path -LiteralPath $exitFile) { Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json } else { $null }
    Write-Output "finished '$Name': exit $(if ($exit) { $exit.ExitCode } else { 'unknown (no exit.json)' }); head $(if ($exit) { $exit.Head }); new commits $(if ($exit) { $exit.NewCommits }); uncommitted $(if ($exit) { $exit.Uncommitted })"
    if (Test-Path -LiteralPath $final) { Get-Content -LiteralPath $final -Encoding UTF8 | Write-Output }
    if (-not $exit) { exit 3 }
    if ($exit.ExitCode) { exit $exit.ExitCode }
    # 写代码的轮次必须留下新提交，否则不算完成，调用方不要接着派审查。
    if ($mode -ne 'review' -and $exit.NewCommits -eq 0) { Write-Output 'NOT DONE: no new commit on the branch'; exit 4 }
    if ($mode -ne 'review' -and $exit.Uncommitted) { Write-Output 'NOT DONE: uncommitted changes left in the worktree'; exit 4 }
    exit 0
}
