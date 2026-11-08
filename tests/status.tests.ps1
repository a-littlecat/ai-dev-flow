param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/status.ps1'), [switch]$Keep)
# status.ps1 的检查：在系统临时目录建几个一次性仓库，对 -Json 和文本输出逐条断言；退出码 0 才算通过。-Keep 保留这些仓库便于查看。
#   pwsh -NoProfile -File tests/status.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("status-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main @args; if ($LASTEXITCODE) { throw "git $args" } }

$a = Join-Path $root '项目 A'
$null = New-Item -ItemType Directory -Force -Path (Join-Path $a 'docs'), (Join-Path $a '.agents/digest')
G init -q $a
Set-Content -LiteralPath (Join-Path $a 'AGENTS.md') -Encoding utf8NoBOM -Value "- **信任等级 L1**（用户定）"
Set-Content -LiteralPath (Join-Path $a '.gitignore') -Encoding utf8NoBOM -Value '.agents/'
@'
# 队列

| # | 目标 | 完成标准 | 档 | 依赖 | 状态 |
|---|---|---|---|---|---|
| 1 | 写 a\|b 解析 | 过 | 自走 | 无 | 完成（合main abc） |
| 2 | 看界面 | 截图 | 看一眼 | 无 | **待用户**（等你看截图） |
| 3 | 推远程 | 授权 | 单向门 | 无 | 待用户 |
| 4 | 跑回归 | 绿 | 自走 | 1 | 在做（r2） |
| 5 | 说不准 | 绿 | 自走 | 无 | 部分已定：选了 A |
| 8 | 依赖已完成 | 绿 | 自走 | 1 | 待做 |
| 9 | 依赖还在做 | 绿 | 自走 | #4、1 | 待做 |
| 10 | 依赖别的项目 | 绿 | 自走 | 天正 #22 | 待做 |
| 11 | 没有依赖 | 绿 | 自走 | 无 | 待做 |
| 12 | 依赖的项已删 | 绿 | 自走 | 99 | 待做 |
| 13 | 依赖只有井号 | 绿 | 自走 | # | 待做 |

另一张不算队列的表：

| 名称 | 值 |
|---|---|
| x | 待用户 |

目标 | # | 档 | 状态
:--|:-:|---|--:
无竖线表 | 6 | 自走 | 待用户（另一种写法）

说明 | 状态
没有分隔行 | 待用户
还是没有 | 待用户

```
| code | 状态 |
|---|---|
| x | 待用户 |
```

````markdown
```
| ex | 状态 |
|---|---|
| e1 | 待用户 |
```
| ex | 状态 |
|---|---|
| e2 | 待用户 |
````

~~~markdown
```powershell
```
~~~

| # | 目标 | 档 | 状态 |
|---|---|---|---|
| 7 | 围栏后的真表 | 看一眼 | 待用户（真的） |

    | ex | 状态 |
    |---|---|
    | e3 | 待用户 |

```
``` 不是结束
| ex | 状态 |
|---|---|
| e4 | 待用户 |
```
'@ | Set-Content -LiteralPath (Join-Path $a 'docs/queue.md') -Encoding utf8NoBOM
G -C $a add -A; G -C $a commit -q -m 'c1'
$c1 = (G -C $a rev-parse HEAD)
@"
reviewed-through: $c1

# 教训

## 规则一
原因：x
Seen：2（2026-10-29、2026-10-30）

## 规则二
Seen：1（2026-10-30）

## 规则三该升级
Seen：3（2026-10-28、2026-10-29、2026-10-30）

## 规则四已交出去
Seen：4（2026-10-27、2026-10-28、2026-10-29、2026-10-30）
升级：已写进 ai-dev-flow 的 docs/requests.md（2026-10-30）
"@ | Set-Content -LiteralPath (Join-Path $a 'LESSONS.md') -Encoding utf8NoBOM
@'
# 收到的请求

## 2026-10-30 已经转了
- **状态**：已转（队列 #3）

## 2026-10-31 还没转
- **现象**：x
- **状态**：待转

## 2026-11-01 忘了写状态
- **请求**：y

## 2026-11-02 处理完了
- **状态**：已处理（2.0.0）
'@ | Set-Content -LiteralPath (Join-Path $a 'docs/requests.md') -Encoding utf8NoBOM
G -C $a add -A; G -C $a commit -q -m 'c2 中文提交'
G -C $a branch merged-one
G -C $a worktree add -q (Join-Path $root 'wt-merged') merged-one
G -C $a worktree add -q --detach (Join-Path $root 'wt-detached') HEAD
G -C $a worktree add -q -b gone (Join-Path $root 'wt-gone') HEAD
Remove-Item -Recurse -Force (Join-Path $root 'wt-gone')
G -C $a switch -q -c side; G -C $a commit -q --allow-empty -m 'side only'; G -C $a switch -q main
Set-Content -LiteralPath (Join-Path $a 'scratch.txt') -Value 'x'
$null = New-Item -ItemType Directory -Force -Path (Join-Path $a '未跟踪 目录')
'1' | Set-Content -LiteralPath (Join-Path $a '未跟踪 目录/一.txt'); '2' | Set-Content -LiteralPath (Join-Path $a '未跟踪 目录/二.txt')
Add-Content -LiteralPath (Join-Path $a 'AGENTS.md') -Value 'edit'
"今天：合了 1 项`n北极星：7（昨天 5）`n返工：0 / 1`n要你做：无" | Set-Content -LiteralPath (Join-Path $a '.agents/digest/2026-10-30.md') -Encoding utf8NoBOM
"北极星：9（昨天 7）" | Set-Content -LiteralPath (Join-Path $a '.agents/digest/2026-10-31.md') -Encoding utf8NoBOM

$b = Join-Path $root 'b'
G init -q $b; G -C $b commit -q --allow-empty -m 'b1'

$cfg = Join-Path $root 'hq/projects.json'
$null = New-Item -ItemType Directory -Force -Path (Split-Path $cfg)
@{ projects = @(
    @{ name = '项目 A'; path = $a; status = '推进中'; priority = 1; trunk = 'main'; dependsOn = @('b', '不存在')
       goals = @(@{ text = '目标一'; items = @('1') }, @{ text = '目标二'; items = @('#4') }, @{ text = '手动勾的 <x>'; done = $true }) }
    @{ name = 'b'; path = $b; status = '维护'; priority = 2 }
    @{ name = 'gone'; path = (Join-Path $root 'nope'); status = '推进中'; priority = 3 }
    @{ name = 'paused'; path = $b; status = '暂停' }
    @{ name = 'paused-gone'; path = (Join-Path $root 'nope'); status = '暂停' }
) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfg -Encoding utf8NoBOM

try {
    (Get-Item -LiteralPath (Join-Path $a '.gitignore')).LastWriteTime = (Get-Date).AddMinutes(-5)
    $run = Join-Path $a '.agents/runs/r1/final.md'
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $run)
    'done' | Set-Content -LiteralPath $run
    $runTime = (Get-Date).AddMinutes(30)
    (Get-Item -LiteralPath $run).LastWriteTime = $runTime
    $index = Join-Path $a '.git/index'
    $indexBefore = (Get-FileHash -LiteralPath $index).Hash
    $j = pwsh -NoProfile -File $Script -Config $cfg -Json -Lessons | Out-String | ConvertFrom-Json
    Check 'exit 0' ($LASTEXITCODE -eq 0)
    Check 'project index not rewritten' ((Get-FileHash -LiteralPath $index).Hash -eq $indexBefore)
    $pa = $j.Projects | Where-Object Name -eq '项目 A'
    Check 'order: active by priority, then maintenance' (($j.Projects.Name -join ',') -eq '项目 A,gone,b')
    Check 'paused listed by name, missing path marked' (($j.Paused -join ',') -eq 'paused,paused-gone（路径不存在）')
    Check 'trust parsed' ($pa.Trust -eq 'L1')
    Check 'queue counts' ($pa.Queue.'完成' -eq 1 -and $pa.Queue.'待用户' -eq 4 -and $pa.Queue.'在做' -eq 1 -and $pa.Queue.'其他' -eq 1 -and $pa.Queue.'待做' -eq 6)
    Check 'tables without state column or separator row, and code blocks, ignored' ((($pa.Queue.PSObject.Properties.Value | Measure-Object -Sum).Sum) -eq 13)
    Check 'available: deps done, none, or deleted; not open, foreign or number-less' ($pa.Available -eq 3)
    Check 'goals: by items, open item, manual done' ((($pa.Goals | ForEach-Object { "$($_.Text)=$($_.Done)" }) -join ';') -eq '目标一=True;目标二=False;手动勾的 <x>=True')
    Check 'last activity takes the newest of branches and runs' ($pa.LastActivity -eq $runTime.ToString('yyyy-MM-dd HH:mm'))
    Check 'doing and nonstandard items listed' ((($pa.Doing | ForEach-Object Id) -join ',') -eq '4' -and (($pa.Other | ForEach-Object Id) -join ',') -eq '5')
    Check 'not stalled while active' (-not ($pa.Problems -match '^可能停滞'))
    $pb0 = $j.Projects | Where-Object Name -eq 'b'
    Check 'last activity from commits when no runs' ($pb0.LastActivity -eq (G -C $b log -1 '--format=%cd' '--date=format:%Y-%m-%d %H:%M') -and $pb0.IdleMinutes -ge 0)
    Check 'waiting items with tier and detail' ((($pa.Waiting | ForEach-Object { "$($_.Id)/$($_.Tier)/$($_.Detail)" }) -join ';') -eq '2/看一眼/等你看截图;3/单向门/;6/自走/另一种写法;7/看一眼/真的')
    Check 'escaped pipe does not shift columns' ($pa.Queue.'完成' -eq 1)
    Check 'unknown state reported' ([bool]($pa.Problems | Where-Object { $_ -like '*#5*' }))
    Check 'unknown dependency reported' ([bool]($pa.Problems | Where-Object { $_ -like '*不存在*' }))
    Check 'unreviewed = 1' ($pa.Unreviewed -eq 1)
    Check 'new commits on trunk only' ($pa.NewCount -eq 2 -and -not ($pa.NewCommits -match 'side only'))
    Check 'chinese subject decoded' ([bool]($pa.NewCommits -match 'c2 中文提交'))
    Check 'lessons with seen' ((($pa.Lessons | ForEach-Object { "$($_.Seen):$($_.Title)" }) -join ';') -eq '2:规则一;1:规则二;3:规则三该升级;4:规则四已交出去')
    Check 'lessons due: seen 3 without an upgrade line, reported' ((($pa.LessonsDue | ForEach-Object { "$($_.Seen):$($_.Title)" }) -join ';') -eq '3:规则三该升级' -and [bool]($pa.Problems -match '^教训 Seen 达到 3 还没升级：规则三该升级（Seen 3）$'))
    Check 'requests: pending and missing state listed, transferred and handled not' ((($pa.Requests | ForEach-Object { "$($_.Title)=$($_.State)" }) -join ';') -eq '2026-10-31 还没转=待转;2026-11-01 忘了写状态=未写状态' -and [bool]($pa.Problems -match '^还没转进队列的请求 2 条：2026-10-31 还没转、2026-11-01 忘了写状态$'))
    Check 'latest digest lines' ($pa.Digest.Date -eq '2026-10-31' -and ($pa.Digest.Lines -join ';') -eq '北极星：9（昨天 7）')
    Check 'worktrees' ($pa.Worktrees -eq 3 -and $pa.WorktreesMerged -eq 2 -and $pa.WorktreesDetached -eq 1 -and $pa.WorktreesMissing -eq 1)
    Check 'merged branches exclude trunk' ($pa.BranchesMerged -eq 2)
    Check 'uncommitted vs untracked files' ($pa.Uncommitted -eq 1 -and $pa.Untracked -eq 3)
    $pg = $j.Projects | Where-Object Name -eq 'gone'
    Check 'missing path reported' ([bool]($pg.Problems | Where-Object { $_ -like '路径不存在*' }))
    $pb = $j.Projects | Where-Object Name -eq 'b'
    Check 'no queue reported' ([bool]($pb.Problems | Where-Object { $_ -like '没有队列文件*' }))

    $null = pwsh -NoProfile -File $Script -Config $cfg -Mark
    G -C $a commit -q --allow-empty -m 'after mark'
    (Get-Item -LiteralPath $run).LastWriteTime = (Get-Date).AddHours(-3)
    $j2 = pwsh -NoProfile -File $Script -Config $cfg -Json | Out-String | ConvertFrom-Json
    $pa2 = $j2.Projects | Where-Object Name -eq '项目 A'
    Check 'lessons due and requests without -Lessons' ($pa2.LessonsDue.Count -eq 1 -and $pa2.Requests.Count -eq 2 -and -not $pa2.Lessons)
    Check 'mark: only commits after it' ($pa2.NewCount -eq 1 -and $pa2.NewSince -like '自上次标记*')
    $j3 = pwsh -NoProfile -File $Script -Config $cfg -Json -Since '2000-01-01' | Out-String | ConvertFrom-Json
    Check 'stale only past -StaleMinutes' (-not (($j2.Projects | Where-Object Name -eq '项目 A').Problems -match '^可能停滞'))
    $js = pwsh -NoProfile -File $Script -Config $cfg -Json -StaleMinutes 0 | Out-String | ConvertFrom-Json
    Check 'stalled: active project with work in progress and no activity' ([bool](($js.Projects | Where-Object Name -eq '项目 A').Problems -match '^可能停滞：在做 1 项') -and -not (($js.Projects | Where-Object Name -eq 'b').Problems -match '^可能停滞'))
    Check '-Since overrides mark' ((($j3.Projects | Where-Object Name -eq '项目 A').NewCount) -eq 3)
    $j4 = pwsh -NoProfile -File $Script -Config $cfg -Json -Project paused | Out-String | ConvertFrom-Json
    Add-Content -LiteralPath (Join-Path $a 'docs/queue.md') -Value '' -Encoding utf8NoBOM
    G -C $a add docs/queue.md; G -C $a commit -q -m 'queue: claim'
    $ju = pwsh -NoProfile -File $Script -Config $cfg -Json -Project '项目 A' | Out-String | ConvertFrom-Json
    Check 'unreviewed: queue-only and empty commits not counted' ($ju.Projects[0].Unreviewed -eq 1)
    Set-Content -LiteralPath (Join-Path $a 'code.txt') -Value 'x' -Encoding utf8NoBOM
    Add-Content -LiteralPath (Join-Path $a 'docs/queue.md') -Value '' -Encoding utf8NoBOM
    G -C $a add code.txt docs/queue.md; G -C $a commit -q -m 'code and queue'
    $ju = pwsh -NoProfile -File $Script -Config $cfg -Json -Project '项目 A' | Out-String | ConvertFrom-Json
    Check 'unreviewed: a commit touching queue and other files counts' ($ju.Projects[0].Unreviewed -eq 2)
    Check '-Project includes paused' (($j4.Projects.Name -join ',') -eq 'paused' -and ($j4.Paused -join ',') -eq 'paused-gone（路径不存在）')
    $j5 = pwsh -NoProfile -File $Script -Config $cfg -Json -Project 'b, 项目 A' | Out-String | ConvertFrom-Json
    Check '-Project takes comma-separated names' (($j5.Projects.Name -join ',') -eq '项目 A,b')
    $null = pwsh -NoProfile -File $Script -Config $cfg -Project b extra 2>&1
    Check 'no positional parameters' ($LASTEXITCODE -ne 0)
    $empty = Join-Path $root 'hq/empty.json'
    Set-Content -LiteralPath $empty -Value '{}'
    $null = pwsh -NoProfile -File $Script -Config $empty 2>&1
    Check 'list without projects fails' ($LASTEXITCODE -ne 0)

    Push-Location (Split-Path $cfg)
    try { $j6 = & $Script -Config './projects.json' -Json | Out-String | ConvertFrom-Json } catch { $j6 = $null } finally { Pop-Location }
    Check 'relative -Config resolved against current location' ($j6 -and $j6.Projects.Count -eq 3)

    $t = pwsh -NoProfile -File $Script -Config $cfg | Out-String
    Check 'text summary line' ($t -match '推进中 2 · 维护 1 · 暂停 2；待用户合计 4（单向门 1 · 看一眼 2 · 自走 1）')
    Check 'text waiting line' ($t -match '待用户 #2 \[看一眼\] 看界面：等你看截图')
    Check 'maintenance is brief' ($t -notmatch '(?s)## b · 维护.*工作区')
    Check 'text available and goals' ($t -match '可领 3' -and $t -match '本周目标 2/3：✓ 目标一；○ 目标二；✓ 手动勾的 <x>')

    Check 'no shelved rows: no shelved count in text' ($t -notmatch '搁置')
    Check 'text hints for lessons due and pending requests' ($t -match '提示：教训 Seen 达到 3 还没升级：规则三该升级' -and $t -match '提示：还没转进队列的请求 2 条')
    Check 'all rows numbered: no missing-number hint' (-not ($pa.Problems -match '没有编号'))

    $c = Join-Path $root '项目 C'
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $c 'docs')
    G init -q $c
    @'
| # | 目标 | 依赖 | 状态 |
|---|---|---|---|
| 1 | 先放着 | 无 | 搁置（等数据） |
| 2 | 依赖搁置的项 | 1 | 待做 |
| 3 | 能领的项 | 无 | 待做 |
| 4 | 写法不对 | 无 | 暂停于安全点 |
| 5 | 做完了 | 无 | 完成 |
| 6 | 等别处 | 无 | 待用户（不急，等导图提出再开） |
| 7 | 长记录 | 无 | 待用户（LONGLOG） |
| 8 | 真问题一 | 无 | 待用户（要不要合并：推荐合并；等你说可以就合并、再做 #12） |
| 9 | 真问题二 | 无 | 待用户（要不要暂停 watch 的计划任务；A 简单但不急着要，推荐 A） |
| 10 | 用户先不改 | 无 | 待用户（用户："先不改，用一段时间再说"；等 2.6.1 用过一段时间、看停下的频率再定） |
| 11 | 真问题三 | 无 | 待用户（要不要合并：推荐合并，小问题合并后再说；要不要先停掉 watch；等您确认后合并） |
| 12 | 只写不急 | 无 | 待用户（不急） |

| 目标 | 状态 |
|---|---|
| 没编号等你 | 待用户（看报告） |
| 没编号在做 | 在做 |
| 没编号做完了 | 完成 |

| 项 | 状态 | 说明 / 提交 |
|---|---|---|
| 说明写在别列 | 待用户 | 本周暂停（用户：先停，等本周结果） |
| 说明只是历史 | 待用户（选 A 还是 B，推荐 A） | 11-01 搁置过，用户 11-05 恢复 |
'@ -replace 'LONGLOG', ('过程' * 160) | Set-Content -LiteralPath (Join-Path $c 'docs/queue.md') -Encoding utf8NoBOM
    G -C $c add -A; G -C $c commit -q -m 'c1'
    $cfgC = Join-Path $root 'projects-c.json'
    @{ projects = @(@{ name = '项目 C'; path = $c; status = '推进中' }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfgC -Encoding utf8NoBOM
    $pc = (pwsh -NoProfile -File $Script -Config $cfgC -Json | ConvertFrom-Json).Projects[0]
    $tc = pwsh -NoProfile -File $Script -Config $cfgC | Out-String
    $alias = Join-Path $root 'alias'
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $alias 'docs')
    G init -q $alias
    @'
| # | 目标 | 依赖 | 状态 |
|---|---|---|---|
| 1 | 甲 | 无 | 已合并（11-06） |
| 2 | 乙 | 无 | 已完成 |
| 3 | 丙 | 无 | 进行中（r2） |
| 4 | 丁 | 无 | 暂停（等数据） |
| 5 | 戊 | 无 | 暂停于安全点 |
| 6 | 己 | 无 | 部分已定：选了 A |
| 7 | 依赖暂停的项 | 4 | 待做 |
| 8 | 依赖已合并的项 | 1 | 待做 |
'@ | Set-Content -LiteralPath (Join-Path $alias 'docs/queue.md') -Encoding utf8NoBOM
    G -C $alias add -A; G -C $alias commit -q -m 'a1'
    $cfgAlias = Join-Path $root 'projects-alias.json'
    @{ projects = @(@{ name = '写法'; path = $alias; status = '推进中' }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfgAlias -Encoding utf8NoBOM
    $pAlias = (pwsh -NoProfile -File $Script -Config $cfgAlias -Json | ConvertFrom-Json).Projects[0]
    Check 'state aliases: counted as the standard state' ($pAlias.Queue.'完成' -eq 2 -and $pAlias.Queue.'在做' -eq 1 -and $pAlias.Queue.'搁置' -eq 1 -and (($pAlias.Doing | ForEach-Object Detail) -join ',') -eq 'r2')
    Check 'state aliases: pause at a safe point and unclear words are still reported' ((($pAlias.Other | ForEach-Object Id) -join ',') -eq '5,6' -and [bool]($pAlias.Problems -match '认不出.*#5.*#6') -and -not ($pAlias.Problems -match '认不出.*#[1-4]（'))
    Check 'state aliases: dependencies follow the standard state' ($pAlias.Next.Id -contains '8' -and $pAlias.Next.Id -notcontains '7')
    Check 'shelved: counted, not reported as unknown' ($pc.Queue.'搁置' -eq 1 -and $pc.Queue.'其他' -eq 1 -and -not ($pc.Problems -match '先放着|等数据') -and $tc -match '搁置 1')
    Check 'shelved: still an unknown state next to it is reported' ([bool]($pc.Problems -match '认不出.*#4'))
    Check 'shelved: not available, and blocks what depends on it' ($pc.Available -eq 1 -and $pc.Next[0].Id -eq '3')
    Check 'no number: open rows reported, done rows not' ([bool]($pc.Problems -match '没有编号的项：没编号等你、没编号在做、说明写在别列、说明只是历史$'))
    Check 'no lessons or requests file: nothing due, no hint' (-not $pc.LessonsDue -and -not $pc.Requests -and -not ($pc.Problems -match '教训|请求'))
    Check 'no number: no lone # in the text' ($tc -match '待用户 没编号等你：看报告' -and $tc -notmatch '# 没编号' -and $tc -notmatch '待用户 #\s')
    Check 'no runs dir: no dead runs' (-not $pc.DeadRuns -and -not ($pc.Problems -match '运行死了'))
    Check 'waiting hints: shelved-like, process log, plain ask untouched' ((($pc.Waiting | ForEach-Object { "$($_.Id)=$($_.Hint)" }) -join ';') -eq '6=像搁置;7=过程记录;8=;9=;10=像搁置;11=;12=像搁置;=;=像搁置;=' -and [bool]($pc.Problems -match '^待用户项像是搁置.*：#6、#10、#12、说明写在别列；') -and [bool]($pc.Problems -match '^待用户项的状态格写成了过程记录.*：#7；'))
    Check 'waiting hints: none on ordinary asks' (-not ($pa.Problems -match '^待用户项'))

    $dd = Join-Path $root '项目 D'
    G init -q $dd; G -C $dd commit -q --allow-empty -m 'd1'
    $self = Get-Process -Id $PID
    $gone = Start-Process -FilePath $self.Path -ArgumentList '-NoProfile -Command exit' -PassThru -WindowStyle Hidden
    $gone.WaitForExit()
    foreach ($case in @(@{ n = 'dead'; pid = $gone.Id; started = (Get-Date) }, @{ n = 'alive'; pid = $PID; started = $self.StartTime },
                        @{ n = 'reused'; pid = $PID; started = $self.StartTime.AddHours(-3) }, @{ n = 'old-dead'; pid = $gone.Id; started = (Get-Date).AddDays(-10) },
                        @{ n = 'finished'; pid = $gone.Id; started = (Get-Date); exit = $true },
                        @{ n = 'superseded'; pid = $gone.Id; started = (Get-Date).AddHours(-2); branch = 'b1' }, @{ n = 'redo'; pid = $gone.Id; started = (Get-Date).AddHours(-1); branch = 'b1'; exit = $true },
                        @{ n = 'last-on-branch'; pid = $gone.Id; started = (Get-Date).AddHours(-1); branch = 'b2' }, @{ n = 'earlier-on-branch'; pid = $gone.Id; started = (Get-Date).AddHours(-2); branch = 'b2'; exit = $true })) {
        $rd = Join-Path $dd ".agents/runs/$($case.n)"
        $null = New-Item -ItemType Directory -Force -Path $rd
        @{ Name = $case.n; Branch = $case.branch; Pid = $case.pid; Started = $case.started.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $rd 'meta.json') -Encoding utf8NoBOM
        if ($case.exit) { '{"ExitCode":0}' | Set-Content -LiteralPath (Join-Path $rd 'exit.json') }
    }
    $cfgD = Join-Path $root 'projects-d.json'
    @{ projects = @(@{ name = '项目 D'; path = $dd; status = '推进中' }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfgD -Encoding utf8NoBOM
    $pd = (pwsh -NoProfile -File $Script -Config $cfgD -Json | ConvertFrom-Json).Projects[0]
    Check 'dead runs: no exit record and process gone or reused; not alive, finished, older than 7 days or redone on the same branch' ((@($pd.DeadRuns | Sort-Object) -join ',') -eq 'dead,last-on-branch,reused')
    Check 'dead runs: reported as a hint' (@($pd.Problems | Where-Object { $_ -match '^派出去的运行死了（没有退出记录，进程也不在）：' -and $_ -match '\bdead\b' -and $_ -match 'reused' -and $_ -match 'last-on-branch' -and $_ -notmatch 'superseded' }).Count -eq 1)

    $pageC = Join-Path $root 'out/status-c.html'
    $null = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'daily.ps1') -Config $cfgC -Out $pageC -NoNotify
    $htmlC = Get-Content -LiteralPath $pageC -Raw -Encoding UTF8
    Check 'daily: shelved left out of progress, shown in the details' ($htmlC -match '完成 2 / 共 16 项' -and $htmlC -match '&#183; 搁置 1')
    Check 'daily: shelved-like ask still listed, marked, with the command to shelve it' ($htmlC -match '等你定 #6 等别处（像已搁置）' -and $htmlC -match '<code>/next #6 改成搁置</code>' -and $htmlC -match '<code>/next #6 你的答复</code>')
    $ncC = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'daily.ps1') -Config $cfgC -Out $pageC -State (Join-Path $root 'out/daily-c.json') -DryRun | Out-String
    Check 'daily: shelved-like asks still counted, real asks listed first' ($ncC -match '要你管 10 件事' -and $ncC -match 'body: 项目 C：#7 长记录 等你定' -and $ncC -match '#8 真问题一 等你定' -and $ncC -match '另有 5 件等你定' -and $ncC -notmatch '像已搁置')
    $wc = pwsh -NoProfile -File (Join-Path (Split-Path $Script) 'watch.ps1') -Config $cfgC -State (Join-Path $root 'out/watch-c.json') -StaleMinutes 0 -DryRun | Out-String
    Check 'watch: no lone # for an unnumbered item' ($wc -match '项目 C：没编号在做' -and $wc -notmatch '# 没编号')

    $daily = Join-Path (Split-Path $Script) 'daily.ps1'
    $page = Join-Path $root 'out/status.html'
    $null = pwsh -NoProfile -File $daily -Config $cfg -Out $page -NoNotify
    $html = if (Test-Path -LiteralPath $page) { Get-Content -LiteralPath $page -Raw -Encoding UTF8 } else { '' }
    Check 'daily: page written' ($LASTEXITCODE -eq 0 -and $html -match '<title>项目状态</title>')
    Check 'daily: waiting items in plain words with how to answer' ($html -match '<b>项目 A</b> 等你定 #2 看界面：等你看截图' -and $html -match '/next #2 你的答复')
    Check 'daily: one-line summary, raw queue hints folded away' ($html -match '<p class="lead">要你管 4 件事；项目 A：等你' -and $html -match '1 项的状态写法不标准' -and $html -notmatch '队列里状态认不出')
    Check 'daily: fixed rows now, progress, next, recent' ($html -match '<div class="k">现在</div><div>#4 跑回归</div>' -and $html -match '完成 1 / 共 13 项' -and $html -match '<div class="k">接下来</div><div>#8 依赖已完成<br>#11 没有依赖<br>#12 依赖的项已删</div>' -and $html -match '<div class="k">最近完成</div><div>#1 写 a')
    Check 'daily: goals section' ($html -match '② 本周目标' -and $html -match '完成 2/3')
    Check 'daily: goal cells wrap long paths and links' ($html -match '\.goals>\*\{min-width:0;overflow-wrap:anywhere\}')
    Check 'daily: html escaped' ($html -match '手动勾的 &lt;x&gt;' -and $html -notmatch '<x>')
    $nd = pwsh -NoProfile -File $daily -Config $cfg -Out $page -DryRun | Out-String
    Check 'daily: notification title and plain lines' ($nd -match 'title: 🟡 要你管 4 件事' -and $nd -match '项目 A：#2 看界面 等你定' -and $nd -match '项目 A：#7 围栏后的真表 等你定' -and $nd -match 'bark: (yes|no)')
    $ns = pwsh -NoProfile -File $daily -Config $cfg -Out $page -DryRun -StaleMinutes 0 | Out-String
    Check 'daily: stalled item named in the notification' ($ns -match '项目 A：#4 跑回归 已 .*没动静，可能停了')
    Push-Location $root
    try { $null = pwsh -NoProfile -File $daily -Config $cfg -Out 'bare.html' -NoNotify } finally { Pop-Location }
    Check 'daily: bare -Out file name' ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path $root 'bare.html')))

    $notify = Join-Path (Split-Path $Script) 'notify.ps1'
    $ncfg = Join-Path $root 'hq/notify.json'
    '{ "bark": "https://example.invalid/secret-key", "barkLevels": ["user", "stuck"] }' | Set-Content -LiteralPath $ncfg
    $n1 = pwsh -NoProfile -File $notify -Config $ncfg -Title 'p' -Body 'b' -Level done -DryRun | Out-String
    $n2 = pwsh -NoProfile -File $notify -Config $ncfg -Title 'p' -Body 'b' -Level stuck -DryRun | Out-String
    Check 'notify: done stays on the desktop, stuck goes to the phone' ($n1 -match 'bark: no' -and $n2 -match 'bark: yes' -and $n2 -match 'title: 🔴 p')
    Check 'notify: dry run never prints the key' ($n1 + $n2 -notmatch 'secret-key')
    $n3 = '{"cwd":"C:\\x\\项目 A","message":"needs permission"}' | pwsh -NoProfile -File $notify -Config $ncfg -Hook -DryRun | Out-String
    Check 'notify: hook event gives project and message, desktop only' ($n3 -match 'title: 项目 A' -and $n3 -match 'body: needs permission' -and $n3 -match 'bark: no')
    $null = pwsh -NoProfile -File $notify -Config $ncfg -Title 'p' -Level urgent -DryRun 2>&1
    Check 'notify: unknown level fails' ($LASTEXITCODE -ne 0)
    $n4 = '{"cwd":"C:\\x\\项目 A","message":"Claude is waiting for your input","notification_type":"idle_prompt"}' | pwsh -NoProfile -File $notify -Config $ncfg -Hook -DryRun | Out-String
    Check 'notify: idle reminder is dropped' ($n4 -match 'skip: idle_prompt' -and $n4 -notmatch 'toast:')
    $n5 = '{"cwd":"C:\\x\\项目 A","message":"x","notification_type":"quota_auto_resume_stale"}' | pwsh -NoProfile -File $notify -Config $ncfg -Hook -DryRun | Out-String
    Check 'notify: missed auto-resume goes to the phone in plain words' ($n5 -match 'bark: yes' -and $n5 -match 'title: 🔴 项目 A' -and $n5 -match 'body: 额度已经重置.*按回车')
    $n6 = '{"cwd":"C:\\x\\项目 A","message":"Claude needs your permission","notification_type":"permission_prompt"}' | pwsh -NoProfile -File $notify -Config $ncfg -Hook -DryRun | Out-String
    Check 'notify: permission prompt stays on the desktop' ($n6 -match 'toast: yes' -and $n6 -match 'bark: no' -and $n6 -match 'body: Claude needs your permission')
    $n7 = '{"cwd":"C:\\x\\项目 A","message":"Bash 要你批准","notification_type":"agent_needs_input"}' | pwsh -NoProfile -File $notify -Config $ncfg -Hook -DryRun | Out-String
    Check 'notify: background session waiting on you goes to the phone and says where to answer' ($n7 -match 'bark: yes' -and $n7 -match 'title: 🟡 项目 A' -and $n7 -match 'body: 后台会话在等你：Bash 要你批准.*claude agents')
    $n8 = '{"cwd":"C:\\x\\项目 A","message":"done","notification_type":"agent_completed"}' | pwsh -NoProfile -File $notify -Config $ncfg -Hook -DryRun | Out-String
    Check 'notify: background session finished stays on the desktop' ($n8 -match 'toast: yes' -and $n8 -match 'bark: no')

    $watch = Join-Path (Split-Path $Script) 'watch.ps1'
    $wstate = Join-Path $root 'out/watch-state.json'
    $wq = Join-Path $root 'hq/quiet.json'
    '{ "toast": false }' | Set-Content -LiteralPath $wq
    $w0 = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -DryRun | Out-String
    Check 'watch: nothing stalled, nothing sent' ($w0 -match 'no new stall' -and -not (Test-Path -LiteralPath $wstate))
    $env:AI_DEV_FLOW_NOTIFY = $ncfg
    $w1 = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -StaleMinutes 0 -DryRun | Out-String
    Check 'watch: new stall goes to the phone with what to do' ($w1 -match 'title: 🔴 1 个项目可能停了' -and $w1 -match 'bark: yes' -and $w1 -match '项目 A：#4 跑回归 已 .*没动静.*/next')
    Check 'watch: dry run keeps no state' (-not (Test-Path -LiteralPath $wstate))
    $env:AI_DEV_FLOW_NOTIFY = $wq
    $null = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -StaleMinutes 0
    Check 'watch: sent stall is remembered' ($LASTEXITCODE -eq 0 -and (Get-Content -LiteralPath $wstate -Raw) -match '项目 A\|4\|')
    $w2 = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -StaleMinutes 0 -DryRun | Out-String
    Check 'watch: same stall is not sent again' ($w2 -match 'no new stall')
    $null = pwsh -NoProfile -File $watch -Config $cfg -State $wstate
    $w3 = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -StaleMinutes 0 -DryRun | Out-String
    Check 'watch: stall after it cleared is sent again' ($w3 -match '可能停了')
    '{"stalled":[' | Set-Content -LiteralPath $wstate
    $w4 = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -StaleMinutes 0 -DryRun 2>$null | Out-String
    $null = pwsh -NoProfile -File $watch -Config $cfg -State $wstate -StaleMinutes 0 2>$null
    Check 'watch: broken state file does not stop alerts and is rewritten' ($w4 -match '可能停了' -and $LASTEXITCODE -eq 0 -and (Get-Content -LiteralPath $wstate -Raw) -match '项目 A\|4\|' -and -not (Test-Path -LiteralPath "$wstate.tmp"))
    $dstate = Join-Path $root 'out/daily-state.json'
    $env:AI_DEV_FLOW_NOTIFY = $ncfg
    $d1 = pwsh -NoProfile -File $daily -Config $cfg -Out $page -State $dstate -DryRun | Out-String
    Check 'daily: first push goes to the phone, dry run keeps no state' ($d1 -match 'bark: yes' -and $d1 -notmatch '新：' -and -not (Test-Path -LiteralPath $dstate))
    $env:AI_DEV_FLOW_NOTIFY = $wq
    $null = pwsh -NoProfile -File $daily -Config $cfg -Out $page -State $dstate
    Check 'daily: pushed asks are remembered' ($LASTEXITCODE -eq 0 -and (Get-Content -LiteralPath $dstate -Raw -Encoding UTF8) -match '项目 A\|#2\|看界面')
    $env:AI_DEV_FLOW_NOTIFY = $ncfg
    $d2 = pwsh -NoProfile -File $daily -Config $cfg -Out $page -State $dstate -DryRun | Out-String
    Check 'daily: same asks again stay on the desktop' ($d2 -match 'bark: no' -and $d2 -match 'title: .*要你管 4 件事（都推过）')
    $qa = Join-Path $a 'docs/queue.md'
    $qaText = Get-Content -LiteralPath $qa -Raw -Encoding UTF8
    $qaText -replace '（等你看截图）', '（换了个问题：看新截图）' | Set-Content -LiteralPath $qa -Encoding utf8NoBOM -NoNewline
    $d2b = pwsh -NoProfile -File $daily -Config $cfg -Out $page -State $dstate -DryRun | Out-String
    Check 'daily: same item with a new question goes to the phone again' ($d2b -match 'bark: yes' -and $d2b -match '新：项目 A：#2 看界面')
    $qaText | Set-Content -LiteralPath $qa -Encoding utf8NoBOM -NoNewline
    (Get-Content -LiteralPath (Join-Path $a 'docs/queue.md') -Raw -Encoding UTF8) -replace '\| 11 \| 没有依赖 \| 绿 \| 自走 \| 无 \| 待做 \|', '| 11 | 没有依赖 | 绿 | 自走 | 无 | 待用户（新问题） |' | Set-Content -LiteralPath (Join-Path $a 'docs/queue.md') -Encoding utf8NoBOM -NoNewline
    $d3 = pwsh -NoProfile -File $daily -Config $cfg -Out $page -State $dstate -DryRun | Out-String
    Check 'daily: a new ask goes to the phone, marked and listed first' ($d3 -match 'bark: yes' -and $d3 -match '(?s)body: 新：项目 A：#11 没有依赖 等你定.*项目 A：#2' -and $d3 -notmatch '新：项目 A：#2')
    '{"pushed":[' | Set-Content -LiteralPath $dstate
    $d4 = pwsh -NoProfile -File $daily -Config $cfg -Out $page -State $dstate -DryRun 2>$null | Out-String
    Check 'daily: broken state file still pushes' ($d4 -match 'bark: yes')
    Remove-Item Env:AI_DEV_FLOW_NOTIFY

    $e = Join-Path $root '项目 E'
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $e 'docs')
    G init -q $e
    "| # | 目标 | 依赖 | 状态 |`n|---|---|---|---|`n| 1 | 能领 | 无 | 待做 |" | Set-Content -LiteralPath (Join-Path $e 'docs/queue.md') -Encoding utf8NoBOM
    G -C $e add -A; G -C $e commit -q -m 'e1'
    $cfgE = Join-Path $root 'projects-e.json'
    @{ projects = @(@{ name = '项目 E'; path = $e; status = '推进中' }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $cfgE -Encoding utf8NoBOM
    $pageE = Join-Path $root 'out/status-e.html'
    $e1 = pwsh -NoProfile -File $daily -Config $cfgE -Out $pageE -State (Join-Path $root 'out/daily-e.json') -DryRun | Out-String
    $htmlE = Get-Content -LiteralPath $pageE -Raw -Encoding UTF8
    Check 'daily: recent activity without work in progress is not idle' ($htmlE -match '刚有动静' -and $htmlE -match '<div class="k">现在</div><div>刚有动静（' -and $htmlE -notmatch '空着' -and $e1 -notmatch '空着')
    $e2 = pwsh -NoProfile -File $daily -Config $cfgE -Out $pageE -State (Join-Path $root 'out/daily-e.json') -StaleMinutes 0 -DryRun | Out-String
    Check 'daily: quiet past -StaleMinutes is idle again' ($e2 -match '项目 E 空着，可以发 /next 开工')
    $null = pwsh -NoProfile -File $Script -Config (Join-Path $root 'missing.json') 2>&1
    Check 'missing config fails' ($LASTEXITCODE -ne 0)
    $null = pwsh -NoProfile -File $Script -Config $cfg -Project nobody 2>&1
    Check 'unknown -Project fails' ($LASTEXITCODE -ne 0)
}
finally {
    if ($Keep) { "kept: $root" } else {
    Get-ChildItem -LiteralPath $root -Recurse -Force | ForEach-Object { $_.Attributes = 'Normal' }
    Remove-Item -LiteralPath $root -Recurse -Force }
}
if ($fail) { "$fail check(s) failed"; exit 1 } else { 'all checks passed'; exit 0 }

