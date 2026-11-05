[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)][string]$Branch,
    [string]$Trunk = 'main',
    [string]$Repo = '.'
)
# 合并前的机械检查（land.md 第 2、3 节），在主项目工作区、主干上跑。任一项不满足就不要合并：
#   1. 当前检出的是主干，工作区干净（git status --short 为空）。
#   2. 分支 head 是主干的后代，能快进。
#   3. git diff --check <主干>..<分支> 通过。
#   4. head 上有 verify note（refs/notes/verify），结论是 Pass，"覆盖：<base>..<head>" 写的就是这个 head。
#      note 挂在旧 head 上、或覆盖的是别的 head，都算没有。覆盖范围的起点不在主干里的（叠在另一个候选分支上），
#      起点那个提交也要有符合要求的 note，一直接到主干。分支相对主干只改了 .md、.markdown 的，
#      按 verify.md 第 1 节不要求 note，这一项跳过并提示逐条核对文档。
#   pwsh -NoProfile -File <skill>/scripts/land-check.ps1 -Branch <分支> [-Trunk main] [-Repo <主项目目录>]
# 全部满足退出 0，最后一行是可以直接运行的合并命令；有不满足的逐条打出原因，退出 1；参数或仓库不对，退出 2。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

function Invoke-Git([string[]]$a) { $o = @(git -C $Repo -c core.quotePath=false @a 2>$null); [pscustomobject]@{ Out = $o; Code = $LASTEXITCODE } }

$top = Invoke-Git @('rev-parse', '--show-toplevel')
if ($top.Code) { Write-Error "不是 Git 仓库：$Repo" -ErrorAction Continue; exit 2 }
$head = Invoke-Git @('rev-parse', '--verify', '--quiet', "$Branch^{commit}")
if ($head.Code -or -not $head.Out) { Write-Error "找不到分支：$Branch" -ErrorAction Continue; exit 2 }
$trunkSha = Invoke-Git @('rev-parse', '--verify', '--quiet', "$Trunk^{commit}")
if ($trunkSha.Code -or -not $trunkSha.Out) { Write-Error "找不到主干：$Trunk" -ErrorAction Continue; exit 2 }
$head = $head.Out[0]; $trunkSha = $trunkSha.Out[0]; $short = $head.Substring(0, 7)

$bad = [Collections.Generic.List[string]]::new()
$info = [Collections.Generic.List[string]]::new()

$cur = (Invoke-Git @('symbolic-ref', '--quiet', '--short', 'HEAD')).Out
if ("$cur" -ne $Trunk) { $bad.Add("当前检出的不是 $Trunk（是 $(if ($cur) { $cur } else { '分离头' })）：在主项目工作区切到主干再合并") }
$dirty = (Invoke-Git @('status', '--short')).Out
if ($dirty) { $bad.Add("工作区不干净（$(@($dirty).Count) 处）：$((@($dirty) | Select-Object -First 3) -join '；')") }

if ($head -eq $trunkSha) { $bad.Add("$Branch 和 $Trunk 是同一个提交，没有要合并的") }
else {
    $null = git -C $Repo merge-base --is-ancestor $trunkSha $head 2>$null
    if ($LASTEXITCODE) { $bad.Add("$Branch 不是 $Trunk 的后代，不能快进：按 build.md 第 4 节 rebase 重新定稿，按 verify.md 第 5 节复验") }
}

$check = Invoke-Git @('diff', '--check', "$trunkSha..$head")
if ($check.Code) { $bad.Add("git diff --check 没过：$((@($check.Out) | Select-Object -First 3) -join '；')") }

$files = @((Invoke-Git @('diff', '--name-only', "$trunkSha...$head")).Out | Where-Object { $_ })
$docsOnly = $files -and -not ($files | Where-Object { $_ -notmatch '\.(md|markdown)$' })

# 从 head 往回走：每条 note 覆盖 <base>..<这个提交>；base 已在主干里就够了，否则 base 自己也要有 note（叠在别的候选分支上的情况）。
$note = Invoke-Git @('notes', '--ref=verify', 'show', $head)
$noteMissing = $note.Code -or -not $note.Out
if ($noteMissing -and $docsOnly) { $info.Add("只改了文档（$($files.Count) 个文件），不要求 verify note：按 verify.md 第 1 节逐条核对过再合") }
else {
    $at = $head; $seen = @{}
    while ($true) {
        $s7 = $at.Substring(0, 7)
        $n = Invoke-Git @('notes', '--ref=verify', 'show', $at)
        if ($n.Code -or -not $n.Out) {
            $older = @((Invoke-Git @('log', '--format=%h', '--notes=verify', '--grep=覆盖：', "$trunkSha..$at^")).Out | Where-Object { $_ })
            $bad.Add("$s7 上没有 verify note$(if ($at -eq $head -and $older) { "（更早的提交 $($older -join '、') 有 note，只算到它们自己；head 一变，旧结论就作废）" })：按 verify.md 验证，或按第 5 节的例外补沿用记录")
            break
        }
        $text = $n.Out -join "`n"
        if ($text -notmatch '覆盖：\s*([0-9a-fA-F]{7,40})\.\.([0-9a-fA-F]{7,40})') { $bad.Add("$s7 的 note 没有写 `"覆盖：<base>..<head>`"（verify.md 第 6 节）"); break }
        $b = $Matches[1]; $h = $Matches[2]
        if (-not $at.StartsWith($h.ToLower())) { $bad.Add("$s7 的 note 写的覆盖范围是 ..$h，不是这个提交"); break }
        if ($text -notmatch 'Pass') { $bad.Add("$s7 的 note 里没有 Pass 结论"); break }
        $base = (Invoke-Git @('rev-parse', '--verify', '--quiet', "$b^{commit}")).Out
        if (-not $base) { $bad.Add("$s7 的 note 覆盖范围的起点 $b 在仓库里找不到"); break }
        $base = $base[0]
        $null = git -C $Repo merge-base --is-ancestor $base $trunkSha 2>$null
        if (-not $LASTEXITCODE) { break }
        $null = git -C $Repo merge-base --is-ancestor $base $at 2>$null
        if ($LASTEXITCODE -or $seen[$base]) { $bad.Add("$s7 的 note 覆盖范围的起点 $b 既不在主干里，也不在这个分支上"); break }
        $seen[$base] = $true; $at = $base
    }
}

if ($bad.Count) {
    "不能合并 $Branch（$short）："
    $bad | ForEach-Object { "  - $_" }
    $info | ForEach-Object { "  注意：$_" }
    exit 1
}
"可以合并 $Branch（$short）：主干 $Trunk 干净、能快进、diff --check 通过、$(if ($docsOnly -and $noteMissing) { '纯文档' } else { 'verify note 覆盖这个 head' })"
$info | ForEach-Object { "注意：$_" }
"git merge --ff-only $Branch"
exit 0
