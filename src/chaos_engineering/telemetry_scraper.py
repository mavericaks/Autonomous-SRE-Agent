import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)

tests = [
    ("Internet", "ping -c 1 -W 3 8.8.8.8 && echo 'PASS' || echo 'FAIL'"),
    ("DNS Resolution", "host api.cerebras.ai 8.8.8.8 2>&1 | head -3"),
    ("Cerebras API", "curl -s -w '\\nHTTP_STATUS:%{http_code}' --connect-timeout 8 https://api.cerebras.ai/v1/models 2>&1 | tail -2"),
    ("Mist API", "curl -s -w '\\nHTTP_STATUS:%{http_code}' --connect-timeout 8 -H 'Authorization: Token <REDACTED_MIST_TOKEN>' https://api.gc4.mist.com/api/v1/self 2>&1 | tail -2"),
    ("AI Agent Health", "curl -s http://localhost:9999/health"),
    ("K8s via qrouter", "source /etc/kolla/admin-openrc.sh && ROUTER_ID=$(openstack router show router1 -c id -f value) && sudo ip netns exec qrouter-$ROUTER_ID ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 'kubectl get nodes' 2>&1"),
]

for label, cmd in tests:
    print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=30)
    time.sleep(1)
    # Handle sudo password prompt safely
    try:
        if stdin.channel.recv_ready():
            pass
        # For commands that need sudo password
        stdin.write("<REDACTED>
")
        stdin.flush()
    except OSError:
        pass  # Command finished instantly
    try:
        output = stdout.read().decode('utf-8').strip()
        for line in output.split('\n'):
            line = line.strip()
            if line and '[sudo]' not in line.lower() and 'password' not in line.lower():
                print(line)
    except Exception as e:
        print(f"Timeout/Error: {e}")

ssh.close()
print("\n=== FULL HEALTH CHECK COMPLETE ===")
