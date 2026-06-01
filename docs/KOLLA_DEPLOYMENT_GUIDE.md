# Kolla Ansible Multinode OpenStack Deployment Guide
### Complete Step-by-Step Walkthrough (Ubuntu 24.04 + OpenStack 2024.2 Dalmatian)

> **Tested and verified on:** VMware Workstation Pro, 64GB RAM Host, Ubuntu 24.04 Noble VMs  
> **Date:** March 2026  
> **OpenStack Release:** 2024.2 (Dalmatian)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 1: VMware Virtual Machine Setup](#2-phase-1-vmware-virtual-machine-setup)
3. [Phase 2: OS Installation & Network Configuration](#3-phase-2-os-installation--network-configuration)
4. [Phase 3: Environment Preparation](#4-phase-3-environment-preparation)
5. [Phase 4: Kolla Ansible Deployment](#5-phase-4-kolla-ansible-deployment)
6. [Phase 5: Post-Deployment & Verification](#6-phase-5-post-deployment--verification)
7. [Known Issues & Fixes](#7-known-issues--fixes)
8. [Startup Procedure After Reboot](#8-startup-procedure-after-reboot)

---

## 1. Architecture Overview

### Node Layout

| Node | Role | IP (Management) | RAM | vCPUs | Disk |
|------|------|-----------------|-----|-------|------|
| openstack-controller | Control, Network, Monitoring, Storage | 10.10.10.10 | 10GB | 4 | 100GB |
| openstack-compute1 | Compute | 10.10.10.11 | 16GB | 6 | 200GB |
| openstack-compute2 | Compute | 10.10.10.12 | 16GB | 6 | 200GB |

### Network Design

| Interface | Network Type | Purpose | Subnet |
|-----------|-------------|---------|--------|
| ens33 | NAT (VMware) | Internet access + Neutron External | DHCP from host |
| ens34 | Host-Only (VMnet2) | Management/API/Tunnel (OpenStack internal) | 10.10.10.0/24 |

- **VIP (Keepalived):** `10.10.10.200` on ens34

### Services Deployed

Core: Keystone, Nova, Neutron (OVS), Glance, Placement, Heat, Horizon  
Monitoring: Prometheus, Grafana  
Infrastructure: MariaDB, RabbitMQ, Memcached, HAProxy, Keepalived, Fluentd

---

## 2. Phase 1: VMware Virtual Machine Setup

### 2.1 Create Host-Only Network

1. Open VMware Workstation → **Edit → Virtual Network Editor**
2. Click **Add Network** → Select **VMnet2**
3. Configure:
   - Type: **Host-only**
   - Subnet IP: `10.10.10.0`
   - Subnet Mask: `255.255.255.0`
   - **Uncheck** "Use local DHCP service"
4. Click **Apply** and **OK**

### 2.2 Create VMs

Create 3 VMs with these specs:

**VM 1: openstack-controller**
- RAM: 10 GB
- vCPUs: 4
- Disk: 100 GB
- Network Adapter 1: NAT
- Network Adapter 2: Host-Only (VMnet2)

**VM 2: openstack-compute1**
- RAM: 16 GB
- vCPUs: 6
- Disk: 200 GB
- Network Adapter 1: NAT
- Network Adapter 2: Host-Only (VMnet2)

**VM 3: openstack-compute2**
- RAM: 16 GB
- vCPUs: 6
- Disk: 200 GB
- Network Adapter 1: NAT
- Network Adapter 2: Host-Only (VMnet2)

### 2.3 Enable Nested Virtualization

For **each VM**, before starting it:
1. Right-click VM → **Settings → Processors**
2. Check **"Virtualize Intel VT-x/EPT or AMD-V/RVI"**
3. Click OK

> [!IMPORTANT]
> Nested virtualization is required for KVM inside the compute nodes. Without it, Nova instances will fail to launch.

---

## 3. Phase 2: OS Installation & Network Configuration

### 3.1 Install Ubuntu 24.04

Install Ubuntu 24.04 **Desktop** on all 3 VMs with:
- Username: `kolla`
- Password: `123`
- Install OpenSSH server during installation (or install after: `sudo apt install -y openssh-server`)

### 3.2 Set Unique Hostnames

> [!CAUTION]
> Each VM **must** have a unique hostname. Kolla Ansible prechecks will fail if hostnames are not unique.

**On Controller (10.10.10.10):**
```bash
sudo hostnamectl set-hostname openstack-controller
```

**On Compute1 (10.10.10.11):**
```bash
sudo hostnamectl set-hostname openstack-compute1
```

**On Compute2 (10.10.10.12):**
```bash
sudo hostnamectl set-hostname openstack-compute2
```

### 3.3 Configure Static IPs on Host-Only Interface (ens34)

**On Controller — run:**
```bash
sudo tee /etc/netplan/01-hostonly.yaml << 'EOF'
network:
  version: 2
  ethernets:
    ens34:
      addresses:
        - 10.10.10.10/24
EOF
sudo netplan apply
```

**On Compute1 — run:**
```bash
sudo tee /etc/netplan/01-hostonly.yaml << 'EOF'
network:
  version: 2
  ethernets:
    ens34:
      addresses:
        - 10.10.10.11/24
EOF
sudo netplan apply
```

**On Compute2 — run:**
```bash
sudo tee /etc/netplan/01-hostonly.yaml << 'EOF'
network:
  version: 2
  ethernets:
    ens34:
      addresses:
        - 10.10.10.12/24
EOF
sudo netplan apply
```

### 3.4 Verify Connectivity

From the Controller, verify all nodes can reach each other:
```bash
ping -c2 10.10.10.11
ping -c2 10.10.10.12
```

---

## 4. Phase 3: Environment Preparation

> [!NOTE]
> All commands in this phase are run on the **Controller (10.10.10.10)** unless otherwise stated.

### 4.1 Configure Passwordless sudo on ALL Nodes

Run this on **all 3 VMs**:
```bash
echo "kolla ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/kolla
```

### 4.2 Set Up SSH Key Authentication (Controller → All Nodes)

**On the Controller:**
```bash
ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
ssh-copy-id kolla@10.10.10.10
ssh-copy-id kolla@10.10.10.11
ssh-copy-id kolla@10.10.10.12
```

Verify passwordless SSH works:
```bash
ssh kolla@10.10.10.11 "hostname"
ssh kolla@10.10.10.12 "hostname"
```

### 4.3 Install Kolla Ansible Dependencies (Controller Only)

```bash
sudo apt update
sudo apt install -y git python3-dev libffi-dev gcc libssl-dev python3-venv
```

### 4.4 Create Python Virtual Environment

```bash
python3 -m venv ~/kolla-venv
source ~/kolla-venv/bin/activate
pip install -U pip
pip install 'ansible-core>=2.16,<2.17'
pip install git+https://opendev.org/openstack/kolla-ansible@stable/2024.2
```

### 4.5 Install Ansible Galaxy Requirements

```bash
kolla-ansible install-deps
```

### 4.6 Create Kolla Configuration Directory

```bash
sudo mkdir -p /etc/kolla
sudo chown $USER:$USER /etc/kolla
cp ~/kolla-venv/share/kolla-ansible/etc_examples/kolla/passwords.yml /etc/kolla/
cp ~/kolla-venv/share/kolla-ansible/etc_examples/kolla/globals.yml /etc/kolla/globals.yml
```

### 4.7 Generate Passwords

```bash
source ~/kolla-venv/bin/activate
kolla-genpwd
```

### 4.8 Fix bcrypt Library (CRITICAL)

> [!WARNING]
> The `bcrypt` library version 5.x has a strict 72-byte password limit that causes Prometheus deployment to fail. You **must** downgrade it.

```bash
~/kolla-venv/bin/pip install 'bcrypt<5'
```

Verify:
```bash
~/kolla-venv/bin/python3 -c "import bcrypt; print(bcrypt.__version__)"
# Should output: 4.x.x (e.g., 4.3.0)
```

### 4.9 Patch the Prometheus Template (CRITICAL)

> [!WARNING]
> Even with bcrypt 4.x, you must patch the Prometheus web config template to truncate passwords before hashing. Without this fix, the deployment **will fail**.

```bash
sed -i 's/user.password | password_hash/user.password[:72] | password_hash/' \
  ~/kolla-venv/share/kolla-ansible/ansible/roles/prometheus/templates/prometheus-web.yml.j2
```

Verify the patch:
```bash
cat ~/kolla-venv/share/kolla-ansible/ansible/roles/prometheus/templates/prometheus-web.yml.j2
```

Expected output:
```
basic_auth_users:
{% for user in prometheus_basic_auth_users | selectattr('enabled') | list %}
    {{ user.username }}: {{ user.password[:72] | password_hash('bcrypt', salt=prometheus_bcrypt_salt) }}
{% endfor %}
```

---

## 5. Phase 4: Kolla Ansible Deployment

### 5.1 Configure globals.yml

Edit `/etc/kolla/globals.yml` and add these lines **at the bottom** (or uncomment/modify the relevant lines):

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

**Parameter explanations:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `kolla_base_distro` | `ubuntu` | Matches our Ubuntu VMs |
| `kolla_internal_vip_address` | `10.10.10.200` | Unused IP on the management subnet for HAProxy VIP |
| `network_interface` | `ens34` | Host-Only adapter for management/API/tunnel traffic |
| `neutron_external_interface` | `ens33` | NAT adapter used as the Neutron external bridge |
| `enable_haproxy` | `yes` | Load balancing for API endpoints |
| `enable_neutron_provider_networks` | `yes` | Allows flat/VLAN networks mapped to physical NICs |
| `enable_prometheus` | `yes` | Monitoring stack |
| `enable_grafana` | `yes` | Dashboards for Prometheus metrics |

### 5.2 Create the Multinode Inventory File

Copy the sample inventory:
```bash
cp ~/kolla-venv/share/kolla-ansible/ansible/inventory/multinode ~/multinode
```

Edit `~/multinode` and modify the **top sections** as follows:

```ini
[control]
10.10.10.10

[network]
10.10.10.10

[compute]
10.10.10.11
10.10.10.12

[monitoring]
10.10.10.10

[storage]
10.10.10.10

[deployment]
localhost       ansible_connection=local
```

> [!TIP]
> Leave all the other group sections (like `[baremetal:children]`, `[common:children]`, etc.) as they are in the template. Only modify the groups listed above.

### 5.3 Bootstrap the Servers

```bash
source ~/kolla-venv/bin/activate
kolla-ansible bootstrap-servers -i ~/multinode -e ansible_become_password=123
```

This installs Docker, configures NTP, sets up `/etc/hosts`, and prepares all nodes.

**Expected result:** `failed=0` on all hosts.

### 5.4 Run Prechecks

```bash
source ~/kolla-venv/bin/activate
kolla-ansible prechecks -i ~/multinode -e ansible_become_password=123
```

This validates that all prerequisites are met before deployment.

**Expected result:** `failed=0` on all hosts.

> [!NOTE]
> If prechecks fail with "Hostname has to resolve uniquely to the IP address of api_interface", recheck that hostnames are unique (see Section 3.2) and re-run `kolla-ansible bootstrap-servers` to regenerate `/etc/hosts`.

### 5.5 Deploy OpenStack

```bash
source ~/kolla-venv/bin/activate
kolla-ansible deploy -i ~/multinode -e ansible_become_password=123
```

> [!IMPORTANT]
> This step takes **30-60 minutes** depending on internet speed (container images are pulled from `quay.io`). If it fails mid-way due to a network timeout, simply re-run the same command — it's idempotent.

**Expected result:**
```
PLAY RECAP *********************************************************************
10.10.10.10 : ok=346  changed=108  unreachable=0  failed=0
10.10.10.11 : ok=63   changed=14   unreachable=0  failed=0
10.10.10.12 : ok=67   changed=14   unreachable=0  failed=0
localhost   : ok=4    changed=0    unreachable=0  failed=0
```

### 5.6 Post-Deploy (Generate Credentials)

```bash
source ~/kolla-venv/bin/activate
kolla-ansible post-deploy -i ~/multinode -e ansible_become_password=123
```

This generates:
- `/etc/kolla/admin-openrc.sh` — OpenStack admin credentials
- `/etc/openstack/clouds.yaml` — Cloud config file

### 5.7 Install OpenStack CLI Client

```bash
sudo apt install -y python3-openstackclient
```

---

## 6. Phase 5: Post-Deployment & Verification

### 6.1 Verify OpenStack Services

```bash
source /etc/kolla/admin-openrc.sh
openstack service list
```

Expected output (7 services):
```
+----+-----------+----------------+
| ID | Name      | Type           |
+----+-----------+----------------+
| .. | keystone  | identity       |
| .. | nova      | compute        |
| .. | neutron   | network        |
| .. | glance    | image          |
| .. | placement | placement      |
| .. | heat      | orchestration  |
| .. | heat-cfn  | cloudformation |
+----+-----------+----------------+
```

### 6.2 Verify Docker Containers

```bash
sudo docker ps --format 'table {{.Names}}\t{{.Status}}' | head -30
```

All containers should show `Up` and `(healthy)`.

### 6.3 Check Compute Hypervisors

```bash
source /etc/kolla/admin-openrc.sh
openstack hypervisor list
```

Should show both compute nodes.

### 6.4 Access Horizon Dashboard

Get the admin password:
```bash
grep 'keystone_admin_password' /etc/kolla/passwords.yml
```

Open your browser and navigate to:
- **URL:** `http://10.10.10.10` or `http://10.10.10.200`
- **Domain:** `default`
- **Username:** `admin`
- **Password:** (from the command above)

### 6.5 Create Test Networks & Launch an Instance

```bash
source /etc/kolla/admin-openrc.sh

# Create external network (flat, mapped to physnet1/ens33)
openstack network create --external \
  --provider-physical-network physnet1 \
  --provider-network-type flat ext-net

# Create external subnet (adjust IPs to match your NAT subnet)
openstack subnet create --network ext-net \
  --allocation-pool start=192.168.137.200,end=192.168.137.250 \
  --dns-nameserver 8.8.8.8 \
  --gateway 192.168.137.1 \
  --subnet-range 192.168.137.0/24 ext-subnet

# Create internal network
openstack network create int-net

openstack subnet create --network int-net \
  --dns-nameserver 8.8.8.8 \
  --gateway 172.16.0.1 \
  --subnet-range 172.16.0.0/24 int-subnet

# Create router connecting internal to external
openstack router create router1
openstack router set router1 --external-gateway ext-net
openstack router add subnet router1 int-subnet

# Download and upload a cloud image
wget -O jammy.img https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
openstack image create --disk-format qcow2 --container-format bare --public \
  --file jammy.img ubuntu-22.04

# Create a flavor
openstack flavor create --ram 2048 --disk 10 --vcpus 1 test-flavor

# Create a keypair
ssh-keygen -t rsa -N '' -f ~/.ssh/test_rsa
openstack keypair create --public-key ~/.ssh/test_rsa.pub test-key

# Create a security group
openstack security group create test-sg
openstack security group rule create --protocol icmp test-sg
openstack security group rule create --protocol tcp --dst-port 22 test-sg

# Launch an instance
openstack server create --flavor test-flavor --image ubuntu-22.04 \
  --key-name test-key --security-group test-sg --network int-net test-vm

# Assign a floating IP
FIP=$(openstack floating ip create ext-net -f value -c floating_ip_address)
openstack server add floating ip test-vm $FIP
echo "Floating IP: $FIP"
```

---

## 7. Known Issues & Fixes

### Issue 1: bcrypt v5 Password Length Error

**Symptom:**
```
AnsibleFilterError: Could not hash the secret.. password cannot be longer 
than 72 bytes, truncate manually if necessary
```

**Root Cause:** bcrypt 5.x strictly enforces the 72-byte password limit for bcrypt hashing.

**Fix:** Applied in Phase 3, Steps 4.8 and 4.9.

---

### Issue 2: OVS Bridge Steals Internet After Reboot

**Symptom:** After rebooting VMs, internet connectivity is lost because OpenVSwitch takes over `ens33` as a port in the `br-ex` bridge.

**Root Cause:** When the `openvswitch_vswitchd` Docker container starts, it reclaims `ens33` into `br-ex`, stripping the IP address from `ens33`.

**Fix:** Move the NAT IP from `ens33` to `br-ex` on each affected VM:

```bash
# Replace <NAT_IP> with the VM's NAT IP and <GATEWAY> with the NAT gateway
sudo ip link set br-ex up
sudo ip addr flush dev ens33
sudo ip addr add <NAT_IP>/24 dev br-ex
sudo ip route del default 2>/dev/null
sudo ip route add default via <GATEWAY> dev br-ex
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

---

### Issue 3: Non-Unique Hostnames Cause Precheck Failure

**Symptom:**
```
Hostname has to resolve uniquely to the IP address of api_interface
```

**Root Cause:** All VMs have the default Ubuntu hostname (e.g., `ubuntu`), causing DNS confusion.

**Fix:** Set unique hostnames on each VM (see Section 3.2), then re-run bootstrap.

---

### Issue 4: Docker Image Pull Fails (DNS Resolution)

**Symptom:**
```
failed to resolve reference "quay.io/openstack.kolla/nova-api:2024.2-ubuntu-noble":
lookup quay.io: server misbehaving
```

**Root Cause:** Internet connectivity lost (usually due to Issue 2 or NAT adapter disconnection).

**Fix:** Restore internet connectivity (see Issue 2), then re-run the deploy command. It's idempotent.

---

## 8. Startup Procedure After Reboot

When the host machine or VMs are restarted:

1. **Power on all 3 VMware VMs** (controller first, then computes)
2. **Wait ~2-3 minutes** for Docker containers to auto-start
3. **Fix internet on each VM** (see Issue 2 in Known Issues):
   ```bash
   # Controller (SSH via 10.10.10.10):
   echo '123' | sudo -S bash -c '
     ip link set br-ex up
     ip addr flush dev ens33
     ip addr add <CONTROLLER_NAT_IP>/24 dev br-ex
     ip route del default 2>/dev/null
     ip route add default via 192.168.137.1 dev br-ex
     echo "nameserver 8.8.8.8" > /etc/resolv.conf'
   ```
   Repeat for both compute nodes with their respective NAT IPs.
4. **Verify services:**
   ```bash
   source /etc/kolla/admin-openrc.sh
   openstack service list
   ```
5. **Check running containers:**
   ```bash
   sudo docker ps | grep -c healthy
   # Should show 20+ healthy containers on the controller
   ```

---

## Appendix A: Configuration Files Reference

### globals.yml (Custom Settings)

The only lines added at the bottom of `/etc/kolla/globals.yml`:

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

### Multinode Inventory (Top Section)

```ini
[control]
10.10.10.10

[network]
10.10.10.10

[compute]
10.10.10.11
10.10.10.12

[monitoring]
10.10.10.10

[storage]
10.10.10.10

[deployment]
localhost       ansible_connection=local
```

---

## Appendix B: Important Paths

| File | Location | Purpose |
|------|----------|---------|
| globals.yml | `/etc/kolla/globals.yml` | Main Kolla configuration |
| passwords.yml | `/etc/kolla/passwords.yml` | Auto-generated service passwords |
| admin-openrc.sh | `/etc/kolla/admin-openrc.sh` | OpenStack admin credentials |
| multinode inventory | `~/multinode` | Ansible inventory for node roles |
| Kolla virtualenv | `~/kolla-venv/` | Python environment with kolla-ansible |
| Prometheus template | `~/kolla-venv/share/kolla-ansible/ansible/roles/prometheus/templates/prometheus-web.yml.j2` | Patched for bcrypt fix |

---

## Appendix C: Service Endpoints

| Service | Internal URL | External URL |
|---------|-------------|--------------|
| Keystone (Identity) | http://10.10.10.200:5000 | http://10.10.10.200:5000 |
| Nova (Compute) | http://10.10.10.200:8774 | http://10.10.10.200:8774 |
| Neutron (Network) | http://10.10.10.200:9696 | http://10.10.10.200:9696 |
| Glance (Image) | http://10.10.10.200:9292 | http://10.10.10.200:9292 |
| Placement | http://10.10.10.200:8780 | http://10.10.10.200:8780 |
| Heat (Orchestration) | http://10.10.10.200:8004 | http://10.10.10.200:8004 |
| Horizon (Dashboard) | http://10.10.10.200:80 | http://10.10.10.200:80 |
| Grafana | http://10.10.10.200:3000 | http://10.10.10.200:3000 |
| Prometheus | http://10.10.10.200:9091 | http://10.10.10.200:9091 |
