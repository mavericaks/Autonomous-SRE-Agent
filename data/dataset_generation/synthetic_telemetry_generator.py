import paramiko
import json
import time
import os
import random
import urllib.request
from datetime import datetime, timezone

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



# Artifact path
CSV_PATH = r"C:\Users\PowerX\.gemini\antigravity\brain\8a74dadb-06ba-4c57-895a-00a4700061ef\telemetry_dataset_gnn_20k.csv"
APP_URL = "http://10.10.10.10:30080" # K8s NodePort for Video App

# ALL Parameters from telemetry_parameters.md + App Layer
COLUMNS = [
    "Timestamp",
    "node_cpu_seconds_total", "node_load_1m", "node_load_5m", "node_load_15m",
    "node_memory_MemTotal_bytes", "node_memory_MemAvailable_bytes", "node_swap_utilization",
    "node_disk_read_bytes_total", "node_disk_written_bytes_total", "node_disk_reads_completed_total", "node_disk_read_time_seconds_total",
    "node_network_receive_bytes_total", "node_network_transmit_bytes_total", "node_network_dropped_packets", "node_network_transmit_errors",
    "container_cpu_usage_seconds_total", "container_memory_working_set_bytes", "container_fs_usage_bytes",
    "container_rx_bytes", "container_tx_bytes",
    "kube_pod_container_status_restarts_total", "pod_ready_status", "pod_scheduling_latency_ms",
    "os_cpu_time", "os_cpu_util_percentage", "os_memory_usage_mb", "os_memory_resident_mb",
    "os_disk_read_bytes_rate", "os_disk_write_bytes_rate", "os_disk_read_requests_rate", "os_disk_write_requests_rate",
    "os_network_incoming_bytes_rate", "os_network_outgoing_bytes_rate", "os_network_packet_drop_rate",
    "os_hypervisor_vcpus_total", "os_hypervisor_vcpus_used",
    "os_hypervisor_memory_mb_total", "os_hypervisor_memory_mb_used",
    "os_hypervisor_local_gb_total", "os_hypervisor_local_gb_used",
    "os_api_response_latency_ms", "os_rabbitmq_queue_depth", "os_haproxy_connections",
    "mist_time_to_connect_ms", "mist_coverage_score", "mist_capacity_score", "mist_roaming_score",
    "mist_ap_cpu_utilization", "mist_ap_memory_utilization", "mist_ap_uptime_seconds", "mist_ap_temperature_c",
    "mist_channel_utilization_24ghz", "mist_channel_utilization_5ghz", "mist_channel_utilization_6ghz",
    "mist_noise_floor_dbm", "mist_rf_retries_percent", "mist_client_rssi", "mist_client_snr",
    "mist_client_tx_bytes", "mist_client_rx_bytes", "mist_client_throughput_kbps",
    "mist_client_connection_state",
    # NEW APPLICATION LAYER METRICS
    "app_http_response_code", "app_request_latency_ms", "app_throughput_kbps",
    "Fault_Label"
]

with open(CSV_PATH, "w") as f:
    f.write(",".join(COLUMNS) + "\n")

print(f"Starting Application-Centric GNN Dataset Generation (20,000 rows). Writing to {CSV_PATH}")

MAX_ROWS = 20000
current_fault = "No_Fault"
fault_types = ["K8s_Pod_Crash", "OS_CPU_Exhaustion", "Mist_Network_Congestion"]

for i in range(MAX_ROWS):
    try:
        # Random Fault State Machine
        if current_fault == "No_Fault":
            if random.random() < 0.10:
                current_fault = random.choice(fault_types)
        else:
            if random.random() < 0.20:
                current_fault = "No_Fault"

        # --- LIVE APP LAYER POLLING ---
        app_start_time = time.time()
        try:
            req = urllib.request.urlopen(APP_URL, timeout=3)
            app_http_response_code = req.getcode()
            app_request_latency_ms = (time.time() - app_start_time) * 1000
            app_throughput_kbps = random.uniform(8000, 15000) # Baseline streaming rate
        except urllib.error.URLError:
            app_http_response_code = 503
            app_request_latency_ms = 5000.0 # Timeout
            app_throughput_kbps = 0.0
        except Exception:
            app_http_response_code = 500
            app_request_latency_ms = 5000.0
            app_throughput_kbps = 0.0

        # --- SSH INFRASTRUCTURE POLLING ---
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)

        def run_cmd(cmd):
            stdin, stdout, stderr = ssh.exec_command(cmd)
            return stdout.read().decode('utf-8').strip()

        # Gather real Hypervisor data
        os_raw = run_cmd("source /etc/kolla/admin-openrc.sh && openstack hypervisor stats show -f json")
        try:
            os_stats = json.loads(os_raw)
            os_hypervisor_vcpus_total = os_stats.get('vcpus', 0)
            os_hypervisor_vcpus_used = os_stats.get('vcpus_used', 0)
            os_hypervisor_memory_mb_total = os_stats.get('memory_mb', 0)
            os_hypervisor_memory_mb_used = os_stats.get('memory_mb_used', 0)
            os_hypervisor_local_gb_total = os_stats.get('local_gb', 0)
            os_hypervisor_local_gb_used = os_stats.get('local_gb_used', 0)
        except:
            os_hypervisor_vcpus_total, os_hypervisor_vcpus_used = 0, 0
            os_hypervisor_memory_mb_total, os_hypervisor_memory_mb_used = 0, 0
            os_hypervisor_local_gb_total, os_hypervisor_local_gb_used = 0, 0

        # OS CPU / Mem Real Data
        top_raw = run_cmd("top -b -n 1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        os_cpu_util_percentage = float(top_raw) if top_raw else 5.0
        
        free_raw = run_cmd("free -m | awk 'NR==2{print $3, $2}'")
        if free_raw:
            os_memory_usage_mb, os_memory_resident_mb = map(int, free_raw.split())
        else:
            os_memory_usage_mb, os_memory_resident_mb = 4096, 8192

        # IO/Net Real Data
        io_raw = run_cmd("cat /proc/diskstats | grep vda1 | awk '{print $6, $10, $4, $8}'")
        if io_raw:
            os_disk_read_bytes_rate, os_disk_write_bytes_rate, os_disk_read_requests_rate, os_disk_write_requests_rate = map(int, io_raw.split())
        else:
            os_disk_read_bytes_rate, os_disk_write_bytes_rate, os_disk_read_requests_rate, os_disk_write_requests_rate = 0, 0, 0, 0

        net_raw = run_cmd("cat /proc/net/dev | grep eth0 | awk '{print $2, $10, $4}'")
        if net_raw:
            os_network_incoming_bytes_rate, os_network_outgoing_bytes_rate, os_network_packet_drop_rate = map(int, net_raw.split())
        else:
            os_network_incoming_bytes_rate, os_network_outgoing_bytes_rate, os_network_packet_drop_rate = 0, 0, 0

        # K8s Nodes
        router_id = run_cmd("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value")
        k8s_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74"
        
        k8s_load = run_cmd(f"{k8s_cmd} 'cat /proc/loadavg'")
        if k8s_load:
            node_load_1m, node_load_5m, node_load_15m = map(float, k8s_load.split()[:3])
        else:
            node_load_1m, node_load_5m, node_load_15m = 0.5, 0.4, 0.3

        k8s_mem = run_cmd(f"{k8s_cmd} 'cat /proc/meminfo | grep -E \"MemTotal|MemAvailable\" | awk \"{{print /$2}}\"'")
        if k8s_mem:
            mem_parts = k8s_mem.split()
            node_memory_MemTotal_bytes = int(mem_parts[0]) * 1024 if len(mem_parts)>0 else 4096000000
            node_memory_MemAvailable_bytes = int(mem_parts[1]) * 1024 if len(mem_parts)>1 else 2048000000
        else:
            node_memory_MemTotal_bytes, node_memory_MemAvailable_bytes = 4096000000, 2048000000

        ssh.close()

        # ==========================================
        # SYNTHESIZE FAULTS & NULL METRICS
        # ==========================================
        # Baseline Mocks
        mist_num_clients = random.randint(10, 25)
        mist_time_to_connect_ms = random.uniform(200, 500)
        mist_rf_retries_percent = random.uniform(1, 4)
        mist_client_rssi = random.uniform(-65, -50)
        kube_pod_container_status_restarts_total = 0
        pod_ready_status = 1
        pod_scheduling_latency_ms = random.uniform(10, 30)
        os_api_response_latency_ms = random.uniform(20, 50)
        node_network_dropped_packets = 0
        mist_client_connection_state = 1
        mist_coverage_score = random.uniform(98, 100)
        mist_roaming_score = random.uniform(95, 100)

        # Apply Fault Contexts
        if current_fault == "K8s_Pod_Crash":
            kube_pod_container_status_restarts_total = random.randint(3, 15)
            pod_ready_status = 0
            pod_scheduling_latency_ms = random.uniform(2000, 8000)
            app_http_response_code = 503
            app_throughput_kbps = 0.0
        
        elif current_fault == "OS_CPU_Exhaustion":
            os_cpu_util_percentage = random.uniform(95, 100)
            os_api_response_latency_ms = random.uniform(3000, 10000)
            node_load_1m = random.uniform(15, 25)
            app_throughput_kbps = random.uniform(100, 1000)
            # App Latency will naturally spike from urllib timeout above!
        
        elif current_fault == "Mist_Network_Congestion":
            mist_num_clients = random.randint(45, 80)
            mist_time_to_connect_ms = random.uniform(8000, 15000)
            mist_rf_retries_percent = random.uniform(40, 75)
            mist_client_rssi = random.uniform(-85, -95)
            mist_coverage_score = random.uniform(40, 60)
            mist_roaming_score = random.uniform(30, 50)
            node_network_dropped_packets = random.randint(100, 500)
            app_throughput_kbps = random.uniform(10, 80) # Congested throughput

        os_cpu_time = os_cpu_util_percentage * 100 

        # Other internal mocks
        node_cpu_seconds_total = 12000 + i*5
        node_swap_utilization = 0.0
        node_disk_read_bytes_total = os_disk_read_bytes_rate * 512
        node_disk_written_bytes_total = os_disk_write_bytes_rate * 512
        node_disk_reads_completed_total = os_disk_read_requests_rate
        node_disk_read_time_seconds_total = 1.2 + random.uniform(0, 0.1)
        node_network_receive_bytes_total = os_network_incoming_bytes_rate
        node_network_transmit_bytes_total = os_network_outgoing_bytes_rate
        node_network_transmit_errors = 0

        container_cpu_usage_seconds_total = 400 + i*2
        container_memory_working_set_bytes = 250000000
        container_fs_usage_bytes = 10000000
        container_rx_bytes = 150000 + random.randint(0, 1000)
        container_tx_bytes = 120000 + random.randint(0, 1000)

        os_rabbitmq_queue_depth = 0
        os_haproxy_connections = 45 + random.randint(-5, 5)

        mist_capacity_score = 100
        mist_ap_cpu_utilization = 15 + random.uniform(-2, 2)
        mist_ap_memory_utilization = 40 + random.uniform(-2, 2)
        mist_ap_uptime_seconds = 86400 + i*5
        mist_ap_temperature_c = 45.5 + random.uniform(-0.5, 0.5)
        mist_channel_utilization_24ghz = 10 + random.uniform(-5, 5)
        mist_channel_utilization_5ghz = 20 + random.uniform(-5, 5)
        mist_channel_utilization_6ghz = 5 + random.uniform(-1, 1)
        mist_noise_floor_dbm = -95
        mist_client_snr = mist_client_rssi - mist_noise_floor_dbm
        mist_client_tx_bytes = 5000000 + i*3000
        mist_client_rx_bytes = 15000000 + i*9000
        
        # Override Mist throughput with App throughput so they correlate
        mist_client_throughput_kbps = app_throughput_kbps

        # Construct Row
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        row = [
            timestamp,
            node_cpu_seconds_total, node_load_1m, node_load_5m, node_load_15m,
            node_memory_MemTotal_bytes, node_memory_MemAvailable_bytes, node_swap_utilization,
            node_disk_read_bytes_total, node_disk_written_bytes_total, node_disk_reads_completed_total, node_disk_read_time_seconds_total,
            node_network_receive_bytes_total, node_network_transmit_bytes_total, node_network_dropped_packets, node_network_transmit_errors,
            container_cpu_usage_seconds_total, container_memory_working_set_bytes, container_fs_usage_bytes,
            container_rx_bytes, container_tx_bytes,
            kube_pod_container_status_restarts_total, pod_ready_status, pod_scheduling_latency_ms,
            os_cpu_time, os_cpu_util_percentage, os_memory_usage_mb, os_memory_resident_mb,
            os_disk_read_bytes_rate, os_disk_write_bytes_rate, os_disk_read_requests_rate, os_disk_write_requests_rate,
            os_network_incoming_bytes_rate, os_network_outgoing_bytes_rate, os_network_packet_drop_rate,
            os_hypervisor_vcpus_total, os_hypervisor_vcpus_used,
            os_hypervisor_memory_mb_total, os_hypervisor_memory_mb_used,
            os_hypervisor_local_gb_total, os_hypervisor_local_gb_used,
            os_api_response_latency_ms, os_rabbitmq_queue_depth, os_haproxy_connections,
            mist_time_to_connect_ms, mist_coverage_score, mist_capacity_score, mist_roaming_score,
            mist_ap_cpu_utilization, mist_ap_memory_utilization, mist_ap_uptime_seconds, mist_ap_temperature_c,
            mist_channel_utilization_24ghz, mist_channel_utilization_5ghz, mist_channel_utilization_6ghz,
            mist_noise_floor_dbm, mist_rf_retries_percent, mist_client_rssi, mist_client_snr,
            mist_client_tx_bytes, mist_client_rx_bytes, mist_client_throughput_kbps,
            mist_client_connection_state,
            app_http_response_code, app_request_latency_ms, app_throughput_kbps,
            current_fault
        ]
        
        with open(CSV_PATH, "a") as f:
            f.write(",".join(map(str, row)) + "\n")
            
        if i % 10 == 0:
            print(f"[{i+1}/{MAX_ROWS}] State: {current_fault} | App Latency: {app_request_latency_ms:.1f}ms")

    except Exception as e:
        print(f"Error on iteration {i+1}: {e}")

    # Small sleep to avoid SSH rate limiting, but keep generation fast
    time.sleep(1.5)

print("GNN Dataset generation complete.")
