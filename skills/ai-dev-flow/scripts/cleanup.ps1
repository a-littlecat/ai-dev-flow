[CmdletBinding(PositionalBinding = $false)]
param(
    [string[]]$Branch = @(),
    [string]$Trunk,
    [string]$Repo = '.',
    [int]$IdleMinutes = 60,
    [switch]$DryRun
)
# 合并后清理（land.md 第 6 节）：删已经合进主干、没有未提交改动的 worktree 和分支。/next 每项合并后调用，合并的会话不用记。
#   pwsh -NoProfile -File <skill>/scripts/cleanup.ps1 -Branch <刚合并的分支> [-Trunk main] [-Repo <项目目录>] [-DryRun]
#   -Branch       刚合并的分支（可以几个）：它的 worktree 不看"最近有没有动静"，直接按下面的条件删
#   -Trunk        主干。不给时取 origin/HEAD，没有就取 main 或 master（两个都有时取主检出所在的那个）；判断不了，或主检出不在主干上，退出 2，不猜
#   -IdleMinutes  没点名的 worktree 最近这么多分钟内有动静就不动（默认 60）：刚开出来、还没提交的 worktree，head 也在主干上，可能正有会话在用
#   -DryRun       只列出会删什么，什么都不动，所以也不试目录有没有被占用
# worktree 只删同时满足的：head 是主干的祖先；git status --short 没有输出（未跟踪文件也算有）；被忽略的文件都是构建产物（$buildDirs，其余的如证据、.env 不能丢）；
# 里面没有嵌套别的 worktree；没上锁；不是当前所在目录；没有还在跑的派活；claude agents 里没有会话在里面；目录没被别的进程占用。
# 分支只删已合进主干的；主干、origin/HEAD 指的分支和长期分支（$longLived）不删，列出来，要删手工删。
# 用 git worktree remove 和 git branch -d，不加 --force、不用 -D，Git 拒绝的就留着并说明。没合并的一律不动，也不列。
# 项目 AGENTS.md 写了"不自动清理"的什么也不做（land.md 第 6 节）。
# 目录已经不在的 worktree 记录用 git worktree prune 清掉。审查 worktree 里留着未跟踪证据的，由 dispatch.ps1 -CleanReviews 处理。
# 退出码：0 做完了（有留着的也是 0）；1 试占用时目录没能改回原名，输出里写着现在在哪，要手工改回；2 参数或仓库不对。
$ErrorActionPreference = 'Stop'
# git status 默认会刷新 index，这个脚本一跑，所有 worktree 都成了"刚有动静"。
$env:GIT_OPTIONAL_LOCKS = '0'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

function Norm([string]$p) { [IO.Path]::GetFullPath($p).TrimEnd('\', '/') }
function Git-Out([string]$dir, [string[]]$a) { $o = @(git -C $dir -c core.quotePath=false @a 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Code = $LASTEXITCODE } }

$top = Git-Out $Repo @('rev-parse', '--show-toplevel')
if ($top.Code) { [Console]::Error.WriteLine("cleanup.ps1: 不是 Git 仓库：$Repo"); exit 2 }

function Read-Trees([string]$dir) {
    $trees = [Collections.Generic.List[object]]::new()
    foreach ($line in (Git-Out $dir @('worktree', 'list', '--porcelain')).Out) {
        if ($line -like 'worktree *') { $trees.Add([pscustomobject]@{ Path = $line.Substring(9); Head = $null; Branch = $null; Locked = $false; Prunable = $false }) }
        elseif ($line -like 'HEAD *') { $trees[-1].Head = $line.Substring(5) }
        elseif ($line -like 'branch refs/heads/*') { $trees[-1].Branch = $line.Substring(18) }
        elseif ($line -like 'locked*') { $trees[-1].Locked = $true }
        elseif ($line -like 'prunable*') { $trees[-1].Prunable = $true }
    }
    $trees
}

$trees = @(Read-Trees $Repo)
$main = $trees[0]
$agentsFile = Join-Path $main.Path 'AGENTS.md'
if ((Test-Path -LiteralPath $agentsFile) -and (Get-Content -LiteralPath $agentsFile -Raw -Encoding UTF8) -match '不自动清理') { '项目 AGENTS.md 写了不自动清理，没动'; exit 0 }
$buildDirs = 'node_modules', 'bin', 'obj', 'dist', 'build', 'target', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.cache', '.next', '.vs', 'coverage'
$longLived = '^(main|master|develop|development|dev|trunk|stable|release|hotfix|backup)([/_.-]|$)'
$originHead = @(git -C $main.Path symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>$null) -replace '^origin/', ''
if (-not $Trunk) {
    $named = @('main', 'master' | Where-Object { git -C $main.Path show-ref --verify --quiet "refs/heads/$_"; -not $LASTEXITCODE })
    $Trunk = if ($originHead) { $originHead } elseif ($named.Count -eq 1) { $named[0] } elseif ($named -contains $main.Branch) { $main.Branch }
    if (-not $Trunk) { [Console]::Error.WriteLine('cleanup.ps1: 判断不了主干，用 -Trunk 指定'); exit 2 }
    if ($main.Branch -ne $Trunk) { [Console]::Error.WriteLine("cleanup.ps1: 主检出在 $(if ($main.Branch) { $main.Branch } else { '分离头' })，不在主干 $Trunk 上，没动；切回主干，或用 -Trunk 明确指定"); exit 2 }
}
$trunkSha = Git-Out $main.Path @('rev-parse', '--verify', '--quiet', "$Trunk^{commit}")
if ($trunkSha.Code -or -not $trunkSha.Out) { [Console]::Error.WriteLine("cleanup.ps1: 找不到主干：$Trunk"); exit 2 }
$trunkSha = $trunkSha.Out[0]
foreach ($b in $Branch) {
    if ((Git-Out $main.Path @('rev-parse', '--verify', '--quiet', "refs/heads/$b")).Code -and -not ($trees | Where-Object Branch -eq $b)) { "注意：没有分支 $b（可能已经删了）" }
}

# 还在跑的派活（有 meta.json、没有 exit.json、进程还在）用的目录不动。
$live = @{}
$runs = Join-Path $main.Path '.agents/runs'
if (Test-Path -LiteralPath $runs) {
    foreach ($d in Get-ChildItem -LiteralPath $runs -Directory -ErrorAction SilentlyContinue) {
        $mf = Join-Path $d.FullName 'meta.json'
        if (-not (Test-Path -LiteralPath $mf) -or (Test-Path -LiteralPath (Join-Path $d.FullName 'exit.json'))) { continue }
        try { $m = Get-Content -LiteralPath $mf -Raw -Encoding UTF8 | ConvertFrom-Json } catch { continue }
        if ($m.Worktree -and $m.Pid -and (Get-Process -Id $m.Pid -ErrorAction SilentlyContinue)) { $live[(Norm $m.Worktree).ToLowerInvariant()] = $true }
    }
}
# claude agents 里有进程的会话所在的目录：会话闲着也在用，删了它就没地方干活了。没装 claude 就跳过。
$claude = if ($env:AI_DEV_FLOW_CLAUDE) { $env:AI_DEV_FLOW_CLAUDE } else { 'claude' }
$sessionDirs = @()
if (Get-Command $claude -ErrorAction SilentlyContinue) {
    try {
        $raw = (& $claude agents --json 2>$null | Out-String)
        if ($raw.Trim()) { $sessionDirs = @($raw | ConvertFrom-Json | Where-Object { $_.pid -and $_.cwd } | ForEach-Object { Norm $_.cwd }) }
    } catch { '注意：读不了 claude agents，只按目录占用判断有没有会话在用' }
}
function Test-Inside([string]$child, [string]$parent) { $child -eq $parent -or $child.StartsWith("$parent\", [StringComparison]::OrdinalIgnoreCase) -or $child.StartsWith("$parent/", [StringComparison]::OrdinalIgnoreCase) }
# Windows 上有进程把工作目录放在里面时，git worktree remove 会先删光文件、最后才失败。先试着改名：改不动就是被占用，一点没动。
# 改过去以后，扫描目录的程序（IDE 搜索、同步盘、杀软）可能挡住改回，所以多试几秒；还不行就如实报，不再动它。返回留着的原因，能删返回空。
$stuck = [Collections.Generic.List[string]]::new()
function Get-BusyReason([string]$path) {
    $probe = "$path.cleanup-probe"
    if (Test-Path -LiteralPath $probe) { return "旁边有上次试占用留下的 $probe，看一眼再处理" }
    try { [IO.Directory]::Move($path, $probe) } catch { return '目录被别的进程占用' }
    for ($i = 0; $i -lt 30; $i++) {
        try { [IO.Directory]::Move($probe, $path); return '' } catch { Start-Sleep -Milliseconds 200 }
    }
    $stuck.Add("$probe 要手工改回 $path")
    '目录被占用，没能改回原名'
}
# 这个 worktree 最近一次有动静的时间：它在 .git/worktrees 下的 HEAD、index，加上目录本身（有文件进出时会变）。
function Get-LastTouch($t) {
    $gitDir = (Git-Out $t.Path @('rev-parse', '--absolute-git-dir')).Out[0]
    $items = @(Get-Item -LiteralPath $t.Path) + @(foreach ($n in 'HEAD', 'index') { Get-Item -LiteralPath (Join-Path $gitDir $n) -ErrorAction SilentlyContinue })
    ($items | ForEach-Object LastWriteTime | Measure-Object -Maximum).Maximum
}

$here = Norm (Get-Location).Path
$removedTrees = 0; $removedBranches = 0
$kept = [Collections.Generic.List[string]]::new()
$pruned = @($trees | Select-Object -Skip 1 | Where-Object Prunable)
if ($pruned -and -not $DryRun) { $null = Git-Out $main.Path @('worktree', 'prune') }
if ($pruned) { "$(if ($DryRun) { '会清掉' } else { '清掉了' })目录已不在的 worktree 记录 $($pruned.Count) 条" }

$gone = @{}
$failed = @{}
$removedPaths = @{}
foreach ($t in @($trees | Select-Object -Skip 1 | Where-Object { -not $_.Prunable })) {
    $name = if ($t.Branch) { $t.Branch } else { "分离头 $($t.Head.Substring(0, 7))" }
    $null = git -C $main.Path merge-base --is-ancestor $t.Head $trunkSha 2>$null
    if ($LASTEXITCODE) { continue }
    $path = Norm $t.Path
    $why = $null
    if ($t.Locked) { $why = '上了锁' }
    elseif ($live[$path.ToLowerInvariant()]) { $why = '还有派活在跑' }
    elseif (Test-Inside $here $path) { $why = '当前就在这个目录里' }
    elseif ($sessionDirs | Where-Object { Test-Inside $_ $path }) { $why = '有会话在里面' }
    elseif ($trees | Where-Object { -not $_.Prunable -and -not $removedPaths[(Norm $_.Path)] -and (Norm $_.Path) -ne $path -and (Test-Inside (Norm $_.Path) $path) }) { $why = '里面还嵌着别的 worktree' }
    else {
        # 写明 --untracked-files：项目配了 status.showUntrackedFiles=no 时，默认看不到未跟踪文件，会被当成干净删掉。
        $st = Git-Out $t.Path @('status', '--short', '--ignored', '--untracked-files=normal')
        $ignored = @($st.Out | Where-Object { $_ -like '!! *' } | ForEach-Object { $_.Substring(3).Trim('"') } | Where-Object { -not (@($_ -split '/' | Where-Object { $buildDirs -contains $_ }).Count) })
        if ($st.Code) { $why = '读不了状态' }
        elseif ($st.Out | Where-Object { $_ -and $_ -notlike '!! *' }) { $why = '有未提交改动或未跟踪文件' }
        elseif ($ignored) { $why = "有被忽略的文件：$(($ignored | Select-Object -First 3) -join '、')" }
        elseif (-not ($t.Branch -and $Branch -contains $t.Branch) -and ((Get-Date) - (Get-LastTouch $t)).TotalMinutes -lt $IdleMinutes) { $why = "$IdleMinutes 分钟内有动静，可能有会话在用" }
    }
    if (-not $why -and -not $DryRun) { $why = Get-BusyReason $path }
    if ($why) { $kept.Add("$name（$($t.Path)）：$why"); continue }
    if ($DryRun) { "会删 worktree：$name（$($t.Path)）"; $removedTrees++; if ($t.Branch) { $gone[$t.Branch] = $true }; continue }
    $rm = Git-Out $main.Path @('worktree', 'remove', $t.Path)
    if ($rm.Code) {
        $kept.Add("$name（$($t.Path)）：Git 拒绝删除，留下的情况要看一眼：$($rm.Out -join ' ')")
        if ($t.Branch) { $failed[$t.Branch] = $true }
        continue
    }
    "删了 worktree：$name"
    $removedTrees++
    $removedPaths[$path] = $true
    if ($t.Branch) { $gone[$t.Branch] = $true }
}

# 还挂着 worktree 的分支 Git 不让删，这里也不试；刚删了 worktree 的才算空出来。
$held = @{}
foreach ($t in @(Read-Trees $main.Path)) { if ($t.Branch -and -not ($DryRun -and $gone[$t.Branch])) { $held[$t.Branch] = $true } }
foreach ($b in (Git-Out $main.Path @('branch', '--merged', $trunkSha, '--format=%(refname:short)')).Out | Where-Object { $_ -and $_ -ne $Trunk }) {
    if ($held[$b] -or $failed[$b]) { continue }
    if ($b -eq $originHead -or $b -match $longLived) { $kept.Add("分支 $b：长期分支，要删手工删"); continue }
    if ($DryRun) { "会删分支：$b"; $removedBranches++; continue }
    # 从主检出删：-d 认主检出当前的 HEAD 或上游，主检出不在主干上时可能拒绝，就留着说明。
    $del = Git-Out $main.Path @('branch', '-d', $b)
    if ($del.Code) { $kept.Add("分支 $b：Git 拒绝删除：$($del.Out -join ' ')"); continue }
    "删了分支：$b"
    $removedBranches++
}

"$(if ($DryRun) { '会删' } else { '删了' }) worktree $removedTrees 个、分支 $removedBranches 个；留着 $($kept.Count) 个"
$kept | ForEach-Object { "留着：$_" }
if ($stuck.Count) { $stuck | ForEach-Object { "要你处理：$_" }; exit 1 }
exit 0
