#!/bin/bash
GRAFANA_URL="http://10.10.10.200:3000"
AUTH="admin:DVDl10RWwECLcIev4PcdFuAhuznYHnX6oo1a7rIU"

# Dashboard 1: Node Overview (CPU, Memory, Disk, Network for all hosts)
curl -s -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -u "${AUTH}" \
  -d '{
  "dashboard": {
    "id": null,
    "title": "OpenStack Nodes Overview",
    "tags": ["openstack","nodes"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "panels": [
      {
        "title": "CPU Usage per Node",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "datasource": "Prometheus",
        "targets": [{"expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)", "legendFormat": "{{instance}}"}],
        "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100}}
      },
      {
        "title": "Memory Usage per Node",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "datasource": "Prometheus",
        "targets": [{"expr": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100", "legendFormat": "{{instance}}"}],
        "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100}}
      },
      {
        "title": "Disk Usage per Node",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "datasource": "Prometheus",
        "targets": [{"expr": "(1 - node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"}) * 100", "legendFormat": "{{instance}}"}],
        "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100}}
      },
      {
        "title": "Network Traffic per Node (Received)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "datasource": "Prometheus",
        "targets": [{"expr": "rate(node_network_receive_bytes_total{device!=\"lo\"}[5m])", "legendFormat": "{{instance}} - {{device}}"}],
        "fieldConfig": {"defaults": {"unit": "Bps"}}
      },
      {
        "title": "System Load (1m) per Node",
        "type": "gauge",
        "gridPos": {"h": 6, "w": 8, "x": 0, "y": 16},
        "datasource": "Prometheus",
        "targets": [{"expr": "node_load1", "legendFormat": "{{instance}}"}],
        "fieldConfig": {"defaults": {"min": 0, "max": 16, "thresholds": {"steps": [{"value": 0, "color": "green"}, {"value": 4, "color": "yellow"}, {"value": 8, "color": "red"}]}}}
      },
      {
        "title": "Uptime per Node",
        "type": "stat",
        "gridPos": {"h": 6, "w": 8, "x": 8, "y": 16},
        "datasource": "Prometheus",
        "targets": [{"expr": "node_time_seconds - node_boot_time_seconds", "legendFormat": "{{instance}}"}],
        "fieldConfig": {"defaults": {"unit": "s"}}
      },
      {
        "title": "Total RAM per Node",
        "type": "stat",
        "gridPos": {"h": 6, "w": 8, "x": 16, "y": 16},
        "datasource": "Prometheus",
        "targets": [{"expr": "node_memory_MemTotal_bytes", "legendFormat": "{{instance}}"}],
        "fieldConfig": {"defaults": {"unit": "bytes"}}
      }
    ]
  },
  "overwrite": true
}'

echo ""
echo "=== Dashboard 1 done ==="

# Dashboard 2: OpenStack Services Health
curl -s -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -u "${AUTH}" \
  -d '{
  "dashboard": {
    "id": null,
    "title": "OpenStack Services Health",
    "tags": ["openstack","services"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "panels": [
      {
        "title": "HAProxy Frontend Sessions",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "datasource": "Prometheus",
        "targets": [{"expr": "haproxy_frontend_current_sessions", "legendFormat": "{{proxy}}"}]
      },
      {
        "title": "HAProxy Backend Status",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "datasource": "Prometheus",
        "targets": [{"expr": "haproxy_backend_active_servers", "legendFormat": "{{proxy}}"}]
      },
      {
        "title": "HAProxy HTTP Request Rate",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "datasource": "Prometheus",
        "targets": [{"expr": "rate(haproxy_frontend_http_requests_total[5m])", "legendFormat": "{{proxy}}"}],
        "fieldConfig": {"defaults": {"unit": "reqps"}}
      },
      {
        "title": "MySQL Queries per Second",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "datasource": "Prometheus",
        "targets": [{"expr": "rate(mysql_global_status_queries[5m])", "legendFormat": "QPS"}],
        "fieldConfig": {"defaults": {"unit": "ops"}}
      },
      {
        "title": "MySQL Connections",
        "type": "stat",
        "gridPos": {"h": 6, "w": 8, "x": 0, "y": 16},
        "datasource": "Prometheus",
        "targets": [{"expr": "mysql_global_status_threads_connected", "legendFormat": "Connected"}]
      },
      {
        "title": "RabbitMQ Messages",
        "type": "timeseries",
        "gridPos": {"h": 6, "w": 8, "x": 8, "y": 16},
        "datasource": "Prometheus",
        "targets": [{"expr": "rabbitmq_queue_messages", "legendFormat": "{{queue}}"}]
      },
      {
        "title": "Memcached Hit Ratio",
        "type": "gauge",
        "gridPos": {"h": 6, "w": 8, "x": 16, "y": 16},
        "datasource": "Prometheus",
        "targets": [{"expr": "rate(memcached_commands_total{command=\"get\",status=\"hit\"}[5m]) / (rate(memcached_commands_total{command=\"get\",status=\"hit\"}[5m]) + rate(memcached_commands_total{command=\"get\",status=\"miss\"}[5m])) * 100", "legendFormat": "Hit Ratio"}],
        "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100, "thresholds": {"steps": [{"value": 0, "color": "red"}, {"value": 60, "color": "yellow"}, {"value": 90, "color": "green"}]}}}
      }
    ]
  },
  "overwrite": true
}'

echo ""
echo "=== Dashboard 2 done ==="

# Dashboard 3: Prometheus Self-Monitoring
curl -s -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -u "${AUTH}" \
  -d '{
  "dashboard": {
    "id": null,
    "title": "Prometheus Overview",
    "tags": ["prometheus","monitoring"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "panels": [
      {
        "title": "Scrape Targets Up/Down",
        "type": "stat",
        "gridPos": {"h": 6, "w": 24, "x": 0, "y": 0},
        "datasource": "Prometheus",
        "targets": [{"expr": "up", "legendFormat": "{{job}} - {{instance}}"}],
        "fieldConfig": {"defaults": {"mappings": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}]}}
      },
      {
        "title": "Prometheus Scrape Duration",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 6},
        "datasource": "Prometheus",
        "targets": [{"expr": "scrape_duration_seconds", "legendFormat": "{{job}}"}],
        "fieldConfig": {"defaults": {"unit": "s"}}
      },
      {
        "title": "Total Time Series in Prometheus",
        "type": "stat",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 6},
        "datasource": "Prometheus",
        "targets": [{"expr": "prometheus_tsdb_head_series", "legendFormat": "Series Count"}]
      }
    ]
  },
  "overwrite": true
}'

echo ""
echo "=== Dashboard 3 done ==="
echo "All dashboards imported!"
