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

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74"

script = """
systemctl stop kubelet
crictl stop $(crictl ps -a --name etcd -q) || true

rm -rf /var/lib/etcd/new-member
rm -rf /var/lib/etcd/member

# Restore using etcdctl
ctr -n k8s.io run --rm \
    --mount type=bind,src=/var/lib/etcd,dst=/var/lib/etcd,options=rbind:rw \
    --mount type=bind,src=/tmp,dst=/tmp,options=rbind:rw \
    registry.k8s.io/etcd:3.5.16-0 etcd-restore \
    etcdctl snapshot restore /tmp/db.bak --data-dir /var/lib/etcd/new-member --skip-hash-check=true

mv /var/lib/etcd/new-member /var/lib/etcd/member
chown -R root:root /var/lib/etcd/member

systemctl start kubelet
"""

b64_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')
cmd = f"{ssh_inner} 'echo {b64_script} | base64 -d | sudo bash'"

print("Running pure etcdctl snapshot restore...")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
print(stdout.read().decode('utf-8', 'ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', 'ignore'))

ssh.close()
print("Done.")
