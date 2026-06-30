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

patch_cmd = """kubectl patch deployment video-encoder-worker -p '{"spec": {"template": {"spec": {"containers": [{"name": "worker", "image": "registry.k8s.io/pause:3.10.1", "command": []}]}}}}'"""
b64_cmd = base64.b64encode(patch_cmd.encode('utf-8')).decode('utf-8')

cmd = f"{ssh_inner} 'echo {b64_cmd} | base64 -d | bash'"

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
ssh.close()
