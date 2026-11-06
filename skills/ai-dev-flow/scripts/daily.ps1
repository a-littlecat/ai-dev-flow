[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Out,
    [int]$StaleMinutes = 60,
    [string]$State,
    [switch]$NoNotify,
    [switch]$DryRun
)
# 状态页：跑 status.ps1，把结果写成一页 HTML，再发一条通知（点开就是这一页）。给计划任务定时跑，不花模型额度。
#   -Config   总览仓库的 projects.json（同 status.ps1）
#   -Out      页面写到哪里，默认 %LOCALAPPDATA%\ai-dev-flow\status.html
#   -NoNotify 只生成页面
#   -State    上次通知推过哪些事，默认 %LOCALAPPDATA%\ai-dev-flow\daily-state.json
#   -DryRun   通知只打印不发（传给 notify.ps1），也不改 -State
# 页面固定三块：① 要你做（编号，附要发的命令）② 本周目标 ③ 各项目（状态标签，加 现在 / 进度 / 北极星 / 接下来 / 最近完成 五行，其余收进"细节"）。
# 有待用户的项或可能停滞的项目时，通知级别为 user（按 notify.json 的配置会推到手机），否则为 info。
# 只在有上次没推过的事时才用 user：和上次推过的一样，就降成 info，只弹系统通知，不再推手机。通知发不出去时不记，下次照常推。
# 状态脚本标成"像搁置"的待用户项（Hint，见 status.ps1）不算要你管的事，单列在页面上，附改成搁置的命令。
# 推进中的项目没有在做的项、但最近 StaleMinutes 分钟内有动静的，标"刚有动静"，不算空着：会话可能正在两项之间。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
if (-not $Out) { $Out = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/status.html' }
$Out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)
if (-not $State) { $State = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/daily-state.json' }
$State = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($State)

$statusArgs = @('-Json', '-StaleMinutes', $StaleMinutes)
if ($Config) { $statusArgs += '-Config', $Config }
$json = & pwsh -NoProfile -File (Join-Path $here 'status.ps1') @statusArgs | Out-String
if ($LASTEXITCODE) { throw "status.ps1 failed: $json" }
$s = $json | ConvertFrom-Json

function Enc($v) { [Net.WebUtility]::HtmlEncode([string]$v) }
function Cut([string]$t, [int]$n) { $t = ($t -replace '\s+', ' ').Trim(); if ($t.Length -gt $n) { $t.Substring(0, $n - 1) + '…' } else { $t } }
function Nick([string]$name) { $n = $name -replace '^\d+\s*', ''; if ($n) { $n } else { $name } }
function Ago($m) { if ($null -eq $m) { '' } elseif ($m -lt 60) { "$m 分钟" } elseif ($m -lt 2880) { "$([math]::Floor($m / 60)) 小时" } else { "$([math]::Floor($m / 1440)) 天" } }
function Item($i, [int]$n = 24) { $t = "$(if ($i.Id) { '#' + (Cut $i.Id 8) }) $(Cut $i.Goal $n)".Trim(); if ($t) { $t } else { '未命名的一项' } }
function Lines($list, [int]$n = 28) { $x = @($list | Where-Object { $_ }); if ($x) { ($x | ForEach-Object { Enc (Item $_ $n) }) -join '<br>' } else { '无' } }
function Answer($i) { if ($i.Id) { "/next #$(($i.Id -replace '^#', '').Trim()) 你的答复" } else { '/next 你的答复' } }
function IsStalled($p) { [bool](@($p.Problems) -match '^可能停滞') }
function Asks($p) { @(@($p.Waiting) | Where-Object { $_.Hint -ne '像搁置' }) }
function Recent($p) { $null -ne $p.IdleMinutes -and $p.IdleMinutes -lt $StaleMinutes }
function Label($i) { if ($i.Id) { '#' + (($i.Id -replace '^#', '').Trim()) } else { "「$(Cut $i.Goal 20)」" } }
# 状态标签：可能停了 > 等你 > 在做 > 刚有动静 > 空着 > 没活；维护中的项目单列
function State($p) {
    if ($p.Status -eq '维护') { return @('维护中', 'muted') }
    if (IsStalled $p) { return @('可能停了', 'bad') }
    if ((Asks $p).Count) { return @('等你', 'warn') }
    if (@($p.Doing).Count) { return @('在做', 'ok') }
    if ($p.Available -and (Recent $p)) { return @('刚有动静', 'ok') }
    if ($p.Available) { return @('空着，可开工', 'idle') }
    @('没有能做的项', 'muted')
}

$active = @($s.Projects)
$waiting = @(foreach ($p in $active) { foreach ($w in Asks $p) { [pscustomobject]@{ Project = $p.Name; Item = $w } } })
$shelvedLike = @(foreach ($p in $active) { foreach ($w in @(@($p.Waiting) | Where-Object { $_.Hint -eq '像搁置' })) { [pscustomobject]@{ Project = $p.Name; Item = $w } } })
$stalled = @($active | Where-Object { IsStalled $_ })
$free = @($active | Where-Object { $_.Status -eq '推进中' -and $_.Available -and -not @($_.Doing).Count -and -not (IsStalled $_) -and -not (Recent $_) })
$n = $waiting.Count + $stalled.Count
$summary = @(if ($n) { "要你管 $n 件事" } else { '暂时没有要你管的事' }) +
    @($active | Where-Object Status -eq '推进中' | ForEach-Object { "$(Nick $_.Name)：$((State $_)[0])" })

$b = [Text.StringBuilder]::new()
$null = $b.Append(@"
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>项目状态</title><style>
:root{--bg:#f6f6f3;--card:#fff;--fg:#1d1d1b;--muted:#6f6f69;--line:#e4e4df;--warn:#a85d00;--warnbg:#fdf1dc;--bad:#b42318;--badbg:#fde7e4;--ok:#17703a;--okbg:#e2f3e7;--idle:#3d5a99;--idlebg:#e6ecf8;--chip:#efefea;--bar:#2f7d4f}
@media (prefers-color-scheme:dark){:root{--bg:#151514;--card:#1f1f1d;--fg:#ececea;--muted:#a0a09a;--line:#33332f;--warn:#f5b24a;--warnbg:#3a2c12;--bad:#f87171;--badbg:#3b1714;--ok:#6ad08c;--okbg:#15301f;--idle:#93b0ee;--idlebg:#1c2740;--chip:#2a2a27;--bar:#4fae75}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 56px}h1{font-size:22px;margin:0}h2{font-size:16px;margin:30px 0 10px}
.muted{color:var(--muted)}.lead{margin:6px 0 0;font-size:15px}.ok{color:var(--ok)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.card h3{font-size:16px;margin:0 0 10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.tag{font-size:12px;font-weight:600;border-radius:999px;padding:1px 9px}
.tag.bad{color:var(--bad);background:var(--badbg)}.tag.warn{color:var(--warn);background:var(--warnbg)}.tag.ok{color:var(--ok);background:var(--okbg)}
.tag.idle{color:var(--idle);background:var(--idlebg)}.tag.muted{color:var(--muted);background:var(--chip)}
.pri{margin-left:auto;font-size:12px;color:var(--muted);font-weight:400}
.grid{display:grid;grid-template-columns:4.8em 1fr;gap:5px 12px}.grid>.k{color:var(--muted);font-size:13px;padding-top:1px}
.bar{display:inline-block;width:120px;height:8px;background:var(--chip);border-radius:4px;vertical-align:middle;margin-right:8px;overflow:hidden}.bar>span{display:block;height:100%;background:var(--bar)}
ol{margin:0;padding-left:22px}ol li{margin:0 0 10px}ol li:last-child{margin:0}.how{color:var(--muted);font-size:13px}
code{background:var(--chip);border-radius:4px;padding:1px 6px;font-size:13px;user-select:all}
.goals{display:grid;grid-template-columns:auto 1fr;gap:4px 14px}.goals .p{font-weight:600}.goals>*{min-width:0;overflow-wrap:anywhere}
details{margin-top:10px}summary{cursor:pointer;color:var(--muted);font-size:13px}details div{font-size:13px;color:var(--muted);margin:3px 0;overflow-wrap:anywhere}
</style></head><body><main>
<h1>项目状态</h1><div class="muted">$(Enc $s.Generated)</div>
<p class="lead">$(Enc ($summary -join '；'))</p>
"@)

# ① 要你做
$todo = [Collections.Generic.List[string]]::new()
foreach ($w in $waiting) {
    $i = $w.Item
    $why = if ($i.Detail) { '：' + (Enc (Cut $i.Detail 120)) } else { '' }
    $todo.Add("<li><b>$(Enc (Nick $w.Project))</b> 等你定 $(Enc (Item $i 40))$why<div class=`"how`">到这个项目新建会话，发 <code>$(Enc (Answer $i))</code>；同意推荐就回 <code>按你的</code></div></li>")
}
foreach ($p in $stalled) {
    $d = @($p.Doing)[0]
    $todo.Add("<li><b>$(Enc (Nick $p.Name))</b> 可能停了：$(if ($d) { Enc (Item $d 40) } else { '在做的项' }) 已经 $(Ago $p.IdleMinutes)没动静<div class=`"how`">到这个项目新建会话，发 <code>/next$(if ($d -and $d.Id) { ' #' + (Enc (($d.Id -replace '^#', '').Trim())) })</code> 接着做</div></li>")
}
foreach ($w in $shelvedLike) {
    $i = $w.Item
    $todo.Add("<li><b>$(Enc (Nick $w.Project))</b> 像是已经说过先不做：$(Enc (Item $i 40))$(if ($i.Detail) { '：' + (Enc (Cut $i.Detail 120)) })<div class=`"how`">不算要你管的事。下次在这个项目发 /next 时带上 <code>$(Enc "$(Label $i) 改成搁置")</code>；其实还要你定的，直接回答案</div></li>")
}
foreach ($p in $free) { $todo.Add("<li><b>$(Enc (Nick $p.Name))</b> 空着，有 $($p.Available) 项可以开工<div class=`"how`">到这个项目新建会话，发 <code>/next</code></div></li>") }
$null = $b.Append('<h2>① 要你做</h2><div class="card">')
$null = $b.Append($(if ($todo.Count) { '<ol>' + ($todo -join '') + '</ol>' } else { '<span class="muted">暂时没有要你处理的事</span>' }) + '</div>')

# ② 本周目标
$null = $b.Append('<h2>② 本周目标</h2><div class="card">')
$withGoals = @($active | Where-Object { @($_.Goals).Count })
if ($withGoals) {
    $null = $b.Append('<div class="goals">')
    foreach ($p in $withGoals) {
        $g = @($p.Goals)
        $list = ($g | ForEach-Object { "<span class=`"$(if ($_.Done) { 'ok' })`">$(if ($_.Done) { '✓' } else { '○' }) $(Enc $_.Text)</span>" }) -join '<br>'
        $null = $b.Append("<div class=`"p`">$(Enc (Nick $p.Name))<div class=`"muted`" style=`"font-weight:400;font-size:13px`">完成 $(@($g | Where-Object Done).Count)/$($g.Count)</div></div><div>$list</div>")
    }
    $null = $b.Append('</div>')
} else { $null = $b.Append('<span class="muted">还没定，周会（<code>/week</code>）时定</span>') }
$null = $b.Append('</div>')

# ③ 各项目
$null = $b.Append('<h2>③ 各项目</h2>')
foreach ($p in $active) {
    $st = State $p
    $doing = @($p.Doing)
    $now = if (IsStalled $p) { "$(Lines $doing)<br><span class=`"muted`">$(Ago $p.IdleMinutes)没动静</span>" }
           elseif ($doing) { Lines $doing }
           elseif ((Asks $p).Count) { "等你定：$(Lines (Asks $p))" }
           elseif ($p.Available -and (Recent $p)) { "刚有动静（$(Ago $p.IdleMinutes)前），有 $($p.Available) 项可领" }
           elseif ($p.Available) { "空着，有 $($p.Available) 项可以开工" }
           elseif ($p.Queue) { '没有能做的项' } else { '还没有队列' }
    $prog = if ($p.Queue) {
        $q = $p.Queue; $total = 0; foreach ($v in $q.PSObject.Properties) { if ($v.Name -ne '搁置') { $total += [int]$v.Value } }
        $done = [int]$q.'完成'; $pct = if ($total) { [math]::Round(100 * $done / $total) } else { 0 }
        "<span class=`"bar`"><span style=`"width:$pct%`"></span></span>完成 $done / 共 $total 项"
    } else { '<span class="muted">—</span>' }
    $star = @(@($p.Digest.Lines) | Where-Object { $_ -match '^北极星' }) | Select-Object -First 1
    $starHtml = if ($star) { "$(Enc (Cut ($star -replace '^北极星[：:]\s*', '') 70)) <span class=`"muted`">（$(Enc $p.Digest.Date) 复盘）</span>" } else { '<span class="muted">还没有复盘数据</span>' }

    $pri = if ($null -ne $p.Priority) { '<span class="pri">优先级 ' + $p.Priority + '</span>' } else { '' }
    $null = $b.Append("<div class=`"card`"><h3>$(Enc (Nick $p.Name))<span class=`"tag $($st[1])`">$(Enc $st[0])</span>$pri</h3><div class=`"grid`">")
    $null = $b.Append("<div class=`"k`">现在</div><div>$now</div>")
    $null = $b.Append("<div class=`"k`">进度</div><div>$prog</div>")
    $null = $b.Append("<div class=`"k`">北极星</div><div>$starHtml</div>")
    $null = $b.Append("<div class=`"k`">接下来</div><div>$(Lines $p.Next)</div>")
    $null = $b.Append("<div class=`"k`">最近完成</div><div>$(Lines $p.Recent)</div>")
    $null = $b.Append('</div>')

    $det = [Collections.Generic.List[string]]::new()
    $other = @($p.Other)
    if ($other) { $det.Add("队列里有 $($other.Count) 项的状态写法不标准，下次在这个项目发 /next 会顺手改好") }
    if ($p.Queue) { $q = $p.Queue; $det.Add("队列：在做 $($q.'在做') · 待做 $($q.'待做')（可领 $($p.Available)） · 待验证 $($q.'待验证') · 等你 $($q.'待用户') · 完成 $($q.'完成')$(if ($q.'搁置') { " · 搁置 $($q.'搁置')" })$(if ($q.'其他') { " · 写法不标准 $($q.'其他')" })") }
    if ($p.LastActivity) { $det.Add("最后动静 $($p.LastActivity)（$(Ago $p.IdleMinutes)前）；主干新提交 $($p.NewCount)（$($p.NewSince)）") }
    if ($null -ne $p.Worktrees -and ($p.WorktreesMerged + $p.WorktreesDetached + $p.BranchesMerged)) { $det.Add("可以清理：已合并的分支 $($p.BranchesMerged) 个，临时工作目录 $($p.Worktrees) 个") }
    if ($p.Trust) { $det.Add("信任等级 $($p.Trust)") }
    foreach ($x in @($p.Problems) | Where-Object { $_ -notmatch '^(可能停滞|队列里状态认不出)' }) { $det.Add("提示：$(Cut $x 120)") }
    if ($det.Count) { $null = $b.Append('<details><summary>细节</summary>' + (($det | ForEach-Object { "<div>$(Enc $_)</div>" }) -join '') + '</details>') }
    $null = $b.Append('</div>')
}
if (@($s.Paused)) { $null = $b.Append("<div class=`"muted`" style=`"font-size:13px`">暂停：$(Enc ((@($s.Paused) | ForEach-Object { Nick $_ }) -join '、'))</div>") }
$null = $b.Append('</main></body></html>')

$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Out)
Set-Content -LiteralPath $Out -Value $b.ToString() -Encoding utf8NoBOM
$Out

if (-not $NoNotify) {
    # 每件要你管的事一个键（项目、编号、目标、问题前 60 字）；和上次推过的比，有新的才推手机。同一项换了问题算新的
    $events = @(
        foreach ($w in $waiting) { [pscustomobject]@{ Key = "$($w.Project)|$(Label $w.Item)|$(Cut $w.Item.Goal 40)|$(Cut $w.Item.Detail 60)"; Line = "$(Nick $w.Project)：$(Item $w.Item) 等你定"; Ask = $true } }
        foreach ($p in $stalled) { $d = @($p.Doing)[0]; [pscustomobject]@{ Key = "$($p.Name)|停滞|$((@($p.Doing) | ForEach-Object { $_.Id }) -join ',')|$($p.LastActivity)"; Line = "$(Nick $p.Name)：$(if ($d) { Item $d } else { '在做的项' }) 已 $(Ago $p.IdleMinutes)没动静，可能停了"; Ask = $false } }
    )
    $pushed = @(if (Test-Path -LiteralPath $State) {
        try { (Get-Content -LiteralPath $State -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop).pushed }
        catch { [Console]::Error.WriteLine("daily.ps1 ignores unreadable state ${State}: $($_.Exception.Message)") }
    })
    foreach ($e in $events) { $e | Add-Member -NotePropertyName New -NotePropertyValue ($pushed -notcontains $e.Key) }
    $fresh = @($events | Where-Object New)
    $mixed = $fresh.Count -and $fresh.Count -lt $events.Count
    $show = { param($e) "$(if ($mixed -and $e.New) { '新：' })$($e.Line)" }
    $asks = @(@($events | Where-Object { $_.Ask -and $_.New }) + @($events | Where-Object { $_.Ask -and -not $_.New }))
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($e in $asks | Select-Object -First 5) { $lines.Add((& $show $e)) }
    if ($asks.Count -gt 5) { $lines.Add("另有 $($asks.Count - 5) 件等你定，见状态页") }
    foreach ($e in $events | Where-Object { -not $_.Ask }) { $lines.Add((& $show $e)) }
    if ($shelvedLike) { $lines.Add("另有 $($shelvedLike.Count) 件像是已经说过先不做，不算要你管，见状态页") }
    if ($free) { $lines.Add("$((@($free | ForEach-Object { Nick $_.Name })) -join '、') 空着，可以发 /next 开工") }
    $title = if ($n -and -not $fresh) { "要你管 $n 件事（都推过）" } elseif ($n) { "要你管 $n 件事" } elseif ($free) { '有项目可以开工' } else { '暂时没有要你管的事' }
    if (-not $lines.Count) { $lines.Add('点开看各项目进度') }
    $level = if ($fresh) { 'user' } else { 'info' }
    $notifyArgs = @('-Title', $title, '-Body', ($lines -join "`n"), '-Level', $level, '-Open', $Out)
    if ($DryRun) { $notifyArgs += '-DryRun' }
    & pwsh -NoProfile -File (Join-Path $here 'notify.ps1') @notifyArgs
    $code = $LASTEXITCODE
    if (-not $DryRun -and -not $code) {
        $null = New-Item -ItemType Directory -Force -Path (Split-Path $State)
        $tmp = "$State.tmp"
        [ordered]@{ checked = (Get-Date).ToString('yyyy-MM-dd HH:mm'); pushed = @($events | ForEach-Object Key) } | ConvertTo-Json | Set-Content -LiteralPath $tmp -Encoding utf8NoBOM
        Move-Item -LiteralPath $tmp -Destination $State -Force
    }
    exit $code
}
