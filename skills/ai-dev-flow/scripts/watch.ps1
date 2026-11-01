[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [int]$StaleMinutes = 60,
    [string]$State,
    [switch]$DryRun
)
# 停滞检查：跑 status.ps1，只在有项目新变成"可能停滞"时发一条 stuck 通知（按 notify.json 的配置会推到手机）。给计划任务每小时跑，不花模型额度。
#   -Config        总览仓库的 projects.json（同 status.ps1）
#   -StaleMinutes  同 status.ps1，默认 60
#   -State         上次已经提醒过哪些停滞，默认 %LOCALAPPDATA%\ai-dev-flow\watch-state.json
#   -DryRun        通知只打印不发（传给 notify.ps1），也不改 -State
# 同一次停滞只提醒一次：项目、在做的项和最后活动时间都没变，就不再发。项目动过以后又停住，算新的一次。
# 通知发不出去时不记下这次停滞，下次检查会再发；退出码同 notify.ps1。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
if (-not $State) { $State = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/watch-state.json' }
$State = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($State)

$statusArgs = @('-Json', '-StaleMinutes', $StaleMinutes)
if ($Config) { $statusArgs += '-Config', $Config }
$json = & pwsh -NoProfile -File (Join-Path $here 'status.ps1') @statusArgs | Out-String
if ($LASTEXITCODE) { throw "status.ps1 failed: $json" }
$s = $json | ConvertFrom-Json

function Nick([string]$name) { $n = $name -replace '^\d+\s*', ''; if ($n) { $n } else { $name } }
function Ago($m) { if ($m -lt 60) { "$m 分钟" } elseif ($m -lt 2880) { "$([math]::Floor($m / 60)) 小时" } else { "$([math]::Floor($m / 1440)) 天" } }

$stalled = @($s.Projects | Where-Object { @($_.Problems) -match '^可能停滞' })
$now = [ordered]@{}
foreach ($p in $stalled) {
    $ids = (@($p.Doing) | ForEach-Object { $_.Id }) -join ','
    $now["$($p.Name)|$ids|$($p.LastActivity)"] = $p
}
$seen = @(if (Test-Path -LiteralPath $State) { (Get-Content -LiteralPath $State -Raw -Encoding UTF8 | ConvertFrom-Json).stalled })
$new = @($now.Keys | Where-Object { $seen -notcontains $_ })

$code = 0
if ($new) {
    $lines = foreach ($k in $new) {
        $p = $now[$k]; $d = @($p.Doing)[0]
        $what = if ($d) { "#$($d.Id) $(($d.Goal -replace '\s+', ' ').Trim())".Trim() } else { '在做的项' }
        if ($what.Length -gt 30) { $what = $what.Substring(0, 29) + '…' }
        "$(Nick $p.Name)：$what 已 $(Ago $p.IdleMinutes)没动静，回到那个会话看一眼，或新开会话发 /next"
    }
    $notifyArgs = @('-Title', "$($new.Count) 个项目可能停了", '-Body', ($lines -join "`n"), '-Level', 'stuck')
    if ($DryRun) { $notifyArgs += '-DryRun' }
    & pwsh -NoProfile -File (Join-Path $here 'notify.ps1') @notifyArgs
    $code = $LASTEXITCODE
} elseif ($DryRun) { 'no new stall' }

if (-not $DryRun -and -not $code) {
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $State)
    [ordered]@{ checked = (Get-Date).ToString('yyyy-MM-dd HH:mm'); stalled = @($now.Keys) } | ConvertTo-Json | Set-Content -LiteralPath $State -Encoding utf8NoBOM
}
exit $code
