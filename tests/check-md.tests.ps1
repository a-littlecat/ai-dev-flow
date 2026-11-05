param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/check-md.ps1'), [switch]$Keep)
# check-md.ps1 的检查：在系统临时目录按字节写几份 .md，逐条断言输出和退出码；退出码 0 才算通过。-Keep 保留这些文件便于查看。
#   pwsh -NoProfile -File tests/check-md.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("check-md-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$null = New-Item -ItemType Directory -Force -Path $root
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main @args; if ($LASTEXITCODE) { throw "git $args" } }
function Put([string]$name, [string]$text) {
    $p = Join-Path $root $name
    [IO.File]::WriteAllBytes($p, [Text.UTF8Encoding]::new($false).GetBytes($text))
    $p
}
function Run([string[]]$files) { $o = @(pwsh -NoProfile -File $Script -Files ($files -join ',') 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Code = $LASTEXITCODE } }

try {
    $clean = Put 'clean.md' (@(
        '# 中文标题', '', '| # | 目标 | 状态 |', '|---|:-:|--:|', '| 1 | 写 a\|b 解析 | 完成 |', '| 2 | 路径 `<本机路径>` | 待做 |',
        '- 表格后面直接接列表', '', '目标 | 状态', '--- | ---', 'x | y', 'z', '',
        '```', "func() {`n`treturn 1`n}", '| 代码里 | 的竖线', '```', '',
        "`tTab 缩进的代码行", '', '    | 缩进代码 | 里的表格', '|---|---|', ''
    ) -join "`r`n")
    $r = Run @($clean)
    Check 'clean file passes (CRLF, tables, lists after table, tabs in code)' ($r.Code -eq 0 -and -not $r.Out)

    $lf = Put 'lf.md' "a`nb`n| x | y |`n|---|---|`n| 1 | 2 |`n"
    $r = Run @($lf)
    Check 'LF file passes' ($r.Code -eq 0)

    $cr = Put 'cr.md' "line1`r`nline2 D:`r8-routing`r`nline3`n"
    $r = Run @($cr)
    Check 'bare CR in a line is reported with its line' ($r.Code -eq 1 -and ($r.Out -match '^.*cr\.md:2 控制字符 0x0D$'))

    $crEnd = Put 'crend.md' "a`r`nb`r"
    $r = Run @($crEnd)
    Check 'bare CR at end of file is reported' ($r.Code -eq 1 -and ($r.Out -match 'crend\.md:2 控制字符 0x0D'))

    $missed = @()
    foreach ($c in 0..31) {
        if ($c -in 9, 10, 13) { continue }
        $p = Put "c$c.md" ("ok`na" + [char]$c + "b`n")
        $r = Run @($p)
        if (-not ($r.Code -eq 1 -and ($r.Out -match ("c$c\.md:2 控制字符 0x{0:X2}" -f $c)))) { $missed += $c }
    }
    Check 'every other control byte is reported' (-not $missed)

    $tab = Put 'tab.md' "路径 D:`tools`x 在正文里`n"
    $r = Run @($tab)
    Check 'tab in the middle of text is reported' ($r.Code -eq 1 -and ($r.Out -match 'tab\.md:1 控制字符 0x09'))

    $split = Put 'split.md' (@('| # | 目标 | 状态 |', '|---|---|---|', '| 21 | 好的 | 待做 |', '| 22 | 路由 D:\work', 'r8-routing | 待做 |', '| 23 | 好的 | 完成 |', '') -join "`n")
    $r = Run @($split)
    Check 'row split by an escaped \n is reported at the broken line' ($r.Code -eq 1 -and ($r.Out -match 'split\.md:4 表格行没有以竖线结尾') -and ($r.Out -match 'split\.md:5 表格中间夹着'))

    $esc = Put 'esc.md' (@('| a | b |', '|---|---|', '| 1 | 2\|', '') -join "`n")
    $r = Run @($esc)
    Check 'row ending with an escaped pipe is reported' ($r.Code -eq 1 -and ($r.Out -match 'esc\.md:3 表格行没有以竖线结尾'))

    $fenced = Put 'fenced.md' (@('~~~~', '| a | b |', '|---|---|', '| 1 | 2', '~~~', 'still code | x', '~~~~', 'after') -join "`n")
    $r = Run @($fenced)
    Check 'tables inside fenced code are not checked' ($r.Code -eq 0)

    $r = Run @($clean, $cr, $split)
    Check 'several files: all problems listed, summary line, exit 1' ($r.Code -eq 1 -and @($r.Out | Where-Object { $_ -match '\.md:\d+ ' }).Count -eq 3 -and $r.Out[-1] -match '^3 处问题')

    $repo = Join-Path $root 'repo'
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $repo '文档')
    G init -q $repo
    [IO.File]::WriteAllBytes((Join-Path $repo '文档/好.md'), [Text.Encoding]::UTF8.GetBytes("ok`n"))
    [IO.File]::WriteAllBytes((Join-Path $repo 'notes.txt'), [byte[]](0x61, 0x0D, 0x62))
    [IO.File]::WriteAllBytes((Join-Path $repo 'untracked.md'), [byte[]](0x61, 0x0D, 0x62))
    G -C $repo add '文档/好.md' notes.txt
    G -C $repo commit -qm init
    $o = @(pwsh -NoProfile -File $Script -Repo (Join-Path $repo '文档') 2>&1); $code = $LASTEXITCODE
    Check 'repo mode: only tracked .md, from a subdirectory' ($code -eq 0 -and -not $o)
    [IO.File]::WriteAllBytes((Join-Path $repo '文档/坏.md'), [Text.Encoding]::UTF8.GetBytes("a`bb`n"))
    G -C $repo add '文档/坏.md'
    $o = @(pwsh -NoProfile -File $Script -Repo $repo 2>&1 | ForEach-Object { "$_" }); $code = $LASTEXITCODE
    Check 'repo mode: tracked bad file reported with repo-relative path' ($code -eq 1 -and ($o -contains '文档/坏.md:1 控制字符 0x08'))

    Remove-Item -LiteralPath (Join-Path $repo '文档/坏.md')
    $o = @(pwsh -NoProfile -File $Script -Repo $repo 2>&1); $code = $LASTEXITCODE
    Check 'repo mode: tracked file deleted in the worktree is skipped' ($code -eq 0 -and -not $o)

    $plain = Join-Path $root 'not-a-repo'
    $null = New-Item -ItemType Directory -Force -Path $plain
    $null = pwsh -NoProfile -File $Script -Repo $plain 2>&1
    Check 'not a git repo exits 2' ($LASTEXITCODE -eq 2)
    $null = pwsh -NoProfile -File $Script -Files (Join-Path $root 'missing.md') 2>&1
    Check 'missing file exits 2' ($LASTEXITCODE -eq 2)
}
finally {
    if ($Keep) { "kept: $root" } else {
    Get-ChildItem -LiteralPath $root -Recurse -Force | ForEach-Object { $_.Attributes = 'Normal' }
    Remove-Item -LiteralPath $root -Recurse -Force }
}
if ($fail) { "$fail check(s) failed"; exit 1 } else { 'all checks passed'; exit 0 }
