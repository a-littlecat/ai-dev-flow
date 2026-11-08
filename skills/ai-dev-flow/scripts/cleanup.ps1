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
#   -Trunk        主干，默认主检出当前所在的分支
#   -IdleMinutes  没点名的 worktree 最近这么多分钟内有动静就不动（默认 60）：刚开出来、还没提交的 worktree，head 也在主干上，可能正有会话在用
#   -DryRun       只列出会删什么
# 只删同时满足的：head 是主干的祖先；git status --short 没有输出（未跟踪文件也算有）；没上锁；不是当前所在目录；没有还在跑的派活。
# 用 git worktree remove 和 git branch -d，不加 --force、不用 -D，Git 拒绝的就留着并说明。没合并的、有改动的一律不动，只列出来。
# 目录已经不在的 worktree 记录用 git worktree prune 清掉。审查 worktree 里留着未跟踪证据的，由 dispatch.ps1 -CleanReviews 处理。
# 退出码：0 做完了（有留着的也是 0）；2 参数或仓库不对。
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
if (-not $Trunk) { $Trunk = $main.Branch }
if (-not $Trunk) { [Console]::Error.WriteLine('cleanup.ps1: 主检出是分离头，用 -Trunk 指定主干'); exit 2 }
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
foreach ($t in @($trees | Select-Object -Skip 1 | Where-Object { -not $_.Prunable })) {
    $name = if ($t.Branch) { $t.Branch } else { "分离头 $($t.Head.Substring(0, 7))" }
    $null = git -C $main.Path merge-base --is-ancestor $t.Head $trunkSha 2>$null
    if ($LASTEXITCODE) { continue }
    $path = Norm $t.Path
    $why = $null
    if ($t.Locked) { $why = '上了锁' }
    elseif ($live[$path.ToLowerInvariant()]) { $why = '还有派活在跑' }
    elseif ($here -eq $path -or $here.StartsWith("$path\", [StringComparison]::OrdinalIgnoreCase) -or $here.StartsWith("$path/", [StringComparison]::OrdinalIgnoreCase)) { $why = '当前就在这个目录里' }
    else {
        $st = Git-Out $t.Path @('status', '--short')
        if ($st.Code) { $why = '读不了状态' }
        elseif ($st.Out | Where-Object { $_ }) { $why = '有未提交改动或未跟踪文件' }
        elseif (-not ($t.Branch -and $Branch -contains $t.Branch) -and ((Get-Date) - (Get-LastTouch $t)).TotalMinutes -lt $IdleMinutes) { $why = "$IdleMinutes 分钟内有动静，可能有会话在用" }
    }
    if ($why) { $kept.Add("$name（$($t.Path)）：$why"); continue }
    if ($DryRun) { "会删 worktree：$name（$($t.Path)）"; $removedTrees++; if ($t.Branch) { $gone[$t.Branch] = $true }; continue }
    $rm = Git-Out $main.Path @('worktree', 'remove', $t.Path)
    if ($rm.Code) { $kept.Add("$name（$($t.Path)）：Git 拒绝删除：$($rm.Out -join ' ')"); continue }
    "删了 worktree：$name"
    $removedTrees++
    if ($t.Branch) { $gone[$t.Branch] = $true }
}

# 还挂着 worktree 的分支 Git 不让删，这里也不试；刚删了 worktree 的才算空出来。
$held = @{}
foreach ($t in @(Read-Trees $main.Path)) { if ($t.Branch -and -not ($DryRun -and $gone[$t.Branch])) { $held[$t.Branch] = $true } }
foreach ($b in (Git-Out $main.Path @('branch', '--merged', $trunkSha, '--format=%(refname:short)')).Out | Where-Object { $_ -and $_ -ne $Trunk }) {
    if ($held[$b]) { continue }
    if ($DryRun) { "会删分支：$b"; $removedBranches++; continue }
    # 从主检出删：-d 认主检出当前的 HEAD 或上游，主检出不在主干上时可能拒绝，就留着说明。
    $del = Git-Out $main.Path @('branch', '-d', $b)
    if ($del.Code) { $kept.Add("分支 $b：Git 拒绝删除：$($del.Out -join ' ')"); continue }
    "删了分支：$b"
    $removedBranches++
}

"$(if ($DryRun) { '会删' } else { '删了' }) worktree $removedTrees 个、分支 $removedBranches 个；留着 $($kept.Count) 个"
$kept | ForEach-Object { "留着：$_" }
exit 0
