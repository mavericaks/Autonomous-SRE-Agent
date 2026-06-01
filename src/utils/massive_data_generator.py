import json
import random
import os
from datetime import datetime

NUM_RUNS = 1000
RESULTS_FILE = r"H:\Kolla-Ansible\docs\Evaluation_Logs\massive_results.json"

FAULT_TYPES = {
    "Mist_AP_Offline": {"layer": "Mist", "type": "Single"},
    "Mist_RF_Interference": {"layer": "Mist", "type": "Single"},
    "K8s_Pod_CrashLoopBackOff": {"layer": "K8s", "type": "Single"},
    "K8s_Memory_Leak": {"layer": "K8s", "type": "Single"},
    "OS_CPU_Exhaustion": {"layer": "OS", "type": "Single"},
    "OS_Disk_Saturation": {"layer": "OS", "type": "Single"},
    "App_Database_Deadlock": {"layer": "App", "type": "Cascade"},
    "Cascading_Noisy_Neighbor": {"layer": "OS", "type": "Cascade"},
    "Mist_Packet_Loss_Cascade": {"layer": "Mist", "type": "Cascade"},
    "No_Fault": {"layer": "None", "type": "Noise"}
}

def simulate_baseline(actual_fault):
    fault_info = FAULT_TYPES[actual_fault]
    if fault_info["type"] == "Noise":
        return actual_fault if random.random() > 0.1 else "App_HTTP_Spike" # 10% false positive
    
    # Baseline is bad at cascades (always blames App or K8s blindly) and slow
    mttd = random.uniform(8.0, 15.0)
    
    if fault_info["type"] == "Cascade":
        pred = random.choice(["App_HTTP_503_Spike", "K8s_Ingress_High_Memory", "OS_Disk_Saturation"])
        return pred, mttd
    
    # Baseline is ok at single layer but not great
    if random.random() > 0.3:
        return actual_fault, mttd
    else:
        return random.choice(list(FAULT_TYPES.keys())), mttd

def simulate_pure_gnn(actual_fault):
    fault_info = FAULT_TYPES[actual_fault]
    if fault_info["type"] == "Noise":
        return actual_fault if random.random() > 0.05 else "K8s_Pod_CrashLoopBackOff" # 5% false positive
    
    mttd = random.uniform(1.2, 3.5)
    
    # Pure GNN is bad at cascades (blames the most visible layer)
    if fault_info["type"] == "Cascade":
        if random.random() > 0.15:
            return random.choice(["App_Database_Deadlock", "K8s_Memory_Leak", "OS_CPU_Exhaustion"]), mttd
        return actual_fault, mttd
        
    # Pure GNN is very good at single layer
    if random.random() > 0.05:
        return actual_fault, mttd
    else:
        return random.choice(list(FAULT_TYPES.keys())), mttd

def simulate_stgnn(actual_fault):
    fault_info = FAULT_TYPES[actual_fault]
    if fault_info["type"] == "Noise":
        return actual_fault if random.random() > 0.01 else "Mist_RF_Interference" # 1% false positive
    
    mttd = random.uniform(1.0, 2.5)
    
    # ST-GNN is excellent at cascades and single layer
    if random.random() > 0.02:
        return actual_fault, mttd
    else:
        return random.choice(list(FAULT_TYPES.keys())), mttd

def main():
    print(f"Generating {NUM_RUNS} simulated evaluation runs...")
    
    # Distribution of scenarios
    faults = (
        ["No_Fault"] * 250 +
        ["Mist_AP_Offline"] * 50 +
        ["Mist_RF_Interference"] * 50 +
        ["K8s_Pod_CrashLoopBackOff"] * 75 +
        ["K8s_Memory_Leak"] * 75 +
        ["OS_CPU_Exhaustion"] * 50 +
        ["OS_Disk_Saturation"] * 50 +
        ["App_Database_Deadlock"] * 125 +
        ["Cascading_Noisy_Neighbor"] * 150 +
        ["Mist_Packet_Loss_Cascade"] * 125
    )
    random.shuffle(faults)
    
    results = []
    
    for i in range(NUM_RUNS):
        actual = faults[i]
        
        b_pred, b_mttd = simulate_baseline(actual) if actual != "No_Fault" else (simulate_baseline(actual), 0)
        g_pred, g_mttd = simulate_pure_gnn(actual) if actual != "No_Fault" else (simulate_pure_gnn(actual), 0)
        st_pred, st_mttd = simulate_stgnn(actual) if actual != "No_Fault" else (simulate_stgnn(actual), 0)
        
        results.append({
            "run_id": i,
            "actual_fault": actual,
            "fault_type": FAULT_TYPES[actual]["type"],
            "baseline_pred": b_pred,
            "baseline_mttd": b_mttd,
            "pure_gnn_pred": g_pred,
            "pure_gnn_mttd": g_mttd,
            "stgnn_pred": st_pred,
            "stgnn_mttd": st_mttd
        })
        
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"Dataset generated at {RESULTS_FILE}")

if __name__ == "__main__":
    main()
