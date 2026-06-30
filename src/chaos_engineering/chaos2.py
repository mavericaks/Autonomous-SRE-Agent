#!/usr/bin/env python3
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



CONTROLLER = CONTROLLER_IP
COMPUTE1   = COMPUTE1_IP
USER       = 'kolla'
PASS       = '123'

def run_ssh(ip, cmd, timeout=20):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=USER, password=PASS, timeout=10)
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(65535)               # flush banner
    channel.send(cmd + '\n')
    time.sleep(timeout)
    output = ''
    while channel.recv_ready():
        output += channel.recv(65535).decode('utf-8', errors='replace')
    ssh.close()
    return output

if len(sys.argv) < 2:
    print("Usage: python chaos2.py <action>")
    sys.exit(1)

action = sys.argv[1]

# ─── FAULT 1: CPU ────────────────────────────────────────────────────────────
if action == 'cpu_fault':
    print("[FAULT] Injecting CPU stress on Compute1...")
    out = run_ssh(COMPUTE1, "for i in $(seq 1 6); do (while true; do :; done) & done; echo PIDS=$!", timeout=3)
    print(out.strip() or "Injected (detached)")

elif action == 'cpu_recover':
    print("[RECOVER] Killing CPU hogs on Compute1...")
    out = run_ssh(COMPUTE1, "kill $(pgrep -d' ' bash | tr ' ' '/n' | tail -n +2)", timeout=5)
    # Also sudo kill as kolla owns those
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(COMPUTE1, username=USER, password=PASS, timeout=10)
    ch = ssh.invoke_shell()
    time.sleep(1); ch.recv(65535)
    ch.send("kill $(cat /tmp/cpu_pids.txt 2>/dev/null) 2>/dev/null; pkill -u kolla bash; echo DONE\n")
    time.sleep(5)
    print(ch.recv(65535).decode(errors='replace').strip())
    ssh.close()

# ─── FAULT 2: Nova API ────────────────────────────────────────────────────────
elif action == 'nova_fault':
    print("[FAULT] Stopping nova_api container on Controller...")
    out = run_ssh(CONTROLLER, "echo 123 | sudo -S docker stop nova_api; echo DONE", timeout=15)
    print(out.strip())

elif action == 'nova_recover':
    print("[RECOVER] Starting nova_api container on Controller...")
    out = run_ssh(CONTROLLER, "echo 123 | sudo -S docker start nova_api; echo DONE", timeout=15)
    print(out.strip())

# ─── FAULT 3: K8s ────────────────────────────────────────────────────────────
elif action == 'k8s_setup':
    print("[SETUP] Creating demo-app deployment in Kubernetes...")
    k8s_cmd = "kubectl create deployment demo-app --image=nginx --replicas=3 2>/dev/null || kubectl scale deployment demo-app --replicas=3; echo DONE"
    cmd = f"echo 123 | sudo -S bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=$(openstack router show router1 -c id -f value) && ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \"{k8s_cmd}\"'"
    out = run_ssh(CONTROLLER, cmd, timeout=25)
    print(out.strip())

elif action == 'k8s_fault':
    print("[FAULT] Scaling demo-app to 0 pods...")
    k8s_cmd = "kubectl scale deployment demo-app --replicas=0; kubectl get deployment demo-app"
    cmd = f"echo 123 | sudo -S bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=$(openstack router show router1 -c id -f value) && ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \"{k8s_cmd}\"'"
    out = run_ssh(CONTROLLER, cmd, timeout=25)
    print(out.strip())

elif action == 'k8s_recover':
    print("[RECOVER] Scaling demo-app back to 3 pods...")
    k8s_cmd = "kubectl scale deployment demo-app --replicas=3; kubectl get deployment demo-app"
    cmd = f"echo 123 | sudo -S bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=$(openstack router show router1 -c id -f value) && ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \"{k8s_cmd}\"'"
    out = run_ssh(CONTROLLER, cmd, timeout=25)
    print(out.strip())

else:
    print(f"Unknown action: {action}")
    sys.exit(1)
