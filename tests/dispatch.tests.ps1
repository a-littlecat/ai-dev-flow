param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/dispatch.ps1'), [switch]$Keep)
# dispatch.ps1 的检查：在系统临时目录建一次性仓库，用假的执行方走重试和审查清理，不调真模型。退出码 0 才算通过。
#   pwsh -NoProfile -File tests/dispatch.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Script = [IO.Path]::GetFullPath($Script)
$root = Join-Path ([IO.Path]::GetTempPath()) ("dispatch-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main @args; if ($LASTEXITCODE) { throw "git $args failed" } }

$repo = Join-Path $root '项目 A'
$null = New-Item -ItemType Directory -Force -Path (Join-Path $repo 'scripts')
G init -q $repo
Set-Content -LiteralPath (Join-Path $repo 'AGENTS.md') -Encoding utf8NoBOM -Value 'x'
Set-Content -LiteralPath (Join-Path $repo '.gitignore') -Encoding utf8NoBOM -Value ".agents/`nbin/"
G -C $repo add -A
G -C $repo commit -q -m init
$brief = Join-Path $root 'brief.md'
Set-Content -LiteralPath $brief -Encoding utf8NoBOM -Value '任务'

# 假执行方：按 plan 里这一次的动作行事。400 / err / ok；可加 +commit、+dirty、+evidence、+touch、+ignored、+big。
$fake = Join-Path $root 'fake.ps1'
Set-Content -LiteralPath $fake -Encoding utf8NoBOM -Value @'
param($final, $counter, $plan)
$n = if (Test-Path -LiteralPath $counter) { [int](Get-Content -LiteralPath $counter -Raw) } else { 0 }
Set-Content -LiteralPath $counter -Value ($n + 1)
$step = ($plan -split ',')[$n]
if ($step -match 'commit') { Set-Content -LiteralPath "c$n.txt" -Value x; git add -A; git -c user.name=t -c user.email=t@t commit -q -m "c$n" }
if ($step -match 'dirty') { Set-Content -LiteralPath 'dirty.txt' -Value x }
if ($step -match 'evidence') { $null = New-Item -ItemType Directory -Force -Path evidence; Set-Content -LiteralPath 'evidence/证据 1.txt' -Value proof }
if ($step -match 'ignored') { $null = New-Item -ItemType Directory -Force -Path bin; Set-Content -LiteralPath 'bin/a.dll' -Value x }
if ($step -match 'touch') { Set-Content -LiteralPath 'AGENTS.md' -Value changed }
if ($step -match 'move') { git checkout -q --detach main }
if ($step -match 'big') { $s = [IO.File]::Create((Join-Path $PWD 'big.bin')); $s.SetLength(501MB); $s.Dispose() }
if ($step -match '^400') { 'ERROR: {"error":{"message":"Codex: Bad Request"},"status":400,"type":"error"}'; exit 1 }
if ($step -match '^err') { 'ERROR: something else'; exit 1 }
Set-Content -LiteralPath $final -Value done
exit 0
'@

function Write-Config($extra) {
    $call = "& (Get-Process -Id `$PID).Path -NoProfile -File '$($fake -replace "'", "''")' {final} `$env:FAKE_COUNTER `$env:FAKE_PLAN *> {log}"
    $cfg = [ordered]@{ verify = 'echo ok'; agents = @{ fake = @{ build = $call; review = $call } } }
    foreach ($k in $extra.Keys) { $cfg[$k] = $extra[$k] }
    $cfg | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $repo 'scripts/dispatch.json') -Encoding utf8NoBOM
}
$runs = Join-Path $repo '.agents/runs'
function Run($name, $plan, [string[]]$more = @()) {
    $env:FAKE_PLAN = $plan
    $env:FAKE_COUNTER = Join-Path $root "$name.count"
    $out = & (Get-Process -Id $PID).Path -NoProfile -File $Script -Name $name -Agent fake -BriefFile $brief -Config (Join-Path $repo 'scripts/dispatch.json') -Wait @more 2>&1
    [pscustomobject]@{ Code = $LASTEXITCODE; Out = ($out -join "`n"); Exit = (Get-Content -LiteralPath (Join-Path $runs "$name/exit.json") -Raw | ConvertFrom-Json); Count = [int](Get-Content -LiteralPath $env:FAKE_COUNTER -Raw) }
}
function Wt($n) { Join-Path $repo ".agents/worktrees/$n" }

try {
    Write-Config @{ retry400Seconds = @(0, 0) }

    $r = Run 'retry-once' '400,ok+commit'
    Check '400 then success: exit 0' ($r.Code -eq 0)
    Check '400 then success: ran twice, one retry recorded' ($r.Count -eq 2 -and $r.Exit.Retries -eq 1 -and -not $r.Exit.Error400)
    Check '400 then success: failed log kept' (Test-Path -LiteralPath (Join-Path $runs 'retry-once/run.log.attempt-1'))
    Check '400 then success: clean prompt not annotated' (-not ((Get-Content -LiteralPath (Join-Path $runs 'retry-once/prompt.md') -Raw) -match '上一次运行被接口中断'))

    $r = Run 'retry-limit' '400,400,400,ok+commit'
    Check 'retries stop at the limit' ($r.Count -eq 3 -and $r.Exit.Retries -eq 2)
    Check 'over the limit: fails and says so' ($r.Code -eq 1 -and $r.Exit.Error400 -and $r.Out -match '已重试 2 次')

    $r = Run 'no-retry-other' 'err,ok+commit'
    Check 'other failures are not retried' ($r.Count -eq 1 -and $r.Code -eq 1 -and $r.Exit.Retries -eq 0 -and -not $r.Exit.Error400)

    $r = Run 'dirty-retry' '400+dirty,ok+commit'
    $prompt = Get-Content -LiteralPath (Join-Path $runs 'dirty-retry/prompt.md') -Raw
    Check 'retry after partial work tells the agent' ($r.Count -eq 2 -and $prompt -match '上一次运行被接口中断')

    Write-Config @{ retry400Seconds = @() }
    $r = Run 'retry-off' '400,ok+commit'
    Check 'empty retry400Seconds turns retry off' ($r.Count -eq 1 -and $r.Code -eq 1)

    Write-Config @{ retry400Seconds = @(0) }
    G -C $repo switch -q -c candidate
    Set-Content -LiteralPath (Join-Path $repo 'candidate.txt') -Encoding utf8NoBOM -Value x
    G -C $repo add candidate.txt
    G -C $repo commit -q -m candidate
    G -C $repo switch -q main
    $candidateHead = git -C $repo rev-parse candidate

    $r = Run 'rev-clean' 'ok+evidence+ignored' @('-Review', 'candidate')
    Check 'review: worktree removed' (-not (Test-Path -LiteralPath (Wt 'rev-clean')))
    Check 'review: git forgets the worktree' (-not ((git -C $repo worktree list) -match 'rev-clean'))
    Check 'review: evidence kept in the run dir' ((Get-Content -LiteralPath (Join-Path $runs 'rev-clean/worktree-files/evidence/证据 1.txt') -Raw).Trim() -eq 'proof')
    Check 'review: ignored build output not copied' (-not (Test-Path -LiteralPath (Join-Path $runs 'rev-clean/worktree-files/bin')))
    Check 'review: result recorded' ($r.Exit.ReviewWorktree -eq 'removed' -and $r.Code -eq 0)
    Check 'review: candidate branch untouched' ((git -C $repo rev-parse candidate) -eq $candidateHead)
    Check 'review: footer says where evidence goes' ((Get-Content -LiteralPath (Join-Path $runs 'rev-clean/prompt.md') -Raw) -match 'worktree-files')

    $r = Run 'rev-touched' 'ok+touch' @('-Review', 'candidate')
    Check 'review with tracked change: worktree kept' ((Test-Path -LiteralPath (Wt 'rev-touched')) -and $r.Exit.ReviewWorktree -eq 'kept: tracked files changed')

    $r = Run 'rev-400' '400,400' @('-Review', 'candidate')
    Check 'failed review also cleaned' (-not (Test-Path -LiteralPath (Wt 'rev-400')) -and $r.Code -eq 1 -and $r.Exit.ReviewWorktree -eq 'removed')

    Write-Config @{ retry400Seconds = @(); keepReviewWorktree = $true }
    $r = Run 'rev-keep' 'ok+evidence' @('-Review', 'candidate')
    Check 'keepReviewWorktree leaves it' (Test-Path -LiteralPath (Wt 'rev-keep'))
    $null = Run 'rev-running' 'ok' @('-Review', 'candidate')
    Remove-Item -LiteralPath (Join-Path $runs 'rev-running/exit.json')
    $meta = Get-Content -LiteralPath (Join-Path $runs 'rev-running/meta.json') -Raw | ConvertFrom-Json
    $meta.Pid = $PID
    $meta | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runs 'rev-running/meta.json') -Encoding utf8NoBOM

    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check '-CleanReviews removes finished review worktrees' (-not (Test-Path -LiteralPath (Wt 'rev-keep')))
    Check '-CleanReviews copies evidence first' (Test-Path -LiteralPath (Join-Path $runs 'rev-keep/worktree-files/evidence/证据 1.txt'))
    Check '-CleanReviews leaves a running review' ((Test-Path -LiteralPath (Wt 'rev-running')) -and $out -match 'keep rev-running: still running')
    Check '-CleanReviews leaves tracked changes' (Test-Path -LiteralPath (Wt 'rev-touched'))
    Check '-CleanReviews leaves build worktrees' (Test-Path -LiteralPath (Wt 'retry-once'))

    # 只删分离头：把 review 记录指到一个在分支上的 worktree
    $meta = Get-Content -LiteralPath (Join-Path $runs 'rev-touched/meta.json') -Raw | ConvertFrom-Json
    $meta.Worktree = Wt 'retry-once'
    $meta | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runs 'rev-touched/meta.json') -Encoding utf8NoBOM
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-touched' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check '-CleanReviews never removes a worktree on a branch' ((Test-Path -LiteralPath (Wt 'retry-once')) -and $out -match 'kept: on a branch')

    # 只删 .agents/worktrees 下的
    $outside = Join-Path $root 'outside'
    G -C $repo worktree add -q --detach $outside
    $meta.Worktree = $outside
    $meta | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runs 'rev-touched/meta.json') -Encoding utf8NoBOM
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-touched' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check '-CleanReviews never removes outside .agents/worktrees' ((Test-Path -LiteralPath $outside) -and $out -match 'kept: outside')

    # 上次删到一半：.git 没了，目录还在；主仓库不能受影响
    $null = Run 'rev-orphan' 'ok' @('-Review', 'candidate')
    G -C $repo worktree remove --force (Wt 'rev-orphan')
    $null = New-Item -ItemType Directory -Force -Path (Wt 'rev-orphan')
    Set-Content -LiteralPath (Join-Path (Wt 'rev-orphan') 'locked.dll') -Value x
    $mainHead = git -C $repo rev-parse HEAD
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-orphan' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check '-CleanReviews finishes a half-removed worktree' ((-not (Test-Path -LiteralPath (Wt 'rev-orphan'))) -and $out -match 'rev-orphan: removed')
    Check 'half-removed cleanup leaves the main repo alone' ((git -C $repo rev-parse HEAD) -eq $mainHead -and (Test-Path -LiteralPath (Join-Path $repo 'AGENTS.md')))

    # 没合并的超大目录留着；合并后不再看大小，证据也不留
    $null = Run 'rev-big' 'ok+big' @('-Review', 'candidate')
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-big' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check 'unmerged and oversized: kept' ((Test-Path -LiteralPath (Wt 'rev-big')) -and $out -match 'over 500 MB')
    $null = Run 'rev-merged' 'ok+evidence' @('-Review', 'candidate')
    Check 'before merge: earlier evidence still there' (Test-Path -LiteralPath (Join-Path $runs 'rev-clean/worktree-files'))
    G -C $repo merge -q --ff-only candidate
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check 'merged: worktree removed without copying' ((-not (Test-Path -LiteralPath (Wt 'rev-merged'))) -and -not (Test-Path -LiteralPath (Join-Path $runs 'rev-merged/worktree-files')))
    Check 'merged: size no longer matters' (-not (Test-Path -LiteralPath (Wt 'rev-big')))
    Check 'merged: evidence copied earlier is deleted' (-not (Test-Path -LiteralPath (Join-Path $runs 'rev-clean/worktree-files')))
    Check 'merged: run records stay' ((Test-Path -LiteralPath (Join-Path $runs 'rev-clean/final.md')) -and (Test-Path -LiteralPath (Join-Path $runs 'rev-clean/exit.json')))
    Check 'merged: running review still left alone' (Test-Path -LiteralPath (Wt 'rev-running'))

    # 审查刚结束时证据总要留，哪怕审的版本已经合并
    Write-Config @{ retry400Seconds = @() }
    $null = Run 'rev-post' 'ok+evidence' @('-Review', 'candidate')
    Check 'review of a merged head: evidence kept at the end of the run' ((-not (Test-Path -LiteralPath (Wt 'rev-post'))) -and (Test-Path -LiteralPath (Join-Path $runs 'rev-post/worktree-files/evidence/证据 1.txt')))

    # 基准分支查不到：按没合并算，证据不删
    $null = & (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-post' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1
    Check 'sweep deletes it afterwards' (-not (Test-Path -LiteralPath (Join-Path $runs 'rev-post/worktree-files')))
    $null = Run 'rev-nobase' 'ok+evidence' @('-Review', 'candidate')
    $meta = Get-Content -LiteralPath (Join-Path $runs 'rev-nobase/meta.json') -Raw | ConvertFrom-Json
    $meta.Base = 'no-such-branch'
    $meta | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runs 'rev-nobase/meta.json') -Encoding utf8NoBOM
    $null = & (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-nobase' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1
    Check 'unknown base: evidence not deleted' (Test-Path -LiteralPath (Join-Path $runs 'rev-nobase/worktree-files/evidence/证据 1.txt'))

    # 审查方把 worktree 切到了主干，审的版本其实没合并：证据不删
    G -C $repo switch -q -c candidate2
    Set-Content -LiteralPath (Join-Path $repo 'candidate2.txt') -Encoding utf8NoBOM -Value x
    G -C $repo add candidate2.txt
    G -C $repo commit -q -m candidate2
    G -C $repo switch -q main
    $null = Run 'rev-moved' 'ok+evidence+move' @('-Review', 'candidate2')
    $null = & (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-moved' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1
    Check 'reviewer moved its HEAD to main: unmerged evidence stays' (Test-Path -LiteralPath (Join-Path $runs 'rev-moved/worktree-files/evidence/证据 1.txt'))

    # 运行异常死掉（没有 exit.json、进程不在），审的版本已合并：证据照样复制
    Write-Config @{ retry400Seconds = @(); keepReviewWorktree = $true }
    $null = Run 'rev-died' 'ok+evidence' @('-Review', 'candidate')
    Remove-Item -LiteralPath (Join-Path $runs 'rev-died/exit.json')
    $null = & (Get-Process -Id $PID).Path -NoProfile -File $Script -CleanReviews -Name 'rev-died' -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1
    Check 'died run with a merged head: evidence copied before removing' ((-not (Test-Path -LiteralPath (Wt 'rev-died'))) -and (Test-Path -LiteralPath (Join-Path $runs 'rev-died/worktree-files/evidence/证据 1.txt')))
}
finally {
    if ($Keep) { "kept: $root" } else {
        Get-ChildItem -LiteralPath $root -Recurse -Force | ForEach-Object { $_.Attributes = 'Normal' }
        Remove-Item -LiteralPath $root -Recurse -Force
    }
}
if ($fail) { "$fail check(s) failed"; exit 1 } else { 'all checks passed'; exit 0 }
