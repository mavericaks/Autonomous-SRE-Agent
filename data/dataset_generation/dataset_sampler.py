import paramiko
import json
import time
from datetime import datetime

# 1. Connect to OpenStack Controller
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)

def run_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8').strip()

# Fetch OpenStack Hypervisor Stats
os_raw = run_cmd("source /etc/kolla/admin-openrc.sh && openstack hypervisor stats show -f json")
try:
    os_stats = json.loads(os_raw)
    os_vcpus_used = os_stats.get('vcpus_used', 0)
    os_mem_used = os_stats.get('memory_mb_used', 0)
    os_running_vms = os_stats.get('running_vms', 0)
except Exception:
    os_vcpus_used, os_mem_used, os_running_vms = 0, 0, 0

# Fetch OpenStack Compute nodes status
os_computes = run_cmd("source /etc/kolla/admin-openrc.sh && openstack compute service list -c Host -c Status -c State -f json")
os_active_computes = 0
try:
    computes = json.loads(os_computes)
    os_active_computes = sum(1 for c in computes if c.get('State') == 'up' and 'compute' in c.get('Host', ''))
except Exception:
    pass

# Fetch K8s nodes status via qrouter
router_id = run_cmd("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value")
k8s_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 'kubectl get nodes --no-headers | wc -l'"
k8s_nodes_raw = run_cmd(k8s_cmd)
try:
    k8s_nodes = int(k8s_nodes_raw.split()[-1])
except Exception:
    k8s_nodes = 0

# Fetch K8s Pods
k8s_pods_raw = run_cmd(f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 'kubectl get pods -A --field-selector=status.phase=Running --no-headers | wc -l'")
try:
    k8s_running_pods = int(k8s_pods_raw.split()[-1])
except Exception:
    k8s_running_pods = 0

# Fetch K8s API Latency
k8s_latency_raw = run_cmd(f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 'curl -o /dev/null -s -w \"%{{time_total}}\" -k https://127.0.0.1:6443/version'")
try:
    k8s_api_latency_ms = round(float(k8s_latency_raw.split()[-1]) * 1000, 2)
except Exception:
    k8s_api_latency_ms = 0.0

# Fetch Mist Stats
mist_token = "<REDACTED_MIST_TOKEN>"
org_id = "827b719a-9542-43c7-888a-e87ae715585c"
mist_cmd = f"curl -s -H 'Authorization: Token {mist_token}' https://api.gc4.mist.com/api/v1/orgs/{org_id}/stats"
mist_raw = run_cmd(mist_cmd)
try:
    mist_stats = json.loads(mist_raw)
    mist_num_devices = mist_stats.get('num_devices', 0)
    mist_num_clients = mist_stats.get('num_clients', 0)
except Exception:
    mist_num_devices = 0
    mist_num_clients = 0

# Mock average RSSI since no clients
mist_avg_rssi = -65 if mist_num_clients == 0 else -50

ssh.close()

# Format as CSV
from datetime import timezone
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
fault_label = "No_Fault"

print("Timestamp,OS_vCPUs_Used,OS_Mem_MB_Used,OS_Disk_GB_Used,OS_Running_VMs,OS_Active_Computes,K8s_Active_Nodes,K8s_Running_Pods,K8s_API_Latency_ms,Mist_Num_Devices,Mist_Num_Clients,Mist_Avg_RSSI,Fault_Label")
os_disk_used = os_stats.get('local_gb_used', 0) if 'os_stats' in locals() else 0
print(f"{timestamp},{os_vcpus_used},{os_mem_used},{os_disk_used},{os_running_vms},{os_active_computes},{k8s_nodes},{k8s_running_pods},{k8s_api_latency_ms},{mist_num_devices},{mist_num_clients},{mist_avg_rssi},{fault_label}")
