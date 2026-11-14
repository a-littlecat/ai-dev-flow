[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Repo = '.',
    [string]$Rev = 'HEAD',
    [string]$Command,
    [string]$For,
    [switch]$Check,
    [switch]$Record,
    [ValidateSet('green', 'red')][string]$Result,
    [int]$Seconds = -1,
    [string]$Where,
    [switch]$Force,
    [switch]$Json
)
# 快检记账（ai-dev-flow modules/build.md 第 3 节、verify.md 第 2 节）：同一棵代码树、同一条命令只跑一次快检。
# 账记在主项目工作区的 .agents/verify-ledger.jsonl（各 worktree 共用一份，.agents/ 要被 Git 忽略），一行一条：树、命令、绿红、用时、在哪跑、提交、时间。
# 算"已绿"：账上这棵树、这条命令最近的一条是 green。命令不一样的不算（审查方的命令多带 -Base 之类的，照跑）；红的不算；记录读不出、行写坏了，按没跑。
# 只有经这个脚本真跑过的才记账，别人贴的结果、note 里的文字都不记。
#   跑：  pwsh -NoProfile -File verify-ledger.ps1 -Command '<快检命令>' [-Repo <目录>] [-Where <在哪跑>] [-Force]
#         在 -Repo 里看 HEAD 的树：已绿就不跑，打出那条记录，退出 0；没绿就在 -Repo 里跑命令，按退出码记一条，退出码照传。
#         有没提交的改动（含没被忽略的未跟踪文件，比如漏了 git add 的）时照样跑，但不看账、不记账（树对不上这份代码）。-Force 已绿也重跑。
#   查：  pwsh -NoProfile -File verify-ledger.ps1 -Check -For '<快检命令>' [-Rev <提交>] [-Json]    已绿退出 0，没绿退出 3；-For 必给，只认这条命令的记录（单个测试、check-md 绿了不算快检绿）
#         -Json 里 entry 是算已绿的那条，last 是这棵树、这条命令最近的一条，不管红绿
#   记：  pwsh -NoProfile -File verify-ledger.ps1 -Record -Rev <提交> -Result green|red -For '<命令>' [-Seconds <秒>] -Where <来源>
#         别处真跑过的结果补进账（例如外部 CI、跑之前就失败的装依赖）。
# 退出码：跑的模式照传快检命令的退出码；查的模式 0 已绿、3 没绿；参数或仓库不对 2。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

function Fail([string]$m) { Write-Error $m -ErrorAction Continue; exit 2 }
$modes = @($Check, $Record, [bool]$Command) | Where-Object { $_ }
if ($modes.Count -ne 1) { Fail '要给 -Command、-Check、-Record 里的一个' }
if ($Record -and -not $Result) { Fail '-Record 要给 -Result green 或 red' }
if (($Record -or $Check) -and -not $For) { Fail "-$(if ($Check) { 'Check' } else { 'Record' }) 要给 -For <命令>：账按树和命令记" }
if ($Command) { $For = $Command }

$top = @(git -C $Repo rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -or -not $top) { Fail "不是 Git 仓库：$Repo" }
$top = $top[0]
if ($Command -and $Rev -ne 'HEAD') { Fail '跑的模式只看 HEAD：在要跑的那个检出里运行' }
$commit = @(git -C $top rev-parse --verify --quiet "$Rev^{commit}" 2>$null)
if ($LASTEXITCODE -or -not $commit) { Fail "找不到提交：$Rev" }
$commit = $commit[0]
$tree = (git -C $top rev-parse "$commit^{tree}").Trim()

# 主项目工作区：git common dir 的上一层（worktree 里也指回主项目）；裸仓库之类找不到的，用当前检出。
$common = (git -C $top rev-parse --path-format=absolute --git-common-dir 2>$null | Select-Object -First 1)
$main = if ($common -and (Split-Path $common -Leaf) -eq '.git') { Split-Path $common } else { $top }
$ledger = Join-Path $main '.agents/verify-ledger.jsonl'

function Read-Ledger {
    if (-not (Test-Path -LiteralPath $ledger -PathType Leaf)) { return @() }
    $lines = try { @(Get-Content -LiteralPath $ledger -Encoding UTF8 -ErrorAction Stop) } catch { @() }
    @(foreach ($l in $lines) {
        if (-not $l.Trim()) { continue }
        $e = try { $l | ConvertFrom-Json -ErrorAction Stop } catch { $null }
        if ($e -and $e.tree -is [string] -and $e.result -in 'green', 'red') { $e }
    })
}
function Get-Last([string]$t) { @(Read-Ledger | Where-Object { $_.tree -eq $t -and $_.command -eq $For }) | Select-Object -Last 1 }
function Get-Green([string]$t) {
    $last = Get-Last $t
    if ($last -and $last.result -eq 'green') { $last }
}
function Add-Entry($e) {
    $null = git -C $main check-ignore -q .agents/verify-ledger.jsonl 2>$null
    if ($LASTEXITCODE) { "没记账：$main 的 .agents/ 没有被 Git 忽略（harness.md 第 2 节第 8 条）"; return }
    $line = $e | ConvertTo-Json -Compress
    # 几个 worktree 可能同时记：按账本路径加进程间锁，一次只追加一行。写不进（沙箱只许写自己的目录）不算失败。
    try {
        $null = New-Item -ItemType Directory -Force -Path (Split-Path $ledger)
        $mx = [Threading.Mutex]::new($false, 'Local\ai-dev-flow-ledger-' + [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($ledger.ToLowerInvariant()))).Substring(0, 16))
        try { try { $null = $mx.WaitOne() } catch [Threading.AbandonedMutexException] { }; [IO.File]::AppendAllText($ledger, $line + "`n", [Text.UTF8Encoding]::new($false)) }
        finally { $mx.ReleaseMutex(); $mx.Dispose() }
    }
    catch { "没记账：写不进 $ledger（$($_.Exception.Message)），沙箱里跑的常见；结果照样以退出码为准"; return }
    "记账：树 $($tree.Substring(0, 12)) $($e.result)$(if ($null -ne $e.seconds) { "，$($e.seconds) 秒" })（$($e.where)）"
}
function Show($e) { "树 $($tree.Substring(0, 12)) 已绿：$($e.time) 在 $($e.where) 跑过$(if ($null -ne $e.seconds) { "，快检用时：$($e.seconds) 秒" })（提交 $("$($e.commit)".Substring(0, [Math]::Min(7, "$($e.commit)".Length)))）" }
function New-Entry([string]$r, $sec, [string]$w) { [ordered]@{ tree = $tree; command = $For; result = $r; seconds = $sec; where = $w; commit = $commit; time = (Get-Date).ToString('yyyy-MM-dd HH:mm') } }

if ($Check) {
    $g = Get-Green $tree
    if ($Json) { [ordered]@{ tree = $tree; commit = $commit; green = [bool]$g; entry = $g; last = (Get-Last $tree) } | ConvertTo-Json -Depth 4 }
    elseif ($g) { Show $g } else { "树 $($tree.Substring(0, 12)) 还没绿过：要跑快检" }
    exit $(if ($g) { 0 } else { 3 })
}

if ($Record) {
    Add-Entry (New-Entry $Result $(if ($Seconds -ge 0) { $Seconds } else { $null }) $(if ($Where) { $Where } else { '补记' }))
    exit 0
}

$dirty = @(git -C $top status --porcelain --untracked-files=all 2>$null)
$g = if (-not $dirty) { Get-Green $tree }
if ($g -and -not $Force) { Show $g; '不再重跑（同一份代码只跑一次）；要重跑加 -Force'; exit 0 }
$w = if ($Where) { $Where } else { "本机 $env:COMPUTERNAME" }
$sw = [Diagnostics.Stopwatch]::StartNew()
Push-Location $top
try { & pwsh -NoProfile -Command $Command; $code = $LASTEXITCODE } finally { Pop-Location }
$sw.Stop()
if ($null -eq $code) { $code = 0 }
$sec = [int][math]::Round($sw.Elapsed.TotalSeconds)
"快检退出码：$code；快检用时：$sec 秒"
if ($dirty) { "没记账：有 $($dirty.Count) 处没提交的改动（含没被忽略的未跟踪文件），树对不上这份代码" }
else { Add-Entry (New-Entry $(if ($code -eq 0) { 'green' } else { 'red' }) $sec $w) }
exit $code
