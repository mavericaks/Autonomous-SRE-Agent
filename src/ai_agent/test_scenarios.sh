#!/bin/bash
# Test 2: K8s Pod Failure
echo "=== TEST 2: K8s Pod Failure ==="
curl -s -X POST http://localhost:9999/test \
  -H 'Content-Type: application/json' \
  -d '{"alert": "[K8s Alert] A critical pod in the kube-system namespace has been restarting repeatedly. Pod kube-proxy-abc123 on node k8s-worker1 has restarted 5 times in the last 10 minutes. CrashLoopBackOff detected. Container logs show OOM (Out of Memory) errors. Investigate the root cause of the memory exhaustion and remediate."}' && echo ""

echo "=== Waiting 30s before next test ==="
sleep 30

# Test 3: OpenStack Neutron Network Partition
echo "=== TEST 3: OpenStack Neutron Issue ==="
curl -s -X POST http://localhost:9999/test \
  -H 'Content-Type: application/json' \
  -d '{"alert": "OpenStack Neutron agent on openstack-compute1 (10.10.10.11) has gone down. Multiple tenant VMs are reporting loss of network connectivity. The neutron-openvswitch-agent service is not responding. The Open vSwitch bridge br-int may have an issue. Investigate and restore network connectivity for affected VMs."}' && echo ""

echo "=== Waiting 30s before next test ==="
sleep 30

# Test 4: Cross-layer cascading failure (should trigger Gemini escalation)
echo "=== TEST 4: Cross-Layer Cascading Failure (Gemini Escalation Test) ==="
curl -s -X POST http://localhost:9999/test \
  -H 'Content-Type: application/json' \
  -d '{"alert": "COMPLEX CASCADING FAILURE: Kubernetes pods running on OpenStack VMs are experiencing intermittent connectivity loss. The K8s worker nodes (which are OpenStack instances) show high network latency. OpenStack Neutron logs show DHCP lease renewal failures. Simultaneously, etcd on the K8s master is reporting high commit latency (>500ms). This appears to be a cross-layer issue spanning both OpenStack networking and Kubernetes control plane. The root cause is unclear and needs deep investigation across both layers."}' && echo ""

echo "=== All tests complete ==="
