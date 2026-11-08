param([string]$Script = (Join-Path $PSScriptRoot 'run-all.ps1'))
# run-all.ps1 自己的检查：用几个假的测试文件断言并行、退出码、FAIL 行和用时。不会被 run-all.ps1 带上，改了 run-all.ps1 单独跑。
#   pwsh -NoProfile -File tests/run-all.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("run-all-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$null = New-Item -ItemType Directory -Force -Path $root
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function Run { $o = @(pwsh -NoProfile -File $Script -Dir $root -Repo $root 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Text = ($o -join "`n"); Code = $LASTEXITCODE } }
try {
    "Start-Sleep 3; 'ok   a'; exit 0" | Set-Content -LiteralPath (Join-Path $root 'a.tests.ps1') -Encoding utf8NoBOM
    "Start-Sleep 3; 'ok   b'; exit 0" | Set-Content -LiteralPath (Join-Path $root 'b b.tests.ps1') -Encoding utf8NoBOM
    "throw 'must not run'" | Set-Content -LiteralPath (Join-Path $root 'run-all.tests.ps1') -Encoding utf8NoBOM
    $r = Run
    Check 'all pass: exit 0, every suite listed, a path with a space works' ($r.Code -eq 0 -and $r.Text -match 'a\.tests：退出 0' -and $r.Text -match 'b b\.tests：退出 0')
    Check 'its own test file is left out' ($r.Text -notmatch 'run-all\.tests')
    $sec = [regex]::Match($r.Out[-1], '^快检用时：(\d+) 秒$')
    Check 'last line is the time, in the form land-check reads' ($sec.Success)
    Check 'suites run in parallel' ($sec.Success -and [int]$sec.Groups[1].Value -lt 6)

    "'ok   fine'; 'FAIL the broken check'; exit 1" | Set-Content -LiteralPath (Join-Path $root 'c.tests.ps1') -Encoding utf8NoBOM
    $r = Run
    Check 'one fails: exit 1, names it, shows the FAIL line, still gives the time' ($r.Code -eq 1 -and $r.Text -match 'c\.tests：退出 1' -and $r.Text -match 'FAIL the broken check' -and $r.Out[-1] -match '^快检用时：')
} finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
if ($fail) { "$fail failed"; exit 1 }
'all passed'
exit 0
