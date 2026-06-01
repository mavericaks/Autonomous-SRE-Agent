# Quick Reference: Health Check Commands
> Run these from your Windows terminal (SSH into the controller) or directly on the controller VM.

---

## 🔌 OpenStack Services

```bash
# Source credentials first
source /etc/kolla/admin-openrc.sh

# List all services
openstack service list

# List API endpoints
openstack endpoint list

# Check compute hypervisors
openstack hypervisor list

# List running instances
openstack server list

# List networks, routers, floating IPs
openstack network list
openstack router list
openstack floating ip list

# List images and flavors
openstack image list
openstack flavor list

# Check Neutron agents
openstack network agent list
```

---

## 🐳 Docker Containers (on each VM)

```bash
# Count healthy containers
sudo docker ps --format '{{.Names}} {{.Status}}' | grep -c healthy

# List all containers with status
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'

# Check a specific container's logs
sudo docker logs <container_name> --tail 50

# Restart a container
sudo docker restart <container_name>
```

---

## ☸️ Kubernetes Cluster (from k8s-master)

```bash
# SSH into k8s-master from controller
ssh -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229

# Check nodes
kubectl get nodes

# Check all pods (all namespaces)
kubectl get pods -A

# Check monitoring pods
kubectl get pods -n monitoring

# Check services
kubectl get svc -A

# Describe a pod (for debugging)
kubectl describe pod <pod-name> -n <namespace>

# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check cluster info
kubectl cluster-info
```

---

## 📊 Monitoring Access

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| Horizon | http://10.10.10.10 | `admin` | `<REDACTED_OS_PASSWORD>` |
| Grafana | http://10.10.10.10:3000 | `admin` | `DVDl10RWwECLcIev4PcdFuAhuznYHnX6oo1a7rIU` |
| Prometheus | http://10.10.10.10:9091 | `admin` | `VlgbNmcbQDvwXK7YBQil31sfEvQ1zN0WvUDwNfaI` |

---

## 🔧 Post-Reboot Recovery

```bash
# On EACH VM — move NAT IP to br-ex (replace <NAT_IP> accordingly):
# Controller: 192.168.137.196  |  Compute1: 192.168.137.7  |  Compute2: 192.168.137.13
sudo ip link set br-ex up
sudo ip addr flush dev ens33
sudo ip addr add <NAT_IP>/24 dev br-ex
sudo ip route del default 2>/dev/null
sudo ip route add default via 192.168.137.1 dev br-ex
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

---

## 🩺 Quick Health Check (run from controller)

```bash
source /etc/kolla/admin-openrc.sh

echo "=== OpenStack Services ==="
openstack service list

echo "=== Hypervisors ==="
openstack hypervisor list

echo "=== Instances ==="
openstack server list

echo "=== Network Agents ==="
openstack network agent list

echo "=== Docker Containers ==="
sudo docker ps --format '{{.Names}} {{.Status}}' | grep -v healthy | head -5
echo "Unhealthy containers above (empty = all good)"

echo "=== K8s Nodes ==="
ssh -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 'kubectl get nodes' 2>/dev/null

echo "=== K8s Monitoring ==="
ssh -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 'kubectl get pods -n monitoring' 2>/dev/null
```
