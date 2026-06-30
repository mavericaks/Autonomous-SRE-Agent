import paramiko
import time

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
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)

def fix_dns(node_ip):
    router_id = "1166407d-006b-4231-8187-3ad4ac6fbb03" # known from previous cmd
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} 'sudo bash -c \"rm -f /etc/resolv.conf && echo nameserver 8.8.8.8 > /etc/resolv.conf\"'"
    
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)
    channel.send(full_cmd + "\n")
    time.sleep(5)
    print(f"Fixed {node_ip}")
    channel.close()

for ip in ["172.16.0.74", "172.16.0.146", "172.16.0.130"]:
    fix_dns(ip)

# Run helm via absolute path just in case
print("\n=== Redeploying Prometheus / Grafana stack ===")
helm_cmd = (
    "sudo ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 "
    "'export PATH=$PATH:/snap/bin;/snap/bin/helm repo update && "
    "/snap/bin/helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --set prometheus.service.type=NodePort --set prometheus.service.nodePort=30090 --set grafana.service.type=NodePort --set grafana.service.nodePort=30080 --set alertmanager.service.type=NodePort --set alertmanager.service.nodePort=30093 2>&1 | tail -20'"
)
stdin, stdout, stderr = ssh.exec_command(helm_cmd, timeout=120)
print(stdout.read().decode().strip())

# Do alert manager configuration
print("\n=== Configured Alertmanager to point to AI SRE agent ===")
alert_cmd = (
    "sudo ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 "
    "'cat << /\"EOF/\" > alertmanager-config.yaml\n"
    "alertmanager:\n"
    "  config:\n"
    "    global:\n"
    "      resolve_timeout: 5m\n"
    "    route:\n"
    "      group_by: [/\"job/\"]\n"
    "      group_wait: 30s\n"
    "      group_interval: 5m\n"
    "      repeat_interval: 12h\n"
    "      receiver: /\"webhook/\"\n"
    "      routes:\n"
    "      - receiver: /\"webhook/\"\n"
    "        matchers:\n"
    "        - alertname = /\"PodNotReady/\"\n"
    "    receivers:\n"
    "    - name: /\"webhook/\"\n"
    "      webhook_configs:\n"
    "      - url: /\"http://172.16.0.1:9999/k8s-alert/\"\n"
    "        send_resolved: true\n"
    "EOF\n"
    "export PATH=$PATH:/snap/bin;/snap/bin/helm upgrade prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring -f alertmanager-config.yaml'"
)
stdin, stdout, stderr = ssh.exec_command(alert_cmd, timeout=120)
print(stdout.read().decode().strip())

ssh.close()
print("\n=== DONE ===")
