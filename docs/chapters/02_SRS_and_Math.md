# Chapter 2: SOFTWARE REQUIREMENT SPECIFICATION

## 2.1 Overview of SRS
This Software Requirement Specification (SRS) details the operational bounds, functional capabilities, and performance constraints of the proposed Autonomous AI SRE System. The system is designed to operate seamlessly across three virtualization boundaries, continuously monitoring telemetry and executing deterministic anomaly resolution in real-time.

## 2.2 Requirement Specifications

### 2.2.1 Functional Requirements
*   **FR1 (Cross-Layer Telemetry Ingestion):** The system shall expose secure HTTP webhook endpoints to receive real-time alerting payloads from Prometheus Alertmanager (OpenStack metrics), Kubernetes Monitoring stacks, and actively poll the Juniper Mist AI Cloud via REST APIs.
*   **FR2 (Multi-Provider LLM Routing):** The AI Agent framework must implement a failover routing mechanism capable of escalating inference tasks dynamically. It must default to a high-speed inference engine (e.g., Llama 3.3 via Cerebras) and programmatically escalate to a deep-reasoning model (e.g., Gemini 2.0 Flash) if uncertainty is detected in the response.
*   **FR3 (Autonomous Tool Execution):** The system shall possess the capability to execute state-mutating commands via SSH tunnels. This includes standard Linux operations (pkill), OpenStack CLI administration, Kubernetes API manipulation (kubectl), and REST operations against physical network controllers.
*   **FR4 (Mathematical Governance):** The system must execute a PyTorch-based Spatio-Temporal Graph Neural Network (ST-GNN) inference upon receiving an alert, providing the LLM agent with a deterministic probability array of root causes to prevent LLM hallucination.
*   **FR5 (Incident Journaling):** All alerts, telemetry windows, LLM reasoning chains (Thoughts/Actions/Observations), and executed commands shall be logged to a persistent .jsonl audit trail to ensure system transparency and facilitate future model fine-tuning.

### 2.2.2 Non-Functional Requirements

**Performance Requirements:**
*   **NFR1 (GNN Inference Latency):** The PyTorch ST-GNN must complete its forward pass and calculate root cause probabilities across a 5-tick sliding window within **50 milliseconds** to satisfy near-real-time operational constraints.
*   **NFR2 (Agent Reasoning Latency):** The LangChain ReAct loop must utilize API providers capable of achieving high tokens-per-second (TPS) throughput, completing a full Thought-Action-Observation cycle within **3.0 seconds**.
*   **NFR3 (System-wide MTTR):** The total time from alert inception (T=0) to successful fault mitigation (Verification phase) must not exceed **15 seconds** for standard failure patterns (e.g., CPU exhaustion).

**Reliability and Availability:**
*   **NFR4 (Model Failover):** The agent must gracefully handle API rate limiting (HTTP 429) and provider outages by falling through its 4-tier model chain without halting the systemd daemon process.
*   **NFR5 (Concurrency):** The FastAPI webhook ingress must utilize uvicorn asynchronous workers to process up to 100 simultaneous alert storms without blocking the GNN inference thread.

---

# Chapter 3: MATHEMATICAL MODELING

## 3.1 Overview
The architectural complexity of nested virtualized networks prevents traditional linear correlation from accurately identifying root causes. An anomaly in physical hardware propagates temporally and spatially across software layers. Therefore, the system relies on a Spatio-Temporal Graph Neural Network (ST-GNN) combined with a customized mathematical representation of cascading physics.

## 3.2 Spatio-Temporal Graph Neural Network (ST-GNN) Model

### 3.2.1 Graph Construction and Adjacency
The infrastructure is modeled as a directed graph  = (V, E)$, where $ represents the set of nodes (e.g., Physical Switch, Hypervisor, OpenStack VM, K8s Pod) and $ represents the topological dependencies between them. 
The adjacency matrix $ is defined such that {i,j} = 1$ if node $ physically or virtually depends on node $ (e.g., Pod depends on VM).

### 3.2.2 Spatial Extraction (GCNConv)
To capture spatial dependencies at time $, the system employs two layers of Graph Convolutional Networks (GCN). The hidden state representation ^{(l+1)}$ at layer +1$ is calculated as:

 H^{(l+1)} = \sigma\left(\tilde{D}^{-\frac{1}{2}}\tilde{A}\tilde{D}^{-\frac{1}{2}}H^{(l)}W^{(l)}\right) 

Where:
*   $\tilde{A} = A + I_N$ is the adjacency matrix with added self-connections.
*   $\tilde{D}$ is the diagonal degree matrix of $\tilde{A}$.
*   ^{(l)}$ is the learnable weight matrix for layer $.
*   $\sigma$ is the ReLU activation function.

This allows the model to propagate "distress" signals mathematically across the topology; if a hypervisor is failing, the convolution mathematically alerts the connected Kubernetes pods within the graph.

### 3.2.3 Temporal Extraction (LSTM)
Because network faults evolve over time (e.g., a memory leak gradually consumes resources before causing a crash), the spatial embeddings $ generated by the GCN are fed into a Long Short-Term Memory (LSTM) network across a sliding window of size =5$. The temporal hidden state $ is updated as:

 f_t = \sigma(W_f \cdot [h_{t-1}, Z_t] + b_f) 
 i_t = \sigma(W_i \cdot [h_{t-1}, Z_t] + b_i) 
 C_t = f_t * C_{t-1} + i_t * \tanh(W_C \cdot [h_{t-1}, Z_t] + b_C) 
 h_t = \sigma(W_o \cdot [h_{t-1}, Z_t] + b_o) * \tanh(C_t) 

The final hidden state $ encodes the complete spatio-temporal evolution of the fault, which is passed to a fully connected layer with a log_softmax activation to output a deterministic probability array spanning the 13 defined fault classes.

## 3.3 Mathematical Modeling of Cascading Faults

To robustly train the GNN, the system utilizes a cascading fault physics engine (cascading_fault_synthesizer.py) that models the mathematical deterioration of related nodes. The degradation of Application Latency ({app}$) is modeled as a non-linear combination of underlying infrastructure stress:

 L_{app} = L_{base} + e^{\left(\frac{CPU_{os}}{18}\right)} + \frac{IO_{disk}}{10} + \omega_{k8s} 

Where:
*   {os}$ is the percentage utilization of the underlying OpenStack compute node.
*   {disk}$ is the block storage latency.
*   $\omega_{k8s}$ is a heavy penalty added if the Kubernetes scheduler reports a state of starvation.

This exponential smoothing relationship proves that physical resource exhaustion leads to catastrophic, non-linear application-level failures, validating the absolute necessity of the cross-layer AI intervention described in the following chapters.
