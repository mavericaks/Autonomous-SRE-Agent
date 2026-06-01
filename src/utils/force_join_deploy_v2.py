import paramiko
import time

def run_on_controller(cmd, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8').strip()
    ssh.close()
    return out

def run_on_k8s_node(node_ip, cmd, timeout=60):
    router_cmd = "source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value"
    router_id = run_on_controller(router_cmd).strip()
    
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} '{cmd}'"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)
    channel.send(full_cmd + "\n")
    time.sleep(2)
    
    output = ""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if channel.recv_ready():
            chunk = channel.recv(65535).decode('utf-8')
            output += chunk
            if 'kolla@openstack-controller' in chunk and chunk.strip().endswith('$'):
                break
        elif channel.exit_status_ready():
            break
    
    channel.close()
    ssh.close()
    return output

print("Cleaning worker 1...")
print(run_on_k8s_node("172.16.0.146", "sudo rm -rf /etc/kubernetes/kubelet.conf /etc/kubernetes/pki/ca.crt /etc/kubernetes/bootstrap-kubelet.conf"))

print("Joining worker 1...")
join_cmd = open("H:/Kolla-Ansible/k8s_join_cmd.txt").read().strip().replace('\r', '').split('\n')
join_cmd = [l.strip() for l in join_cmd if 'kubeadm join' in l][0]
print(run_on_k8s_node("172.16.0.146", f"sudo {join_cmd}"))

print("Cleaning worker 2...")
print(run_on_k8s_node("172.16.0.130", "sudo rm -rf /etc/kubernetes/kubelet.conf /etc/kubernetes/pki/ca.crt /etc/kubernetes/bootstrap-kubelet.conf"))

print("Joining worker 2...")
print(run_on_k8s_node("172.16.0.130", f"sudo {join_cmd}"))

print("Applying video app...")
print(run_on_k8s_node("172.16.0.74", "kubectl apply -f /home/ubuntu/video-app.yaml"))

print("Cluster Status:")
print(run_on_k8s_node("172.16.0.74", "kubectl get nodes && kubectl get pods -A"))
