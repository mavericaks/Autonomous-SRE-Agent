# Autonomous AI SRE Framework

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![OpenStack Kolla](https://img.shields.io/badge/OpenStack-Kolla--Ansible-red.svg)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-blue.svg)

> **Disclaimer**: This repository contains a complex testbed for an experimental **Autonomous AI Site Reliability Engineer (SRE)** framework. It includes nested virtualization (OpenStack running Kubernetes) and utilizes a combination of LLM Agents and Spatio-Temporal Graph Neural Networks (ST-GNNs).

## Overview

Modern cloud and telecommunications infrastructures are highly dynamic, deeply nested, and incredibly complex. This project introduces an **Autonomous AI SRE Framework**, a closed-loop AIOps architecture designed to operate within an OpenStack (via Kolla-Ansible) and Kubernetes environment.

By integrating the deterministic mathematical rigor of a Spatio-Temporal Graph Neural Network (ST-GNN) with the dynamic reasoning and execution capabilities of a Large Language Model (LLM) instantiated as a LangChain ReAct agent, this system aims to fully automate root cause analysis and infrastructure self-healing.

## Key Features

- **Nested Infrastructure Testbed**: Full Kolla-Ansible OpenStack deployment nesting a Calico-based Kubernetes cluster.
- **LLM Reasoning Agent**: A LangChain ReAct loop that traverses OpenStack networking namespaces and executes bash/python commands across virtualization boundaries.
- **GNN Root Cause Analysis**: Spatio-temporal anomaly detection for metrics across nodes, pods, and VMs.
- **Chaos Engineering Suite**: Automated fault injectors for CPU saturation, disk IO bottlenecks, and network bridge failures.

## Directory Structure

```text
├── src/                     # Core source code
│   ├── ai_agent/            # LLM ReAct agent, prompts, and tool definitions
│   ├── chaos_engineering/   # Fault injectors and test scenarios
│   ├── kubernetes_mgmt/     # Scripts for k8s cluster lifecycle and monitoring
│   └── utils/               # Helper scripts for networking and OpenStack bridging
├── data/                    # Datasets and model checkpoints
│   ├── datasets/            # Telemetry datasets for GNN training
│   └── models/              # Pre-trained ST-GNN models
├── docs/                    # Documentation and Final Reports
│   ├── reports/             # Comprehensive evaluation reports and PDFs
│   └── chapters/            # Project report chapters
├── deployment/              # Infrastructure-as-Code & configurations
│   ├── openstack_setup/     # Kolla-Ansible globals and multinode configs
│   └── openstack-*/         # VM Definitions (Compute, Controller)
└── scripts/                 # Standalone entry point scripts
```

## Setup & Installation

### 1. Prerequisites
- A powerful bare-metal server (minimum 64GB RAM, 16+ Cores) for nested virtualization.
- Ubuntu 22.04 LTS recommended.
- Python 3.10+
- Docker & Kolla-Ansible dependencies.

### 2. Configure Environment
Set up your `.env` file inside `src/ai_agent/` based on the `.env.example` template:
```bash
cp src/ai_agent/.env.example src/ai_agent/.env
# Edit .env with your credentials and keys
```
*(Note: Do not commit your `.env` or SSH keys to version control. They are ignored in `.gitignore`)*

### 3. Deploy OpenStack Testbed
Navigate to `deployment/openstack_setup` to access the globals and multinode configuration used by Kolla-Ansible.
Refer to the official [Kolla-Ansible Documentation](https://docs.openstack.org/kolla-ansible/latest/) for bootstrap and deploy commands.

### 4. Run the AI Agent
```bash
python src/ai_agent/main.py
```

## Security & Usage Notice
- **Hardcoded Paths**: Some scripts might still expect the original monolithic `H:\Kolla-Ansible` structure. If you encounter missing module errors, run the scripts from the root directory or update Python's `sys.path`.
- **Sensitive Data**: We have scrubbed the repository of real credentials and passwords, replacing them with `<REDACTED>`. Please ensure you supply valid test credentials in your private environment.

## License
MIT License. See `LICENSE` for details.
