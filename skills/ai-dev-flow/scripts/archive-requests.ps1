[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Repo = '.',
    [switch]$DryRun
)
# 把 docs/requests.md 里处理完的小节整段移到 docs/requests-done.md，主文件只留还要转的，/next 开场只读主文件（skills/next/SKILL.md 第 1 节）。
#   -Repo    项目目录，默认当前目录
#   -DryRun  只说会移哪些，不改文件
# 只移状态明确处理完的：以 已转、已处理、已答复、已完成、完成、不做 开头。待转、没写状态、写法说不准的（进行中、通知……）留着，
# 猜错了顶多多读几段，不会把没转的请求藏起来（docs/code-standards.md 第 1 条）。
# 移走的接在 requests-done.md 末尾，原文不改；文件没有就新建。不提交，由调用的会话单独提交（requests: archive handled items）。
# 退出码：0 做完了（没有要移的也是 0）；2 参数或文件不对。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$file = Join-Path $Repo 'docs/requests.md'
$done = Join-Path $Repo 'docs/requests-done.md'
if (-not (Test-Path -LiteralPath $Repo -PathType Container)) { [Console]::Error.WriteLine("archive-requests.ps1: 找不到目录：$Repo"); exit 2 }
if (-not (Test-Path -LiteralPath $file)) { '没有 docs/requests.md，不用移'; exit 0 }

$utf8 = [Text.UTF8Encoding]::new($false)
$text = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $file).ProviderPath, $utf8)
$nl = if ($text -match "`r`n") { "`r`n" } else { "`n" }
$parts = @($text -split '(?m)^(?=##\s)')
$head = if ($parts.Count -and $parts[0] -notmatch '^##\s') { $parts[0] } else { '' }
$sections = @($parts | Where-Object { $_ -match '^##\s' })
$stateRe = '(?m)^\s*(?:[-*]\s*)?\**状态\**\s*[：:]\s*\**\s*(.*?)\s*$'
$handled = '^(已转|已处理|已答复|已完成|完成|不做)'
$keep = [Collections.Generic.List[string]]::new()
$move = [Collections.Generic.List[string]]::new()
foreach ($sec in $sections) {
    $m = [regex]::Match($sec, $stateRe)
    if ($m.Success -and $m.Groups[1].Value -match $handled) { $move.Add($sec) } else { $keep.Add($sec) }
}
if (-not $move.Count) { '没有要移的'; exit 0 }
$titles = $move | ForEach-Object { (($_ -split '\r?\n')[0] -replace '^##\s+', '').Trim() }
if ($DryRun) { "会移 $($move.Count) 条到 docs/requests-done.md："; $titles | ForEach-Object { "  $_" }; exit 0 }

function Ends([string]$s) { if ($s -and -not $s.EndsWith("`n")) { $s + $nl } else { $s } }
$moved = (($move | ForEach-Object { Ends $_ }) -join '')
if (Test-Path -LiteralPath $done) {
    $old = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $done).ProviderPath, $utf8)
    $sep = if ($old.EndsWith("$nl$nl") -or -not $old) { '' } elseif ($old.EndsWith("`n")) { $nl } else { "$nl$nl" }
    $new = $old + $sep + $moved
} else {
    $new = "# 处理过的请求$nl$nl从 ``docs/requests.md`` 移来的、已经转进队列或处理完的请求，原文照留，按移来的先后排。``/next`` 开场不读这份，要查当初怎么定的再来搜。$nl$nl" + $moved
}
$rest = $head + (($keep | ForEach-Object { Ends $_ }) -join '')
[IO.File]::WriteAllText([IO.Path]::GetFullPath($done), $new, $utf8)
[IO.File]::WriteAllText((Resolve-Path -LiteralPath $file).ProviderPath, $rest, $utf8)
"移了 $($move.Count) 条到 docs/requests-done.md，主文件留 $($keep.Count) 条："
$titles | ForEach-Object { "  $_" }
exit 0
