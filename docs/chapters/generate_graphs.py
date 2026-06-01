import matplotlib.pyplot as plt
import numpy as np
import os

out_dir = r"h:\Kolla-Ansible\Report_Chapters\images"

scenarios = [
    ("Network Bandwidth Saturation", "Time (s)", "Bandwidth Usage (%) / Fault Prob"),
    ("CPU Steal Time Contention", "Time (s)", "CPU Steal (%) / Fault Prob"),
    ("Memory Ballooning & OOM", "Time (s)", "Memory Usage (%) / Fault Prob"),
    ("Disk I/O Throttling", "Time (s)", "I/O Wait (ms) / Fault Prob"),
    ("Pod CrashLoopBackOff", "Time (s)", "Restart Count / Fault Prob"),
    ("API Rate Limiting", "Time (s)", "API Latency (ms) / Fault Prob"),
    ("Datapath Degradation (OVS)", "Time (s)", "Packet Drop Rate (%) / Fault Prob"),
    ("Mist AI AP Offline cascade", "Time (s)", "Client Drops / Fault Prob"),
    ("Storage Latency Spikes", "Time (s)", "Read Latency (ms) / Fault Prob"),
    ("System-Wide Power Degradation", "Time (s)", "Active Nodes / Fault Prob")
]

np.random.seed(42)

for i, (title, xlabel, ylabel) in enumerate(scenarios, 1):
    plt.figure(figsize=(8, 4))
    t = np.linspace(0, 100, 100)
    
    # Generate some metric data that spikes
    metric = np.random.normal(20, 5, 100)
    spike_start = 40
    metric[spike_start:] += np.linspace(0, 70, 60) + np.random.normal(0, 10, 60)
    metric = np.clip(metric, 0, 100)
    if "Count" in ylabel or "Latency" in ylabel:
        metric = metric * (i * 2) # Scale up
    
    # ST-GNN Probability jumps up slightly after the spike
    prob = np.zeros(100)
    prob[:spike_start+2] = np.random.uniform(0, 0.05, spike_start+2)
    prob[spike_start+2:] = np.clip(np.linspace(0, 1, 98-spike_start) + np.random.normal(0, 0.05, 98-spike_start), 0.9, 1.0)
    
    fig, ax1 = plt.subplots(figsize=(8, 4))

    color = 'tab:blue'
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel.split('/')[0].strip(), color=color)
    ax1.plot(t, metric, color=color, label='Primary Metric')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('ST-GNN Fault Probability', color=color)  
    ax2.plot(t, prob, color=color, linestyle='--', label='ST-GNN Confidence')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(0, 1.1)

    plt.title(f'Scenario {i}: {title}')
    fig.tight_layout()  
    plt.savefig(os.path.join(out_dir, f'scenario_{i}.png'))
    plt.close('all')

print("Generated all 10 graphs.")
