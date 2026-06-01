$vmrun = "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"
$snapName = "healthy-baseline-2026-03-26"

$vms = @(
    "H:\Kolla-Ansible\openstack-controller\openstack-controller.vmx",
    "H:\Kolla-Ansible\openstack-compute1\openstack-compute1.vmx",
    "H:\Kolla-Ansible\openstack-compute2\openstack-compute2.vmx"
)

foreach ($vm in $vms) {
    & $vmrun -T ws snapshot $vm $snapName
}
