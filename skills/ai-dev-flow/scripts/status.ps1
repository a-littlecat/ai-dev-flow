[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Since,
    [string[]]$Project,
    [switch]$All,
    [switch]$Lessons,
    [switch]$Mark,
    [switch]$Json,
    [int]$StaleMinutes = 60,
    [int]$IdleHours = 12,
    [int]$GoalHours = 24,
    [int]$CleanupOver = 10,
    [int]$SlowVerifyMinutes = 10
)
# 收状态：按总览仓库的项目清单 projects.json，列出每个项目的事实——主干新提交、未复盘的提交（只改队列文件和它的搁置文件的不算）、队列各状态的项数和待用户项、
# 最近一份复盘摘要、worktree 和分支、未提交改动、最后活动时间、可领的项、本周目标、该升级的教训、还没转的请求。只收事实，判断和汇报由总览做（格式见 ai-dev-flow modules/portfolio.md）。
# 在总览仓库里任意目录运行，或用 -Config 指定清单（默认 <仓库>/projects.json）。
#   默认      推进中的项目全量；维护中的只列提交数、队列和待用户项；暂停的只列名字
#   -Since    新提交从这个时间算（git 的写法：'24 hours ago'、'2026-10-30'）；不给就从上次 -Mark 记下的位置算，没有记录按 24 小时
#   -Project  只看这几个（按名字，多个用逗号隔开，暂停的也看）
#   -All      维护中的也全量
#   -Lessons  附上各项目 LESSONS.md 每条教训的 Seen 和标题（合并跨项目教训用）
#   -Mark     把各项目当前的主干位置记为下次的起点（周会时用），记在 <清单所在目录>/.agents/status-marks.json
#   -Json     输出 JSON
#   -StaleMinutes  推进中的项目有"在做"的项、最后活动又早于这么多分钟前，提示"可能停滞"（默认 60）
#   -SlowVerifyMinutes  快检超过这么多分钟算太慢（默认 10，harness.md 第 2 节）；项目 AGENTS.md 写"快检提速阈值：<分钟> 分钟"的以项目为准
#   -IdleHours     推进中的项目有可领的项、没有"在做"的、最后活动又早于这么多小时前，提示"有活没人做"（默认 12），不管有没有待用户项
#   -GoalHours     推进中的项目这么多小时内有新提交，本周目标挂的、还没完成的项却这么久没有提到它的提交，提示"本周目标没动"（默认 24）
#   -CleanupOver   已合进主干的分支或 worktree 超过这么多个，提示运行 cleanup.ps1（默认 10）
# 最后活动：所有本地分支里最新的提交时间，和 .agents/runs 下（两层以内）最新的文件改动时间，取较晚者。
# 可领：状态"待做"、依赖为空或"无"、依赖的编号在本队列里都已"完成"（队列和搁置文件里都找不到的按已完成算，完成的项会删；搁置文件读不出表时不这么算），而且不在搁置文件里；
#   依赖里写了编号以外的东西（例如别的项目的项）就不算可领。
# 接下来（Next）：可领的前 3 项；最近完成（Recent）：队列里最后 3 个"完成"的项。
# 待放行（Pending）：会话自己加、还没人放行的项（skills/next/SKILL.md 第 4 节），不算可领，依赖它的也没满足，文本和状态页逐条列出。
# 全部项（Items，只在 -Json 里）：队列每一项的编号、目标、状态、说明、依赖原文和是否可领（Claimable），状态页画全景图用。
# 该升级的教训（LessonsDue）：LESSONS.md 里 Seen 达到 3、又没写"升级："一行的教训（garden.md 第 2 节第 5 步）。
# 还没转的请求（Requests）：docs/requests.md 里状态"待转"或没写状态的 ## 小节（portfolio.md 第 7 节）。
# 快检太慢（VerifySeconds 和提示）：推进中的项目 .agents/verify-last.json 的用时超过阈值，队列里又没有目标写着"快检提速"、还没完成的项。
# 该清理（提示）：已合进主干的分支或 worktree 超过 -CleanupOver 个（land.md 第 6 节）。
# 基准和方向（Direction）：判定都在 direction.ps1（modules/direction.md），这里接过来。要停或已结束的方向，它的 [方向 X]、[方向原型 X] 项不算可领；队列里有 [方向 X] 项、
#   方向却没写成"进行中"的（没定就排了）提示。推进中的项目把 Actions 写成提示；benchmark.json 写错的任何状态都提示。
# 死掉的运行（DeadRuns）：.agents/runs 下 7 天内开始、没有 exit.json、进程也不在了、同一分支后来也没再派过的运行。
# 待用户项的 Hint：状态格超过 300 字的是"过程记录"；没那么长、写着 不急， / 先停 / 先不改 / 本周暂停 / 搁置 / 等（别处）…提出 这类话的是"像搁置"（"等你…""要不要先停"不算；说明 / 备注列只认 先不做 / 先不改 / 本周暂停 / 不主动做）；都写成"提示"。
# 本周目标：清单里项目的 goals（[{ "text": "...", "items": ["22"], "done": false }]）；done 为 true，或 items 里的项在队列里都"完成"，算完成。
# 只读各项目：不 fetch，不改项目里的任何文件；git 不拿可选锁，不刷新项目的索引，不和项目会话的提交抢 index.lock。
$ErrorActionPreference = 'Stop'
$env:GIT_OPTIONAL_LOCKS = '0'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8

if (-not $Config) {
    $top = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -or -not $top) { throw 'Run status.ps1 inside the portfolio repository, or pass -Config <projects.json>' }
    $Config = Join-Path $top 'projects.json'
}
if (-not (Test-Path -LiteralPath $Config)) { throw "No project list: $Config (see ai-dev-flow modules/portfolio.md)" }
$Config = (Resolve-Path -LiteralPath $Config).ProviderPath
$cfg = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
$projects = @($cfg.projects | Where-Object { $_ })
if (-not $projects.Count) { throw "No projects in $Config" }
$names = @($projects | ForEach-Object { $_.name })
$Project = @($Project | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
foreach ($n in $Project) { if ($names -notcontains $n) { throw "Unknown project: $n (names: $($names -join ', '))" } }

$marksFile = Join-Path ([IO.Path]::GetDirectoryName($Config)) '.agents/status-marks.json'
$marks = @{}
if (Test-Path -LiteralPath $marksFile) {
    (Get-Content -LiteralPath $marksFile -Raw -Encoding UTF8 | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $marks[$_.Name] = $_.Value }
}

$states = '待做', '在做', '待验证', '待用户', '待放行', '完成', '搁置'
# 常见的另一种写法归到标准状态。只认这个词单独写或后面紧跟括号：归错会放行依赖、藏掉提示，说不准的（"已完成部分""暂停于安全点""部分已定"）不归，照常提示。
# 括号里还有半截话的也不归（已合并（到分支，待验证）、暂停（要不要继续））；暂停里写着安全点、接力的是接力（/next 第 3 节当待做），不算搁置。
$aliasUnsure = '部分|一半|阶段|到分支|未|待|等你|等您|要不要|[?？]'
$stateAliases = @(@("^(已合并|已完成)(?=$|[（(])(?!.*($aliasUnsure))", '完成'), @('^进行中(?=$|[（(])', '在做'), @("^暂停(?=$|[（(])(?!.*(安全点|接力|$aliasUnsure))", '搁置'))
# 待用户项里像"先不做 / 在等别处"的说法。"等你 / 等您 / 等待…"是在问用户，不算；"暂停""不急"单独出现常在问句里（要不要暂停、不急着要），只认带停顿的写法。
# 说明 / 备注列常写来龙去脉（"搁置过、已恢复"），只认更窄的几个词。判错只影响标签：像搁置的项照常算要你管（daily.ps1）。
$shelvedWords = '不急[，,。；;）)]|不急$|(?<!要不要)先停|先不做|先不改|(?<!要不要)先暂停|本周暂停|搁置|不主动做|等(?!你|您|待).{0,40}?(提出|结果|跑通|下来|再开|再做|再定)'
$noteWords = '先不做|先不改|本周暂停|不主动做'
$statusOrder = @{ '推进中' = 0; '维护' = 1; '暂停' = 2 }

function Format-Idle([int]$m) {
    if ($m -lt 60) { "$m 分钟" } elseif ($m -lt 2880) { "$([math]::Floor($m / 60)) 小时" } else { "$([math]::Floor($m / 1440)) 天" }
}

function Short([string]$s, [int]$n) {
    $s = ($s -replace '\s+', ' ').Trim()
    if ($s.Length -gt $n) { $s.Substring(0, $n - 1) + '…' } else { $s }
}

# 队列项的编号写成 #7；没有编号的返回空，别显示成一个孤零零的 #。
function Format-Id([string]$id, [int]$n = 12) { $v = ($id -replace '^#', '').Trim(); if ($v) { '#' + (Short $v $n) } else { '' } }

# 队列：Markdown 表格，表头里有"状态"列、下一行是分隔行；状态格以 待做 / 在做 / 待验证 / 待用户 / 待放行 / 完成 / 搁置 开头，后面可以跟括号说明。
# 首尾竖线可有可无；代码块里的不算（围栏按 CommonMark：同种字符、不短于开头、整行只有围栏才算结束；表格外缩进 4 格的行算缩进代码）。
function Read-Queue([string]$file) {
    $cols = $header = $fence = $null
    foreach ($line in Get-Content -LiteralPath $file -Encoding UTF8) {
        if ($fence) {
            $m = [regex]::Match($line, '^ {0,3}(`{3,}|~{3,})\s*$')
            if ($m.Success -and $m.Groups[1].Value[0] -eq $fence[0] -and $m.Groups[1].Value.Length -ge $fence.Length) { $fence = $null }
            continue
        }
        $m = [regex]::Match($line, '^ {0,3}(`{3,}|~{3,})')
        if ($m.Success) { $fence = $m.Groups[1].Value; $cols = $header = $null; continue }
        if ($line -notmatch '\|' -or (-not $cols -and $line -match '^( {4}|\t)')) { $cols = $header = $null; continue }
        $cells = @(($line.Trim() -replace '^\||\|$', '') -split '(?<!\\)\|' | ForEach-Object { $_.Trim() })
        if ($header) {
            $cols = if (-not @($cells | Where-Object { $_ -notmatch '^:?-+:?$' }).Count) { $header }
            if ($cols) { $script:queueTableSeen = $true }
            $header = $null
            continue
        }
        if (-not $cols) {
            if ($cells -contains '状态') { $header = $cells }
            continue
        }
        $get = { param($name) $i = [array]::IndexOf($cols, $name); if ($i -ge 0 -and $i -lt $cells.Count) { $cells[$i] } else { '' } }
        $raw = ((& $get '状态') -replace '\*', '').Trim()
        $state = $states | Where-Object { $raw.StartsWith($_, [StringComparison]::Ordinal) } | Select-Object -First 1
        $len = "$state".Length
        if (-not $state) { foreach ($a in $stateAliases) { $m = [regex]::Match($raw, $a[0]); if ($m.Success) { $state = $a[1]; $len = $m.Length; break } } }
        [pscustomobject]@{
            Id     = & $get '#'
            Goal   = $(if ($cols -contains '目标') { & $get '目标' } else { & $get '项' })
            Tier   = (& $get '档') -replace '\*', ''
            Deps   = & $get '依赖'
            Note   = $(foreach ($c in $cols) { if ($c -match '^(说明|备注)') { & $get $c; break } })
            State  = if ($state) { $state } else { '其他' }
            Detail = if ($state) { $raw.Substring($len).Trim() -replace '^[（(]', '' -replace '[）)]$', '' } else { $raw }
        }
    }
}

# 搁置文件：和队列同目录，文件名加 -shelved（docs/queue.md → docs/queue-shelved.md）。
function Get-ShelfPath([string]$queueFile) { [IO.Path]::Combine([IO.Path]::GetDirectoryName($queueFile), [IO.Path]::GetFileNameWithoutExtension($queueFile) + '-shelved' + [IO.Path]::GetExtension($queueFile)) }

function Get-ProjectStatus($p) {
    $r = [ordered]@{
        Name = $p.name; Status = $p.status; Priority = $p.priority
        DependsOn = @($p.dependsOn | Where-Object { $_ })
        Trust = $null; Trunk = $null; Head = $null; HeadDate = $null
        NewSince = $null; NewCount = 0; NewCommits = @(); Unreviewed = $null
        Queue = $null; Items = @(); Waiting = @(); Pending = @(); Doing = @(); Other = @(); Next = @(); Recent = @(); Digest = $null
        Uncommitted = $null; Untracked = $null; Worktrees = $null; WorktreesMerged = $null; WorktreesDetached = $null; WorktreesMissing = $null; BranchesMerged = $null
        Lessons = @(); LessonsDue = @(); Requests = @(); DeadRuns = @(); VerifySeconds = $null; Direction = $null
        LastActivity = $null; IdleMinutes = $null; Available = $null; Goals = @(); Unwatched = $false; GoalStalled = $null
        Problems = [Collections.Generic.List[string]]::new()
    }
    if ($statusOrder.Keys -notcontains $p.status) { $r.Problems.Add("状态应为 推进中 / 维护 / 暂停，现在是：$($p.status)") }
    foreach ($d in $r.DependsOn) { if ($names -notcontains $d) { $r.Problems.Add("依赖的项目不在清单里：$d") } }
    $path = $p.path
    if (-not $path -or -not (Test-Path -LiteralPath $path)) { $r.Problems.Add("路径不存在：$path"); return [pscustomobject]$r }
    $null = git -C $path rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE) { $r.Problems.Add('不是 Git 仓库'); return [pscustomobject]$r }

    $agents = Join-Path $path 'AGENTS.md'
    if (Test-Path -LiteralPath $agents) {
        $m = [regex]::Match((Get-Content -LiteralPath $agents -Raw -Encoding UTF8), '信任等级[^L\r\n]{0,8}(L[0-3])')
        $r.Trust = if ($m.Success) { $m.Groups[1].Value } else { '未写等级' }
    } else { $r.Trust = '未写等级'; $r.Problems.Add('没有 AGENTS.md') }

    $r.Trunk = if ($p.trunk) { $p.trunk } else { git -C $path rev-parse --abbrev-ref HEAD 2>$null }
    $head = git -C $path rev-parse --verify --quiet "$($r.Trunk)^{commit}" 2>$null
    if (-not $head) { $r.Problems.Add("主干分支不存在：$($r.Trunk)"); return [pscustomobject]$r }
    $r.Head = $head
    $r.HeadDate = git -C $path log -1 --format=%cd '--date=format:%Y-%m-%d %H:%M' $head

    $mark = $marks[$p.name]
    $useMark = $false
    if (-not $Since -and $mark) {
        $null = git -C $path merge-base --is-ancestor $mark.head $head 2>$null
        $useMark = -not $LASTEXITCODE
        if (-not $useMark) { $r.Problems.Add('上次标记的提交不在主干历史里，新提交改按 24 小时算') }
    }
    $logArgs = @(if ($useMark) { $r.NewSince = "自上次标记 $($mark.time)"; "$($mark.head)..$head" }
                 elseif ($Since) { $r.NewSince = "自 $Since"; "--since=$Since"; $head }
                 else { $r.NewSince = '近 24 小时'; '--since=24 hours ago'; $head })
    $r.NewCommits = @(git -C $path log --format='%h %s' @logArgs)
    $r.NewCount = $r.NewCommits.Count

    $lessonsFile = Join-Path $path 'LESSONS.md'
    if (Test-Path -LiteralPath $lessonsFile) {
        $text = Get-Content -LiteralPath $lessonsFile -Raw -Encoding UTF8
        $m = [regex]::Match($text, 'reviewed-through:\s*([0-9a-fA-F]{4,40})')
        if ($m.Success) {
            # 只改队列文件和它的搁置文件的提交（认领、改状态、搬行）不算：它们占一大半，按总数算会天天触发复盘。
            $qRel = $(if ($p.queue) { $p.queue } else { 'docs/queue.md' }) -replace '\\', '/'
            $shelfRel = (Get-ShelfPath $qRel) -replace '\\', '/'
            $count = git -C $path rev-list --count --full-history "$($m.Groups[1].Value)..$head" -- . ":(exclude)$qRel" ":(exclude)$shelfRel" 2>$null
            if ($LASTEXITCODE) { $r.Problems.Add("LESSONS.md 的 reviewed-through 不是有效提交：$($m.Groups[1].Value)") } else { $r.Unreviewed = [int]$count }
        }
        $all = @(foreach ($sec in ($text -split '(?m)^(?=##\s)') | Where-Object { $_ -match '^##\s' }) {
            $seen = [regex]::Match($sec, 'Seen[：:]\s*(\d+)')
            [pscustomobject]@{ Seen = if ($seen.Success) { [int]$seen.Groups[1].Value } else { $null }; Title = (($sec -split '\r?\n')[0] -replace '^##\s+', '').Trim()
                               Handed = $sec -match '(?m)^\s*升级[：:]' }
        })
        if ($Lessons) { $r.Lessons = @($all | Select-Object Seen, Title) }
        # 写了"升级："一行的已经交出去（改成测试、写进标准，或请求了 ai-dev-flow），不再催。
        $r.LessonsDue = @($all | Where-Object { $_.Seen -ge 3 -and -not $_.Handed } | Select-Object Seen, Title)
        if ($r.LessonsDue) { $r.Problems.Add('教训 Seen 达到 3 还没升级：' + (($r.LessonsDue | ForEach-Object { "$(Short $_.Title 30)（Seen $($_.Seen)）" }) -join '、')) }
    }

    $requestsFile = Join-Path $path 'docs/requests.md'
    if (Test-Path -LiteralPath $requestsFile) {
        $text = Get-Content -LiteralPath $requestsFile -Raw -Encoding UTF8
        $r.Requests = @(foreach ($sec in ($text -split '(?m)^(?=##\s)') | Where-Object { $_ -match '^##\s' }) {
            $m = [regex]::Match($sec, '(?m)^\s*(?:[-*]\s*)?\**状态\**\s*[：:]\s*\**\s*(.*?)\s*$')
            $state = if ($m.Success) { $m.Groups[1].Value } else { '' }
            if (-not $state -or $state.StartsWith('待转', [StringComparison]::Ordinal)) {
                [pscustomobject]@{ Title = (($sec -split '\r?\n')[0] -replace '^##\s+', '').Trim(); State = if ($state) { $state } else { '未写状态' } }
            }
        })
        if ($r.Requests) { $r.Problems.Add("还没转进队列的请求 $($r.Requests.Count) 条：" + (($r.Requests | ForEach-Object { Short $_.Title 30 }) -join '、')) }
    }

    $stoppedDirs = @()
    try {
        $r.Direction = & (Join-Path $PSScriptRoot 'direction.ps1') -Repo $path -Json | Out-String | ConvertFrom-Json
        $stoppedDirs = @(@($r.Direction.Stopped | ForEach-Object { $_.Name }) + @(@($r.Direction.Directions) | Where-Object { $_.State -eq '结束' } | ForEach-Object { $_.Name }))
    } catch { $r.Problems.Add("direction.ps1 出错：$($_.Exception.Message)") }
    $global:LASTEXITCODE = 0
    $tagRe = '^[\s*]*\[方向(原型)?\s+([^\]]+?)\s*\]'

    $done = @()
    $items = @()
    $queueRel = if ($p.queue) { $p.queue } else { 'docs/queue.md' }
    $queueFile = Join-Path $path $queueRel
    if (Test-Path -LiteralPath $queueFile) {
        $items = @(Read-Queue $queueFile)
        if (-not $items.Count) { $r.Problems.Add("$queueRel 里没有带「状态」列的表") }
        # 搁置的行放在队列旁的搁置文件里（skills/next/SKILL.md 第 1 节），和主文件一起算：依赖它的照样算没满足，状态页照样列出。
        # 搁置文件里的项一律不算可领（/next 开工不读它）。它有内容却认不出带状态列的表时，两份都找不到的依赖编号不再按已完成算；
        # 只有表头（最后一项恢复了）是正常的，空文件当作没有。
        $shelfFile = Get-ShelfPath $queueFile
        $shelfBroken = $false
        $shelf = @()
        if ((Test-Path -LiteralPath $shelfFile) -and "$(Get-Content -LiteralPath $shelfFile -Raw -Encoding UTF8)".Trim()) {
            $shelfLeaf = Split-Path $shelfFile -Leaf
            $script:queueTableSeen = $false
            $shelf = @(Read-Queue $shelfFile)
            if (-not $script:queueTableSeen) { $shelfBroken = $true; $r.Problems.Add("$shelfLeaf 里没有带「状态」列的表：依赖编号两份都找不到的项先不算可领") }
            $notShelved = @($shelf | Where-Object State -ne '搁置')
            if ($notShelved) { $r.Problems.Add("$shelfLeaf 里有不是搁置的项：$(($notShelved | ForEach-Object { if ($_.Id) { Format-Id $_.Id } else { Short $_.Goal 12 } }) -join '、')；移回 $queueRel（在那里不算可领）") }
            $mainIds = @($items | ForEach-Object { ($_.Id -replace '^#', '').Trim() } | Where-Object { $_ })
            $dup = @($shelf | ForEach-Object { ($_.Id -replace '^#', '').Trim() } | Where-Object { $_ -and $mainIds -contains $_ } | Select-Object -Unique)
            if ($dup) { $r.Problems.Add("$queueRel 和 $shelfLeaf 里都有的编号：$(($dup | ForEach-Object { "#$_" }) -join '、')；搬行时删掉其中一份") }
            $items += $shelf
        }
        $counts = [ordered]@{}
        foreach ($s in $states + '其他') { $counts[$s] = @($items | Where-Object State -eq $s).Count }
        $r.Queue = $counts
        # 待用户只写现在要定的（skills/next/SKILL.md 第 5 节）。状态格很长的多半是过程记录；短的里写着先不做、在等别处的，多半该是搁置。
        foreach ($w in @($items | Where-Object State -eq '待用户')) {
            $hint = if ($w.Detail.Length -gt 300) { '过程记录' } elseif ($w.Detail.Trim() -match $shelvedWords -or "$($w.Note)" -match $noteWords) { '像搁置' } else { '' }
            $w | Add-Member -NotePropertyName Hint -NotePropertyValue $hint
        }
        $r.Waiting = @($items | Where-Object State -eq '待用户')
        $label = { if ($_.Id) { Format-Id $_.Id } else { Short $_.Goal 20 } }
        $shelvedLike = @($r.Waiting | Where-Object Hint -eq '像搁置')
        if ($shelvedLike) { $r.Problems.Add("待用户项像是搁置（写着先不做或在等别处）：$(($shelvedLike | ForEach-Object $label) -join '、')；用户说过先不做的改成 搁置（<恢复条件>）") }
        $logLike = @($r.Waiting | Where-Object Hint -eq '过程记录')
        if ($logLike) { $r.Problems.Add("待用户项的状态格写成了过程记录（超过 300 字）：$(($logLike | ForEach-Object $label) -join '、')；只留现在要用户定的，过程写进提交正文") }
        $r.Pending = @($items | Where-Object State -eq '待放行')
        $r.Doing = @($items | Where-Object State -eq '在做')
        $other = @($items | Where-Object State -eq '其他')
        $r.Other = $other
        if ($other) { $r.Problems.Add("队列里状态认不出的项：" + (($other | ForEach-Object { "$(if ($_.Id) { (Format-Id $_.Id) } else { Short $_.Goal 12 })（$(Short $_.Detail 20)）" }) -join '、')) }
        # 完成的项没人再回，不用编号；其余的没有编号就没法用 /next #n 点名。
        $noId = @($items | Where-Object { -not (Format-Id $_.Id) -and $_.State -ne '完成' })
        if ($noId) { $r.Problems.Add("队列里没有编号的项：" + (($noId | ForEach-Object { if ($_.Goal) { Short $_.Goal 20 } else { '未命名' } }) -join '、')) }
        $done = @($items | Where-Object State -eq '完成' | ForEach-Object { $_.Id -replace '^#', '' })
        $open = @($items | Where-Object State -ne '完成' | ForEach-Object { $_.Id -replace '^#', '' })
        $known = @($done) + @($open)
        $availItems = @($items | Where-Object { $_.State -eq '待做' } | Where-Object { $it = $_; -not @($shelf | Where-Object { [object]::ReferenceEquals($_, $it) }).Count } | Where-Object {
            $d = ($_.Deps -replace '\*', '').Trim()
            if ($d -match '^(无|-|—|)$') { return $true }
            $nums = @([regex]::Matches($d, '\d+') | ForEach-Object Value)
            if ($d -notmatch '^[#\d\s,，、]+$' -or -not $nums) { return $false }
            if ($shelfBroken -and @($nums | Where-Object { $known -notcontains $_ }).Count) { return $false }
            -not @($nums | Where-Object { $open -contains $_ }).Count
        })
        $availItems = @($availItems | Where-Object { $t = [regex]::Match("$($_.Goal)", $tagRe); -not ($t.Success -and $stoppedDirs -contains $t.Groups[2].Value) })
        $r.Available = $availItems.Count
        $r.Items = @(foreach ($it in $items) {
            [pscustomobject]@{ Id = $it.Id; Goal = $it.Goal; State = $it.State; Detail = $it.Detail; Hint = $it.Hint; Deps = $it.Deps
                               Claimable = [bool]@($availItems | Where-Object { [object]::ReferenceEquals($_, $it) }).Count }
        })
        $r.Next = @($availItems | Select-Object -First 3)
        $r.Recent = @($items | Where-Object State -eq '完成' | Select-Object -Last 3)
    } else { $r.Problems.Add("没有队列文件 $queueRel") }
    if ($r.Direction) {
        # 方向没人看：推进中的项目没有 docs/benchmark.json，也没写不登记的理由（notApplicable）。排进队列了也照样标，登记了才算有人看（direction.md 第 4 节）。
        if ($p.status -eq '推进中' -and $r.Direction.Benchmark -eq 'none') {
            $r.Unwatched = $true
            $r.Problems.Add('方向没人看：没有 docs/benchmark.json，也没写不登记的理由；/next 开场先做 登记基准')
        }
        $openGoals = @($items | Where-Object { $_.State -notin '完成', '搁置' } | ForEach-Object { "$($_.Goal)" })
        foreach ($a in @($r.Direction.Actions)) {
            if ($p.status -ne '推进中' -and $a -notmatch '^改好') { continue }
            # 已经排进队列的不再催
            if ($a -match '加一项 (登记基准|流程图)') { $what = $Matches[1]; if (@($openGoals | Where-Object { $_ -match $what }).Count) { continue } }
            $r.Problems.Add($a)
        }
        $dirs = @($r.Direction.Directions)
        foreach ($goal in $openGoals) {
            $t = [regex]::Match($goal, $tagRe)
            if (-not $t.Success) { continue }
            $name = $t.Groups[2].Value
            $state = @($dirs | Where-Object { $_.Name -eq $name } | ForEach-Object { $_.State })
            $ok = if ($t.Groups[1].Value) { $state -contains '原型' -or $state -contains '进行中' } else { $state -contains '进行中' }
            if (-not $ok) { $r.Problems.Add("队列里有 $($t.Value.Trim()) 的项，docs/benchmark.json 的方向 $name 却不是$(if ($t.Groups[1].Value) { '原型或' })进行中：用户定了才排（direction.md 第 2 节）") }
        }
    }
    $verifyFile = Join-Path $path '.agents/verify-last.json'
    if (Test-Path -LiteralPath $verifyFile) {
        try { $r.VerifySeconds = [int](Get-Content -LiteralPath $verifyFile -Raw -Encoding UTF8 | ConvertFrom-Json).seconds } catch { $r.VerifySeconds = $null }
        $limit = $SlowVerifyMinutes
        $agentsFile = Join-Path $path 'AGENTS.md'
        if (Test-Path -LiteralPath $agentsFile) {
            $lm = [regex]::Match((Get-Content -LiteralPath $agentsFile -Raw -Encoding UTF8), '快检提速阈值\**[：:]\s*\**\s*(\d+)\s*分钟')
            if ($lm.Success) { $limit = [int]$lm.Groups[1].Value }
        }
        $speedUp = @($items | Where-Object { $_.State -ne '完成' -and "$($_.Goal)" -match '快检提速' })
        if ($p.status -eq '推进中' -and $r.VerifySeconds -gt $limit * 60 -and -not $speedUp) {
            $r.Problems.Add("快检最近一次用了 $([math]::Round($r.VerifySeconds / 60)) 分钟，超过 $limit 分钟，队列里没有快检提速的项：下次 /next 开场自动加（skills/next/SKILL.md 第 1 节）")
        }
    }
    $r.Goals = @(foreach ($g in @($p.goals | Where-Object { $_ })) {
        $ids = @($g.items | Where-Object { $_ } | ForEach-Object { "$_" -replace '^#', '' })
        $byItems = $ids.Count -and $done -and -not @($ids | Where-Object { $done -notcontains $_ }).Count
        [pscustomobject]@{ Text = $g.text; Done = [bool]($g.done -eq $true -or $byItems) }
    })

    $digestDir = Join-Path $path '.agents/digest'
    if (Test-Path -LiteralPath $digestDir) {
        $latest = Get-ChildItem -LiteralPath $digestDir -Filter '*.md' -File | Sort-Object Name | Select-Object -Last 1
        if ($latest) {
            $keep = @(Get-Content -LiteralPath $latest.FullName -Encoding UTF8 | Where-Object { $_ -match '^(北极星|返工|建议)[：:]' })
            $r.Digest = [pscustomobject]@{ Date = $latest.BaseName; Lines = $keep }
        }
    }

    $changes = @(git -C $path status --porcelain --untracked-files=all)
    $r.Untracked = @($changes | Where-Object { $_.StartsWith('??') }).Count
    $r.Uncommitted = $changes.Count - $r.Untracked
    $merged = @(git -C $path branch --merged $head --format='%(refname:short)' | Where-Object { $_ -and $_ -ne $r.Trunk })
    $r.BranchesMerged = $merged.Count
    $trees = [Collections.Generic.List[object]]::new()
    foreach ($line in git -C $path worktree list --porcelain) {
        if ($line -like 'worktree *') { $trees.Add([ordered]@{ Head = $null; Branch = $null; Detached = $false; Prunable = $false }) }
        elseif ($line -like 'HEAD *') { $trees[-1].Head = $line.Substring(5) }
        elseif ($line -like 'branch refs/heads/*') { $trees[-1].Branch = $line.Substring(18) }
        elseif ($line -eq 'detached') { $trees[-1].Detached = $true }
        elseif ($line -like 'prunable*') { $trees[-1].Prunable = $true }
    }
    $extra = @($trees | Select-Object -Skip 1)
    $r.Worktrees = $extra.Count
    $r.WorktreesMerged = @($extra | Where-Object { $_.Branch -and $merged -contains $_.Branch }).Count
    $r.WorktreesDetached = @($extra | Where-Object { $_.Detached }).Count
    $r.WorktreesMissing = @($extra | Where-Object { $_.Prunable }).Count
    # 分离头的 head 已在主干里的也算可以清（审查 worktree 多半是这种）。不逐个看干不干净：几十个 worktree 跑 status 太慢，cleanup.ps1 删的时候会看。
    $mergedTrees = $r.WorktreesMerged + @($extra | Where-Object { $_.Detached -and -not $_.Prunable -and $_.Head } | Where-Object { git -C $path merge-base --is-ancestor $_.Head $head 2>$null; -not $LASTEXITCODE }).Count
    if ($r.BranchesMerged -gt $CleanupOver -or $mergedTrees -gt $CleanupOver) { $r.Problems.Add("已合进主干还没删：分支 $($r.BranchesMerged) 个、worktree $mergedTrees 个，超过 $CleanupOver 个：在项目里运行 cleanup.ps1（land.md 第 6 节）") }

    $times = @(git -C $path for-each-ref refs/heads --format='%(committerdate:iso-strict)' | Where-Object { $_ } | ForEach-Object { [datetimeoffset]::Parse($_).LocalDateTime })
    $runs = Join-Path $path '.agents/runs'
    if (Test-Path -LiteralPath $runs) { $times += @(Get-ChildItem -LiteralPath $runs -Recurse -Depth 1 -File -ErrorAction SilentlyContinue | ForEach-Object LastWriteTime) }
    if ($times) {
        $last = ($times | Measure-Object -Maximum).Maximum
        $r.LastActivity = $last.ToString('yyyy-MM-dd HH:mm')
        $r.IdleMinutes = [int][math]::Floor(((Get-Date) - $last).TotalMinutes)
        if ($p.status -eq '推进中' -and $r.Queue -and $r.Queue['在做'] -and $r.IdleMinutes -ge $StaleMinutes) {
            $r.Problems.Add("可能停滞：在做 $($r.Queue['在做']) 项，已 $(Format-Idle $r.IdleMinutes)没有动静")
        }
        # 有活没人做：可领的项摆着、没有会话在做。待用户项再多也照样提示，用户可能以为项目在等自己，其实还有别的能做。
        if ($p.status -eq '推进中' -and $r.Available -and -not ($r.Queue -and $r.Queue['在做']) -and $r.IdleMinutes -ge $IdleHours * 60) {
            $r.Problems.Add("有活没人做：$($r.Available) 项可领，没有在做的，已 $(Format-Idle $r.IdleMinutes)没有动静；在这个项目发 /next")
        }
    }
    # 本周目标没动：GoalHours 小时内有新提交，本周目标挂的、还没完成的项却这么久没有提到它的提交（"#<编号>"，认领、合并、队列改状态都带编号）。
    # 进展只认提交：在做的项写着在做，却一直没提交，也算没动。起点是最近一次提到它们的提交，和周会定目标后的 -Mark 时间，取较晚者；
    # 两样都没有（目标刚定、还没 -Mark）不知道从哪天算，不提示。只看队列和搁置文件里还在、没完成的编号：找不到的按已完成算（完成的项会删），同依赖。
    $goalIds = @($p.goals | Where-Object { $_ -and $_.done -ne $true } | ForEach-Object { @($_.items) } | Where-Object { $_ } | ForEach-Object { "$_" -replace '^#', '' } | Where-Object { $_ -match '^\d+$' -and $open -contains $_ } | Select-Object -Unique)
    $lastCommit = @(git -C $path for-each-ref refs/heads --format='%(committerdate:unix)' | Where-Object { $_ } | ForEach-Object { [long]$_ } | Measure-Object -Maximum).Maximum
    if ($p.status -eq '推进中' -and $goalIds -and $lastCommit) {
        $nowUnix = [DateTimeOffset]::Now.ToUnixTimeSeconds()
        if ($nowUnix - $lastCommit -lt $GoalHours * 3600) {
            $goalRe = '#(' + ($goalIds -join '|') + ')([^0-9]|$)'
            $lastGoal = git -C $path log --branches -1 -E -i "--grep=$goalRe" --format=%ct 2>$null | Select-Object -First 1
            $from = @(if ($lastGoal) { [long]$lastGoal }
                      $mt = [datetime]::MinValue
                      if ($mark -and [datetime]::TryParseExact("$($mark.time)", 'yyyy-MM-dd HH:mm', $null, 'None', [ref]$mt)) { ([DateTimeOffset]$mt).ToUnixTimeSeconds() }) | Measure-Object -Maximum
            if ($from.Count) {
                $since = [long]$from.Maximum
                $goalAge = [int][math]::Floor(($nowUnix - $since) / 60)
                if ($goalAge -ge $GoalHours * 60) {
                    $r.GoalStalled = [pscustomobject]@{ Ids = $goalIds; Minutes = $goalAge; Since = [DateTimeOffset]::FromUnixTimeSeconds($since).LocalDateTime.ToString('yyyy-MM-dd HH:mm') }
                    $r.Problems.Add("本周目标没动：有新提交，本周目标挂的 $(($goalIds | ForEach-Object { "#$_" }) -join '、') 已 $(Format-Idle $goalAge)没有提交提到它们")
                }
            }
        }
    }
    # 死掉的运行：dispatch.ps1 的运行没有 exit.json，记下的进程也不在了（或进程号已被别的进程复用），多半被杀了。只看 7 天内开始的，更早的没人再管；
    # 同一分支后来又派过的（重派、续做、复审）算已接上，不报。
    if (Test-Path -LiteralPath $runs) {
        $metas = @(foreach ($d in Get-ChildItem -LiteralPath $runs -Directory -ErrorAction SilentlyContinue) {
            $mf = Join-Path $d.FullName 'meta.json'
            if (-not (Test-Path -LiteralPath $mf)) { continue }
            try { $meta = Get-Content -LiteralPath $mf -Raw -Encoding UTF8 | ConvertFrom-Json; $started = [datetime]$meta.Started } catch { continue }
            [pscustomobject]@{ Name = $d.Name; Meta = $meta; Started = $started; Exited = Test-Path -LiteralPath (Join-Path $d.FullName 'exit.json') }
        })
        $r.DeadRuns = @(foreach ($x in $metas) {
            if ($x.Exited -or $x.Started -lt (Get-Date).AddDays(-7)) { continue }
            if ($x.Meta.Branch -and @($metas | Where-Object { $_.Meta.Branch -eq $x.Meta.Branch -and $_.Started -gt $x.Started }).Count) { continue }
            $proc = if ($x.Meta.Pid) { Get-Process -Id $x.Meta.Pid -ErrorAction SilentlyContinue }
            $alive = $proc -and $(try { $gap = ($x.Started - $proc.StartTime).TotalMinutes; $gap -ge -1 -and $gap -le 5 } catch { $true })
            if (-not $alive) { $x.Name }
        })
        if ($r.DeadRuns) { $r.Problems.Add("派出去的运行死了（没有退出记录，进程也不在）：$(($r.DeadRuns | Select-Object -First 5) -join '、')$(if ($r.DeadRuns.Count -gt 5) { " 等 $($r.DeadRuns.Count) 个" })；用 dispatch.ps1 -List 看") }
    }
    [pscustomobject]$r
}

$selected = if ($Project) { @($projects | Where-Object { $Project -contains $_.name }) } else { @($projects | Where-Object { $_.status -ne '暂停' }) }
$selected = @($selected | Sort-Object { if ($statusOrder.ContainsKey([string]$_.status)) { $statusOrder[[string]$_.status] } else { 0 } }, { if ($null -ne $_.priority) { [int]$_.priority } else { 99 } })
$results = @(foreach ($p in $selected) { Get-ProjectStatus $p })
$paused = @($projects | Where-Object { $_.status -eq '暂停' -and $Project -notcontains $_.name } | ForEach-Object {
    if ($_.path -and (Test-Path -LiteralPath $_.path)) { $_.name } else { "$($_.name)（路径不存在）" } })

if ($Mark) {
    $time = Get-Date -Format 'yyyy-MM-dd HH:mm'
    foreach ($r in $results) { if ($r.Head) { $marks[$r.Name] = [pscustomobject]@{ head = $r.Head; time = $time } } }
    $null = New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($marksFile))
    $marks | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $marksFile -Encoding utf8NoBOM
}

if ($Json) {
    [pscustomobject]@{ Generated = (Get-Date -Format 'yyyy-MM-dd HH:mm'); Config = $Config; Projects = $results; Paused = $paused } | ConvertTo-Json -Depth 12
    exit 0
}

$waiting = @($results | ForEach-Object { $_.Waiting })
$byTier = ($waiting | Group-Object { if ($_.Tier) { $_.Tier } else { '未写档' } } | ForEach-Object { "$($_.Name) $($_.Count)" }) -join ' · '
$count = { param($s) @($projects | Where-Object status -eq $s).Count }
$out = [Collections.Generic.List[string]]::new()
$out.Add("# 项目状态 $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
$out.Add("推进中 $(& $count '推进中') · 维护 $(& $count '维护') · 暂停 $(& $count '暂停')；待用户合计 $($waiting.Count)$(if ($byTier) { "（$byTier）" })")
foreach ($r in $results) {
    $brief = $r.Status -eq '维护' -and -not $All -and -not $Project
    $head = @($r.Name, $r.Status)
    if ($null -ne $r.Priority) { $head += "优先级 $($r.Priority)" }
    if ($r.Trust) { $head += $r.Trust }
    if ($r.DependsOn) { $head += "依赖 $($r.DependsOn -join '、')" }
    $out.Add('')
    $out.Add("## $($head -join ' · ')")
    if ($r.Head) {
        $out.Add("主干 $($r.Trunk) @ $($r.Head.Substring(0, 9))（$($r.HeadDate)）；新提交 $($r.NewCount)（$($r.NewSince)）$(if ($null -ne $r.Unreviewed) { "；未复盘 $($r.Unreviewed)" })")
        if (-not $brief) {
            foreach ($c in $r.NewCommits | Select-Object -First 8) { $out.Add("  $(Short $c 100)") }
            if ($r.NewCount -gt 8) { $out.Add("  …另 $($r.NewCount - 8) 条") }
        }
    }
    if ($r.Queue) { $out.Add('队列：' + (($r.Queue.GetEnumerator() | Where-Object { $_.Key -notin '其他', '搁置', '待放行' -or $_.Value } | ForEach-Object { "$($_.Key) $($_.Value)" }) -join ' · ') + "；可领 $($r.Available)") }
    if ($r.Goals) { $out.Add("本周目标 $(@($r.Goals | Where-Object Done).Count)/$($r.Goals.Count)：" + (($r.Goals | ForEach-Object { "$(if ($_.Done) { '✓' } else { '○' }) $(Short $_.Text 40)" }) -join '；')) }
    if ($r.LastActivity) { $out.Add("最后活动 $($r.LastActivity)（$(Format-Idle $r.IdleMinutes)前）") }
    if ($r.Direction -and $r.Direction.Benchmark -eq 'ok' -and -not $brief) {
        $d = $r.Direction
        $trend = @($d.Trend | Select-Object -Last 6 | ForEach-Object { $_.Gap }) -join ' → '
        $out.Add("基准：$($d.Baseline.Model)（$($d.Baseline.Date)）；差距 $(if ($null -ne $d.Gap) { "$($d.Gap)（$($d.LastRun)）" } else { '还没量' })$(if ($trend) { "；按周 $trend" })")
    }
    foreach ($c in @($r.Direction.Cards | Where-Object { $_ })) { $out.Add("  决定卡 $(Short $c.Title 60)：$($c.File)") }
    foreach ($w in $r.Waiting) { $out.Add("  待用户$(if ($w.Id) { ' ' + (Format-Id $w.Id 40) })$(if ($w.Tier) { " [$($w.Tier)]" }) $(Short $w.Goal 60)$(if ($w.Detail) { "：$(Short $w.Detail 80)" })") }
    foreach ($w in $r.Pending) { $out.Add("  待放行$(if ($w.Id) { ' ' + (Format-Id $w.Id 40) }) $(Short $w.Goal 60)$(if ($w.Detail) { "：$(Short $w.Detail 80)" })") }
    if ($r.Digest -and -not $brief) {
        $out.Add("最近摘要 $($r.Digest.Date)")
        foreach ($l in $r.Digest.Lines) { $out.Add("  $(Short $l 120)") }
    }
    if ($null -ne $r.Worktrees -and -not $brief) {
        $out.Add("工作区：未提交改动 $($r.Uncommitted) · 未跟踪 $($r.Untracked) · worktree $($r.Worktrees)（分支已合进主干 $($r.WorktreesMerged) · 分离头 $($r.WorktreesDetached) · 目录已不在 $($r.WorktreesMissing)）· 已合进主干的分支 $($r.BranchesMerged)")
    }
    foreach ($l in $r.Lessons) { $out.Add("  教训 Seen $(if ($null -ne $l.Seen) { $l.Seen } else { '?' })：$(Short $l.Title 80)") }
    foreach ($x in $r.Problems) { $out.Add("提示：$x") }
}
if ($paused) { $out.Add(''); $out.Add('暂停：' + ($paused -join '、')) }
$out -join [Environment]::NewLine
