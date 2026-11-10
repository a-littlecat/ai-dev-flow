param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/archive-requests.ps1'))
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) "archive-requests-tests-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function Run([string]$repo, [string[]]$a = @()) { $o = @(pwsh -NoProfile -File $Script -Repo $repo @a 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Text = ($o -join "`n"); Code = $LASTEXITCODE } }
$utf8 = [Text.UTF8Encoding]::new($false)
function Put([string]$path, [string]$text) { $null = New-Item -ItemType Directory -Force -Path (Split-Path $path); [IO.File]::WriteAllText($path, $text, $utf8) }
function Get([string]$path) { [IO.File]::ReadAllText($path, $utf8) }

$sample = @'
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

- **状态**：已处理（2.6.0）：
  1. 做了

## 2026-11-05 说不准的

- **状态**：进行中（平面批 1）

## 2026-11-06 不做的

- **状态**：不做（理由）
'@

try {
    $a = Join-Path $root 'a'
    Put (Join-Path $a 'docs/requests.md') ($sample -replace "`r?`n", "`n")
    $before = Get (Join-Path $a 'docs/requests.md')
    $r = Run $a @('-DryRun')
    Check 'dry run: lists what it would move, changes nothing' ($r.Code -eq 0 -and $r.Text -match '会移 3 条' -and (Get (Join-Path $a 'docs/requests.md')) -eq $before -and -not (Test-Path (Join-Path $a 'docs/requests-done.md')))

    $r = Run $a
    $main = Get (Join-Path $a 'docs/requests.md')
    $done = Get (Join-Path $a 'docs/requests-done.md')
    Check 'exit 0, says how many moved' ($r.Code -eq 0 -and $r.Text -match '移了 3 条' -and $r.Text -match '主文件留 3 条')
    Check 'handled ones moved: 已转, 已处理, 不做' ($done -match '## 2026-11-01 已转的' -and $done -match '## 2026-11-04 处理完的' -and $done -match '## 2026-11-06 不做的' -and $main -notmatch '已转的|处理完的|不做的')
    Check 'pending, no status and unclear ones stay' ($main -match '## 2026-11-02 还要转' -and $main -match '## 2026-11-03 没写状态' -and $main -match '## 2026-11-05 说不准的' -and $done -notmatch '还要转|没写状态|说不准的')
    Check 'preamble stays in the main file' ($main.StartsWith("# 收到的请求`n`n开头的说明。`n`n## "))
    Check 'moved text kept word for word, in order' ($done.Contains("## 2026-11-04 处理完的`n`n- **状态**：已处理（2.6.0）：`n  1. 做了`n") -and $done.IndexOf('11-01') -lt $done.IndexOf('11-04') -and $done.IndexOf('11-04') -lt $done.IndexOf('11-06'))
    Check 'new archive gets a header' ($done.StartsWith('# 处理过的请求'))
    Check 'last section without a newline still separated' ($done.EndsWith("（理由）`n") -or $done.EndsWith("（理由）"))

    Put (Join-Path $a 'docs/requests.md') ($main + "`n## 2026-11-07 后来转的`n`n- **状态**：已转（队列 #9）`n")
    $r = Run $a
    $done2 = Get (Join-Path $a 'docs/requests-done.md')
    Check 'second run appends to the archive, keeps the old' ($r.Code -eq 0 -and $done2.StartsWith($done.TrimEnd("`n")) -and $done2 -match '## 2026-11-07 后来转的' -and $done2 -notmatch "`n`n`n")
    Check 'nothing left to move: says so, no change' ((Run $a).Text -match '没有要移的')

    $b = Join-Path $root 'b'
    Put (Join-Path $b 'docs/requests.md') ($sample -replace "`r?`n", "`r`n")
    $r = Run $b
    $mb = Get (Join-Path $b 'docs/requests.md'); $db = Get (Join-Path $b 'docs/requests-done.md')
    Check 'CRLF file: both files stay CRLF' ($r.Code -eq 0 -and $mb -notmatch "[^`r]`n" -and $db -notmatch "[^`r]`n" -and $db -match "`r`n")

    $c = Join-Path $root 'c'
    $null = New-Item -ItemType Directory -Force -Path $c
    $r = Run $c
    Check 'no requests file: exit 0, nothing created' ($r.Code -eq 0 -and -not (Test-Path (Join-Path $c 'docs')))
    $d = Join-Path $root 'd'
    Put (Join-Path $d 'docs/requests.md') "# 收到的请求`n`n## 一条`n`n- **状态**：待转`n"
    $r = Run $d
    Check 'only pending: no archive file created' ($r.Code -eq 0 -and $r.Text -match '没有要移的' -and -not (Test-Path (Join-Path $d 'docs/requests-done.md')))
    $r = Run (Join-Path $root 'nowhere')
    Check 'missing folder: exit 2' ($r.Code -eq 2)
} finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
if ($fail) { "$fail failed"; exit 1 }
'all passed'
exit 0
