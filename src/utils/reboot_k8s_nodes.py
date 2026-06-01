import paramiko
import time

def run_on_controller(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8').strip()
    ssh.close()
    return out

def run_on_node(ip, cmd):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@{ip} '{cmd}'"
    return run_on_controller(full_cmd)

print("Reverting Calico env change...")
run_on_node("172.16.0.74", "kubectl set env daemonset/calico-node -n kube-system CALICO_IPV4POOL_IPIP- CALICO_IPV4POOL_VXLAN-")

print("Rebooting k8s-worker-1...")
run_on_node("172.16.0.146", "sudo reboot")

print("Wait 10 seconds, then reboot master...")
time.sleep(10)
run_on_node("172.16.0.74", "sudo reboot")

print("Reboot commands sent.")
