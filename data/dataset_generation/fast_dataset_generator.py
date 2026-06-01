import json
import time
import os
import random
from datetime import datetime, timezone, timedelta

# Artifact path
CSV_PATH = r"h:\Kolla-Ansible\datasets\telemetry_dataset_gnn_20k_synthetic.csv"

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

print(f"Starting FAST Application-Centric GNN Dataset Generation (20,000 rows). Writing to {CSV_PATH}")

MAX_ROWS = 20000
current_fault = "No_Fault"
fault_types = ["K8s_Pod_Crash", "OS_CPU_Exhaustion", "Mist_Network_Congestion"]

# Generate time series starting from a few hours ago
current_time = datetime.now(timezone.utc) - timedelta(seconds=15 * MAX_ROWS)

for i in range(MAX_ROWS):
    current_time += timedelta(seconds=15)
    
    # Random Fault State Machine
    if current_fault == "No_Fault":
        if random.random() < 0.05: # 5% chance to enter a fault state
            current_fault = random.choice(fault_types)
    else:
        if random.random() < 0.10: # 10% chance to recover
            current_fault = "No_Fault"

    # ==========================================
    # SYNTHESIZE METRICS BASED ON FAULT STATE
    # ==========================================
    
    # --- Baselines (Healthy) ---
    app_http_response_code = 200
    app_request_latency_ms = random.uniform(40, 80)
    app_throughput_kbps = random.uniform(8000, 15000)
    
    os_cpu_util_percentage = random.uniform(5, 15)
    os_memory_usage_mb = random.randint(4000, 5000)
    os_memory_resident_mb = random.randint(8000, 8500)
    
    os_disk_read_bytes_rate = random.randint(100, 500)
    os_disk_write_bytes_rate = random.randint(100, 500)
    os_disk_read_requests_rate = random.randint(5, 20)
    os_disk_write_requests_rate = random.randint(5, 20)
    
    os_network_incoming_bytes_rate = random.randint(5000, 10000)
    os_network_outgoing_bytes_rate = random.randint(5000, 10000)
    os_network_packet_drop_rate = 0
    
    os_hypervisor_vcpus_total = 64
    os_hypervisor_vcpus_used = random.randint(12, 16)
    os_hypervisor_memory_mb_total = 128000
    os_hypervisor_memory_mb_used = random.randint(30000, 40000)
    os_hypervisor_local_gb_total = 1000
    os_hypervisor_local_gb_used = 250
    
    node_load_1m = random.uniform(0.3, 0.8)
    node_load_5m = random.uniform(0.3, 0.6)
    node_load_15m = random.uniform(0.3, 0.5)
    
    node_memory_MemTotal_bytes = 16000000000
    node_memory_MemAvailable_bytes = random.randint(8000000000, 10000000000)
    
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

    # --- Apply Fault Contexts ---
    if current_fault == "K8s_Pod_Crash":
        kube_pod_container_status_restarts_total = random.randint(3, 15)
        pod_ready_status = 0
        pod_scheduling_latency_ms = random.uniform(2000, 8000)
        app_http_response_code = 503
        app_request_latency_ms = 5000.0 # Timeout
        app_throughput_kbps = 0.0
        node_load_1m = random.uniform(1.5, 3.0)
    
    elif current_fault == "OS_CPU_Exhaustion":
        os_cpu_util_percentage = random.uniform(95, 100)
        os_api_response_latency_ms = random.uniform(3000, 10000)
        node_load_1m = random.uniform(15, 25)
        app_throughput_kbps = random.uniform(100, 1000)
        app_request_latency_ms = random.uniform(2000, 5000)
        os_hypervisor_vcpus_used = 64
    
    elif current_fault == "Mist_Network_Congestion":
        mist_num_clients = random.randint(45, 80)
        mist_time_to_connect_ms = random.uniform(8000, 15000)
        mist_rf_retries_percent = random.uniform(40, 75)
        mist_client_rssi = random.uniform(-85, -95)
        mist_coverage_score = random.uniform(40, 60)
        mist_roaming_score = random.uniform(30, 50)
        node_network_dropped_packets = random.randint(100, 500)
        app_throughput_kbps = random.uniform(10, 80)
        app_request_latency_ms = random.uniform(1000, 3000)
        os_network_packet_drop_rate = random.randint(50, 200)

    # Derived/Correlated Metrics
    os_cpu_time = os_cpu_util_percentage * 100 

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

    os_rabbitmq_queue_depth = 0 if current_fault != "OS_CPU_Exhaustion" else random.randint(100, 500)
    os_haproxy_connections = 45 + random.randint(-5, 5)

    mist_capacity_score = 100 if current_fault != "Mist_Network_Congestion" else random.uniform(20, 40)
    mist_ap_cpu_utilization = 15 + random.uniform(-2, 2)
    mist_ap_memory_utilization = 40 + random.uniform(-2, 2)
    mist_ap_uptime_seconds = 86400 + i*15
    mist_ap_temperature_c = 45.5 + random.uniform(-0.5, 0.5)
    mist_channel_utilization_24ghz = 10 + random.uniform(-5, 5)
    mist_channel_utilization_5ghz = 20 + random.uniform(-5, 5)
    mist_channel_utilization_6ghz = 5 + random.uniform(-1, 1)
    mist_noise_floor_dbm = -95
    mist_client_snr = mist_client_rssi - mist_noise_floor_dbm
    mist_client_tx_bytes = 5000000 + i*3000
    mist_client_rx_bytes = 15000000 + i*9000
    
    mist_client_throughput_kbps = app_throughput_kbps

    timestamp_str = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    row = [
        timestamp_str,
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
        
    if i % 2000 == 0:
        print(f"[{i}/{MAX_ROWS}] Generated...")

print("GNN Dataset generation complete.")
