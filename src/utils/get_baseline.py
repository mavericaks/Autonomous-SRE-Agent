#!/usr/bin/env python3
import time, os, sys, subprocess, json, urllib.parse

PROM_SSH = "ssh -o StrictHostKeyChecking=no kolla@10.10.10.10"
CTRL_SSH = "ssh -o StrictHostKeyChecking=no kolla@10.10.10.10"
PROM_URL = "http://10.10.10.200:9091"
PROM_AUTH = "admin:VlgbNmcbQDvwXK7YBQil31sfEvQ1zN0WvUDwNfaI"
COMPUTE = "10.10.10.11"

PROM_QUERIES = {
    "node_cpu_seconds_total": f"sum(node_cpu_seconds_total{{instance=~'{COMPUTE}.*'}})",
    "node_load_1m": f"node_load1{{instance=~'{COMPUTE}.*'}}",
    "node_load_5m": f"node_load5{{instance=~'{COMPUTE}.*'}}",
    "node_load_15m": f"node_load15{{instance=~'{COMPUTE}.*'}}",
    "node_memory_MemTotal_bytes": f"node_memory_MemTotal_bytes{{instance=~'{COMPUTE}.*'}}",
    "node_memory_MemAvailable_bytes": f"node_memory_MemAvailable_bytes{{instance=~'{COMPUTE}.*'}}",
    "node_swap_utilization": f"(node_memory_SwapTotal_bytes{{instance=~'{COMPUTE}.*'}} - node_memory_SwapFree_bytes{{instance=~'{COMPUTE}.*'}}) / (node_memory_SwapTotal_bytes{{instance=~'{COMPUTE}.*'}} + 1) * 100",
    "node_disk_read_bytes_total": f"sum(node_disk_read_bytes_total{{instance=~'{COMPUTE}.*'}})",
    "node_disk_written_bytes_total": f"sum(node_disk_written_bytes_total{{instance=~'{COMPUTE}.*'}})",
    "node_disk_reads_completed_total": f"sum(node_disk_reads_completed_total{{instance=~'{COMPUTE}.*'}})",
    "node_disk_read_time_seconds_total": f"sum(node_disk_read_time_seconds_total{{instance=~'{COMPUTE}.*'}})",
    "node_network_receive_bytes_total": f"sum(node_network_receive_bytes_total{{instance=~'{COMPUTE}.*'}})",
    "node_network_transmit_bytes_total": f"sum(node_network_transmit_bytes_total{{instance=~'{COMPUTE}.*'}})",
    "node_network_dropped_packets": f"sum(node_network_receive_drop_total{{instance=~'{COMPUTE}.*'}})",
    "node_network_transmit_errors": f"sum(node_network_transmit_errs_total{{instance=~'{COMPUTE}.*'}})",
    "container_cpu_usage_seconds_total": f"sum(container_cpu_usage_seconds_total{{instance=~'{COMPUTE}.*',cpu='total'}})",
    "container_memory_working_set_bytes": f"sum(container_memory_working_set_bytes{{instance=~'{COMPUTE}.*'}})",
    "container_fs_usage_bytes": f"sum(container_fs_usage_bytes{{instance=~'{COMPUTE}.*'}})",
    "container_rx_bytes": f"sum(container_network_receive_bytes_total{{instance=~'{COMPUTE}.*'}})",
    "container_tx_bytes": f"sum(container_network_transmit_bytes_total{{instance=~'{COMPUTE}.*'}})",
    "os_cpu_util_percentage": f"100 - (avg(rate(node_cpu_seconds_total{{mode='idle',instance=~'{COMPUTE}.*'}}[5m])) * 100)",
    "os_memory_usage_mb": f"(node_memory_MemTotal_bytes{{instance=~'{COMPUTE}.*'}} - node_memory_MemAvailable_bytes{{instance=~'{COMPUTE}.*'}}) / 1048576",
    "os_disk_read_bytes_rate": f"sum(rate(node_disk_read_bytes_total{{instance=~'{COMPUTE}.*'}}[5m]))",
    "os_disk_write_bytes_rate": f"sum(rate(node_disk_written_bytes_total{{instance=~'{COMPUTE}.*'}}[5m]))",
    "os_network_incoming_bytes_rate": f"sum(rate(node_network_receive_bytes_total{{instance=~'{COMPUTE}.*'}}[5m]))",
    "os_network_outgoing_bytes_rate": f"sum(rate(node_network_transmit_bytes_total{{instance=~'{COMPUTE}.*'}}[5m]))",
    "os_network_packet_drop_rate": f"sum(rate(node_network_receive_drop_total{{instance=~'{COMPUTE}.*'}}[5m]))",
    "os_haproxy_connections": "sum(haproxy_server_current_sessions)",
}

def query_prom(query):
    encoded = urllib.parse.quote(query)
    cmd = f"curl -s -u {PROM_AUTH} '{PROM_URL}/api/v1/query?query={encoded}'"
    try:
        r = subprocess.run(f'{CTRL_SSH} "{cmd}"', shell=True, capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout.strip())
        results = data.get("data", {}).get("result", [])
        if results:
            fv = float(results[0]["value"][1])
            if fv != fv: return None
            return fv
    except Exception as e:
        pass
    return None

def poll_live_telemetry():
    telemetry = {}
    for feature, promql in PROM_QUERIES.items():
        val = query_prom(promql)
        if val is not None:
            telemetry[feature] = val
    return telemetry

if __name__ == "__main__":
    t = poll_live_telemetry()
    with open("real_baseline.json", "w") as f:
        json.dump(t, f, indent=2)
    print("Saved baseline to real_baseline.json")
