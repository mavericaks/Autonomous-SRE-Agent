# RCA Execution Log: Scenario 1: Noisy Neighbor (OS -> K8s -> App)

**Timestamp:** 2026-05-25 21:35:38
**Injected Fault:** `Noisy_Neighbor_OS_CPU_Exhaustion`

## 1. Metric Contention Timeline
| Tick (Seconds) | Layer | Metric Anomalies Detected |
|---|---|---|
| 2s | OS | node_load_1m spikes to 12.0; CPU iowait increases. |
| 4s | K8s | Video streaming pod CPU throttled; Redis cache latency spikes. |
| 6s | App | E-Commerce throughput drops 60%; HTTP 503 errors begin. |

## 2. Model RCA Comparison
| Architecture | Predicted Root Cause | Confidence | MTTD (Seconds) |
|---|---|---|---|
| **Baseline (Prometheus)** | `App_HTTP_503_Spike` | N/A | 12.0s |
| **Pure GNN (Spatial)** | `App_Failure_Cascade` | 72% | 2.5s |
| **ST-GNN (Spatio-Temporal)** | `Noisy_Neighbor_OS_CPU_Exhaustion` | 96.4% | 1.8s |

## 3. Automated Recovery Action Taken
The ST-GNN identified the correct root cause and triggered the following autonomous playbook:
> `kubectl evict pod stress-batch-processor-pod -n default`

> Service restored to 100% throughput.
