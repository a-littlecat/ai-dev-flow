param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/trunk-check.ps1'), [switch]$Keep)
# trunk-check.ps1 的检查：在系统临时目录建一个项目和清单，用假的全量命令（写一行计数再按 FAKE_EXIT 退出），断言：主干没变不跑、变了跑并记账、红了推一次、锁住不叠跑、有会话在跑快检时等；状态脚本看得到主干红了。退出码 0 才算通过。
#   pwsh -NoProfile -File tests/trunk-check.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("trunk-check-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$null = New-Item -ItemType Directory -Force -Path $root
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main @args; if ($LASTEXITCODE) { throw "git $args" } }
$lock = Join-Path $root 'trunk-check.lock'
function Run([string[]]$more) { $o = @(pwsh -NoProfile -File $Script -Config $cfg -Lock $lock -NotifyDryRun @more 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Text = ($o -join "`n"); Code = $LASTEXITCODE } }

$env:AI_DEV_FLOW_BUSY_MARK = 'trunk-check-test-busy-' + [guid]::NewGuid().ToString('N').Substring(0, 6)
try {
    $proj = Join-Path $root 'proj'
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $proj 'docs')
    G init -q $proj
    Set-Content -LiteralPath (Join-Path $proj '.gitignore') -Encoding utf8NoBOM -Value '.agents/'
    Set-Content -LiteralPath (Join-Path $proj 'docs/queue.md') -Encoding utf8NoBOM -Value "| # | 目标 | 依赖 | 状态 |`n|---|---|---|---|`n| 1 | x | 无 | 待做 |"
    G -C $proj add -A; G -C $proj commit -q -m one
    $count = Join-Path $root 'runs.txt'
    $runs = { if (Test-Path -LiteralPath $count) { @(Get-Content -LiteralPath $count).Count } else { 0 } }
    # 假全量：在 worktree 里跑（写下当前目录），按项目里 fail.txt 的有无决定红绿
    $verify = "Add-Content -LiteralPath '$count' -Value (Get-Location).Path; if (Test-Path fail.txt) { exit 1 } else { exit 0 }"
    $cfg = Join-Path $root 'projects.json'
    $writeCfg = { param($v, $s) @{ projects = @(@{ name = '项目'; path = $proj; status = '推进中'; trunkVerify = $v; trunkSetup = $s }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfg -Encoding utf8NoBOM }

    & $writeCfg $null
    $r = Run
    Check 'no trunkVerify: nothing to run' ($r.Code -eq 0 -and $r.Text -match '没有要跑的' -and (& $runs) -eq 0)

    & $writeCfg $verify
    $r = Run
    $ledger = Join-Path $proj '.agents/verify-ledger.jsonl'
    Check 'trunk not in the ledger: runs once in a clean worktree, records green, removes the worktree' ($r.Code -eq 0 -and (& $runs) -eq 1 -and $r.Text -match '：green' -and (Get-Content -LiteralPath $count -Raw) -match 'trunk-check' -and -not (Test-Path -LiteralPath (Join-Path $proj '.agents/trunk-check')) -and (Test-Path -LiteralPath $ledger))
    $last = Join-Path $proj '.agents/verify-last.json'
    $vl = try { Get-Content -LiteralPath $last -Raw | ConvertFrom-Json } catch { $null }
    Check 'green: the time goes into .agents/verify-last.json for the status page' ($vl -and $vl.source -eq 'trunk-check' -and $vl.head -eq (git -C $proj rev-parse HEAD) -and $null -ne $vl.seconds -and $vl.date -eq (Get-Date).ToString('yyyy-MM-dd'))
    $r = Run
    Check 'trunk unchanged: not run again' ($r.Text -match '没有要跑的' -and (& $runs) -eq 1)

    Set-Content -LiteralPath (Join-Path $proj 'fail.txt') -Encoding utf8NoBOM -Value 'x'
    G -C $proj add -A; G -C $proj commit -q -m 'break it'
    $r = Run
    Check 'trunk changed and red: recorded red, notifies once' ($r.Code -eq 0 -and (& $runs) -eq 2 -and $r.Text -match '：red' -and $r.Text -match 'title: .*项目 主干全量红了' -and $r.Text -match 'bark: yes')
    $r = Run
    Check 'red tree: not rerun, no second notice' ((& $runs) -eq 2 -and $r.Text -notmatch '主干全量红了')
    Check 'red: verify-last.json keeps the last green' ((Get-Content -LiteralPath $last -Raw | ConvertFrom-Json).head -eq $vl.head)
    $redMark = Join-Path $proj '.agents/trunk-red.json'
    $rm = try { Get-Content -LiteralPath $redMark -Raw | ConvertFrom-Json } catch { $null }
    Check 'red: .agents/trunk-red.json tells the project session the head and how to rerun' ($rm -and $rm.head -eq (git -C $proj rev-parse HEAD) -and $rm.project -eq '项目' -and $rm.config -and (Test-Path -LiteralPath $rm.config))

    $st = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'status.ps1') -Config $cfg -All -Json | ConvertFrom-Json
    Check 'status: trunk red is flagged for /next' ($st.Projects[0].TrunkRed -and [bool](@($st.Projects[0].Problems) -match '^主干全量红了'))

    Remove-Item -LiteralPath (Join-Path $proj 'fail.txt')
    Set-Content -LiteralPath (Join-Path $proj 'b.txt') -Encoding utf8NoBOM -Value 'new'
    G -C $proj add -A; G -C $proj commit -q -m 'fix it'
    Set-Content -LiteralPath $lock -Value "$PID|$((Get-Process -Id $PID).StartTime.ToUniversalTime().Ticks)" -NoNewline
    $r = Run
    Check 'lock held by a live process: skipped' ($r.Text -match '跳过：另一轮' -and (& $runs) -eq 2)
    Set-Content -LiteralPath $lock -Value 999999 -NoNewline
    $busy = Start-Process -FilePath (Get-Command pwsh -CommandType Application | Select-Object -First 1).Source -ArgumentList "-NoProfile -Command ""Start-Sleep 60 # $env:AI_DEV_FLOW_BUSY_MARK""" -WindowStyle Hidden -PassThru
    try {
        Start-Sleep -Milliseconds 1500
        $r = Run
        Check 'a session is running a check through the ledger: waits for the next round' ($r.Text -match '跳过：有 \d+ 个进程' -and (& $runs) -eq 2)
    } finally { Stop-Process -Id $busy.Id -Force -ErrorAction SilentlyContinue }
    $r = Run
    Check 'stale lock and nobody busy: runs, green again, the red record is gone' ((& $runs) -eq 3 -and $r.Text -match '：green' -and -not (Test-Path -LiteralPath $lock) -and -not (Test-Path -LiteralPath $redMark))
    $null = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'verify-ledger.ps1') -Repo $proj -Record -Rev HEAD -Result red -For 'one test' -Where 会话
    $st = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'status.ps1') -Config $cfg -All -Json | ConvertFrom-Json
    Check 'status: another command red on the trunk tree is not trunk red' (-not $st.Projects[0].TrunkRed -and -not (@($st.Projects[0].Problems) -match '^主干全量红了'))
    $commit = { param($name) Set-Content -LiteralPath (Join-Path $proj $name) -Encoding utf8NoBOM -Value $name; G -C $proj add -A; G -C $proj commit -q -m $name }

    & $commit 'c.txt'
    Set-Content -LiteralPath $lock -Value "$PID|123" -NoNewline
    $r = Run
    Check 'lock PID reused by another process (start time differs): stale, runs' ((& $runs) -eq 4 -and $r.Text -match '：green' -and -not (Test-Path -LiteralPath $lock))

    & $commit 'd.txt'
    & $writeCfg $verify 'Set-Content copied.dat x'
    $r = Run
    $r2 = Run
    Check 'trunkSetup copies a file into the worktree: still recorded, not rerun' ((& $runs) -eq 5 -and $r.Text -match '：green' -and $r2.Text -match '没有要跑的' -and $r2.Text -match '账上是 green')
    & $writeCfg $verify

    Set-Content -LiteralPath (Join-Path $proj 'fail.txt') -Encoding utf8NoBOM -Value 'x'
    & $commit 'e.txt'
    $null = Run
    $r = Run @('-Rerun', '项目')
    $r2 = Run
    Check '-Rerun: a red tree runs once more, then waits again' ((& $runs) -eq 7 -and $r.Text -match '：red' -and $r2.Text -match '账上是 red')
    $r = Run @('-Rerun', '项目')
    Remove-Item -LiteralPath (Join-Path $proj 'fail.txt')
    & $commit 'f.txt'
    $null = Run
    $r = Run @('-Rerun', '项目')
    Check '-Rerun: a green tree is not rerun' ((& $runs) -eq 9 -and $r.Text -match '账上是 green')

    & $commit 'g.txt'
    Move-Item -LiteralPath $ledger -Destination "$ledger.bak"
    $null = New-Item -ItemType Directory -Path $ledger
    $r = Run
    $r2 = Run
    Check 'ledger cannot be written: notifies once, the tree is not rerun' ((& $runs) -eq 10 -and $r.Text -match '记不进账' -and $r.Text -match 'title: .*主干全量记不进账' -and $r2.Text -match '上次跑完记不进账' -and (& $runs) -eq 10)
    Remove-Item -LiteralPath $ledger -Recurse
    Move-Item -LiteralPath "$ledger.bak" -Destination $ledger

    $m = Join-Path $root 'm'
    $null = New-Item -ItemType Directory -Force -Path $m
    git -c init.defaultBranch=master init -q $m
    Set-Content -LiteralPath (Join-Path $m '.gitignore') -Encoding utf8NoBOM -Value '.agents/'
    G -C $m add -A; G -C $m commit -q -m one
    $cfgMain = $cfg; $cfg = Join-Path $root 'm.json'
    @{ projects = @(@{ name = 'M'; path = $m; status = '推进中'; trunkVerify = $verify }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfg -Encoding utf8NoBOM
    $r = Run
    Check 'no trunk written, the checkout is on master: runs master' ((& $runs) -eq 11 -and $r.Text -match '：green')
    Set-Content -LiteralPath (Join-Path $m '.gitignore') -Encoding utf8NoBOM -Value 'x'
    G -C $m add -A; G -C $m commit -q -m 'stop ignoring'
    $r = Run
    $st = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'status.ps1') -Config $cfg -All -Json | ConvertFrom-Json
    Check '.agents/ not ignored: skipped with the reason, status says so' ((& $runs) -eq 11 -and $r.Text -match '没被 Git 忽略' -and [bool](@($st.Projects[0].Problems) -match '合并后全量'))
    $cfg = $cfgMain
}
finally {
    Remove-Item Env:AI_DEV_FLOW_BUSY_MARK -ErrorAction SilentlyContinue
    if ($Keep) { "fixture kept: $root" } else { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }
}
if ($fail) { "$fail check(s) failed"; exit 1 }
'all checks passed'
