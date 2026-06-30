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
    ssh.close()
    return out

def run_on_k8s_node(node_ip, cmd, timeout=60):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
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

join_cmd = open("H:/Kolla-Ansible/k8s_join_cmd.txt").read().strip().replace('\r','')
for line in join_cmd.split('\n'):
    if 'kubeadm join' in line:
        join_cmd = line.strip()
        break
print(f"Join cmd: {join_cmd}")

# Fix worker-1: clean stale files then rejoin
print("\n=== Cleaning stale files on worker-1 ===")
out = run_on_k8s_node("172.16.0.146", 
    "sudo rm -rf /etc/kubernetes/ /etc/cni/net.d /var/lib/kubelet/pki && "
    "sudo kubeadm reset -f 2>&1 | tail -5 && echo CLEAN_DONE", timeout=60)
print(out[-500:])

print("\n=== Joining worker-1 ===")
out = run_on_k8s_node("172.16.0.146", f"sudo {join_cmd} --ignore-preflight-errors=all && echo W1_JOIN_DONE", timeout=90)
print(out[-500:])

# Verify full cluster
print("\n=== Waiting 45s for Calico to initialize ===")
time.sleep(45)

print("\n=== Final cluster status ===")
out = run_on_k8s_node("172.16.0.74", "kubectl get nodes; echo '---PODS---'; kubectl get pods -A", timeout=30)
print(out)
