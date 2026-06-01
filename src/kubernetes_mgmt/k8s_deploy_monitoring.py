import paramiko
import time

def run_on_controller(cmd, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8').strip()
    ssh.close()
    return out

def run_on_k8s_node(node_ip, cmd, timeout=90):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} '{cmd}'"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)
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
    ssh.close()
    return output

# Redisploy Prometheus/Grafana stack
print("\n=== Redeploying Prometheus / Grafana stack ===")
helm_cmd = (
    "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && "
    "helm repo update && "
    "helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --set prometheus.service.type=NodePort --set prometheus.service.nodePort=30090 --set grafana.service.type=NodePort --set grafana.service.nodePort=30080 --set alertmanager.service.type=NodePort --set alertmanager.service.nodePort=30093 2>&1"
)
out = run_on_k8s_node("172.16.0.74", helm_cmd, timeout=120)
print(out[-800:])

print("\n=== Configured Alertmanager to point to AI SRE agent ===")
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
    "        - alertname = \"PodNotReady\"  # Or whatever specific alerts you want\n"
    "    receivers:\n"
    "    - name: 'webhook'\n"
    "      webhook_configs:\n"
    "      - url: 'http://172.16.0.1:9999/k8s-alert'  # IP of Controller node on qrouter interface\n"
    "        send_resolved: true\n"
    "EOF\n"
    "helm upgrade prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring -f alertmanager-config.yaml"
)
out = run_on_k8s_node("172.16.0.74", alert_cmd, timeout=120)
print(out[-800:])

print("\n=== Deployment Status ===")
out = run_on_k8s_node("172.16.0.74", "kubectl get pods -n monitoring", timeout=30)
print(out)
