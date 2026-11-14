[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Config,
    [string]$Lock,
    [string]$Rerun,
    [switch]$DryRun,
    [switch]$NotifyDryRun
)
# 合并后在本机后台跑全量（ai-dev-flow modules/land.md 第 6 节，队列 #66）：一轮最多跑一个项目，全机一次只跑一个全量。
# 清单 projects.json 里没暂停、写了 "trunkVerify": "<全量命令>" 的项目，按清单顺序找第一个"主干这棵树、这条全量命令账上还没有记录"的
# （verify-ledger.ps1：绿的、红的都算有记录，红的不重跑），在 <项目>/.agents/trunk-check 开一个干净的分离 worktree，
# 写了 "trunkSetup": "<命令>"（如 npm ci）的先跑它，再跑全量，按退出码经 verify-ledger.ps1 -Record 记到主干那棵树上（在哪跑写"主干后台 本机"），跑完删 worktree。
# 直接跑、再补记：trunkSetup 往 worktree 里复制了文件也照样记账（经 -Command 跑会因为"有没提交的改动"不记）。输出留在 <项目>/.agents/trunk-check.log。
# 主干不写就用主检出当前所在的分支（和 status.ps1 一样）。项目的 .agents/ 没被 Git 忽略的不跑（记不了账，会每轮重跑），状态页提示。
# 跑完账上还是没有记录的（写不进账），这棵树记进 -Lock 旁边的 trunk-check-norecord.txt，不再跑，推一次手机。
# 跑绿了把用时写进 <项目>/.agents/verify-last.json（source 写 trunk-check）：合并前不跑全量以后，note 里没有全量用时，状态页靠这里看快检慢不慢。
# seconds 只算全量命令（不含 trunkSetup）；setup 失败没跑全量时，红账保留失败 setup 的耗时和退出位置，不更新 verify-last.json。
# 红了在 <项目>/.agents/trunk-red.json 留一份记录（主干、命令、清单路径、日志），项目会话的 /next 开场看它就知道主干红了、怎么重跑；之后跑绿了删掉。
# 红了推一次手机（notify.ps1 -Level stuck）；红的树账上有记录，不会重跑，也就只推这一次。状态页和 /next 从账上看到主干红了（status.ps1）。
# 不叠跑：-Lock 文件（默认 %LOCALAPPDATA%\ai-dev-flow\trunk-check.lock）用独占新建拿锁，里面记持锁进程的 PID 和启动时间，进程不在了或启动时间对不上算陈旧锁；
# 有别的进程正经 verify-ledger.ps1 跑快检（会话在跑测试），这轮不跑，等下一轮。
# 进程优先级设成低于正常，子进程跟着低。给 watch.ps1 每 15 分钟拉起一次（不带 -DryRun 时），也可以手动跑。
#   pwsh -NoProfile -File trunk-check.ps1 -Config <总览仓库>/projects.json [-DryRun]
#   -Rerun <项目名>  这个项目主干这棵树红过的也重跑一次（修好环境或 trunkSetup 之后用，skills/next/SKILL.md 第 1 节第 5 步）；绿过的不跑
#   -DryRun  只打印这一轮会跑哪个项目、为什么，不跑、不发通知
#   -NotifyDryRun  通知只打印不发（传 -DryRun 给 notify.ps1，测试用）
# 退出码：0 这轮跑完或没有要跑的；1 脚本自己出错；全量红了也是 0（结果在账上和通知里）。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
$ledgerScript = Join-Path $here 'verify-ledger.ps1'
if (-not $Config) { $Config = Join-Path (Split-Path $here -Parent) 'projects.json' }
if (-not $Lock) { $Lock = Join-Path $env:LOCALAPPDATA 'ai-dev-flow/trunk-check.lock' }
if (-not (Test-Path -LiteralPath $Config)) { throw "没有清单：$Config" }
$cfgDir = Split-Path (Resolve-Path -LiteralPath $Config).Path
$noRecord = Join-Path (Split-Path $Lock) 'trunk-check-norecord.txt'

function Notify([string]$title, [string]$body) {
    $nArgs = @('-Title', $title, '-Body', $body, '-Level', 'stuck')
    if ($NotifyDryRun) { $nArgs += '-DryRun' }
    & pwsh -NoProfile -File (Join-Path $here 'notify.ps1') @nArgs
}
# 锁：内容是"PID|进程启动时间（UTC ticks）"。进程不在了、启动时间对不上（PID 被别的进程复用）、内容读不出，都算陈旧锁。
function Test-LockLive {
    if (-not (Test-Path -LiteralPath $Lock)) { return $false }
    $parts = "$(Get-Content -LiteralPath $Lock -Raw -ErrorAction SilentlyContinue)".Trim() -split '\|'
    $id = 0; $ticks = 0L
    if ($parts.Count -ne 2 -or -not [int]::TryParse($parts[0], [ref]$id) -or -not [long]::TryParse($parts[1], [ref]$ticks)) { return $false }
    $pr = Get-Process -Id $id -ErrorAction SilentlyContinue
    if (-not $pr) { return $false }
    try { $pr.StartTime.ToUniversalTime().Ticks -eq $ticks } catch { $false }
}
function Enter-Lock {
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $Lock)
    if ((Test-Path -LiteralPath $Lock) -and -not (Test-LockLive)) { Remove-Item -LiteralPath $Lock -ErrorAction SilentlyContinue }
    try { $fs = [IO.File]::Open($Lock, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read) } catch { return $false }
    try { $b = [Text.Encoding]::ASCII.GetBytes("$PID|$((Get-Process -Id $PID).StartTime.ToUniversalTime().Ticks)"); $fs.Write($b, 0, $b.Length) } finally { $fs.Dispose() }
    $true
}

if ($DryRun) { if (Test-LockLive) { "跳过：另一轮全量还在跑（$Lock）"; exit 0 } }
elseif (-not (Enter-Lock)) { "跳过：另一轮全量还在跑（$Lock）"; exit 0 }
try {
    # 测试用 AI_DEV_FLOW_BUSY_MARK 换成自己的记号，免得被本机别的会话的快检挡住。
    $busyMark = if ($env:AI_DEV_FLOW_BUSY_MARK) { [regex]::Escape($env:AI_DEV_FLOW_BUSY_MARK) } else { 'verify-ledger\.ps1.*-Command' }
    $others = @(Get-CimInstance Win32_Process -Filter "Name='pwsh.exe' OR Name='powershell.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessId -ne $PID -and "$($_.CommandLine)" -match $busyMark })
    if ($others) { "跳过：有 $($others.Count) 个进程正经 verify-ledger.ps1 跑快检，等下一轮"; exit 0 }

    $skipped = @(if (Test-Path -LiteralPath $noRecord) { Get-Content -LiteralPath $noRecord -Encoding UTF8 })
    $cfg = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
    $why = [Collections.Generic.List[string]]::new()
    $pick = $null
    foreach ($p in @($cfg.projects)) {
        if ($p.status -eq '暂停' -or -not $p.trunkVerify) { continue }
        if ($Rerun -and $p.name -ne $Rerun) { continue }
        $path = if ([IO.Path]::IsPathRooted($p.path)) { $p.path } else { Join-Path $cfgDir $p.path }
        if (-not (Test-Path -LiteralPath $path)) { $why.Add("$($p.name)：目录不在"); continue }
        $null = git -C $path check-ignore -q .agents/verify-ledger.jsonl 2>$null
        if ($LASTEXITCODE) { $why.Add("$($p.name)：.agents/ 没被 Git 忽略，记不了账"); continue }
        $trunk = if ($p.trunk) { $p.trunk } else { git -C $path rev-parse --abbrev-ref HEAD 2>$null }
        $sha = git -C $path rev-parse --verify --quiet "$trunk^{commit}" 2>$null
        if ($LASTEXITCODE -or -not $sha) { $why.Add("$($p.name)：找不到主干 $trunk"); continue }
        $sha = "$sha".Trim()
        if ("$path|$sha" -in $skipped) { $why.Add("$($p.name)：主干 $($sha.Substring(0, 7)) 上次跑完记不进账，不再跑"); continue }
        $lj = try { (pwsh -NoProfile -File $ledgerScript -Repo $path -Check -Rev $sha -For ([string]$p.trunkVerify) -Json) -join "`n" | ConvertFrom-Json } catch { $null }
        if ($lj -and $lj.last -and -not ($Rerun -and $lj.last.result -eq 'red')) { $why.Add("$($p.name)：主干 $($sha.Substring(0, 7)) 账上是 $($lj.last.result)"); continue }
        $pick = [pscustomobject]@{ Name = $p.name; Path = $path; Trunk = $trunk; Sha = $sha; Verify = [string]$p.trunkVerify; Setup = [string]$p.trunkSetup }
        break
    }
    if (-not $pick) { "没有要跑的：$(if ($why.Count) { $why -join '；' } else { '没有配了 trunkVerify、没暂停的项目' })"; exit 0 }
    if ($DryRun) { "会跑：$($pick.Name) 主干 $($pick.Trunk) $($pick.Sha.Substring(0, 7))：$($pick.Verify)"; exit 0 }

    try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch { }
    $wt = Join-Path $pick.Path '.agents/trunk-check'
    $log = Join-Path $pick.Path '.agents/trunk-check.log'
    $redMark = Join-Path $pick.Path '.agents/trunk-red.json'
    if (Test-Path -LiteralPath $wt) { $null = git -C $pick.Path worktree remove --force $wt 2>$null; if (Test-Path -LiteralPath $wt) { Remove-Item -LiteralPath $wt -Recurse -Force } }
    $null = git -C $pick.Path worktree prune 2>$null
    $null = git -C $pick.Path worktree add -q --detach $wt $pick.Sha 2>&1
    if ($LASTEXITCODE) { throw "开不出 worktree：$wt" }
    try {
        $out = [Collections.Generic.List[string]]::new()
        $out.Add("$(Get-Date -Format 'yyyy-MM-dd HH:mm') $($pick.Name) 主干 $($pick.Sha)")
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $code = 0; $where = '主干后台 本机'
        Push-Location -LiteralPath $wt
        try {
            if ($pick.Setup) {
                $out.Add("> $($pick.Setup)")
                & pwsh -NoProfile -Command $pick.Setup *>&1 | ForEach-Object { $out.Add("$_") }
                if ($LASTEXITCODE) { $code = $LASTEXITCODE; $where = "主干后台 本机（trunkSetup 退出 $code）" }
            }
            if (-not $code) {
                $out.Add("> $($pick.Verify)")
                $sw.Restart()
                & pwsh -NoProfile -Command $pick.Verify *>&1 | ForEach-Object { $out.Add("$_") }
                $sw.Stop()
                $code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
            }
        }
        finally { Pop-Location }
        $sec = [int][math]::Round($sw.Elapsed.TotalSeconds)
        $out.Add("退出码 $code，$sec 秒")
        try { [IO.File]::WriteAllLines($log, $out, [Text.UTF8Encoding]::new($false)) } catch { }
        $res = if ($code -eq 0) { 'green' } else { 'red' }
        $null = pwsh -NoProfile -File $ledgerScript -Repo $pick.Path -Record -Rev $pick.Sha -Result $res -For $pick.Verify -Seconds $sec -Where $where
        $lj = try { (pwsh -NoProfile -File $ledgerScript -Repo $pick.Path -Check -Rev $pick.Sha -For $pick.Verify -Json) -join "`n" | ConvertFrom-Json } catch { $null }
        $recorded = $lj -and $lj.last -and $lj.last.result -eq $res -and $lj.last.where -eq $where
        "$($pick.Name) 主干 $($pick.Sha.Substring(0, 7))：$res（$sec 秒）$(if (-not $recorded) { '，记不进账' })"
        $short = $pick.Sha.Substring(0, 7)
        if (-not $recorded) {
            Add-Content -LiteralPath $noRecord -Value "$($pick.Path)|$($pick.Sha)" -Encoding UTF8
            Notify "$($pick.Name) 主干全量记不进账" "主干 $short 跑完是 $res，可账上没记下（.agents/verify-ledger.jsonl 写不进）。这棵树不再自动跑，输出在 .agents/trunk-check.log"
        }
        elseif ($res -eq 'green') {
            Remove-Item -LiteralPath $redMark -ErrorAction SilentlyContinue
            try {
                [ordered]@{ head = $pick.Sha; seconds = $sec; date = (Get-Date).ToString('yyyy-MM-dd'); source = 'trunk-check' } | ConvertTo-Json |
                    Set-Content -LiteralPath (Join-Path $pick.Path '.agents/verify-last.json') -Encoding utf8NoBOM
            } catch { }
        }
        else {
            try {
                [ordered]@{ project = $pick.Name; head = $pick.Sha; command = $pick.Verify; config = (Resolve-Path -LiteralPath $Config).Path; log = '.agents/trunk-check.log'; date = (Get-Date).ToString('yyyy-MM-dd HH:mm') } | ConvertTo-Json |
                    Set-Content -LiteralPath $redMark -Encoding utf8NoBOM
            } catch { }
            $tail = (@($out) | Where-Object { $_ -match 'FAIL|失败|退出 [1-9]|exit [1-9]' } | Select-Object -First 3) -join '；'
            Notify "$($pick.Name) 主干全量红了" "主干 $short 合并后全量没过$(if ($tail) { "：$tail" })。在那个项目发 /next，会先修；输出在 .agents/trunk-check.log"
        }
    }
    finally { $null = git -C $pick.Path worktree remove --force $wt 2>$null }
}
finally { if (-not $DryRun) { Remove-Item -LiteralPath $Lock -ErrorAction SilentlyContinue } }
exit 0
