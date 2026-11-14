param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/verify-ledger.ps1'), [switch]$Keep)
# verify-ledger.ps1 的检查：在系统临时目录建一个仓库和一个 worktree，用假的快检命令（写一行计数再按要求退出），断言同树已绿不重跑、树变了要跑、红的不算、记录读不了按没跑。退出码 0 才算通过。
#   pwsh -NoProfile -File tests/verify-ledger.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("verify-ledger-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$null = New-Item -ItemType Directory -Force -Path $root
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main @args; if ($LASTEXITCODE) { throw "git $args" } }
function Run([string]$repo, [string[]]$a) { $o = @(pwsh -NoProfile -File $Script -Repo $repo @a 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Code = $LASTEXITCODE } }

try {
    $repo = Join-Path $root 'repo'
    $null = New-Item -ItemType Directory -Force -Path $repo
    G init -q $repo
    Set-Content -LiteralPath (Join-Path $repo '.gitignore') -Encoding utf8NoBOM -Value '.agents/'
    Set-Content -LiteralPath (Join-Path $repo 'a.txt') -Encoding utf8NoBOM -Value '1'
    G -C $repo add -A; G -C $repo commit -q -m one
    $count = Join-Path $root 'runs.txt'
    # 假快检：每跑一次往计数文件写一行；退出码取环境变量 FAKE_EXIT（没设就是 0）。
    $verify = "Add-Content -LiteralPath '$count' -Value x; exit [int](`$env:FAKE_EXIT ?? 0)"
    $runs = { if (Test-Path -LiteralPath $count) { @(Get-Content -LiteralPath $count).Count } else { 0 } }
    $ledger = Join-Path $repo '.agents/verify-ledger.jsonl'

    $r = Run $repo @('-Command', $verify)
    Check 'first run: runs and records green' ($r.Code -eq 0 -and (& $runs) -eq 1 -and ($r.Out -join "`n") -match '记账：树 \w+ green')

    $wt = Join-Path $root 'wt'
    G -C $repo worktree add -q --detach $wt HEAD
    $r = Run $wt @('-Command', $verify)
    Check 'same tree in another worktree: already green, not rerun' ($r.Code -eq 0 -and (& $runs) -eq 1 -and ($r.Out -join "`n") -match '已绿')
    Check 'check: green tree exits 0' ((Run $wt @('-Check')).Code -eq 0)

    G -C $wt commit -q --allow-empty -m 'same tree, new commit'
    Check 'a new commit with the same tree still counts' ((Run $wt @('-Check')).Code -eq 0)

    Set-Content -LiteralPath (Join-Path $wt 'a.txt') -Encoding utf8NoBOM -Value '2'
    G -C $wt commit -q -am two
    $r = Run $wt @('-Check')
    Check 'tree changed: check exits 3' ($r.Code -eq 3)
    $env:FAKE_EXIT = '1'
    try { $r = Run $wt @('-Command', $verify) } finally { Remove-Item Env:FAKE_EXIT }
    Check 'red run: exit code passed through and recorded red' ($r.Code -eq 1 -and (& $runs) -eq 2 -and ($r.Out -join "`n") -match 'red')
    Check 'red does not count' ((Run $wt @('-Check')).Code -eq 3)
    $r = Run $wt @('-Command', $verify)
    Check 'after red: runs again, green now counts' ($r.Code -eq 0 -and (& $runs) -eq 3 -and (Run $wt @('-Check')).Code -eq 0)

    Set-Content -LiteralPath (Join-Path $wt 'a.txt') -Encoding utf8NoBOM -Value 'dirty'
    $r = Run $wt @('-Command', $verify)
    Check 'uncommitted tracked change: the green tree is not trusted, runs, records nothing' ($r.Code -eq 0 -and (& $runs) -eq 4 -and ($r.Out -join "`n") -match '没记账' -and @(Get-Content -LiteralPath $ledger).Count -eq 3)
    G -C $wt checkout -q -- a.txt

    Set-Content -LiteralPath $ledger -Encoding utf8NoBOM -Value 'not json'
    Check 'unreadable ledger counts as not run' ((Run $wt @('-Check')).Code -eq 3)

    $r = Run $repo @('-Record', '-Rev', 'HEAD', '-Result', 'green', '-Seconds', '42', '-Where', 'verify note')
    $c = Run $repo @('-Check', '-Json')
    $j = ($c.Out -join "`n") | ConvertFrom-Json
    Check 'record: a result from elsewhere goes into the ledger' ($c.Code -eq 0 -and $j.entry.seconds -eq 42 -and $j.entry.where -eq 'verify note')
}
finally {
    if ($Keep) { "fixture kept: $root" } else { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }
}
if ($fail) { "$fail check(s) failed"; exit 1 }
'all checks passed'
