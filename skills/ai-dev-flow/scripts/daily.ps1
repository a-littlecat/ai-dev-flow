[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Out,
    [int]$StaleMinutes = 60,
    [switch]$NoNotify,
    [switch]$DryRun
)
# 状态页：跑 status.ps1，把结果写成一页 HTML，再发一条通知（点开就是这一页）。给计划任务定时跑，不花模型额度。
#   -Config   总览仓库的 projects.json（同 status.ps1）
#   -Out      页面写到哪里，默认 %LOCALAPPDATA%\ai-dev-flow\status.html
#   -NoNotify 只生成页面
#   -DryRun   通知只打印不发（传给 notify.ps1）
# 页面和通知都用白话：每个项目先一句结论，计数和提示收进"细节"。
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
function Cut([string]$t, [int]$n) { $t = ($t -replace '\s+', ' ').Trim(); if ($t.Length -gt $n) { $t.Substring(0, $n - 1) + '…' } else { $t } }
function Nick([string]$name) { $n = $name -replace '^\d+\s*', ''; if ($n) { $n } else { $name } }
function Ago($m) { if ($null -eq $m) { '' } elseif ($m -lt 60) { "$m 分钟" } elseif ($m -lt 2880) { "$([math]::Floor($m / 60)) 小时" } else { "$([math]::Floor($m / 1440)) 天" } }
function Item($i) { "$(if ($i.Id) { '#' + (Cut $i.Id 8) }) $(Cut $i.Goal 24)".Trim() }
function Answer($i) { if ($i.Id) { "/next #$(Cut $i.Id 8) 你的答复" } else { '/next 你的答复' } }

$active = @($s.Projects)
$waiting = @(foreach ($p in $active) { foreach ($w in @($p.Waiting)) { [pscustomobject]@{ Project = $p.Name; Item = $w } } })
$stalled = @($active | Where-Object { @($_.Problems) -match '^可能停滞' })
$free = @($active | Where-Object { $_.Status -eq '推进中' -and $_.Available -and -not @($_.Doing).Count })

$b = [Text.StringBuilder]::new()
$null = $b.Append(@"
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>项目状态</title><style>
:root{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--muted:#6b6b66;--line:#e4e4df;--warn:#b45309;--bad:#b91c1c;--ok:#15803d;--chip:#efefea}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#1f1f1d;--fg:#ececea;--muted:#a0a09a;--line:#33332f;--warn:#f59e0b;--bad:#f87171;--ok:#4ade80;--chip:#2a2a27}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
.muted{color:var(--muted)}.warn{color:var(--warn)}.bad{color:var(--bad)}.ok{color:var(--ok)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.card h3{font-size:16px;margin:0 0 6px}ul{margin:4px 0;padding-left:20px}code{background:var(--chip);border-radius:4px;padding:1px 5px;font-size:13px}
.row{margin:4px 0}.say{font-size:15px;margin:2px 0 6px}details{margin-top:8px}summary{cursor:pointer;color:var(--muted);font-size:13px}
details .row{font-size:13px;color:var(--muted);overflow-wrap:anywhere}
</style></head><body><main>
<h1>项目状态</h1><div class="muted">$(Enc $s.Generated) 生成</div>
"@)

$null = $b.Append('<h2>要你做</h2>')
$todo = [Collections.Generic.List[string]]::new()
foreach ($g in $waiting | Group-Object Project) {
    foreach ($w in $g.Group) {
        $i = $w.Item
        $detail = if ($i.Detail) { '：' + (Enc (Cut $i.Detail 120)) } else { '' }
        $todo.Add("<li><b>$(Enc (Nick $g.Name))</b> $(Enc (Item $i))$detail<br><span class=`"muted`">去这个项目新建会话，发 <code>$(Enc (Answer $i))</code>（同意推荐就回 <code>按你的</code>）</span></li>")
    }
}
foreach ($p in $stalled) {
    $d = @($p.Doing)[0]
    $what = if ($d) { Enc (Item $d) } else { '在做的项' }
    $todo.Add("<li><b>$(Enc (Nick $p.Name))</b> $what 已经 $(Ago $p.IdleMinutes)没动静，可能停了<br><span class=`"muted`">去这个项目新建会话，发 <code>/next$(if ($d) { ' #' + (Enc (Cut $d.Id 8)) })</code> 接着做</span></li>")
}
foreach ($p in $free) { $todo.Add("<li><b>$(Enc (Nick $p.Name))</b> 空着，有 $($p.Available) 项可以开工<br><span class=`"muted`">去这个项目新建会话，发 <code>/next</code></span></li>") }
if ($todo.Count) { $null = $b.Append('<div class="card"><ul>' + ($todo -join '') + '</ul></div>') } else { $null = $b.Append('<div class="card muted">无，都在正常推进</div>') }

$null = $b.Append('<h2>各项目</h2>')
foreach ($p in $active) {
    $doing = @($p.Doing); $nWait = @($p.Waiting).Count
    $isStalled = [bool](@($p.Problems) -match '^可能停滞')
    $say = [Collections.Generic.List[string]]::new()
    if ($nWait) { $say.Add("<div class=`"say warn`">有 $nWait 件事等你定</div>") }
    if ($isStalled) { $say.Add("<div class=`"say bad`">在做的项已经 $(Ago $p.IdleMinutes)没动静，可能停了</div>") }
    elseif ($doing) { $say.Add("<div class=`"say`">正在做：$(Enc ((@($doing | ForEach-Object { Item $_ }) -join '；')))</div>") }
    if (-not $doing -and $p.Available) { $say.Add("<div class=`"say`">空着，有 $($p.Available) 项可以开工</div>") }
    if (-not $say.Count -and $p.Queue) { $say.Add('<div class="say muted">队列里暂时没有能做的项</div>') }
    if (-not $p.Queue) { $say.Add('<div class="say muted">还没有队列</div>') }

    $null = $b.Append("<div class=`"card`"><h3>$(Enc (Nick $p.Name)) <span class=`"muted`">$(Enc $p.Status)$(if ($null -ne $p.Priority) { " · 优先级 $($p.Priority)" })</span></h3>" + ($say -join ''))
    $goals = @($p.Goals)
    if ($goals) {
        $null = $b.Append("<div class=`"row`">本周目标 $(@($goals | Where-Object Done).Count)/$($goals.Count)</div><ul>")
        foreach ($g in $goals) { $null = $b.Append("<li class=`"$(if ($g.Done) { 'ok' })`">$(if ($g.Done) { '✓' } else { '○' }) $(Enc $g.Text)</li>") }
        $null = $b.Append('</ul>')
    }
    if ($p.Digest) { foreach ($l in @($p.Digest.Lines) | Where-Object { $_ -match '^北极星' }) { $null = $b.Append("<div class=`"row muted`">$(Enc (Cut $l 90))（$(Enc $p.Digest.Date) 复盘）</div>") } }
    $other = @($p.Other)
    if ($other) { $null = $b.Append("<div class=`"row muted`">队列里有 $($other.Count) 项的状态写法不标准，下次在这个项目发 <code>/next</code> 会顺手改好</div>") }

    $det = [Collections.Generic.List[string]]::new()
    if ($p.Queue) { $q = $p.Queue; $det.Add("队列：在做 $($q.'在做') · 待做 $($q.'待做')（可领 $($p.Available)） · 待验证 $($q.'待验证') · 待你 $($q.'待用户') · 完成 $($q.'完成')$(if ($q.'其他') { " · 写法不标准 $($q.'其他')" })") }
    if ($p.LastActivity) { $det.Add("最后活动 $($p.LastActivity)（$(Ago $p.IdleMinutes)前）；主干新提交 $($p.NewCount)（$($p.NewSince)）") }
    if ($null -ne $p.Worktrees -and ($p.WorktreesMerged + $p.WorktreesDetached + $p.BranchesMerged)) { $det.Add("可以清理：已合并的分支 $($p.BranchesMerged) 个，临时工作目录 $($p.Worktrees) 个") }
    if ($p.Trust) { $det.Add("信任等级 $($p.Trust)") }
    foreach ($x in @($p.Problems) | Where-Object { $_ -notmatch '^(可能停滞|队列里状态认不出)' }) { $det.Add("提示：$(Cut $x 120)") }
    $null = $b.Append('<details><summary>细节</summary>' + (($det | ForEach-Object { "<div class=`"row`">$(Enc $_)</div>" }) -join '') + '</details></div>')
}
if (@($s.Paused)) { $null = $b.Append("<div class=`"muted row`">暂停：$(Enc ((@($s.Paused) | ForEach-Object { Nick $_ }) -join '、'))</div>") }
$null = $b.Append('</main></body></html>')

$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Out)
Set-Content -LiteralPath $Out -Value $b.ToString() -Encoding utf8NoBOM
$Out

if (-not $NoNotify) {
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($w in $waiting | Select-Object -First 2) { $lines.Add("$(Nick $w.Project)：$(Item $w.Item) 等你定") }
    if ($waiting.Count -gt 2) { $lines.Add("另有 $($waiting.Count - 2) 件等你定") }
    foreach ($p in $stalled) { $d = @($p.Doing)[0]; $lines.Add("$(Nick $p.Name)：$(if ($d) { Item $d } else { '在做的项' }) 已 $(Ago $p.IdleMinutes)没动静，可能停了") }
    if ($free) { $lines.Add("$((@($free | ForEach-Object { Nick $_.Name })) -join '、') 空着，可以发 /next 开工") }
    $n = $waiting.Count + $stalled.Count
    $title = if ($n) { "要你管 $n 件事" } elseif ($free) { '有项目可以开工' } else { '项目都在正常推进' }
    if (-not $lines.Count) { $lines.Add('没有要你做的事') }
    $level = if ($n) { 'user' } else { 'info' }
    $notifyArgs = @('-Title', $title, '-Body', ($lines -join "`n"), '-Level', $level, '-Open', $Out)
    if ($DryRun) { $notifyArgs += '-DryRun' }
    & pwsh -NoProfile -File (Join-Path $here 'notify.ps1') @notifyArgs
    exit $LASTEXITCODE
}
