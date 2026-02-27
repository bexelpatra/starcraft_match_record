Add-Type -AssemblyName System.Windows.Forms

$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(5000, 'Star Record', 'Test notification works!', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 5
$n.Dispose()
