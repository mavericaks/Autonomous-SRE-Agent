import paramiko
import time
import sys

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



def run_on_controller(cmd, timeout=30):
    """Run a command on the OpenStack Controller"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8').strip()
    err = stderr.read().decode('utf-8').strip()
    ssh.close()
    return out, err

def run_on_k8s_node(node_ip, cmd, timeout=60):
    """Run a command on a K8s node via qrouter SSH chain"""
    # Get router ID first
    router_cmd = "source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value"
    router_id, _ = run_on_controller(router_cmd)
    router_id = router_id.strip()
    
    # Build SSH chain command through qrouter
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} '{cmd}'"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)  # clear banner
    channel.send(full_cmd + "\n")
    time.sleep(2)
    
    # Collect output
    output = ""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if channel.recv_ready():
            chunk = channel.recv(65535).decode('utf-8')
            output += chunk
            # Check if we're back at prompt
            if 'kolla@openstack-controller' in chunk and chunk.strip().endswith('$'):
                break
        else:
            # Check if command is done
            if channel.exit_status_ready():
                break
    
    channel.close()
    ssh.close()
    return output

# ===== STEP 1: Reset kubeadm on master =====
print("=" * 60)
print("STEP 1: Resetting kubeadm on k8s-master...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.74", "sudo kubeadm reset -f && sudo rm -rf /etc/cni/net.d && echo RESET_DONE", timeout=60)
print(out)
if "RESET_DONE" not in out:
    print("WARNING: Reset may not have completed cleanly, continuing anyway...")

# ===== STEP 2: Re-initialize kubeadm on master =====
print("\n" + "=" * 60)
print("STEP 2: Initializing kubeadm on k8s-master...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.74", "sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=172.16.0.74 2>&1 | tail -30", timeout=180)
print(out)

# ===== STEP 3: Setup kubeconfig =====
print("\n" + "=" * 60)
print("STEP 3: Setting up kubeconfig...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.74", "mkdir -p ~/.kube && sudo cp -f /etc/kubernetes/admin.conf ~/.kube/config && sudo chown ubuntu:ubuntu ~/.kube/config && kubectl get nodes && echo KUBECONFIG_DONE", timeout=30)
print(out)

# ===== STEP 4: Get join command =====
print("\n" + "=" * 60)
print("STEP 4: Getting join command...")
print("=" * 60)
out = run_on_k8s_node("172.16.0.74", "kubeadm token create --print-join-command 2>/dev/null", timeout=20)
print(out)

# Extract the join command from output
join_cmd = ""
for line in out.split('\n'):
    if 'kubeadm join' in line:
        join_cmd = line.strip()
        break

if join_cmd:
    print(f"\nJoin command: {join_cmd}")
    # Save it for next steps
    with open("H:/Kolla-Ansible/k8s_join_cmd.txt", "w") as f:
        f.write(join_cmd)
    print("Saved to k8s_join_cmd.txt")
else:
    print("ERROR: Could not extract join command!")

print("\n" + "=" * 60)
print("MASTER RECOVERY COMPLETE - Next: join workers")
print("=" * 60)
