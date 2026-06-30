<div align="center">
  
# 🌌 Autonomous AI SRE Framework
### *Zero-Touch Self-Healing for Deeply Nested Cloud Infrastructures*

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![OpenStack Kolla](https://img.shields.io/badge/OpenStack-Dalmatian-ed1944?style=for-the-badge&logo=openstack)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30%2B-326ce5?style=for-the-badge&logo=kubernetes)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c?style=for-the-badge&logo=pytorch)
![LangChain](https://img.shields.io/badge/LangChain-ReAct-121212?style=for-the-badge&logo=chainlink)

*An enterprise-grade, closed-loop AIOps architecture bridging the mathematical rigor of Spatio-Temporal Graph Neural Networks (ST-GNNs) with the dynamic execution of Large Language Models (LLMs).*

</div>

---

## 🚀 The Vision & Impact

Modern telecommunications and 5G infrastructures operate on deeply nested virtualized environments (e.g., Kubernetes running inside OpenStack VMs). When cascading failures occur across these abstraction layers, traditional threshold-based alerts and static playbooks catastrophically fail to identify the root cause, leading to extended downtime and revenue loss.

This project introduces a **"Dual-Brain" Autonomous Site Reliability Engineer (SRE)** capable of navigating, diagnosing, and repairing catastrophic infrastructure failures without human intervention. 

### How It Works: The Dual-Brain Architecture
1. **The Critic (ST-GNN):** Ingests massive streams of multi-dimensional telemetry data from both OpenStack hypervisors and Kubernetes nodes. Utilizing Graph Convolutional Networks (GCNs), it mathematically isolates the exact root cause of anomalies (e.g., distinguishing between a rogue CPU-hogging pod and underlying host hardware degradation).
2. **The Actor (LLM ReAct Agent):** Once the ST-GNN pinpoints the failure, the LangChain-powered LLM Agent takes over. Armed with context and a suite of infrastructure tools, it dynamically traverses network boundaries (navigating OpenStack `qrouter` namespaces to reach internal Kubernetes nodes) and executes bash commands, API calls, and Python scripts to permanently resolve the issue in under 5 seconds.

**Impact:** What historically took human SREs 45+ minutes to diagnose and resolve through complex namespace hopping is now solved completely autonomously.

---

## 🧬 Core Features

- **Nested Virtualization Testbed:** A robust Kolla-Ansible OpenStack deployment hosting a Calico-based Kubernetes cluster.
- **Spatio-Temporal Root Cause Analysis:** Pre-trained GNN models capable of predicting cascading failures before they bring down the control plane.
- **Dynamic Cross-Boundary Execution:** The AI Agent is not bound by a single environment. It seamlessly hops from the OpenStack controller to compute nodes, down into specific Kubernetes pods.
- **Chaos Engineering Suite:** Includes comprehensive fault injectors for CPU saturation, network bridge teardowns, and storage IO bottlenecks to validate the AI's resilience.

---

## 📁 Repository Structure

```text
├── src/                     # Core system architecture
│   ├── ai_agent/            # LangChain ReAct agent, prompts, and toolsets
│   ├── chaos_engineering/   # Advanced fault injectors and defense scenarios
│   ├── kubernetes_mgmt/     # K8s cluster lifecycle and monitoring scripts
│   └── utils/               # Telemetry scrapers and OpenStack networking bridges
├── data/                    # Datasets and AI Models
│   ├── datasets/            # Training data for anomalous and baseline states
│   └── models/              # Compiled PyTorch ST-GNN models
├── docs/                    # Deep dive documentation, mathematical models, and reports
├── deployment/              # Infrastructure-as-Code (OpenStack VMs)
└── scripts/                 # Standalone system entry points
```

---

## 🛠️ Kolla-Ansible OpenStack Deployment Guide

*The official OpenStack documentation is often insufficient for highly nested, multinode setups. Below is the definitive, battle-tested guide used to deploy this framework's infrastructure on Ubuntu 24.04 (OpenStack 2024.2 Dalmatian).*

### ⚡ 1-Click Infrastructure Setup (Recommended)
This repository includes Infrastructure-as-Code via **Vagrant**. Instead of manually creating VMs, you can instantly spin up the entire 3-node OpenStack cluster:
1. Install [Vagrant](https://developer.hashicorp.com/vagrant/downloads) and VirtualBox (or VMware).
2. Run the following command in the repository root:
   ```bash
   vagrant up
   ```
This will automatically download Ubuntu 24.04, create the 3 VMs (`controller`, `compute1`, `compute2`), allocate the required massive RAM/CPUs, configure the dual-network adapters, and set up passwordless SSH. 

---

### Architecture Specs
- **Controller Node** (`10.10.10.10`): 10GB RAM, 4 vCPUs
- **Compute1 Node** (`10.10.10.11`): 16GB RAM, 6 vCPUs
- **Compute2 Node** (`10.10.10.12`): 16GB RAM, 6 vCPUs
- *Ensure nested virtualization (Intel VT-x/AMD-V) is enabled on all VMs.*

### 1. Network Prep & Passwords
Ensure all nodes have a NAT interface (`ens33` for internet) and a Host-Only interface (`ens34` for management/tunneling).
Set unique hostnames (`openstack-controller`, etc.) and establish passwordless SSH from the controller to the compute nodes.

### 2. Install Kolla Dependencies (On Controller)
```bash
sudo apt update && sudo apt install -y git python3-venv
python3 -m venv ~/kolla-venv
source ~/kolla-venv/bin/activate
pip install -U pip 'ansible-core>=2.16,<2.17'
pip install git+https://opendev.org/openstack/kolla-ansible@stable/2024.2
kolla-ansible install-deps
```

### 3. Generate Configs & Fix bcrypt
Generate passwords in `/etc/kolla/passwords.yml` using `kolla-genpwd`. 
> ⚠️ **CRITICAL FIX**: bcrypt v5 strictly enforces a 72-byte password limit, breaking Prometheus deployments.
```bash
# Fix 1: Downgrade bcrypt
~/kolla-venv/bin/pip install 'bcrypt<5'

# Fix 2: Patch Prometheus template to truncate passwords
sed -i 's/user.password | password_hash/user.password[:72] | password_hash/' \
  ~/kolla-venv/share/kolla-ansible/ansible/roles/prometheus/templates/prometheus-web.yml.j2
```

### 4. Configure `globals.yml`
Add the following to `/etc/kolla/globals.yml`:
```yaml
kolla_base_distro: "ubuntu"
kolla_internal_vip_address: "10.10.10.200"
network_interface: "ens34"
neutron_external_interface: "ens33"
enable_haproxy: "yes"
enable_neutron_provider_networks: "yes"
enable_prometheus: "yes"
enable_grafana: "yes"
```

### 5. Deploy OpenStack!
Create your `~/multinode` inventory file mapping your IPs, then deploy:
```bash
source ~/kolla-venv/bin/activate
kolla-ansible bootstrap-servers -i ~/multinode -e ansible_become_password=<your-sudo-password>
kolla-ansible prechecks -i ~/multinode -e ansible_become_password=<your-sudo-password>
kolla-ansible deploy -i ~/multinode -e ansible_become_password=<your-sudo-password>
kolla-ansible post-deploy -i ~/multinode -e ansible_become_password=<your-sudo-password>
```

### 6. Verify Deployment
Retrieve your `admin` password from `/etc/kolla/passwords.yml` under `keystone_admin_password`.
Navigate to `http://10.10.10.200` to access the Horizon dashboard!

---

## 🔒 Security Disclaimer
This project simulates devastating infrastructure attacks (e.g., `chaos_engineering/`) designed to validate the AI's response. **Do not run the chaos injectors in a production environment.** All hardcoded API keys, passwords, and sensitive IPs have been scrubbed from this public repository.

## 📄 License
This project is licensed under the MIT License.
