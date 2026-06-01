import os
import random
import math
from datetime import datetime, timezone, timedelta

CSV_PATH = r"h:\Kolla-Ansible\datasets\telemetry_dataset_gnn_20k_advanced.csv"

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
    "app_http_response_code", "app_request_latency_ms", "app_throughput_kbps",
    "Fault_Label"
]

class SystemState:
    def __init__(self):
        # Initial Healthy Baseline
        self.os_cpu_util = 10.0
        self.k8s_load = 0.5
        self.mist_drops = 0.0
        self.pod_restarts = 0
        self.app_response_code = 200
        
        self.current_fault = "No_Fault"
        self.ticks_in_state = 0
        self.target_state_duration = 500

    def rw(self, val, min_v, max_v, step):
        return max(min_v, min(max_v, val + random.uniform(-step, step)))

    def transition(self, current, target, rate):
        return current * (1 - rate) + target * rate

    def update(self):
        self.ticks_in_state += 1
        
        # State Machine Transitions
        if self.ticks_in_state > self.target_state_duration:
            if self.current_fault == "No_Fault":
                # Enter a fault (distribute evenly)
                faults = ["K8s_Pod_Crash", "OS_CPU_Exhaustion", "Mist_Network_Congestion"]
                self.current_fault = random.choice(faults)
                self.target_state_duration = random.randint(150, 250) # Fault lasts ~45-60 mins
            else:
                self.current_fault = "No_Fault"
                self.target_state_duration = random.randint(300, 600) # Healthy lasts 1.5 - 2.5 hours
            self.ticks_in_state = 0
            
            if self.current_fault == "No_Fault":
                self.pod_restarts = 0
                self.app_response_code = 200

        # Physical Physics Engine
        if self.current_fault == "No_Fault":
            self.os_cpu_util = self.rw(self.os_cpu_util, 5, 20, 1.0)
            self.k8s_load = self.rw(self.k8s_load, 0.2, 0.8, 0.05)
            self.mist_drops = self.rw(self.mist_drops, 0, 5, 1.0)
            self.app_response_code = 200
            
        elif self.current_fault == "OS_CPU_Exhaustion":
            self.os_cpu_util = self.transition(self.os_cpu_util, 99.5, 0.05)
            self.k8s_load = self.transition(self.k8s_load, 25.0, 0.02)
            self.mist_drops = self.rw(self.mist_drops, 0, 5, 1.0)

        elif self.current_fault == "Mist_Network_Congestion":
            self.os_cpu_util = self.rw(self.os_cpu_util, 5, 20, 1.0)
            self.k8s_load = self.rw(self.k8s_load, 0.2, 1.5, 0.05)
            self.mist_drops = self.transition(self.mist_drops, 300.0, 0.08)

        elif self.current_fault == "K8s_Pod_Crash":
            self.os_cpu_util = self.rw(self.os_cpu_util, 5, 15, 1.0)
            self.k8s_load = self.transition(self.k8s_load, 5.0, 0.1)
            self.mist_drops = self.rw(self.mist_drops, 0, 5, 1.0)
            if self.ticks_in_state % 30 == 0:
                self.pod_restarts += 1
            if self.ticks_in_state > 10:
                self.app_response_code = 503

print(f"Starting ADVANCED Application-Centric GNN Dataset Generation...")
with open(CSV_PATH, "w") as f:
    f.write(",".join(COLUMNS) + "\n")

MAX_ROWS = 20000
state = SystemState()
current_time = datetime.now(timezone.utc) - timedelta(seconds=15 * MAX_ROWS)

# Monotonic counters
node_cpu_sec = 10000.0
container_cpu_sec = 400.0

for i in range(MAX_ROWS):
    current_time += timedelta(seconds=15)
    state.update()
    
    # ---------------------------------------------------------
    # LAYER 1: OpenStack (OS)
    # ---------------------------------------------------------
    os_cpu_time = state.os_cpu_util * 100
    os_mem_mb = 4000 + (state.os_cpu_util * 15) + random.uniform(-100, 100)
    os_api_lat = 20 + math.exp(state.os_cpu_util / 20.0) + random.uniform(-5, 5)
    
    os_net_in = 8000 + random.uniform(-1000, 1000)
    os_net_out = 8000 + random.uniform(-1000, 1000)
    if state.current_fault == "Mist_Network_Congestion":
        os_net_in *= 0.5
        os_net_out *= 0.5
        
    os_disk_read = 200 + random.randint(-50, 50)
    
    # ---------------------------------------------------------
    # LAYER 2: Kubernetes (K8s)
    # ---------------------------------------------------------
    node_cpu_sec += (state.k8s_load * 0.15)
    container_cpu_sec += (state.k8s_load * 0.05)
    
    pod_ready = 1 if state.app_response_code == 200 else 0
    pod_sched_lat = 10 + math.exp(state.k8s_load / 5.0)

    # ---------------------------------------------------------
    # LAYER 3: Mist AI Network (Mist)
    # ---------------------------------------------------------
    mist_retries = 2.0 + (state.mist_drops / 10.0) + random.uniform(-0.5, 0.5)
    mist_capacity = max(0, 100 - (state.mist_drops / 3.0))
    mist_time_to_connect = 200 + (state.mist_drops * 5.0) + random.uniform(-20, 20)

    # ---------------------------------------------------------
    # LAYER 4: Application Layer (App)
    # ---------------------------------------------------------
    # Non-linear correlation from infrastructure to application!
    # Latency goes up exponentially with OS CPU or K8s Load
    app_lat = 40 + math.exp(state.os_cpu_util / 16.0) + math.exp(state.k8s_load / 2.0) + random.uniform(-5, 5)
    if state.app_response_code == 503:
        app_lat = 5000.0 # Timeout

    # Throughput drops logarithmically with network drops
    app_throughput = 12000.0 * math.exp(-state.mist_drops / 50.0) + random.uniform(-500, 500)
    if state.app_response_code == 503:
        app_throughput = 0.0

    # Build the row
    row = [
        current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        node_cpu_sec, state.k8s_load, state.k8s_load*0.9, state.k8s_load*0.8,
        16000000000, 8000000000 - (state.os_cpu_util * 10000000), 0.0,
        os_disk_read * 512, os_disk_read * 512, 10, 1.2,
        os_net_in, os_net_out, state.mist_drops, 0,
        container_cpu_sec, 250000000, 10000000,
        150000, 120000,
        state.pod_restarts, pod_ready, pod_sched_lat,
        os_cpu_time, state.os_cpu_util, os_mem_mb, os_mem_mb + 4000,
        os_disk_read, os_disk_read, 10, 10,
        os_net_in, os_net_out, state.mist_drops,
        64, 12 + int(state.os_cpu_util / 10),
        128000, 35000, 1000, 250,
        os_api_lat, 0, 45,
        mist_time_to_connect, 99.0, mist_capacity, 98.0,
        15.0, 40.0, 86400+i*15, 45.5,
        10.0, 20.0, 5.0,
        -95.0, mist_retries, -60.0, 35.0,
        5000000, 15000000, app_throughput,
        1,
        state.app_response_code, app_lat, app_throughput,
        state.current_fault
    ]
    
    with open(CSV_PATH, "a") as f:
        f.write(",".join(map(str, row)) + "\n")

    if i % 2000 == 0:
        print(f"[{i}/{MAX_ROWS}] Advanced Synthesis...")

print("Advanced GNN Dataset generation complete.")
