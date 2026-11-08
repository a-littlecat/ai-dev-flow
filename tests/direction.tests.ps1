param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/direction.ps1'), [switch]$Keep)
# direction.ps1 的检查：在系统临时目录建一次性项目目录，对 -Json 和退出码逐条断言；退出码 0 才算通过。
#   pwsh -NoProfile -File tests/direction.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("direction-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }

$script:n = 0
# 建一个项目。$b 是 benchmark.json 的内容（对象或原文字符串），$null 就不写。默认带流程图，只看基准的判定。
function New-Repo($b, [switch]$NoFlow) {
    $script:n++
    $repo = Join-Path $root "项目 $($script:n)"
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $repo 'docs/pics')
    if (-not $NoFlow) { Set-Content -LiteralPath (Join-Path $repo 'docs/flow.html') -Encoding utf8NoBOM -Value '<html></html>' }
    Set-Content -LiteralPath (Join-Path $repo 'docs/pics/a.png') -Encoding utf8NoBOM -Value 'x'
    if ($null -ne $b) {
        $text = if ($b -is [string]) { $b } else { $b | ConvertTo-Json -Depth 6 }
        Set-Content -LiteralPath (Join-Path $repo 'docs/benchmark.json') -Encoding utf8NoBOM -Value $text
    }
    $repo
}
function Run($repo, $today = '2026-11-30') {
    $out = pwsh -NoProfile -File $Script -Repo $repo -Today $today -Json 2>&1 | Out-String
    $code = $LASTEXITCODE
    $o = $out | ConvertFrom-Json
    $o | Add-Member -NotePropertyName Code -NotePropertyValue $code
    $o
}
function Base($runs = @(), $dirs = @()) {
    [ordered]@{
        northStar = '最终图纸和基准的差异比例'
        baseline = [ordered]@{ model = '通用模型 X'; date = '2026-11-20'; input = '三张固定样图'; cost = '12 元'; minutes = 40 }
        directions = @($dirs)
        runs = @($runs)
    }
}
function Pt($d, $g) { [ordered]@{ date = $d; gap = $g } }
function D($name, $state = '进行中', $started = '2026-11-01', $days = 60, $extra = @{}) {
    $o = [ordered]@{ name = $name; state = $state; started = $started; budgetDays = $days }
    foreach ($k in $extra.Keys) { $o[$k] = $extra[$k] }
    $o
}

try {
    # 周一：2026-11-02、11-09、11-16、11-23、11-30 分属相邻的五周
    $r = Run (New-Repo $null)
    Check 'no benchmark file asks to register one' ($r.Benchmark -eq 'none' -and $r.Code -eq 3 -and ($r.Actions -join '') -match '登记基准')

    $r = Run (New-Repo ([ordered]@{ notApplicable = '这是工具仓库，没有交付物' }) -NoFlow)
    Check 'notApplicable has nothing to do, flow page included' ($r.Benchmark -eq 'notApplicable' -and $r.Code -eq 0 -and $r.NotApplicable -match '工具仓库')

    $r = Run (New-Repo (Base @((Pt '2026-11-23' 0.5), (Pt '2026-11-30' 0.3))) -NoFlow)
    Check 'missing flow page is an action' ($r.Code -eq 3 -and ($r.Actions -join '') -match '流程图' -and -not $r.FlowUrl)

    # 收敛
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.5), (Pt '2026-11-23' 0.4), (Pt '2026-11-30' 0.3)) @((D 'A'))))
    Check 'shrinking gap: nothing stopped, exit 0' ($r.Code -eq 0 -and -not @($r.Stopped).Count -and $r.Gap -eq 0.3 -and @($r.Trend).Count -eq 3)
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3), (Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.3)) @((D 'A'))))
    Check 'flat for 2 weeks stops the direction' ($r.Code -eq 3 -and @($r.Stopped).Count -eq 1 -and $r.Stopped[0].Name -eq 'A' -and $r.Stopped[0].Reason -match '连续 2 周没缩小')
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3), (Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.4)) @((D 'A'))))
    Check 'growing gap stops the direction' (@($r.Stopped).Count -eq 1)
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.5), (Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.3)) @((D 'A'))))
    Check 'one flat week is not enough' (-not @($r.Stopped).Count -and $r.Code -eq 0)
    $r = Run (New-Repo (Base @((Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.3)) @((D 'A'))))
    Check 'two points are not enough' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @((Pt '2026-11-16' (-0.1)), (Pt '2026-11-23' (-0.1)), (Pt '2026-11-30' (-0.1))) @((D 'A'))))
    Check 'flat but already past the baseline does not stop' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3), (Pt '2026-11-30' 0.9), (Pt '2026-11-17' 0.2), (Pt '2026-11-24' 0.25)) @((D 'A'))))
    Check 'each week uses its last run, in date order' (($r.Trend | ForEach-Object { $_.Gap }) -join ',' -eq '0.2,0.25,0.9' -and @($r.Stopped).Count -eq 1 -and $r.LastRun -eq '2026-11-30')

    # 用户定过以后重新算
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3), (Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.3)) @((D 'A' -extra @{ decided = '2026-11-23' }))))
    Check 'decided restarts the stall window' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @((Pt '2026-11-02' 0.3), (Pt '2026-11-30' 0.3)) @((D 'A' -extra @{ decided = '2026-11-30' }))))
    Check 'decided today has no quiet period' (-not @($r.Stopped).Count)

    # 没量
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3)) @((D 'A'))))
    Check 'no run for 14 days stops' (@($r.Stopped).Count -eq 1 -and $r.Stopped[0].Reason -match '14 天没量')
    $r = Run (New-Repo (Base @((Pt '2026-11-17' 0.3)) @((D 'A'))))
    Check 'no run for 13 days does not' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @() @((D 'A' -started '2026-11-10'))))
    Check 'a direction never measured stops after 14 days' (@($r.Stopped).Count -eq 1)

    # 预算
    $r = Run (New-Repo (Base @((Pt '2026-11-23' 0.4), (Pt '2026-11-30' 0.3)) @((D 'A' -days 29))))
    Check 'budget days used up without beating the baseline stops' (@($r.Stopped).Count -eq 1 -and $r.Stopped[0].Reason -match '预算 29 天')
    $r = Run (New-Repo (Base @((Pt '2026-11-23' 0.4), (Pt '2026-11-30' 0.3)) @((D 'A' -days 30 -started '2026-11-02'))))
    Check 'budget one day short of used up does not' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @((Pt '2026-11-23' 0.4), (Pt '2026-11-30' (-0.1))) @((D 'A' -days 5))))
    Check 'budget used up but baseline beaten does not stop' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @((Pt '2026-11-23' 0.4), (Pt '2026-11-30' 0.3)) @((D 'A' -extra @{ budgetQuota = 100; spentQuota = 100 }))))
    Check 'quota used up stops' (@($r.Stopped).Count -eq 1 -and $r.Stopped[0].Reason -match '额度预算 100')
    $r = Run (New-Repo (Base @((Pt '2026-11-30' (-0.5))) @((D 'P' '原型' '2026-11-20' 3))))
    Check 'a prototype over budget stops even when the gap is fine' (@($r.Stopped).Count -eq 1 -and $r.Stopped[0].Reason -match '^原型')
    $r = Run (New-Repo (Base @() @((D 'P' '原型' '2026-11-29' 3))))
    Check 'a prototype in budget and unmeasured is fine' (-not @($r.Stopped).Count)
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3), (Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.3)) @((D 'A' '结束' -days 1))))
    Check 'a finished direction is not judged by itself' (-not @($r.Stopped).Count -and ($r.Actions -join '') -match '连续 2 周没缩小')

    # 没有方向时按项目整体看
    $r = Run (New-Repo (Base @((Pt '2026-11-16' 0.3), (Pt '2026-11-23' 0.3), (Pt '2026-11-30' 0.3))))
    Check 'no direction: stall still asks for a review, nothing to stop' ($r.Code -eq 3 -and -not @($r.Stopped).Count -and ($r.Actions -join '') -match '方向复盘')
    $r = Run (New-Repo (Base @((Pt '2026-11-02' 0.3))))
    Check 'no direction: quiet asks for a measurement' (($r.Actions -join '') -match '28 天没量')
    $r = Run (New-Repo (Base @((Pt '2026-11-30' 0.3))))
    Check 'fresh baseline and run: nothing to do' ($r.Code -eq 0 -and $r.Baseline.AgeDays -eq 10)

    # 基准过期
    $old = Base @((Pt '2026-11-30' 0.3)); $old.baseline.date = '2026-10-29'
    $r = Run (New-Repo $old)
    Check 'baseline older than a month asks for a rerun' ($r.Code -eq 3 -and ($r.Actions -join '') -match '基准 32 天没重跑')
    $old.baseline.date = '2026-10-30'
    $r = Run (New-Repo $old)
    Check 'baseline at 31 days is fine' ($r.Code -eq 0)

    # 写错的
    $r = Run (New-Repo '{ 不是 json')
    Check 'broken JSON is reported, not thrown' ($r.Benchmark -eq 'bad' -and $r.Code -eq 3 -and @($r.Problems).Count -eq 1)
    $r = Run (New-Repo '[1, 2]')
    Check 'top level must be an object' ($r.Benchmark -eq 'bad' -and $r.Code -eq 3)
    $bad = Base @((Pt '2026/11/30' 0.3), (Pt '2026-11-30' '0.3'), (Pt '2026-11-29' 0.2))
    $r = Run (New-Repo $bad)
    Check 'bad run date and string gap are reported and skipped' (@($r.Problems).Count -eq 2 -and $r.Gap -eq 0.2)
    $bad = Base; $bad.baseline = [ordered]@{ model = '' }
    $r = Run (New-Repo $bad)
    Check 'baseline needs model and date' (($r.Problems -join '') -match 'baseline' -and $r.Code -eq 3)
    $bad = Base; $bad.northStar = ''
    $r = Run (New-Repo $bad)
    Check 'northStar is required' (($r.Problems -join '') -match 'northStar')
    $r = Run (New-Repo (Base @((Pt '2026-11-30' 0.3)) @((D 'A' '不知道'), (D 'B[1]'), [ordered]@{ name = 'C'; state = '进行中'; started = '2026-11-20' }, (D 'E'), (D 'E'))))
    Check 'bad directions are reported' (($r.Problems -join '|') -match '不知道' -and ($r.Problems -join '|') -match '方括号' -and ($r.Problems -join '|') -match 'C 要写预算' -and ($r.Problems -join '|') -match 'E 写了两次')

    # 图
    $img = Base @((Pt '2026-11-23' 0.4), ([ordered]@{ date = '2026-11-30'; gap = 0.3; image = 'docs/pics/a.png'; note = '第一版' }))
    $r = Run (New-Repo $img)
    Check 'image in the repo gives a file URL' ($r.ImageUrl -like 'file:///*/docs/pics/a.png' -and $r.ImageUrl -notmatch ' ' -and $r.Note -eq '第一版' -and $r.Code -eq 0)
    foreach ($case in @(@('docs/pics/none.png', '不存在'), @('../outside.png', '仓库外'), @('C:/Windows/win.ini', '相对路径'), @('https://example.com/a.png', '相对路径'), @('/etc/passwd', '相对路径'))) {
        $img = Base @((,([ordered]@{ date = '2026-11-30'; gap = 0.3; image = $case[0] })))
        $r = Run (New-Repo $img)
        Check "bad image $($case[0]) has no URL" (-not $r.ImageUrl -and ($r.Problems -join '') -match $case[1] -and $r.Code -eq 3)
    }

    # 决定卡
    $repo = New-Repo (Base @((Pt '2026-11-30' 0.3)))
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $repo 'docs/decisions')
    Set-Content -LiteralPath (Join-Path $repo 'docs/decisions/2026-11-30-换路线.md') -Encoding utf8NoBOM -Value @'
# 决定卡：换不换路线

状态：待定
日期：2026-11-30

## 要定什么

<b>走</b>到一半。

- 证据：![行内](../pics/a.png) 看这里

![A 并排](../pics/a.png)
![坏的](../../../外面.png)
'@
    Set-Content -LiteralPath (Join-Path $repo 'docs/decisions/2026-11-01-旧的.md') -Encoding utf8NoBOM -Value "# 决定卡：旧的`n`n状态：已定（2026-11-02）"
    $r = Run $repo
    Check 'only pending cards are listed' (@($r.Cards).Count -eq 1 -and $r.Cards[0].Title -eq '换不换路线' -and $r.Cards[0].File -eq 'docs/decisions/2026-11-30-换路线.md')
    $lines = @($r.Cards[0].Lines)
    Check 'card lines keep headings and text' (@($lines | Where-Object { $_.Type -eq 'h' -and $_.Text -eq '要定什么' }).Count -eq 1 -and @($lines | Where-Object { $_.Type -eq 'text' -and $_.Text -match '走' }).Count -eq 1)
    Check 'card images resolve from the card folder, inline ones too' (@($lines | Where-Object { $_.Type -eq 'image' -and $_.Url -like '*/docs/pics/a.png' }).Count -eq 2)
    Check 'a card image outside the repo becomes text and a problem' (@($lines | Where-Object { $_.Type -eq 'text' -and $_.Text -match '图打不开' }).Count -eq 1 -and ($r.Problems -join '') -match '仓库外')
    Check 'the title and status lines are not repeated in the body' (-not @($lines | Where-Object { $_.Text -match '换不换路线|状态' }).Count)

    # 模板和本仓库自己的那页：流程图要有的几样都在；模板不能被当成一张待定的卡
    $here = Join-Path $PSScriptRoot '..'
    foreach ($page in 'skills/ai-dev-flow/templates/flow.html', 'docs/flow.html') {
        $t = Get-Content -LiteralPath (Join-Path $here $page) -Raw -Encoding UTF8
        Check "$page has steps, who, what passes, how to measure, weak spots" ($t -match 'class="step"' -and $t -match 'class="who ' -and $t -match 'class="pass"' -and $t -match '<dt>怎么量</dt>' -and $t -match '<dt>短板</dt>')
    }
    $card = Get-Content -LiteralPath (Join-Path $here 'skills/ai-dev-flow/templates/decision-card.md') -Raw -Encoding UTF8
    Check 'decision card template has what a card needs' ($card -match '状态：待定' -and $card -match '## 选项' -and $card -match '做法' -and $card -match '质量 / 成本 / 时间' -and $card -match '风险' -and $card -match '## 推荐' -and $card -match '## 不定的代价' -and $card -match '!\[')
    $r = Run $here
    Check 'this repository needs no baseline and has its flow page' ($r.Benchmark -eq 'notApplicable' -and $r.FlowUrl -and $r.Code -eq 0)

    # 文本输出
    $repo = New-Repo (Base @((Pt '2026-11-30' 0.3)))
    $text = pwsh -NoProfile -File $Script -Repo $repo -Today '2026-11-30' | Out-String
    Check 'text output says nothing to do' ($text -match '没有要处理的' -and $LASTEXITCODE -eq 0)
    $repo = New-Repo $null
    $text = pwsh -NoProfile -File $Script -Repo $repo | Out-String
    Check 'text output lists the action, exit 3' ($text -match '登记基准' -and $LASTEXITCODE -eq 3)
    $null = pwsh -NoProfile -File $Script -Repo (Join-Path $root 'nowhere') 2>&1
    Check 'missing repo fails with 1' ($LASTEXITCODE -eq 1)
}
finally {
    if ($Keep) { "kept: $root" } elseif (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
}
if ($fail) { "$fail check(s) failed"; exit 1 } else { 'all checks passed'; exit 0 }
