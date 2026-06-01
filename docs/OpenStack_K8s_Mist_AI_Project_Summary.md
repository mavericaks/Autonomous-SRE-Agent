# Full Stack OpenStack SRE & AI Integration Project Summary
**Date:** April 2026
**Environment:** Windows Host -> VMware Workstation Pro -> Ubuntu 24.04 Virtualization -> Kolla-Ansible OpenStack -> Nova Instances -> Kubernetes

This document serves as the comprehensive "Master Runbook" and context summary for the entire project. It documents the architecture, the journey of how it was built, the challenges overcome, and the final state of the integrated system.

---

## 1. System Architecture & Topology

The system is a 3-layer nested cloud architecture designed for Site Reliability Engineering (SRE) and AI-driven observability.

### Layer A: The Bare Metal & Hypervisor
*   **Host:** Windows Workstation with 64GB RAM allocated.
*   **Hypervisor:** VMware Workstation Pro.
*   **Network:** `VMnet2` (Host-Only `10.10.10.0/24`) and `VMnet8` (NAT `192.168.137.0/24` for internet access).
*   **VMs:**
    1.  `openstack-controller` (`10.10.10.10`): Management plane, 10GB RAM, 4 vCPU.
    2.  `openstack-compute1` (`10.10.10.11`): Nova workload hypervisor, 16GB RAM, 6 vCPU.
    3.  `openstack-compute2` (`10.10.10.12`): Nova workload hypervisor, 16GB RAM, 6 vCPU.
*   *Feature Enablement:* VT-x / EPT nested virtualization is enabled physically on all three VMs to allow KVM to function inside them.

### Layer B: The OpenStack Cloud (Kolla-Ansible)
*   **Deployment Method:** Containerized OpenStack via Kolla-Ansible.
*   **Core Services:** Nova (Compute), Neutron (OpenvSwitch + DVR), Keystone (Identity), Horizon (Dashboard), Cinder (Block Storage via LVM backing), Ceilometer/Aodh (Telemetry).
*   **Networking:** The `br-ex` interface bridges to the `VMnet8` NAT, allowing floating IPs and outbound internet access, while management traffic rides smoothly over `VMnet2` (`10.10.10.x`).

### Layer C: The Kubernetes Edge Cluster
*   **Host Environment:** 3 virtual machines initialized *inside* the OpenStack Nova engine.
*   **Nodes:** 
    1. `k8s-master` (`172.16.0.74`)
    2. `k8s-worker-1` (`172.16.0.146`)
    3. `k8s-worker-2` (`172.16.0.130`)
*   **Network Infrastructure:** Runs behind an OpenStack virtual router (`qrouter-[ID]`) handling NAT. Internal cluster connectivity is managed by the **Calico CNI** plugin.
*   **Observability:** The full `kube-prometheus-stack` (Prometheus, Grafana, Alertmanager) deployed via Helm into the `monitoring` namespace, mapped via NodePorts (`30090`, `30080`).

### Layer D: The SRE AI "Brain" (Juniper Mist Integration)
*   **Agent Core:** A custom FastAPI + LangChain Python application running natively on the Windows host (`port 8000`).
*   **Functionality:** Receives active webhooks from K8s Alertmanager and OpenStack Aodh. 
*   **Edge Polling:** A background thread periodically pings the **Juniper Mist AI API** (`api.gc4.mist.com`) to cross-reference physical network alarms (AP drops, Switch port failures) alongside cloud metrics.
*   **LLM Decisioning:** LLM models automatically analyze faults across Cloud (OpenStack), Compute (K8s), and Edge Network (Mist) to isolate root causes without manual human diagnosis.

---

## 2. Project Timeline & Key Milestones

### Phase 1-4: Building the Private Cloud
We started with bare Ubuntu ISOs. We mapped out `.vmx` files, assigned static IPs, and successfully installed the massive Kolla-Ansible framework. We fought through LVM volume group blockings, container engine crashes, and successfully spun up Horizon and Nova compute agents perfectly synchronized.

### Phase 5-6: Nesting Kubernetes
We uploaded an Ubuntu cloud-image to OpenStack Glance, provisioned virtual network topologies (`ext-net` and `int-net`), and launched 3 instances. We bootstrapped `kubeadm` flawlessly across the OpenStack overlay network, overcoming intense OpenvSwitch and `qrouter` namespace MTU/routing hurdles natively over SSH.

### Phase 7-8: Telemetry and The AI Engine
With the cloud functioning, we needed eyes on it. We established Prometheus and Alertmanager inside K8s. Rather than dumping metrics to a dashboard, we built a Python AI agent equipped with actual CLI execution tools (`kubectl get pods`, `openstack server list`). We successfully simulated pod-crashes and evaluated the AI's ability to logically debug and correlate faults in real-time.

### Phase 9: Headless Stealth Operations
To ensure this entire environment wasn't hogging the desktop, we transitioned the VMware infrastructure to run completely headlessly in the background via `vmrun`.
*   Created `Start-OpenStackVMs.ps1` to background initialize.
*   Created Windows Task Scheduler jobs to run as the `SYSTEM` user.
*   Engineered clean shutdown protocols (`Stop-OpenStackVMs.ps1`) to avoid `.lck` contentions.

### Phase 10: Extensibility & Mist AI 
We upgraded the python agent code to authenticate with Juniper Mist Cloud APIs. The system prompt was rewritten to use Graph Neural Network (GNN) causality logic (Message Passing across layers), enabling it to understand that a physical Switch dropping in Mist is causally linked to a Kubernetes node dropping in OpenStack!

---

## 3. Tooling & Recovery Scripts Created

During the journey, several crucial Python and Bash scripts were engineered to manage and recover the infrastructure if it crashes. These are all saved in `H:\Kolla-Ansible\`:

*   **`k8s_full_recovery.py`**: A master Paramiko script that runs from Windows. It parses through the OpenStack `qrouter`, clears out dead CNI configs, systematically `kubeadm resets` nodes, regenerates join tokens, connects the workers, and finally upgrades the Helm Prometheus charts if they are dead.
*   **`fix_network_paramiko.py`**: Solves the complex `systemd-resolved` DNS override issue inside `ens4`/`br-ex` bridges by actively writing `8.8.8.8` logic so the Mist AI agent and Kubernetes Helm engines can reach the public internet through Windows ICS.
*   **`ai-agent\main.py`**: The LangChain brain logic, complete with Mist integrations (`get_inventory`, `get_alarms`). 
*   **`Start-OpenStackVMs.ps1`**: The obfuscated background bootstrapper for `vmrun`.

## 4. Final System State

As of project completion, the following is true:
1. All three OpenStack nodes (`10.10.10.10`, `10.10.10.11`, `10.10.10.12`) are running without hypervisor locks.
2. The `router1` namespace is forwarding traffic flawlessly to the Nova subnet.
3. K8s master and workers are `Ready`.
4. The Juniper Mist background polling API is initialized and waiting for active Mist Portal events.
5. The entire project is deeply persisted to local disks across sessions. 

The SRE architecture is actively monitoring, bridging the gap between On-Premises Cloud Compute and Physical Enterprise Networking!
