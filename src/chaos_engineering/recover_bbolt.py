import paramiko, base64

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD)

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74"

print("Copying bbolt to k8s master via scp...")
cmd_scp = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 scp -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa /tmp/bbolt ubuntu@172.16.0.74:/tmp/bbolt"
stdin, stdout, stderr = ssh.exec_command(cmd_scp)
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))

script = """
set -e
sudo chmod +x /tmp/bbolt
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

sudo cp /var/lib/etcd/member/snap/db /var/lib/etcd/member/snap/db.corrupt
sudo /tmp/bbolt compact -o /var/lib/etcd/member/snap/db.compacted /var/lib/etcd/member/snap/db.corrupt
sudo mv /var/lib/etcd/member/snap/db.compacted /var/lib/etcd/member/snap/db
sudo chown root:root /var/lib/etcd/member/snap/db

sudo systemctl start kubelet
"""

b64_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')
cmd = f"{ssh_inner} 'echo {b64_script} | base64 -d | sudo bash'"

print("Running bbolt compact on k8s master...")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
print(stdout.read().decode('utf-8', 'ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', 'ignore'))

ssh.close()
print("Done.")
