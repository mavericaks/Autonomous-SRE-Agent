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



def run_on_controller(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8').strip()
    ssh.close()
    return out

def run_on_node(ip, cmd):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@{ip} '{cmd}'"
    return run_on_controller(full_cmd)

join_cmd = "sudo kubeadm join 172.16.0.74:6443 --token o87odz.c0vre1mw7d1hrdt0 --discovery-token-ca-cert-hash sha256:1ec21b7defa2d3ea96c39e979c9c95524a6e86a4f1ca9b8bee2c29f3dd38dd50"

print("Fixing worker 1...")
run_on_node("172.16.0.146", "sudo rm -rf /etc/kubernetes/kubelet.conf /etc/kubernetes/pki/ca.crt /etc/kubernetes/bootstrap-kubelet.conf")
print(run_on_node("172.16.0.146", join_cmd))

print("Fixing worker 2...")
run_on_node("172.16.0.130", "sudo rm -rf /etc/kubernetes/kubelet.conf /etc/kubernetes/pki/ca.crt /etc/kubernetes/bootstrap-kubelet.conf")
print(run_on_node("172.16.0.130", join_cmd))

print("Deploying video app...")
print(run_on_node("172.16.0.74", "kubectl apply -f /home/ubuntu/video-app.yaml"))

print("Wait 10s...")
time.sleep(10)
print(run_on_node("172.16.0.74", "kubectl get nodes && kubectl get pods -A"))
