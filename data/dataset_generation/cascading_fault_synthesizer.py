import os
import random
import math
from datetime import datetime, timezone, timedelta

CSV_PATH = r"h:\Kolla-Ansible\datasets\telemetry_dataset_gnn_20k_cascading.csv"

COLUMNS = [
    "app_http_response_code", "app_request_latency_ms", "app_throughput_kbps", 
    "node_cpu_seconds_total", "node_load_1m", "node_load_5m", "node_load_15m", 
    "node_memory_MemTotal_bytes", "node_memory_MemAvailable_bytes", "node_swap_utilization", 
    "node_disk_read_bytes_total", "node_disk_written_bytes_total", "node_disk_reads_completed_total", "node_disk_read_time_seconds_total", 
    "node_network_receive_bytes_total", "node_network_transmit_bytes_total", "node_network_dropped_packets", "node_network_transmit_errors", 
    "container_cpu_usage_seconds_total", "container_memory_working_set_bytes", "container_fs_usage_bytes", "container_rx_bytes", "container_tx_bytes", 
    "kube_pod_container_status_restarts_total", "pod_ready_status", "pod_scheduling_latency_ms", 
    "os_cpu_time", "os_cpu_util_percentage", "os_memory_usage_mb", "os_memory_resident_mb", 
    "os_disk_read_bytes_rate", "os_disk_write_bytes_rate", "os_disk_read_requests_rate", "os_disk_write_requests_rate", 
    "os_network_incoming_bytes_rate", "os_network_outgoing_bytes_rate", "os_network_packet_drop_rate", 
    "os_hypervisor_vcpus_total", "os_hypervisor_vcpus_used", "os_hypervisor_memory_mb_total", "os_hypervisor_memory_mb_used", 
    "os_hypervisor_local_gb_total", "os_hypervisor_local_gb_used", "os_api_response_latency_ms", "os_rabbitmq_queue_depth", "os_haproxy_connections", 
    "mist_time_to_connect_ms", "mist_coverage_score", "mist_capacity_score", "mist_roaming_score", 
    "mist_ap_cpu_utilization", "mist_ap_memory_utilization", "mist_ap_uptime_seconds", "mist_ap_temperature_c", 
    "mist_channel_utilization_24ghz", "mist_channel_utilization_5ghz", "mist_channel_utilization_6ghz", 
    "mist_noise_floor_dbm", "mist_rf_retries_percent", "mist_client_rssi", "mist_client_snr", 
    "mist_client_tx_bytes", "mist_client_rx_bytes", "mist_client_throughput_kbps", "mist_client_connection_state",
    "Root_Cause_Fault_Label"
]

FAULTS = [
    "OS_CPU_Exhaustion", "OS_Memory_Leak", "OS_Disk_IO_Saturation", "OS_Network_Partition",
    "K8s_Pod_CrashLoopBackOff", "K8s_API_Server_Overload", "K8s_Node_NotReady", "K8s_Node_CPU_Exhaustion",
    "Mist_AP_Offline", "Mist_Switch_Port_Flap", "Mist_RF_Interference",
    "App_Memory_Leak", "App_DB_Connection_Timeout"
]

class CascadeEngine:
    def __init__(self):
        # Base independent variables (healthy state)
        self.os_cpu_base = 40.0
        self.os_mem_base = 10000.0
        self.os_disk_io_base = 200000.0
        self.os_net_drop_base = 0.1
        
        self.k8s_api_base = 25.0
        self.k8s_pod_restarts = 0
        self.k8s_node_ready = 1
        self.k8s_node_cpu_stress = 0.0 # specific to K8s CPU fault
        
        self.mist_ap_cpu = 20.0
        self.mist_interference = 2.0
        self.mist_connection = 1
        
        self.app_mem_base = 250.0
        self.app_db_lat = 12.0
        
        self.current_fault = "No_Fault"
        self.ticks_in_state = 0
        self.target_state_duration = 300

    def rw(self, val, min_v, max_v, step):
        """Random walk with boundaries."""
        new_val = val + random.uniform(-step, step)
        return max(min_v, min(max_v, new_val))

    def transition(self, current, target, rate):
        """Smooth exponential transition towards a target."""
        return current * (1 - rate) + target * rate

    def update(self):
        self.ticks_in_state += 1
        
        # State Machine Transitions
        if self.ticks_in_state > self.target_state_duration:
            if self.current_fault == "No_Fault":
                self.current_fault = random.choice(FAULTS)
                self.target_state_duration = random.randint(150, 300)
            else:
                self.current_fault = "No_Fault"
                self.target_state_duration = random.randint(300, 600)
            self.ticks_in_state = 0
            
            # Reset triggers on recovery
            if self.current_fault == "No_Fault":
                self.k8s_pod_restarts = 0
                self.k8s_node_ready = 1
                self.mist_connection = 1
                self.k8s_node_cpu_stress = 0.0

        # Healthy random walks (adds noise so NO feature is ever completely static/zero)
        self.os_cpu_base = self.rw(self.os_cpu_base, 30, 50, 1.5)
        self.os_mem_base = self.rw(self.os_mem_base, 9000, 11000, 50.0)
        self.os_disk_io_base = self.rw(self.os_disk_io_base, 150000, 250000, 5000.0)
        self.os_net_drop_base = self.rw(self.os_net_drop_base, 0.01, 0.5, 0.05)
        self.k8s_api_base = self.rw(self.k8s_api_base, 15, 35, 2.0)
        self.k8s_node_cpu_stress = self.rw(self.k8s_node_cpu_stress, 0.0, 5.0, 0.5)
        self.mist_ap_cpu = self.rw(self.mist_ap_cpu, 15, 25, 1.0)
        self.mist_interference = self.rw(self.mist_interference, 0.5, 3.0, 0.2)
        self.app_mem_base = self.rw(self.app_mem_base, 200, 300, 5.0)
        self.app_db_lat = self.rw(self.app_db_lat, 8, 18, 0.5)

        # Fault Specific Drivers
        if self.current_fault == "OS_CPU_Exhaustion":
            self.os_cpu_base = self.transition(self.os_cpu_base, 99.9, 0.08)
        elif self.current_fault == "OS_Memory_Leak":
            self.os_mem_base += 15.0 # Strict linear leak
            self.os_mem_base = min(self.os_mem_base, 128000.0)
        elif self.current_fault == "OS_Disk_IO_Saturation":
            self.os_disk_io_base = self.transition(self.os_disk_io_base, 1000000.0, 0.1)
        elif self.current_fault == "OS_Network_Partition":
            self.os_net_drop_base = self.transition(self.os_net_drop_base, 100.0, 0.2) # 100% packet drop
            
        elif self.current_fault == "K8s_Pod_CrashLoopBackOff":
            if self.ticks_in_state % 15 == 0:
                self.k8s_pod_restarts += 1
        elif self.current_fault == "K8s_API_Server_Overload":
            self.k8s_api_base = self.transition(self.k8s_api_base, 8000.0, 0.05)
        elif self.current_fault == "K8s_Node_NotReady":
            self.k8s_node_ready = 0
        elif self.current_fault == "K8s_Node_CPU_Exhaustion":
            # This is specific to a container running a stress loop
            self.k8s_node_cpu_stress = self.transition(self.k8s_node_cpu_stress, 100.0, 0.1)
            
        elif self.current_fault == "Mist_AP_Offline":
            self.mist_connection = 0
        elif self.current_fault == "Mist_Switch_Port_Flap":
            self.mist_connection = 1 if self.ticks_in_state % 3 == 0 else 0
        elif self.current_fault == "Mist_RF_Interference":
            self.mist_interference = self.transition(self.mist_interference, 85.0, 0.1)
            
        elif self.current_fault == "App_Memory_Leak":
            self.app_mem_base += 8.0
        elif self.current_fault == "App_DB_Connection_Timeout":
            self.app_db_lat = self.transition(self.app_db_lat, 15000.0, 0.2)


print(f"Starting MASSIVE Cascading Fault GNN Dataset Generation (20,000 rows)...")
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
with open(CSV_PATH, "w") as f:
    f.write(",".join(COLUMNS) + "\n")

MAX_ROWS = 20000
engine = CascadeEngine()
current_time = datetime.now(timezone.utc) - timedelta(seconds=15 * MAX_ROWS)

# Monotonically increasing counters
node_cpu_sec = 15000.0
container_cpu_sec = 5000.0
node_net_rx = 1000000.0
node_net_tx = 1000000.0
node_disk_read_tot = 500000.0
node_disk_write_tot = 500000.0
node_disk_reads_completed = 1000.0
node_disk_read_time = 50.0

for i in range(MAX_ROWS):
    current_time += timedelta(seconds=15)
    engine.update()
    
    # ---------------------------------------------------------
    # CASCADING PHYSICS AND MATHEMATICAL CORRELATION
    # ---------------------------------------------------------
    
    # OS Net Partition causes K8s Node failure & AP disconnect
    if engine.os_net_drop_base > 80.0:
        engine.k8s_node_ready = 0
        engine.mist_connection = 0

    # 1. OS LAYER Physics
    os_cpu_util = engine.os_cpu_base
    if engine.current_fault == "K8s_Node_CPU_Exhaustion":
        # Container CPU explicitly drives up OS CPU
        os_cpu_util = min(100.0, engine.os_cpu_base + engine.k8s_node_cpu_stress * 0.9)

    os_cpu_time = os_cpu_util * 150.0 + random.uniform(-10, 10)
    os_mem_mb = engine.os_mem_base
    os_disk_read = engine.os_disk_io_base * 0.05 + random.uniform(-15, 15)
    os_disk_write = engine.os_disk_io_base * 0.95 + random.uniform(-20, 20)
    
    os_net_in = 326000.0 * (1.0 - (engine.os_net_drop_base / 100.0)) + random.uniform(-5000, 5000)
    os_net_out = 326000.0 * (1.0 - (engine.os_net_drop_base / 100.0)) + random.uniform(-5000, 5000)
    
    # OS API suffers from high CPU and Memory constraints
    os_api_lat = 25.0 + math.exp(os_cpu_util / 20.0) + (os_mem_mb / 2500.0)**2 + random.uniform(-2, 2)

    # 2. K8S LAYER Physics
    # K8s API suffers from OS API delays, native overload, and Node failures
    k8s_api_final = engine.k8s_api_base + (os_api_lat * 0.6) + ((1 - engine.k8s_node_ready) * 2500.0)
    
    # Node Load is driven by OS CPU, Disk IO, and specific K8s CPU stress
    k8s_load_1m = (os_cpu_util / 20.0) + (engine.os_disk_io_base / 2000000.0) + random.uniform(-0.2, 0.2)
    k8s_load_5m = k8s_load_1m * 0.9 + random.uniform(-0.1, 0.1)
    k8s_load_15m = k8s_load_1m * 0.8 + random.uniform(-0.1, 0.1)
    
    # Stationary counters instead of monotonic growth
    node_cpu_sec = 10000.0 + (k8s_load_1m * 100.0) + random.uniform(-50, 50)
    container_cpu_sec = 1057.0 + (engine.k8s_node_cpu_stress * 500.0) + (os_cpu_util * 10.0) + random.uniform(-20, 20)
    node_net_rx = 1012185581.0 + os_net_in * 10.0 + random.uniform(-1000, 1000)
    node_net_tx = 547246765.0 + os_net_out * 10.0 + random.uniform(-1000, 1000)
    node_disk_read_tot = 6833943552.0 + os_disk_read * 1024.0 + random.uniform(-1000, 1000)
    node_disk_write_tot = 1555470336.0 + os_disk_write * 1024.0 + random.uniform(-1000, 1000)
    node_disk_reads_completed = 93375.0 + (os_disk_read * 2.0) + random.uniform(0, 10)
    node_disk_read_time = 3964.0 + (os_disk_read / 10.0) + random.uniform(0, 5)
    
    pod_sched_lat = 15.0 + math.exp(k8s_api_final / 1200.0) + (engine.os_disk_io_base / 20000.0) + random.uniform(-3, 3)
    pod_ready = 1 if engine.k8s_node_ready == 1 and engine.k8s_pod_restarts < 6 else 0

    # 3. MIST AI LAYER Physics
    mist_retries = 3.0 + engine.mist_interference + (engine.os_net_drop_base / 8.0) + random.uniform(-0.5, 0.5)
    mist_capacity = max(0.0, 100.0 - engine.mist_interference * 2.2) + random.uniform(-1, 1)
    mist_time_to_connect = 250.0 + (mist_retries * 60.0) + ((1 - engine.mist_connection) * 9000.0) + random.uniform(-10, 10)
    mist_throughput = 15000.0 * engine.mist_connection * math.exp(-mist_retries / 25.0) + random.uniform(-500, 500)

    # 4. APP LAYER Physics
    # App latency is the grand cascade of ALL underlying constraints
    app_lat = 45.0 + math.exp(os_cpu_util / 20.0) + (engine.os_disk_io_base / 20000.0) + (pod_sched_lat * 0.15) + engine.app_db_lat + (mist_time_to_connect * 0.05) + random.uniform(-5, 5)
    
    app_response_code = 200
    if pod_ready == 0 or engine.mist_connection == 0 or engine.os_net_drop_base > 40.0 or app_lat > 2500.0 or engine.k8s_pod_restarts > 3:
        app_response_code = 503
        app_lat = 5000.0 + random.uniform(-100, 100) # Timeout
        app_throughput = 0.0 + random.uniform(0, 10)
    else:
        app_throughput = mist_throughput * 0.9 + random.uniform(-200, 200)

    # Compile the 66-element row (65 features + 1 label) exactly matching COLUMNS
    row = [
        app_response_code, app_lat, app_throughput,
        node_cpu_sec, k8s_load_1m, k8s_load_5m, k8s_load_15m,
        16720404480, max(100000, 16720404480 - (os_mem_mb * 1000000) - random.uniform(0, 500000)), 0.0 + random.uniform(0, 0.01),
        node_disk_read_tot, node_disk_write_tot, node_disk_reads_completed, node_disk_read_time,
        node_net_rx, node_net_tx, engine.os_net_drop_base + random.uniform(0, 0.5), engine.os_net_drop_base * 0.5 + random.uniform(0, 0.2),
        container_cpu_sec, engine.app_mem_base * 1000000 + random.uniform(-50000, 50000), 10000000 + random.uniform(-1000, 1000),
        os_net_in * 0.85 + random.uniform(-100, 100), os_net_out * 0.85 + random.uniform(-100, 100),
        engine.k8s_pod_restarts, pod_ready, pod_sched_lat,
        os_cpu_time, os_cpu_util, os_mem_mb, os_mem_mb + 4500 + random.uniform(-100, 100),
        os_disk_read, os_disk_write, os_disk_read / 12.0 + random.uniform(0, 1), os_disk_write / 12.0 + random.uniform(0, 1),
        os_net_in, os_net_out, engine.os_net_drop_base,
        64, 12 + int(os_cpu_util / 10) + random.randint(0, 2),
        128000, os_mem_mb, 1000, 280 + random.uniform(-5, 5),
        os_api_lat, 0 + random.uniform(0, 2), 55 + random.uniform(-5, 5),
        mist_time_to_connect, 99.0 + random.uniform(-0.5, 0), mist_capacity, 98.0 + random.uniform(-1, 0),
        engine.mist_ap_cpu, 42.0 + random.uniform(-2, 2), 86400+i*15, 46.5 + random.uniform(-1, 1),
        12.0 + random.uniform(-1, 1), 22.0 + random.uniform(-1, 1), 6.0 + random.uniform(-0.5, 0.5),
        -94.0 + random.uniform(-2, 2), mist_retries, -58.0 + random.uniform(-3, 3), 36.0 + random.uniform(-2, 2),
        1500000 + random.uniform(-10000, 10000), 25000000 + random.uniform(-100000, 100000), mist_throughput, engine.mist_connection,
        engine.current_fault
    ]
    
    with open(CSV_PATH, "a") as f:
        f.write(",".join(map(lambda x: str(round(x, 4)) if isinstance(x, float) else str(x), row)) + "\n")

    if i % 2000 == 0:
        print(f"[{i}/{MAX_ROWS}] Cascading Synthesis running...")

print("20k Cascading GNN Dataset generation complete.")
