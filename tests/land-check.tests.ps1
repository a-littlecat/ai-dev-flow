param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/land-check.ps1'), [switch]$Keep)
# land-check.ps1 的检查：在系统临时目录建一次性仓库，逐个造出合并前的各种状态，断言退出码和原因；退出码 0 才算通过。-Keep 保留仓库便于查看。
#   pwsh -NoProfile -File tests/land-check.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("land-check-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$repo = Join-Path $root '项目 A'
$null = New-Item -ItemType Directory -Force -Path $repo
$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function G { $o = git -C $repo -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c core.autocrlf=false @args 2>&1; if ($LASTEXITCODE) { throw "git $args`n$o" }; $o }
function Put([string]$rel, [string]$text) { $p = Join-Path $repo $rel; $null = New-Item -ItemType Directory -Force -Path (Split-Path $p); [IO.File]::WriteAllText($p, $text) }
function Commit([string]$rel, [string]$text) { Put $rel $text; $null = G add -- $rel; $null = G commit -qm "change $rel"; (G rev-parse HEAD) }
function Note([string]$sha, [string]$base, [string]$verdict = 'Pass', [string]$head = $sha) { $null = G notes --ref=verify add -f -m "覆盖：$($base.Substring(0, 7))..$($head.Substring(0, 7))；子 agent → $verdict；跑了：verify → 0" $sha }
function Run([string]$branch) { $o = @(pwsh -NoProfile -File $Script -Branch $branch -Repo $repo 2>&1 | ForEach-Object { "$_" }); [pscustomobject]@{ Out = $o; Text = ($o -join "`n"); Code = $LASTEXITCODE } }
function Branch([string]$name, [string]$from) { $null = G branch -f $name $from }

try {
    $null = G init -q
    $c0 = Commit 'src/a.ps1' "1`n"

    $null = G checkout -q -b ok
    $b1 = Commit 'src/a.ps1' "2`n"
    Note $b1 $c0
    $null = G checkout -q main
    $r = Run 'ok'
    Check 'all good: exit 0 and prints the merge command' ($r.Code -eq 0 -and $r.Out[-1] -eq 'git merge --ff-only ok')
    Check 'all good: says to clean up after merging' ($r.Text -match '合并后运行：.*cleanup\.ps1" -Branch ok -Trunk main -Repo ".*项目 A"')

    $null = G checkout -q -b nonote ok
    $b2 = Commit 'src/a.ps1' "3`n"
    $null = G checkout -q main
    $r = Run 'nonote'
    Check 'note only on an older commit: refused, names the older one' ($r.Code -eq 1 -and $r.Text -match "$($b2.Substring(0, 7)) 上没有 verify note" -and $r.Text -match $b1.Substring(0, 7))

    Branch 'wronghead' $b2
    Note $b2 $c0 'Pass' $b1
    $r = Run 'wronghead'
    Check 'note covering another head: refused' ($r.Code -eq 1 -and $r.Text -match '覆盖范围是 \.\.' + $b1.Substring(0, 7))

    Note $b2 $c0 'Fix'
    $r = Run 'wronghead'
    Check 'note without Pass: refused' ($r.Code -eq 1 -and $r.Text -match '没有 Pass')

    $null = G notes --ref=verify add -f -m '审过了 → Pass' $b2
    $r = Run 'wronghead'
    Check 'note without a 覆盖 range: refused' ($r.Code -eq 1 -and $r.Text -match '没有写 "覆盖')

    $null = G checkout -q -b stacked ok
    $s2 = Commit 'src/b.ps1' "b`n"
    Note $s2 $b1
    $null = G checkout -q main
    $r = Run 'stacked'
    Check 'stacked on a verified candidate: passes' ($r.Code -eq 0)
    $null = G notes --ref=verify remove $b1
    $r = Run 'stacked'
    Check 'stacked on an unverified candidate: refused at the lower commit' ($r.Code -eq 1 -and $r.Text -match "$($b1.Substring(0, 7)) 上没有 verify note")
    Note $b1 $c0

    Branch 'notrun' $b1
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($b1.Substring(0, 7))；子 agent → Pass；跑了：verify → 0；没跑：宿主测试（沙箱拦了）" $b1
    $r = Run 'notrun'
    Check 'note with a skipped check and no rerun: refused' ($r.Code -eq 1 -and $r.Text -match '写了没跑：宿主测试（沙箱拦了），还没有补跑')
    $null = G notes --ref=verify append -m "补跑：verify.ps1 → 退出 1（$($b1.Substring(0, 7))）" $b1
    $r = Run 'notrun'
    Check 'rerun that failed does not count' ($r.Code -eq 1 -and $r.Text -match '还没有补跑')
    $null = G notes --ref=verify append -m "补跑：verify.ps1 → 退出 0（$($b1.Substring(0, 7))）" $b1
    $r = Run 'notrun'
    Check 'skipped check rerun with exit 0: passes' ($r.Code -eq 0)
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($b1.Substring(0, 7))；子 agent → Pass；跑了：verify → 0；没跑：无" $b1
    $r = Run 'notrun'
    Check 'nothing skipped: passes' ($r.Code -eq 0)
    $null = G checkout -q -b stacknr ok
    $n2 = Commit 'src/n.ps1' "n`n"
    Note $n2 $b1
    $null = G checkout -q main
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($b1.Substring(0, 7))；子 agent → Pass；没跑：全量快检" $b1
    $r = Run 'stacknr'
    Check 'skipped check on the lower commit of a stack: refused' ($r.Code -eq 1 -and $r.Text -match "$($b1.Substring(0, 7)) 的 note 写了没跑：全量快检")
    Note $b1 $c0

    $base7 = "覆盖：$($c0.Substring(0, 7))..$($b1.Substring(0, 7))；子 agent → Pass；跑了：verify → 0"
    foreach ($case in @(
            @{ n = 'half-width colons count'; t = '；没跑:宿主测试'; code = 1 },
            @{ n = 'rerun "→ 0 passed, 3 failed" does not count'; t = '；没跑：宿主测试；补跑：npm test → 0 passed, 3 failed'; code = 1 },
            @{ n = 'rerun "→ 0（head）" counts'; t = '；没跑：宿主测试；补跑：npm test → 0（abc）'; code = 0 },
            @{ n = '"没跑：无。" passes'; t = '；没跑：无。没采纳：无'; code = 0 },
            @{ n = '"没跑：不适用" passes'; t = '；没跑：不适用'; code = 0 },
            @{ n = 'empty 没跑 does not swallow the next line'; t = "；没跑：`n说明：见上"; code = 0 },
            @{ n = 'value starting with a bracket or dot is a real skip'; t = '；没跑：（沙箱拦了）宿主测试'; code = 1 },
            @{ n = 'value ".github CI" is a real skip'; t = '；没跑：.github CI（沙箱无网络）'; code = 1 },
            @{ n = 'rerun "→ 0" followed by another note line counts'; t = "；没跑：宿主测试`n补跑：verify.ps1 → 0`n备注：见证据目录"; code = 0 })) {
        $null = G notes --ref=verify add -f -m "$base7$($case.t)" $b1
        $r = Run 'notrun'
        Check "skipped field: $($case.n)" ($r.Code -eq $case.code)
    }
    Note $b1 $c0

    $null = G notes --ref=verify add -f -m "$base7；没跑：宿主测试（沙箱拦了）" $b1
    $null = G checkout -q -b carry ok
    $x1 = Commit 'docs/x.md' "x`n"
    $null = G checkout -q main
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($x1.Substring(0, 7))；沿用 $($b1.Substring(0, 7)) 的 Pass（子 agent）；之后只多了文档：docs/x.md；没采纳：无" $x1
    $r = Run 'carry'
    Check 'carried-over note inherits an unrerun skipped check: refused' ($r.Code -eq 1 -and $r.Text -match "写了没跑：宿主测试（沙箱拦了）（沿用的 $($b1.Substring(0, 7)) 的 note 里）")
    $null = G notes --ref=verify append -m "补跑：verify.ps1 → 退出 0（$($x1.Substring(0, 7))）" $x1
    $r = Run 'carry'
    Check 'carried-over note with a rerun on the new head: passes' ($r.Code -eq 0)

    $null = G notes --ref=verify add -f -m "$base7；没跑：宿主测试（沙箱拦了）；补跑：verify.ps1 → 退出 0" $b1
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($x1.Substring(0, 7))；沿用 $($b1.Substring(0, 7)) 的 Pass（子 agent）；没采纳：无" $x1
    $r = Run 'carry'
    Check 'carried-over note whose original was rerun: passes' ($r.Code -eq 0)

    $null = G notes --ref=verify add -f -m "$base7；没跑：无" $b1
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($x1.Substring(0, 7))；沿用 $($b1.Substring(0, 7)) 的 Pass（子 agent）；没跑：同原 note；没采纳：同原 note" $x1
    $r = Run 'carry'
    Check 'carried-over "没跑：同原 note" reads the original' ($r.Code -eq 0)

    $null = G notes --ref=verify add -f -m "$base7；没跑：宿主测试（沙箱拦了）" $b1
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($x1.Substring(0, 7))；沿用 $($b1.Substring(0, 7)) 的 Pass（子 agent）；没采纳：无" $x1
    $null = G checkout -q -b carry2 carry
    $x2 = Commit 'docs/y.md' "y`n"
    $null = G checkout -q main
    $null = G notes --ref=verify add -f -m "覆盖：$($c0.Substring(0, 7))..$($x2.Substring(0, 7))；沿用 $($x1.Substring(0, 7)) 的 Pass（子 agent）；没采纳：无" $x2
    $r = Run 'carry2'
    Check 'two-level carry-over still finds the unrerun skip' ($r.Code -eq 1 -and $r.Text -match "沿用的 $($b1.Substring(0, 7)) 的 note 里")
    Note $b1 $c0

    $null = G checkout -q -b docs main
    $d1 = Commit 'docs/说明.md' "文档`n"
    $null = G checkout -q main
    $r = Run 'docs'
    Check 'docs-only without a note: passes with a reminder' ($r.Code -eq 0 -and $r.Text -match '只改了文档')

    $null = G checkout -q -b config main
    $null = Commit 'requirements.txt' "x==1`n"
    $null = G checkout -q main
    $r = Run 'config'
    Check 'config-only (.txt) branch without a note: refused, not treated as docs' ($r.Code -eq 1 -and $r.Text -match '没有 verify note')

    $null = G checkout -q -b ws main
    $w1 = Commit 'src/c.ps1' "x   `n"
    Note $w1 $c0
    $null = G checkout -q main
    $r = Run 'ws'
    Check 'diff --check failure: refused' ($r.Code -eq 1 -and $r.Text -match 'diff --check')

    Put 'src/a.ps1' "dirty`n"
    $r = Run 'ok'
    Check 'dirty worktree: refused' ($r.Code -eq 1 -and $r.Text -match '工作区不干净')
    $null = G checkout -q -- src/a.ps1
    Put 'tmp.txt' "x"
    $r = Run 'ok'
    Check 'untracked file counts as dirty' ($r.Code -eq 1 -and $r.Text -match '工作区不干净')
    Remove-Item -LiteralPath (Join-Path $repo 'tmp.txt')

    $null = G checkout -q ok
    $r = Run 'ok'
    Check 'not on the trunk: refused' ($r.Code -eq 1 -and $r.Text -match '当前检出的不是 main')
    $null = G checkout -q main

    $m1 = Commit 'docs/queue.md' "q`n"
    $r = Run 'ok'
    Check 'trunk moved on: cannot fast-forward' ($r.Code -eq 1 -and $r.Text -match '不能快进')
    $null = G reset -q --hard $c0

    $r = Run 'main'
    Check 'branch equal to trunk: refused' ($r.Code -eq 1 -and $r.Text -match '没有要合并的')

    $r = Run 'nobody'
    Check 'unknown branch exits 2' ($r.Code -eq 2)
    $o = @(pwsh -NoProfile -File $Script -Branch ok -Repo $root 2>&1); $code = $LASTEXITCODE
    Check 'not a repo exits 2' ($code -eq 2)
    $vl = Join-Path $repo '.agents/verify-last.json'
    Check 'verify time: note without it, no record' (-not (Test-Path -LiteralPath $vl))
    $null = G branch -f timed0 HEAD
    $null = G checkout -q timed0; $t0 = Commit 'src/t0.ps1' "1`n"; $null = G checkout -q main
    $m0 = G rev-parse main
    $null = G notes --ref=verify add -f -m "覆盖：$($m0.Substring(0, 7))..$($t0.Substring(0, 7))；x → Pass；快检用时：9 秒；没跑：无" $t0
    $rt = Run 'timed0'
    Check 'verify time: .agents not ignored, nothing written' ($rt.Code -eq 0 -and -not (Test-Path -LiteralPath $vl))
    Put '.gitignore' ".agents/`n"; $null = G add .gitignore; $null = G commit -qm ignore
    $null = G branch -f timed HEAD
    $null = G checkout -q timed; $tb = Commit 'src/t.ps1' "1`n"; $null = G checkout -q main
    $mainSha = G rev-parse main
    $null = G notes --ref=verify add -f -m "覆盖：$($mainSha.Substring(0, 7))..$($tb.Substring(0, 7))；x → Pass；快检用时：725 秒；没跑：无" $tb
    $rt = Run 'timed'
    $rec = if (Test-Path -LiteralPath $vl) { Get-Content -LiteralPath $vl -Raw -Encoding UTF8 | ConvertFrom-Json }
    Check 'verify time: recorded from the note, worktree stays clean' ($rt.Code -eq 0 -and $rec.seconds -eq 725 -and $rec.head -eq $tb -and -not (G status --short))
    $null = G checkout -q timed; $tc = Commit 'b.md' "x`n"; $null = G checkout -q main
    $null = G notes --ref=verify add -f -m "覆盖：$($mainSha.Substring(0, 7))..$($tc.Substring(0, 7))；沿用 $($tb.Substring(0, 7)) 的 Pass；没跑：同原 note" $tc
    Remove-Item -LiteralPath $vl
    $rt = Run 'timed'
    Check 'verify time: found through a carried-over note' ($rt.Code -eq 0 -and (Test-Path -LiteralPath $vl) -and (Get-Content -LiteralPath $vl -Raw -Encoding UTF8 | ConvertFrom-Json).head -eq $tc)
    Remove-Item -LiteralPath $vl
}
finally {
    if ($Keep) { "kept: $root" } else {
    Get-ChildItem -LiteralPath $root -Recurse -Force | ForEach-Object { $_.Attributes = 'Normal' }
    Remove-Item -LiteralPath $root -Recurse -Force }
}
if ($fail) { "$fail check(s) failed"; exit 1 } else { 'all checks passed'; exit 0 }
