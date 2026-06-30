import paramiko

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



ip = CONTROLLER_IP
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(ip, username='kolla', password=SSH_PASSWORD, timeout=10)
    
    def run_cmd(cmd):
        stdin, stdout, stderr = ssh.exec_command(cmd)
        return stdout.read().decode()

    instances = [
        ('k8s-master', '192.168.137.229'),
        ('k8s-worker-1', '192.168.137.248'),
        ('k8s-worker-2', '192.168.137.211')
    ]

    for name, fip in instances:
        print(f"Pinging 8.8.8.8 from {name} ({fip})...")
        # -o ConnectTimeout=5
        cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/k8s_rsa ubuntu@{fip} 'ping -c 1 8.8.8.8'"
        out = run_cmd(cmd)
        if '1 received' in out or 'bytes from 8.8.8.8' in out:
            print(f"{name} internet OK")
        else:
            print(f"{name} internet FAILED")
            print(out)

    ssh.close()
except Exception as e:
    print(f"Error: {e}")
