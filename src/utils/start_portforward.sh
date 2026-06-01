#!/bin/bash
nohup kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 --address 0.0.0.0 > /tmp/grafana-pf.log 2>&1 &
nohup kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 --address 0.0.0.0 > /tmp/prom-pf.log 2>&1 &
sleep 3
ss -tlnp | grep -E '3000|9090'
echo "Port-forwarding started"
