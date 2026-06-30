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
    err = stderr.read().decode('utf-8').strip()
    ssh.close()
    if err:
        print("ERR:", err)
    return out

def run_on_node(ip, cmd):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@{ip} '{cmd}'"
    return run_on_controller(full_cmd)

patch = '[{"op": "replace", "path": "/spec/template/spec/containers/0/livenessProbe/exec/command", "value": ["/bin/calico-node", "-felix-live"]}, {"op": "replace", "path": "/spec/template/spec/containers/0/readinessProbe/exec/command", "value": ["/bin/calico-node", "-felix-ready"]}]'
cmd = f"kubectl patch daemonset calico-node -n kube-system --type=json -p='{patch}'"
print("Patching daemonset probes...")
print(run_on_node("172.16.0.74", cmd))
