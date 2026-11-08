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
    [switch]$List,
    [switch]$CleanReviews,
    [switch]$KeepEvidence
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
#         状态：done / failed / not-done（写代码却没留下提交）/ running / died（没有 exit.json，进程也不在了，多半被杀了）。
#   清理  dispatch.ps1 -CleanReviews [-Name <运行名>]
#         删除已结束的审查 worktree；只删 .agents/worktrees 下的分离头，改动过被跟踪文件的留着。
#         审查的版本还没合进基准分支的，未跟踪文件先复制到 .agents/runs/<运行名>/worktree-files/；已合并的不复制，之前复制的也删掉，只留 final.md 等运行记录。
#         -KeepEvidence：已合并的也复制（审查刚结束时脚本自己用）。
#   加 -Wait：等执行方跑完才返回，打印它的最终回复。退出码：执行方的退出码；写代码的轮次没有新提交或留了未提交改动时为 4。
#   加 -Full：配置了稀疏检出时改为检出全部文件。
# 执行方遇接口 400 时自动重试：等待秒数取配置的 retry400Seconds，默认 120、300、900，写 [] 就不重试。审查结束自动删它的 worktree，配置 keepReviewWorktree 为 true 时不删。
# 任务说明之后自动附上固定要求（边界、自查、verify、改坏验证、提交正文、三行交付）；只改文档时免 verify 和改坏验证。
# 配置 minFreeMemoryMB 时，可用内存低于它就不派，退出码 6，并列出还在跑的运行；不写不查。
# 配置 builderVerify 写 related 时，执行方只跑构建和相关测试，完整 verify 只由审查方在候选 head 上跑一次；默认 full。
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
# 运行还活着：记下的进程还在，而且是那次启动的（Windows 会复用进程号，只看进程号会把死掉的运行当成还在跑）。
function Test-RunAlive($meta) {
    $p = Get-Process -Id $meta.Pid -ErrorAction SilentlyContinue
    if (-not $p) { return $false }
    try { $gap = ([datetime]$meta.Started - $p.StartTime).TotalMinutes } catch { return $true }
    $gap -ge -1 -and $gap -le 5
}

if ($CleanReviews) {
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    $limitBytes = 500MB
    $worktreesRoot = [IO.Path]::GetFullPath((Join-Path $repo '.agents/worktrees')) + [IO.Path]::DirectorySeparatorChar
    # 查不出来的（基准分支没了、head 不存在）一律按没合并算，证据不删。
    function Test-Merged($head, $base) {
        if (-not $head -or -not $base) { return $false }
        git -C $repo merge-base --is-ancestor $head $base *> $null
        $LASTEXITCODE -eq 0
    }
    $dirs = if ($Name) { @(Get-Item -LiteralPath (Join-Path $runsRoot $Name) -ErrorAction SilentlyContinue) } elseif (Test-Path -LiteralPath $runsRoot) { @(Get-ChildItem -LiteralPath $runsRoot -Directory) } else { @() }
    foreach ($dir in $dirs) {
        $metaFile = Join-Path $dir.FullName 'meta.json'
        if (-not (Test-Path -LiteralPath $metaFile)) { continue }
        $meta = Get-Content -LiteralPath $metaFile -Raw | ConvertFrom-Json
        if ($meta.Mode -ne 'review') { continue }
        $exitFile = Join-Path $dir.FullName 'exit.json'
        $evidence = Join-Path $dir.FullName 'worktree-files'
        if (-not $KeepEvidence -and (Test-Path -LiteralPath $exitFile) -and (Test-Path -LiteralPath $evidence)) {
            $finished = Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json
            # 旧记录没有 ReviewedHead，退回用结束时的 head。
            if (Test-Merged $(if ($meta.ReviewedHead) { $meta.ReviewedHead } else { $finished.Head }) $meta.Base) {
                try { Remove-Item -LiteralPath $evidence -Recurse -Force -ErrorAction Stop; "$($dir.Name): merged, evidence deleted" }
                catch { "$($dir.Name): merged, evidence not deleted: $($_.Exception.Message)" }
            }
        }
        if (-not $meta.Worktree -or -not (Test-Path -LiteralPath $meta.Worktree)) { continue }
        $state = 'removed'
        $wtPath = [IO.Path]::GetFullPath($meta.Worktree)
        if (-not (Test-Path -LiteralPath $exitFile) -and (Test-RunAlive $meta)) { "keep $($dir.Name): still running"; continue }
        if (-not $wtPath.StartsWith($worktreesRoot, [StringComparison]::OrdinalIgnoreCase)) { $state = 'kept: outside .agents/worktrees' }
        elseif (-not (Test-Path -LiteralPath (Join-Path $wtPath '.git'))) {
            # 上次删到一半（文件被占用）：git 已不认它，git -C 会落到主仓库，直接删剩下的目录。证据上次已复制。
            try { Remove-Item -LiteralPath $wtPath -Recurse -Force -ErrorAction Stop }
            catch { $state = 'kept: leftover directory still in use' }
            "$($dir.Name): $state"
            if (Test-Path -LiteralPath $exitFile) {
                $exit = Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json
                $exit | Add-Member -NotePropertyName ReviewWorktree -NotePropertyValue $state -Force
                $exit | ConvertTo-Json | Set-Content -LiteralPath $exitFile -Encoding utf8NoBOM
            }
            continue
        }
        else {
            git -C $wtPath symbolic-ref -q HEAD *> $null
            if ($LASTEXITCODE -eq 0) { $state = 'kept: on a branch' }
            elseif (@(git -C $wtPath status --porcelain | Where-Object { $_ -notmatch '^\?\? ' }).Count) { $state = 'kept: tracked files changed' }
        }
        if ($state -eq 'removed') {
            try {
                # 没有 exit.json 的是异常死掉的运行，不确定审完没有，证据照样复制。
                $dropEvidence = -not $KeepEvidence -and (Test-Path -LiteralPath $exitFile) -and (Test-Merged $(if ($meta.ReviewedHead) { $meta.ReviewedHead } else { git -C $wtPath rev-parse HEAD }) $meta.Base)
                $files = if ($dropEvidence) { @() } else { @(git -C $wtPath -c core.quotepath=false ls-files -o --exclude-standard) }
                # 证据可能有几万个文件，用 .NET 直接算大小和复制，cmdlet 逐个调用要十几分钟。
                [long]$bytes = 0
                foreach ($f in $files) { $bytes += ([IO.FileInfo](Join-Path $wtPath $f)).Length }
                if ($bytes -gt $limitBytes) { $state = "kept: untracked files over $([int]($limitBytes / 1MB)) MB" }
                else {
                    foreach ($f in $files) {
                        $to = [IO.Path]::Combine($dir.FullName, 'worktree-files', $f)
                        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($to))
                        [IO.File]::Copy((Join-Path $wtPath $f), $to, $true)
                    }
                    git -C $repo worktree remove --force $wtPath 2>&1 | Out-Null
                    if ($LASTEXITCODE) { $state = 'kept: git worktree remove failed' }
                }
            }
            catch { $state = "kept: $($_.Exception.Message)" }
        }
        "$($dir.Name): $state"
        if (Test-Path -LiteralPath $exitFile) {
            $exit = Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json
            $exit | Add-Member -NotePropertyName ReviewWorktree -NotePropertyValue $state -Force
            $exit | ConvertTo-Json | Set-Content -LiteralPath $exitFile -Encoding utf8NoBOM
        }
    }
    exit 0
}

if ($List) {
    if (-not (Test-Path -LiteralPath $runsRoot)) { 'no runs'; exit 0 }
    $rows = foreach ($dir in Get-ChildItem -LiteralPath $runsRoot -Directory | Sort-Object CreationTime) {
        $metaFile = Join-Path $dir.FullName 'meta.json'
        if (-not (Test-Path -LiteralPath $metaFile)) { continue }
        $meta = Get-Content -LiteralPath $metaFile -Raw | ConvertFrom-Json
        $exitFile = Join-Path $dir.FullName 'exit.json'
        $exit = if (Test-Path -LiteralPath $exitFile) { Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json } else { $null }
        $alive = Test-RunAlive $meta
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
$builderVerify = if ($cfg.builderVerify) { [string]$cfg.builderVerify } else { 'full' }
if ($builderVerify -notin 'full', 'related') { throw "dispatch config: builderVerify must be full or related, got '$builderVerify'" }
$agents = @($cfg.agents.PSObject.Properties.Name)
if (-not $Name -or -not $Agent -or -not $BriefFile) { throw 'Need -Name, -Agent and -BriefFile (or -List)' }
if ($Agent -notin $agents) { throw "Unknown agent '$Agent'; config has: $($agents -join ', ')" }
if ($Name -notmatch '^[a-z0-9][a-z0-9-]{1,60}$') { throw 'Name must be lowercase ASCII letters, digits and hyphens' }
# 内存不够时不开新活：几项并行加上各自的快检，会把机器拖到杀进程。AI_DEV_FLOW_FREE_MEMORY_MB 给测试注入读数。
if ($cfg.minFreeMemoryMB) {
    $freeMB = if ($env:AI_DEV_FLOW_FREE_MEMORY_MB) { [int]$env:AI_DEV_FLOW_FREE_MEMORY_MB }
              else { try { [int]((Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).FreePhysicalMemory / 1024) } catch { $null } }
    if ($null -eq $freeMB) { Write-Warning 'Cannot read free memory; dispatching without the minFreeMemoryMB check' }
    elseif ($freeMB -lt [int]$cfg.minFreeMemoryMB) {
        $running = @(if (Test-Path -LiteralPath $runsRoot) { foreach ($d in Get-ChildItem -LiteralPath $runsRoot -Directory) {
            $mf = Join-Path $d.FullName 'meta.json'
            if ((Test-Path -LiteralPath $mf) -and -not (Test-Path -LiteralPath (Join-Path $d.FullName 'exit.json')) -and (Test-RunAlive (Get-Content -LiteralPath $mf -Raw | ConvertFrom-Json))) { $d.Name }
        } })
        Write-Output "NOT STARTED: free memory $freeMB MB is below minFreeMemoryMB $($cfg.minFreeMemoryMB). Running: $(if ($running) { $running -join ', ' } else { 'none of ours' }). Wait for one to finish, or free memory, then dispatch again."
        exit 6
    }
}
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
- 只在这个目录里工作。不提交，不改任何分支，不碰其他目录。构建产物可以留在这里；做改坏检查时可以临时改源码，改完改回原样，并用 ``git diff --stat`` 确认没有差异。这个目录审完就删，未跟踪的文件（不含 .gitignore 忽略的）会复制到 ``$runDir/worktree-files/``，回复里提到证据文件时写相对这个目录的路径。
$(($rules) -join "`n")
- $readNote$(if ($docsOnly) { '这次只改了文档，不跑 verify；把文档里写的路径、命令、源码位置逐条实际查一遍或跑一遍。' } else { "自己运行一次 ``$verifyReview``（只跑这一次），把命令、退出码和 head 写进回复。改坏检查只跑相关的那一段，恢复后不再重跑。" })
- 结果是新写的评分、读回、比较工具判出来的：核对它拿已知对、已知错各跑过一例，判定脚本和证据都在提交里；缺了，这次判定不算证据。
- 对照上面的目标和完成标准审。不报命名、格式、写法偏好。只报 P0–P2，每条附可执行的证明（命令、会失败的测试、具体输入和输出）；拿不出证明的写进"没覆盖"。没有带证明的 P0/P1，就给 Pass。
- 不写长报告。最后的回复只写下面五行，用白话：

结论：Pass 或 Fix
门禁：verify 的命令、退出码、head；只改文档写"不适用"
没跑：因环境原因没跑的检查和原因，由总览补跑；全跑了写"无"
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
    $builderCheck = if ($builderVerify -eq 'related') { "完成前跑构建和与改动相关的测试，退出码必须是 0，跑了什么列在回复里。不跑完整的 ``$($cfg.verify)``：这个项目由审查方在候选 head 上跑一次，那次才算门禁结果" } else { "完成前在本目录运行 ``$($cfg.verify)``，退出码必须是 0" }
    $builderRan = if ($builderVerify -eq 'related') { '构建和相关测试的结果' } else { 'verify 结果' }
    $footer = @"

---
## 固定要求（派活脚本自动附加）

- 你的工作目录是 worktree ``$wt``，分支 ``$branch``（相对 ``$Base`` $baseSha）。只改这个目录。$(if ($Continue) { '这个分支上已有之前的提交，在它们之上接着改，不要改写已有提交。' })$(if ($leftover) { "`n- 工作区里有上一轮没提交的改动，先检查它们是否符合目标，再接着做：$($leftover -join '；')" })$sparseNote
- $readNote
- 不 push，不合并，不切换或删除其他分支。$($protected)不删除、覆盖、改名已有报告和失败产物。
$(($rules) -join "`n")
- 修 bug 要修到所有同类位置。只做目标需要的部分，不留 TODO。
- 写进文档或回复的每条事实（文件路径、命令、函数在哪个文件、某项能跑通、某项已验收）都要先自己用命令确认过；确认不了的写"未查到"，不要推测。提交前把改动从头核对一遍。
- 改了代码、脚本或配置：$builderCheck。再把修复撤掉或改坏一处，跑覆盖这一处的测试，确认会变红（改的是验证脚本、hook、CI 本身的，要从 verify 命令确认变红，可以只跑其中相关的那一段），然后恢复，用 ``git diff --stat`` 确认和改坏前一样。不为改坏再跑一遍完整 verify。
- 只改了文档：不跑 verify，不做改坏验证；把文档里写的路径、命令逐条实际查一遍或跑一遍。
- 核对过程中产生的临时文件放到系统临时目录下，结束时工作目录里只能有已提交的改动。
- 用新写的评分、读回、比较工具判结果的：先拿已知对、已知错各跑一例，结果写进证据，判定脚本和证据一起提交。
- 提交到本分支。提交正文写四行：为什么 / 跑了（命令 → 结果）/ 改坏验证（撤掉什么 → 哪一步红了；只改文档写"不适用"）/ 没试。
- 不写长报告。最后的回复只写下面三行，用白话，让不看代码的人也能懂：

结果：做成了什么，或卡在哪
跑了：$builderRan；改坏验证结果
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
$retryDelays = if ($null -ne $cfg.retry400Seconds) { @($cfg.retry400Seconds | ForEach-Object { [int]$_ }) } else { @(120, 300, 900) }
$cleanArgs = "-NoProfile -File $(& $q $PSCommandPath) -CleanReviews -KeepEvidence -Name $(& $q $Name)$(if ($Config) { ' -Config ' + (& $q ([IO.Path]::GetFullPath($Config))) })"
$cleanLine = if ($mode -eq 'review' -and -not $cfg.keepReviewWorktree) { "Set-Location -LiteralPath $(& $q $repo)`n& (Get-Process -Id `$PID).Path $cleanArgs | Out-Null" } else { '' }
# 执行方输出 UTF-8；Windows 中文系统控制台默认 GBK，不设置的话管道读进来是乱码。
# 退出码 0 不代表做完了：另记本轮新增提交数和未提交的改动数，由 -Wait 和 -List 判断。
# 配置的命令里没有调用外部程序时退出码为空：看最后一条是否成功、有没有找不到的命令。
# 退出码为 0 却没写出最终回复的，记为 5（例如 agent 启动了但什么都没输出）。
# 接口 400 多半过几分钟就好（同样的说明隔几分钟再发能通过），所以等一等在原地重试；每次失败的日志留成 run.log.attempt-N。
Set-Content -LiteralPath $runner -Encoding utf8NoBOM -Value @"
[Console]::OutputEncoding = [Text.Encoding]::UTF8; `$OutputEncoding = [Text.Encoding]::UTF8
$($envLines -join "`n")
Set-Location -LiteralPath $(& $q $wt)
`$delays = @($($retryDelays -join ','))
`$is400 = `$false
for (`$attempt = 0; ; `$attempt++) {
    `$global:LASTEXITCODE = `$null; `$Error.Clear()
$command
    `$ok = `$?
    `$code = if (`$Error | Where-Object { `$_.FullyQualifiedErrorId -like 'CommandNotFoundException*' }) { 127 } elseif (`$null -ne `$LASTEXITCODE) { `$LASTEXITCODE } elseif (`$ok) { 0 } else { 1 }
    if (`$code -eq 0 -and -not ((Test-Path -LiteralPath $(& $q $final)) -and (Get-Item -LiteralPath $(& $q $final)).Length -gt 0)) { `$code = 5 }
    `$is400 = `$code -ne 0 -and (Test-Path -LiteralPath $(& $q $log)) -and ((Get-Content -LiteralPath $(& $q $log) -Tail 40 -Encoding UTF8) -join "``n") -match '"status"\s*:\s*400'
    if (-not `$is400 -or `$attempt -ge `$delays.Count) { break }
    Copy-Item -LiteralPath $(& $q $log) -Destination ($(& $q $log) + ".attempt-`$(`$attempt + 1)") -Force
    Remove-Item -LiteralPath $(& $q $final) -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds `$delays[`$attempt]
    if ($(if ($mode -eq 'review') { '$false' } else { '$true' }) -and(@(git status --porcelain).Count -or [int](git rev-list --count $startHead..HEAD)) -and -not ((Get-Content -LiteralPath $(& $q $prompt) -Raw) -match '上一次运行被接口中断')) {
        Add-Content -LiteralPath $(& $q $prompt) -Encoding utf8NoBOM -Value "``n上一次运行被接口中断，这个目录里可能已有它留下的提交和未提交改动。先看 git log 和 git status，确认符合目标的留下，接着做完。"
    }
}
[ordered]@{ ExitCode = `$code; Finished = (Get-Date).ToString('o'); Head = (git rev-parse HEAD); NewCommits = [int](git rev-list --count $startHead..HEAD); Uncommitted = @(git status --porcelain).Count; Retries = `$attempt; Error400 = [bool]`$is400 } | ConvertTo-Json | Set-Content -LiteralPath $(& $q $exitFile) -Encoding utf8NoBOM
$cleanLine
exit `$code
"@
# 参数整体传一个带引号的字符串：路径含空格时，数组形式会被拆开。
$process = Start-Process -FilePath (Get-Command pwsh).Source -ArgumentList "-NoProfile -File `"$runner`"" -WindowStyle Hidden -PassThru
[ordered]@{ Name = $Name; Agent = $Agent; Mode = $mode; Sparse = [bool]$sparse; Branch = $(if ($Review) { $Review } elseif ($Continue) { $Continue } else { $Name }); Worktree = $wt; Base = $Base; BaseSha = $baseSha; ReviewedHead = $(if ($Review) { $headSha }); Started = (Get-Date).ToString('o'); Pid = $process.Id } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDir 'meta.json') -Encoding utf8NoBOM
Write-Output "started $Agent $mode '$Name' (pid $($process.Id)); worktree $wt; records $runDir"
if ($Wait) {
    $process.WaitForExit()
    $exit = if (Test-Path -LiteralPath $exitFile) { Get-Content -LiteralPath $exitFile -Raw | ConvertFrom-Json } else { $null }
    Write-Output "finished '$Name': exit $(if ($exit) { $exit.ExitCode } else { 'unknown (no exit.json)' }); head $(if ($exit) { $exit.Head }); new commits $(if ($exit) { $exit.NewCommits }); uncommitted $(if ($exit) { $exit.Uncommitted })"
    if (Test-Path -LiteralPath $final) { Get-Content -LiteralPath $final -Encoding UTF8 | Write-Output }
    if ($exit.Error400) { Write-Output "接口一直报 400，已重试 $($exit.Retries) 次。等一会儿再派；还不行就改写说明，可能是内容被拒。日志：$log" }
    if (-not $exit) { exit 3 }
    if ($exit.ExitCode) { exit $exit.ExitCode }
    # 写代码的轮次必须留下新提交，否则不算完成，调用方不要接着派审查。
    if ($mode -ne 'review' -and $exit.NewCommits -eq 0) { Write-Output 'NOT DONE: no new commit on the branch'; exit 4 }
    if ($mode -ne 'review' -and $exit.Uncommitted) { Write-Output 'NOT DONE: uncommitted changes left in the worktree'; exit 4 }
    exit 0
}
