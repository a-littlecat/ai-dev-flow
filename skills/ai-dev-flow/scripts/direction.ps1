[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Repo = '.',
    [switch]$Json,
    [string]$Today
)
# 方向检查（ai-dev-flow modules/direction.md）：读一个项目的 docs/benchmark.json、docs/decisions/*.md、docs/flow.html（或 docs/flow.md），判断要不要停、要不要补。只读。
#   pwsh -NoProfile -File direction.ps1 [-Repo <项目>] [-Json]
# 退出码：0 没有要处理的；3 有要处理的（Actions 逐条列出，/next 开场按它做）；1 脚本自己出错。
#   -Today   按这一天算（yyyy-MM-dd，测试用），默认今天
# 判定（direction.md 第 5 节）。差距 gap：0 是和基准一样，大于 0 是比基准差，小于等于 0 是比过了；缩小就是变小。
#   每周取最后一次测量。"进行中"的方向只看 started 和 decided（用户上次定的日期）之后的测量，"比过了"也只认这之后、基准日期之后的：
#   最近一周 gap > 0，且最近三个周点依次没变小 → 连续 2 周没缩小，停；14 天没量 → 停（不量就算没缩小）。
#   预算：过了 budgetDays 天，或 spentQuota 到了 budgetQuota，最新 gap 还不是 <= 0 → 停。"原型"的方向只看预算，有待定决定卡（卡的开头写着"方向：<方向名>"）就算在等用户，不停。"结束"的不看。
#   没有未结束的方向时按项目整体看，只看顶层 decided 和已结束方向的 decided 之后的测量，有问题只报，没有项要停。
# 写错的（日期、数字、图的路径）进 Problems，不猜；图只认仓库里、真实存在的文件。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8

$repoFull = (Resolve-Path -LiteralPath $Repo).ProviderPath.TrimEnd('\', '/')
$now = if ($Today) { [datetime]::ParseExact($Today, 'yyyy-MM-dd', $null) } else { (Get-Date).Date }
$problems = [Collections.Generic.List[string]]::new()
$actions = [Collections.Generic.List[string]]::new()

function Read-Date($v) {
    if ($v -is [datetime]) { return $v.Date }
    if ($v -is [datetimeoffset]) { return $v.Date }
    $d = [datetime]::MinValue
    if ($v -is [string] -and [datetime]::TryParseExact($v, 'yyyy-MM-dd', $null, 'None', [ref]$d)) { return $d }
    $null
}
function Read-Number($v) { if ($v -is [int] -or $v -is [long] -or $v -is [double] -or $v -is [decimal]) { [double]$v } else { $null } }
function Date-Text($d) { if ($d) { $d.ToString('yyyy-MM-dd') } }

# 主检出的根目录。.agents/ 不进 worktree，在 worktree 里跑时那里的图要回主检出找。
function Get-MainRoot {
    $top = git -C $repoFull rev-parse --path-format=absolute --show-toplevel 2>$null
    $dir = git -C $repoFull rev-parse --path-format=absolute --git-dir 2>$null
    $common = git -C $repoFull rev-parse --path-format=absolute --git-common-dir 2>$null
    $global:LASTEXITCODE = 0
    # 只认普通 worktree：项目就是这个工作区的根（不是大仓库里的子目录），主检出是 <根>/.git（不是 bare 仓库）。其他情况不回退，报图不存在。
    if (-not $top -or -not $common -or $dir -eq $common -or (Split-Path $common -Leaf) -ne '.git') { return }
    if ([IO.Path]::GetFullPath($top).TrimEnd('\', '/') -ne $repoFull) { return }
    Split-Path ([IO.Path]::GetFullPath($common)) -Parent
}

# 图：相对 $base 的路径，要在仓库里、文件存在。返回 file: 地址；不行返回 $null 并记问题。
function Get-ImageUrl([string]$path, [string]$base, [string]$where) {
    $path = $path.Trim().Trim('<', '>')
    if ($path -match '^[a-zA-Z][a-zA-Z0-9+.-]*:|^[\\/]') { $problems.Add("$where 的图不是仓库里的相对路径：$path"); return $null }
    $full = [IO.Path]::GetFullPath((Join-Path $base $path))
    if (-not $full.StartsWith($repoFull + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { $problems.Add("$where 的图跑到仓库外了：$path"); return $null }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        $main = Get-MainRoot
        $other = if ($main -and $main.TrimEnd('\', '/') -ne $repoFull) { Join-Path $main ([IO.Path]::GetRelativePath($repoFull, $full)) }
        if ($other -and (Test-Path -LiteralPath $other -PathType Leaf)) { $full = [IO.Path]::GetFullPath($other) }
        else { $problems.Add("$where 的图不存在：$path"); return $null }
    }
    ([Uri]$full).AbsoluteUri
}

$result = [ordered]@{
    Benchmark = 'none'; NotApplicable = $null; NorthStar = $null; Baseline = $null
    Gap = $null; LastRun = $null; ImageUrl = $null; Note = $null; Trend = @()
    Directions = @(); Stopped = @(); Cards = @(); FlowUrl = $null; Actions = @(); Problems = @()
}

# 有待定决定卡的方向。卡的完整解析在后面，这里只要开头 10 行。
$cardDir = Join-Path $repoFull 'docs/decisions'
$waitingDirs = @(if (Test-Path -LiteralPath $cardDir) { foreach ($f in Get-ChildItem -LiteralPath $cardDir -Filter '*.md' -File) {
    $top = @(Get-Content -LiteralPath $f.FullName -Encoding UTF8 -TotalCount 10)
    if (@($top | Where-Object { $_ -match '^\s*状态\s*[：:]\s*待定' }).Count) {
        foreach ($l in $top) { if ($l -match '^\s*方向\s*[：:]\s*(.+?)\s*$') { $Matches[1] } }
    }
} })

$file = Join-Path $repoFull 'docs/benchmark.json'
$b = $null
if (Test-Path -LiteralPath $file) {
    try { $b = Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop }
    catch { $result.Benchmark = 'bad'; $problems.Add("docs/benchmark.json 读不了：$($_.Exception.Message)") }
    if ($null -ne $b -and $b -isnot [pscustomobject]) { $b = $null; $result.Benchmark = 'bad'; $problems.Add('docs/benchmark.json 顶层应是一个对象') }
}

if ($b -and $null -ne $b.notApplicable -and ($b.notApplicable -isnot [string] -or -not $b.notApplicable.Trim())) { $problems.Add('notApplicable 要写一句原因（字符串）') }
if ($b -and $b.notApplicable -is [string] -and $b.notApplicable.Trim()) {
    $result.Benchmark = 'notApplicable'
    $result.NotApplicable = "$($b.notApplicable)".Trim()
} elseif ($b) {
    $result.Benchmark = 'ok'
    $result.NorthStar = $b.northStar
    if (-not "$($b.northStar)".Trim()) { $problems.Add('northStar 没写（口径：最终交付物和基准的差距怎么量）') }
    $bl = $b.baseline
    $blDate = if ($bl) { Read-Date $bl.date }
    if (-not $bl -or -not "$($bl.model)".Trim() -or -not $blDate) {
        $problems.Add('baseline 要写 model 和 date（yyyy-MM-dd）')
    } else {
        $age = [int]($now - $blDate).TotalDays
        $url = if ("$($bl.image)".Trim()) { Get-ImageUrl "$($bl.image)" $repoFull 'baseline' }
        $result.Baseline = [ordered]@{ Model = "$($bl.model)"; Date = Date-Text $blDate; AgeDays = $age; Input = $bl.input; Cost = $bl.cost; Minutes = $bl.minutes; ImageUrl = $url }
        if ($age -gt 31) { $actions.Add("基准 $age 天没重跑（超过一个月）：加一项重跑基准（direction.md 第 4 节）") }
    }

    $runs = @(foreach ($x in @($b.runs | Where-Object { $null -ne $_ })) {
        $d = Read-Date $x.date
        $g = Read-Number $x.gap
        if (-not $d -or $null -eq $g) { $problems.Add("runs 里有一条写错了（date 要 yyyy-MM-dd，gap 要数字）：$($x | ConvertTo-Json -Compress -Depth 2)"); continue }
        [pscustomobject]@{ Date = $d; Gap = $g; Image = $x.image; Note = $x.note }
    })
    # 同一天多条取文件里靠后的：Sort-Object -Stable 保留原顺序。
    $runs = @($runs | Sort-Object -Property Date -Stable)
    $weekly = {
        param($list)
        @($list | Group-Object { '{0}-W{1:00}' -f [Globalization.ISOWeek]::GetYear($_.Date), [Globalization.ISOWeek]::GetWeekOfYear($_.Date) } | ForEach-Object {
            $last = $_.Group[-1]
            [pscustomobject]@{ Week = $_.Name; Date = $last.Date; Gap = $last.Gap }
        } | Sort-Object Date)
    }
    $result.Trend = @(& $weekly $runs | ForEach-Object { [ordered]@{ Week = $_.Week; Date = Date-Text $_.Date; Gap = $_.Gap } })
    $latest = if ($runs) { $runs[-1] }
    if ($latest) {
        $result.Gap = $latest.Gap
        $result.LastRun = Date-Text $latest.Date
        $result.Note = $latest.Note
        if ("$($latest.Image)".Trim()) { $result.ImageUrl = Get-ImageUrl "$($latest.Image)" $repoFull "runs $(Date-Text $latest.Date)" }
    }

    # 三个周点依次没变小，最近一点还没比过基准：连续 2 周没缩小。
    $stalled = {
        param($points)
        if ($points.Count -lt 3) { return $null }
        $c = $points[-3..-1]
        if ($c[2].Gap -gt 0 -and $c[1].Gap -ge $c[0].Gap -and $c[2].Gap -ge $c[1].Gap) { "$($c[0].Gap) → $($c[1].Gap) → $($c[2].Gap)" }
    }

    $seen = @{}
    $dirs = @(foreach ($x in @($b.directions | Where-Object { $null -ne $_ })) {
        $name = "$($x.name)".Trim()
        $state = "$($x.state)".Trim()
        $started = Read-Date $x.started
        if (-not $name -or $name -match '[\[\]]') { $problems.Add("directions 里有一条 name 没写或带方括号：$name"); continue }
        if ($seen[$name]) { $problems.Add("directions 里 $name 写了两次"); continue }
        $seen[$name] = $true
        if ($state -notin '原型', '进行中', '结束') { $problems.Add("方向 $name 的 state 要写 原型 / 进行中 / 结束，现在是：$state"); continue }
        $budgetDays = Read-Number $x.budgetDays
        $budgetQuota = Read-Number $x.budgetQuota
        $spentQuota = Read-Number $x.spentQuota
        foreach ($q in 'budgetQuota', 'spentQuota') { if ($null -ne $x.$q -and $null -eq (Read-Number $x.$q)) { $problems.Add("方向 $name 的 $q 要写数字：$($x.$q)") } }
        $reasons = [Collections.Generic.List[string]]::new()
        $used = $null
        if ($null -ne $x.decided -and -not (Read-Date $x.decided)) { $problems.Add("方向 $name 的 decided 要写 yyyy-MM-dd：$($x.decided)") }
        if ($state -ne '结束') {
            if (-not $started) { $problems.Add("方向 $name 要写 started（yyyy-MM-dd）") }
            if (-not $budgetDays -or $budgetDays -le 0) { $problems.Add("方向 $name 要写预算 budgetDays（天数）") }
            if ($started) { $used = [int]($now - $started).TotalDays }
            $decided = Read-Date $x.decided
            $since = if ($started -and $decided -and $decided -gt $started) { $decided } else { $started }
            $mine = if ($since) { @($runs | Where-Object { $_.Date -ge $since }) } else { @() }
            $lastMine = if ($mine) { $mine[-1] }
            # 比过基准只认这个方向开工以后、基准重跑以后的测量。
            $beaten = $lastMine -and $lastMine.Gap -le 0 -and (-not $blDate -or $lastMine.Date -ge $blDate)
            $overDays = $null -ne $used -and $budgetDays -gt 0 -and $used -ge $budgetDays
            $overQuota = $budgetQuota -gt 0 -and $spentQuota -ge $budgetQuota
            $what = if ($overDays) { "预算 $budgetDays 天花完了（已 $used 天）" } elseif ($overQuota) { "额度预算 $budgetQuota 花完了（已用 $spentQuota）" }
            if ($what -and $state -eq '原型') { if ($waitingDirs -notcontains $name) { $reasons.Add("原型$what") } }
            elseif ($what -and -not $beaten) { $reasons.Add("$what，还没比过基准") }
            if ($state -eq '进行中' -and $started) {
                $trail = & $stalled @(& $weekly $mine)
                if ($trail) { $reasons.Add("差距连续 2 周没缩小（$trail）") }
                $lastDate = if ($mine) { $mine[-1].Date } else { $since }
                $quiet = [int]($now - $lastDate).TotalDays
                if ($quiet -ge 14) { $reasons.Add("差距 $quiet 天没量（不量就算没缩小）") }
            }
        }
        [ordered]@{ Name = $name; State = $state; Started = Date-Text $started; Used = $used; BudgetDays = $budgetDays; BudgetQuota = $budgetQuota; SpentQuota = $spentQuota; Reasons = @($reasons) }
    })
    $result.Directions = $dirs
    $result.Stopped = @($dirs | Where-Object { $_.Reasons.Count } | ForEach-Object { [ordered]@{ Name = $_.Name; Reason = ($_.Reasons -join '；') } })
    foreach ($s in $result.Stopped) { $actions.Add("方向 $($s.Name) 要停：$($s.Reason)。不再派它的新项，加一项 方向复盘：$($s.Name)，先复盘再报决定卡（direction.md 第 5 节）") }
    if (-not @($dirs | Where-Object { $_.State -ne '结束' })) {
        # 用户定过（继续，或者放弃了某个方向）以后重新算，不然放弃以后每次都再报一遍。
        if ($null -ne $b.decided -and -not (Read-Date $b.decided)) { $problems.Add("顶层 decided 要写 yyyy-MM-dd：$($b.decided)") }
        $marks = @(@(Read-Date $b.decided) + @(@($b.directions | Where-Object { $null -ne $_ }) | ForEach-Object { Read-Date $_.decided }) | Where-Object { $_ } | Sort-Object)
        $projSince = if ($marks) { $marks[-1] }
        $recent = if ($projSince) { @($runs | Where-Object { $_.Date -ge $projSince }) } else { $runs }
        $trail = & $stalled @(& $weekly $recent)
        if ($trail) { $actions.Add("差距连续 2 周没缩小（$trail）：加一项 方向复盘，先复盘再报决定卡（direction.md 第 5 节）") }
        $from = if ($latest) { $latest.Date } else { $blDate }
        if ($projSince -and (-not $from -or $projSince -gt $from)) { $from = $projSince }
        $quiet = if ($from) { [int]($now - $from).TotalDays } else { 0 }
        if ($quiet -ge 14) { $actions.Add("差距 $quiet 天没量：加一项量一次（direction.md 第 4 节）") }
    }
} elseif ($result.Benchmark -eq 'none') {
    $actions.Add('还没登记基准（docs/benchmark.json）：加一项 登记基准（direction.md 第 4 节）')
}

# 流程图：docs/flow.html 或 docs/flow.md 都算，两个都有用 html（direction.md 第 6 节）。
$flow = @('docs/flow.html', 'docs/flow.md' | ForEach-Object { Join-Path $repoFull $_ } | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1)
if ($flow.Count) { $result.FlowUrl = ([Uri]$flow[0]).AbsoluteUri }
elseif ($result.Benchmark -ne 'notApplicable') { $actions.Add('还没有流程图（docs/flow.html 或 docs/flow.md）：加一项 流程图（direction.md 第 6 节）') }

# 决定卡：docs/decisions/*.md，开头 10 行里写着"状态：待定"的。正文按行给状态页，图换成地址。
if (Test-Path -LiteralPath $cardDir) {
    $imageRe = '!\[([^\]]*)\]\(([^)]+)\)'
    $result.Cards = @(foreach ($f in Get-ChildItem -LiteralPath $cardDir -Filter '*.md' -File | Sort-Object Name) {
        $text = @(Get-Content -LiteralPath $f.FullName -Encoding UTF8)
        if (-not @($text | Select-Object -First 10 | Where-Object { $_ -match '^\s*状态\s*[：:]\s*待定' }).Count) { continue }
        $rel = "docs/decisions/$($f.Name)"
        $title = @($text | Where-Object { $_ -match '^#\s+' } | Select-Object -First 1) -replace '^#\s+', '' -replace '^决定卡[：:]\s*', ''
        $lines = @(foreach ($l in $text) {
            if ($l -match '^\s*$' -or $l -match '^\s*状态\s*[：:]') { continue }
            $imgs = [regex]::Matches($l, $imageRe)
            $rest = ([regex]::Replace($l, $imageRe, '')).Trim()
            if ($rest -match '^#{2,}\s+(.*)$') { [ordered]@{ Type = 'h'; Text = $Matches[1] } }
            elseif ($rest -match '^#\s+') { continue }
            elseif ($rest) { [ordered]@{ Type = 'text'; Text = $rest } }
            foreach ($m in $imgs) {
                $url = Get-ImageUrl $m.Groups[2].Value $f.DirectoryName "决定卡 $rel"
                if ($url) { [ordered]@{ Type = 'image'; Alt = $m.Groups[1].Value; Url = $url } }
                else { [ordered]@{ Type = 'text'; Text = "（图打不开：$($m.Groups[2].Value)）" } }
            }
        })
        [ordered]@{ Title = "$title"; File = $rel; Url = ([Uri]$f.FullName).AbsoluteUri; Lines = $lines }
    })
}

foreach ($p in $problems) { $actions.Add("改好 docs/benchmark.json 或决定卡：$p") }
$result.Actions = @($actions)
$result.Problems = @($problems)

if ($Json) { [pscustomobject]$result | ConvertTo-Json -Depth 8 }
else {
    if ($actions.Count) { $actions | ForEach-Object { $_ } }
    else { '没有要处理的' }
}
if ($actions.Count) { exit 3 }
exit 0
