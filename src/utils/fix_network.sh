#!/bin/bash
# Description: Restores internet connectivity to OpenStack nodes after a reboot
# by assigning an IP on the VMnet8 subnet (Windows ICS NAT) and routing through it.

echo "Fixing OpenStack Controller (10.10.10.10) Internet..."
ssh kolla@10.10.10.10 "sudo ip link set br-ex up 2>/dev/null; \
sudo ip addr add 192.168.137.10/24 dev br-ex 2>/dev/null; \
sudo ip route del default 2>/dev/null; \
sudo ip route add default via 192.168.137.1 2>/dev/null; \
sudo resolvectl dns br-ex 8.8.8.8 2>/dev/null; \
if ping -c 1 8.8.8.8 &> /dev/null; then echo 'Controller Internet Restored (192.168.137.10)'; else echo 'Controller Internet FAILED'; fi"

echo "Fixing OpenStack Compute1 (10.10.10.11) Internet..."
ssh kolla@10.10.10.11 "sudo ip link set br-ex up 2>/dev/null; \
sudo ip addr add 192.168.137.11/24 dev br-ex 2>/dev/null; \
sudo ip route del default 2>/dev/null; \
sudo ip route add default via 192.168.137.1 2>/dev/null; \
sudo resolvectl dns br-ex 8.8.8.8 2>/dev/null; \
if ping -c 1 8.8.8.8 &> /dev/null; then echo 'Compute1 Internet Restored (192.168.137.11)'; else echo 'Compute1 Internet FAILED'; fi"

echo "Fixing OpenStack Compute2 (10.10.10.12) Internet (if up)..."
ssh kolla@10.10.10.12 "sudo ip link set br-ex up 2>/dev/null; \
sudo ip addr add 192.168.137.12/24 dev br-ex 2>/dev/null; \
sudo ip route del default 2>/dev/null; \
sudo ip route add default via 192.168.137.1 2>/dev/null; \
sudo resolvectl dns br-ex 8.8.8.8 2>/dev/null; \
if ping -c 1 8.8.8.8 &> /dev/null; then echo 'Compute2 Internet Restored (192.168.137.12)'; else echo 'Compute2 Internet FAILED (or node down)'; fi"

echo "Network fix complete. To verify Kubernetes health, run:"
echo "ssh kolla@10.10.10.10 'sudo ip netns exec qrouter-... ssh -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 kubectl get nodes'"
