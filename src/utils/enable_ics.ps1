# Re-enable Internet Connection Sharing: Ethernet -> VMnet8
$m = New-Object -ComObject HNetCfg.HNetShare
$connections = $m.EnumEveryConnection

foreach ($c in $connections) {
    $props = $m.NetConnectionProps($c)
    $cfg = $m.INetSharingConfigurationForINetConnection($c)
    
    # Disable all existing sharing first
    if ($cfg.SharingEnabled) {
        $cfg.DisableSharing()
        Write-Host "Disabled sharing on: $($props.Name)"
    }
}

Start-Sleep -Seconds 2

# Now enable: Ethernet = Public (shared), VMnet8 = Private (receives)
foreach ($c in $connections) {
    $props = $m.NetConnectionProps($c)
    $cfg = $m.INetSharingConfigurationForINetConnection($c)
    
    if ($props.Name -eq 'Ethernet') {
        $cfg.EnableSharing(0)  # 0 = Public
        Write-Host "Enabled PUBLIC sharing on: Ethernet"
    }
    elseif ($props.Name -eq 'VMware Network Adapter VMnet8') {
        $cfg.EnableSharing(1)  # 1 = Private
        Write-Host "Enabled PRIVATE sharing on: VMnet8"
    }
}

Write-Host "ICS reconfigured successfully."
