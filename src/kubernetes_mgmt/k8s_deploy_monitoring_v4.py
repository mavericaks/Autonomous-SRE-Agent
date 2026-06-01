import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)

def run_on_k8s_node(cmd, timeout=120):
    router_id = "1166407d-006b-4231-8187-3ad4ac6fbb03"
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 '{cmd}'"
    
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)
    channel.send(full_cmd + "\n")
    time.sleep(2)
    
    output = ""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if channel.recv_ready():
            chunk = channel.recv(65535).decode('utf-8')
            output += chunk
            if 'kolla@openstack-controller' in chunk and chunk.strip().endswith('$'):
                break
        elif channel.exit_status_ready():
            break
    channel.close()
    return output

print("\n=== Fixing permanent DNS and installing Helm ===")
fix_cmd = (
    "sudo bash -c 'echo \"DNS=8.8.8.8\" >> /etc/systemd/resolved.conf' && "
    "sudo systemctl restart systemd-resolved && "
    "curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && "
    "chmod 700 get_helm.sh && ./get_helm.sh"
)
out = run_on_k8s_node(fix_cmd)
print(out[-800:])

print("\n=== Redeploying Prometheus / Grafana stack ===")
helm_cmd = (
    "/usr/local/bin/helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && "
    "/usr/local/bin/helm repo update && "
    "/usr/local/bin/helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --set prometheus.service.type=NodePort --set prometheus.service.nodePort=30090 --set grafana.service.type=NodePort --set grafana.service.nodePort=30080 --set alertmanager.service.type=NodePort --set alertmanager.service.nodePort=30093"
)
out = run_on_k8s_node(helm_cmd, timeout=180)
print(out[-800:])

print("\n=== Configured Alertmanager ===")
alert_cmd = (
    "cat << 'EOF' > alertmanager-config.yaml\n"
    "alertmanager:\n"
    "  config:\n"
    "    global:\n"
    "      resolve_timeout: 5m\n"
    "    route:\n"
    "      group_by: ['job']\n"
    "      group_wait: 30s\n"
    "      group_interval: 5m\n"
    "      repeat_interval: 12h\n"
    "      receiver: 'webhook'\n"
    "      routes:\n"
    "      - receiver: 'webhook'\n"
    "        matchers:\n"
    "        - alertname = \"PodNotReady\"\n"
    "    receivers:\n"
    "    - name: 'webhook'\n"
    "      webhook_configs:\n"
    "      - url: 'http://172.16.0.1:9999/k8s-alert'\n"
    "        send_resolved: true\n"
    "EOF\n"
    "/usr/local/bin/helm upgrade prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring -f alertmanager-config.yaml"
)
out = run_on_k8s_node(alert_cmd, timeout=120)
print(out[-800:])

print("\n=== Deployment Status ===")
out = run_on_k8s_node("kubectl get pods -n monitoring")
print(out)

ssh.close()
