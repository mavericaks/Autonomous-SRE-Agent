import json
import os
import glob
import matplotlib.pyplot as plt

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



LOG_DIR = os.path.join(BASE_DIR, "\docs\Evaluation_Logs")
list_of_files = glob.glob(os.path.join(LOG_DIR, "eval_results_*.json"))
if not list_of_files:
    print("No results found.")
    exit(1)

latest_file = max(list_of_files, key=os.path.getctime)
with open(latest_file, 'r') as f:
    results = json.load(f)

# Calculate Accuracy
total = len(results)
baseline_acc = sum(1 for r in results if r['baseline_pred'] == r['expected']) / total * 100
pure_gnn_acc = sum(1 for r in results if r['pure_gnn_pred'] == r['expected']) / total * 100
stgnn_acc = sum(1 for r in results if r['stgnn_pred'] == r['expected']) / total * 100

# Calculate MTTD
baseline_mttd = sum(r['baseline_mttd'] for r in results if r['baseline_pred'] == r['expected']) / (sum(1 for r in results if r['baseline_pred'] == r['expected']) or 1)
pure_gnn_mttd = sum(r['pure_gnn_mttd'] for r in results if r['pure_gnn_pred'] == r['expected']) / (sum(1 for r in results if r['pure_gnn_pred'] == r['expected']) or 1)
stgnn_mttd = sum(r['stgnn_mttd'] for r in results if r['stgnn_pred'] == r['expected']) / (sum(1 for r in results if r['stgnn_pred'] == r['expected']) or 1)

# Generate Accuracy Chart
labels = ['Baseline (Prom)', 'Pure GNN', 'ST-GNN (Ours)']
accuracies = [baseline_acc, pure_gnn_acc, stgnn_acc]
colors = ['#ff9999','#66b3ff','#99ff99']

plt.figure(figsize=(10, 6))
plt.bar(labels, accuracies, color=colors)
plt.title('RCA Accuracy Comparison (Multi-Layer Faults)')
plt.ylabel('Accuracy (%)')
plt.ylim(0, 110)
for i, v in enumerate(accuracies):
    plt.text(i, v + 2, f"{v:.1f}%", ha='center')
plt.savefig(os.path.join(LOG_DIR, "accuracy_comparison.png"))
plt.close()

# Generate MTTD Chart
mttds = [baseline_mttd, pure_gnn_mttd, stgnn_mttd]
plt.figure(figsize=(10, 6))
plt.bar(labels, mttds, color=['#ffcc99','#c2c2f0','#ffb3e6'])
plt.title('Mean Time To Detect (MTTD) Comparison')
plt.ylabel('Time (Seconds)')
for i, v in enumerate(mttds):
    plt.text(i, v + 0.5, f"{v:.1f}s", ha='center')
plt.savefig(os.path.join(LOG_DIR, "mttd_comparison.png"))
plt.close()

print(f"Charts generated successfully in {LOG_DIR}")
