import paramiko

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

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03"

cmd = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 'kubeadm token create --print-join-command'"
stdin, stdout, stderr = ssh.exec_command(cmd)
join_cmd = stdout.read().decode('utf-8').strip()

print("Join cmd:", join_cmd)

print("Joining worker 1...")
cmd_join1 = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.146 'sudo {join_cmd}'"
stdin, stdout, stderr = ssh.exec_command(cmd_join1)
print(stdout.read().decode('utf-8'))

print("Joining worker 2...")
cmd_join2 = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.130 'sudo {join_cmd}'"
stdin, stdout, stderr = ssh.exec_command(cmd_join2)
print(stdout.read().decode('utf-8'))

ssh.close()
