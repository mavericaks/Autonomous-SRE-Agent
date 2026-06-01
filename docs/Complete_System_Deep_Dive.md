# Complete System Architecture: Every Module Analyzed

This document provides a systematic, exhaustive analysis of every component in the Autonomous AI SRE system. It covers the **Agentic AI Framework** (890 lines), the **Mathematical GNN Critic**, the **Chaos Orchestrator**, the **Data Synthesis Engine**, and all supporting infrastructure scripts.

---

## System Overview: The 3 Subsystems

The project consists of three distinct subsystems that work together:

| Subsystem | Location | Purpose |
|-----------|----------|---------|
| **Agentic AI Framework** | `ai-agent/main.py` (890 lines) | A FastAPI server running a LangChain ReAct agent with 10 infrastructure tools, multi-provider LLM routing, background alert pollers, and incident journaling |
| **Mathematical GNN Critic** | `ml_models/` | A PyTorch Spatio-Temporal GNN that provides deterministic mathematical root cause probabilities |
| **Chaos Orchestrator** | `chaos_engineering/` | Injects faults, monitors application health, bridges the GNN and LLM, and executes recovery |

---

## SUBSYSTEM 1: The Agentic AI Framework (`ai-agent/main.py`)

This is the heart of the system — an **890-line autonomous AI agent** deployed as a `systemd` service on the OpenStack controller node (`10.10.10.10:9999`). It uses the **LangChain ReAct (Reasoning + Acting)** paradigm where the LLM thinks step-by-step, invokes tools to gather data, reasons about the results, and then acts.

### 1.1 Deployment Architecture

The agent runs as a Linux daemon managed by `systemd`:
```ini
# ai-sre-agent.service
[Service]
ExecStart=/opt/ai-sre-agent/venv/bin/python /opt/ai-sre-agent/main.py
Restart=on-failure
RestartSec=5
```
The `deploy.sh` script automates the full setup:
1. Creates `/opt/ai-sre-agent/` on the controller.
2. Sets up a Python virtual environment.
3. Installs LangChain, FastAPI, Uvicorn, and provider SDKs.
4. Registers the systemd service for automatic restart on failure.

### 1.2 Multi-Provider LLM Smart Router (Lines 466-589)

The agent does NOT rely on a single LLM. It implements a **4-tier provider failover chain** with automatic escalation:

```
Priority Chain: Cerebras (Llama 3.3 70B) -> OpenRouter -> Groq
Escalation:     If output is uncertain -> Gemini 2.0 Flash (Deep Reasoning)
```

**How the routing works** (`smart_invoke()`, Lines 537-589):
1. The system tries Cerebras first (fastest inference, ~200ms).
2. If the response contains uncertainty keywords like `"unclear"`, `"cascading"`, or `"unable to determine"` (checked by `needs_reasoning_escalation()`, Lines 531-534), the system automatically **escalates to Google Gemini** for deeper cross-layer reasoning.
3. If any provider returns HTTP 429 (rate limit), the system silently falls through to the next provider.
4. If ALL providers fail, it raises an exception.

This means the system handles **thousands of alerts per day** without hitting API rate limits, and complex multi-layer faults get the most powerful reasoning model.

### 1.3 The 10 Infrastructure Tools (Lines 120-384)

The LLM does not blindly guess. It has 10 concrete tools (Python functions decorated with `@tool`) that give it real-time access to every layer of the infrastructure:

#### Cloud Layer Tools (OpenStack)
| Tool | What It Does | How |
|------|-------------|-----|
| `run_openstack_command` | Executes any OpenStack CLI command | Sources admin credentials, runs `bash -c`, caps output at 3000 chars |
| `run_shell_command` | Runs arbitrary diagnostics on the controller | `subprocess.run` with 30s timeout |
| `query_prometheus` | Queries both OpenStack AND K8s Prometheus | Parses `target|promql` format; K8s queries tunnel through `qrouter` namespace |

#### Edge Layer Tools (Kubernetes)
| Tool | What It Does | How |
|------|-------------|-----|
| `run_kubectl_command` | Executes kubectl on the K8s master | SSH tunnels through the Neutron router namespace: `sudo ip netns exec qrouter-XXX ssh ubuntu@172.16.0.74 'kubectl ...'` |

#### Network Layer Tools (Juniper Mist AI)
| Tool | What It Does | How |
|------|-------------|-----|
| `get_mist_device_inventory` | Lists all physical devices (APs, switches, gateways) with health stats | REST API call to `api.gc4.mist.com` with auth token |
| `get_mist_alarms` | Fetches active unacknowledged alarms | Filters by `ack=false` |
| `get_mist_sle_metrics` | Pulls Service Level Experience scores (coverage, capacity, roaming) | Queries WiFi/Wired/WAN SLE endpoints |
| `get_mist_marvis_actions` | Gets Juniper's built-in AI (Marvis) recommendations | Queries the Marvis insights API |
| `restart_mist_device` | Restarts a physical AP/switch/gateway | POST to device restart endpoint |
| `bounce_mist_port` | Disables and re-enables a switch port | POST with port list to bounce endpoint |

### 1.4 The ReAct Agent Loop (Lines 390-528)

The agent uses a carefully engineered **System Prompt** (Lines 390-463) that defines:
1. The complete environment layout (all IPs, all services, all layers).
2. A 5-step workflow: **Investigate -> Diagnose -> Plan -> Execute -> Verify**.
3. The exact ReAct format: `Thought -> Action -> Observation -> ... -> Final Answer`.

When an alert arrives, the agent enters a loop (max 15 iterations):
```
Thought: "I need to check K8s pod status"
Action: run_kubectl_command
Action Input: "kubectl get pods -A"
Observation: "video-streaming-server-xyz   0/1   CrashLoopBackOff"
Thought: "The video pod is crash-looping. Let me check the underlying VM CPU..."
Action: query_prometheus
Action Input: "openstack|100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
Observation: "98.5%"
Thought: "OpenStack CPU is at 98.5% which is causing the K8s pod to starve."
Final Answer: [AI-RCA] Root Cause: OpenStack CPU Exhaustion cascading to K8s pod failure.
```

Each iteration, the LLM decides which tool to call, reads the output, and reasons about what to do next. The `AgentExecutor` (Line 520) manages this loop with `max_iterations=15` and `handle_parsing_errors=True`.

### 1.5 Three Alert Ingestion Channels (Lines 599-863)

The agent receives alerts from three independent sources simultaneously:

#### Channel 1: Prometheus Alertmanager Webhook (Lines 761-827)
A FastAPI `POST /alert` endpoint that receives structured JSON from Prometheus Alertmanager. When an OpenStack node fires an alert (e.g., CPU > 90%), Alertmanager sends the webhook. The agent parses the labels, annotations, and severity, builds a human-readable summary, and dispatches it to `smart_invoke()`.

#### Channel 2: K8s Alert Poller (Lines 618-685)
A background daemon thread that polls the K8s Prometheus API every 60 seconds via the `qrouter` SSH tunnel. It maintains a `seen_alerts` set to avoid processing the same alert twice. When a new firing alert is detected, it constructs a prompt and dispatches it to the agent.

#### Channel 3: Mist Alarm Poller (Lines 688-746)
A background daemon thread that polls the Juniper Mist REST API every 60 seconds for unacknowledged alarms. It tracks seen alarm IDs and dispatches new alarms (e.g., AP offline, switch port flap) to the agent for cross-layer investigation.

### 1.6 Incident Journaling (Lines 96-114)
Every alert processed by the agent is persisted to disk as a JSONL file (`/opt/ai-sre-agent/incidents.jsonl`). Each record contains:
- The original alert payload
- The LLM's full analysis text
- Every tool call made (tool name + input)
- The provider used (Cerebras, Gemini, etc.)
- Timestamp

This creates a complete audit trail. The `/incidents` API endpoint (Line 866) returns all incidents as JSON.

### 1.7 API Endpoints Summary
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /alert` | Webhook | Receives Prometheus Alertmanager payloads |
| `POST /test` | Manual | Trigger the agent with a custom alert string |
| `GET /health` | Status | Returns agent version, provider chain, incident count |
| `GET /incidents` | Audit | Returns full incident journal |

---

## SUBSYSTEM 2: The Mathematical GNN Critic

### 2.1 Offline Training (`stgnn_model_trainer.py`, 186 lines)

**Data Pipeline:**
1. Loads 100,000 rows from `telemetry_dataset_gnn_100k_cascading.csv`.
2. Encodes 13 fault labels into integer classes via `LabelEncoder`.
3. Splits 54 metric columns into 4 node groups by prefix.
4. Normalizes all features to zero-mean unit-variance via `StandardScaler`.
5. Pads node features to uniform dimension (23) with zeros.
6. Constructs 99,995 sliding windows of size 5.

**Model Architecture (`RCA_STGNN`):**
- Two `GCNConv` layers (spatial extraction, 2-hop message passing).
- Block-diagonal adjacency matrix construction for batched graph processing.
- `nn.LSTM` layer (temporal extraction across 5-tick windows).
- `nn.Linear` classifier with `log_softmax` output.
- Trained with `NLLLoss` and `Adam` optimizer (lr=0.005).
- **Result: 99.2% test accuracy.**

### 2.2 Live Inference (`stgnn_mathematical_critic.py`, 133 lines)

**Stateful Architecture:**
- `STGNNCritic` class loads saved weights, scaler, and encoder on init.
- Maintains a `deque(maxlen=5)` buffer for rolling temporal context.
- `ingest_telemetry(dict)`: Scales live metrics, splits into 4 node groups, pads, appends to buffer.
- `evaluate()`: When buffer is full, constructs `[1, 5, 4, 23]` tensor, runs `torch.no_grad()` forward pass, returns sorted probability list.
- Inference time: <50ms on CPU.

### 2.3 Data Synthesis Engine (`cascading_fault_synthesizer.py`, 229 lines)

**`CascadeEngine` State Machine:**
- Maintains internal state for each layer (OS CPU, OS memory, K8s API, Mist AP, App DB latency).
- Uses a finite state machine to transition between 12 fault types and `No_Fault`.
- Fault durations: 300-600 ticks. Healthy durations: 800-1500 ticks.
- `rw()` function: Random walk for natural metric jitter.
- `transition()` function: Exponential smoothing toward fault targets.

**Cascading Physics:**
- OS API latency = `20 + e^(cpu/15) + (mem/1000)^2` (exponential + quadratic).
- K8s API latency = `k8s_base + OS_API_lat * 0.5 + (1 - node_ready) * 2000`.
- App latency = `40 + e^(cpu/18) + disk_io/10 + pod_sched * 0.1 + db_lat`.
- Cross-layer: OS network drop > 80% forces K8s node NotReady AND Mist AP offline.

---

## SUBSYSTEM 3: The Chaos Orchestrator

### 3.1 Core Orchestrator (`autonomous_orchestrator.py`, 270 lines)

**SSH Execution Layer:**
- `run()`: Blocking SSH command execution for queries.
- `fire()`: Fire-and-forget interactive shell for persistent background processes.

**Application Health Monitor:**
- `check_app_health()`: HTTP GET to `10.10.10.10:30080`, measures round-trip latency in ms.

**GNN Bridge:**
- `invoke_gnn_critic()`: Clears LSTM buffer, feeds 5-tick temporal sequence, returns top mathematical prediction.

**3 Fault Scenarios:**
1. **CPU Cascade**: Injects infinite loops on compute node, monitors app degradation, feeds GNN, recovers with `pkill`.
2. **Pod Crash**: Scales K8s deployment to 0 replicas via SSH tunnel, feeds GNN, recovers by scaling back to 2.
3. **Cross-Layer**: Simultaneously floods network (4 parallel `dd | ssh` streams) and kills CoreDNS. Phased recovery: kill flood first, then restore DNS.

### 3.2 LLM Prompt Patcher (`llm_recovery_actor.py`, 70 lines)
- Downloads `main.py` from the controller via SFTP.
- Uses 3 regex substitutions to replace all alert handler prompts with strict RCA-formatted prompts.
- Uploads patched file and restarts the `ai-sre-agent` systemd service.

### 3.3 Application Deployer (`deploy_video_app.py`, 132 lines)
- Deploys a multi-container video streaming stack to K8s via SSH tunnel.
- Creates: `video-streaming-server` (2x NGINX-RTMP), `video-encoder-worker` (2x CPU stress), `video-streaming-svc` (NodePort 30080/31935).

---

## COMPLETE REAL-TIME EXECUTION FLOW

Here is exactly what happens end-to-end when a fault occurs:

```
T=0s   [OpenStack]     CPU spikes to 100% on Compute1
T=2s   [K8s]           Video encoder pods starve for CPU cycles
T=5s   [Application]   HTTP latency exceeds 2000ms, video stream buffers
T=5s   [Prometheus]    Alert fires: "HighCPUUsage" on 10.10.10.11
       |
       v
T=6s   [Alertmanager]  Sends webhook POST to http://10.10.10.10:9999/alert
       |
       v
T=6s   [AI Agent]      FastAPI receives webhook, parses alert labels
       |
       v
T=7s   [Smart Router]  Tries Cerebras (Llama 3.3 70B) first
       |
       v
T=7s   [ReAct Loop]    
       |  Thought: "CPU alert on compute1, let me check the hypervisor"
       |  Action: query_prometheus("openstack|node_cpu_seconds_total...")
       |  Observation: "98.5%"
       |  Thought: "CPU is critically high. Let me check K8s pods..."
       |  Action: run_kubectl_command("kubectl get pods")
       |  Observation: "video-encoder-worker  0/2  Pending"
       |  Thought: "Pods can't schedule because the underlying VM is exhausted"
       |
       v
T=12s  [GNN Critic]    Orchestrator feeds 5-tick telemetry to LSTM buffer
       |                PyTorch forward pass: [99.2%] OS_CPU_Exhaustion
       |
       v
T=12s  [Governance]    LLM says "CPU Exhaustion" -> GNN says "CPU Exhaustion" -> MATCH
       |
       v
T=13s  [ReAct Loop]    
       |  Action: run_shell_command("pkill -9 -f hog.sh")
       |  Action: run_kubectl_command("kubectl rollout restart deployment video-encoder-worker")
       |  
       v
T=15s  [Verification]  Agent re-queries Prometheus: CPU dropped to 15%
       |                Agent re-checks pods: 2/2 Running
       |
       v
T=15s  [Incident Log]  Full record saved to /opt/ai-sre-agent/incidents.jsonl
       |                Contains: alert payload, all tool calls, LLM reasoning, GNN output
       |
       v
T=15s  [Application]   Video stream resumes. Latency: 150ms.
```

---

## TOTAL ENGINEERING SUMMARY

| Component | File | Lines | Key Engineering |
|-----------|------|-------|-----------------|
| AI Agent (LangChain ReAct) | `ai-agent/main.py` | **890** | Multi-provider LLM router, 10 infrastructure tools, 3 alert channels, ReAct reasoning loop, incident journal |
| Agent Deployment | `ai-agent/deploy.sh` | 63 | Systemd service, venv setup, auto-restart |
| ST-GNN Model Trainer | `stgnn_model_trainer.py` | 186 | GCN + LSTM, sliding windows, block-diagonal adjacency |
| ST-GNN Mathematical Critic | `stgnn_mathematical_critic.py` | 133 | Stateful deque buffer, live tensor inference |
| Cascading Fault Synthesizer | `cascading_fault_synthesizer.py` | 229 | Physics engine with exponential cascading formulas |
| Autonomous Orchestrator | `autonomous_orchestrator.py` | 270 | SSH injection/recovery, GNN-LLM bridge, 3 fault scenarios |
| LLM Prompt Patcher | `llm_recovery_actor.py` | 70 | SFTP remote patching, regex prompt injection |
| Video App Deployer | `deploy_video_app.py` | 132 | Multi-container YAML, tunneled K8s deployment |
| Telemetry Scraper | `telemetry_scraper.py` | 41 | 6-probe diagnostic suite |
| **TOTAL** | | **~2,014** | **Full-stack autonomous AI SRE with mathematical governance** |
