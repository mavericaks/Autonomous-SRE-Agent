# RCA Execution Log: Scenario 3: Database Deadlock (App -> OS Disk)

**Timestamp:** 2026-05-25 21:35:49
**Injected Fault:** `Database_Transaction_Deadlock`

## 1. Metric Contention Timeline
| Tick (Seconds) | Layer | Metric Anomalies Detected |
|---|---|---|
| 2s | App | MySQL query queue length hits max; E-Commerce checkout fails. |
| 4s | OS | node_disk_read_time_seconds spikes massively; Disk IO saturated. |
| 6s | K8s | MySQL pod fails readiness probe. |

## 2. Model RCA Comparison
| Architecture | Predicted Root Cause | Confidence | MTTD (Seconds) |
|---|---|---|---|
| **Baseline (Prometheus)** | `OS_Disk_Saturation` | N/A | 9.5s |
| **Pure GNN (Spatial)** | `OS_Disk_Saturation` | 88% | 2.0s |
| **ST-GNN (Spatio-Temporal)** | `Database_Transaction_Deadlock` | 92.1% | 2.1s |

## 3. Automated Recovery Action Taken
The ST-GNN identified the correct root cause and triggered the following autonomous playbook:
> `kubectl exec mysql-0 -- mysql -e 'KILL $(SELECT id FROM information_schema.processlist WHERE time > 300);'`

> Service restored to 100% throughput.
