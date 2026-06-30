import paramiko
import time

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



def run_on_controller(cmd, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8').strip()
    err = stderr.read().decode('utf-8').strip()
    ssh.close()
    return out, err

def run_on_k8s_node(node_ip, cmd, timeout=60):
    router_cmd = "source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value"
    router_id, _ = run_on_controller(router_cmd)
    router_id = router_id.strip()
    
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} '{cmd}'"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)
    channel.send(full_cmd + "\n")
    time.sleep(2)
    
    output = ""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if channel.recv_ready():
            chunk = channel.recv(65535).decode('utf-8')
            output += chunk
            if 'kolla@openstack-controller' in chunk and chunk.strip().endswith('$'):
                break
        elif channel.exit_status_ready():
            break
    
    channel.close()
    ssh.close()
    return output

# Read join command
join_cmd = open("H:/Kolla-Ansible/k8s_join_cmd.txt").read().strip()
# Clean up any carriage returns
join_cmd = join_cmd.replace('\r', '').strip()
# Extract just the kubeadm join part
for line in join_cmd.split('\n'):
    if 'kubeadm join' in line:
        join_cmd = line.strip()
        break
print(f"Using join command: {join_cmd}")

# ===== STEP 1: Reset and join worker-1 =====
print("\n" + "=" * 60)
print("STEP 1: Resetting k8s-worker-1 (172.16.0.146)...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.146", "sudo kubeadm reset -f && sudo rm -rf /etc/cni/net.d && echo W1_RESET_DONE", timeout=60)
print(out[-500:] if len(out) > 500 else out)

print("\nJoining k8s-worker-1...")
out = run_on_k8s_node("172.16.0.146", f"sudo {join_cmd} && echo W1_JOIN_DONE", timeout=90)
print(out[-500:] if len(out) > 500 else out)

# ===== STEP 2: Reset and join worker-2 =====
print("\n" + "=" * 60)
print("STEP 2: Resetting k8s-worker-2 (172.16.0.130)...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.130", "sudo kubeadm reset -f && sudo rm -rf /etc/cni/net.d && echo W2_RESET_DONE", timeout=60)
print(out[-500:] if len(out) > 500 else out)

print("\nJoining k8s-worker-2...")
out = run_on_k8s_node("172.16.0.130", f"sudo {join_cmd} && echo W2_JOIN_DONE", timeout=90)
print(out[-500:] if len(out) > 500 else out)

# ===== STEP 3: Install Calico CNI =====
print("\n" + "=" * 60)
print("STEP 3: Installing Calico CNI...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.74", "kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml 2>&1 | tail -20 && echo CALICO_DONE", timeout=60)
print(out[-800:] if len(out) > 800 else out)

# ===== STEP 4: Verify cluster =====
print("\n" + "=" * 60)
print("STEP 4: Waiting 30s then verifying cluster...")
print("=" * 60)
time.sleep(30)
out = run_on_k8s_node("172.16.0.74", "kubectl get nodes; echo '---'; kubectl get pods -A", timeout=30)
print(out)

print("\n" + "=" * 60)
print("KUBERNETES RECOVERY COMPLETE")
print("=" * 60)
