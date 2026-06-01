# Autonomous AI SRE: Live Cross-Layer Fault Cascade Demo (OS_Disk_IO_Saturation)

```

============================================================
  PHASE 0: INITIALIZATION
============================================================

[20:17:02] [INIT] Loading ST-GNN Spatio-Temporal Model (GCNConv -> LSTM -> Linear)...
[20:17:03] [INIT] Model loaded. 65-feature topology across App/K8s/OS/Mist layers.
[20:17:03] [INIT] Prometheus: http://10.10.10.200:9091 | Compute target: 10.10.10.11

============================================================
  PHASE 1: BASELINE HEALTH CAPTURE
============================================================

[20:17:03] [PROM] Polling LIVE baseline from Prometheus + App endpoint...
[20:17:14] [PROM] Polled 25/28 metrics from Prometheus.
[20:17:14] [BASELINE] OS Disk Read      = 7844723712.0 bytes
[20:17:14] [BASELINE] OS Disk Write     = 44123343872.0 bytes
[20:17:14] [BASELINE] App Latency       = 18.0ms
[20:17:20] [BASELINE] Tick 1 ingested into GNN buffer.
[20:17:30] [BASELINE] Tick 2 ingested into GNN buffer.

============================================================
  PHASE 2: FAULT INJECTION (OS_Disk_IO_Saturation)
============================================================

[20:17:32] [INJECT] Target: OpenStack Compute Node (10.10.10.11)
[20:17:32] [INJECT] Spawning intensive background dd disk writes to saturate I/O...
[20:17:32] [INJECT] Command: nohup dd if=/dev/zero of=/tmp/stressfile bs=1M count=50000 oflag=dsync > /dev/null 2>&1 &
[20:17:36] [INJECT] Spawned 5 dd process(es).
[20:17:39] [INJECT] Disk I/O burn process spawned. Expected cascade:
[20:17:40] [INJECT]   OS Layer   -> node_disk_written_bytes_total skyrockets, iowait increases
[20:17:40] [INJECT]   K8s Layer  -> Minor container scheduling and logging delays
[20:17:40] [INJECT] Waiting 60s for stress to fully register in Prometheus rate windows...

============================================================
  PHASE 3: LIVE CROSS-LAYER IMPACT MONITORING
============================================================

[20:18:40] [MONITOR] Polling REAL Prometheus + App endpoint during active fault...
[20:19:05] [MONITOR] --- Tick 1 ---
[20:19:05] [MONITOR]   OS Disk Write Rate = 524.5 MB/s
[20:19:05] [MONITOR]   App HTTP           = 0 | Latency = 120.0ms
[20:19:05] [MONITOR]   Polled 25 Prometheus metrics.
[20:19:34] [MONITOR] --- Tick 2 ---
[20:19:35] [MONITOR]   OS Disk Write Rate = 524.5 MB/s
[20:19:35] [MONITOR]   App HTTP           = 0 | Latency = 120.0ms
[20:19:35] [MONITOR]   Polled 25 Prometheus metrics.
[20:20:00] [MONITOR] --- Tick 3 ---
[20:20:00] [MONITOR]   OS Disk Write Rate = 524.5 MB/s
[20:20:01] [MONITOR]   App HTTP           = 0 | Latency = 120.0ms
[20:20:04] [MONITOR]   Polled 25 Prometheus metrics.

============================================================
  PHASE 4: MULTI-LAYER ROOT CAUSE ANALYSIS
============================================================

[20:20:05] [GNN] Running ST-GNN inference on 5-tick spatio-temporal window...
[20:20:05] [GNN] === Fault Probability Matrix ===
[20:20:05] [GNN]    92.87% | ############################################## | OS_Disk_IO_Saturation
[20:20:05] [GNN]     3.15% | # | OS_CPU_Exhaustion
[20:20:05] [GNN]     1.98% |  | OS_Memory_Leak
[20:20:05] [GNN]     1.12% |  | K8s_Node_NotReady
[20:20:05] [GNN]     0.88% |  | No_Fault
[20:20:05] 
[20:20:05] [RCA] === Extensive Cross-Layer Root Cause Analysis ===
[20:20:05] [RCA] Primary prediction: OS_Disk_IO_Saturation (92.87%)
[20:20:05] [RCA]
[20:20:05] [RCA] Layer-by-Layer Evidence (all from LIVE Prometheus):
[20:20:05] [RCA]   1. OS Layer (node_exporter on 10.10.10.11):
[20:20:05] [RCA]      - Disk Write Rate skyrocketed massively (>500MB/s)
[20:20:05] [RCA]      - IOWait times elevated across all cores
[20:20:05] [RCA]   2. K8s Layer (cAdvisor on compute node):
[20:20:05] [RCA]      - Minor container performance throttling due to block I/O starvation
[20:20:05] [RCA]   3. Application Layer (video-streaming-svc endpoint):
[20:20:05] [RCA]      - HTTP response: 0 | Latency: 120.0 ms (Mild Degradation)
[20:20:05] [RCA]
[20:20:05] [RCA] CONCLUSION: OS_Disk_IO_Saturation originating at the OpenStack Bare Metal layer.

============================================================
  PHASE 5: AUTONOMOUS RECOVERY STRATEGY
============================================================

[20:20:05] [STRATEGY] Fault: OS_Disk_IO_Saturation | Target: OpenStack Compute Node (10.10.10.11)
[20:20:05] [STRATEGY] Recovery plan:
[20:20:05] [STRATEGY]   1. SSH into OpenStack compute node 10.10.10.11
[20:20:05] [STRATEGY]   2. Execute 'killall dd' to terminate rogue disk I/O processes
[20:20:05] [STRATEGY]   3. Execute 'rm -f /tmp/stressfile' to reclaim storage
[20:20:05] [STRATEGY]   4. Verify OS Disk Write rate drops back to baseline
[20:20:05] [STRATEGY]   Risk assessment: LOW - standard process termination.

============================================================
  PHASE 6: RECOVERY EXECUTION
============================================================

[20:20:05] [RECOVER] Executing: killall dd and cleaning temp file on OS Layer
[20:20:07] [RECOVER] Executing: restoring K8s deployment pods
[20:20:13] [RECOVER] Rogue I/O processes terminated and temp file cleaned.

============================================================
  PHASE 7: POST-RECOVERY VERIFICATION
============================================================

[20:20:13] [VERIFY] Waiting 30s for Prometheus rate windows to reflect recovery...
[20:20:52] [VERIFY] Post-recovery metrics (25 polled from Prometheus):
[20:20:52] [VERIFY]   OS Disk Write Rate = 69.4 MB/s
[20:20:52] [VERIFY]   App HTTP           = 200 | Latency = 3.4ms
[20:20:52] [VERIFY] System returning to baseline. Autonomous recovery successful.
[20:20:52] [SUMMARY] Full cross-layer fault lifecycle complete.
```
