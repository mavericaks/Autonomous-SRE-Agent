import paramiko, base64, time, re

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

print("Resetting k8s-worker-1...")
cmd = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.146 'sudo kubeadm reset -f && sudo rm -rf /etc/cni/net.d'"
ssh.exec_command(cmd)

print("Resetting k8s-worker-2...")
cmd = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.130 'sudo kubeadm reset -f && sudo rm -rf /etc/cni/net.d'"
ssh.exec_command(cmd)

print("Resetting k8s-master...")
script_master = """
set -e
sudo kubeadm reset -f
sudo rm -rf /etc/cni/net.d
sudo rm -rf /var/lib/etcd
sudo rm -rf $HOME/.kube/config

sudo systemctl restart containerd
sudo systemctl restart kubelet

sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --kubernetes-version=v1.29.15
"""
b64_script = base64.b64encode(script_master.encode('utf-8')).decode('utf-8')
cmd = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 'echo {b64_script} | base64 -d | sudo bash'"

print("Running kubeadm init on master...")
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode('utf-8', 'ignore')
print("STDOUT:")
print(out)

# Extract join command
join_cmd = ""
for line in out.split('/n'):
    if "kubeadm join" in line or "--discovery-token-ca-cert-hash" in line:
        join_cmd += line.strip() + " "
join_cmd = re.search(r'(kubeadm join .*?--discovery-token-ca-cert-hash sha256:[a-z0-9]+)', out, re.DOTALL)

if not join_cmd:
    print("Could not find join command!")
    exit(1)

join_cmd_str = join_cmd.group(1).replace('/n', '').replace('//', '').replace('\t', ' ')
join_cmd_str = ' '.join(join_cmd_str.split())
print("Join command:", join_cmd_str)

# Setup kubeconfig on master
cmd_config = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 'mkdir -p $HOME/.kube && sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config && sudo chown $(id -u):$(id -g) $HOME/.kube/config'"
ssh.exec_command(cmd_config)

print("Joining workers...")
cmd_join1 = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.146 'sudo {join_cmd_str}'"
ssh.exec_command(cmd_join1)

cmd_join2 = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.130 'sudo {join_cmd_str}'"
ssh.exec_command(cmd_join2)

time.sleep(5)
ssh.close()
print("Done rebuilding cluster.")
