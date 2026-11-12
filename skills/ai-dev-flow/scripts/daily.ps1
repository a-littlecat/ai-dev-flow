[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Out,
    [int]$StaleMinutes = 60,
    [int]$IdleHours = 12,
    [int]$GoalHours = 24,
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
# 页面：顶上一句话；一张全景图（横向 已完成 / 现在 / 可以开工 / 被挡住，纵向一个项目一条泳道，位置固定，依赖画成线）；下面三块：要你管（一件一张卡，问题、推荐、牵动哪些、要发的命令分开）、本周目标、各项目
# （状态标签、进度、北极星 / 方向 / 现在 / 等你定 / 接下来 / 被挡住 / 最近完成，空的不显示，流程图可以就地展开，其余收进"细节"；维护中的项目收起来）。页尾有名词说明。
# 墨色和纸色为主，朱红只给等你的事，跟随系统亮暗色。队列里写"同 #n 一起定"的项并进 #n，算一个决定。脚本只管悬停时点亮牵动的链、复制命令，没有脚本页面照样能读；系统设了减少动态效果就不动。队列原文的 Markdown 记号不上页面，长句只显示第一句，悬停看全文。
# 有待用户的项或可能停滞的项目时，通知级别为 user（按 notify.json 的配置会推到手机），否则为 info。
# 只在有上次没推过的事时才用 user：和上次推过的一样，就降成 info，只弹系统通知，不再推手机。通知发不出去时不记，下次照常推。
# 状态脚本标成"像搁置"的待用户项（Hint，见 status.ps1）照常算要你管，排在最后、标"像已搁置"，附改成搁置的命令；判断靠关键词，可能判错，所以不拿掉。
# 推进中的项目没有在做的项、但最近 StaleMinutes 分钟内有动静的，标"刚有动静"，不算空着：会话可能正在两项之间。
# 基准和决定卡（status.ps1 的 Direction，modules/direction.md）：每张项目卡多"和基准比"（差距、基准和按周小图）、"并排图"（缩略图，点开看大图）、"流程图"（docs/flow.html 的链接）三样；
# 待定的决定卡显示在"要你管"：挂在提到它的待用户项下面，没有这样的项就单独一条。方向要停、又没有在处理的（待用户或在做的项目标写着"方向复盘：<这个方向>"）也进"要你管"。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
if (-not $Out) { $Out = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/status.html' }
$Out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)
if (-not $State) { $State = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/daily-state.json' }
$State = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($State)

$statusArgs = @('-Json', '-StaleMinutes', $StaleMinutes, '-IdleHours', $IdleHours, '-GoalHours', $GoalHours)
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
# 短标题：去掉全角括号里的补充说明，到第一句为止（第一句太短的不断），超长再截断；全文放在悬停提示里。冒号不断：常常是"需求：具体内容"，断了就认不出是哪一项。
function Brief([string]$t, [int]$n = 42) {
    $p = Plain $t
    $q = ($p -replace '（[^（）]*）', '').Trim()
    if ($q) { $p = $q }
    $m = [regex]::Match($p, '[。；;]')
    if ($m.Success -and $m.Index -ge 4) { $p = $p.Substring(0, $m.Index) }
    Cut $p $n
}
function ItemHtml($i, [int]$n = 42) {
    $num = if ($i.Id) { '<span class="num">#' + (Enc (Cut (($i.Id -replace '^#', '').Trim()) 8)) + '</span> ' } else { '' }
    $text = Brief $i.Goal $n
    $num + $(if ($text) { "<span title=`"$(Enc (Plain $i.Goal))`">$(Enc $text)</span>" } else { '未命名的一项' })
}
function ListHtml($list) { $x = @($list | Where-Object { $_ }); '<ul class="items">' + (($x | ForEach-Object { "<li>$(ItemHtml $_)</li>" }) -join '') + '</ul>' }
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
        "<g><title>$(Enc $t[$_].Week)（$(Enc $t[$_].Date)）：$(Num $gaps[$_])</title><circle cx=`"$(Num $xs[$_])`" cy=`"$(Num $ys[$_])`" r=`"10`" fill=`"transparent`"/><circle cx=`"$(Num $xs[$_])`" cy=`"$(Num $ys[$_])`" r=`"3.5`" fill=`"var(--ink)`" stroke=`"var(--bg)`" stroke-width=`"2`"/></g>" }) -join ''
    $lastX = $xs[-1] + 8; $lastY = $ys[-1] + 4
    "<svg class=`"spark`" width=`"$w`" height=`"$h`" viewBox=`"0 0 $w $h`" role=`"img`" aria-label=`"按周差距：$(Enc (($gaps | ForEach-Object { Num $_ }) -join ' → '))`">" +
    "<line x1=`"0`" x2=`"$($w - $right)`" y1=`"$(Num $zero)`" y2=`"$(Num $zero)`" stroke=`"var(--mut)`" stroke-width=`"1`" stroke-dasharray=`"2 3`"/>" +
    "<text x=`"$($w - 26)`" y=`"$(Num ($zero + 4))`" font-size=`"11`" fill=`"var(--mut)`">基准</text>" +
    $(if ($t.Count -gt 1) { "<polyline points=`"$line`" fill=`"none`" stroke=`"var(--ink)`" stroke-width=`"1.5`" stroke-linejoin=`"round`" stroke-linecap=`"round`"/>" }) +
    "$dots<text x=`"$(Num $lastX)`" y=`"$(Num $lastY)`" font-size=`"11`" fill=`"var(--ink)`">$(Num $gaps[-1])</text></svg>"
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
# 状态标签：可能停了 > 等你 > 方向要停 > 方向没人看（没登记基准，status.ps1 的 Unwatched） > 在做 > 刚有动静 > 空着 > 没活；维护中的项目单列
function State($p) {
    if ($p.Status -eq '维护') { return @('维护中', 'muted') }
    if (IsStalled $p) { return @('可能停了', 'bad') }
    if ((Asks $p).Count) { return @('等你', 'warn') }
    if (@(StoppedOpen $p).Count) { return @('方向要停', 'bad') }
    if ($p.Unwatched) { return @('方向没人看', 'bad') }
    if (@($p.Doing).Count) { return @('在做', 'ok') }
    if ($p.Available -and (Recent $p)) { return @('刚有动静', 'ok') }
    if ($p.Available) { return @('空着，可开工', 'idle') }
    @('没有能做的项', 'muted')
}

$active = @($s.Projects)
$waiting = @(foreach ($p in $active) { foreach ($w in Asks $p) { [pscustomobject]@{ Project = $p.Name; Item = $w } } })
$waiting = @(@($waiting | Where-Object { $_.Item.Hint -ne '像搁置' }) + @($waiting | Where-Object { $_.Item.Hint -eq '像搁置' }))
$stalled = @($active | Where-Object { IsStalled $_ })
# 有活没人做（status.ps1 的提示，-IdleHours 小时没动静）：单独一行写明空了多久，不管有没有等你定的项；其余空着的照旧并成一行。
$unattended = @($active | Where-Object { @($_.Problems) -match '^有活没人做' })
$free = @($active | Where-Object { $_.Status -eq '推进中' -and $_.Available -and -not @($_.Doing).Count -and -not (IsStalled $_) -and -not (Recent $_) -and $unattended -notcontains $_ })
$cards = @(foreach ($p in $active) { foreach ($c in @($p.Direction.Cards) | Where-Object { $_ }) {
    $leaf = Split-Path $c.File -Leaf
    $owner = @(@($p.Waiting) | Where-Object { "$($_.Detail)".Contains($leaf) })[0]
    [pscustomobject]@{ Project = $p.Name; Card = $c; Owner = $owner }
} })
$looseCards = @($cards | Where-Object { -not $_.Owner })
$stops = @(foreach ($p in $active) { foreach ($d in StoppedOpen $p) { [pscustomobject]@{ Project = $p.Name; Dir = $d } } })
$n = $waiting.Count + $stalled.Count + $looseCards.Count + $stops.Count

$b = [Text.StringBuilder]::new()
$style = @'
:root{color-scheme:light dark;--bg:#f1f0ec;--ink:#121210;--mut:#66665f;--faint:#7c7c74;--rule:rgba(18,18,16,.14);--rule2:rgba(18,18,16,.34);--band:rgba(18,18,16,.045);--sig:#d9360f;--on-sig:#fff;--sans:"Segoe UI Variable Text","Segoe UI","PingFang SC","Microsoft YaHei UI",system-ui,sans-serif;--display:"Segoe UI Variable Display","Segoe UI","Helvetica Neue",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#101010;--ink:#eeede8;--mut:#a09f98;--faint:#85847d;--rule:rgba(238,237,232,.14);--rule2:rgba(238,237,232,.36);--band:rgba(238,237,232,.05);--sig:#ff5a2b;--on-sig:#150501}}
*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--bg)}body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.65 var(--sans);-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums;overflow-x:hidden}
main{max-width:1264px;margin:0 auto;padding:44px 32px 96px;overflow-wrap:anywhere}a{color:inherit}
.stamp{font-size:12.5px;color:var(--mut);letter-spacing:.02em}
h1{display:flex;align-items:baseline;gap:22px;flex-wrap:wrap;margin:22px 0 10px;font-size:52px;line-height:1.1;font-weight:300;letter-spacing:-.025em;animation:rise .8s cubic-bezier(.2,.8,.2,1) both}
h1 em{font:200 176px/.8 var(--display);letter-spacing:-.05em;color:var(--sig)}
.sub{margin:0 0 44px;font-size:17px;color:var(--mut);min-height:1px}.sub b{color:var(--ink);font-weight:600}
.mapwrap{overflow-x:auto;border-top:1.5px solid var(--ink);scrollbar-width:thin}
#map{display:block;min-width:1040px;width:100%;height:auto}#map text{font-family:var(--sans)}
.hl{font-size:13px;fill:var(--mut)}.hl.on{fill:var(--ink);font-weight:600}
#map text.hn{font:200 46px var(--display);letter-spacing:-.03em;fill:var(--ink)}.hc{font-size:12px;fill:var(--mut)}
.spot{fill:var(--band);animation:fade 1s ease both}
.lane{stroke:var(--rule)}.ln{font-size:15px;font-weight:600;fill:var(--ink)}.lm{font-size:12px;fill:var(--mut)}.lt0{fill:var(--rule)}.lt1{fill:var(--ink);transform-box:fill-box;transform-origin:left;animation:grow 1s cubic-bezier(.2,.8,.2,1) both}
a:hover .ln{text-decoration:underline}
.tick{fill:var(--ink);transform-box:fill-box;transform-origin:bottom;animation:tick .4s cubic-bezier(.2,.8,.2,1) both;animation-delay:var(--d);transition:opacity .15s}.tick:hover{fill:var(--mut)}
.chip{cursor:default;transition:opacity .18s}a.chip{cursor:pointer}.chip text{font-size:13px}
.chip rect{fill:none;stroke-width:1;transition:fill .15s,stroke .15s}
.chip.ask rect{fill:var(--sig);stroke:var(--sig)}.chip.ask text{fill:var(--on-sig)}.chip.ask .chip-dot{fill:var(--on-sig);stroke:none}.chip.ask .chip-b{font-size:14px;font-weight:700}
.chip.doing rect{fill:var(--ink);stroke:var(--ink)}.chip.doing text{fill:var(--bg)}.chip.doing .chip-dot{fill:var(--bg);stroke:none}.chip.doing.live .chip-dot{animation:blink 1.8s ease-in-out infinite}.chip.doing.stale rect{stroke:var(--sig);stroke-width:2}
.chip.verify rect{stroke:var(--ink);stroke-width:1.5}.chip.verify text{fill:var(--ink)}.chip.verify .chip-dot{fill:var(--ink);stroke:none}
.chip.nx rect{stroke:var(--rule2)}.chip.nx text{fill:var(--ink);font-size:12.5px}.chip.nx:hover rect{stroke:var(--ink)}
.chip.lt rect{stroke:var(--rule2);stroke-dasharray:2 3}.chip.lt text{fill:var(--mut);font-size:12.5px}.morec{font-size:12px;fill:var(--faint)}
.eb{fill:none;stroke:var(--rule2);stroke-width:1;stroke-dasharray:1;animation:draw 1.2s .35s cubic-bezier(.4,0,.2,1) both}.e-ask .eb{stroke:var(--sig)}
.ef{fill:none;stroke-width:1.6;stroke-linecap:round;stroke-dasharray:1.5 9;opacity:0;stroke:var(--sig)}.e-live .ef{stroke:var(--ink)}.edge.hot .ef{opacity:1;animation:flow .9s linear infinite}.edge{transition:opacity .18s}
.bracket path{fill:none;stroke:var(--sig);stroke-width:1}.bracket text{fill:var(--sig);font-size:12px;writing-mode:vertical-rl}.bracket{transition:opacity .18s}
#map.focus .chip,#map.focus .tick,#map.focus .edge,#map.focus .bracket{opacity:.14}#map.focus .hot{opacity:1!important}
.mapnote{display:flex;justify-content:space-between;gap:8px 24px;flex-wrap:wrap;margin-top:12px;font-size:12.5px;color:var(--mut)}.legend{display:flex;gap:6px 16px;flex-wrap:wrap}.legend span{display:inline-flex;align-items:center;gap:7px}.legend i{display:block;width:14px;height:9px;border-radius:2px}
.legend .done{width:2.5px;height:12px;border-radius:0;background:var(--ink)}.legend .ask{background:var(--sig)}.legend .doing{background:var(--ink)}.legend .verify{border:1.5px solid var(--ink)}.legend .idle{border:1px solid var(--rule2)}.legend .wait{border:1px dashed var(--rule2)}
h2{font-size:13px;font-weight:600;margin:64px 0 0;padding-bottom:10px;display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;border-bottom:1.5px solid var(--ink)}h2 small{font-size:12.5px;font-weight:400;color:var(--mut)}
.cards{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,500px),1fr));column-gap:48px}
.card{min-width:0;padding:24px 0 30px;border-bottom:1px solid var(--rule);scroll-margin-top:20px;animation:rise .7s cubic-bezier(.2,.8,.2,1) both;animation-delay:calc(var(--i) * 80ms + 250ms);box-shadow:0 -2px 0 transparent;transition:box-shadow .18s}.card:hover,.card:target,.card.hot{box-shadow:0 -2px 0 var(--sig)}
.ct{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px}.ct>div{min-width:0}.meta{font-size:12.5px;color:var(--mut)}.num{color:var(--faint);font-size:.82em;font-weight:400}
.q{font-size:22px;line-height:1.38;font-weight:400;letter-spacing:-.012em;margin:5px 0 0}
.imp{text-align:right;line-height:1;white-space:nowrap}.imp b{display:block;font:200 52px/1 var(--display);letter-spacing:-.03em;color:var(--sig)}.imp span{font-size:11.5px;color:var(--mut)}.imp.z b{color:var(--faint)}
.why{margin:12px 0 0;font-size:13.5px;color:var(--mut)}.rec{margin:16px 0 0;font-size:15px;padding-left:14px;border-left:2px solid var(--ink)}.rec span{font-weight:600;margin-right:10px}
.after{display:grid;grid-template-columns:56px minmax(0,1fr);gap:10px;margin-top:14px;font-size:13px}.after>span{color:var(--mut)}.after ul{list-style:none;margin:0;padding:0}.after li{padding:1px 0}.after em{font-style:normal;color:var(--mut);display:block;font-size:12.5px}
.cmd{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:18px;padding:9px 14px;border:1px solid var(--rule2);border-radius:3px}.cmd code{font:13px "Cascadia Code",Consolas,monospace;user-select:all;min-width:0}.cp{display:none;background:none;border:0;padding:0;color:var(--mut);font:12.5px var(--sans);cursor:pointer;white-space:nowrap}.js .cp{display:inline}.cp:hover{color:var(--ink);text-decoration:underline}.cp:focus-visible{outline:2px solid var(--sig);outline-offset:2px}
.how{color:var(--mut);font-size:13px;margin-top:8px}.how code,.free code,.goals code{font:12.5px "Cascadia Code",Consolas,monospace;user-select:all}
.free{font-size:14px;color:var(--mut);margin:16px 0 0}
.goals{display:grid;grid-template-columns:minmax(90px,180px) 1fr;gap:14px 20px;padding:18px 0;border-bottom:1px solid var(--rule)}.goals .p{font-weight:600}.goals>*{min-width:0;overflow-wrap:anywhere}.goals .sub2{font-weight:400;font-size:12.5px;color:var(--mut)}.done-goal{color:var(--mut)}.none{padding:18px 0;color:var(--mut);border-bottom:1px solid var(--rule)}
.proj{padding:26px 0 30px;border-bottom:1px solid var(--rule);scroll-margin-top:20px}.proj:target{box-shadow:0 -2px 0 var(--ink)}
.proj-h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 16px}.proj-h h3{font-size:22px;font-weight:300;letter-spacing:-.012em;margin:0}.proj-h .right{margin-left:auto;font-size:13px;color:var(--mut);display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.tag{font-size:12px;white-space:nowrap;color:var(--mut)}.tag.warn,.tag.bad{color:var(--sig);font-weight:600}.tag.ok{color:var(--ink);font-weight:600}
.bar{display:inline-flex;gap:2px;width:120px;height:3px;background:var(--rule);vertical-align:middle;margin-right:8px;overflow:hidden}.seg{display:block;height:100%}.seg.done{background:var(--ink)}.seg.verify,.seg.doing{background:var(--mut)}.seg.ask{background:var(--sig)}.prog{white-space:nowrap}
.pgrid{display:grid;grid-template-columns:minmax(0,1fr);gap:24px 48px}.pgrid.two{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.facts{display:grid;grid-template-columns:64px minmax(0,1fr);gap:9px 14px;margin:0;font-size:14px}.facts dt{color:var(--mut);font-size:13px}.facts dd{margin:0;min-width:0}.facts dt.live::before{content:"";display:inline-block;width:6px;height:6px;margin-right:7px;vertical-align:2px;background:var(--ink);animation:blink 1.8s ease-in-out infinite}.facts dd.stale{color:var(--sig)}
.items{list-style:none;margin:0;padding:0}.items li{padding:1px 0}.wait{color:var(--mut);font-size:12px;white-space:nowrap}.more{color:var(--mut)}
.k{color:var(--mut);font-size:13px}.bench{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px 24px}.bench>*{min-width:0}.gap{font:200 34px/1.3 var(--display);letter-spacing:-.02em}.gap span{font:13px var(--sans);letter-spacing:0;color:var(--mut)}.thumb{display:block;max-width:100%;max-height:200px;margin:6px 0;border:1px solid var(--rule)}.spark{display:block;max-width:100%;margin-top:8px}
.alert{color:var(--sig);font-weight:600;font-size:14px;margin-top:12px}.missing{font-size:13px;color:var(--mut);margin-top:12px}
details{margin-top:12px}summary{cursor:pointer;color:var(--mut);font-size:13px}summary:hover{color:var(--ink)}summary:focus-visible{outline:2px solid var(--sig)}details div{font-size:13px;color:var(--mut);margin:3px 0}
.flowbox iframe{display:block;width:100%;height:440px;margin-top:8px;border:1px solid var(--rule);background:var(--bg)}
.dc{margin:14px 0 2px;padding:2px 0 2px 14px;border-left:1px solid var(--rule2)}.dc summary{font-size:14px;color:var(--ink);font-weight:600}.dc div{color:var(--ink);font-size:14px}.dc .ch{font-weight:600;margin-top:10px}.dc .meta,.dc .how{color:var(--mut);font-size:13px}
.maint{margin-top:22px}.maint>summary{font-size:15px;font-weight:600;color:var(--ink)}.paused{font-size:13px;color:var(--mut);margin-top:14px}
.gloss{margin-top:30px}.gloss dl{display:grid;grid-template-columns:70px minmax(0,1fr);gap:6px 12px;margin:8px 0 0;font-size:14px}.gloss dt{font-weight:600}.gloss dd{margin:0;color:var(--mut)}
@keyframes grow{from{transform:scaleX(0)}}@keyframes rise{from{opacity:0;transform:translateY(8px)}}@keyframes fade{from{opacity:0}}@keyframes tick{from{transform:scaleY(0)}}@keyframes blink{50%{opacity:.25}}@keyframes flow{to{stroke-dashoffset:-10.5}}@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}html{scroll-behavior:auto}}
@media (max-width:760px){main{padding:24px 16px 56px}h1{font-size:30px;gap:12px}h1 em{font-size:96px}.sub{font-size:15px;margin-bottom:28px}.q{font-size:19px}.imp b{font-size:40px}.pgrid.two,.bench,.goals{grid-template-columns:minmax(0,1fr)}}
'@
$pageScript = @'
(function () {
  var root = document.documentElement, map = document.getElementById('map');
  root.classList.add('js');
  function each(sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }
  var byA = {}, byB = {};
  each('.edge', function (e) { var a = e.getAttribute('data-a'), b = e.getAttribute('data-b'); (byA[a] = byA[a] || []).push(e); (byB[b] = byB[b] || []).push(e); });
  function light(keys) {
    var seen = {};
    function mark(k) { each('#map [data-k="' + k + '"]', function (n) { n.classList.add('hot'); }); each('.card[data-keys~="' + k + '"]', function (c) { c.classList.add('hot'); }); }
    function walk(k, table, attr) { (table[k] || []).forEach(function (e) { e.classList.add('hot'); var o = e.getAttribute(attr); if (!seen[attr + o]) { seen[attr + o] = 1; mark(o); walk(o, table, attr); } }); }
    keys.forEach(function (k) { mark(k); walk(k, byA, 'data-b'); walk(k, byB, 'data-a'); });
    map.classList.add('focus');
  }
  function clear() { map.classList.remove('focus'); each('.hot', function (n) { n.classList.remove('hot'); }); }
  function bind(el, keys) { el.addEventListener('mouseenter', function () { light(keys()); }); el.addEventListener('mouseleave', clear); el.addEventListener('focusin', function () { light(keys()); }); el.addEventListener('focusout', clear); }
  each('.card[data-keys]', function (c) { bind(c, function () { return c.getAttribute('data-keys').split(' '); }); });
  each('#map .chip[data-k]', function (c) { bind(c, function () { var k = c.getAttribute('data-k'), g = document.querySelector('.card[data-keys~="' + k + '"]'); return g ? g.getAttribute('data-keys').split(' ') : [k]; }); });
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.cp'); if (!b) return;
    var t = b.getAttribute('data-cmd');
    function ok() { b.textContent = '已复制'; setTimeout(function () { b.textContent = '复制'; }, 1400); }
    function fb() { var a = document.createElement('textarea'); a.value = t; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); ok(); } catch (x) {} a.remove(); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(ok, fb); else fb();
  });
})();
'@

# 全景图的数据：每个项目的全部项，加上依赖；写"同 #n 一起定"的待用户项并进 #n，算一个决定。
function IdOf($i) { ("$($i.Id)" -replace '^#', '').Trim() }
function TextW([string]$t, [double]$size) { $w = 0.0; foreach ($c in $t.ToCharArray()) { $w += $(if ([int]$c -gt 255) { $size } else { $size * 0.56 }) }; $w }
function Fit([string]$t, [double]$width, [double]$size = 13) {
    if ((TextW $t $size) -le $width) { return $t }
    while ($t.Length -gt 2 -and (TextW "$t…" $size) -gt $width) { $t = $t.Substring(0, $t.Length - 1) }
    "$($t.TrimEnd())…"
}
# 全景图上的短标题：全角冒号前够长（6 字以上）就只留冒号前；"方向实验：xxx"这种太短的不断。
function Tiny([string]$t) { $q = Brief $t 80; $c = $q.IndexOf('：'); if ($c -ge 6) { $q.Substring(0, $c) } else { $q } }
$models = @(for ($pIdx = 0; $pIdx -lt $active.Count; $pIdx++) {
    $its = @(@($active[$pIdx].Items) | Where-Object { $_ })
    $ms = @(for ($k = 0; $k -lt $its.Count; $k++) {
        $it = $its[$k]
        $dep = ("$($it.Deps)" -replace '\*', '').Trim()
        $ids = @(if ($dep -match '^[#\d\s,，、]+$') { [regex]::Matches($dep, '\d+') | ForEach-Object Value })
        [pscustomobject]@{ Key = "$pIdx-$k"; Id = (IdOf $it); It = $it; State = $it.State; Claimable = [bool]$it.Claimable; DepIds = $ids; DepText = $(if ($dep -notmatch '^(无|-|—|)$' -and -not $ids.Count) { $dep }) }
    })
    $byId = @{}; $rev = @{}
    foreach ($m in $ms) { if ($m.Id -and -not $byId.ContainsKey($m.Id)) { $byId[$m.Id] = $m } }
    foreach ($m in $ms) { foreach ($x in $m.DepIds) { if (-not $rev.ContainsKey($x)) { $rev[$x] = [Collections.Generic.List[object]]::new() }; $rev[$x].Add($m) } }
    [pscustomobject]@{ Index = $pIdx; P = $active[$pIdx]; Items = $ms; ById = $byId; Rev = $rev }
})
function Of($mo, [string]$state) { @($mo.Items | Where-Object State -eq $state) }
function GroupRoot([string]$id, $askById) {
    $seen = @{}
    while ($true) {
        if ($seen[$id]) { return $id }
        $seen[$id] = $true
        $g = [regex]::Match((Plain $askById[$id].It.Detail), '^同\s*#(\S+?)\s*一起')
        if (-not $g.Success -or -not $askById.ContainsKey($g.Groups[1].Value)) { return $id }
        $id = $g.Groups[1].Value
    }
}
$decisions = @(foreach ($mo in $models) {
    $askItems = Of $mo '待用户'
    $askById = @{}; foreach ($m in $askItems) { if ($m.Id -and -not $askById.ContainsKey($m.Id)) { $askById[$m.Id] = $m } }
    $rootOf = @{}; foreach ($m in $askItems) { if ($m.Id) { $rootOf[$m.Key] = GroupRoot $m.Id $askById } }
    foreach ($m in $askItems) {
        # 重复的编号只有第一项能当根、当子项，后面的各算各的。
        $first = $m.Id -and $askById[$m.Id].Key -eq $m.Key
        if ($first -and $rootOf[$m.Key] -ne $m.Id) { continue }
        $kids = @(if ($first) { $askItems | Where-Object { $_.Key -ne $m.Key -and $_.Id -and $askById[$_.Id].Key -eq $_.Key -and $rootOf[$_.Key] -eq $m.Id } })
        $group = @($m) + $kids
        $inGroup = @{}; foreach ($g in $group) { $inGroup[$g.Key] = $true }
        $down = [ordered]@{}
        $todoIds = [Collections.Generic.Queue[string]]::new()
        foreach ($g in $group) { if ($g.Id) { $todoIds.Enqueue($g.Id) } }
        $walked = @{}
        while ($todoIds.Count) {
            $cur = $todoIds.Dequeue()
            if ($walked[$cur]) { continue }
            $walked[$cur] = $true
            foreach ($o in @($mo.Rev[$cur])) {
                if (-not $o -or $inGroup[$o.Key] -or $o.State -in '完成', '搁置') { continue }
                $down[$o.Key] = $o
                if ($o.Id) { $todoIds.Enqueue($o.Id) }
            }
        }
        [pscustomobject]@{ Model = $mo; Item = $m; Kids = $kids; Down = @($down.Values); Shelved = ($m.It.Hint -eq '像搁置') }
    }
})
$decisions = @($decisions | Sort-Object -Stable { [int]$_.Shelved }, { - $_.Down.Count }, { - $_.Kids.Count })
$followers = @{}; foreach ($dc in $decisions) { foreach ($o in $dc.Down) { $followers[$o.Key] = $true } }
$askCount = @($models | ForEach-Object { Of $_ '待用户' }).Count
$pageCount = $decisions.Count + $looseCards.Count + $stalled.Count + $stops.Count
$allItems = @($models | ForEach-Object { $_.Items })
$totals = @{}; foreach ($st in '完成', '在做', '待验证', '待用户', '待放行', '搁置', '其他') { $totals[$st] = @($allItems | Where-Object State -eq $st).Count }
$openCount = @($allItems | Where-Object { $_.State -eq '待做' -and $_.Claimable }).Count
$blockedCount = @($allItems | Where-Object { $_.State -eq '待做' -and -not $_.Claimable }).Count

# 全景图：横向是 已完成 / 现在 / 可以开工 / 被挡住，纵向一个项目一条泳道。位置只由状态和项目决定。
$colDone = @(176, 392); $colNow = @(404, 716); $colNext = @(728, 968); $colLater = @(980, 1188)
$mapW = 1200; $laneTop = 104
$nodes = @{}; $ticks = [Text.StringBuilder]::new(); $chips = [Text.StringBuilder]::new(); $laneSvg = [Text.StringBuilder]::new(); $edgeSvg = [Text.StringBuilder]::new()
function ChipSvg([string]$key, [string]$cls, [double]$x0, [double]$x1, [double]$cy, [double]$tall, [string]$label, [string]$full, [string]$href, [string]$badge, [bool]$mark) {
    $hrefAttr = if ($href) { " href=`"$href`"" } else { '' }
    $tag = if ($href) { 'a' } else { 'g' }
    $textX = if ($mark) { $x0 + 25 } else { $x0 + 10 }
    $dot = if ($mark) { "<rect class=`"chip-dot`" x=`"$(Num ($x0 + 10))`" y=`"$(Num ($cy - 3))`" width=`"6`" height=`"6`"/>" } else { '' }
    $bd = if ($badge) { "<text class=`"chip-b`" x=`"$(Num ($x1 - 12))`" y=`"$(Num ($cy + 4.5))`" text-anchor=`"end`">$badge</text>" } else { '' }
    "<$tag$hrefAttr class=`"chip $cls`" data-k=`"$key`"><title>$(Enc (Cut (Plain $full) 200))</title><rect x=`"$(Num $x0)`" y=`"$(Num ($cy - $tall / 2))`" width=`"$(Num ($x1 - $x0))`" height=`"$(Num $tall)`" rx=`"2`"/>$dot<text x=`"$(Num $textX)`" y=`"$(Num ($cy + 4.5))`">$(Enc $label)</text>$bd</$tag>"
}
function ItemLabel($m) { $t = Tiny $m.It.Goal; if ($m.Id) { "#$(Cut $m.Id 8) $t" } elseif ($t) { $t } else { '未命名的一项' } }
$laneY = $laneTop
foreach ($mo in $models) {
    $p = $mo.P; $pIdx = $mo.Index
    $done = Of $mo '完成'
    $now = @(Of $mo '在做') + @(Of $mo '待验证') + @($decisions | Where-Object { $_.Model.Index -eq $pIdx } | ForEach-Object { $_.Item; $_.Kids })
    $opn = @($mo.Items | Where-Object { $_.State -eq '待做' -and $_.Claimable })
    $blocked = @($mo.Items | Where-Object { $_.State -eq '待做' -and -not $_.Claimable })
    $shownNext = @($opn | Select-Object -First 3); $shownLater = @($blocked | Select-Object -First 3)
    $perRow = 27; $rowGap = 26; $shownDone = @($done | Select-Object -First ($perRow * 3))
    $rows = [math]::Max(1, [math]::Ceiling($shownDone.Count / $perRow))
    $tall = [math]::Max([math]::Max($now.Count * 36, $rows * $rowGap), [math]::Max(($shownNext.Count + [int]($opn.Count -gt 3)), ($shownLater.Count + [int]($blocked.Count -gt 3))) * 32)
    $tall = [math]::Max($tall, 44) + 30
    for ($k = 0; $k -lt $shownDone.Count; $k++) {
        $m = $shownDone[$k]
        $cx = $colDone[0] + 6 + ($k % $perRow) * 8
        $cy = $laneY + $tall / 2 - ($rows - 1) * $rowGap / 2 + [math]::Floor($k / $perRow) * $rowGap
        $null = $ticks.Append("<rect class=`"tick`" data-k=`"$($m.Key)`" x=`"$(Num ($cx - 1.25))`" y=`"$(Num ($cy - 9))`" width=`"2.5`" height=`"18`" style=`"--d:$([math]::Min($k * 18, 700))ms`"><title>$(Enc (ItemLabel $m))</title></rect>")
    }
    if ($done.Count -gt $shownDone.Count) { $null = $chips.Append("<text class=`"morec`" x=`"$($colDone[0] + 2)`" y=`"$(Num ($laneY + $tall - 6))`">还有 $($done.Count - $shownDone.Count) 项</text>") }
    $top = $laneY + ($tall - $now.Count * 36) / 2 + 3
    for ($k = 0; $k -lt $now.Count; $k++) {
        $m = $now[$k]; $cy = $top + $k * 36 + 15; $x0 = $colNow[0] + 6; $x1 = $colNow[1] - 6
        $kind = switch ($m.State) { '待用户' { 'ask' } '在做' { 'doing' } default { 'verify' } }
        $badge = ''; $href = ''
        if ($kind -eq 'ask') {
            $owner = @($decisions | Where-Object { $_.Item.Key -eq $m.Key -or @($_.Kids | Where-Object Key -eq $m.Key).Count })[0]
            $href = "#d$($owner.Item.Key)"
            if ($owner.Item.Key -eq $m.Key -and $owner.Down.Count) { $badge = "+$($owner.Down.Count)" }
        }
        if ($kind -eq 'doing') {
            if (IsStalled $p) { $kind = 'doing stale'; $href = "#s$pIdx" }
            elseif (Recent $p) { $kind = 'doing live' }
        }
        $label = Fit (ItemLabel $m) ($x1 - $x0 - 30 - $(if ($badge) { 34 } else { 0 }))
        $null = $chips.Append((ChipSvg $m.Key $kind $x0 $x1 $cy 30 $label $m.It.Goal $href $badge $true))
        $nodes[$m.Key] = @($x0, $cy, $x1)
    }
    if (-not $now.Count) {
        $idle = if (-not $p.Queue) { '还没有队列' } elseif (-not $mo.Items.Count) { '队列里没有项' } elseif ($p.Available -and (Recent $p)) { "刚有动静（$(Ago $p.IdleMinutes)前）" } else { '没人在做，也不用你定' }
        $null = $chips.Append("<text class=`"morec`" x=`"$(Num (($colNow[0] + $colNow[1]) / 2))`" y=`"$(Num ($laneY + $tall / 2 + 4))`" text-anchor=`"middle`">$(Enc $idle)</text>")
    }
    foreach ($spec in @(@($shownNext, $opn, $colNext, 'nx'), @($shownLater, $blocked, $colLater, 'lt'))) {
        $list = @($spec[0]); $whole = @($spec[1]); $cols = $spec[2]; $cls = $spec[3]
        $slots = $list.Count + [int]($whole.Count -gt $list.Count)
        $top = $laneY + ($tall - $slots * 32) / 2 + 1
        $x0 = $cols[0] + 6; $x1 = $cols[1] - 6
        for ($k = 0; $k -lt $list.Count; $k++) {
            $m = $list[$k]; $cy = $top + $k * 32 + 14
            $null = $chips.Append((ChipSvg $m.Key $cls $x0 $x1 $cy 26 (Fit (ItemLabel $m) ($x1 - $x0 - 18) 12.5) $m.It.Goal '' '' $false))
            $nodes[$m.Key] = @($x0, $cy, $x1)
        }
        if ($whole.Count -gt $list.Count) {
            $cy = $top + $list.Count * 32 + 14
            $null = $chips.Append("<text class=`"morec`" x=`"$(Num ($x0 + 10))`" y=`"$(Num ($cy + 4))`">还有 $($whole.Count - $list.Count) 项</text>")
        }
    }
    $workTotal = @($mo.Items | Where-Object State -ne '搁置').Count
    $stateText = if (-not $p.Queue) { '还没有队列' } else { "$($done.Count) / $workTotal &#183; $(Enc (State $p)[0])" }
    $mid = $laneY + $tall / 2
    $barW = 130 * $(if ($workTotal) { $done.Count / $workTotal } else { 0 })
    $null = $laneSvg.Append("<a href=`"#p$pIdx`"><line class=`"lane`" x1=`"0`" x2=`"$mapW`" y1=`"$(Num ($laneY + $tall + 1))`" y2=`"$(Num ($laneY + $tall + 1))`"/><text class=`"ln`" x=`"4`" y=`"$(Num ($mid - 7))`">$(Enc (Fit (Nick $p.Name) 150 15))</text><text class=`"lm`" x=`"4`" y=`"$(Num ($mid + 12))`">$stateText</text><rect class=`"lt0`" x=`"4`" y=`"$(Num ($mid + 21))`" width=`"130`" height=`"3`"/><rect class=`"lt1`" x=`"4`" y=`"$(Num ($mid + 21))`" width=`"$(Num $barW)`" height=`"3`"/></a>")
    $laneY += $tall + 2
}
$mapH = $laneY
# 依赖线：两头都还没完成、都画在图上才画（折进"还有 n 项"的不连）；同一个决定里的不画，用一道括号标"一起定"。
foreach ($mo in $models) {
    $seenEdge = @{}
    $sameGroup = @{}
    foreach ($dc in $decisions | Where-Object { $_.Model.Index -eq $mo.Index }) { $g = @($dc.Item) + $dc.Kids; foreach ($x in $g) { $sameGroup[$x.Key] = $dc.Item.Key } }
    foreach ($b2 in $mo.Items) {
        foreach ($depId in $b2.DepIds) {
            $a2 = $mo.ById[$depId]
            if (-not $a2 -or $a2.State -in '完成', '搁置', '其他' -or $b2.State -in '完成', '搁置', '其他') { continue }
            if ($sameGroup[$a2.Key] -and $sameGroup[$a2.Key] -eq $sameGroup[$b2.Key]) { continue }
            $na = $nodes[$a2.Key]; $nb = $nodes[$b2.Key]
            if (-not $na -or -not $nb) { continue }
            $pair = "$($na -join ',')>$($nb -join ',')"
            if ($seenEdge[$pair]) { continue }
            $seenEdge[$pair] = $true
            if ([math]::Abs($na[0] - $nb[0]) -lt 2) {
                $path = "M$(Num $na[2]) $(Num $na[1])C$(Num ($na[2] + 22)) $(Num $na[1]),$(Num ($nb[2] + 22)) $(Num $nb[1]),$(Num $nb[2]) $(Num $nb[1])"
            } else {
                $midX = ($na[2] + $nb[0]) / 2
                $path = "M$(Num $na[2]) $(Num $na[1])C$(Num $midX) $(Num $na[1]),$(Num $midX) $(Num $nb[1]),$(Num $nb[0]) $(Num $nb[1])"
            }
            $edgeCls = if ($a2.State -eq '待用户') { 'e-ask' } else { 'e-live' }
            $null = $edgeSvg.Append("<g class=`"edge $edgeCls`" data-a=`"$($a2.Key)`" data-b=`"$($b2.Key)`"><path class=`"eb`" pathLength=`"1`" d=`"$path`"/><path class=`"ef`" d=`"$path`"/></g>")
        }
    }
}
foreach ($dc in $decisions | Where-Object { $_.Kids.Count }) {
    $ys = @(@($dc.Item) + $dc.Kids | ForEach-Object { $nodes[$_.Key][1] })
    $yStat = $ys | Measure-Object -Minimum -Maximum
    $bx = $colNow[1] - 6
    $null = $edgeSvg.Append("<g class=`"bracket`" data-k=`"$($dc.Item.Key)`"><path d=`"M$(Num ($bx + 2)) $(Num $yStat.Minimum)H$(Num ($bx + 8))V$(Num $yStat.Maximum)H$(Num ($bx + 2))`"/><text x=`"$(Num ($bx + 20))`" y=`"$(Num (($yStat.Minimum + $yStat.Maximum) / 2 - 18))`">一起定</text></g>")
}
$nowSub = @(if ($totals['待用户']) { "$($totals['待用户']) 等你" }; if ($totals['在做']) { "$($totals['在做']) 在做" }; if ($totals['待验证']) { "$($totals['待验证']) 待验证" }) -join ' &#183; '
$heads = ''
foreach ($hd in @(@(($colDone[0] + 2), '已完成', $totals['完成'], '', ''), @(($colNow[0] + 10), '现在', ($totals['待用户'] + $totals['在做'] + $totals['待验证']), $nowSub, ' on'), @(($colNext[0] + 6), '可以开工', $openCount, '', ''), @(($colLater[0] + 6), '被挡住', $blockedCount, '', ''))) {
    $heads += "<text class=`"hl$($hd[4])`" x=`"$($hd[0])`" y=`"28`">$($hd[1])</text><text class=`"hn`" data-col=`"$($hd[1])`" x=`"$($hd[0] - 2)`" y=`"76`">$($hd[2])</text>"
    if ($hd[3]) { $heads += "<text class=`"hc`" x=`"$($hd[0] + 36)`" y=`"76`">$($hd[3])</text>" }
}
$mapSvg = "<svg id=`"map`" viewBox=`"0 0 $mapW $(Num $mapH)`" role=`"img`" aria-label=`"全景图：横向是进度，纵向是项目`"><rect class=`"spot`" x=`"$($colNow[0])`" y=`"0`" width=`"$($colNow[1] - $colNow[0])`" height=`"$(Num $mapH)`"/>$heads$($laneSvg.ToString())$($edgeSvg.ToString())$($ticks.ToString())$($chips.ToString())</svg>"
$legend = (@(@('done', '完成'), @('ask', '等你'), @('doing', '在做'), @('verify', '待验证'), @('idle', '可以开工'), @('wait', '被挡住')) | ForEach-Object { "<span><i class=`"$($_[0])`"></i>$($_[1])</span>" }) -join ''
$mapNotes = @(
    if ($totals['搁置']) { "另有 $($totals['搁置']) 项搁置" }
    if ($totals['待放行']) { "$($totals['待放行']) 项待放行" }
    if ($totals['其他']) { "$($totals['其他']) 项写法不标准" }
    foreach ($mo in $models) { if (-not $mo.Items.Count) { "$(Nick $mo.P.Name) 没读到队列" } }
)
$mapNote = "<div class=`"mapnote`"><div class=`"legend`">$legend</div><div>$(if ($mapNotes) { Enc (($mapNotes -join '；') + '，没画在图上') })</div></div>"

# 顶上一句话：全是决定就说决定，还有别的（可能停了、方向要停）就说件事。
$null = $b.Append("<!doctype html><html lang=`"zh-CN`"><head><meta charset=`"utf-8`"><meta name=`"viewport`" content=`"width=device-width,initial-scale=1`"><title>项目状态</title><style>$style</style></head><body><main>")
$null = $b.Append("<div class=`"stamp`">$(Enc $s.Generated) 更新</div>")
if ($pageCount) {
    $unit = if ($decisions.Count + $looseCards.Count -eq $pageCount) { '个决定等你拍板' } else { '件事要你管' }
    $null = $b.Append("<h1><em>$pageCount</em> $unit</h1>")
    $subParts = @(
        if ($askCount -ne $decisions.Count) { "涉及 $askCount 项" }
        if ($followers.Count) { "后面还有 <b>$($followers.Count)</b> 项跟着它们走" }
    )
    $null = $b.Append("<p class=`"sub`">$(if ($subParts) { ($subParts -join '，') + '。' })</p>")
} else {
    $null = $b.Append('<h1>暂时没有要你管的事</h1><p class="sub"></p>')
}
# 本周目标没动（status.ps1 的 GoalStalled）：放在最上面，项目在忙别的、目标挂的项却没动，用户不看细节也能看出偏了。
$goalStuck = @($active | Where-Object { $_.GoalStalled })
foreach ($p in $goalStuck) {
    $g = $p.GoalStalled
    $null = $b.Append("<div class=`"alert`">本周目标没动：$(Enc (Nick $p.Name)) 有新提交，本周目标挂的 $(Enc ((@($g.Ids) | ForEach-Object { "#$_" }) -join '、')) 已 $(Ago $g.Minutes)没进展。在这个项目问一句在做什么，或者周会改目标</div>")
}
$null = $b.Append("<div class=`"mapwrap`">$mapSvg</div>$mapNote")

function CmdHtml([string]$t) { "<div class=`"cmd`"><code>$(Enc $t)</code><button type=`"button`" class=`"cp`" data-cmd=`"$(Enc $t)`">复制</button></div>" }
function ProjectMeta([string]$name, [string]$extra = '') { "<div class=`"meta`">$(Enc (Nick $name))$extra</div>" }
# 一项待用户的说明：卡就显示在这一项下面时，路径不用再写一遍；没挂上的卡只有这句话告诉用户它在哪。
function AttachedCards([string]$project, $i) { (@($cards | Where-Object { $_.Project -eq $project -and $_.Owner -and $_.Owner.Id -eq $i.Id -and $_.Owner.Goal -eq $i.Goal }) | ForEach-Object { CardBody $_.Card }) -join '' }
function SplitDetail([string]$detail, [bool]$attached) {
    $d = Plain $detail
    if ($attached) { $d = $d -replace '决定卡\s+\S+\.md\s*[：:]?\s*', '' }
    $rec = [regex]::Match($d, '(?<!不|没有|无|暂无|还没|未)推荐[^。；;]*')
    # "没有推荐""推荐"后面什么都没写，都不算有推荐：命令不能写成"按你的"。
    $hasRec = $rec.Success -and ($rec.Value -replace '^推荐[：:\s]*', '')
    $why = (($(if ($hasRec) { $d.Remove($rec.Index, $rec.Length) } else { $d })) -replace '[；;，,]\s*(?=[。；;，,])', '').Trim(' ', '；', ';', '。', '，', ',', '：', ':')
    @{ Why = $why; Rec = $(if ($hasRec) { $rec.Value }) }
}

# 要你管：一件一张卡。决定按牵动多少排，像已搁置的排最后。
$cardsHtml = [Collections.Generic.List[string]]::new()
foreach ($dc in $decisions) {
    $mo = $dc.Model; $name = [string]$mo.P.Name; $i = $dc.Item.It
    $attached = AttachedCards $name $i
    $parts = SplitDetail $i.Detail ([bool]$attached)
    $why = $parts.Why; $recText = $parts.Rec
    $kidIds = @($dc.Kids | ForEach-Object { "#$($_.Id)" })
    $kidRows = ''
    foreach ($kid in $dc.Kids) {
        $kidCards = AttachedCards $name $kid.It
        $kidParts = SplitDetail $kid.It.Detail ([bool]$kidCards)
        $extra = $kidParts.Why -replace '^同\s*#\S+?\s*一起定?\s*[；;，,：:]?\s*', ''
        $note = @($extra, ($kidParts.Rec -replace '^推荐[：:\s]*', '')) | Where-Object { $_ }
        $kidRows += "<li>$(ItemHtml $kid.It 30)$(if ($note) { "<em>$(Enc (Cut ($note -join '；') 120))</em>" })</li>"
        $attached += $kidCards
    }
    $downRows = (@($dc.Down | Select-Object -First 4) | ForEach-Object { "<li>$(ItemHtml $_.It 34)</li>" }) -join ''
    if ($dc.Down.Count -gt 4) { $downRows += "<li class=`"more`">还有 $($dc.Down.Count - 4) 项</li>" }
    $imp = if ($dc.Down.Count) { "<div class=`"imp`"><b>$($dc.Down.Count)</b><span>项跟着它</span></div>" } else { '<div class="imp z"><b>0</b><span>不牵动别的</span></div>' }
    $reply = if ($recText) { '按你的' } else { '你的答复' }
    $cmd = if ($dc.Item.Id) { "/next #$($dc.Item.Id) $reply" } else { "/next $reply" }
    if ($kidIds) { $cmd += "（连同 $($kidIds -join '、')）" }
    $how = @(
        if ($dc.Shelved) { "像是已经说过先不做：是的话发 <code>$(Enc "/next $(Label $i) 改成搁置")</code>" }
        if ($recText) { '同意推荐就发这条；不同意就把"按你的"换成你的答复' }
    )
    $keys = (@($dc.Item) + $dc.Kids | ForEach-Object Key) -join ' '
    $h = "<li class=`"card`" id=`"d$($dc.Item.Key)`" data-keys=`"$keys`" style=`"--i:$([math]::Min($cardsHtml.Count, 6))`"><div class=`"ct`"><div>$(ProjectMeta $name $(if ($kidIds) { " &#183; $($kidIds.Count + 1) 项一起定" }))<div class=`"q`">$(ItemHtml $i 60)$(if ($dc.Shelved) { ' <span class="tag muted">像已搁置</span>' })</div></div>$imp</div>"
    if ($why) { $h += "<div class=`"why`">$(Enc (Cut $why 200))</div>" }
    if ($recText) { $h += "<div class=`"rec`"><span>推荐</span>$(Enc (Cut ($recText -replace '^推荐[：:\s]*', '') 140))</div>" }
    if ($kidRows) { $h += "<div class=`"after`"><span>一起定</span><ul>$kidRows</ul></div>" }
    if ($downRows) { $h += "<div class=`"after`"><span>定了之后</span><ul>$downRows</ul></div>" }
    $h += "$attached$(CmdHtml $cmd)"
    if ($how) { $h += "<div class=`"how`">$($how -join '；')</div>" }
    $cardsHtml.Add("$h</li>")
}
foreach ($c in $looseCards) { $cardsHtml.Add("<li class=`"card`" style=`"--i:$([math]::Min($cardsHtml.Count, 6))`">$(ProjectMeta $c.Project)<div class=`"q`">有一张决定卡等你定</div>$(CardBody $c.Card)$(CmdHtml "/next 决定卡 $(Split-Path $c.Card.File -Leaf) 你的答复")</li>") }
foreach ($stop in $stops) { $cardsHtml.Add("<li class=`"card`" style=`"--i:$([math]::Min($cardsHtml.Count, 6))`">$(ProjectMeta $stop.Project)<div class=`"q`">方向 $(Enc $stop.Dir.Name) 要停：$(Enc (Cut $stop.Dir.Reason 120))</div><div class=`"how`">先复盘，再报决定卡给你定</div>$(CmdHtml '/next')</li>") }
foreach ($mo in $models | Where-Object { IsStalled $_.P }) {
    $doingNow = Of $mo '在做'
    $first = @($doingNow)[0]
    $stallCmd = if ($first -and $first.Id) { "/next #$($first.Id)" } else { '/next' }
    $cardsHtml.Add("<li class=`"card`" id=`"s$($mo.Index)`" data-keys=`"$(($doingNow | ForEach-Object Key) -join ' ')`" style=`"--i:$([math]::Min($cardsHtml.Count, 6))`">$(ProjectMeta $mo.P.Name)<div class=`"q`">可能停了：$(if ($first) { ItemHtml $first.It 40 } else { '在做的项' })，已经 $(Ago $mo.P.IdleMinutes)没动静</div>$(CmdHtml $stallCmd)<div class=`"how`">接着做</div></li>")
}
$null = $b.Append('<h2>要你管<small>到对应项目新建会话，发卡片上的命令</small></h2>')
if ($cardsHtml.Count) { $null = $b.Append("<ol class=`"cards`">$($cardsHtml -join '')</ol>") }
else { $null = $b.Append('<div class="none">暂时没有要你处理的事</div>') }
if ($unattended) { $null = $b.Append("<div class=`"free`"><b>有活没人做</b>：$(($unattended | ForEach-Object { Enc "$(Nick $_.Name)（$($_.Available) 项可领，已 $(Ago $_.IdleMinutes)没动静）" }) -join '、')。到这个项目新建会话，发 <code>/next</code></div>") }
if ($free) { $null = $b.Append("<div class=`"free`">有空可以开工：$(($free | ForEach-Object { Enc "$(Nick $_.Name)（$($_.Available) 项）" }) -join '、')。到这个项目新建会话，发 <code>/next</code></div>") }

# 本周目标
$null = $b.Append('<h2>本周目标</h2>')
$withGoals = @($active | Where-Object { @($_.Goals).Count })
if ($withGoals) {
    $null = $b.Append('<div class="goals">')
    foreach ($p in $withGoals) {
        $g = @($p.Goals)
        $list = ($g | ForEach-Object { "<span class=`"$(if ($_.Done) { 'done-goal' })`">$(if ($_.Done) { '✓' } else { '○' }) $(Enc (Plain $_.Text))</span>" }) -join '<br>'
        $null = $b.Append("<div class=`"p`">$(Enc (Nick $p.Name))<div class=`"sub2`">完成 $(@($g | Where-Object Done).Count)/$($g.Count)</div></div><div>$list</div>")
    }
    $null = $b.Append('</div>')
} else { $null = $b.Append('<div class="none">还没定，周会（<code>/week</code>）时定</div>') }

# 各项目：推进中的展开，维护中的收起来
function Progress($p) {
    if (-not $p.Queue) { return '<span class="prog">还没有队列</span>' }
    $q = $p.Queue; $total = 0; foreach ($v in $q.PSObject.Properties) { if ($v.Name -ne '搁置') { $total += [int]$v.Value } }
    $done = [int]$q.'完成'
    $segs = foreach ($st in @(@('完成', 'done'), @('待验证', 'verify'), @('在做', 'doing'), @('待用户', 'ask'))) {
        $c = [int]$q.($st[0])
        if ($c -and $total) { "<span class=`"seg $($st[1])`" style=`"width:$([math]::Round(100 * $c / $total, 1))%`" title=`"$($st[0]) $c`"></span>" }
    }
    "<span class=`"prog`"><span class=`"bar`">$($segs -join '')</span>完成 $done / 共 $total 项</span>"
}
function BlockedHtml($mo) {
    $blocked = @($mo.Items | Where-Object { $_.State -eq '待做' -and -not $_.Claimable })
    if (-not $blocked) { return '' }
    $rows = (@($blocked | Select-Object -First 5) | ForEach-Object {
        $m = $_
        $unmet = @($m.DepIds | Where-Object { $mo.ById[$_] -and $mo.ById[$_].State -ne '完成' })
        $why = if ($unmet) { '等 ' + ((@($unmet | Select-Object -First 3) | ForEach-Object { "#$_" }) -join '、') } elseif ($m.DepText) { '等 ' + (Cut $m.DepText 20) } else { '方向已停' }
        "<li>$(ItemHtml $m.It 34) <span class=`"wait`">$(Enc $why)</span></li>"
    }) -join ''
    if ($blocked.Count -gt 5) { $rows += "<li class=`"more`">还有 $($blocked.Count - 5) 项</li>" }
    "<ul class=`"items`">$rows</ul>"
}
function ProjectCard($mo) {
    $p = $mo.P
    $st = State $p
    $doing = @($p.Doing)
    $now = if (IsStalled $p) { "$(ListHtml $doing)<div>$(Ago $p.IdleMinutes)没动静</div>" }
           elseif ($doing) { ListHtml $doing }
           elseif ((Asks $p).Count) { '等你定，见上面' }
           elseif ($p.Available -and (Recent $p)) { "刚有动静（$(Ago $p.IdleMinutes)前），有 $($p.Available) 项可做" }
           elseif ($p.Available) { "空着，有 $($p.Available) 项可以开工" }
           elseif ($p.Queue) { '暂时没有能做的项' } else { '还没有队列' }
    $bench = $p.Direction
    $flow = if ($bench -and $bench.FlowUrl) { "<a href=`"$(Enc $bench.FlowUrl)`" target=`"_blank`">流程图</a>" }
    $facts = [Collections.Generic.List[string]]::new()
    $star = @(@($p.Digest.Lines) | Where-Object { $_ -match '^北极星' }) | Select-Object -First 1
    if ($star) { $facts.Add("<dt>北极星</dt><dd>$(Enc (Cut (Plain ($star -replace '^北极星[：:]\s*', '')) 110)) <span class=`"more`">（$(Enc $p.Digest.Date) 复盘）</span></dd>") }
    $dirs = @(if ($bench) { @($bench.Directions) | Where-Object { $_ } })
    if ($dirs) { $facts.Add("<dt>方向</dt><dd>$(($dirs | ForEach-Object { Enc "$($_.Name)（$($_.State)）" }) -join '、')</dd>") }
    # 活的标记只给真有动静的：维护中的项目和久没动静的，写着在做也不闪。
    $liveClass = if (-not (IsStalled $p) -and $doing -and (Recent $p)) { ' class="live"' } else { '' }
    $staleClass = if (IsStalled $p) { ' class="stale"' } else { '' }
    $facts.Add("<dt$liveClass>现在</dt><dd$staleClass>$now</dd>")
    $askList = @(Asks $p)
    if ($askList) { $facts.Add("<dt>等你定</dt><dd>$(ListHtml $askList)</dd>") }
    if ($p.Next) { $facts.Add("<dt>接下来</dt><dd>$(ListHtml $p.Next)</dd>") }
    $blockedRows = BlockedHtml $mo
    if ($blockedRows) { $facts.Add("<dt>被挡住</dt><dd>$blockedRows</dd>") }
    # 会话自己加、还没人放行的项（/next 第 4 节）：不领，等你或周会说做再改成待做。
    if ($p.Pending) { $facts.Add("<dt>待放行</dt><dd>$(ListHtml $p.Pending)<div class=`"how`">会话自己加的，你或周会说做，才改成待做</div></dd>") }
    if ($p.Recent) { $facts.Add("<dt>最近完成</dt><dd>$(ListHtml $p.Recent)</dd>") }
    $x = [Text.StringBuilder]::new()
    $null = $x.Append("<section class=`"proj`" id=`"p$($mo.Index)`"><div class=`"proj-h`"><h3>$(Enc (Nick $p.Name))</h3><span class=`"tag $($st[1])`">$(Enc $st[0])</span><span class=`"right`">$flow$(Progress $p)$(if ($null -ne $p.Priority) { "<span>优先级 $(Enc $p.Priority)</span>" })</span></div>")
    $benchHtml = ''
    if ($bench -and $bench.Benchmark -eq 'ok') {
        $gapNote = if ($bench.Note) { '<div class="why">' + (Enc (Cut (Plain $bench.Note) 60)) + '</div>' } else { '' }
        $gapText = if ($null -ne $bench.Gap) { '<div class="gap">差距 ' + (Num $bench.Gap) + '<span>（' + (Enc $bench.LastRun) + '）</span></div>' + $gapNote } else { '<div class="more">还没量</div>' }
        $base = if ($bench.Baseline) { "<div class=`"how`">基准：$(Enc $bench.Baseline.Model)，$(Enc $bench.Baseline.Date)$(if ($bench.Baseline.Cost) { '，' + (Enc $bench.Baseline.Cost) })$(if ($bench.Baseline.Minutes) { '，' + (Enc $bench.Baseline.Minutes) + ' 分钟' })</div>" }
        $weeks = @(@($bench.Trend) | Where-Object { $_ } | Select-Object -Last 12)
        $trend = if ($weeks) { "$(Spark $weeks)<div class=`"how`">按周：$(($weeks | ForEach-Object { Num $_.Gap }) -join ' → ')。虚线是基准，越低越好，碰到或低于虚线就比过了</div>" }
        $pic = if ($bench.ImageUrl) { Thumb $bench.ImageUrl "$(Nick $p.Name) 和基准的并排图" } else { '<div class="how">这次没有并排图</div>' }
        $benchHtml = "<div class=`"bench`"><div><span class=`"k`">和基准比</span>$gapText$base$trend</div><div><span class=`"k`">并排图（点开看大图）</span>$pic</div></div>"
    }
    $null = $x.Append("<div class=`"pgrid$(if ($benchHtml) { ' two' })`"><dl class=`"facts`">$($facts -join '')</dl>$benchHtml</div>")
    if ($bench -and $bench.Benchmark -eq 'ok') { foreach ($d in @($bench.Stopped) | Where-Object { $_ }) { $null = $x.Append("<div class=`"alert`">方向 $(Enc $d.Name) 要停：$(Enc (Cut $d.Reason 120))</div>") } }
    if ($bench -and $bench.FlowUrl) { $null = $x.Append("<details class=`"flowbox`"><summary>展开流程图：这个项目从输入到输出，每一步谁做</summary><iframe src=`"$(Enc $bench.FlowUrl)`" loading=`"lazy`" sandbox title=`"$(Enc (Nick $p.Name)) 的流程图`"></iframe></details>") }
    if ($bench -and $bench.Benchmark -ne 'notApplicable' -and $p.Status -eq '推进中') {
        $lack = @(if ($bench.Benchmark -eq 'none') { '还没登记基准' }; if (-not $bench.FlowUrl) { '还没有流程图' })
        if ($lack) { $null = $x.Append("<div class=`"missing`">$(if ($p.Unwatched) { '方向没人看：' })$($lack -join '，')：下次在这个项目发 /next 会先做</div>") }
    }
    $det = [Collections.Generic.List[string]]::new()
    $other = @($p.Other)
    if ($other) { $det.Add("队列里有 $($other.Count) 项的状态写法不标准，下次在这个项目发 /next 会顺手改好") }
    if ($p.Queue) { $q = $p.Queue; $det.Add("队列：在做 $($q.'在做') · 待做 $($q.'待做')（可领 $($p.Available)） · 待验证 $($q.'待验证') · 等你 $($q.'待用户')$(if ($q.'待放行') { " · 待放行 $($q.'待放行')" }) · 完成 $($q.'完成')$(if ($q.'搁置') { " · 搁置 $($q.'搁置')" })$(if ($q.'其他') { " · 写法不标准 $($q.'其他')" })") }
    if ($p.LastActivity) { $det.Add("最后动静 $($p.LastActivity)（$(Ago $p.IdleMinutes)前）；主干新提交 $($p.NewCount)（$($p.NewSince)）") }
    if ($null -ne $p.Worktrees -and ($p.WorktreesMerged + $p.WorktreesDetached + $p.BranchesMerged)) { $det.Add("可以清理：已合并的分支 $($p.BranchesMerged) 个，临时工作目录 $($p.Worktrees) 个") }
    if ($p.Trust) { $det.Add("信任等级 $($p.Trust)") }
    foreach ($y in @($p.Problems) | Where-Object { $_ -notmatch '^(可能停滞|队列里状态认不出)' }) { $det.Add("提示：$(Cut $y 120)") }
    if ($det.Count) { $null = $x.Append('<details><summary>细节</summary>' + (($det | ForEach-Object { "<div>$(Enc $_)</div>" }) -join '') + '</details>') }
    $null = $x.Append('</section>')
    $x.ToString()
}
$null = $b.Append('<h2>各项目</h2>')
$running = @($models | Where-Object { $_.P.Status -ne '维护' })
$kept = @($models | Where-Object { $_.P.Status -eq '维护' })
foreach ($mo in $running) { $null = $b.Append((ProjectCard $mo)) }
if ($kept) {
    $null = $b.Append("<details class=`"maint`"><summary>维护中的项目（$($kept.Count) 个）</summary>")
    foreach ($mo in $kept) { $null = $b.Append((ProjectCard $mo)) }
    $null = $b.Append('</details>')
}
if (@($s.Paused)) { $null = $b.Append("<div class=`"paused`">暂停：$(Enc ((@($s.Paused) | ForEach-Object { Nick $_ }) -join '、'))</div>") }
$null = $b.Append('<details class="gloss"><summary>这些词是什么意思</summary><dl><dt>北极星</dt><dd>这个项目最终要做好的那个数，用它判断方向对不对。</dd><dt>基准</dt><dd>直接用通用模型能做到的结果。项目要比它好才有意义。</dd><dt>差距</dt><dd>最新结果和基准差多少。0 是一样，越低越好，小于等于 0 就算比过了。</dd><dt>方向</dt><dd>一条要花预算试的路线。差距连续 2 周没缩小、14 天没量，或者预算花完还没比过基准，就停下复盘。</dd><dt>决定卡</dt><dd>要你拍板时的一页材料：选项、代价和推荐。</dd><dt>待验证</dt><dd>改完了，等全新上下文的审查方专门挑错。</dd><dt>流程图</dt><dd>这个项目从输入到输出分几步，每一步是模型、程序、人还是外部服务做的。</dd></dl></details>')
$null = $b.Append("</main><script>$pageScript</script></body></html>")

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
    foreach ($p in $unattended) { $lines.Add("$(Nick $p.Name)：有 $($p.Available) 项可领，已 $(Ago $p.IdleMinutes)没人做，可以发 /next") }
    if ($free) { $lines.Add("$((@($free | ForEach-Object { Nick $_.Name })) -join '、') 空着，可以发 /next 开工") }
    $title = if ($n -and -not $fresh) { "要你管 $n 件事（都推过）" } elseif ($n) { "要你管 $n 件事" } elseif ($free -or $unattended) { '有项目可以开工' } else { '暂时没有要你管的事' }
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
