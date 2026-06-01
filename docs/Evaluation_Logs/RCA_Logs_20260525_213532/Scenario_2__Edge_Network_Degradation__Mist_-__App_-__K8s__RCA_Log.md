# RCA Execution Log: Scenario 2: Edge Network Degradation (Mist -> App -> K8s)

**Timestamp:** 2026-05-25 21:35:43
**Injected Fault:** `Mist_AP_Packet_Loss`

## 1. Metric Contention Timeline
| Tick (Seconds) | Layer | Metric Anomalies Detected |
|---|---|---|
| 1s | Mist Edge | SLE Throughput drops to 40%; AP packet retries surge. |
| 3s | App | Client connection retries cause 300% spike in active connections. |
| 5s | K8s | Ingress Controller Memory Working Set spikes; OOMKilled risk. |

## 2. Model RCA Comparison
| Architecture | Predicted Root Cause | Confidence | MTTD (Seconds) |
|---|---|---|---|
| **Baseline (Prometheus)** | `K8s_Ingress_High_Memory` | N/A | 15.0s |
| **Pure GNN (Spatial)** | `K8s_Memory_Leak` | 81% | 2.2s |
| **ST-GNN (Spatio-Temporal)** | `Mist_AP_Packet_Loss` | 94.8% | 1.5s |

## 3. Automated Recovery Action Taken
The ST-GNN identified the correct root cause and triggered the following autonomous playbook:
> `Mist API Trigger: AP Radio Reset -> Restore Capacity`

> Service restored to 100% throughput.
