import sys
sys.path.append(os.path.join(BASE_DIR, ""))
from ml_models.stgnn_mathematical_critic import STGNNCritic
import csv

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



critic = STGNNCritic(model_dir=os.path.join(BASE_DIR, "\ml_models\models"))
rows = list(csv.DictReader(open(os.path.join(BASE_DIR, "\datasets\telemetry_dataset_gnn_20k_cascading.csv"))))

faults_to_test = ["OS_CPU_Exhaustion", "No_Fault", "K8s_Pod_CrashLoopBackOff",
                   "Mist_AP_Offline", "OS_Memory_Leak", "OS_Disk_IO_Saturation",
                   "K8s_Node_NotReady", "K8s_API_Server_Overload"]
for fault in faults_to_test:
    fault_rows = [r for r in rows if r["Root_Cause_Fault_Label"] == fault]
    if len(fault_rows) < 10:
        print(f"SKIP: {fault} (only {len(fault_rows)} rows)")
        continue
    start = len(fault_rows) // 2
    critic.telemetry_buffer = []
    for j in range(5):
        d = {}
        for k, v in fault_rows[start + j].items():
            if k != "Root_Cause_Fault_Label":
                try:
                    d[k] = float(v)
                except:
                    d[k] = 0.0
        critic.ingest_telemetry(d)
    preds = critic.evaluate()
    top = preds[0]
    match = "OK" if top["fault"] == fault else "MISMATCH"
    print(f"[{match}] TRUE: {fault:35s} PRED: {top['fault']:35s} ({top['probability']*100:.1f}%)")
