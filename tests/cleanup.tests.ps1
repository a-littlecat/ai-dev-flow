param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/cleanup.ps1'), [switch]$Keep)
# cleanup.ps1 的检查：在系统临时目录建一次性仓库，造出各种 worktree 和分支，断言哪些删、哪些不动；退出码 0 才算通过。-Keep 保留临时目录便于查看。
#   pwsh -NoProfile -File tests/cleanup.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("cleanup-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$repo = Join-Path $root '项目 A'
$null = New-Item -ItemType Directory -Force -Path $repo
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { $o = git -C $repo -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c core.autocrlf=false @args 2>&1; if ($LASTEXITCODE) { throw "git $args`n$o" }; $o }
function Put([string]$dir, [string]$rel, [string]$text) { [IO.File]::WriteAllText((Join-Path $dir $rel), $text) }
function Commit([string]$rel) { Put $repo $rel $rel; $null = G add -- $rel; $null = G commit -qm "c $rel" }
function WtCommit([string]$dir, [string]$rel) { Put $dir $rel $rel; $null = git -C $dir add -- $rel; $null = git -C $dir -c user.name=t -c user.email=t@t commit -qm "c $rel" }
function Run([string[]]$a) { $o = @(pwsh -NoProfile -File $Script -Repo $repo @a 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Text = ($o -join "`n"); Code = $LASTEXITCODE } }
function Wt([string]$n) { Join-Path $root "wt-$n" }
function HasBranch([string]$n) { [bool](git -C $repo branch --list $n) }
# 让 worktree 看起来很久没动过：把它的目录和 .git/worktrees 下的 HEAD、index 改旧。
function Age([string]$dir) {
    $g = git -C $dir rev-parse --absolute-git-dir
    foreach ($p in @($dir, (Join-Path $g 'HEAD'), (Join-Path $g 'index'))) { if (Test-Path -LiteralPath $p) { (Get-Item -LiteralPath $p).LastWriteTime = (Get-Date).AddDays(-1) } }
}

try {
    $null = G init -q
    Commit 'a.txt'

    # 已合并、干净、很久没动：删 worktree 和分支
    $null = G worktree add -q -b done (Wt 'done')
    WtCommit (Wt 'done') 'done.txt'
    $null = G merge -q --ff-only done
    Age (Wt 'done')
    # 已合并、没有 worktree 的分支：删
    $null = G branch merged-plain
    # 已合并的分离头：删
    $null = G worktree add -q --detach (Wt 'detached') HEAD
    Age (Wt 'detached')
    # 没合并：不动
    $null = G worktree add -q -b unmerged (Wt 'unmerged')
    WtCommit (Wt 'unmerged') 'u.txt'
    Age (Wt 'unmerged')
    $null = G branch plain-unmerged unmerged
    # 已合并、有未提交改动：不动
    $null = G worktree add -q -b dirty (Wt 'dirty')
    Put (Wt 'dirty') 'a.txt' 'changed'
    Age (Wt 'dirty')
    # 已合并、有未跟踪文件：不动
    $null = G worktree add -q -b untracked (Wt 'untracked')
    Put (Wt 'untracked') 'new.txt' 'x'
    Age (Wt 'untracked')
    # 已合并、干净，但刚开出来：不动（可能有会话正要用）
    $null = G worktree add -q -b fresh (Wt 'fresh')
    # 刚合并、点名的：不看动静
    $null = G worktree add -q -b just (Wt 'just')
    WtCommit (Wt 'just') 'just.txt'
    $null = G merge -q --ff-only just
    # 上锁的：不动
    $null = G worktree add -q -b locked (Wt 'locked')
    Age (Wt 'locked')
    $null = G worktree lock (Wt 'locked')
    # 还有派活在跑的：不动
    $null = G worktree add -q -b running (Wt 'running')
    Age (Wt 'running')
    $run = Join-Path $repo '.agents/runs/r1'
    $null = New-Item -ItemType Directory -Force -Path $run
    Set-Content -LiteralPath (Join-Path $repo '.git/info/exclude') -Value '.agents/' -Encoding utf8NoBOM
    @{ Worktree = (Wt 'running'); Pid = $PID } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'meta.json') -Encoding utf8NoBOM
    # 同一个目录派活已经结束的：照常删
    $null = G worktree add -q -b finished (Wt 'finished')
    Age (Wt 'finished')
    $run2 = Join-Path $repo '.agents/runs/r2'
    $null = New-Item -ItemType Directory -Force -Path $run2
    @{ Worktree = (Wt 'finished'); Pid = $PID } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run2 'meta.json') -Encoding utf8NoBOM
    '{}' | Set-Content -LiteralPath (Join-Path $run2 'exit.json') -Encoding utf8NoBOM
    # 目录已经不在的记录：prune
    $null = G worktree add -q -b vanished (Wt 'vanished')
    Remove-Item -LiteralPath (Wt 'vanished') -Recurse -Force

    $before = (G worktree list --porcelain) -join "`n"
    $r = Run @('-DryRun', '-Branch', 'just')
    Check 'dry run: exit 0, says what it would delete' ($r.Code -eq 0 -and $r.Text -match '会删 worktree：done' -and $r.Text -match '会删分支：merged-plain')
    Check 'dry run: lists the branch of a worktree it would remove' ($r.Text -match '会删分支：done')
    Check 'dry run: nothing changed' (((G worktree list --porcelain) -join "`n") -eq $before -and (HasBranch 'merged-plain') -and (HasBranch 'done'))

    $r = Run @('-Branch', 'just')
    Check 'exit 0 with some kept' ($r.Code -eq 0)
    Check 'merged and clean: worktree and branch removed' (-not (Test-Path -LiteralPath (Wt 'done')) -and -not (HasBranch 'done'))
    Check 'merged branch without a worktree: removed' (-not (HasBranch 'merged-plain'))
    Check 'merged detached worktree: removed' (-not (Test-Path -LiteralPath (Wt 'detached')))
    Check 'named branch: removed even though it just moved' (-not (Test-Path -LiteralPath (Wt 'just')) -and -not (HasBranch 'just'))
    Check 'run that finished: its worktree removed' (-not (Test-Path -LiteralPath (Wt 'finished')) -and -not (HasBranch 'finished'))
    Check 'unmerged worktree and branch: untouched, not even listed' ((Test-Path -LiteralPath (Wt 'unmerged')) -and (HasBranch 'unmerged') -and (HasBranch 'plain-unmerged') -and $r.Text -notmatch 'unmerged')
    Check 'uncommitted change: kept, reason given' ((Test-Path -LiteralPath (Join-Path (Wt 'dirty') 'a.txt')) -and (HasBranch 'dirty') -and ((Get-Content -LiteralPath (Join-Path (Wt 'dirty') 'a.txt') -Raw) -eq 'changed') -and $r.Text -match '留着：dirty.*未提交改动')
    Check 'untracked file: kept, reason given' ((Test-Path -LiteralPath (Join-Path (Wt 'untracked') 'new.txt')) -and (HasBranch 'untracked') -and $r.Text -match '留着：untracked.*未跟踪')
    Check 'just opened and not named: kept, reason given' ((Test-Path -LiteralPath (Wt 'fresh')) -and (HasBranch 'fresh') -and $r.Text -match '留着：fresh.*动静')
    Check 'locked: kept' ((Test-Path -LiteralPath (Wt 'locked')) -and (HasBranch 'locked') -and $r.Text -match '留着：locked.*锁')
    Check 'dispatch still running: kept' ((Test-Path -LiteralPath (Wt 'running')) -and (HasBranch 'running') -and $r.Text -match '留着：running.*派活')
    Check 'missing directory: record pruned' (-not ((G worktree list --porcelain) -join "`n" -match 'wt-vanished') -and $r.Text -match '目录已不在')
    Check 'trunk stays' ((HasBranch 'main') -and ((G symbolic-ref --short HEAD) -eq 'main'))
    Check 'counts in the summary' ($r.Text -match '留着 5 个')

    $r = Run @('-IdleMinutes', '0')
    Check 'idle 0: the fresh worktree goes too' (-not (Test-Path -LiteralPath (Wt 'fresh')))

    Push-Location -LiteralPath (Wt 'running')
    try { $null = Remove-Item -LiteralPath $run -Recurse -Force; $o = @(pwsh -NoProfile -File $Script -IdleMinutes 0 2>&1 | ForEach-Object { "$_" }) } finally { Pop-Location }
    Check 'run from inside a worktree: finds the repo, keeps the one it stands in' ((Test-Path -LiteralPath (Wt 'running')) -and ($o -join "`n") -match '留着：running.*当前')

    $r = Run @('-Trunk', 'nope')
    Check 'unknown trunk: exit 2' ($r.Code -eq 2 -and $r.Text -match '找不到主干')
    $o = @(pwsh -NoProfile -File $Script -Repo (Join-Path $root 'nowhere') 2>&1 | ForEach-Object { "$_" }); $code = $LASTEXITCODE
    Check 'not a repository: exit 2' ($code -eq 2)
} finally {
    if ($Keep) { "kept: $root" } else {
        Get-ChildItem -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object { try { $_.Attributes = 'Normal' } catch {} }
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
}
if ($fail) { "$fail failed"; exit 1 }
'all passed'
exit 0
