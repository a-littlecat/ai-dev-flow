[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [int]$StaleMinutes = 60,
    [int]$IdleHours = 12,
    [int]$GoalHours = 24,
    [string]$State,
    [switch]$DryRun
)
# 停滞检查：跑 status.ps1，只在有项目新变成"可能停滞"时发一条 stuck 通知（按 notify.json 的配置会推到手机）。给计划任务每 15 分钟跑，不花模型额度；停住后最晚约 StaleMinutes + 15 分钟收到。
#   -Config        总览仓库的 projects.json（同 status.ps1）
#   -StaleMinutes  同 status.ps1，默认 60
#   -IdleHours     同 status.ps1，默认 12：有可领的项、没有在做的、这么多小时没动静，也推一次（"有活没人做"），不管有没有待用户项
#   -GoalHours     同 status.ps1，默认 24：项目有新提交、本周目标挂的项这么多小时没进展，也推一次（"本周目标没动"）
#   -State         上次已经提醒过哪些停滞，默认 %LOCALAPPDATA%\ai-dev-flow\watch-state.json
#   -DryRun        通知只打印不发（传给 notify.ps1），也不改 -State
# 同一次停滞只提醒一次：项目、在做的项和最后活动时间都没变，就不再发。项目动过以后又停住，算新的一次。"有活没人做"同样按项目和最后活动时间只提醒一次。
# 通知发不出去时不记下这次停滞，下次检查会再发；退出码同 notify.ps1。状态文件读不出来时当作没提醒过，照常检查。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
if (-not $State) { $State = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/watch-state.json' }
$State = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($State)

$statusArgs = @('-Json', '-StaleMinutes', $StaleMinutes, '-IdleHours', $IdleHours, '-GoalHours', $GoalHours)
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
$idle = @($s.Projects | Where-Object { @($_.Problems) -match '^有活没人做' })
foreach ($p in $idle) { $now["$($p.Name)|idle|$($p.LastActivity)"] = $p }
# 本周目标没动：同一批项、同一次最后进展只推一次；目标的项有了新提交、或换了目标，算新的一次。
foreach ($p in @($s.Projects | Where-Object { $_.GoalStalled })) { $now["$($p.Name)|goal|$((@($p.GoalStalled.Ids)) -join ',')|$($p.GoalStalled.Since)"] = $p }
$seen = @(if (Test-Path -LiteralPath $State) {
    try { (Get-Content -LiteralPath $State -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop).stalled }
    catch { [Console]::Error.WriteLine("watch.ps1 ignores unreadable state ${State}: $($_.Exception.Message)") }
})
$new = @($now.Keys | Where-Object { $seen -notcontains $_ })

$code = 0
if ($new) {
    $lines = foreach ($k in $new) {
        $p = $now[$k]
        if ($k -like '*|goal|*') { $g = $p.GoalStalled; "$(Nick $p.Name)：本周目标挂的 $((@($g.Ids) | ForEach-Object { "#$_" }) -join '、') 已 $(Ago $g.Minutes)没进展，项目却有新提交，看看是不是偏了"; continue }
        if ($k -like '*|idle|*') { "$(Nick $p.Name)：有 $($p.Available) 项可领，没人在做，已 $(Ago $p.IdleMinutes)没动静，在那个项目发 /next"; continue }
        $d = @($p.Doing)[0]
        $what = if ($d) { "$(if ($d.Id) { '#' + ($d.Id -replace '^#', '') }) $(($d.Goal -replace '\s+', ' ').Trim())".Trim() } else { '在做的项' }
        if ($what.Length -gt 30) { $what = $what.Substring(0, 29) + '…' }
        "$(Nick $p.Name)：$what 已 $(Ago $p.IdleMinutes)没动静，回到那个会话看一眼，或新开会话发 /next"
    }
    $notifyArgs = @('-Title', $(if (-not @($new | Where-Object { $_ -match '\|(idle|goal)\|' }).Count) { "$($new.Count) 个项目可能停了" } elseif (-not @($new | Where-Object { $_ -notlike '*|idle|*' }).Count) { "$($new.Count) 个项目有活没人做" } elseif (-not @($new | Where-Object { $_ -notlike '*|goal|*' }).Count) { "$($new.Count) 个项目本周目标没动" } else { "$($new.Count) 件事要你看一眼" }), '-Body', ($lines -join "`n"), '-Level', 'stuck')
    if ($DryRun) { $notifyArgs += '-DryRun' }
    & pwsh -NoProfile -File (Join-Path $here 'notify.ps1') @notifyArgs
    $code = $LASTEXITCODE
} elseif ($DryRun) { 'no new stall' }

if (-not $DryRun -and -not $code) {
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $State)
    $tmp = "$State.tmp"
    [ordered]@{ checked = (Get-Date).ToString('yyyy-MM-dd HH:mm'); stalled = @($now.Keys) } | ConvertTo-Json | Set-Content -LiteralPath $tmp -Encoding utf8NoBOM
    Move-Item -LiteralPath $tmp -Destination $State -Force
}
exit $code
