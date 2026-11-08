param([string]$Dir = $PSScriptRoot, [string]$Repo = (Join-Path $PSScriptRoot '..'))
# 并行跑全部检查：tests 下的 *.tests.ps1（run-all.tests.ps1 除外）和文档格式检查。各测试都建自己的临时目录，互不影响。
#   pwsh -NoProfile -File tests/run-all.ps1
# 逐项打出退出码和用时，失败的再打出 FAIL 行；最后一行是"快检用时：<秒> 秒"，验证方照抄。全部通过退出 0，否则退出 1。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$pwshPath = (Get-Process -Id $PID).Path
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("run-all-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$null = New-Item -ItemType Directory -Force -Path $tmp
$jobs = @(foreach ($f in Get-ChildItem -LiteralPath $Dir -Filter '*.tests.ps1' | Where-Object Name -ne 'run-all.tests.ps1') { [pscustomobject]@{ Name = $f.BaseName; Args = @('-NoProfile', '-File', $f.FullName) } })
$checkMd = Join-Path $Repo 'skills/ai-dev-flow/scripts/check-md.ps1'
if (Test-Path -LiteralPath $checkMd) { $jobs += [pscustomobject]@{ Name = 'check-md.ps1'; Args = @('-NoProfile', '-File', (Resolve-Path -LiteralPath $checkMd).ProviderPath, '-Repo', (Resolve-Path -LiteralPath $Repo).ProviderPath) } }
$start = Get-Date
foreach ($j in $jobs) {
    $log = Join-Path $tmp "$($j.Name).log"
    $p = Start-Process -FilePath $pwshPath -ArgumentList ($j.Args | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -RedirectStandardOutput $log -RedirectStandardError "$log.err" -NoNewWindow -PassThru
    $null = $p.Handle
    $j | Add-Member -NotePropertyName Proc -NotePropertyValue $p
    $j | Add-Member -NotePropertyName Log -NotePropertyValue $log
}
$failed = 0
foreach ($j in $jobs) {
    $j.Proc.WaitForExit()
    $code = $j.Proc.ExitCode
    $secs = [int]($j.Proc.ExitTime - $j.Proc.StartTime).TotalSeconds
    "$($j.Name)：退出 $code，$secs 秒"
    if ($code) {
        $failed++
        Get-Content -LiteralPath $j.Log, "$($j.Log).err" -Encoding UTF8 -ErrorAction SilentlyContinue | Where-Object { $_ -match '^FAIL|rror' } | Select-Object -First 20 | ForEach-Object { "  $_" }
    }
}
if ($failed) { "$failed 项没过（完整输出在 $tmp）" } else { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
"快检用时：$([int]((Get-Date) - $start).TotalSeconds) 秒"
if ($failed) { exit 1 }
exit 0
