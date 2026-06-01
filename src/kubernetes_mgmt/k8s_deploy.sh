#!/bin/bash
source /etc/kolla/admin-openrc.sh
ROUTER_ID=$(openstack router show router1 -c id -f value)
exec_k8s() {
  sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 "$1"
}

# Fix DNS permanently
exec_k8s "sudo rm -f /etc/resolv.conf; echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf >/dev/null"
sleep 2

# Redeploy helm
exec_k8s "export PATH=\$PATH:/usr/local/bin:/snap/bin; helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true"
exec_k8s "export PATH=\$PATH:/usr/local/bin:/snap/bin; helm repo update"

# Setup alertmanager config
exec_k8s "cat << 'INNER_EOF' > alertmanager-config.yaml
alertmanager:
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ['job']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: 'webhook'
      routes:
      - receiver: 'webhook'
        matchers:
        - alertname = \"PodNotReady\"
    receivers:
    - name: 'webhook'
      webhook_configs:
      - url: 'http://172.16.0.1:9999/k8s-alert'
        send_resolved: true
INNER_EOF"

exec_k8s "export PATH=\$PATH:/usr/local/bin:/snap/bin; helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --set prometheus.service.type=NodePort --set prometheus.service.nodePort=30090 --set grafana.service.type=NodePort --set grafana.service.nodePort=30080 --set alertmanager.service.type=NodePort --set alertmanager.service.nodePort=30093 -f alertmanager-config.yaml"
