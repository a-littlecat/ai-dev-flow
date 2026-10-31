[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Since,
    [string[]]$Project,
    [switch]$All,
    [switch]$Lessons,
    [switch]$Mark,
    [switch]$Json
)
# 收状态：按总览仓库的项目清单 projects.json，列出每个项目的事实——主干新提交、未复盘的提交、队列各状态的项数和待用户项、
# 最近一份每日摘要、worktree 和分支、未提交改动。只收事实，判断和汇报由总览做（格式见 ai-dev-flow modules/portfolio.md）。
# 在总览仓库里任意目录运行，或用 -Config 指定清单（默认 <仓库>/projects.json）。
#   默认      推进中的项目全量；维护中的只列提交数、队列和待用户项；暂停的只列名字
#   -Since    新提交从这个时间算（git 的写法：'24 hours ago'、'2026-10-30'）；不给就从上次 -Mark 记下的位置算，没有记录按 24 小时
#   -Project  只看这几个（按名字，多个用逗号隔开，暂停的也看）
#   -All      维护中的也全量
#   -Lessons  附上各项目 LESSONS.md 每条教训的 Seen 和标题（合并跨项目教训用）
#   -Mark     把各项目当前的主干位置记为下次的起点（写每日摘要时用），记在 <清单所在目录>/.agents/status-marks.json
#   -Json     输出 JSON
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
$Config = [IO.Path]::GetFullPath($Config)
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

$states = '待做', '在做', '待验证', '待用户', '完成'
$statusOrder = @{ '推进中' = 0; '维护' = 1; '暂停' = 2 }

function Short([string]$s, [int]$n) {
    $s = ($s -replace '\s+', ' ').Trim()
    if ($s.Length -gt $n) { $s.Substring(0, $n - 1) + '…' } else { $s }
}

# 队列：Markdown 表格，表头里有"状态"列；状态格以 待做 / 在做 / 待验证 / 待用户 / 完成 开头，后面可以跟括号说明。
function Read-Queue([string]$file) {
    $cols = $null
    foreach ($line in Get-Content -LiteralPath $file -Encoding UTF8) {
        if ($line -notmatch '\|') { $cols = $null; continue }
        $cells = @(($line.Trim() -replace '^\||\|$', '') -split '(?<!\\)\|' | ForEach-Object { $_.Trim() })
        if (-not $cols) {
            if ($cells -contains '状态') { $cols = $cells }
            continue
        }
        if ($cells[0] -match '^:?-+:?$') { continue }
        $get = { param($name) $i = [array]::IndexOf($cols, $name); if ($i -ge 0 -and $i -lt $cells.Count) { $cells[$i] } else { '' } }
        $raw = ((& $get '状态') -replace '\*', '').Trim()
        $state = $states | Where-Object { $raw.StartsWith($_, [StringComparison]::Ordinal) } | Select-Object -First 1
        [pscustomobject]@{
            Id     = & $get '#'
            Goal   = & $get '目标'
            Tier   = (& $get '档') -replace '\*', ''
            State  = if ($state) { $state } else { '其他' }
            Detail = if ($state) { $raw.Substring($state.Length).Trim() -replace '^[（(]', '' -replace '[）)]$', '' } else { $raw }
        }
    }
}

function Get-ProjectStatus($p) {
    $r = [ordered]@{
        Name = $p.name; Status = $p.status; Priority = $p.priority; Session = $p.session
        DependsOn = @($p.dependsOn | Where-Object { $_ })
        Trust = $null; Trunk = $null; Head = $null; HeadDate = $null
        NewSince = $null; NewCount = 0; NewCommits = @(); Unreviewed = $null
        Queue = $null; Waiting = @(); Digest = $null
        Uncommitted = $null; Untracked = $null; Worktrees = $null; WorktreesMerged = $null; WorktreesDetached = $null; WorktreesMissing = $null; BranchesMerged = $null
        Lessons = @()
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
            $count = git -C $path rev-list --count "$($m.Groups[1].Value)..$head" 2>$null
            if ($LASTEXITCODE) { $r.Problems.Add("LESSONS.md 的 reviewed-through 不是有效提交：$($m.Groups[1].Value)") } else { $r.Unreviewed = [int]$count }
        }
        if ($Lessons) {
            $r.Lessons = @(foreach ($sec in ($text -split '(?m)^(?=##\s)') | Where-Object { $_ -match '^##\s' }) {
                $seen = [regex]::Match($sec, 'Seen[：:]\s*(\d+)')
                [pscustomobject]@{ Seen = if ($seen.Success) { [int]$seen.Groups[1].Value } else { $null }; Title = (($sec -split '\r?\n')[0] -replace '^##\s+', '').Trim() }
            })
        }
    }

    $queueRel = if ($p.queue) { $p.queue } else { 'docs/queue.md' }
    $queueFile = Join-Path $path $queueRel
    if (Test-Path -LiteralPath $queueFile) {
        $items = @(Read-Queue $queueFile)
        if (-not $items.Count) { $r.Problems.Add("$queueRel 里没有带「状态」列的表") }
        $counts = [ordered]@{}
        foreach ($s in $states + '其他') { $counts[$s] = @($items | Where-Object State -eq $s).Count }
        $r.Queue = $counts
        $r.Waiting = @($items | Where-Object State -eq '待用户')
        $other = @($items | Where-Object State -eq '其他')
        if ($other) { $r.Problems.Add("队列里状态认不出的项：" + (($other | ForEach-Object { "#$($_.Id)（$(Short $_.Detail 20)）" }) -join '、')) }
    } else { $r.Problems.Add("没有队列文件 $queueRel") }

    $digestDir = Join-Path $path '.agents/digest'
    if (Test-Path -LiteralPath $digestDir) {
        $latest = Get-ChildItem -LiteralPath $digestDir -Filter '*.md' -File | Sort-Object Name | Select-Object -Last 1
        if ($latest) {
            $keep = @(Get-Content -LiteralPath $latest.FullName -Encoding UTF8 | Where-Object { $_ -match '^(北极星|返工|建议)[：:]' })
            $r.Digest = [pscustomobject]@{ Date = $latest.BaseName; Lines = $keep }
        }
    }

    $changes = @(git -C $path status --porcelain)
    $r.Untracked = @($changes | Where-Object { $_.StartsWith('??') }).Count
    $r.Uncommitted = $changes.Count - $r.Untracked
    $merged = @(git -C $path branch --merged $head --format='%(refname:short)' | Where-Object { $_ -and $_ -ne $r.Trunk })
    $r.BranchesMerged = $merged.Count
    $trees = [Collections.Generic.List[object]]::new()
    foreach ($line in git -C $path worktree list --porcelain) {
        if ($line -like 'worktree *') { $trees.Add([ordered]@{ Branch = $null; Detached = $false; Prunable = $false }) }
        elseif ($line -like 'branch refs/heads/*') { $trees[-1].Branch = $line.Substring(18) }
        elseif ($line -eq 'detached') { $trees[-1].Detached = $true }
        elseif ($line -like 'prunable*') { $trees[-1].Prunable = $true }
    }
    $extra = @($trees | Select-Object -Skip 1)
    $r.Worktrees = $extra.Count
    $r.WorktreesMerged = @($extra | Where-Object { $_.Branch -and $merged -contains $_.Branch }).Count
    $r.WorktreesDetached = @($extra | Where-Object { $_.Detached }).Count
    $r.WorktreesMissing = @($extra | Where-Object { $_.Prunable }).Count
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
    [pscustomobject]@{ Generated = (Get-Date -Format 'yyyy-MM-dd HH:mm'); Config = $Config; Projects = $results; Paused = $paused } | ConvertTo-Json -Depth 6
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
    if ($r.Session -and -not $brief) { $head += "主会话「$($r.Session)」" }
    $out.Add('')
    $out.Add("## $($head -join ' · ')")
    if ($r.Head) {
        $out.Add("主干 $($r.Trunk) @ $($r.Head.Substring(0, 9))（$($r.HeadDate)）；新提交 $($r.NewCount)（$($r.NewSince)）$(if ($null -ne $r.Unreviewed) { "；未复盘 $($r.Unreviewed)" })")
        if (-not $brief) {
            foreach ($c in $r.NewCommits | Select-Object -First 8) { $out.Add("  $(Short $c 100)") }
            if ($r.NewCount -gt 8) { $out.Add("  …另 $($r.NewCount - 8) 条") }
        }
    }
    if ($r.Queue) { $out.Add('队列：' + (($r.Queue.GetEnumerator() | Where-Object { $_.Key -ne '其他' -or $_.Value } | ForEach-Object { "$($_.Key) $($_.Value)" }) -join ' · ')) }
    foreach ($w in $r.Waiting) { $out.Add("  待用户 #$($w.Id)$(if ($w.Tier) { " [$($w.Tier)]" }) $(Short $w.Goal 60)$(if ($w.Detail) { "：$(Short $w.Detail 80)" })") }
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
