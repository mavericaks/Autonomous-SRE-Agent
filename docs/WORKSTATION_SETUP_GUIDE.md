# Workstation Setup Guide
### Multi-Node OpenStack + Kubernetes Deployment
> **Take this to the college workstation**
> Date: 2026-02-26

---

## Workstation Specs
- **OS:** Windows + VMware Workstation
- **RAM:** 64 GB
- **CPU:** Intel (VT-x capable)
- **Status:** Has existing VMs — check RAM before creating new ones

---

## Step 1 — Arrival Checks

### 1a. Check Existing VM RAM
VMware Workstation → each existing VM → Settings → Memory
Note total RAM consumed by existing VMs.

**RAM Budget:**
```
64 GB total
- Windows host OS:       ~4 GB
- Existing VMs (running): ? GB  ← check this
- Our 3 new VMs:         42 GB  ← need this free
- Minimum needed free:   42 GB
```

### 1b. Check VMware Workstation Version
Help → About VMware Workstation
**Need:** Version 16 or higher

---

## Step 2 — VMware Network Setup

Create a dedicated Host-only network for OpenStack:
1. Edit → Virtual Network Editor → Add Network
2. Name: **VMnet2** (or any free slot)
3. Type: **Host-only**
4. Subnet: `10.10.10.0` / `255.255.255.0`
5. **Uncheck** "Use local DHCP" (we'll assign IPs manually)

---

## Step 3 — Create 3 Ubuntu 24.04 VMs

Download Ubuntu 24.04 LTS ISO first:
```
https://ubuntu.com/download/server  (Ubuntu 24.04 LTS Server)
```

### VM 1: openstack-controller
| Setting | Value |
|---|---|
| Name | `openstack-controller` |
| OS | Ubuntu 64-bit |
| RAM | **10 GB** |
| CPUs | 4 cores |
| Disk | 100 GB (single file) |
| NIC 1 | NAT (internet access) |
| NIC 2 | VMnet2 / Host-only (management) |

### VM 2: openstack-compute1
| Setting | Value |
|---|---|
| Name | `openstack-compute1` |
| RAM | **16 GB** |
| CPUs | 6 cores |
| Disk | 200 GB |
| NIC 1 | NAT |
| NIC 2 | VMnet2 / Host-only |

### VM 3: openstack-compute2
| Setting | Value |
|---|---|
| Name | `openstack-compute2` |
| RAM | **16 GB** |
| CPUs | 6 cores |
| Disk | 200 GB |
| NIC 1 | NAT |
| NIC 2 | VMnet2 / Host-only |

---

## Step 4 — CRITICAL: Enable Nested KVM on ALL 3 VMs
**Do this BEFORE powering on for the first time.**

For each VM:
VM Settings → Processors → ✅ **"Virtualize Intel VT-x/EPT or AMD-V/RVI"**

Without this, OpenStack Nova cannot launch Kubernetes VMs.

---

## Step 5 — Ubuntu Install (Same on All 3 VMs)

During installation:
- Username: `kolla` (keep consistent with current setup)
- Set a password (remember it)
- ✅ Install OpenSSH server
- No additional snaps needed
- Let it partition automatically

After install, note each VM's **management NIC IP** (on VMnet2):
```
openstack-controller:  10.10.10.10  (set static)
openstack-compute1:    10.10.10.11  (set static)
openstack-compute2:    10.10.10.12  (set static)
```

Set static IPs on the management interface (VMnet2 NIC) via:
```bash
sudo nano /etc/netplan/00-installer-config.yaml
# Add static IP for the second interface (ens37 or enp2s0 — check with: ip -br link show)
```

---

## Step 6 — Install Antigravity on Controller VM

Once Ubuntu is installed on `openstack-controller`, install the Antigravity agent and continue the deployment from there. Antigravity will handle:
1. Multi-node Kolla Ansible OpenStack deployment
2. kubeadm-based Kubernetes cluster (proper 4 GB/node)
3. OCCM + Calico with correct MTU
4. Prometheus + Grafana monitoring

---

## Architecture After Deployment

```
VMware Workstation (64 GB RAM, Windows Host)
│
├── openstack-controller (10 GB)
│   ├── Keystone, Horizon, Glance
│   ├── Nova API, Neutron Server
│   ├── MariaDB, RabbitMQ, HAProxy
│   └── Kolla Ansible orchestration
│
├── openstack-compute1 (16 GB)
│   ├── Nova Compute (runs K8s master VM)
│   └── Neutron OVS agent
│
└── openstack-compute2 (16 GB)
    ├── Nova Compute (runs K8s worker VMs)
    └── Neutron OVS agent

Kubernetes Cluster (on Nova VMs inside OpenStack):
├── k8s-master   (4 GB Nova VM on compute1)
├── k8s-worker-1 (4 GB Nova VM on compute2)
└── k8s-worker-2 (4 GB Nova VM on compute2)
```

---

## Networking Overview

```
NAT (ens33) → internet access for all VMs
VMnet2 / Host-only (ens37, 10.10.10.0/24) → OpenStack management
OpenStack Neutron external net → floating IPs for K8s nodes
OpenStack Neutron internal net (10.0.0.0/24) → K8s VM internal traffic
Calico pod CIDR (192.168.0.0/16) → Kubernetes pod networking
```

---

## Notes
- Keep this file open during deployment
- All generated scripts/guides will be saved to `/home/kolla/Documents/Minor/`
- Antigravity agent on controller VM will handle the rest
