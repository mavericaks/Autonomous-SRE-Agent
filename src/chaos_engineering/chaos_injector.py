import paramiko
import time
import sys

def get_ssh_client(ip):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username='kolla', password='<REDACTED>', timeout=10)
    return ssh

def run_cmd(ssh, cmd, sudo=False):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    time.sleep(1)
    if sudo:
        try:
            if stdin.channel.recv_ready():
                pass
            stdin.write("<REDACTED>
")
            stdin.flush()
        except OSError:
            pass
    try:
        out = stdout.read().decode('utf-8').strip()
        return out
    except:
        return ""

print("========================================")
print("  AUTONOMOUS CHAOS ENGINEERING SUITE")
print("========================================")

# --- FAULT 1: CPU Exhaustion ---
print("\n[1/3] Injecting CPU Exhaustion Fault on Compute1 (10.10.10.11)...")
ssh_compute1 = get_ssh_client('10.10.10.11')
run_cmd(ssh_compute1, "sudo apt-get update && sudo apt-get install stress -y", sudo=True)
# Run stress in background
run_cmd(ssh_compute1, "nohup stress --cpu 6 --timeout 120 > /dev/null 2>&1 &", sudo=False)

print(">>> FAULT INJECTED! Please watch the Grafana Node Exporter dashboard for 10.10.10.11.")
print(">>> Waiting 45 seconds for metrics to appear in Grafana...")
time.sleep(45)

print("\n[1/3] Recovering CPU Exhaustion Fault...")
run_cmd(ssh_compute1, "sudo killall stress", sudo=True)
ssh_compute1.close()
print(">>> RECOVERED! CPU usage should drop back to normal on the dashboard.")
print(">>> Waiting 15 seconds before next fault...")
time.sleep(15)

# --- FAULT 2: Nova API Crash ---
print("\n[2/3] Injecting OpenStack Nova API Failure on Controller (10.10.10.10)...")
ssh_controller = get_ssh_client('10.10.10.10')
run_cmd(ssh_controller, "sudo docker stop nova_api", sudo=True)

print(">>> FAULT INJECTED! Please watch the OpenStack Services / Nova dashboard.")
print(">>> The nova_api service should show as DOWN.")
print(">>> Waiting 45 seconds for metrics to appear in Grafana...")
time.sleep(45)

print("\n[2/3] Recovering Nova API Failure...")
run_cmd(ssh_controller, "sudo docker start nova_api", sudo=True)
print(">>> RECOVERED! nova_api should show as UP again.")
print(">>> Waiting 15 seconds before next fault...")
time.sleep(15)

# --- FAULT 3: K8s App Crash ---
print("\n[3/3] Setting up Kubernetes Test Application...")
setup_cmd = "bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=`openstack router show router1 -c id -f value` && sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 \"kubectl create deployment demo-app --image=nginx && kubectl scale deployment demo-app --replicas=3\"'"
run_cmd(ssh_controller, setup_cmd, sudo=True)
time.sleep(10)

print("\n[3/3] Injecting Kubernetes Application Failure (Scaling down to 0)...")
fault_cmd = "bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=`openstack router show router1 -c id -f value` && sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 \"kubectl scale deployment demo-app --replicas=0\"'"
run_cmd(ssh_controller, fault_cmd, sudo=True)

print(">>> FAULT INJECTED! If you check K8s Workload Grafana, Pods available will be 0.")
print(">>> Waiting 30 seconds...")
time.sleep(30)

print("\n[3/3] Recovering Kubernetes Application Failure...")
recover_cmd = "bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=`openstack router show router1 -c id -f value` && sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 \"kubectl scale deployment demo-app --replicas=3\"'"
run_cmd(ssh_controller, recover_cmd, sudo=True)
ssh_controller.close()

print(">>> RECOVERED! K8s pods are restored.")
print("\n========================================")
print("  CHAOS ENGINEERING SUITE COMPLETE!")
print("========================================")
