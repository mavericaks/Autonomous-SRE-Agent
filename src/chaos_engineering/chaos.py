import paramiko
import sys
import time

def get_ssh(ip):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username='kolla', password='<REDACTED>', timeout=10)
    return ssh

def run_cmd(ip, cmd):
    ssh = get_ssh(ip)
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    time.sleep(1)
    try:
        if stdin.channel.recv_ready(): pass
        stdin.write("<REDACTED>
")
        stdin.flush()
    except OSError:
        pass
    try:
        print(stdout.read(timeout=5).decode().strip())
    except:
        pass
    ssh.close()

if len(sys.argv) < 2:
    print("Usage: python chaos.py <fault_name>")
    sys.exit(1)

action = sys.argv[1]

if action == "cpu_fault":
    print("Injecting CPU Exhaustion on Compute1 (10.10.10.11) using native bash loops...")
    run_cmd('10.10.10.11', 'nohup bash -c "for i in {1..6}; do while :; do :; done & done" > /dev/null 2>&1 &')
elif action == "cpu_recover":
    print("Recovering CPU Exhaustion...")
    run_cmd('10.10.10.11', 'pkill -f "while :"')
elif action == "nova_fault":
    print("Injecting Nova API Crash on Controller (10.10.10.10)...")
    run_cmd('10.10.10.10', "sudo docker stop nova_api")
elif action == "nova_recover":
    print("Recovering Nova API...")
    run_cmd('10.10.10.10', "sudo docker start nova_api")
elif action == "k8s_fault":
    print("Scaling down K8s app to 0...")
    cmd = "bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=`openstack router show router1 -c id -f value` && sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 \"kubectl scale deployment demo-app --replicas=0\"'"
    run_cmd('10.10.10.10', cmd)
elif action == "k8s_recover":
    print("Scaling K8s app back to 3...")
    cmd = "bash -c 'source /etc/kolla/admin-openrc.sh && ROUTER_ID=`openstack router show router1 -c id -f value` && sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 \"kubectl scale deployment demo-app --replicas=3\"'"
    run_cmd('10.10.10.10', cmd)
else:
    print("Unknown action.")
