# Chapter 5: IMPLEMENTATION

## 5.1 Overview
This chapter details the codebase implementation of the Autonomous AI SRE system. Unlike traditional AIOps platforms that rely entirely on supervised thresholds, this project synthesizes a Mathematical Graph Neural Network with a LangChain Agentic loop. The implementation comprises over 2,000 lines of highly optimized Python code distributed across inference engines, chaos orchestrators, and system daemons.

## 5.2 Baseline Conventional Handling vs Proposed System
In a standard OpenStack/K8s deployment, telemetry alerts are forwarded to a Slack channel or PagerDuty. A human operator logs in, runs kubectl get pods, checks Nova compute states, and manually intervenes.
The proposed implementation entirely replaces this human-in-the-middle loop.

## 5.3 Core AI Scheduler Implementation

### 5.3.1 Snippet 1: The Multi-Provider Smart LLM Router
The agent's reliability depends on its ability to handle API rate limiting and complex cognitive tasks. The following simplified Python snippet from i-agent/main.py demonstrates the smart escalation protocol.

`python
# Algorithm 1: LLM Smart Escalation Router (Python)
def smart_invoke(self, prompt: str, requires_deep_reasoning: bool = False):
    """Routes requests to the optimal LLM based on task complexity."""
    
    # Check for uncertainty flags in previous observations
    if any(keyword in prompt for keyword in ["unclear", "cascading", "unable to determine"]):
        requires_deep_reasoning = True
        
    if requires_deep_reasoning:
        try:
            return self.gemini_flash.invoke(prompt)  # Deep reasoning escalation
        except RateLimitError:
            pass # Fall through to baseline
            
    # Default fast-path execution
    try:
        return self.cerebras_llama.invoke(prompt) # High TPS inference
    except Exception as e:
        self.log_error(f"Primary provider failed: {e}")
        return self.openrouter_fallback.invoke(prompt)
`
**Innovation:** By parsing the semantic context of the incident in real-time, the router dynamically allocates expensive computational resources (Deep Reasoning models) only to complex, multi-layer topology faults, while routing simple kubectl log parsing to ultra-fast, lightweight models.

### 5.3.2 Snippet 2: The Spatio-Temporal GNN Critic
To provide deterministic guardrails against LLM hallucinations, the system runs a PyTorch ST-GNN inference locally. The model maintains a sliding window of historical telemetry states.

`python
# Algorithm 2: Live ST-GNN Inference Engine (PyTorch)
class STGNNCritic:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.temporal_buffer = deque(maxlen=5) # 5-tick sliding window
        
    def ingest_telemetry(self, raw_metrics: dict):
        # 1. Scale metrics via StandardScaler
        scaled_features = self.scaler.transform(raw_metrics)
        # 2. Extract into 4 cross-layer spatial node groups
        padded_tensor = self.pad_features(scaled_features)
        self.temporal_buffer.append(padded_tensor)
        
    def evaluate(self):
        if len(self.temporal_buffer) < 5:
            return "NO_ANOMALY"
            
        # Construct [Batch, Time, Nodes, Features] tensor
        x = torch.stack(list(self.temporal_buffer)).unsqueeze(0)
        
        with torch.no_grad():
            output_log_probs = self.model(x)
            probabilities = torch.exp(output_log_probs)
            
        predicted_class = torch.argmax(probabilities)
        return self.label_encoder.inverse_transform(predicted_class)
`
**Innovation:** The deque buffer acts as a temporal memory bank, enabling the LSTM layer inside the ST-GNN to distinguish between momentary metric jitter (noise) and genuine exponential degradation (a cascading fault).

### 5.3.3 Snippet 3: The Cross-Layer Tool Execution Framework
When the LLM formulates a recovery action, it must securely traverse virtualization boundaries to execute commands.

`python
# Algorithm 3: Cross-Boundary Execution Tool (Python)
@tool
def run_kubectl_command(command: str) -> str:
    """Executes a kubectl command securely inside the nested K8s cluster."""
    # The K8s master is unreachable directly from the host.
    # We must tunnel through the OpenStack Neutron qrouter namespace.
    
    qrouter_id = "qrouter-a1b2c3d4-..."
    k8s_master_ip = "172.16.0.74"
    
    # Construct the SSH tunnel payload
    tunnel_cmd = (
        f"sudo ip netns exec {qrouter_id} "
        f"ssh -o StrictHostKeyChecking=no ubuntu@{k8s_master_ip} '{command}'"
    )
    
    result = subprocess.run(tunnel_cmd, shell=True, capture_output=True)
    return result.stdout[:3000] # Cap output to prevent LLM context overflow
`

## 5.4 Summary
The implementation successfully bridges the theoretical domain of Graph Neural Networks with the practical domain of Autonomous LLM Agents. By explicitly defining tools that handle SSH tunnels and network namespace routing, the agent can physically mutate the state of the cloud infrastructure, moving SRE from "passive alerting" to "active healing."
