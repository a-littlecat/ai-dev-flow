[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Repo = '.',
    [switch]$DryRun
)
# 把 docs/requests.md 里处理完的小节整段移到 docs/requests-done.md，主文件只留还要转的，/next 开场只读主文件（skills/next/SKILL.md 第 1 节）。
#   -Repo    项目目录，默认当前位置
#   -DryRun  只说会移哪些，不改文件
# 只移状态明确处理完的：已转、已处理、已答复、已完成、完成、不做，单独写或后面紧跟括号、标点；后面还写着 待、等用户、未、部分、要不要、问号的不算。
# 待转、没写状态、写法说不准的（进行中、通知……）留着：猜错了顶多多读几段，不会把没转的请求藏起来（docs/code-standards.md 第 1 条）。
# 每条状态取小节里第一行"状态："；代码块里的 ## 不当小节；代码块没闭合的小节不移，报出来。
# 移走的原文接在 requests-done.md 末尾；主文件开头补一句去哪找。两个文件有未提交的改动时不动（可能是别的会话刚写进来的），下次再移。
# 不提交，由调用的会话单独提交（requests: archive handled items）。退出码：0 做完了（没有要移的、这次跳过也是 0）；2 参数或文件不对。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) { [Console]::Error.WriteLine("archive-requests.ps1: 找不到目录：$Repo"); exit 2 }
$Repo = (Resolve-Path -LiteralPath $Repo).ProviderPath
$file = Join-Path $Repo 'docs/requests.md'
$done = Join-Path $Repo 'docs/requests-done.md'
if (-not (Test-Path -LiteralPath $file)) { '没有 docs/requests.md，不用移'; exit 0 }

$null = git -C $Repo rev-parse --is-inside-work-tree 2>$null
if (-not $LASTEXITCODE) {
    $dirty = @(git -C $Repo status --porcelain --untracked-files=normal -- docs/requests.md docs/requests-done.md 2>$null)
    if ($dirty) { "docs/requests.md 或 requests-done.md 有未提交的改动，这次不移：$($dirty -join '；')"; exit 0 }
}
$global:LASTEXITCODE = 0

$utf8 = [Text.UTF8Encoding]::new($false)
$text = [IO.File]::ReadAllText($file, $utf8)
$nl = if ($text -match "`r`n") { "`r`n" } else { "`n" }

# 按行切小节：## 开头（### 不算），代码块里的不算。
$head = [Text.StringBuilder]::new()
$sections = [Collections.Generic.List[object]]::new()
$fence = $null
foreach ($line in [regex]::Split($text, '(?<=\n)')) {
    if ($line -eq '') { continue }
    $bare = $line.TrimEnd("`r", "`n")
    if (-not $fence -and $bare -match '^##\s' ) { $sections.Add([pscustomobject]@{ Text = [Text.StringBuilder]::new(); Open = $false }) }
    if ($bare -match '^ {0,3}(```+|~~~+)') {
        $mark = $Matches[1]
        if (-not $fence) { $fence = $mark } elseif ($mark[0] -eq $fence[0] -and $mark.Length -ge $fence.Length -and $bare.Trim() -eq $mark) { $fence = $null }
    }
    if ($sections.Count) { $null = $sections[-1].Text.Append($line); $sections[-1].Open = [bool]$fence } else { $null = $head.Append($line) }
}

$stateRe = '(?m)^\s*(?:[-*]\s*)?\**状态\**\s*[：:]\s*\**\s*(.*?)\s*$'
$handled = '^(已转|已处理|已答复|已完成|完成|不做)(?=$|[（(：:，,。.；;\s])'
$unsure = '待|等用户|等你|等您|未|部分|一半|要不要|[?？]'
$keep = [Collections.Generic.List[string]]::new()
$move = [Collections.Generic.List[string]]::new()
$notes = [Collections.Generic.List[string]]::new()
$unclosed = [Collections.Generic.List[string]]::new()
foreach ($s in $sections) {
    $sec = $s.Text.ToString()
    $title = (($sec -split '\r?\n')[0] -replace '^##\s+', '').Trim()
    $m = [regex]::Match($sec, $stateRe)
    $state = if ($m.Success) { $m.Groups[1].Value } else { '' }
    if ($state -match $handled -and $state -notmatch $unsure) {
        if ($s.Open) { $unclosed.Add($title); $keep.Add($sec); continue }
        $move.Add($sec); $notes.Add("  $title（状态：$state）")
    } else { $keep.Add($sec) }
}
$unclosed | ForEach-Object { "注意：$_ 里的代码块没闭合，没移，看一眼" }
if (-not $move.Count) { '没有要移的'; exit 0 }
if ($DryRun) { "会移 $($move.Count) 条到 docs/requests-done.md："; $notes; exit 0 }

function Ends([string]$s) { if ($s -and -not $s.EndsWith("`n")) { $s + $nl } else { $s } }
# 小节之间空一行：每段末尾去掉多余的空行再补一个。
function Join-Sections($list) { (@($list | ForEach-Object { (Ends $_).TrimEnd("`r", "`n") + $nl }) -join $nl) }
$moved = Join-Sections $move
if (Test-Path -LiteralPath $done) {
    $old = [IO.File]::ReadAllText($done, $utf8)
    $new = if ($old.Trim()) { $old.TrimEnd("`r", "`n") + $nl + $nl + $moved } else { $moved }
} else {
    $new = "# 处理过的请求${nl}${nl}从 ``docs/requests.md`` 移来的、已经转进队列或处理完的请求，原文照留，按移来的先后排。``/next`` 开场不读这份，要查当初怎么定的再来搜。${nl}${nl}" + $moved
}
$pointer = '处理完的小节移到了 `docs/requests-done.md`，按日期引用在这里找不到的去那里找。'
$headText = $head.ToString()
if ($headText -notmatch 'requests-done\.md') {
    $headText = if ($headText.Trim()) { $headText.TrimEnd("`r", "`n") + $nl + $nl + $pointer + $nl + $nl } else { $pointer + $nl + $nl }
}
$rest = $headText + $(if ($keep.Count) { Join-Sections $keep } else { '' })
[IO.File]::WriteAllText($done, $new, $utf8)
[IO.File]::WriteAllText($file, $rest, $utf8)
"移了 $($move.Count) 条到 docs/requests-done.md，主文件留 $($keep.Count) 条："
$notes
exit 0
