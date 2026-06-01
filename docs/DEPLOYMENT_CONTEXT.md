# OpenStack + Kubernetes Deployment Context
> Last updated: 2026-03-02

## VM Infrastructure (VMware Workstation)

| VM | IP (Host-Only) | NAT IP (br-ex) | RAM | vCPUs | Role |
|---|---|---|---|---|---|
| openstack-controller | 10.10.10.10 | 192.168.137.196 | 10GB | 4 | Controller |
| openstack-compute1 | 10.10.10.11 | 192.168.137.7 | 16GB | 6 | Compute |
| openstack-compute2 | 10.10.10.12 | 192.168.137.13 | 16GB | 6 | Compute |

- **VM User:** `kolla` / **Password:** `123`
- **VIP (Keepalived):** `10.10.10.200`

## OpenStack Credentials

- **Horizon URL:** http://10.10.10.10
- **Username:** `admin` / **Password:** `<REDACTED_OS_PASSWORD>`
- **Admin OpenRC:** `/etc/kolla/admin-openrc.sh` (on controller)

## OpenStack Monitoring (Kolla-deployed, WORKING)

- **Grafana:** http://10.10.10.10:3000 — User: `admin` / Pass: `DVDl10RWwECLcIev4PcdFuAhuznYHnX6oo1a7rIU`
- **Prometheus:** http://10.10.10.10:9091 — User: `admin` / Pass: `VlgbNmcbQDvwXK7YBQil31sfEvQ1zN0WvUDwNfaI`

## OpenStack Networking

| Resource | Name | Details |
|---|---|---|
| External Network | ext-net | flat/physnet1, 192.168.137.0/24, pool: .200-.250 |
| Internal Network | int-net | vxlan, 172.16.0.0/24 |
| Router | router1 | gateway: ext-net, interface: int-subnet |

## Kubernetes Cluster (Inside OpenStack)

### Instances

| Instance | Host | Internal IP | Floating IP | K8s Role |
|---|---|---|---|---|
| k8s-master | openstack-compute1 | 172.16.0.74 | 192.168.137.229 | control-plane |
| k8s-worker-1 | openstack-compute1 | 172.16.0.146 | 192.168.137.248 | worker |
| k8s-worker-2 | openstack-compute1 | 172.16.0.130 | 192.168.137.211 | worker |

- **Instance User:** `ubuntu` / **Console Password:** `123`
- **SSH Key:** `~kolla/.ssh/k8s_rsa` (on controller)
- **Kubernetes Version:** v1.29.15
- **CNI:** Calico v3.27.0
- **Container Runtime:** containerd

### K8s Monitoring (Helm-deployed, access via SSH tunnel only)

- kube-prometheus-stack deployed in `monitoring` namespace
- Grafana password: `prom-operator` (default Helm chart password)
- **Note:** NodePorts and floating IPs don't work for accessing K8s services due to OpenStack virtual networking. Use SSH tunnel from controller or access from within the cluster.

### K8s Join Command (for reference)
```
kubeadm join 172.16.0.74:6443 --token imxq5c.c64alm79gchl7ju6 \
  --discovery-token-ca-cert-hash sha256:4af0cda35f25065c71217b00f03dba26901293d35cea265883c38cbb141b015d
```

## Known Issues & Fixes

1. **OVS steals ens33 after reboot** — Move NAT IP to br-ex (see KOLLA_DEPLOYMENT_GUIDE.md)
2. **bcrypt v5 bug** — Downgrade to `bcrypt<5` and patch prometheus-web.yml.j2
3. **SSL proxy intercepts HTTPS inside OpenStack VMs** — Use `curl -k`, pre-stage GPG keys, or copy .deb packages between VMs
4. **K8s NodePorts unreachable via floating IPs** — Use SSH tunnels from controller instead

## Startup Procedure After Reboot

1. Power on all 3 VMware VMs
2. Wait ~2 min for Docker containers to auto-start
3. Fix internet by moving NAT IP to br-ex on each VM
4. Verify: `openstack service list` and `openstack server list`
5. K8s instances should auto-start; verify with `kubectl get nodes` from k8s-master
