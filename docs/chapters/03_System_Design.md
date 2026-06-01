# Chapter 4: SYSTEM DESIGN

## 4.1 Architecture Design Overview
The Autonomous AI SRE system is structured around a three-tier nested cloud topology, governed by an out-of-band management plane where the AI framework resides. This decouples the intelligence layer from the data plane, ensuring that catastrophic faults within the cloud do not blind the monitoring agent.

### 4.1.1 Nested Topology

1.  **Layer A (Bare Metal & Hardware):** A robust hypervisor environment (VMware) hosting the core Virtual Machines. It is bridged to a simulated physical network represented by the Juniper Mist AI ecosystem.
2.  **Layer B (OpenStack Cloud):** Deployed via Kolla-Ansible across three nodes (10.10.10.10 controller, 10.10.10.11/10.10.10.12 compute). This provides the Virtual Infrastructure Manager (VIM) abstractions (Nova, Neutron, Cinder).
3.  **Layer C (Kubernetes Edge):** Nestled entirely within OpenStack instances, communicating over virtual routers (qrouter), establishing the application hosting plane utilizing the Calico CNI.

### 4.1.2 Overall System Architecture Diagram

`mermaid
graph TD
    subgraph SRE_AI_Management_Plane["AI SRE Management Plane (Windows Host)"]
        AIAgent[FastAPI LangChain Agent]
        GNN[PyTorch ST-GNN Critic]
        Mist[Juniper Mist AI API Poller]
        LLM[Multi-Provider LLM Router]
        
        AIAgent <-->|Mathematical Governance| GNN
        AIAgent <-->|Query/Execute| LLM
        AIAgent <-->|REST Polling| Mist
    end

    subgraph OpenStack_Cloud["Layer B: OpenStack Kolla-Ansible"]
        Controller[OpenStack Controller]
        Compute1[Nova Compute 1]
        Compute2[Nova Compute 2]
        Neutron[Neutron qrouter NAT]
        
        Controller --- Compute1
        Controller --- Compute2
        Compute1 --- Neutron
    end

    subgraph Kubernetes_Edge["Layer C: Kubernetes Cluster"]
        K8sMaster[K8s Master Node]
        K8sWorker1[K8s Worker 1]
        K8sWorker2[K8s Worker 2]
        Prometheus[Prometheus / Alertmanager]
        
        K8sMaster --- K8sWorker1
        K8sMaster --- K8sWorker2
        K8sWorker1 --- Prometheus
    end

    %% Connections
    Prometheus -->|Webhook Alerts| AIAgent
    Controller -->|Aodh Alerts| AIAgent
    AIAgent -->|SSH Tunnel Tool Execution| K8sMaster
    AIAgent -->|OpenStack CLI Tool Execution| Controller
    Neutron <--> K8sMaster
`

## 4.2 Workflow of the Proposed System

The operational heart of the system is the closed-loop feedback cycle orchestrated by the LangChain ReAct (Reasoning + Acting) Agent. It relies on a multi-stage deterministic workflow.

### 4.2.1 The Agentic Flowchart
The following diagram illustrates the exact decision-making process the AI Agent undertakes when a fault is detected.

`mermaid
flowchart TD
    Start([Alert Received via Webhook/Poller]) --> Parse[Parse Alert Labels & Severity]
    Parse --> GNN_Eval[Pass 5-Tick Window to ST-GNN]
    GNN_Eval --> GNN_Result{GNN Output Probability > 90%?}
    
    GNN_Result -- Yes --> Assign_Context[Append Mathematical Context to Prompt]
    GNN_Result -- No --> Prompt_Gen[Generate Standard RCA Prompt]
    
    Assign_Context --> Prompt_Gen
    Prompt_Gen --> Smart_Router[Invoke Smart LLM Router]
    
    Smart_Router --> LLM_Inference{Provider Select}
    LLM_Inference -- Primary --> Cerebras[Cerebras: Llama 3.3 70B]
    LLM_Inference -- Escalation --> Gemini[Gemini 2.0 Flash]
    
    Cerebras --> Check_Confidence{Is LLM Confident?}
    Check_Confidence -- No (Uncertainty detected) --> Gemini
    Check_Confidence -- Yes --> Extract_Action[Extract Thought & Action]
    
    Gemini --> Extract_Action
    
    Extract_Action --> Run_Tool[Execute Infrastructure Tool via SSH/API]
    Run_Tool --> Observe[Capture Tool Output (Observation)]
    Observe --> Check_Done{Is Root Cause Found & Fixed?}
    
    Check_Done -- No (Loop < 15) --> Smart_Router
    Check_Done -- Yes --> Log[Write to incidents.jsonl]
    Log --> End([End Incident / Recovery Successful])
`

## 4.3 Detailed Subsystem Design

### 4.3.1 The 10-Tool Dynamic Execution Engine
A critical innovation of this design is that the LLM is not restricted to static playbooks. It is provided a dynamic toolbelt containing 10 strictly typed Python functions.
*   **Layer B Tools:** un_openstack_command, query_prometheus, un_shell_command.
*   **Layer C Tools:** un_kubectl_command (utilizes complex SSH tunneling through the OpenStack qrouter namespace to securely breach the virtualized perimeter).
*   **Physical Tools:** get_mist_alarms, estart_mist_device, ounce_mist_port.

### 4.3.2 The Multi-Provider Smart Router
To circumvent the inherent limitations of cloud-based APIs (rate limiting, latency spikes, and provider outages), the AI Agent implements a custom Smart Routing protocol. The router evaluates the required cognitive load of an incident. Standard metric queries are dispatched to ultra-fast inference engines (Cerebras), whereas cross-layer topology reasoning (e.g., relating a physical switch flap to a Kubernetes pod crash-loop) is escalated to high-capacity reasoning models (Gemini Flash). This guarantees high-throughput scalability during severe alert storms.
