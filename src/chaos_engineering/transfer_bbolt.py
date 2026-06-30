import paramiko, urllib.request, os

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



print("Downloading bbolt on Windows host...")
url = "https://github.com/etcd-io/bbolt/releases/download/v1.3.11/bbolt-linux-amd64"
bbolt_path = os.path.join(BASE_DIR, "/src/chaos_engineering/bbolt")
urllib.request.urlretrieve(url, bbolt_path)

print("Connecting to Kolla controller...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD)

print("Transferring bbolt to Kolla controller...")
sftp = ssh.open_sftp()
sftp.put(bbolt_path, '/tmp/bbolt')
sftp.chmod('/tmp/bbolt', 0o755)
sftp.close()

print("Copying bbolt to k8s master via scp...")
cmd_scp = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 scp -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa /tmp/bbolt ubuntu@172.16.0.74:/tmp/bbolt"
ssh.exec_command(cmd_scp)

ssh.close()
print("Transfer complete.")
