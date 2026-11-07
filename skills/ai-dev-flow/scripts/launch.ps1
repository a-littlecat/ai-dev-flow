[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)][string]$Project,
    [string]$Prompt = '/next',
    [string]$Name,
    [string]$Config,
    [int]$Max = 3,
    [switch]$DryRun
)
# 替用户在一个项目里开命令行后台会话（claude --bg），用终端里登录的账号，不用桌面应用的账号。总览前台用它（portfolio.md 第 4 节）。
#   -Project  项目文件夹，或 -Config 清单里的项目名
#   -Prompt   开场指令，默认 /next
#   -Name     会话名，在 claude agents 里显示、跨会话消息按它找；默认"<项目名> next"
#   -Config   总览仓库的 projects.json，用来按名字找项目
#   -Max      在做的会话（不含空闲、已结束的，也不含调用它的会话）达到这个数就不开，默认 3
#   -DryRun   只打印会怎么开，不开
# 开之前看 claude agents --json：这个项目里已经有会话（命令行、后台、桌面都算）就不开，打印它的名字，改用跨会话消息发给它。
# 开的时候去掉从桌面应用继承来的 CLAUDE_*、ANTHROPIC_* 环境变量，否则新会话可能沿用桌面的登录。
# 退出码：0 开好了（最后一行是 "launched <id> <名字>"）；3 项目里已有会话；4 在做的会话已到上限；1 其他错误（包括文件夹没被信任）。
# 测试用环境变量 AI_DEV_FLOW_CLAUDE 换掉 claude 命令。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$claude = if ($env:AI_DEV_FLOW_CLAUDE) { $env:AI_DEV_FLOW_CLAUDE } else { 'claude' }
$self = $env:CLAUDE_CODE_SESSION_ID

function Norm([string]$p) { [IO.Path]::GetFullPath($p).TrimEnd('\', '/') }
function Fail([string]$msg) { [Console]::Error.WriteLine("launch.ps1: $msg"); exit 1 }

$label = $null
$dir = $null
if (Test-Path -LiteralPath $Project -PathType Container) {
    $dir = Norm (Resolve-Path -LiteralPath $Project).ProviderPath
}
if ($Config) {
    $list = @((Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json).projects)
    $hit = if ($dir) { $list | Where-Object { $_.path -and (Norm $_.path) -eq $dir } | Select-Object -First 1 } else { $list | Where-Object { $_.name -eq $Project } | Select-Object -First 1 }
    if ($hit) { $label = $hit.name; if (-not $dir) { $dir = Norm $hit.path } }
}
if (-not $dir) { Fail "找不到项目：$Project（给文件夹路径，或用 -Config 按清单里的名字找）" }
if (-not (Test-Path -LiteralPath $dir -PathType Container)) { Fail "项目文件夹不存在：$dir" }
if (-not $label) { $label = Split-Path -Leaf $dir }
if (-not $Name) { $Name = "$label next" }

$saved = @{}
Get-ChildItem env: | Where-Object { $_.Name -match '^(CLAUDE|ANTHROPIC)' } | ForEach-Object { $saved[$_.Name] = $_.Value }
function Clean { foreach ($k in $saved.Keys) { Remove-Item -LiteralPath "env:$k" -ErrorAction SilentlyContinue } }
function Restore { foreach ($k in $saved.Keys) { Set-Item -LiteralPath "env:$k" -Value $saved[$k] } }

try {
    Clean
    $raw = & $claude agents --json 2>&1 | Out-String
    if ($LASTEXITCODE) { Fail "claude agents --json 失败：$($raw.Trim())" }
    $sessions = @(if ($raw.Trim()) { $raw | ConvertFrom-Json })
    $inside = { param($s) $s.cwd -and ((Norm $s.cwd) -eq $dir -or (Norm $s.cwd).StartsWith("$dir\", [StringComparison]::OrdinalIgnoreCase)) }
    $here = @($sessions | Where-Object { $_.sessionId -ne $self -and (& $inside $_) })
    if ($here.Count) {
        foreach ($s in $here) { "已有会话：$($s.name)（$($s.kind)，$(if ($s.state) { $s.state } else { $s.status })，id $(if ($s.id) { $s.id } else { $s.sessionId })）" }
        '改用跨会话消息发给它；它不在了再开。'
        exit 3
    }
    $busy = @($sessions | Where-Object { $_.sessionId -ne $self -and $_.status -ne 'idle' -and $_.state -notin 'done', 'completed', 'failed', 'stopped' })
    if ($busy.Count -ge $Max) {
        "在做的会话已有 $($busy.Count) 个（上限 $Max）：$(($busy | ForEach-Object { $_.name }) -join '、')"
        exit 4
    }
    if ($DryRun) {
        "cwd: $dir"
        "run: claude --bg --name `"$Name`" `"$Prompt`""
        exit 0
    }
    Push-Location -LiteralPath $dir
    try { $out = & $claude --bg --name $Name $Prompt 2>&1 | Out-String } finally { Pop-Location }
    if ($LASTEXITCODE) {
        $hint = if ($out -match 'not trusted') { "（先在终端里进这个文件夹运行一次 claude，接受信任）" } else { '' }
        Fail "claude --bg 失败$hint：$($out.Trim())"
    }
    $id = if ($out -match 'backgrounded\s*·\s*([0-9a-f]+)') { $Matches[1] } else { '?' }
    "launched $id $Name"
    exit 0
} finally {
    Restore
}
