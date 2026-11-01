[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Title,
    [string]$Body,
    [ValidateSet('info', 'done', 'user', 'stuck')][string]$Level = 'info',
    [string]$Open,
    [switch]$Hook,
    [switch]$DryRun,
    [string]$Config
)
# 通知：弹一条 Windows 系统通知，级别在本机配置的 barkLevels 里的再推到手机（Bark）。
#   -Level   info：只是提醒；done：做完或合并了；user：要用户看或定；stuck：卡住、停在安全点
#   -Open    点通知时打开的文件或网址
#   -Hook    当 Claude Code 的 Notification hook 用：从标准输入读事件，标题取项目目录名，正文取事件的 message，级别 info
#   -DryRun  只打印会发到哪些渠道，不发
# 本机配置（不入库，里面有 Bark 的 key）：-Config，或环境变量 AI_DEV_FLOW_NOTIFY，默认 %APPDATA%\ai-dev-flow\notify.json
#   { "bark": "https://api.day.app/<key>", "barkLevels": ["user", "stuck"], "toast": true }
# 没有配置时只弹系统通知。任何渠道发送失败，退出码为 1，错误写到标准错误；输出和错误里不出现 Bark 的地址。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

if ($Hook) {
    [Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
    $raw = [Console]::In.ReadToEnd()
    $evt = if ($raw.Trim()) { $raw | ConvertFrom-Json } else { $null }
    if (-not $Title) { $Title = if ($evt.cwd) { Split-Path -Leaf $evt.cwd } else { 'Claude Code' } }
    if (-not $Body) { $Body = if ($evt.message) { $evt.message } else { '需要你看一下' } }
}
if (-not $Title) { throw 'notify.ps1 needs -Title (or -Hook)' }

if (-not $Config) { $Config = if ($env:AI_DEV_FLOW_NOTIFY) { $env:AI_DEV_FLOW_NOTIFY } else { Join-Path $env:APPDATA 'ai-dev-flow/notify.json' } }
$cfg = if (Test-Path -LiteralPath $Config) { Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
$barkLevels = if ($cfg -and $null -ne $cfg.barkLevels) { @($cfg.barkLevels) } else { @('user', 'stuck') }
$useToast = -not ($cfg -and $cfg.toast -eq $false)
$useBark = [bool]($cfg -and $cfg.bark -and $barkLevels -contains $Level)
$mark = @{ info = ''; done = '✅ '; user = '🟡 '; stuck = '🔴 ' }[$Level]
$heading = "$mark$Title"
$openUri = $null
if ($Open) {
    $openUri = if ($Open -match '^[a-z][a-z0-9+.-]*://') { $Open } else { ([Uri](Resolve-Path -LiteralPath $Open).ProviderPath).AbsoluteUri }
}

if ($DryRun) {
    "toast: $(if ($useToast) { 'yes' } else { 'no' })"
    "bark: $(if ($useBark) { 'yes' } else { 'no' })"
    "title: $heading"
    "body: $Body"
    if ($openUri) { "open: $openUri" }
    exit 0
}

$failed = [Collections.Generic.List[string]]::new()

if ($useToast) {
    $esc = { param($s) [Security.SecurityElement]::Escape([string]$s) }
    $launch = if ($openUri) { " activationType=`"protocol`" launch=`"$(& $esc $openUri)`"" } else { '' }
    $xml = "<toast$launch><visual><binding template=`"ToastGeneric`"><text>$(& $esc $heading)</text><text>$(& $esc $Body)</text></binding></visual></toast>"
    # WinRT 的通知接口只在 Windows PowerShell 5.1 里能直接用，PowerShell 7 交给它弹。
    $ps = @"
`$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
`$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime]
`$x = New-Object Windows.Data.Xml.Dom.XmlDocument
`$x.LoadXml('$($xml -replace "'", "''")')
`$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(`$app).Show([Windows.UI.Notifications.ToastNotification]::new(`$x))
"@
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($ps))
    $err = & powershell.exe -NoProfile -NonInteractive -EncodedCommand $enc 2>&1
    if ($LASTEXITCODE) { $failed.Add("toast: $(($err | Out-String).Trim())") }
}

if ($useBark) {
    $payload = [ordered]@{ title = $heading; body = $Body; group = 'ai-dev-flow'; level = if ($Level -in 'user', 'stuck') { 'timeSensitive' } else { 'active' } }
    if ($openUri -and $openUri -notlike 'file:*') { $payload.url = $openUri }
    try {
        $res = Invoke-RestMethod -Method Post -Uri $cfg.bark -ContentType 'application/json; charset=utf-8' -TimeoutSec 15 `
            -Body ([Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json -Compress)))
        if ($res.code -ne 200) { $failed.Add("bark: code $($res.code) $($res.message)") }
    } catch {
        $failed.Add("bark: $($_.Exception.Message.Replace([string]$cfg.bark, '<bark>'))")
    }
}

if ($failed.Count) { $failed | ForEach-Object { [Console]::Error.WriteLine("notify.ps1 $_") }; exit 1 }
exit 0
