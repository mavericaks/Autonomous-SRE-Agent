import paramiko
import sys
import time

nodes = {
    '10.10.10.10': '192.168.137.10',
    '10.10.10.11': '192.168.137.11',
    '10.10.10.12': '192.168.137.12'
}

for ip, ics_ip in nodes.items():
    print(f"Fixing network on {ip}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, username='kolla', password='<REDACTED>', timeout=10)
        
        cmds = [
            'sudo ip link set br-ex up',
            f'sudo ip addr add {ics_ip}/24 dev br-ex',
            'sudo ip route del default',
            'sudo ip route add default via 192.168.137.1',
            'sudo resolvectl dns br-ex 8.8.8.8'
        ]
        
        for c in cmds:
            stdin, stdout, stderr = ssh.exec_command(c, get_pty=True)
            stdin.write('<REDACTED>
')
            stdin.flush()
            time.sleep(0.5)
            
        stdin, stdout, stderr = ssh.exec_command('ping -c 1 8.8.8.8', get_pty=True)
        out = stdout.read().decode()
        if '1 received' in out or 'bytes from 8.8.8.8' in out:
            print(f"{ip} Internet Restored.")
        else:
            print(f"{ip} Internet FAILED.")
            
        if ip == '10.10.10.10':
            # run grafana port forward on controller if kubectl is there
            print("Starting port forward on controller...")
            # We copy the port-forward commands. 
            stdin, stdout, stderr = ssh.exec_command('nohup kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 --address 0.0.0.0 > /tmp/grafana-pf.log 2>&1 &', get_pty=True)
            stdin.write('<REDACTED>
')
            stdin.flush()
            time.sleep(1)
            
            stdin, stdout, stderr = ssh.exec_command('nohup kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 --address 0.0.0.0 > /tmp/prom-pf.log 2>&1 &', get_pty=True)
            stdin.write('<REDACTED>
')
            stdin.flush()
            time.sleep(1)
            
            stdin, stdout, stderr = ssh.exec_command('ss -tlnp | grep -E "3000|9090"', get_pty=True)
            print(stdout.read().decode())
            
        ssh.close()
    except Exception as e:
        print(f"Failed to connect to {ip}: {e}")

