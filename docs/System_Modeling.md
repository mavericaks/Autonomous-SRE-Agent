# Autonomous AI SRE System: Formal System Modeling

This document presents the formal system models for the **real-time operational system only**. All offline/one-time components (dataset generation, model training) are excluded — they are prerequisites, not part of the running system.

---

## 1. Component Diagram — What Exists at Runtime

```plantuml
@startuml
skinparam componentStyle uml2

package "OpenStack Controller (10.10.10.10)" {
  [AI SRE Agent\n(main.py)\nFastAPI + LangChain ReAct] as Agent
  [Prometheus\nAlertmanager] as AlertMgr
  [OpenStack CLI\n(Nova, Neutron, Cinder)] as OSCLI
}

package "OpenStack Compute1 (10.10.10.11)" {
  [Hypervisor\n(KVM / libvirt)] as Hypervisor
  [Node Exporter\n(Prometheus Metrics)] as NodeExp
}

package "Kubernetes Cluster (VMs inside OpenStack)" {
  [Video Streaming App\n(NGINX-RTMP + Encoder)] as VideoApp
  [K8s API Server] as K8sAPI
  [Prometheus\n(kube-prometheus-stack)] as K8sProm
}

package "Juniper Mist Cloud (api.gc4.mist.com)" {
  [Mist REST API\n(Alarms, SLE, Marvis)] as MistAPI
}

package "Local Workstation" {
  [autonomous_orchestrator.py\n(Chaos Injection + GNN Bridge)] as Orchestrator
  [stgnn_mathematical_critic.py\n(PyTorch LSTM Inference)] as GNNCritic
}

AlertMgr --> Agent : Webhook POST /alert
Agent --> OSCLI : run_openstack_command()
Agent --> K8sAPI : run_kubectl_command()\n(via qrouter SSH tunnel)
Agent --> K8sProm : query_prometheus("k8s|...")
Agent --> NodeExp : query_prometheus("openstack|...")
Agent --> MistAPI : get_mist_alarms()\nget_mist_sle_metrics()\nrestart_mist_device()

Orchestrator --> VideoApp : check_app_health()\nHTTP GET :30080
Orchestrator --> Hypervisor : fire() / run()\nSSH fault injection
Orchestrator --> GNNCritic : invoke_gnn_critic()\n5-tick telemetry sequence
Orchestrator --> Agent : Triggers RCA via fault scenarios

GNNCritic --> Orchestrator : Mathematical probability\n(e.g., 99.2% OS_CPU_Exhaustion)
@enduml
```

---

## 2. Deployment Diagram — Where Each Module Runs

```plantuml
@startuml
node "Local Workstation (Windows)" {
  artifact "autonomous_orchestrator.py" as AO
  artifact "stgnn_mathematical_critic.py" as GNN
  artifact "stgnn_rca_model.pt\n(Trained Weights)" as Weights
  artifact "scaler.pkl + label_encoder.pkl" as Scalers
  GNN ..> Weights : loads
  GNN ..> Scalers : loads
  AO --> GNN : imports STGNNCritic
}

node "OpenStack Controller\n10.10.10.10" {
  artifact "main.py (AI SRE Agent)" as MainPy
  artifact "ai-sre-agent.service\n(systemd daemon)" as Systemd
  artifact "incidents.jsonl\n(Audit Log)" as Journal
  Systemd --> MainPy : ExecStart
  MainPy --> Journal : log_incident()
}

node "OpenStack Compute1\n10.10.10.11" {
  artifact "Hypervisor (KVM)" as KVM
}

cloud "Kubernetes VMs" {
  artifact "video-streaming-server\n(2 replicas, NGINX-RTMP)" as VS
  artifact "video-encoder-worker\n(2 replicas, CPU stress)" as VE
  artifact "video-streaming-svc\n(NodePort 30080)" as Svc
}

cloud "Juniper Mist Cloud" {
  artifact "Mist REST API" as Mist
}

AO --> KVM : SSH (paramiko)\nFault injection + recovery
AO --> Svc : HTTP GET\nHealth monitoring
MainPy --> Mist : HTTPS\nAlarm polling + device restart
MainPy --> KVM : SSH tunnel\nkubectl commands
@enduml
```

---

## 3. Class Diagram — Runtime Object Structure

```plantuml
@startuml
class AutonomousOrchestrator {
  - CONTROLLER: str = "10.10.10.10"
  - COMPUTE1: str = "10.10.10.11"
  - APP_URL: str = "http://10.10.10.10:30080"
  - gnn_critic: STGNNCritic
  + run(ip, cmd): str
  + fire(ip, cmd): void
  + check_app_health(): (int, float)
  + invoke_gnn_critic(telemetry_stream): str
  + rca(message): void
}

class STGNNCritic {
  - model: RCA_STGNN
  - scaler: StandardScaler
  - label_encoder: LabelEncoder
  - telemetry_buffer: Deque[maxlen=5]
  - batch_edges: Tensor
  - max_features: int = 23
  + ingest_telemetry(telemetry_dict): void
  + evaluate(): List[Dict]
  + pad_features(array): ndarray
}

class RCA_STGNN {
  - conv1: GCNConv(23, 64)
  - conv2: GCNConv(64, 64)
  - lstm: LSTM(64, 64)
  - fc: Linear(64, 13)
  + forward(x_batch, batch_edges): Tensor
}

class AISREAgent {
  - PROVIDER_CHAIN: List = [cerebras, openrouter, groq]
  - REASONING_PROVIDER: str = "gemini"
  - incident_journal: List[Dict]
  + smart_invoke(prompt): Dict
  + needs_reasoning_escalation(output): bool
  + create_agent_for_provider(provider): AgentExecutor
  + log_incident(alert, analysis, actions): void
  + k8s_alert_poller(): void  <<background thread>>
  + mist_alarm_poller(): void  <<background thread>>
}

class FastAPIEndpoints {
  + POST /alert : receive_alert(webhook)
  + POST /test : test_alert(request)
  + GET /health : health()
  + GET /incidents : list_incidents()
}

class InfrastructureTools {
  + run_openstack_command(cmd): str
  + run_kubectl_command(cmd): str
  + run_shell_command(cmd): str
  + query_prometheus(input_str): str
  + get_mist_device_inventory(filter): str
  + get_mist_alarms(count): str
  + get_mist_sle_metrics(scope, metric): str
  + restart_mist_device(device_id): str
  + bounce_mist_port(device_id, port): str
  + get_mist_marvis_actions(limit): str
}

AutonomousOrchestrator *-- STGNNCritic : uses
STGNNCritic *-- RCA_STGNN : loads trained model
AISREAgent *-- InfrastructureTools : invokes via ReAct loop
AISREAgent *-- FastAPIEndpoints : serves
AutonomousOrchestrator ..> AISREAgent : triggers indirectly\n(via fault injection)
@enduml
```

---

## 4. Sequence Diagram — Full Fault Lifecycle

```plantuml
@startuml
actor Engineer
participant "autonomous_\norchestrator.py" as Orch
participant "Video App\n(K8s)" as App
participant "OpenStack\nCompute1" as OS
participant "stgnn_mathematical\n_critic.py" as GNN
participant "AI SRE Agent\n(main.py)" as Agent
participant "LLM Provider\n(Cerebras/Gemini)" as LLM
participant "Infrastructure\nTools" as Tools

== Fault Injection ==
Engineer -> Orch : python autonomous_orchestrator.py app_cpu_cascade
Orch -> App : check_app_health() -> HTTP 200, 150ms
Orch -> OS : fire("nohup bash /tmp/hog.sh &")
note right of OS : 4 infinite CPU loops\nstarted in background

== Impact Propagation ==
loop Every 4 seconds
  Orch -> App : check_app_health()
  App --> Orch : HTTP 200, latency increasing...
end
App --> Orch : HTTP 503, 5000ms (TIMEOUT)

== Mathematical Root Cause Analysis ==
Orch -> GNN : invoke_gnn_critic([5 telemetry ticks])
GNN -> GNN : Clear LSTM buffer
GNN -> GNN : ingest_telemetry() x5\n(scale, split, pad, append)
GNN -> GNN : evaluate()\nTensor [1,5,4,23] -> forward()
GNN --> Orch : [99.2%] OS_CPU_Exhaustion

== AI Agent Response (Parallel Path) ==
note over Agent : Meanwhile, Prometheus detects\nCPU > 90% and fires alert
Agent <- Agent : k8s_alert_poller() detects firing alert
Agent -> Agent : smart_invoke(prompt)
Agent -> LLM : Send ReAct prompt + tool descriptions
loop ReAct Iterations (max 15)
  LLM --> Agent : Thought + Action + Action Input
  Agent -> Tools : Execute requested tool
  Tools --> Agent : Observation (tool output)
  Agent -> LLM : Feed observation back
end
LLM --> Agent : Final Answer with RCA

== Governance Validation ==
Orch -> Orch : Does LLM root cause\nmatch GNN prediction?
note right of Orch : GNN says: OS_CPU_Exhaustion\nLLM says: OS_CPU_Exhaustion\nResult: MATCH -> Approved

== Recovery Execution ==
Orch -> OS : fire("pkill -9 -f hog.sh")
Orch -> App : check_app_health()
App --> Orch : HTTP 200, 150ms
Orch --> Engineer : [RESOLVED] Health Restored

== Audit ==
Agent -> Agent : log_incident(alert, analysis, tool_calls)
note right of Agent : Persisted to incidents.jsonl
@enduml
```

---

## 5. State Diagram — System Lifecycle States

```plantuml
@startuml
[*] --> Healthy

state Healthy {
  Healthy : All pods Running
  Healthy : App latency < 500ms
  Healthy : Agent polling every 60s
  Healthy : GNN buffer accepting ticks
}

Healthy --> FaultActive : Fault injected\n(CPU/Memory/Network/Pod crash)

state FaultActive {
  FaultActive : Hypervisor/Pod degraded
  FaultActive : App latency rising
}

FaultActive --> SymptomDetected : App latency > 2000ms\nOR HTTP 503 returned

state SymptomDetected {
  SymptomDetected : Orchestrator triggers RCA
  SymptomDetected : Prometheus alert fires
}

SymptomDetected --> MathematicalEvaluation : 5-tick buffer\nfed to PyTorch

state MathematicalEvaluation {
  MathematicalEvaluation : GCNConv extracts spatial dependencies
  MathematicalEvaluation : LSTM extracts temporal trend
  MathematicalEvaluation : Softmax outputs probability distribution
}

MathematicalEvaluation --> GovernanceCheck : GNN returns\ntop prediction

state GovernanceCheck {
  GovernanceCheck : Compare GNN prediction vs LLM diagnosis
}

GovernanceCheck --> StrategyApproved : Predictions MATCH
GovernanceCheck --> StrategyRejected : Predictions CONFLICT

StrategyRejected --> MathematicalEvaluation : Force LLM\nto re-evaluate

state StrategyApproved {
  StrategyApproved : Recovery commands identified
}

StrategyApproved --> Recovering : Execute SSH/API\nmitigation commands

state Recovering {
  Recovering : pkill anomalous processes
  Recovering : kubectl scale/restart pods
  Recovering : restart_mist_device if needed
}

Recovering --> Healthy : App latency < 500ms\nAll pods Running
Recovering --> FaultActive : Mitigation failed\nLatency still high
@enduml
```

---

## 6. Activity Diagram — Decision Logic Flow

```plantuml
@startuml
start

partition "Detection" {
  :Continuously monitor App HTTP endpoint;
  if (Latency > 2000ms OR HTTP 503?) then (Yes)
    :Trigger RCA Phase;
  else (No)
    :Continue monitoring;
    stop
  endif
}

partition "Mathematical Analysis" {
  :Collect 5 consecutive telemetry snapshots;
  :Scale each snapshot using saved StandardScaler;
  :Split into 4 node groups (App, K8s, OS, Mist);
  :Pad to uniform dimension [4 x 23];
  :Push into LSTM Deque Buffer;
  :Run PyTorch forward pass;
  :Extract softmax probability vector (13 classes);
  :Rank predictions by confidence;
}

partition "LLM Reasoning" {
  :Agent receives alert via webhook/poller;
  :Smart Router selects LLM provider;
  if (Primary provider available?) then (Yes)
    :Use Cerebras (Llama 3.3 70B);
  else (No)
    :Fallback to OpenRouter or Groq;
  endif
  :ReAct Loop: Thought -> Tool Call -> Observation;
  :LLM produces root cause diagnosis;
  if (Output contains uncertainty keywords?) then (Yes)
    :Escalate to Gemini for deep reasoning;
  else (No)
    :Accept primary analysis;
  endif
}

partition "Governance" {
  if (GNN prediction matches LLM diagnosis?) then (Yes)
    :Approve recovery strategy;
  else (No)
    :Reject LLM output;
    :Re-prompt with GNN mathematical proof;
  endif
}

partition "Recovery" {
  :Execute mitigation via SSH/API;
  :Re-check application health;
  if (Latency < 500ms?) then (Yes)
    :Mark incident RESOLVED;
    :Log to incidents.jsonl;
  else (No)
    :Escalate to human operator;
  endif
}

stop
@enduml
```
