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
| 5 | 拼写错 | 绿 | 自走 | 无 | 进行中 |
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
"@ | Set-Content -LiteralPath (Join-Path $a 'LESSONS.md') -Encoding utf8NoBOM
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
    Check 'lessons with seen' ((($pa.Lessons | ForEach-Object { "$($_.Seen):$($_.Title)" }) -join ';') -eq '2:规则一;1:规则二')
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
    Check 'mark: only commits after it' ($pa2.NewCount -eq 1 -and $pa2.NewSince -like '自上次标记*')
    $j3 = pwsh -NoProfile -File $Script -Config $cfg -Json -Since '2000-01-01' | Out-String | ConvertFrom-Json
    Check 'stale only past -StaleMinutes' (-not (($j2.Projects | Where-Object Name -eq '项目 A').Problems -match '^可能停滞'))
    $js = pwsh -NoProfile -File $Script -Config $cfg -Json -StaleMinutes 0 | Out-String | ConvertFrom-Json
    Check 'stalled: active project with work in progress and no activity' ([bool](($js.Projects | Where-Object Name -eq '项目 A').Problems -match '^可能停滞：在做 1 项') -and -not (($js.Projects | Where-Object Name -eq 'b').Problems -match '^可能停滞'))
    Check '-Since overrides mark' ((($j3.Projects | Where-Object Name -eq '项目 A').NewCount) -eq 3)
    $j4 = pwsh -NoProfile -File $Script -Config $cfg -Json -Project paused | Out-String | ConvertFrom-Json
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

    $daily = Join-Path (Split-Path $Script) 'daily.ps1'
    $page = Join-Path $root 'out/status.html'
    $null = pwsh -NoProfile -File $daily -Config $cfg -Out $page -NoNotify
    $html = if (Test-Path -LiteralPath $page) { Get-Content -LiteralPath $page -Raw -Encoding UTF8 } else { '' }
    Check 'daily: page written' ($LASTEXITCODE -eq 0 -and $html -match '<title>项目状态</title>')
    Check 'daily: waiting items in plain words with how to answer' ($html -match '<b>项目 A</b> #2 看界面：等你看截图' -and $html -match '/next #2 你的答复')
    Check 'daily: one-line summary, raw queue hints folded away' ($html -match '有 4 件事等你定' -and $html -match '正在做：#4 跑回归' -and $html -match '1 项的状态写法不标准' -and $html -notmatch '队列里状态认不出')
    Check 'daily: html escaped' ($html -match '手动勾的 &lt;x&gt;' -and $html -notmatch '<x>')
    $nd = pwsh -NoProfile -File $daily -Config $cfg -Out $page -DryRun | Out-String
    Check 'daily: notification title and plain lines' ($nd -match 'title: 🟡 要你管 4 件事' -and $nd -match '项目 A：#2 看界面 等你定' -and $nd -match '另有 2 件等你定' -and $nd -match 'bark: (yes|no)')
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

