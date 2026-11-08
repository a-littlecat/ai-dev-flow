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
# 页面：顶上一句话、四个数字、全部项目一览（一个项目一行，点了跳到卡片）；下面三块：要你做（按项目分组，问题、推荐、要发的命令分开）、本周目标、各项目
# （状态标签、进度，加 现在 / 北极星 / 接下来 / 最近完成，空的不显示，其余收进"细节"；维护中的项目收起来）。队列原文的 Markdown 记号不上页面，长句只显示第一句，悬停看全文。
# 有待用户的项或可能停滞的项目时，通知级别为 user（按 notify.json 的配置会推到手机），否则为 info。
# 只在有上次没推过的事时才用 user：和上次推过的一样，就降成 info，只弹系统通知，不再推手机。通知发不出去时不记，下次照常推。
# 状态脚本标成"像搁置"的待用户项（Hint，见 status.ps1）照常算要你管，排在最后、标"像已搁置"，附改成搁置的命令；判断靠关键词，可能判错，所以不拿掉。
# 推进中的项目没有在做的项、但最近 StaleMinutes 分钟内有动静的，标"刚有动静"，不算空着：会话可能正在两项之间。
# 基准和决定卡（status.ps1 的 Direction，modules/direction.md）：每张项目卡多"和基准比"（并排图缩略图，点开看大图）、"差距趋势"（按周小图）、"流程图"（docs/flow.html 的链接）三行；
# 待定的决定卡显示在"要你做"：挂在提到它的待用户项下面，没有这样的项就单独一条。方向要停、又没有在处理的（待用户或在做的项目标写着"方向复盘：<这个方向>"）也进"要你做"。
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
# 队列原文里的 Markdown 记号不上页面。
function Plain([string]$t) { (($t -replace '\*\*|`', '') -replace '\s+', ' ').Trim() }
# 短标题：到第一句为止（第一句太短的不断），超长再截断；全文放在悬停提示里。
function Brief([string]$t, [int]$n = 42) {
    $p = Plain $t
    $m = [regex]::Match($p, '[。；;：:（(]')
    if ($m.Success -and $m.Index -ge 4) { $p = $p.Substring(0, $m.Index) }
    Cut $p $n
}
function ItemHtml($i, [int]$n = 42) {
    $num = if ($i.Id) { '<span class="num">#' + (Enc (Cut (($i.Id -replace '^#', '').Trim()) 8)) + '</span> ' } else { '' }
    $text = Brief $i.Goal $n
    $num + $(if ($text) { "<span title=`"$(Enc (Plain $i.Goal))`">$(Enc $text)</span>" } else { '未命名的一项' })
}
function ListHtml($list) { $x = @($list | Where-Object { $_ }); '<ul class="items">' + (($x | ForEach-Object { "<li>$(ItemHtml $_)</li>" }) -join '') + '</ul>' }
function Answer($i) { if ($i.Id) { "/next #$(($i.Id -replace '^#', '').Trim()) 你的答复" } else { '/next 你的答复' } }
function IsStalled($p) { [bool](@($p.Problems) -match '^可能停滞') }
function Asks($p) { @(@($p.Waiting) | Where-Object { $_.Hint -ne '像搁置' }) + @(@($p.Waiting) | Where-Object { $_.Hint -eq '像搁置' }) }
function Recent($p) { $null -ne $p.IdleMinutes -and $p.IdleMinutes -lt $StaleMinutes }
function Label($i) { if ($i.Id) { '#' + (($i.Id -replace '^#', '').Trim()) } else { "「$(Cut $i.Goal 20)」" } }
function Num([double]$v) { $v.ToString('0.###', [Globalization.CultureInfo]::InvariantCulture) }
function Thumb([string]$url, [string]$alt) { "<a href=`"$(Enc $url)`" target=`"_blank`" title=`"点开看大图`"><img class=`"thumb`" loading=`"lazy`" src=`"$(Enc $url)`" alt=`"$(Enc $alt)`"></a>" }
# 方向要停、还没人在处理：待用户或在做的项里没有"方向复盘：<这个方向>"。
function StoppedOpen($p) {
    $open = @(@($p.Waiting) + @($p.Doing) | ForEach-Object { "$($_.Goal)" })
    @(@($p.Direction.Stopped) | Where-Object { $_ } | Where-Object { $re = '方向复盘[：:]\s*' + [regex]::Escape($_.Name) + '(?=$|[\s，,。；;（(])'; -not @($open | Where-Object { $_ -match $re }).Count })
}
# 按周差距小图：一条线，虚线是基准（差距 0），低于虚线就是比过了；每个点悬停看数，最后一点标数。
function Spark($trend) {
    $t = @(@($trend) | Where-Object { $_ } | Select-Object -Last 12)
    if (-not $t.Count) { return '' }
    $gaps = @($t | ForEach-Object { [double]$_.Gap })
    $stat = $gaps | Measure-Object -Minimum -Maximum
    $lo = [math]::Min(0, $stat.Minimum); $hi = [math]::Max(0, $stat.Maximum)
    if ($hi -eq $lo) { $hi = $lo + 1 }
    $w = 270; $h = 64; $mx = 10; $my = 10; $right = 72
    $xs = @(for ($i = 0; $i -lt $t.Count; $i++) { if ($t.Count -gt 1) { $mx + $i * ($w - $mx - $right) / ($t.Count - 1) } else { $mx } })
    $ys = @(foreach ($g in $gaps) { $h - $my - ($g - $lo) / ($hi - $lo) * ($h - 2 * $my) })
    $zero = $h - $my - (0 - $lo) / ($hi - $lo) * ($h - 2 * $my)
    $line = (0..($t.Count - 1) | ForEach-Object { "$(Num $xs[$_]),$(Num $ys[$_])" }) -join ' '
    $dots = (0..($t.Count - 1) | ForEach-Object {
        "<g><title>$(Enc $t[$_].Week)（$(Enc $t[$_].Date)）：$(Num $gaps[$_])</title><circle cx=`"$(Num $xs[$_])`" cy=`"$(Num $ys[$_])`" r=`"10`" fill=`"transparent`"/><circle cx=`"$(Num $xs[$_])`" cy=`"$(Num $ys[$_])`" r=`"4`" fill=`"var(--idle)`" stroke=`"var(--card)`" stroke-width=`"2`"/></g>" }) -join ''
    $lastX = $xs[-1] + 8; $lastY = $ys[-1] + 4
    "<svg class=`"spark`" width=`"$w`" height=`"$h`" viewBox=`"0 0 $w $h`" role=`"img`" aria-label=`"按周差距：$(Enc (($gaps | ForEach-Object { Num $_ }) -join ' → '))`">" +
    "<line x1=`"0`" x2=`"$($w - $right)`" y1=`"$(Num $zero)`" y2=`"$(Num $zero)`" stroke=`"var(--muted)`" stroke-width=`"1`" stroke-dasharray=`"3 3`"/>" +
    "<text x=`"$($w - 26)`" y=`"$(Num ($zero + 4))`" font-size=`"11`" fill=`"var(--muted)`">基准</text>" +
    $(if ($t.Count -gt 1) { "<polyline points=`"$line`" fill=`"none`" stroke=`"var(--idle)`" stroke-width=`"2`" stroke-linejoin=`"round`" stroke-linecap=`"round`"/>" }) +
    "$dots<text x=`"$(Num $lastX)`" y=`"$(Num $lastY)`" font-size=`"11`" fill=`"var(--fg)`">$(Num $gaps[-1])</text></svg>"
}
# 决定卡正文：标题、文字、图，最多 60 行；打开就能看，不用再开文件。
function CardBody($c) {
    $rows = (@(@($c.Lines) | Where-Object { $_ } | Select-Object -First 60) | ForEach-Object {
        if ($_.Type -eq 'image') { Thumb $_.Url $_.Alt }
        elseif ($_.Type -eq 'h') { "<div class=`"ch`">$(Enc $_.Text)</div>" }
        elseif ($_.Text -match '^(日期|队列|方向)\s*[：:]') { "<div class=`"meta`">$(Enc $_.Text)</div>" }
        else { "<div>$(Enc ($_.Text -replace '^[-*]\s+', '• '))</div>" }
    }) -join ''
    "<details class=`"dc`" open><summary>决定卡：$(Enc $c.Title)</summary>$rows<div class=`"how`">$(Enc $c.File)</div></details>"
}
# 状态标签：可能停了 > 等你 > 在做 > 刚有动静 > 空着 > 没活；维护中的项目单列
function State($p) {
    if ($p.Status -eq '维护') { return @('维护中', 'muted') }
    if (IsStalled $p) { return @('可能停了', 'bad') }
    if ((Asks $p).Count) { return @('等你', 'warn') }
    if (@(StoppedOpen $p).Count) { return @('方向要停', 'bad') }
    if (@($p.Doing).Count) { return @('在做', 'ok') }
    if ($p.Available -and (Recent $p)) { return @('刚有动静', 'ok') }
    if ($p.Available) { return @('空着，可开工', 'idle') }
    @('没有能做的项', 'muted')
}

$active = @($s.Projects)
$waiting = @(foreach ($p in $active) { foreach ($w in Asks $p) { [pscustomobject]@{ Project = $p.Name; Item = $w } } })
$waiting = @(@($waiting | Where-Object { $_.Item.Hint -ne '像搁置' }) + @($waiting | Where-Object { $_.Item.Hint -eq '像搁置' }))
$stalled = @($active | Where-Object { IsStalled $_ })
$free = @($active | Where-Object { $_.Status -eq '推进中' -and $_.Available -and -not @($_.Doing).Count -and -not (IsStalled $_) -and -not (Recent $_) })
$cards = @(foreach ($p in $active) { foreach ($c in @($p.Direction.Cards) | Where-Object { $_ }) {
    $leaf = Split-Path $c.File -Leaf
    $owner = @(@($p.Waiting) | Where-Object { "$($_.Detail)".Contains($leaf) })[0]
    [pscustomobject]@{ Project = $p.Name; Card = $c; Owner = $owner }
} })
$looseCards = @($cards | Where-Object { -not $_.Owner })
$stops = @(foreach ($p in $active) { foreach ($d in StoppedOpen $p) { [pscustomobject]@{ Project = $p.Name; Dir = $d } } })
$n = $waiting.Count + $stalled.Count + $looseCards.Count + $stops.Count
$summary = @(if ($n) { "要你管 $n 件事" } else { '暂时没有要你管的事' }) +
    @($active | Where-Object Status -eq '推进中' | ForEach-Object { "$(Nick $_.Name)：$((State $_)[0])" })

$b = [Text.StringBuilder]::new()
$style = @'
:root{--bg:#f5f5f1;--card:#fff;--fg:#1d1d1b;--muted:#6b6b65;--line:#e5e5df;--warn:#9a5500;--warnbg:#fdf1dc;--bad:#b42318;--badbg:#fde7e4;--ok:#17703a;--okbg:#e2f3e7;--idle:#3d5a99;--idlebg:#e6ecf8;--chip:#efefea;--bar:#2f7d4f;--shadow:0 1px 2px rgba(0,0,0,.05)}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1f1f1d;--fg:#ececea;--muted:#a3a39c;--line:#33332f;--warn:#f5b24a;--warnbg:#3a2c12;--bad:#f87171;--badbg:#3b1714;--ok:#6ad08c;--okbg:#15301f;--idle:#93b0ee;--idlebg:#1c2740;--chip:#2a2a27;--bar:#4fae75;--shadow:none}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:880px;margin:0 auto;padding:28px 16px 64px;overflow-wrap:anywhere}a{color:var(--idle)}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}h1{font-size:15px;font-weight:600;color:var(--muted);margin:0}.top .muted{font-size:13px}
.lead{font-size:26px;font-weight:700;line-height:1.35;margin:6px 0 16px}.lead.calm{color:var(--ok)}
h2{font-size:17px;margin:34px 0 10px}.muted{color:var(--muted)}.ok{color:var(--ok)}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;box-shadow:var(--shadow)}
.tile b{display:block;font-size:26px;line-height:1.2}.tile span{font-size:13px;color:var(--muted)}.tile.zero b{color:var(--muted);font-weight:500}.tile.warn b{color:var(--warn)}.tile.bad b{color:var(--bad)}.tile.ok b{color:var(--ok)}.tile.idle b{color:var(--idle)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:10px 0;box-shadow:var(--shadow)}
.tag{font-size:12px;font-weight:600;border-radius:999px;padding:1px 9px;white-space:nowrap}
.tag.bad{color:var(--bad);background:var(--badbg)}.tag.warn{color:var(--warn);background:var(--warnbg)}.tag.ok{color:var(--ok);background:var(--okbg)}.tag.idle{color:var(--idle);background:var(--idlebg)}.tag.muted{color:var(--muted);background:var(--chip)}
.bar{display:inline-block;width:100px;height:7px;background:var(--chip);border-radius:4px;vertical-align:middle;margin-right:8px;overflow:hidden}.bar>span{display:block;height:100%;background:var(--bar);border-radius:4px}.prog{font-size:13px;color:var(--muted);white-space:nowrap}
.list{margin-top:14px;padding:4px 0}.row{display:grid;grid-template-columns:minmax(90px,150px) 104px 190px 1fr;gap:12px;align-items:center;padding:9px 18px;color:inherit;text-decoration:none;border-top:1px solid var(--line)}.row:first-child{border-top:0}.row:hover{background:var(--chip)}.row b{font-weight:600}.row .what{font-size:13px;color:var(--muted);min-width:0}.row .tag{justify-self:start}
.ask-group h3{font-size:16px;margin:0 0 8px}.asks{list-style:none;margin:0;padding:0}.asks>li{padding:10px 0;border-top:1px solid var(--line)}.asks>li:first-child{border-top:0;padding-top:0}.asks>li:last-child{padding-bottom:0}
.q{font-weight:600}.why{font-size:14px;margin-top:2px}.rec{font-size:14px;margin-top:4px;color:var(--ok);font-weight:600}.how{color:var(--muted);font-size:13px;margin-top:6px}
.num{color:var(--muted);font-size:13px;font-weight:400}
code{background:var(--chip);border-radius:5px;padding:2px 7px;font-size:13px;user-select:all;white-space:normal}
.free{font-size:14px;color:var(--muted);margin:10px 2px}
.goals{display:grid;grid-template-columns:minmax(90px,150px) 1fr;gap:12px 16px}.goals .p{font-weight:600}.goals>*{min-width:0;overflow-wrap:anywhere}.goals .sub{font-weight:400;font-size:13px;color:var(--muted)}
.proj-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 10px}.proj-h h3{font-size:17px;margin:0}.proj-h .right{margin-left:auto;font-size:13px;color:var(--muted);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.k{color:var(--muted);font-size:13px;font-weight:600}
.now{background:var(--bg);border-radius:8px;padding:9px 12px;margin-bottom:12px}.now ul{margin-top:2px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px 22px;margin-top:12px}
.items{list-style:none;margin:3px 0 0;padding:0;font-size:14px}.items li{padding:2px 0}
.star{margin-bottom:10px;font-size:14px}
.bench{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px 18px;border-top:1px solid var(--line);margin-top:12px;padding-top:12px}.bench>*{min-width:0}.gap{font-size:16px;font-weight:600}.thumb{display:block;max-width:100%;max-height:200px;margin:4px 0;border:1px solid var(--line);border-radius:8px}.spark{display:block;max-width:100%;margin-top:8px}
.alert{color:var(--bad);font-weight:600;font-size:14px;margin-top:10px}.missing{font-size:13px;color:var(--muted);margin-top:12px}
details{margin-top:12px}summary{cursor:pointer;color:var(--muted);font-size:13px}details div{font-size:13px;color:var(--muted);margin:3px 0}
.dc{margin:10px 0 2px;padding:10px 14px;border-left:3px solid var(--warn);background:var(--bg);border-radius:0 8px 8px 0}.dc summary{font-size:14px;color:var(--fg);font-weight:600}.dc div{color:var(--fg);font-size:14px}.dc .ch{font-weight:600;margin-top:10px}.dc .meta,.dc .how{color:var(--muted);font-size:13px}
.maint>summary{font-size:15px;font-weight:600;color:var(--fg);margin:6px 0}
@media (max-width:640px){.lead{font-size:22px}.tiles{grid-template-columns:repeat(2,1fr)}.row{grid-template-columns:1fr auto;gap:2px 10px}.row .prog,.row .what{grid-column:1 / -1}.bench{grid-template-columns:minmax(0,1fr)}.goals{grid-template-columns:minmax(0,1fr)}}
'@
$tiles = @(
    @(($waiting.Count + $looseCards.Count), '件等你定', 'warn'),
    @(($stalled.Count + $stops.Count), '处可能有问题', 'bad'),
    @(@($active | Where-Object Status -eq '推进中' | ForEach-Object { @($_.Doing) }).Count, '项正在做', 'ok'),
    @($free.Count, '个项目可以开工', 'idle')
)
$null = $b.Append("<!doctype html><html lang=`"zh-CN`"><head><meta charset=`"utf-8`"><meta name=`"viewport`" content=`"width=device-width,initial-scale=1`"><title>项目状态</title><style>$style</style></head><body><main>")
$null = $b.Append("<div class=`"top`"><h1>项目状态</h1><span class=`"muted`">$(Enc $s.Generated) 更新</span></div>")
$null = $b.Append("<p class=`"lead$(if (-not $n) { ' calm' })`">$(Enc $summary[0])</p>")
$null = $b.Append('<div class="tiles">' + (($tiles | ForEach-Object { "<div class=`"tile $(if ($_[0]) { $_[2] } else { 'zero' })`"><b>$($_[0])</b><span>$($_[1])</span></div>" }) -join '') + '</div>')

# 全部项目一览：一个项目一行，点了跳到它的卡片
$anchor = @{}; $idx = 0; foreach ($p in $active) { $anchor[[string]$p.Name] = "p$idx"; $idx++ }
function Progress($p, [switch]$Long) {
    if (-not $p.Queue) { return '<span class="prog">还没有队列</span>' }
    $q = $p.Queue; $total = 0; foreach ($v in $q.PSObject.Properties) { if ($v.Name -ne '搁置') { $total += [int]$v.Value } }
    $done = [int]$q.'完成'; $pct = if ($total) { [math]::Round(100 * $done / $total) } else { 0 }
    "<span class=`"prog`"><span class=`"bar`"><span style=`"width:$pct%`"></span></span>$(if ($Long) { "完成 $done / 共 $total 项" } else { "$done / $total" })</span>"
}
function NowLine($p) {
    $doing = @($p.Doing)
    if (IsStalled $p) { "$(Ago $p.IdleMinutes)没动静" }
    elseif ($doing) { Brief $doing[0].Goal 34 }
    elseif ((Asks $p).Count) { "$((Asks $p).Count) 件等你定" }
    elseif ($p.Available -and (Recent $p)) { "$(Ago $p.IdleMinutes)前有动静，$($p.Available) 项可做" }
    elseif ($p.Available) { "有 $($p.Available) 项可以开工" }
    elseif ($p.Queue) { '暂时没有能做的项' } else { '还没有队列' }
}
$null = $b.Append('<div class="card list" style="padding:4px 0">')
foreach ($p in $active) {
    $st = State $p
    $null = $b.Append("<a class=`"row`" href=`"#$($anchor[[string]$p.Name])`"><b>$(Enc (Nick $p.Name))</b><span class=`"tag $($st[1])`">$(Enc $st[0])</span>$(Progress $p)<span class=`"what`">$(Enc (NowLine $p))</span></a>")
}
$null = $b.Append('</div>')

# 要你做：按项目分组。一项一个问题，推荐单独一行，命令可以点选复制。
$groups = [ordered]@{}
function Add-Ask([string]$project, [string]$html) { if (-not $groups.Contains($project)) { $groups[$project] = [Collections.Generic.List[string]]::new() }; $groups[$project].Add($html) }
foreach ($w in $waiting) {
    $i = $w.Item
    $d = (Plain $i.Detail) -replace '决定卡\s+\S+\.md\s*[：:]?\s*', ''
    $rec = [regex]::Match($d, '推荐[^。；;]*')
    $why = (($(if ($rec.Success) { $d.Remove($rec.Index, $rec.Length) } else { $d })) -replace '[；;，,]\s*(?=[。；;，,])', '').Trim(' ', '；', ';', '。', '，', ',', '：', ':')
    $attached = (@($cards | Where-Object { $_.Project -eq $w.Project -and $_.Owner -and $_.Owner.Id -eq $i.Id -and $_.Owner.Goal -eq $i.Goal }) | ForEach-Object { CardBody $_.Card }) -join ''
    $how = if ($i.Hint -eq '像搁置') { "像是已经说过先不做：是的话发 <code>$(Enc "/next $(Label $i) 改成搁置")</code>；还要你定的，发 <code>$(Enc (Answer $i))</code>" } else { "发 <code>$(Enc (Answer $i))</code>" }
    Add-Ask $w.Project ("<li><div class=`"q`">$(ItemHtml $i 60)$(if ($i.Hint -eq '像搁置') { ' <span class="tag muted">像已搁置</span>' })</div>" +
        $(if ($why) { "<div class=`"why`">$(Enc (Cut $why 200))</div>" }) + $(if ($rec.Success) { "<div class=`"rec`">$(Enc (Cut $rec.Value 140))</div>" }) + "<div class=`"how`">$how</div>$attached</li>")
}
foreach ($c in $looseCards) { Add-Ask $c.Project "<li><div class=`"q`">有一张决定卡等你定</div>$(CardBody $c.Card)<div class=`"how`">发 <code>/next 决定卡 $(Enc (Split-Path $c.Card.File -Leaf)) 你的答复</code></div></li>" }
foreach ($stop in $stops) { Add-Ask $stop.Project "<li><div class=`"q`">方向 $(Enc $stop.Dir.Name) 要停：$(Enc (Cut $stop.Dir.Reason 120))</div><div class=`"how`">发 <code>/next</code>：先复盘，再报决定卡给你定</div></li>" }
foreach ($p in $stalled) {
    $d = @($p.Doing)[0]
    Add-Ask $p.Name "<li><div class=`"q`">可能停了：$(if ($d) { ItemHtml $d 40 } else { '在做的项' })，已经 $(Ago $p.IdleMinutes)没动静</div><div class=`"how`">发 <code>/next$(if ($d -and $d.Id) { ' #' + (Enc (($d.Id -replace '^#', '').Trim())) })</code> 接着做</div></li>"
}
$null = $b.Append('<h2>要你做</h2>')
if ($groups.Count) {
    # 和上面的一览同一顺序
    $known = @($active | ForEach-Object { [string]$_.Name } | Where-Object { $groups.Contains($_) })
    foreach ($key in @($known) + @($groups.Keys | Where-Object { $known -notcontains $_ })) {
        $null = $b.Append("<div class=`"card ask-group`"><h3>$(Enc (Nick $key))</h3><ol class=`"asks`">$($groups[$key] -join '')</ol><div class=`"how`">到这个项目新建会话，发上面的命令；同意推荐就回 <code>按你的</code></div></div>")
    }
} else { $null = $b.Append('<div class="card"><span class="muted">暂时没有要你处理的事</span></div>') }
if ($free) { $null = $b.Append("<div class=`"free`">有空可以开工：$(($free | ForEach-Object { Enc "$(Nick $_.Name)（$($_.Available) 项）" }) -join '、')。到这个项目新建会话，发 <code>/next</code></div>") }

# 本周目标
$null = $b.Append('<h2>本周目标</h2><div class="card">')
$withGoals = @($active | Where-Object { @($_.Goals).Count })
if ($withGoals) {
    $null = $b.Append('<div class="goals">')
    foreach ($p in $withGoals) {
        $g = @($p.Goals)
        $list = ($g | ForEach-Object { "<span class=`"$(if ($_.Done) { 'ok' })`">$(if ($_.Done) { '✓' } else { '○' }) $(Enc (Plain $_.Text))</span>" }) -join '<br>'
        $null = $b.Append("<div class=`"p`">$(Enc (Nick $p.Name))<div class=`"sub`">完成 $(@($g | Where-Object Done).Count)/$($g.Count)</div></div><div>$list</div>")
    }
    $null = $b.Append('</div>')
} else { $null = $b.Append('<span class="muted">还没定，周会（<code>/week</code>）时定</span>') }
$null = $b.Append('</div>')

# 各项目：推进中的展开，维护中的收起来
function ProjectCard($p) {
    $st = State $p
    $doing = @($p.Doing)
    $now = if (IsStalled $p) { "$(ListHtml $doing)<div class=`"muted`">$(Ago $p.IdleMinutes)没动静</div>" }
           elseif ($doing) { ListHtml $doing }
           elseif ((Asks $p).Count) { "等你定，见上面" }
           elseif ($p.Available -and (Recent $p)) { "刚有动静（$(Ago $p.IdleMinutes)前），有 $($p.Available) 项可做" }
           elseif ($p.Available) { "空着，有 $($p.Available) 项可以开工" }
           elseif ($p.Queue) { '暂时没有能做的项' } else { '还没有队列' }
    $bench = $p.Direction
    $flow = if ($bench -and $bench.FlowUrl) { "<a href=`"$(Enc $bench.FlowUrl)`" target=`"_blank`">流程图</a>" }
    $x = [Text.StringBuilder]::new()
    $null = $x.Append("<div class=`"card`" id=`"$($anchor[[string]$p.Name])`"><div class=`"proj-h`"><h3>$(Enc (Nick $p.Name))</h3><span class=`"tag $($st[1])`">$(Enc $st[0])</span><span class=`"right`">$flow$(Progress $p -Long)$(if ($null -ne $p.Priority) { "<span>优先级 $($p.Priority)</span>" })</span></div>")
    $null = $x.Append("<div class=`"now`"><span class=`"k`">现在</span><div>$now</div></div>")
    $star = @(@($p.Digest.Lines) | Where-Object { $_ -match '^北极星' }) | Select-Object -First 1
    if ($star) { $null = $x.Append("<div class=`"star`"><span class=`"k`">北极星</span> $(Enc (Cut (Plain ($star -replace '^北极星[：:]\s*', '')) 110)) <span class=`"muted`">（$(Enc $p.Digest.Date) 复盘）</span></div>") }
    if ($p.Next -or $p.Recent) {
        $null = $x.Append('<div class="cols">')
        if ($p.Next) { $null = $x.Append("<div><span class=`"k`">接下来</span>$(ListHtml $p.Next)</div>") }
        if ($p.Recent) { $null = $x.Append("<div><span class=`"k`">最近完成</span>$(ListHtml $p.Recent)</div>") }
        $null = $x.Append('</div>')
    }
    if ($bench -and $bench.Benchmark -eq 'ok') {
        $gapNote = if ($bench.Note) { '<div class="why">' + (Enc (Cut (Plain $bench.Note) 60)) + '</div>' } else { '' }
        $gapText = if ($null -ne $bench.Gap) { '<div class="gap">差距 ' + (Num $bench.Gap) + '<span class="muted" style="font-weight:400;font-size:13px">（' + (Enc $bench.LastRun) + '）</span></div>' + $gapNote } else { '<div class="muted">还没量</div>' }
        $base = if ($bench.Baseline) { "<div class=`"how`">基准：$(Enc $bench.Baseline.Model)，$(Enc $bench.Baseline.Date)$(if ($bench.Baseline.Cost) { '，' + (Enc $bench.Baseline.Cost) })$(if ($bench.Baseline.Minutes) { '，' + (Enc $bench.Baseline.Minutes) + ' 分钟' })</div>" }
        $weeks = @(@($bench.Trend) | Where-Object { $_ } | Select-Object -Last 12)
        $trend = if ($weeks) { "$(Spark $weeks)<div class=`"how`">按周：$(($weeks | ForEach-Object { Num $_.Gap }) -join ' → ')。虚线是基准，越低越好，到虚线以下就比过了</div>" }
        $pic = if ($bench.ImageUrl) { Thumb $bench.ImageUrl "$(Nick $p.Name) 和基准的并排图" } else { '<div class="how">这次没有并排图</div>' }
        $null = $x.Append("<div class=`"bench`"><div><span class=`"k`">和基准比</span>$gapText$base$trend</div><div><span class=`"k`">并排图（点开看大图）</span>$pic</div></div>")
        foreach ($d in @($bench.Stopped) | Where-Object { $_ }) { $null = $x.Append("<div class=`"alert`">方向 $(Enc $d.Name) 要停：$(Enc (Cut $d.Reason 120))</div>") }
    }
    if ($bench -and $bench.Benchmark -ne 'notApplicable' -and $p.Status -eq '推进中') {
        $lack = @(if ($bench.Benchmark -eq 'none') { '还没登记基准' }; if (-not $bench.FlowUrl) { '还没有流程图' })
        if ($lack) { $null = $x.Append("<div class=`"missing`">$($lack -join '，')：下次在这个项目发 /next 会自动加</div>") }
    }
    $det = [Collections.Generic.List[string]]::new()
    $other = @($p.Other)
    if ($other) { $det.Add("队列里有 $($other.Count) 项的状态写法不标准，下次在这个项目发 /next 会顺手改好") }
    if ($p.Queue) { $q = $p.Queue; $det.Add("队列：在做 $($q.'在做') · 待做 $($q.'待做')（可领 $($p.Available)） · 待验证 $($q.'待验证') · 等你 $($q.'待用户') · 完成 $($q.'完成')$(if ($q.'搁置') { " · 搁置 $($q.'搁置')" })$(if ($q.'其他') { " · 写法不标准 $($q.'其他')" })") }
    if ($p.LastActivity) { $det.Add("最后动静 $($p.LastActivity)（$(Ago $p.IdleMinutes)前）；主干新提交 $($p.NewCount)（$($p.NewSince)）") }
    if ($null -ne $p.Worktrees -and ($p.WorktreesMerged + $p.WorktreesDetached + $p.BranchesMerged)) { $det.Add("可以清理：已合并的分支 $($p.BranchesMerged) 个，临时工作目录 $($p.Worktrees) 个") }
    if ($p.Trust) { $det.Add("信任等级 $($p.Trust)") }
    foreach ($y in @($p.Problems) | Where-Object { $_ -notmatch '^(可能停滞|队列里状态认不出)' }) { $det.Add("提示：$(Cut $y 120)") }
    if ($det.Count) { $null = $x.Append('<details><summary>细节</summary>' + (($det | ForEach-Object { "<div>$(Enc $_)</div>" }) -join '') + '</details>') }
    $null = $x.Append('</div>')
    $x.ToString()
}
$null = $b.Append('<h2>各项目</h2>')
$running = @($active | Where-Object Status -ne '维护')
$kept = @($active | Where-Object Status -eq '维护')
foreach ($p in $running) { $null = $b.Append((ProjectCard $p)) }
if ($kept) {
    $null = $b.Append("<details class=`"maint`"><summary>维护中的项目（$($kept.Count) 个）</summary>")
    foreach ($p in $kept) { $null = $b.Append((ProjectCard $p)) }
    $null = $b.Append('</details>')
}
if (@($s.Paused)) { $null = $b.Append("<div class=`"muted`" style=`"font-size:13px;margin-top:14px`">暂停：$(Enc ((@($s.Paused) | ForEach-Object { Nick $_ }) -join '、'))</div>") }
$null = $b.Append('</main></body></html>')

$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Out)
Set-Content -LiteralPath $Out -Value $b.ToString() -Encoding utf8NoBOM
$Out

if (-not $NoNotify) {
    # 每件要你管的事一个键（项目、编号、目标、问题前 60 字）；和上次推过的比，有新的才推手机。同一项换了问题算新的
    $events = @(
        foreach ($w in $waiting) { [pscustomobject]@{ Key = "$($w.Project)|$(Label $w.Item)|$(Cut $w.Item.Goal 40)|$(Cut $w.Item.Detail 60)"; Line = "$(Nick $w.Project)：$(Item $w.Item) 等你定$(if ($w.Item.Hint -eq '像搁置') { '（像已搁置）' })"; Ask = $true } }
        foreach ($c in $looseCards) { [pscustomobject]@{ Key = "$($c.Project)|决定卡|$($c.Card.File)"; Line = "$(Nick $c.Project)：决定卡 $(Cut $c.Card.Title 30) 等你定"; Ask = $true } }
        foreach ($stop in $stops) { [pscustomobject]@{ Key = "$($stop.Project)|方向要停|$($stop.Dir.Name)"; Line = "$(Nick $stop.Project)：方向 $($stop.Dir.Name) 要停，$(Cut $stop.Dir.Reason 40)"; Ask = $true } }
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
