import paramiko, urllib.request, base64

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



url = "https://raw.githubusercontent.com/projectcalico/calico/v3.26.4/manifests/calico.yaml"
print("Downloading calico.yaml...")
try:
    response = urllib.request.urlopen(url)
    calico_yaml = response.read().decode('utf-8')
except Exception as e:
    import socket
    orig_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == 'raw.githubusercontent.com':
            return orig_getaddrinfo('185.199.108.133', port, family, type, proto, flags)
        return orig_getaddrinfo(host, port, family, type, proto, flags)
    socket.getaddrinfo = new_getaddrinfo
    response = urllib.request.urlopen(url)
    calico_yaml = response.read().decode('utf-8')

print("Connecting to Kolla controller...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD)

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74"

b64_calico = base64.b64encode(calico_yaml.encode('utf-8')).decode('utf-8')
cmd_deploy_calico = f"{ssh_inner} 'echo {b64_calico} | base64 -d > /tmp/calico.yaml && kubectl apply -f /tmp/calico.yaml'"

print("Deploying Calico...")
stdin, stdout, stderr = ssh.exec_command(cmd_deploy_calico)
print(stdout.read().decode('utf-8'))

print("Done.")
