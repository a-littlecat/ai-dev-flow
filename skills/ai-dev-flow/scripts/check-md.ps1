[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Repo = '.',
    [string[]]$Files
)
# 文档格式检查，放进快检。查被 Git 跟踪的 .md（或 -Files 给的文件）：
#   1. 控制字符（0x00–0x1F）：只允许换行 LF 和 CRLF 里的 CR；单独回车、退格、换页、垂直制表、NUL 等都算错。
#      制表符只在代码块里和行首缩进里允许；正文中间的 Tab 多半是 Windows 路径里的 \t 被转义了。
#   2. 被拆断的表格行：表头两端都有竖线的表格里，以竖线开头的行也要以竖线结尾；表格里不能夹一行普通文字。
#      路径里的 \n、\r 被当成转义写进文件时，一行从中间断开，状态脚本就认不出那一项。
#      表格后面直接接列表、标题、引用、代码块的，算表格结束，不报。
#   pwsh -NoProfile -File <skill>/scripts/check-md.ps1 [-Repo <仓库根>] [-Files a.md,b.md]（-File 调用时逗号连写，会自动拆开）
# 仓库模式下，被跟踪但工作区里已删掉的文件跳过。
# 没有问题退出 0；有问题逐条打出"文件:行 原因"，退出 1；不是 Git 仓库或读不了文件，退出 2。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$fenceOpen = '^ {0,3}(`{3,}|~{3,})'
$blockStart = '^ {0,3}([-*+]\s|\d{1,9}[.)]\s|#{1,6}(\s|$)|>|<|`{3}|~{3})'

function Get-Hits([byte[]]$data) {
    $lines = [Collections.Generic.List[object]]::new()
    $start = 0
    for ($i = 0; $i -le $data.Length; $i++) {
        if ($i -eq $data.Length -or $data[$i] -eq 0x0A) {
            $end = $i
            if ($i -lt $data.Length -and $end -gt $start -and $data[$end - 1] -eq 0x0D) { $end-- }
            $bytes = [byte[]]::new($end - $start)
            [Array]::Copy($data, $start, $bytes, 0, $bytes.Length)
            $lines.Add($bytes)
            $start = $i + 1
        }
    }
    $utf8 = [Text.UTF8Encoding]::new($false)
    $fence = $null; $inTable = $false
    for ($n = 0; $n -lt $lines.Count; $n++) {
        $b = $lines[$n]; $l = $utf8.GetString($b); $no = $n + 1
        $code = [bool]$fence
        if ($fence) {
            if ($l -match '^ {0,3}(`{3,}|~{3,})\s*$' -and $Matches[1][0] -eq $fence[0] -and $Matches[1].Length -ge $fence.Length) { $fence = $null }
        } elseif ($l -match $fenceOpen) { $fence = $Matches[1]; $inTable = $false; $code = $true }
        elseif ($l -match '^( {4}|\t)' -and -not $inTable) { $code = $true }

        $lead = $true
        for ($k = 0; $k -lt $b.Length; $k++) {
            $c = $b[$k]
            if ($c -ne 0x20 -and $c -ne 0x09) { $lead = $false }
            if ($c -ge 0x20) { continue }
            if ($c -eq 0x09 -and ($code -or $lead)) { continue }
            [pscustomobject]@{ Line = $no; Reason = ('控制字符 0x{0:X2}' -f $c) }
        }
        if ($code) { continue }

        $t = $l.Trim()
        if ($inTable) {
            if (-not $t -or $l -match $blockStart) { $inTable = $false; continue }
            if ($t.StartsWith('|') -and $t.EndsWith('|') -and -not $t.EndsWith('\|')) { continue }
            if ($t.StartsWith('|')) { [pscustomobject]@{ Line = $no; Reason = '表格行没有以竖线结尾，像是被拆断了' } }
            else { [pscustomobject]@{ Line = $no; Reason = '表格中间夹着一行不以竖线开头的文字，像是上一行被拆断了' }; $inTable = $false }
            continue
        }
        if (-not ($t.StartsWith('|') -and $t.EndsWith('|'))) { continue }
        if ($n + 1 -lt $lines.Count -and $utf8.GetString($lines[$n + 1]).Trim() -match '^\|(\s*:?-+:?\s*\|)+$') { $inTable = $true; $n++ }
    }
}

if ($Files) {
    $paths = @($Files | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
    $base = ''
} else {
    $base = (git -C $Repo rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -or -not $base) { Write-Error "不是 Git 仓库：$Repo" -ErrorAction Continue; exit 2 }
    $out = git -C $base -c core.quotePath=false ls-files -z -- '*.md'
    if ($LASTEXITCODE) { Write-Error 'git ls-files 失败' -ErrorAction Continue; exit 2 }
    $paths = @(($out -join '') -split "`0" | Where-Object { $_ })
}

$problems = 0
foreach ($rel in $paths) {
    $full = if ($base) { Join-Path $base $rel } else { $rel }
    if ($base -and -not (Test-Path -LiteralPath $full)) { continue }  # 工作区里删了、还没 git rm 的
    try { $data = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $full).ProviderPath) }
    catch { Write-Error "读不了：$rel" -ErrorAction Continue; exit 2 }
    foreach ($h in (Get-Hits $data)) {
        "$(($rel -replace '\\', '/')):$($h.Line) $($h.Reason)"
        $problems++
    }
}
if ($problems) { "$problems 处问题。改的时候用脚本文件按字节改，不要用会把 \r、\n、\t 当转义的命令行内联写法"; exit 1 }
exit 0
