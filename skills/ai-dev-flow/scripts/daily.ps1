[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Out,
    [int]$StaleMinutes = 60,
    [switch]$NoNotify
)
# 状态页：跑 status.ps1，把结果写成一页 HTML，再发一条通知（点开就是这一页）。给计划任务定时跑，不花模型额度。
#   -Config   总览仓库的 projects.json（同 status.ps1）
#   -Out      页面写到哪里，默认 %LOCALAPPDATA%\ai-dev-flow\status.html
#   -NoNotify 只生成页面
# 有待用户的项或可能停滞的项目时，通知级别为 user（按 notify.json 的配置会推到手机），否则为 info。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
if (-not $Out) { $Out = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/status.html' }
$Out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)

$statusArgs = @('-Json', '-StaleMinutes', $StaleMinutes)
if ($Config) { $statusArgs += '-Config', $Config }
$json = & pwsh -NoProfile -File (Join-Path $here 'status.ps1') @statusArgs | Out-String
if ($LASTEXITCODE) { throw "status.ps1 failed: $json" }
$s = $json | ConvertFrom-Json

function Enc($v) { [Net.WebUtility]::HtmlEncode([string]$v) }
$active = @($s.Projects)
$waiting = @(foreach ($p in $active) { foreach ($w in @($p.Waiting)) { [pscustomobject]@{ Project = $p.Name; Item = $w } } })
$stalled = @($active | Where-Object { @($_.Problems) -match '^可能停滞' })
$free = @($active | Where-Object { $_.Status -eq '推进中' -and $_.Available -and -not ($_.Queue -and $_.Queue.'在做') })

$b = [Text.StringBuilder]::new()
$null = $b.Append(@"
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>项目状态</title><style>
:root{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--muted:#6b6b66;--line:#e4e4df;--warn:#b45309;--bad:#b91c1c;--ok:#15803d;--chip:#efefea}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#1f1f1d;--fg:#ececea;--muted:#a0a09a;--line:#33332f;--warn:#f59e0b;--bad:#f87171;--ok:#4ade80;--chip:#2a2a27}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
.muted{color:var(--muted)}.chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.chip{background:var(--chip);border-radius:999px;padding:4px 12px}
.chip b{font-weight:600}.warn{color:var(--warn)}.bad{color:var(--bad)}.ok{color:var(--ok)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.card h3{font-size:15px;margin:0 0 6px}ul{margin:4px 0;padding-left:20px}code{background:var(--chip);border-radius:4px;padding:1px 5px;font-size:13px}
.row{margin:3px 0}
</style></head><body><main>
<h1>项目状态</h1><div class="muted">$(Enc $s.Generated) 生成</div>
<div class="chips"><span class="chip">待你 <b>$($waiting.Count)</b></span><span class="chip">空闲可领 <b>$($free.Count)</b></span><span class="chip">可能停滞 <b>$($stalled.Count)</b></span></div>
"@)

$null = $b.Append('<h2>要你做</h2>')
if ($waiting) {
    foreach ($g in $waiting | Group-Object Project) {
        $null = $b.Append("<div class=`"card`"><h3>$(Enc $g.Name)</h3><ul>")
        foreach ($w in $g.Group) {
            $i = $w.Item
            $tier = if ($i.Tier) { ' <span class="muted">[' + (Enc $i.Tier) + ']</span>' } else { '' }
            $detail = if ($i.Detail) { '：' + (Enc $i.Detail) } else { '' }
            $null = $b.Append("<li><b>#$(Enc $i.Id)</b>$tier $(Enc $i.Goal)$detail</li>")
        }
        $null = $b.Append("</ul><div class=`"muted row`">在这个项目里新建会话，发 <code>/next #编号 你的答复</code>，比如 <code>/next #$(Enc $g.Group[0].Item.Id) 按你的</code></div></div>")
    }
} else { $null = $b.Append('<div class="muted">无</div>') }

if ($free) {
    $null = $b.Append('<h2>空闲可领</h2><div class="card"><ul>')
    foreach ($p in $free) { $null = $b.Append("<li>$(Enc $p.Name)：可领 $($p.Available) 项，新建会话发 <code>/next</code></li>") }
    $null = $b.Append('</ul></div>')
}

$null = $b.Append('<h2>各项目</h2>')
foreach ($p in $active) {
    $meta = @($p.Status) + @(if ($p.Trust) { $p.Trust }) + @(if ($null -ne $p.Priority) { "优先级 $($p.Priority)" })
    $null = $b.Append("<div class=`"card`"><h3>$(Enc $p.Name) <span class=`"muted`">· $(Enc ($meta -join ' · '))</span></h3>")
    if ($p.Digest) { foreach ($l in @($p.Digest.Lines) | Where-Object { $_ -match '^北极星' }) { $null = $b.Append("<div class=`"row`">$(Enc $l) <span class=`"muted`">（$(Enc $p.Digest.Date) 复盘）</span></div>") } }
    $goals = @($p.Goals)
    if ($goals) {
        $null = $b.Append("<div class=`"row`">本周目标 $(@($goals | Where-Object Done).Count)/$($goals.Count)</div><ul>")
        foreach ($g in $goals) { $null = $b.Append("<li class=`"$(if ($g.Done) { 'ok' })`">$(if ($g.Done) { '✓' } else { '○' }) $(Enc $g.Text)</li>") }
        $null = $b.Append('</ul>')
    }
    if ($p.Queue) {
        $q = $p.Queue
        $null = $b.Append("<div class=`"row`">队列：在做 $($q.'在做') · 待做 $($q.'待做')（可领 $($p.Available)） · 待验证 $($q.'待验证') · 待你 $($q.'待用户') · 完成 $($q.'完成')</div>")
    }
    if ($p.LastActivity) { $null = $b.Append("<div class=`"row muted`">最后活动 $(Enc $p.LastActivity)，主干新提交 $($p.NewCount)（$(Enc $p.NewSince)）</div>") }
    if ($null -ne $p.Worktrees -and ($p.WorktreesMerged + $p.WorktreesDetached + $p.BranchesMerged)) {
        $null = $b.Append("<div class=`"row muted`">待清理：已合并的分支 $($p.BranchesMerged)，worktree $($p.Worktrees)（分离头 $($p.WorktreesDetached)）</div>")
    }
    foreach ($x in @($p.Problems)) { $null = $b.Append("<div class=`"row $(if ($x -match '^可能停滞') { 'bad' } else { 'warn' })`">⚠ $(Enc $x)</div>") }
    $null = $b.Append('</div>')
}
if (@($s.Paused)) { $null = $b.Append("<div class=`"muted row`">暂停：$(Enc (@($s.Paused) -join '、'))</div>") }
$null = $b.Append('</main></body></html>')

$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Out)
Set-Content -LiteralPath $Out -Value $b.ToString() -Encoding utf8NoBOM
$Out

if (-not $NoNotify) {
    $parts = @("待你 $($waiting.Count)")
    if ($free) { $parts += "空闲可领：$(($free | ForEach-Object Name) -join '、')" }
    if ($stalled) { $parts += "可能停滞：$(($stalled | ForEach-Object Name) -join '、')" }
    $level = if ($waiting -or $stalled) { 'user' } else { 'info' }
    & pwsh -NoProfile -File (Join-Path $here 'notify.ps1') -Title "项目状态 $(Get-Date -Format 'HH:mm')" -Body ($parts -join ' · ') -Level $level -Open $Out
    exit $LASTEXITCODE
}
