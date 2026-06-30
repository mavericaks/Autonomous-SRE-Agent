import paramiko, urllib.request, tarfile, os, base64
import socket

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



orig_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'github.com':
        return orig_getaddrinfo('20.207.73.82', port, family, type, proto, flags)
    if host == 'objects.githubusercontent.com':
        return orig_getaddrinfo('185.199.110.133', port, family, type, proto, flags)
    return orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = new_getaddrinfo

url = "https://github.com/etcd-io/etcd/releases/download/v3.5.16/etcd-v3.5.16-linux-amd64.tar.gz"
tar_path = os.path.join(BASE_DIR, "/src/chaos_engineering/etcd.tar.gz")
extract_dir = os.path.join(BASE_DIR, "/src/chaos_engineering/etcd_extracted")

print("Downloading etcd on Windows host...")
urllib.request.urlretrieve(url, tar_path)

print("Extracting etcdutl...")
with tarfile.open(tar_path, "r:gz") as tar:
    for member in tar.getmembers():
        if member.name.endswith("etcdutl"):
            tar.extract(member, path=extract_dir)
            etcdutl_path = os.path.join(extract_dir, member.name)
            break

print("Connecting to Kolla controller...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD)

print("Transferring etcdutl to Kolla controller...")
sftp = ssh.open_sftp()
sftp.put(etcdutl_path, '/tmp/etcdutl')
sftp.chmod('/tmp/etcdutl', 0o755)
sftp.close()

print("Copying etcdutl to k8s master via scp...")
ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03"
cmd_scp = f"{ssh_inner} scp -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa /tmp/etcdutl ubuntu@172.16.0.74:/tmp/etcdutl"
ssh.exec_command(cmd_scp)

print("Running etcdutl defrag on k8s master...")
script = """
set -e
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

sudo chmod +x /tmp/etcdutl
sudo cp /var/lib/etcd/member/snap/db /var/lib/etcd/member/snap/db.corrupt
sudo /tmp/etcdutl defrag --data-dir /var/lib/etcd/member/snap/db.corrupt
sudo mv /var/lib/etcd/member/snap/db.corrupt /var/lib/etcd/member/snap/db
sudo chown root:root /var/lib/etcd/member/snap/db

sudo systemctl start kubelet
"""

b64_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')
cmd = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 'echo {b64_script} | base64 -d | sudo bash'"

stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
print(stdout.read().decode('utf-8', 'ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', 'ignore'))

ssh.close()
print("Done.")
