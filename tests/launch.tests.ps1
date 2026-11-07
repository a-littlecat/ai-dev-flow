param([string]$Script = (Join-Path $PSScriptRoot '../skills/ai-dev-flow/scripts/launch.ps1'), [switch]$Keep)
# launch.ps1 的检查：用假的 claude 命令（记下收到的参数、目录和环境），断言什么时候开、什么时候不开、开的时候带了什么；退出码 0 才算通过。-Keep 保留临时目录便于查看。
#   pwsh -NoProfile -File tests/launch.tests.ps1
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Join-Path ([IO.Path]::GetTempPath()) ("launch-fixture-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$projA = Join-Path $root '项目 A'
$projB = Join-Path $root 'B'
$null = New-Item -ItemType Directory -Force -Path $projA, $projB, (Join-Path $projA '.agents/worktrees/x')
$fake = Join-Path $root 'claude.ps1'
$agents = Join-Path $root 'agents.json'
$log = Join-Path $root 'log.txt'
$cfg = Join-Path $root 'projects.json'
@{ projects = @(@{ name = '01 导图'; path = $projA; status = '推进中' }, @{ name = 'B 项目'; path = $projB; status = '推进中' }) } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $cfg -Encoding UTF8
@'
if ($args[0] -eq 'agents') { Get-Content -LiteralPath $env:FAKE_AGENTS -Raw; exit 0 }
if ($env:FAKE_UNTRUSTED) { 'Error: Workspace not trusted. Run claude in this folder first.'; exit 1 }
$leak = @(Get-ChildItem env: | Where-Object { $_.Name -match '^(CLAUDE|ANTHROPIC)' } | ForEach-Object { $_.Name }) -join ','
@("cwd=$((Get-Location).Path)", "args=$($args -join '|')", "leak=$leak") | Set-Content -LiteralPath $env:FAKE_LOG -Encoding UTF8
"backgrounded · abc12345 · $($args[2])"
'@ | Set-Content -LiteralPath $fake -Encoding UTF8

$fail = 0
function Check($name, $cond) { if ($cond) { "ok   $name" } else { "FAIL $name"; $script:fail++ } }
function Agents($list) { ConvertTo-Json -InputObject @($list) -Depth 4 | Set-Content -LiteralPath $agents -Encoding UTF8 }
function S($cwd, $status = 'idle', $state = $null, $name = 's', $sid = [guid]::NewGuid().ToString()) { [ordered]@{ pid = 1; cwd = $cwd; kind = 'interactive'; sessionId = $sid; name = $name; status = $status; state = $state } }
function Run([string[]]$a) {
    Remove-Item -LiteralPath $log -ErrorAction SilentlyContinue
    $o = @(pwsh -NoProfile -File $Script @a 2>&1 | ForEach-Object { "$_" })
    [pscustomobject]@{ Out = $o; Text = ($o -join "`n"); Code = $LASTEXITCODE; Log = if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Encoding UTF8 } else { @() } }
}

$env:AI_DEV_FLOW_CLAUDE = $fake
$env:FAKE_AGENTS = $agents
$env:FAKE_LOG = $log
$env:CLAUDE_CODE_USER_EMAIL = 'desktop@example.com'
$env:ANTHROPIC_BASE_URL = 'http://127.0.0.1:1/desktop'
$env:CLAUDE_CODE_SESSION_ID = 'caller-session'
try {
    Agents @((S $projA.ToUpper() 'idle' $null '导图主会话'))
    $r = Run @('-Project', $projA)
    Check 'existing session in the project (path case differs): not launched, exit 3, names it' ($r.Code -eq 3 -and $r.Text -match '导图主会话' -and -not $r.Log)

    Agents @((S (Join-Path $projA '.agents/worktrees/x') 'busy' 'working' 'wt'))
    $r = Run @('-Project', $projA)
    Check 'session inside a subfolder counts as the project''s' ($r.Code -eq 3 -and $r.Text -match 'wt')

    Agents @((S $projA 'busy' $null 'hq' 'caller-session'))
    $r = Run @('-Project', $projA)
    Check 'the calling session itself is ignored' ($r.Code -eq 0)

    Agents @((S $projB 'busy' 'working' 'b1'), (S $root 'busy' $null 'x2'), (S $root 'busy' 'working' 'x3'), (S $root 'idle' $null 'idle1'), (S $root 'idle' 'done' 'done1'))
    $r = Run @('-Project', $projA)
    Check 'three working sessions elsewhere: cap reached, exit 4, nothing launched' ($r.Code -eq 4 -and $r.Text -match '3 个' -and -not $r.Log)
    $r = Run @('-Project', $projA, '-Max', '4')
    Check 'idle and finished sessions do not count toward the cap' ($r.Code -eq 0)

    Agents @()
    $r = Run @('-Project', $projA)
    Check 'launch: exit 0, last line names id and session' ($r.Code -eq 0 -and $r.Out[-1] -eq 'launched abc12345 项目 A next')
    Check 'launch: runs in the project folder' (($r.Log -match '^cwd=') -and ($r.Log[0] -replace '^cwd=', '').TrimEnd('\') -eq $projA)
    Check 'launch: claude --bg --name <name> /next' ($r.Log[1] -eq 'args=--bg|--name|项目 A next|/next')
    Check 'launch: desktop login variables are not passed on' ($r.Log[2] -eq 'leak=')

    $r = Run @('-Project', 'B 项目', '-Config', $cfg, '-Prompt', '/next #7 按你的')
    Check 'name from projects.json resolves the folder and names the session' ($r.Code -eq 0 -and $r.Out[-1] -eq 'launched abc12345 B 项目 next' -and $r.Log[1] -eq 'args=--bg|--name|B 项目 next|/next #7 按你的')
    $r = Run @('-Project', $projA, '-Config', $cfg)
    Check 'folder listed in projects.json takes the listed name' ($r.Out[-1] -eq 'launched abc12345 01 导图 next')

    $r = Run @('-Project', $projA, '-DryRun')
    Check 'dry run: exit 0, launches nothing' ($r.Code -eq 0 -and $r.Text -match 'claude --bg' -and -not $r.Log)

    $r = Run @('-Project', 'nowhere', '-Config', $cfg)
    Check 'unknown project: exit 1' ($r.Code -eq 1 -and $r.Text -match '找不到项目')

    $env:FAKE_UNTRUSTED = '1'
    $r = Run @('-Project', $projA)
    Check 'untrusted folder: exit 1 with how to fix' ($r.Code -eq 1 -and $r.Text -match '接受信任')
    Remove-Item env:FAKE_UNTRUSTED
} finally {
    foreach ($k in 'AI_DEV_FLOW_CLAUDE', 'FAKE_AGENTS', 'FAKE_LOG', 'FAKE_UNTRUSTED', 'CLAUDE_CODE_USER_EMAIL', 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_SESSION_ID') { Remove-Item -LiteralPath "env:$k" -ErrorAction SilentlyContinue }
    if ($Keep) { "kept: $root" } else { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }
}
if ($fail) { "$fail failed"; exit 1 }
'all passed'
exit 0
