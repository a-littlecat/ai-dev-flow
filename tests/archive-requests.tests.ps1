param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/archive-requests.ps1'))
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Script = (Resolve-Path -LiteralPath $Script).ProviderPath
$root = Join-Path ([IO.Path]::GetTempPath()) "archive-requests-tests-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function Run([string]$repo, [string[]]$a = @()) { $o = @(pwsh -NoProfile -File $Script -Repo $repo @a 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Text = ($o -join "`n"); Code = $LASTEXITCODE } }
$utf8 = [Text.UTF8Encoding]::new($false)
function Put([string]$path, [string]$text) { $null = New-Item -ItemType Directory -Force -Path (Split-Path $path); [IO.File]::WriteAllText($path, $text, $utf8) }
function Get([string]$path) { [IO.File]::ReadAllText($path, $utf8) }
function Lf([string]$s) { $s -replace "`r?`n", "`n" }

$sample = Lf @'
# 收到的请求

开头的说明。

## 2026-11-01 已转的

- **现象**：甲
- **状态**：已转（队列 #3）

## 2026-11-02 还要转

- **状态**：待转

## 2026-11-03 没写状态

- **请求**：乙

## 2026-11-04 处理完的

### 细节

- **状态**：已处理（2.6.0）：
  1. 做了

## 2026-11-05 说不准的

- **状态**：进行中（平面批 1）

## 2026-11-06 不做的

- **状态**：不做（理由）

## 2026-11-07 通知

- **状态**：通知

## 2026-11-08 先待转后已转

- **状态**：待转
- **状态**：已转（队列 #1）

## 2026-11-09 词不在开头

- **状态**：待转（原已转）

## 2026-11-11 前面有字

- **状态**：原先已转（队列 #3）
'@
$header = "# 处理过的请求`n`n从 ``docs/requests.md`` 移来的、已经转进队列或处理完的请求，原文照留，按移来的先后排。``/next`` 开场不读这份，要查当初怎么定的再来搜。`n`n"
$pointer = '处理完的小节移到了 `docs/requests-done.md`，按日期引用在这里找不到的去那里找。'

try {
    $a = Join-Path $root 'a'
    Put (Join-Path $a 'docs/requests.md') $sample
    $r = Run $a @('-DryRun')
    Check 'dry run: lists what it would move with the state, changes nothing' ($r.Code -eq 0 -and $r.Text -match '会移 3 条' -and $r.Text -match '已转的（状态：已转（队列 #3））' -and (Get (Join-Path $a 'docs/requests.md')) -eq $sample -and -not (Test-Path (Join-Path $a 'docs/requests-done.md')))

    $r = Run $a
    $main = Get (Join-Path $a 'docs/requests.md')
    $done = Get (Join-Path $a 'docs/requests-done.md')
    Check 'exit 0, says how many moved' ($r.Code -eq 0 -and $r.Text -match '移了 3 条' -and $r.Text -match '主文件留 7 条')
    Check 'handled ones moved: 已转, 已处理, 不做' ($done -match '## 2026-11-01 已转的' -and $done -match '## 2026-11-04 处理完的' -and $done -match '## 2026-11-06 不做的' -and $main -notmatch '## 2026-11-0[146] ')
    Check 'pending, unset, unclear and 通知 stay' ($main -match '还要转' -and $main -match '没写状态' -and $main -match '说不准的' -and $main -match '11-07 通知' -and $done -notmatch '还要转|没写状态|说不准的|11-07')
    Check 'state is the first 状态 line; a later 已转 does not count' ($main -match '先待转后已转' -and $done -notmatch '先待转后已转')
    Check 'state word not at the start does not count' ($main -match '词不在开头' -and $main -match '前面有字')
    Check 'archive header is whole' ($done.StartsWith($header))
    Check 'moved text kept word for word with its ### heading, in order, one blank line apart' ($done -eq ($header + "## 2026-11-01 已转的`n`n- **现象**：甲`n- **状态**：已转（队列 #3）`n`n## 2026-11-04 处理完的`n`n### 细节`n`n- **状态**：已处理（2.6.0）：`n  1. 做了`n`n## 2026-11-06 不做的`n`n- **状态**：不做（理由）`n"))
    Check 'main file: preamble, pointer, then kept sections in order' ($main.StartsWith("# 收到的请求`n`n开头的说明。`n`n$pointer`n`n## 2026-11-02 还要转`n`n- **状态**：待转`n`n## 2026-11-03 没写状态") -and $main.IndexOf('11-05') -lt $main.IndexOf('11-07') -and $main.IndexOf('11-07') -lt $main.IndexOf('11-09') -and $main.EndsWith("原先已转（队列 #3）`n"))

    Put (Join-Path $a 'docs/requests.md') ($main + "`n## 2026-11-10 后来转的`n`n- **状态**：已转（队列 #9）")
    $r = Run $a
    $done2 = Get (Join-Path $a 'docs/requests-done.md')
    $main2 = Get (Join-Path $a 'docs/requests.md')
    Check 'second run appends one blank line after the old archive' ($r.Code -eq 0 -and $done2 -eq ($done + "`n## 2026-11-10 后来转的`n`n- **状态**：已转（队列 #9）`n"))
    Check 'second run: pointer not added twice' (([regex]::Matches($main2, 'requests-done\.md')).Count -eq 1)
    Check 'nothing left to move: says so' ((Run $a).Text -match '没有要移的')

    $u = Join-Path $root 'unsure'
    Put (Join-Path $u 'docs/requests.md') (Lf @'
## 一

- **状态**：不做？等用户定

## 二

- **状态**：已转（#1）；第 2 条待转

## 三

- **状态**：完成了吗？

## 四

- **状态**：已转？

## 五

- **状态**：已转（队列 #3、#4）；等用户确认

## 六

- **状态**：已完成部分
'@)
    $r = Run $u @('-DryRun')
    Check 'unsure handled-looking states stay' ($r.Code -eq 0 -and $r.Text -match '没有要移的')

    $f = Join-Path $root 'fence'
    $fenced = Lf @'
# 请求

## 待转的带代码块

```
## 这不是小节
```

- **状态**：待转

## 已转的带代码块

~~~
## 也不是
~~~

- **状态**：已转（队列 #2）

## 已转但代码块没闭合

```
没闭合
- **状态**：已转（队列 #5）
'@
    Put (Join-Path $f 'docs/requests.md') $fenced
    $r = Run $f
    $mf = Get (Join-Path $f 'docs/requests.md'); $df = Get (Join-Path $f 'docs/requests-done.md')
    Check '## inside a code block is not a section' ($mf -match "## 待转的带代码块`n`n```````n## 这不是小节`n```````n`n- \*\*状态\*\*：待转" -and $df -match "~~~`n## 也不是`n~~~`n`n- \*\*状态\*\*：已转（队列 #2）")
    Check 'unclosed code block: section kept and reported' ($mf -match '已转但代码块没闭合' -and $df -notmatch '没闭合' -and $r.Text -match '没闭合.*看一眼')

    $b = Join-Path $root 'b'
    Put (Join-Path $b 'docs/requests.md') ($sample -replace "`n", "`r`n")
    $r = Run $b
    $mb = Get (Join-Path $b 'docs/requests.md'); $db = Get (Join-Path $b 'docs/requests-done.md')
    Check 'CRLF file: both files stay CRLF' ($r.Code -eq 0 -and $mb -notmatch "[^`r]`n" -and $db -notmatch "[^`r]`n" -and $db -match "`r`n")

    $w = Join-Path $root 'where'
    $other = Join-Path $root 'other'
    Put (Join-Path $w 'docs/requests.md') $sample
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $other 'docs')
    $o = @(pwsh -NoProfile -Command "[Environment]::CurrentDirectory = '$other'; Set-Location -LiteralPath '$w'; & '$Script' -Repo ." 2>&1)
    Check 'relative -Repo follows the PowerShell location, not the process directory' ((Test-Path (Join-Path $w 'docs/requests-done.md')) -and -not (Test-Path (Join-Path $other 'docs/requests-done.md')))

    $g = Join-Path $root 'git'
    Put (Join-Path $g 'docs/requests.md') $sample
    $null = git -C $g init -q; $null = git -C $g -c user.name=t -c user.email=t@t -c core.autocrlf=false add -A; $null = git -C $g -c user.name=t -c user.email=t@t commit -qm init
    Put (Join-Path $g 'docs/requests.md') ($sample + "`n## 刚写的`n`n- **状态**：待转`n")
    $r = Run $g
    Check 'uncommitted change in the requests file: skipped, nothing moved' ($r.Code -eq 0 -and $r.Text -match '未提交' -and -not (Test-Path (Join-Path $g 'docs/requests-done.md')) -and (Get (Join-Path $g 'docs/requests.md')) -match '刚写的')
    $null = git -C $g -c user.name=t -c user.email=t@t commit -qam more
    $r = Run $g
    Check 'committed: moves as usual' ($r.Code -eq 0 -and $r.Text -match '移了 3 条')

    $c = Join-Path $root 'c'
    $null = New-Item -ItemType Directory -Force -Path $c
    $r = Run $c
    Check 'no requests file: exit 0, nothing created' ($r.Code -eq 0 -and -not (Test-Path (Join-Path $c 'docs')))
    $d = Join-Path $root 'd'
    Put (Join-Path $d 'docs/requests.md') "# 收到的请求`n`n## 一条`n`n- **状态**：待转`n"
    $r = Run $d
    Check 'only pending: no archive, main file untouched' ($r.Code -eq 0 -and $r.Text -match '没有要移的' -and -not (Test-Path (Join-Path $d 'docs/requests-done.md')) -and (Get (Join-Path $d 'docs/requests.md')) -eq "# 收到的请求`n`n## 一条`n`n- **状态**：待转`n")
    $r = Run (Join-Path $root 'nowhere')
    Check 'missing folder: exit 2' ($r.Code -eq 2)
} finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
if ($fail) { "$fail failed"; exit 1 }
'all passed'
exit 0
