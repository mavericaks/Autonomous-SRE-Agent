# Autonomous AI SRE: Cross-Layer Diagnostics via Graph Neural Networks and Large Language Models

## A Comprehensive Project Report
**Date:** May 2026

**Submitted in partial fulfillment of the requirements for the Integrated Project**

---

## ABSTRACT

Modern cloud-native infrastructures are characterized by immense complexity, spanning physical networking hardware, bare-metal hypervisors, virtualization layers, and edge orchestration frameworks like Kubernetes. When a fault occurs—such as a physical switch port dropping or a hypervisor CPU saturating—the resulting failure cascades upward through the abstraction layers, ultimately manifesting as application-level degradation. Traditional Site Reliability Engineering (SRE) relies on human operators to manually correlate discrete alarms across isolated dashboards, a process that is highly susceptible to the "alert storm" phenomenon and introduces unacceptable Mean Time To Resolution (MTTR). 

To address this critical bottleneck, this project introduces the **Autonomous AI SRE Framework**, a novel, closed-loop AIOps architecture deployed within an OpenStack (Kolla-Ansible) and Kubernetes nested environment. The framework integrates the deterministic, mathematical rigor of a Spatio-Temporal Graph Neural Network (ST-GNN) with the dynamic reasoning and execution capabilities of a Large Language Model (LLM) instantiated as a LangChain ReAct (Reasoning + Acting) agent. 

The system continuously ingests telemetry from the hardware/network tier (Juniper Mist AI), the virtualization tier (OpenStack Ceilometer/Aodh), and the application tier (Kubernetes Prometheus). Upon detecting anomalous behavior, the ST-GNN performs sub-50ms causal inference to mathematically isolate the root cause within the topological graph. Simultaneously, the LLM agent formulates a remediation strategy, utilizing a suite of 10 custom infrastructure tools to autonomously SSH into compute nodes, query APIs, and execute recovery commands (e.g., live-migrating pods, restarting physical APs, or throttling noisy neighbors). 

Experimental validation within a chaos-engineered Colosseum testbed demonstrates that the proposed dual-critic system achieves a 99.2% root cause identification accuracy and consistently executes cross-layer remediation within 15 seconds, significantly outperforming context-naive automated drift handling baselines. This work establishes a viable pathway toward fully autonomous, self-healing, zero-touch telecommunication and cloud networks.

---

## TABLE OF CONTENTS
1. [Chapter 1: Introduction](#chapter-1-introduction)
2. [Chapter 2: Software Requirement Specification](#chapter-2-software-requirement-specification)
3. [Chapter 3: Mathematical Modeling](#chapter-3-mathematical-modeling)
4. [Chapter 4: System Design](#chapter-4-system-design)
5. [Chapter 5: Implementation](#chapter-5-implementation)
6. [Chapter 6: Results and Discussion](#chapter-6-results-and-discussion)
7. [Chapter 7: Conclusion and Future Scope](#chapter-7-conclusion-and-future-scope)

---

# Chapter 1: INTRODUCTION

## 1.1 Motivation
The primary motivating factor for this project is the growing disconnect between the operational complexity of modern 5G/Cloud infrastructure and the human capacity to manage it. In a standard enterprise environment today, an application running in a Docker container is orchestrated by Kubernetes, which runs on a Virtual Machine, which is provisioned by OpenStack (Nova), which resides on a bare-metal hypervisor, which connects to a physical switch, which connects to a core router. 

When a physical switch drops packets due to a malfunctioning transceiver, the downstream effect is catastrophic: OpenStack Neutron virtual routers experience latency, Kubernetes nodes begin reporting NotReady statuses, and containerized applications crash. Traditional monitoring tools alert on *all* of these symptoms simultaneously. An SRE is suddenly faced with hundreds of critical alerts across Prometheus, Grafana, and physical network dashboards. The manual correlation of these events is slow and error-prone, directly impacting Service Level Agreements (SLAs).

While Machine Learning (ML) approaches have been introduced for anomaly detection, they predominantly suffer from *concept drift* and lack the ability to actively *remediate* the fault. There is an urgent need for an autonomous system that can not only detect faults across physical, virtual, and application layers but also reason about their causal relationships and take immediate, programmatic action to resolve them without human intervention.

## 1.2 Literature Review
The integration of Artificial Intelligence into IT Operations (AIOps) has seen significant academic and industrial focus over the last five years. 

**LLMs in Operations:** Recent works have explored the use of Large Language Models (LLMs) for interpreting system logs. Jin et al. (2024) demonstrated the utility of retrieval-augmented generation (RAG) in providing context-aware bash commands for system administrators. However, their approach remained an "advisor" loop, requiring a human-in-the-middle to execute the commands, limiting its utility in real-time outage mitigation.

**Graph Neural Networks (GNNs) for Root Cause Analysis:** Wang et al. (2023) proposed a Spatial-Temporal GNN for microservice fault localization. By modeling microservices as nodes and API calls as edges, their model successfully identified the origin of high-latency events. Despite its high accuracy, the model was restricted purely to the application layer (Layer 7) and failed to account for underlying infrastructure faults, such as hypervisor CPU exhaustion or physical network topology changes.

**Closed-Loop Autonomous SRE:** The concept of fully autonomous SRE is still in its infancy. Frameworks like "AutoRemediate" rely heavily on static, pre-defined Ansible playbooks triggered by simple threshold alerts. These rule-based systems are fragile and cannot adapt to novel, unseen failure modes—a phenomenon known as the "rule explosion" problem in complex systems.

## 1.3 Research Gaps
Despite the advancements in AIOps, several critical gaps remain:
*   **The Single-Layer Blind Spot:** Existing anomaly detection models are heavily siloed. A Kubernetes monitoring tool has no visibility into the Juniper Mist physical network controller, making cross-layer causal inference impossible.
*   **The LLM Hallucination Risk:** While LLMs excel at reasoning, they lack deterministic mathematical guarantees and are prone to hallucinations, making them dangerous for autonomous execution in production environments without strict governance.
*   **The Actionability Gap:** Most ML models stop at "prediction" or "classification." There is a distinct lack of frameworks that seamlessly bridge mathematically rigorous anomaly detection with dynamic, LLM-driven execution via SSH and API interfaces.

## 1.4 Problem Definition
To design, develop, and deploy a full-stack, closed-loop Autonomous AI SRE system capable of managing a complex, nested infrastructure (Physical Network -> OpenStack -> Kubernetes). The system must utilize mathematically deterministic Graph Neural Networks for root cause analysis and a multi-provider LangChain ReAct agent for autonomous execution, thereby eliminating the need for manual alert correlation and significantly reducing Mean Time To Resolution (MTTR).

## 1.5 Objectives of the Project
The core objectives of this undertaking are:
1.  **Infrastructure Orchestration:** To successfully deploy a highly available OpenStack cloud (via Kolla-Ansible) nested with a Kubernetes cluster, functioning over a simulated enterprise network (Juniper Mist AI integration).
2.  **Spatio-Temporal Modeling:** To engineer a PyTorch-based GNN capable of analyzing real-time sliding windows of telemetry data across all infrastructure layers to identify the mathematical origin of cascading failures.
3.  **Agentic AI Development:** To develop a LangChain ReAct agent equipped with custom infrastructure tools (e.g., SSH execution, Kubernetes API interaction) capable of reasoning over GNN outputs and executing complex recovery workflows.
4.  **Chaos Engineering & Validation:** To rigorously validate the system's accuracy and responsiveness by systematically injecting faults (CPU starvation, network flooding, pod crashes) and measuring the autonomous recovery performance against traditional baseline handlers.
