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

# 假执行方：按 plan 里这一次的动作行事。400 / err / ok；可加 +commit、+dirty、+evidence、+touch、+ignored、+big；
# +show 把它看到的 CLAUDE_*、ANTHROPIC_* 变量名和多出来的参数（模型）写进最终回复。
$fake = Join-Path $root 'fake.ps1'
Set-Content -LiteralPath $fake -Encoding utf8NoBOM -Value @'
param($final, $counter, $plan, [Parameter(ValueFromRemainingArguments)][string[]]$rest)
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
if ($step -match 'show') {
    $names = @(Get-ChildItem env: | Where-Object { $_.Name -match '^(CLAUDE|ANTHROPIC)' } | ForEach-Object Name | Sort-Object)
    Set-Content -LiteralPath $final -Encoding utf8NoBOM -Value "env=$($names -join ',')`nargs=$($rest -join '|')"; exit 0
}
if ($step -match '^400') { 'ERROR: {"error":{"message":"Codex: Bad Request"},"status":400,"type":"error"}'; exit 1 }
if ($step -match '^err') { 'ERROR: something else'; exit 1 }
if ($step -match 'timed') { Set-Content -LiteralPath $final -Encoding utf8NoBOM -Value "结论：Pass`n快检用时：725 秒"; exit 0 }
if ($step -match 'notime') { Set-Content -LiteralPath $final -Encoding utf8NoBOM -Value "结论：Pass`n快检用时：不适用"; exit 0 }
Set-Content -LiteralPath $final -Value done
exit 0
'@

function Write-Config($extra) {
    $call = "& (Get-Process -Id `$PID).Path -NoProfile -File '$($fake -replace "'", "''")' {final} `$env:FAKE_COUNTER `$env:FAKE_PLAN *> {log}"
    # fake 像现有的 codex/dsh 配置：没有 vendor、model、{model}。claude 是 claude -p 那样的执行方；nomodel 留了 {model} 没配模型；mflag 换了模型参数名。
    $cfg = [ordered]@{ verify = 'echo ok'; agents = [ordered]@{
            fake    = @{ build = $call; review = $call }
            claude  = @{ vendor = 'claude'; model = 'cfg-model'; build = "$call {model}"; review = "$call {model}"; env = @{ ANTHROPIC_FROM_CONFIG = 'x' } }
            nomodel = @{ build = "$call {model}" }
            mflag   = @{ model = 'm-model'; modelFlag = '--mflag'; build = "$call {model}" }
        } }
    foreach ($k in $extra.Keys) { $cfg[$k] = $extra[$k] }
    $cfg | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $repo 'scripts/dispatch.json') -Encoding utf8NoBOM
}
$runs = Join-Path $repo '.agents/runs'
function Run($name, $plan, [string[]]$more = @(), $agent = 'fake') {
    $env:FAKE_PLAN = $plan
    $env:FAKE_COUNTER = Join-Path $root "$name.count"
    $out = & (Get-Process -Id $PID).Path -NoProfile -File $Script -Name $name -Agent $agent -BriefFile $brief -Config (Join-Path $repo 'scripts/dispatch.json') -Wait @more 2>&1
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

    $null = Run 'builder-default' 'ok+commit'
    $prompt = Get-Content -LiteralPath (Join-Path $runs 'builder-default/prompt.md') -Raw
    Check 'builder: new judge tools run on known truth first' ($prompt -match '已知对、已知错各跑一例')
    Check 'builderVerify default: builder runs full verify' ($prompt -match '完成前在本目录运行 `echo ok`' -and $prompt -match '跑了：verify 结果' -and $prompt -notmatch '不跑完整的')

    Write-Config @{ retry400Seconds = @(); builderVerify = 'related' }
    $null = Run 'builder-related' 'ok+commit'
    $prompt = Get-Content -LiteralPath (Join-Path $runs 'builder-related/prompt.md') -Raw
    Check 'builderVerify related: builder skips full verify' ($prompt -match '与改动相关的测试' -and $prompt -match '不跑完整的 `echo ok`' -and $prompt -notmatch '完成前在本目录运行' -and $prompt -match '跑了：构建和相关测试的结果')
    Check 'builderVerify related: break check still required' ($prompt -match '确认会变红')

    # 执行方换成 Claude：继承来的登录变量只在执行方进程里去掉，env 里配的照样设上；模型从配置读，-Model 优先，没配不传。
    Write-Config @{ retry400Seconds = @() }
    $env:CLAUDE_DISPATCH_TEST = 'inherited'; $env:ANTHROPIC_DISPATCH_TEST = 'inherited'
    function Final($n) { Get-Content -LiteralPath (Join-Path $runs "$n/final.md") -Raw -Encoding UTF8 }
    $r = Run 'claude-build' 'show+commit' @() 'claude'
    $seen = Final 'claude-build'
    Check 'claude builder: inherited CLAUDE_*/ANTHROPIC_* removed, config env kept' ($r.Code -eq 0 -and $seen -match '(?m)^env=ANTHROPIC_FROM_CONFIG\s*$')
    Check 'claude builder: model read from the config' ($seen -match '(?m)^args=--model\|cfg-model\s*$')
    Check 'claude builder: model recorded in meta.json' ((Get-Content -LiteralPath (Join-Path $runs 'claude-build/meta.json') -Raw | ConvertFrom-Json).Model -eq 'cfg-model')
    Check 'claude builder: caller keeps its variables' ($env:CLAUDE_DISPATCH_TEST -eq 'inherited' -and $env:ANTHROPIC_DISPATCH_TEST -eq 'inherited')
    $env:FAKE_PLAN = 'show+commit'; $env:FAKE_COUNTER = Join-Path $root 'claude-inproc.count'
    $inproc = (& (Get-Process -Id $PID).Path -NoProfile -Command "& '$($Script -replace "'", "''")' -Name claude-inproc -Agent claude -BriefFile '$($brief -replace "'", "''")' -Config '$((Join-Path $repo 'scripts/dispatch.json') -replace "'", "''")' -Wait | Out-Null; 'after=' + `$env:CLAUDE_DISPATCH_TEST + ',' + `$env:ANTHROPIC_DISPATCH_TEST" 2>&1) -join "`n"
    Check 'claude builder run in the caller''s process: variables there restored' ($inproc -match 'after=inherited,inherited' -and (Final 'claude-inproc') -match '(?m)^env=ANTHROPIC_FROM_CONFIG\s*$')
    $r = Run 'claude-cli-model' 'show+commit' @('-Model', 'cli model') 'claude'
    Check '-Model overrides the configured model' ($r.Code -eq 0 -and (Final 'claude-cli-model') -match '(?m)^args=--model\|cli model\s*$')
    $r = Run 'nomodel' 'show+commit' @() 'nomodel'
    Check 'no model configured: {model} passes nothing' ($r.Code -eq 0 -and (Final 'nomodel') -match '(?m)^args=\s*$' -and $null -eq (Get-Content -LiteralPath (Join-Path $runs 'nomodel/meta.json') -Raw | ConvertFrom-Json).Model)
    $r = Run 'mflag' 'show+commit' @() 'mflag'
    Check 'modelFlag sets the flag; agent without vendor keeps the variables' ($r.Code -eq 0 -and (Final 'mflag') -match '(?m)^args=--mflag\|m-model\s*$' -and (Final 'mflag') -match 'ANTHROPIC_DISPATCH_TEST' -and (Final 'mflag') -match 'CLAUDE_DISPATCH_TEST')
    $r = Run 'fake-plain' 'show+commit'
    $seen = Final 'fake-plain'
    Check 'config without Claude or models: same command, same variables' ($r.Code -eq 0 -and $seen -match '(?m)^args=\s*$' -and $seen -match 'ANTHROPIC_DISPATCH_TEST' -and $seen -match 'CLAUDE_DISPATCH_TEST' -and $seen -notmatch 'ANTHROPIC_FROM_CONFIG')
    $env:FAKE_PLAN = 'ok+commit'; $env:FAKE_COUNTER = Join-Path $root 'model-refused.count'
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -Name 'model-refused' -Agent fake -Model x -BriefFile $brief -Config (Join-Path $repo 'scripts/dispatch.json') -Wait 2>&1) -join "`n"
    Check '-Model for a command without {model}: refused before starting' ($LASTEXITCODE -ne 0 -and $out -match 'has no \{model\}' -and -not (Test-Path -LiteralPath (Join-Path $runs 'model-refused')) -and -not (Test-Path -LiteralPath (Wt 'model-refused')) -and -not (git -C $repo branch --list model-refused))

    Write-Config @{ retry400Seconds = @(); builderVerify = 'none' }
    $env:FAKE_PLAN = 'ok+commit'
    $env:FAKE_COUNTER = Join-Path $root 'builder-bad.count'
    $out = & (Get-Process -Id $PID).Path -NoProfile -File $Script -Name 'builder-bad' -Agent fake -BriefFile $brief -Config (Join-Path $repo 'scripts/dispatch.json') -Wait 2>&1
    Check 'builderVerify bad value: refused before starting' ($LASTEXITCODE -ne 0 -and ($out -join ' ') -match 'builderVerify' -and -not (Test-Path -LiteralPath (Join-Path $runs 'builder-bad')))

    Write-Config @{ retry400Seconds = @(); minFreeMemoryMB = 4096 }
    $env:AI_DEV_FLOW_FREE_MEMORY_MB = '1000'
    $env:FAKE_PLAN = 'ok+commit'
    $env:FAKE_COUNTER = Join-Path $root 'mem-low.count'
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -Name 'mem-low' -Agent fake -BriefFile $brief -Config (Join-Path $repo 'scripts/dispatch.json') -Wait 2>&1) -join "`n"
    Check 'low memory: refused with exit 6 and the reason' ($LASTEXITCODE -eq 6 -and $out -match 'NOT STARTED: free memory 1000 MB is below minFreeMemoryMB 4096')
    Check 'low memory: nothing started' (-not (Test-Path -LiteralPath (Join-Path $runs 'mem-low')) -and -not (Test-Path -LiteralPath (Wt 'mem-low')) -and -not (git -C $repo branch --list mem-low) -and -not (Test-Path -LiteralPath $env:FAKE_COUNTER))
    $env:AI_DEV_FLOW_FREE_MEMORY_MB = '4096'
    $r = Run 'mem-ok' 'ok+commit'
    Check 'enough memory: dispatched as usual' ($r.Code -eq 0 -and $r.Count -eq 1)
    Write-Config @{ retry400Seconds = @() }
    $env:AI_DEV_FLOW_FREE_MEMORY_MB = '1'
    $r = Run 'mem-unset' 'ok+commit'
    Check 'no minFreeMemoryMB: memory not checked' ($r.Code -eq 0 -and $r.Count -eq 1)
    Remove-Item Env:AI_DEV_FLOW_FREE_MEMORY_MB

    # -List：没有 exit.json 的运行，进程在而且是那次启动的才算 running；进程不在、或进程号被别的进程复用了，算 died
    $self = Get-Process -Id $PID
    $gone = Start-Process -FilePath $self.Path -ArgumentList '-NoProfile -Command exit' -PassThru -WindowStyle Hidden
    $gone.WaitForExit()
    foreach ($case in @(@{ n = 'list-alive'; pid = $PID; started = $self.StartTime }, @{ n = 'list-gone'; pid = $gone.Id; started = (Get-Date) }, @{ n = 'list-reused'; pid = $PID; started = $self.StartTime.AddHours(-3) })) {
        $null = Run $case.n 'ok+commit'
        Remove-Item -LiteralPath (Join-Path $runs "$($case.n)/exit.json")
        $m = Get-Content -LiteralPath (Join-Path $runs "$($case.n)/meta.json") -Raw | ConvertFrom-Json
        $m.Pid = $case.pid; $m.Started = $case.started.ToString('o')
        $m | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runs "$($case.n)/meta.json") -Encoding utf8NoBOM
    }
    $list = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -List -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check '-List: live run is running' ($list -match 'list-alive\s+fake\s+build\s+running')
    Check '-List: run whose process is gone is died' ($list -match 'list-gone\s+fake\s+build\s+died')
    Check '-List: reused process id does not count as running' ($list -match 'list-reused\s+fake\s+build\s+died')
    Write-Config @{ retry400Seconds = @(); minFreeMemoryMB = 4096 }
    $env:AI_DEV_FLOW_FREE_MEMORY_MB = '1000'
    $out = (& (Get-Process -Id $PID).Path -NoProfile -File $Script -Name 'mem-low2' -Agent fake -BriefFile $brief -Config (Join-Path $repo 'scripts/dispatch.json') 2>&1) -join "`n"
    Check 'low memory: names the runs still going, not the dead ones' ($LASTEXITCODE -eq 6 -and $out -match 'Running: list-alive\.' )
    Remove-Item Env:AI_DEV_FLOW_FREE_MEMORY_MB
    foreach ($n in 'list-alive', 'list-gone', 'list-reused') { Remove-Item -LiteralPath (Join-Path $runs $n) -Recurse -Force }

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

    $r = Run 'claude-review' 'show' @('-Review', 'candidate') 'claude'
    $seen = Final 'claude-review'
    Check 'claude reviewer: inherited variables removed, model passed, worktree cleaned' ($r.Code -eq 0 -and $seen -match '(?m)^env=ANTHROPIC_FROM_CONFIG\s*$' -and $seen -match '(?m)^args=--model\|cfg-model\s*$' -and $r.Exit.ReviewWorktree -eq 'removed')
    Remove-Item Env:CLAUDE_DISPATCH_TEST, Env:ANTHROPIC_DISPATCH_TEST

    $vl = Join-Path $repo '.agents/verify-last.json'
    Check 'verify time: no line in the reply, no record' (-not (Test-Path -LiteralPath $vl))
    $null = Run 'rev-timed' 'timed' @('-Review', 'candidate')
    $rec = if (Test-Path -LiteralPath $vl) { Get-Content -LiteralPath $vl -Raw -Encoding UTF8 | ConvertFrom-Json }
    Check 'verify time: recorded with the reviewed head' ($rec.seconds -eq 725 -and $rec.head -eq $candidateHead -and $rec.date -eq (Get-Date).ToString('yyyy-MM-dd'))
    $null = Run 'rev-notime' 'notime' @('-Review', 'candidate')
    Check 'verify time: docs-only reply keeps the last record' ((Get-Content -LiteralPath $vl -Raw -Encoding UTF8 | ConvertFrom-Json).seconds -eq 725)
    Remove-Item -LiteralPath $vl
    $fromWt = Join-Path $root 'from-worktree'
    G -C $repo worktree add -q --detach $fromWt main
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $fromWt 'scripts')
    Copy-Item -LiteralPath (Join-Path $repo 'scripts/dispatch.json') -Destination (Join-Path $fromWt 'scripts/dispatch.json') -Force
    $env:FAKE_PLAN = 'timed'; $env:FAKE_COUNTER = Join-Path $root 'rev-fromwt.count'
    $null = & (Get-Process -Id $PID).Path -NoProfile -File $Script -Name 'rev-fromwt' -Agent fake -BriefFile $brief -Config (Join-Path $fromWt 'scripts/dispatch.json') -Review candidate -Wait 2>&1
    Check 'verify time: dispatched from a worktree, recorded in the main repo' ((Test-Path -LiteralPath $vl) -and -not (Test-Path -LiteralPath (Join-Path $fromWt '.agents/verify-last.json')))
    Check 'verify time: the reviewer is asked for it' ((Get-Content -LiteralPath (Join-Path $runs 'rev-timed/prompt.md') -Raw) -match '快检用时：<秒数> 秒')

    $r = Run 'rev-touched' 'ok+touch' @('-Review', 'candidate')
    Check 'review with tracked change: worktree kept' ((Test-Path -LiteralPath (Wt 'rev-touched')) -and $r.Exit.ReviewWorktree -eq 'kept: tracked files changed')

    $r = Run 'rev-400' '400,400' @('-Review', 'candidate')
    Check 'failed review also cleaned' (-not (Test-Path -LiteralPath (Wt 'rev-400')) -and $r.Code -eq 1 -and $r.Exit.ReviewWorktree -eq 'removed')

    Write-Config @{ retry400Seconds = @(); builderVerify = 'related' }
    $null = Run 'rev-related' 'ok' @('-Review', 'candidate')
    Check 'builderVerify related: reviewer still runs full verify' ((Get-Content -LiteralPath (Join-Path $runs 'rev-related/prompt.md') -Raw) -match '自己运行一次 `echo ok`')

    Check 'review: judge tools were run on known truth' ((Get-Content -LiteralPath (Join-Path $runs 'rev-related/prompt.md') -Raw) -match '已知对、已知错各跑过一例')
    Check 'review: reply reports the gate and what was not run' ((Get-Content -LiteralPath (Join-Path $runs 'rev-related/prompt.md') -Raw) -match '门禁：verify 的命令、退出码、head' -and (Get-Content -LiteralPath (Join-Path $runs 'rev-related/prompt.md') -Raw) -match '(?m)^没跑：因环境原因没跑的检查和原因，由总览补跑；全跑了写"无"')

    Write-Config @{ retry400Seconds = @(); keepReviewWorktree = $true }
    $r = Run 'rev-keep' 'ok+evidence' @('-Review', 'candidate')
    Check 'keepReviewWorktree leaves it' (Test-Path -LiteralPath (Wt 'rev-keep'))
    $null = Run 'rev-running' 'ok' @('-Review', 'candidate')
    Remove-Item -LiteralPath (Join-Path $runs 'rev-running/exit.json')
    $meta = Get-Content -LiteralPath (Join-Path $runs 'rev-running/meta.json') -Raw | ConvertFrom-Json
    $meta.Pid = $PID
    $meta.Started = (Get-Process -Id $PID).StartTime.ToString('o')
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
